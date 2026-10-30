"""Shared helpers for the official funding map: DataSF queries, committee roles, donor families and the
text of the city's caption transcripts. Standard library only.

Nothing here decides anything about an official: it names a committee's relation to an official (the data's
own `filer_type` plus the words of the committee's name), keeps each kind of money in its own bucket, and never
sums across forms.
"""

import datetime
import html
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

TRANSACTIONS = "pitq-e56w"
FILERS = "4c8t-ngau"
DATASF = "https://data.sf.gov/resource/%s.json"
DATASET_PAGE = "https://data.sf.gov/d/pitq-e56w"
UA = "Mozilla/5.0 (compatible; official-funding-map research script)"

# Buckets of money. They are never added together.
BUCKET_GIFT = "gift to a committee tied to the official"
BUCKET_OUTSIDE = "outside spending naming the official"

ENTITY_NAMES = {
    "IND": "individual",
    "OTH": "other (business, union, trust or other organisation, filed under its own name)",
    "COM": "committee (carries the giver's FPPC id)",
    "SCC": "small contributor committee",
    "PTY": "political party",
}


class QueryError(Exception):
    """A DataSF query failed. It is reported, never replaced by an empty answer."""


def lit(value):
    """A SoQL string literal."""
    return "'" + str(value).replace("'", "''") + "'"


def query(dataset, params, timeout=120, retries=3):
    """Rows of one SoQL query. Raises QueryError after the retries; an empty list means no rows."""
    url = DATASF % dataset + "?" + urllib.parse.urlencode(params)
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                rows = json.loads(resp.read().decode("utf-8"))
            if not isinstance(rows, list):
                raise QueryError("unexpected reply: %s" % str(rows)[:200])
            return rows
        except (urllib.error.URLError, OSError, ValueError) as exc:
            last = "%s: %s" % (type(exc).__name__, exc)
    raise QueryError("%s (%s)" % (last, url[:300]))


def query_all(dataset, params, page=5000):
    """Every row of a query, paged. The query must carry a stable $order."""
    out, offset = [], 0
    while True:
        p = dict(params)
        p["$limit"] = str(page)
        p["$offset"] = str(offset)
        rows = query(dataset, p)
        out.extend(rows)
        if len(rows) < page:
            return out
        offset += page


def in_list(values):
    return ",".join(lit(v) for v in values)


# --------------------------------------------------------------------------- committees and officials

def office_of(filer_name):
    """The office a candidate committee is for, read from its name (the dataset has no office field)."""
    n = (filer_name or "").upper()
    if "DEMOCRATIC" in n or "DCCC" in n or "CENTRAL COMMITTEE" in n:
        return "Democratic County Central Committee"
    if "COLLEGE" in n:
        return "Community College Board"
    if "SCHOOL BOARD" in n or "BOARD OF EDUCATION" in n:
        return "School Board"
    if "MAYOR" in n:
        return "Mayor"
    if "SUPERVISOR" in n or re.search(r"\bD\d+\b", n) or "MANDELMAN FOR SUPERVISOR" in n:
        return "Supervisor"
    return "unstated in the name"


def relation_of(committee):
    """(key, plain words) for how a committee is tied to the official, from the data's `filer_type` and the
    words of its name. The data has no field for control; a name carrying the official's own is the only tie
    for a ballot-measure committee, so that tie is labelled as a name tie."""
    t = committee["filer_type"]
    n = committee["filer_name"].upper()
    if t == "Candidate or Officeholder":
        office = office_of(committee["filer_name"])
        if office in ("Supervisor", "Mayor"):
            return "own", "own committee for %s" % office
        return "own-other", "own committee for another office (%s)" % office
    if t == "470 [Officeholder]":
        return "own", "officeholder account (Form 470)"
    if t == "Person":
        return "own-other", "the official's own filer record for another office"
    if t == "Primarily Formed Candidate":
        if "OPPOS" in n:
            return "opposing", "primarily formed committee opposing the official (not the official's own; control not stated in the data)"
        return "supporting", "primarily formed committee supporting the official (not the official's own candidate committee; control not stated in the data)"
    if t == "Primarily Formed Measure":
        return "measure", "ballot-measure committee carrying the official's name"
    return "other", t


def own_and_measure(relation):
    return relation in ("own", "own-other", "measure")


