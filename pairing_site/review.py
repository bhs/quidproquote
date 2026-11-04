"""What a person does at the site: enter a donor and a priority, approve a candidate (with the quote's edges, the
doubt level and the statements to show), edit the doubt, or reject.

Every check here refuses; none repairs. A priority is not saved without the donor's exact words, the source type,
its URL and the date it was retrieved. Nothing is published until a candidate is approved, and an approved card
always shows the caption words exactly as the city's transcript has them.
"""

import datetime
import json
import re
from urllib.parse import urlparse

from . import candidates
from . import db

DOUBT_LEVELS = ("low", "medium", "high")
MAX_QUOTE_CHARS = 3000
CAUSAL = ("because of the money", "in return", "bought", "paid for", "caused", "quid pro quo",
          "in exchange for", "payback", "pay-to-play", "pay to play")
SOURCE_TYPE_SUGGESTIONS = (
    "voter guide on the organisation's own site",
    "endorsement list on the organisation's own site",
    "article on the organisation's own site",
    "policy page on the organisation's own site",
    "news article that quotes the organisation",
)


class FormError(ValueError):
    """The form was refused; `errors` says why, field by field."""

    def __init__(self, errors):
        super().__init__("; ".join(errors))
        self.errors = errors


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def lines_of(text):
    """The non-empty lines of a textarea, or the comma-separated items of a one-line field."""
    out = []
    for part in re.split(r"[\n\r]+", text or ""):
        part = part.strip()
        if part:
            out.append(part)
    return out


def iso_date(text):
    try:
        return datetime.date.fromisoformat((text or "").strip()).isoformat()
    except ValueError:
        return None


def causal_words(*texts):
    low = " ".join(texts).lower()
    return [w for w in CAUSAL if w in low]


# --------------------------------------------------------------------------- donors

def save_donor(conn, form):
    """Add a donor: the name it is known by, and the words that take a giver's name as filed to it."""
    errors = []
    name = (form.get("name") or "").strip()
    kind = (form.get("kind") or "").strip()
    patterns = [[w.upper() for w in ln.split()] for ln in lines_of(form.get("patterns"))]
    exclude = [w.upper() for w in lines_of(form.get("exclude"))]
    ids = [x.strip() for x in re.split(r"[,\s]+", form.get("committee_ids") or "") if x.strip()]
    if not name:
        errors.append("The donor's name is required.")
    if not kind:
        errors.append("What kind of donor this is (union, company, association...) is required.")
    if not patterns:
        errors.append("At least one name as filed is required: words that must all be in a giver's name.")
    key = slugify(name)
    if name and conn.execute("SELECT 1 FROM donors WHERE key=?", (key,)).fetchone():
        errors.append("A donor with this name already exists.")
    if errors:
        raise FormError(errors)
    cur = conn.execute("INSERT INTO donors (key, name, kind, patterns, exclude, committee_ids, link_note) "
                       "VALUES (?,?,?,?,?,?,?)",
                       (key, name, kind, json.dumps(patterns), json.dumps(exclude), json.dumps(ids),
                        (form.get("link_note") or "").strip()))
    return cur.lastrowid


# --------------------------------------------------------------------------- priorities

def save_priority(conn, form, today=None, scan=True):
    """Save a donor's stated priority. Refused without the exact words, a source type, a URL and the date the
    words were retrieved; refused too when nothing is given to look for in a transcript. Looks for candidates
    in the stored meetings once saved (unless `scan` is false)."""
    today = today or datetime.date.today().isoformat()
    errors = []
    donor = conn.execute("SELECT * FROM donors WHERE id=?", (form.get("donor_id") or 0,)).fetchone()
    words = " ".join((form.get("words") or "").split())
    source_type = (form.get("source_type") or "").strip()
    url = (form.get("url") or "").strip()
    retrieved = iso_date(form.get("retrieved"))
    page_date = (form.get("page_date") or "").strip()
    if donor is None:
        errors.append("Choose the donor.")
    if len(words) < 10:
        errors.append("The donor's exact words are required (copied from the page, not paraphrased).")
    if not source_type:
        errors.append("The source type is required.")
    parsed = urlparse(url)
    if not (parsed.scheme in ("http", "https") and parsed.netloc):
        errors.append("The source URL is required, as a full http or https address.")
    if retrieved is None:
        errors.append("The retrieval date is required, as YYYY-MM-DD.")
    elif retrieved > today:
        errors.append("The retrieval date cannot be in the future.")
    if page_date and iso_date(page_date) is None:
        errors.append("The page date, when given, must be YYYY-MM-DD.")
    section = " ".join((form.get("section") or "").split())
    measures = list(dict.fromkeys(
        [m.strip() for m in re.split(r"[,\n]+", form.get("measures") or "") if m.strip()]
        + candidates.derive_measures(section, words)))
    phrases = lines_of(form.get("phrases"))
    if not measures and not phrases:
        errors.append("Give at least one measure (Prop H) or distinctive phrase to look for in a transcript.")
    if errors:
        raise FormError(errors)
    cur = conn.execute(
        "INSERT INTO priorities (donor_id, label, section, words, source_type, url, page_date, retrieved, measures, "
        "phrases, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (donor["id"], (form.get("label") or "").strip(), section, words, source_type, url, page_date, retrieved,
         json.dumps(measures), json.dumps(phrases), db.now()))
    if scan:
        candidates.scan(conn, donor_ids={donor["id"]})
    return cur.lastrowid


# --------------------------------------------------------------------------- candidates

