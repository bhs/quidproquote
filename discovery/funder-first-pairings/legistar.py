"""The network side: the city's Legistar calendar, the caption transcripts and the meeting minutes beyond the
meetings sampled so far.

    from legistar import discover, fetch_transcript, fetch_minutes

Every request is made with a plain User-Agent, at most about two a second, and retried three times. A request
that still fails raises FetchError: nothing here turns a failed fetch into an empty answer. The caller records
what could not be read.

The calendar is read the way the page itself is used: the year list is a form field, so the page is requested,
its hidden fields are sent back with the year chosen, and the rows of the calendar table are read for each
meeting's body, date, minutes link and transcript link. When a row carries no transcript link, the meeting's
detail page is read for one.
"""

import html
import io
import os
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://sfgov.legistar.com/"
CALENDAR = BASE + "Calendar.aspx"
TRANSCRIPT = BASE + "Transcript.aspx?ID1=%d"
UA = "Mozilla/5.0 (compatible; funder-first-pairings research script)"
PAUSE_S = 0.5
YEARS_FIELD = "ctl00$ContentPlaceHolder1$lstYears"
BODIES_FIELD = "ctl00$ContentPlaceHolder1$lstBodies"

# The Board and the six standing committees whose members are the officials of the funding map.
BODIES = ("Board of Supervisors", "Budget and Appropriations Committee", "Budget and Finance Committee",
          "Government Audit and Oversight Committee", "Land Use and Transportation Committee",
          "Public Safety and Neighborhood Services Committee", "Rules Committee")

MONTHS = {m: i + 1 for i, m in enumerate("JANUARY FEBRUARY MARCH APRIL MAY JUNE JULY AUGUST SEPTEMBER OCTOBER "
                                          "NOVEMBER DECEMBER".split())}


class FetchError(Exception):
    """A page could not be fetched or did not hold what it should."""


def cache_dir():
    d = os.environ.get("FF_CACHE_DIR") or os.path.join(tempfile.gettempdir(), "ff-cache")
    os.makedirs(d, exist_ok=True)
    return d


