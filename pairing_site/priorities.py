"""Donors' priorities: the form's checks, saving, editing and the history of an edited priority.

A priority is entered in one of two ways. From the donor's own site, the page is fetched and the pasted words must
appear on it word for word (typographic quotes and dashes straightened, whitespace collapsed), or nothing is saved.
From a news report, the outlet, the date of the article and whose words they are are required; the page is fetched
and the words must be on it when it can be, and when it cannot be fetched the priority is saved marked "not checked
against page". The retrieval date is the day the check ran, set here and never taken from the form.

An edit never overwrites: it inserts a new row whose supersedes_key is the key of the row it replaces and stamps the
old row's replaced_at. Lists show the rows not replaced; earlier_versions() walks the chain back.
"""

import datetime
import ipaddress
import re
import socket
import urllib.parse
import uuid

from . import db, sources  # noqa: F401  (sources puts the discovery libraries on the path)

import fmap_lib as fl  # noqa: E402

MIN_WORDS = 6
OWN_KIND = "page on the organisation's own site"
REPORTED_KIND = "news report"
WHOSE = {"reporter": "the reporter's", "donor_person": "a named person at the donor, quoted",
         "third_party": "a third party's"}
FIELDS = ("url", "words", "section", "page_date", "outlet", "whose_words")
MAX_SECTION, MAX_OUTLET = 200, 120


class PriorityError(ValueError):
    """The form's input cannot be accepted; the message says why, for the person who filled it in."""


class PageUnavailable(PriorityError):
    """The page could not be reached or fetched (as opposed to being fetched without the words on it)."""


class PriorityGone(PriorityError):
    """The priority being edited does not exist or has already been replaced."""


def whose_label(value):
    return WHOSE.get(value, "")


# --------------------------------------------------------------------------- checking the input

def check_url_syntax(url):
    parts = urllib.parse.urlsplit((url or "").strip())
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise PriorityError("The link must be a full web address starting with http:// or https://.")
    return parts


def check_public_url(url):
    """The URL's parts, refusing anything that is not an http(s) page on a public address."""
    parts = check_url_syntax(url)
    try:
        infos = socket.getaddrinfo(parts.hostname, parts.port or (443 if parts.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise PageUnavailable("The address %s did not resolve (%s)." % (parts.hostname, exc))
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise PriorityError("The address %s is not a public web page." % parts.hostname)
    return parts


def words_on_page(page_html, words):
    """True when `words` (squashed) occur verbatim in the visible text of the page."""
    needle = fl.squash(words)
    return bool(needle) and needle in fl.page_text(page_html)


def check_words(words):
    words = fl.squash(words)
    if len(words.split()) < MIN_WORDS:
        raise PriorityError("Paste the donor's sentence or two, at least %d words, exactly as the page shows them." % MIN_WORDS)
    return words


def check_date(text, required):
    """The date as ISO text, '' when it is optional and empty. Written year-month-day, a real day, not in the future."""
    text = (text or "").strip()
    if not text:
        if required:
            raise PriorityError("Enter the date the article was published (year-month-day).")
        return ""
    try:
        day = datetime.date.fromisoformat(text) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text) else None
    except ValueError:
        day = None
    if day is None:
        raise PriorityError("The page date %r is not a real date; write it year-month-day, like 2026-10-08." % text[:40])
    if day > db.today():
        raise PriorityError("The page date %s is in the future." % text)
    return text


def clean(ptype, form):
    """The form's fields trimmed and checked for this type ('own' or 'reported'), without touching the network.
    Raises PriorityError naming the first thing wrong."""
    reported = ptype == "reported"
    f = {k: (form.get(k) or "").strip() for k in FIELDS}
    if not f["url"]:
        raise PriorityError("Add the link to the news report." if reported else "Add the link to the donor's page.")
    check_url_syntax(f["url"])
    if reported:
        if not f["outlet"]:
            raise PriorityError("Name the outlet that published the report.")
        if len(f["outlet"]) > MAX_OUTLET:
            raise PriorityError("The outlet name is longer than %d characters." % MAX_OUTLET)
        if f["whose_words"] not in WHOSE:
            raise PriorityError("Say whose words these are: the reporter's, a named person at the donor quoted, or a third party's.")
    else:
        f["outlet"] = f["whose_words"] = ""
    f["page_date"] = check_date(f["page_date"], required=reported)
    if len(f["section"]) > MAX_SECTION:
        raise PriorityError("The section heading is longer than %d characters." % MAX_SECTION)
    f["words"] = check_words(f["words"])
    return f


def verify(url, words, fetch=None, strict=True):
    """{'url', 'text', 'retrieved', 'checked'} for words found verbatim on the page. Raises PriorityError when the
    page does not show them. A page that cannot be fetched raises PageUnavailable when strict; otherwise the words
    come back with checked False."""
    words = check_words(words)
    url = url.strip()
    try:
        check_public_url(url)
        raw = (fetch or fl.fetch_page)(url)
    except PageUnavailable as exc:
        if strict:
            raise
        return {"url": url, "text": words, "retrieved": fl.today(), "checked": False, "why": str(exc)}
    except OSError as exc:
        why = "The page could not be fetched (%s: %s)" % (type(exc).__name__, exc)
        if strict:
            raise PageUnavailable(why + "; nothing was saved.")
        return {"url": url, "text": words, "retrieved": fl.today(), "checked": False, "why": why}
    if not words_on_page(raw, words):
        raise PriorityError("Those words are not on the page as fetched just now, word for word; nothing was saved. "
                            "Copy them from the page itself.")
    return {"url": url, "text": words, "retrieved": fl.today(), "checked": True, "why": ""}


# --------------------------------------------------------------------------- reading

def new_key(prefix):
    return "%s-%d-%s" % (prefix, int(db.now().timestamp()), uuid.uuid4().hex[:6])


def get(conn, priority_id):
    return conn.execute("SELECT * FROM donor_priorities WHERE id = ?", (priority_id,)).fetchone()


def current_rows(conn, limit=40):
    """The priorities in force (not replaced by an edit), newest first."""
    return conn.execute("SELECT * FROM donor_priorities WHERE replaced_at IS NULL "
                        "ORDER BY added_at DESC, id DESC LIMIT ?", (limit,)).fetchall()


def earlier_versions(conn, row):
    """The versions `row` replaced, newest first, each with its replaced_at."""
    out, seen = [], {row["key"]}
    key = row["supersedes_key"]
    while key and key not in seen:
        prev = conn.execute("SELECT * FROM donor_priorities WHERE key = ?", (key,)).fetchone()
        if not prev:
            break
        out.append(prev)
        seen.add(key)
        key = prev["supersedes_key"]
    return out


def current_version(conn, row):
    """The version in force of the priority `row` is a version of (itself when it was never replaced)."""
    seen = {row["id"]}
    while row["replaced_at"]:
        nxt = conn.execute("SELECT * FROM donor_priorities WHERE supersedes_key = ? ORDER BY id DESC LIMIT 1",
                           (row["key"],)).fetchone()
        if not nxt or nxt["id"] in seen:
            break
        row = nxt
        seen.add(row["id"])
    return row


# --------------------------------------------------------------------------- writing

def _insert(conn, key, family, donor, kind, fields, found, actor, supersedes_key=None):
    conn.execute(
        "INSERT INTO donor_priorities (key, family, donor, url, section, text, page_date, retrieved, kind, added_by, "
        "outlet, whose_words, page_checked, supersedes_key) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (key, family, donor, found["url"], fields["section"], found["text"], fields["page_date"], found["retrieved"],
         kind, actor, fields["outlet"], fields["whose_words"], 1 if found["checked"] else 0, supersedes_key))
    return conn.execute("SELECT * FROM donor_priorities WHERE key = ?", (key,)).fetchone()