def cut_quote(doc, cand, begin_at="", end_at=""):
    """The quote an approval publishes: the words of the credited turn from `begin_at` to `end_at` (words the
    reviewer names, looked for in the turn and never altered), or the flagged remark itself. Returns {text,
    first_stamp, last_stamp}. Raises ValueError when what was asked for is not in the turn, the cut does not
    overlap the flagged remark, or it runs past 3,000 characters."""
    rs, re_ = cand["region_start"], cand["region_end"]
    region = doc.text[rs:re_]
    ps, pe = cand["start_off"] - rs, cand["end_off"] - rs
    begin_at, end_at = (begin_at or "").strip(), (end_at or "").strip()
    b = ps
    if begin_at:
        spots = [m.start() for m in re.finditer(re.escape(begin_at), region, flags=re.I)]
        if not spots:
            raise ValueError("The words the quote begins at are not in this speaker's turn: %r" % begin_at)
        b = min(spots, key=lambda s: abs(s - ps))
    e = pe
    if end_at:
        m = re.compile(re.escape(end_at), re.I).search(region, b)
        if not m:
            raise ValueError("The words the quote ends at are not in this speaker's turn after where it begins: %r" % end_at)
        e = m.end()
    while b < e and region[b] in "> .,":
        b += 1
    if e <= b:
        raise ValueError("The quote is empty: it must end after it begins.")
    if b >= pe or e <= ps:
        raise ValueError("The quote must include some of the flagged remark.")
    if e - b > MAX_QUOTE_CHARS:
        raise ValueError("The quote is longer than %d characters; choose a shorter stretch." % MAX_QUOTE_CHARS)
    text = region[b:e].strip()
    if text not in doc.text:
        raise ValueError("The quote is not word for word in the transcript.")
    return {"text": text, "first_stamp": doc.stamp(rs + b), "last_stamp": doc.stamp(rs + e - 1)}


def approve(conn, cid, form):
    """Approve a pending candidate and publish it as a card. form: begin_at, end_at, doubt, doubt_note,
    in_common, differs, statements (priority ids of the donor to show; the ones the remark names by default)."""
    cand = conn.execute("SELECT * FROM candidates WHERE id=?", (cid,)).fetchone()
    if cand is None:
        raise LookupError("no such candidate")
    errors = []
    if cand["status"] != "pending":
        errors.append("This candidate has already been %s." % cand["status"])
    doubt = (form.get("doubt") or cand["doubt"]).strip()
    if doubt not in DOUBT_LEVELS:
        errors.append("The doubt level must be low, medium or high.")
    wanted = form.get("statements")
    wanted = [int(x) for x in wanted] if wanted is not None else db.jl(cand["priority_ids"])
    own = {r["id"] for r in conn.execute("SELECT id FROM priorities WHERE donor_id=?", (cand["donor_id"],))}
    if not wanted or any(x not in own for x in wanted):
        errors.append("Choose at least one of the donor's stated priorities to show beside the quote.")
    notes = [(form.get(k) or "").strip() for k in ("doubt_note", "in_common", "differs")]
    bad = causal_words(*notes)
    if bad:
        errors.append("The notes must not suggest the money caused the words (found: %s)." % ", ".join(bad))
    quote = None
    if not errors:
        try:
            quote = cut_quote(candidates.load_doc(conn, cand["meeting_id"]), cand, form.get("begin_at"), form.get("end_at"))
        except ValueError as exc:
            errors.append(str(exc))
    if errors:
        raise FormError(errors)
    official = conn.execute("SELECT surname FROM officials WHERE id=?", (cand["official_id"],)).fetchone()
    donor = conn.execute("SELECT key FROM donors WHERE id=?", (cand["donor_id"],)).fetchone()
    meeting = conn.execute("SELECT date FROM meetings WHERE id=?", (cand["meeting_id"],)).fetchone()
    base = slugify("%s %s %s %s" % (official["surname"], donor["key"], meeting["date"], quote["first_stamp"].replace(":", "")))
    slug, n = base, 1
    while conn.execute("SELECT 1 FROM candidates WHERE slug=?", (slug,)).fetchone():
        n += 1
        slug = "%s-%d" % (base, n)
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(
            "UPDATE candidates SET status='approved', reviewed_at=?, slug=?, quote_text=?, quote_first_stamp=?, "
            "quote_last_stamp=?, doubt=?, doubt_note=?, in_common=?, differs=? WHERE id=?",
            (db.now(), slug, quote["text"], quote["first_stamp"], quote["last_stamp"], doubt, notes[0], notes[1],
             notes[2], cid))
        conn.executemany("INSERT OR IGNORE INTO card_statements (candidate_id, priority_id) VALUES (?, ?)",
                         [(cid, p) for p in wanted])
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return slug


def reject(conn, cid, note=""):
    cand = conn.execute("SELECT status FROM candidates WHERE id=?", (cid,)).fetchone()
    if cand is None:
        raise LookupError("no such candidate")
    if cand["status"] != "pending":
        raise FormError(["This candidate has already been %s." % cand["status"]])
    conn.execute("UPDATE candidates SET status='rejected', reviewed_at=?, reject_note=? WHERE id=?",
                 (db.now(), (note or "").strip(), cid))


def set_doubt(conn, cid, doubt, note=""):
    """Edit the doubt level (and the note on why) of a candidate, pending or approved."""
    if doubt not in DOUBT_LEVELS:
        raise FormError(["The doubt level must be low, medium or high."])
    bad = causal_words(note or "")
    if bad:
        raise FormError(["The note must not suggest the money caused the words (found: %s)." % ", ".join(bad)])
    cur = conn.execute("UPDATE candidates SET doubt=?, doubt_note=? WHERE id=? AND status != 'rejected'",
                       (doubt, (note or "").strip(), cid))
    if cur.rowcount == 0:
        raise LookupError("no such candidate, or it was rejected")