def get(url, data=None, timeout=60, retries=3):
    """The bytes of a URL (a POST when data is a dict). Raises FetchError after the retries."""
    body = urllib.parse.urlencode(data).encode("utf-8") if data is not None else None
    last = None
    for attempt in range(retries):
        try:
            time.sleep(PAUSE_S)
            req = urllib.request.Request(url, data=body, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except (urllib.error.URLError, OSError) as exc:
            last = "%s: %s" % (type(exc).__name__, exc)
            time.sleep(2 * (attempt + 1))
    raise FetchError("%s (%s)" % (last, url[:200]))


def get_text(url, data=None):
    return get(url, data).decode("utf-8", errors="replace")


# --------------------------------------------------------------------------- the calendar

def hidden_fields(page):
    out = {}
    for m in re.finditer(r'<input[^>]+type="hidden"[^>]*>', page, flags=re.I):
        tag = m.group(0)
        name = re.search(r'name="([^"]+)"', tag)
        value = re.search(r'value="([^"]*)"', tag)
        if name:
            out[name.group(1)] = html.unescape(value.group(1)) if value else ""
    return out


def clean(text):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", text or "")).split())


def iso_date(text):
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", text or "")
    return "%s-%02d-%02d" % (m.group(3), int(m.group(1)), int(m.group(2))) if m else ""


def parse_calendar(page):
    """[{body, date, minutes_url, transcript_id, detail_url}] for the rows of a calendar page."""
    out = []
    for tr in re.findall(r"<tr\b.*?</tr>", page, flags=re.S | re.I):
        cells = re.findall(r"<td\b.*?</td>", tr, flags=re.S | re.I)
        if len(cells) < 4:
            continue
        text = [clean(c) for c in cells]
        date = next((iso_date(t) for t in text if iso_date(t)), "")
        if not date:
            continue
        links = [html.unescape(h) for h in re.findall(r"""href=["']([^"']+)["']""", tr, flags=re.I)]
        minutes = next((l for l in links if re.search(r"View\.ashx\?M=M\b", l)), "")
        detail = next((l for l in links if "MeetingDetail.aspx" in l), "")
        tid = re.search(r"Transcript\.aspx\?ID1=(\d+)", tr)
        out.append({"body": text[0], "date": date,
                    "minutes_url": urllib.parse.urljoin(BASE, minutes) if minutes else "",
                    "detail_url": urllib.parse.urljoin(BASE, detail) if detail else "",
                    "transcript_id": int(tid.group(1)) if tid else None})
    return out


def calendar_year(year):
    """The calendar rows of one year. Raises FetchError when the page or the form does not answer."""
    page = get_text(CALENDAR)
    fields = hidden_fields(page)
    if "__VIEWSTATE" not in fields:
        raise FetchError("the calendar page carries no form state to send back")
    fields.update({
        "__EVENTTARGET": YEARS_FIELD, "__EVENTARGUMENT": "", YEARS_FIELD: str(year), BODIES_FIELD: "All",
        "ctl00_ContentPlaceHolder1_lstYears_ClientState": '{"logEntries":[],"value":"%d","text":"%d","enabled":true,"checkedIndices":[],"checkedItemsTextOverflows":false}' % (year, year),
    })
    rows = parse_calendar(get_text(CALENDAR, fields))
    if not rows:
        raise FetchError("the calendar for %d held no meeting rows" % year)
    return rows


def transcript_from_detail(detail_url):
    m = re.search(r"Transcript\.aspx\?ID1=(\d+)", get_text(detail_url))
    return int(m.group(1)) if m else None


# --------------------------------------------------------------------------- transcripts and minutes

def transcript_rows(raw):
    rows = re.findall(r"(\d\d:\d\d:\d\d)\s*</[^>]+>\s*(?:<[^>]+>\s*)*([^<]+)", raw)
    return [(s, " ".join(html.unescape(t).split())) for s, t in rows]


def fetch_transcript(tid):
    """[(stamp, text)] of a caption transcript, cached on disk. Raises FetchError when it holds no captions."""
    path = os.path.join(cache_dir(), "transcript_%d.tsv" % tid)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return [tuple(line.rstrip("\n").split("\t", 1)) for line in f if "\t" in line]
    rows = transcript_rows(get_text(TRANSCRIPT % tid))
    if len(rows) < 50:
        raise FetchError("transcript %d holds %d caption rows" % (tid, len(rows)))
    with open(path, "w", encoding="utf-8") as f:
        for s, t in rows:
            f.write("%s\t%s\n" % (s, t))
    return rows


def pdf_text(raw):
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # a missing dependency stops the run; it is not a reason to skip the check
        raise FetchError("pypdf is not installed: %s" % exc)
    reader = PdfReader(io.BytesIO(raw))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def fetch_minutes(key, url):
    """The text of a minutes PDF, cached on disk under `key`. Raises FetchError when it is not a readable PDF."""
    path = os.path.join(cache_dir(), "minutes_%s.txt" % key)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    raw = get(url, timeout=120)
    if not raw.startswith(b"%PDF"):
        raise FetchError("minutes at %s are not a PDF" % url[:160])
    text = pdf_text(raw)
    if len(text) < 500:
        raise FetchError("minutes at %s gave %d characters of text" % (url[:160], len(text)))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return text


# --------------------------------------------------------------------------- choosing the meetings

def body_matches(name):
    return next((b for b in BODIES if b.lower() == name.strip().lower()), None)


GRANICUS_RSS = "https://sanfrancisco.granicus.com/ViewPublisherRSS.php?view_id=%d"
RSS_VIEWS = {10: "Board of Supervisors", 177: "Land Use and Transportation Committee", 13: "Rules Committee",
             11: "Government Audit and Oversight Committee"}
RSS_DATE = re.compile(r"dated\s+\w+,\s+(\d{1,2})\s+(\w+)\s+(\d{4})", re.I)


def parse_rss(xml, body):
    """[{body, date, transcript_id, minutes_url}] from a Granicus publisher feed: each item's clip id is the
    transcript id of the Legistar page for the same recording (as for meeting 52849), and its title gives the
    date. No minutes link comes with it."""
    out = []
    for item in re.findall(r"<item>.*?</item>", xml, flags=re.S | re.I):
        cid = re.search(r"clip_id=(\d+)", item)
        d = RSS_DATE.search(html.unescape(item))
        if not (cid and d and d.group(2).upper() in MONTHS):
            continue
        out.append({"body": body, "date": "%s-%02d-%02d" % (d.group(3), MONTHS[d.group(2).upper()], int(d.group(1))),
                    "transcript_id": int(cid.group(1)), "minutes_url": "", "detail_url": ""})
    return out


def rss_rows(year):
    rows = []
    for view, body in RSS_VIEWS.items():
        rows.extend(r for r in parse_rss(get_text(GRANICUS_RSS % view), body) if r["date"].startswith(str(year)))
    if not rows:
        raise FetchError("the Granicus feeds held no meetings of %d" % year)
    return rows


def discover(known, year, max_new):
    """(sampled, new, notes, rows_seen, rows_with_transcript, route): the meetings of `year` in the Board and its
    standing committees that have a transcript, newest first. `sampled` are those whose transcript id is in
    `known` (so their minutes can be read too); `new` are up to max_new others. Each row has body, date,
    transcript_id, minutes_url. The Legistar calendar is read first; when it cannot be, the Granicus feeds are
    (no minutes links then). notes says what was not found."""
    notes = []
    route = "Legistar calendar"
    try:
        rows = [dict(r, body=body_matches(r["body"])) for r in calendar_year(year) if body_matches(r["body"])]
        if not rows:
            raise FetchError("no row of the calendar names the Board or one of its standing committees")
    except FetchError as exc:
        notes.append("Legistar calendar not read (%s); the Granicus feeds were used instead" % exc)
        route = "Granicus feeds"
        rows = rss_rows(year)
    for r in rows:
        if r["transcript_id"] is None and r["detail_url"] and r["minutes_url"]:
            try:
                r["transcript_id"] = transcript_from_detail(r["detail_url"])
            except FetchError as exc:
                notes.append("detail page of %s %s unread: %s" % (r["body"], r["date"], exc))
    with_t = [r for r in rows if r["transcript_id"]]
    without = len(rows) - len(with_t)
    if without:
        notes.append("%d meeting rows of the Board and its standing committees carry no transcript link" % without)
    sampled = [r for r in with_t if r["transcript_id"] in known]
    new = sorted((r for r in with_t if r["transcript_id"] not in known), key=lambda r: r["date"], reverse=True)
    return sampled, new[:max_new], notes, len(rows), len(with_t), route


def identify(rows):
    """(date, body) read from the opening captions of a transcript, for transcripts found without a calendar
    row: the date as the presiding officer says it and the committee's name."""
    head = " ".join(t for _, t in rows[:60])
    d = re.search(r"(%s)\s+(\d{1,2})(?:ST|ND|RD|TH)?,?\s+(\d{4})" % "|".join(MONTHS), head)
    date = "%s-%02d-%02d" % (d.group(3), MONTHS[d.group(1)], int(d.group(2))) if d else ""
    body = None
    for b in BODIES:
        if b.upper() in head:
            body = b
            break
    if not body and "BOARD OF SUPERVISORS" in head:
        body = "Board of Supervisors"
    return date, body
