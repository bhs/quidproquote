"""The priority form's checks. The maintainer pastes a link: the page is fetched and its outlet (og:site_name,
else the domain) and date are read from it for the maintainer to confirm or correct. The pasted words are accepted
only when they appear on the page, fetched again, word for word (typographic quotes and dashes straightened,
whitespace collapsed). The retrieval date is the day the check ran, set here and never taken from the form.

A priority is either a news report (kind 'news report', with its outlet) or a page on the donor's own site. An edit
keeps the earlier row whole in the audit log (snapshot_of) and the history is read back from there (history).
"""

import datetime
import html.parser
import ipaddress
import json
import re
import socket
import urllib.parse

from . import db, sources  # noqa: F401

import fmap_lib as fl  # noqa: E402

MIN_WORDS = 6
MAX_OUTLET = 120
KIND_NEWS = "news report"
KIND_OWN = "page on the organisation's own site"
KINDS = {"news": KIND_NEWS, "own": KIND_OWN}  # what the form's choice stores
ISO_DAY = re.compile(r"\d{4}-\d{2}-\d{2}")


class PriorityError(ValueError):
    """The form's input cannot be accepted; the message says why, for the person who filled it in."""


def check_public_url(url):
    """The URL's parts, refusing anything that is not an http(s) page on a public address."""
    parts = urllib.parse.urlsplit((url or "").strip())
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise PriorityError("The link must be a full web address starting with http:// or https://.")
    try:
        infos = socket.getaddrinfo(parts.hostname, parts.port or (443 if parts.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise PriorityError("The address %s did not resolve (%s)." % (parts.hostname, exc))
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise PriorityError("The address %s is not a public web page." % parts.hostname)
    return parts


def words_on_page(page_html, words):
    """True when `words` (squashed) occur verbatim in the visible text of the page."""
    needle = fl.squash(words)
    return bool(needle) and needle in fl.page_text(page_html)


def verify(url, words, fetch=None):
    """{'url', 'text', 'retrieved'} for words found verbatim on the page. Raises PriorityError otherwise."""
    words = fl.squash(words)
    if len(words.split()) < MIN_WORDS:
        raise PriorityError("Paste the donor's sentence or two, at least %d words, exactly as the page shows them." % MIN_WORDS)
    check_public_url(url)
    try:
        raw = (fetch or fl.fetch_page)(url.strip())
    except OSError as exc:
        raise PriorityError("The page could not be fetched (%s: %s); nothing was saved." % (type(exc).__name__, exc))
    if not words_on_page(raw, words):
        raise PriorityError("Those words are not on the page as fetched just now, word for word; nothing was saved. "
                            "Copy them from the page itself.")
    return {"url": url.strip(), "text": words, "retrieved": fl.today()}


# --------------------------------------------------------------------------- outlet and date from the page

DATE_KEYS = ("article:published_time", "og:article:published_time", "datepublished", "date", "pubdate", "publishdate",
             "dc.date.issued", "dcterms.created", "parsely-pub-date", "sailthru.date")


class PageMeta(html.parser.HTMLParser):
    """The meta tags of a page (by property, name or itemprop, first one wins), its first <time datetime> and its
    JSON-LD blocks."""

    def __init__(self):
        super().__init__()
        self.meta, self.time, self.ld, self._in_ld = {}, "", [], False

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "meta" and a.get("content"):
            for key in (a.get("property"), a.get("name"), a.get("itemprop")):
                if key:
                    self.meta.setdefault(key.strip().lower(), a["content"].strip())
        elif tag == "time" and a.get("datetime") and not self.time:
            self.time = a["datetime"].strip()
        elif tag == "script" and "ld+json" in a.get("type", "").lower():
            self._in_ld = True
            self.ld.append("")

    def handle_endtag(self, tag):
        if tag == "script":
            self._in_ld = False

    def handle_data(self, data):
        if self._in_ld:
            self.ld[-1] += data


def day_of(value):
    """The yyyy-mm-dd day a date text states ('2026-10-08T09:00:00Z', 'October 8, 2026'), or ''."""
    value = (value or "").strip()
    m = ISO_DAY.match(value)
    candidates = [m.group(0)] if m else []
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%d %B %Y"):
        try:
            candidates.append(datetime.datetime.strptime(value, fmt).date().isoformat())
        except ValueError:
            pass
    for day in candidates:
        try:
            datetime.date.fromisoformat(day)
            return day
        except ValueError:
            pass
    return ""


def domain_of(url):
    host = urllib.parse.urlsplit(url or "").hostname or ""
    return host[4:] if host.startswith("www.") else host


def page_details(raw_html, url):
    """{'outlet', 'page_date'} read from a fetched page: the outlet is og:site_name or else the domain of the
    link; the date is the first the page's metadata gives ('' when it gives none)."""
    parser = PageMeta()
    try:
        parser.feed(raw_html or "")
        parser.close()
    except Exception:  # a page the parser cannot read still has a domain
        pass
    outlet = " ".join(parser.meta.get("og:site_name", "").split()) or domain_of(url)
    candidates = [parser.meta.get(k, "") for k in DATE_KEYS]
    for block in parser.ld:
        m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', block)
        if m:
            candidates.append(m.group(1))
    candidates.append(parser.time)
    page_date = next((d for d in (day_of(c) for c in candidates) if d), "")
    return {"outlet": outlet[:MAX_OUTLET], "page_date": page_date}


def lookup(url, fetch=None):
    """{'url', 'outlet', 'page_date'} for a pasted link: the page is fetched and read for its outlet and date."""
    check_public_url(url)
    try:
        raw = (fetch or fl.fetch_page)(url.strip())
    except OSError as exc:
        raise PriorityError("The page could not be fetched (%s: %s). Check the link, or fill in the outlet and date yourself." % (
            type(exc).__name__, exc))
    return dict(page_details(raw, url.strip()), url=url.strip())


def clean_source(outlet, page_date, kind_key, today=None):
    """{'outlet', 'page_date', 'kind'} from the form's source fields, or PriorityError saying what to fix. A news
    report needs its outlet and the day the page shows; a page on the donor's own site needs neither, but a date
    that is given must be a real day that is not in the future."""
    kind = KINDS.get(kind_key)
    if not kind:
        raise PriorityError("Choose whether this is a news report or the donor's own page.")
    outlet = " ".join((outlet or "").split())
    page_date = (page_date or "").strip()
    if len(outlet) > MAX_OUTLET:
        raise PriorityError("The outlet is longer than %d characters." % MAX_OUTLET)
    if kind == KIND_NEWS and not outlet:
        raise PriorityError("Name the outlet of the news report (Fetch outlet and date reads it from the page).")
    if kind == KIND_NEWS and not page_date:
        raise PriorityError("Give the date the article shows, as year-month-day (Fetch outlet and date reads it from the page).")
    if page_date:
        try:
            if not ISO_DAY.fullmatch(page_date):
                raise ValueError(page_date)
            day = datetime.date.fromisoformat(page_date)
        except ValueError:
            raise PriorityError("The page date %r is not a real day; write it as year-month-day, like 2026-10-08." % page_date)
        if day > datetime.date.fromisoformat(today or fl.today()):
            raise PriorityError("The page date %s is in the future." % page_date)
    return {"outlet": outlet if kind == KIND_NEWS else "", "page_date": page_date, "kind": kind}


# --------------------------------------------------------------------------- saving, editing and history

def snapshot_of(row):
    """The whole row as plain JSON-ready values (dates as text)."""
    return {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in row.items()}


def add(conn, fam, key, found, source, actor, section=""):
    """Inserts a new priority (found from verify, source from clean_source). Returns its id."""
    pid = conn.execute(
        "INSERT INTO donor_priorities (key, family, donor, url, section, text, page_date, retrieved, kind, outlet, "
        "added_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (key, fam["key"], fam["name"], found["url"], section, found["text"], source["page_date"], found["retrieved"],
         source["kind"], source["outlet"], actor)).lastrowid
    db.audit(conn, actor, "priority added", None,
             "%s: %s%s (words found verbatim on the page; retrieved %s)" % (
                 fam["name"], found["url"], " [news report: %s]" % source["outlet"] if source["kind"] == KIND_NEWS else "",
                 found["retrieved"]), priority_id=pid)
    return pid


def keep_own_kind(row, source):
    """A priority on a donor's own page keeps the kind of page it was filed under when only 'own page' is chosen
    again (the survey's rows name the page more closely than the form does)."""
    if source["kind"] == KIND_OWN and row["kind"] != KIND_NEWS:
        source["kind"] = row["kind"]
    return source


def unchanged(row, url, words, source):
    """True when the form states what the row already holds (the retrieval date is not a field)."""
    return (row["url"] == url.strip() and row["text"] == fl.squash(words) and row["page_date"] == source["page_date"]
            and row["kind"] == source["kind"] and row["outlet"] == source["outlet"])


def kind_key(kind):
    """The form's choice for a stored kind."""
    return "news" if kind == KIND_NEWS else "own"


def update(conn, pid, found, source, actor, expected_version=None):
    """Replaces the current wording and source of a priority with the re-verified ones. The old row is first
    written in full to the audit log. PriorityError when the priority is gone or was edited since the form was
    opened (expected_version)."""
    old = conn.execute("SELECT * FROM donor_priorities WHERE id = ?", (pid,)).fetchone()
    if not old:
        raise PriorityError("That priority no longer exists.")
    if expected_version is not None and old["version"] != expected_version:
        raise PriorityError("This priority was edited after you opened the form (it is now version %d); "
                            "open it again to see the current wording." % old["version"])
    db.audit(conn, actor, "priority edited", None,
             "%s: version %d replaced by version %d; the earlier wording and source are kept in this entry" % (
                 old["donor"], old["version"], old["version"] + 1), priority_id=pid, snapshot=snapshot_of(old))
    conn.execute(
        "UPDATE donor_priorities SET url = ?, text = ?, page_date = ?, retrieved = ?, kind = ?, outlet = ?, "
        "version = version + 1, updated_at = ? WHERE id = ?",
        (found["url"], found["text"], source["page_date"], found["retrieved"], source["kind"], source["outlet"],
         db.now(), pid))


def history(conn, pid):
    """(current row, earlier versions newest first). Each earlier version is its snapshot with 'superseded_at'
    and 'superseded_by' from the audit entry that kept it. (None, []) when there is no such priority."""
    current = conn.execute("SELECT * FROM donor_priorities WHERE id = ?", (pid,)).fetchone()
    earlier = []
    for e in conn.execute("SELECT at, actor, snapshot FROM audit_log WHERE priority_id = ? AND snapshot IS NOT NULL "
                          "ORDER BY id DESC", (pid,)):
        earlier.append(dict(e["snapshot"], superseded_at=e["at"], superseded_by=e["actor"]))
    return current, earlier


def edit_counts(conn):
    """{priority id: number of earlier wordings kept}."""
    return {r["priority_id"]: r["n"] for r in conn.execute(
        "SELECT priority_id, count(*) AS n FROM audit_log WHERE priority_id IS NOT NULL AND snapshot IS NOT NULL "
        "GROUP BY priority_id")}