def add(ptype, fam, form, actor, fetch=None):
    """Checks and saves a new priority of the donor family `fam` ({'key', 'name'}). Returns (row, found)."""
    fields = clean(ptype, form)
    found = verify(fields["url"], fields["words"], fetch=fetch, strict=ptype != "reported")  # before the write lock
    kind = REPORTED_KIND if ptype == "reported" else OWN_KIND
    with db.session(write=True) as conn:
        row = _insert(conn, new_key("form-" + fam["key"]), fam["key"], fam["name"], kind, fields, found, actor)
        how = ("words found verbatim on the page" if found["checked"]
               else "NOT checked against the page: %s" % found["why"])
        db.audit(conn, actor, "priority added", None, "%s: %s (%s; %s; retrieved %s)" % (
            fam["name"], found["url"], "reported by %s, words are %s" % (fields["outlet"], whose_label(fields["whose_words"]))
            if ptype == "reported" else "donor's own site", how, found["retrieved"]))
    return row, found


def supersede(conn, old, fields, found, actor):
    """Inside a write session: inserts the new version of `old` and marks `old` replaced. Returns the new row."""
    done = conn.execute("UPDATE donor_priorities SET replaced_at = ? WHERE id = ? AND replaced_at IS NULL",
                        (db.now(), old["id"]))
    if done.rowcount != 1:
        raise PriorityGone("This priority was edited by someone else a moment ago; reload the page to see it.")
    return _insert(conn, new_key("edit-" + old["family"]), old["family"], old["donor"], old["kind"], fields, found,
                   actor, supersedes_key=old["key"])


def edit(priority_id, form, actor, fetch=None):
    """Saves an edit of a priority in force as a new version. The page is checked again only when the link or the
    words changed. Returns the new row. Raises PriorityError (PriorityGone when it is not in force)."""
    with db.session() as conn:
        old = get(conn, priority_id)
    if not old or old["replaced_at"]:
        raise PriorityGone("This priority is no longer the current one; reload the page.")
    ptype = "reported" if old["whose_words"] else "own"
    fields = clean(ptype, form)
    same_words = (form.get("words") or "").replace("\r\n", "\n").strip() == old["text"].replace("\r\n", "\n").strip()
    if same_words:
        fields["words"] = old["text"]  # untouched words are kept character for character, never re-squashed
    if (fields["url"], fields["words"], fields["section"], fields["page_date"], fields["outlet"], fields["whose_words"]) == (
            old["url"], old["text"], old["section"], old["page_date"], old["outlet"], old["whose_words"]):
        raise PriorityError("Nothing was changed.")
    if fields["url"] == old["url"] and same_words:
        found = {"url": old["url"], "text": old["text"], "retrieved": old["retrieved"], "checked": old["page_checked"], "why": ""}
    else:
        found = verify(fields["url"], fields["words"], fetch=fetch, strict=ptype != "reported")
    changed = [n for n, a, b in (("link", fields["url"], old["url"]), ("words", fields["words"], old["text"]),
                                 ("section", fields["section"], old["section"]), ("page date", fields["page_date"], old["page_date"]),
                                 ("outlet", fields["outlet"], old["outlet"]), ("whose words", fields["whose_words"], old["whose_words"]))
               if a != b]
    with db.session(write=True) as conn:
        row = supersede(conn, old, fields, found, actor)
        db.audit(conn, actor, "priority edited", None, "%s: %s replaced by %s; changed: %s; the earlier wording is kept" % (
            old["donor"], old["key"], row["key"], ", ".join(changed)))
    return row