def load_committees(path):
    """The seed of officials and committees (the survey's roster and committee match)."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------- donor names and families

CORP_WORDS = {"INC", "LLC", "LLP", "CORP", "CORPORATION", "COMPANY", "CO", "LTD", "THE"}
COMMITTEE_WORDS = {"PAC", "P", "A", "C", "COMMITTEE", "FUND", "ISSUES", "POLITICAL", "ACTION", "ACCOUNT"}


def norm_name(name):
    """Upper-case, punctuation and parenthetical notes removed, whitespace collapsed."""
    n = (name or "").upper()
    n = re.sub(r"\(.*?\)", " ", n)
    n = re.sub(r"[^A-Z0-9 ]", " ", n)
    return " ".join(n.split())


def sponsor_of(name):
    """The sponsor a committee name states ('X, sponsored by Y', 'Supported by Y'), or None."""
    m = re.search(r"\b(?:SPONSORED BY|SUPPORTED BY|SPONSORED|A COMMITTEE OF)\s+(.+)$", norm_name(name))
    return m.group(1) if m else None


def donor_name(row):
    first = (row.get("fn") or row.get("transaction_first_name") or "").strip()
    last = (row.get("ln") or row.get("transaction_last_name") or "").strip()
    return (first + " " + last).strip()


def name_has_words(words, name):
    n = norm_name(name)
    return all(w in n for w in words)


def family_of(families, name, committee_id=None):
    """(key, how) of the first family that takes the giver: by the FPPC id the row carries ('id'), else by one
    of the family's word lists wholly in the name ('name'); (None, None) when none does. Families are listed
    most specific first; the name as filed is kept on every row for a person to check."""
    for fam in families:
        if any(x in norm_name(name) for x in fam.get("exclude", [])):
            continue
        if committee_id and str(committee_id) in fam.get("committee_ids", []):
            return fam["key"], "id"
        for words in fam["patterns"]:
            if name_has_words(words, name):
                return fam["key"], "name"
    return None, None


def family_clause(column, fam, id_column=None):
    """A SoQL clause matching the family's patterns in a name column (upper-cased in the query) and, when
    an id column is named, the family's FPPC ids."""
    groups = []
    for words in fam["patterns"]:
        groups.append("(" + " AND ".join("upper(%s) like %s" % (column, lit("%" + w + "%")) for w in words) + ")")
    if id_column and fam.get("committee_ids"):
        groups.append("%s in (%s)" % (id_column, in_list(fam["committee_ids"])))
    return "(" + " OR ".join(groups) + ")"


def names_official(candidate_field, surname, given=None):
    """True when the candidate as filed is the official: the surname is a whole word of it and, when it holds
    other words, the given name is one of them ('Mike Chen' is not 'Chyanne Chen')."""
    tokens = re.findall(r"[A-Z']+", (candidate_field or "").upper())
    if surname.upper() not in tokens:
        return False
    return given is None or tokens == [surname.upper()] or given.upper() in tokens


def amount(row, field="calculated_amount"):
    try:
        return float(row.get(field) or 0)
    except ValueError:
        return 0.0


def dollars(x):
    x = float(x)
    return ("-$" if x < 0 else "$") + "{:,.0f}".format(abs(x))


def day(stamp):
    return (stamp or "")[:10]


# --------------------------------------------------------------------------- transcripts

def load_rows(data_dir, meeting_id):
    """[(stamp, text)] for one caption transcript, as published."""
    rows = []
    with open(os.path.join(data_dir, "transcripts", "%d.tsv" % meeting_id), encoding="utf-8") as f:
        for line in f:
            stamp, _, text = line.rstrip("\n").partition("\t")
            rows.append((stamp, " ".join(text.split())))
    return rows


def extract_quote(rows, start, end, begin_at=None, end_at=None):
    """The words of the caption rows from stamp `start` to `end`, exactly as published.

    begin_at / end_at cut the first and last row at a phrase that must occur in them. A leading '>>'
    (the captions' speaker-change mark) is dropped. Returns text and the stamps of the rows holding its first
    and last word. Raises ValueError when anything asked for is not there."""
    sel = [(s, t) for s, t in rows if start <= s <= end]
    if not sel:
        raise ValueError("no caption rows between %s and %s" % (start, end))
    joined, offsets = "", []
    for s, t in sel:
        offsets.append((len(joined), s))
        joined += t + " "
    b, e = 0, len(joined.rstrip())
    if begin_at:
        b = joined.find(begin_at)
        if b < 0:
            raise ValueError("begin_at %r not found" % begin_at)
    if end_at:
        i = joined.find(end_at, b)
        if i < 0:
            raise ValueError("end_at %r not found" % end_at)
        e = i + len(end_at)
    while b < e and joined[b] in "> ":
        b += 1
    text = joined[b:e].strip()
    first = [s for off, s in offsets if off <= b][-1]
    last = [s for off, s in offsets if off <= max(e - 1, 0)][-1]
    return {"text": text, "first_stamp": first, "last_stamp": last}


def is_verbatim(rows, text):
    whole = " ".join(t for _, t in rows)
    return text in whole


def cue_rows(rows, stamps):
    out = []
    for stamp in stamps:
        hits = [(s, t) for s, t in rows if s == stamp]
        if not hits:
            raise ValueError("stamp %s not in the transcript" % stamp)
        out.extend(hits)
    return out


# --------------------------------------------------------------------------- donors' own pages

def fetch_page(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def page_text(raw):
    """The visible text of an HTML page, whitespace collapsed and typographic quotes straightened."""
    raw = re.sub(r"<(script|style|noscript|svg)\b.*?</\1>", "", raw, flags=re.S | re.I)
    raw = re.sub(r"</(p|div|li|h[1-6]|tr|section|article)>|<br\s*/?>", "\n", raw, flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", "", raw))
    return squash(text)


def page_lines(raw):
    """The visible lines of an HTML page, each squashed (see squash)."""
    raw = re.sub(r"<(script|style|noscript|svg)\b.*?</\1>", "", raw, flags=re.S | re.I)
    raw = re.sub(r"</(p|div|li|h[1-6]|tr|section|article)>|<br\s*/?>", "\n", raw, flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", "", raw))
    return [ln for ln in (squash(x) for x in text.split("\n")) if ln]


def squash(text):
    text = (text or "").replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2013", "-").replace("\u2014", "-").replace("\xa0", " ")
    return " ".join(text.split())


def today():
    return datetime.date.today().isoformat()
