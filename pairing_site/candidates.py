"""The candidates: remarks of a funded official that name a measure or a distinctive phrase from a priority a
donor's page states.

A candidate appears only when all of these hold: the donor has an entered priority; the donor gave Schedule A
money through a committee tied to the official; the official's turn, as the chair's spoken cue hands it over
(speakers.py), holds a measure name or a phrase of that priority. The finder proposes (the exact caption rows, the
words that matched, the speaker credit with a doubt level); a person decides. Nothing here says why anyone said or
gave anything.

Adapted from ff_lib.candidate_passages (discovery/funder-first-pairings).
"""

import json
import re

from . import db
from . import money
from . import speakers

HIT_GAP_ROWS = 3
PASSAGE_MAX_ROWS = 16
MEASURE_RX = re.compile(r"\b(?:Prop(?:osition)?\.?|Measure)\s+([A-Z])\b")


def derive_measures(*texts):
    """The measures a priority's heading and words name ('Prop H', 'Proposition I'), as search terms."""
    letters = []
    for t in texts:
        for m in MEASURE_RX.finditer(t or ""):
            if m.group(1) not in letters:
                letters.append(m.group(1))
    return ["Prop %s" % x for x in letters]


def measure_variants(measure):
    """'Prop H' also reads 'Proposition H' and 'Measure H' in a transcript."""
    letter = measure.strip().split()[-1]
    return ["Prop %s" % letter, "Proposition %s" % letter, "Measure %s" % letter]


def priority_terms(p):
    """The terms of a priority row: its measures (each in its three spellings) and its phrases."""
    terms = []
    for m in db.jl(p["measures"]):
        terms.extend(measure_variants(m))
    terms.extend(db.jl(p["phrases"]))
    return [t for t in dict.fromkeys(t.strip() for t in terms) if t]


def term_rx(terms):
    """Whole-word, case-insensitive pattern for a list of terms; a term ending in '*' matches any word that
    starts with it. None when there are no terms."""
    if not terms:
        return None
    parts = []
    for t in sorted(terms, key=len, reverse=True):
        parts.append(re.escape(t[:-1]) + r"[A-Z]*" if t.endswith("*") else re.escape(t))
    return re.compile(r"(?<![A-Za-z0-9])(?:%s)(?![A-Za-z0-9])" % "|".join(parts), re.I)


def load_doc(conn, meeting_id):
    rows = [(r["stamp"], r["text"]) for r in conn.execute(
        "SELECT stamp, text FROM lines WHERE meeting_id=? ORDER BY idx", (meeting_id,))]
    return speakers.Doc(rows)


def find_passages(doc, region, rx):
    """Passages of a credited turn that hit the terms: [{start, end, first_idx, last_idx, text, hits}]. Rows
    holding a hit are grouped when at most three rows apart; a passage runs from the row before the first hit to
    the row after the last, never past the turn or 16 rows."""
    r0, r1 = doc.row_index(region["start"]), doc.row_index(max(region["end"] - 1, region["start"]))
    hits = []
    for i in range(r0, r1 + 1):
        lo = max(doc.starts[i], region["start"])
        hi = min(doc.starts[i] + len(doc.rows[i][1]), region["end"])
        found = sorted({m.group(0).upper() for m in rx.finditer(doc.text[lo:hi])})
        if found:
            hits.append((i, found))
    groups, cur = [], []
    for h in hits:
        if cur and h[0] - cur[-1][0] > HIT_GAP_ROWS:
            groups.append(cur)
            cur = []
        cur.append(h)
    if cur:
        groups.append(cur)
    out = []
    for g in groups:
        i0 = max(g[0][0] - 1, r0)
        i1 = min(g[-1][0] + 1, r1, i0 + PASSAGE_MAX_ROWS - 1)
        start = max(doc.starts[i0], region["start"])
        end = min(doc.starts[i1] + len(doc.rows[i1][1]), region["end"])
        text = doc.text[start:end]
        lead = len(text) - len(text.lstrip(".>, "))
        start += lead
        out.append({"start": start, "end": end, "text": doc.text[start:end].strip(), "first_idx": doc.row_index(start),
                    "last_idx": doc.row_index(max(end - 1, start)),
                    "hits": sorted({x for h in g for x in h[1]})})
    return out


def cue_rows(doc, region):
    """The caption rows that hold the cue handing the turn over (for the Mayor, the clerk's introduction and
    the thanks that close the turn too): [(stamp, text)]."""
    idx = set(range(doc.row_index(region["cue_pos"]), doc.row_index(max(region["start"] - 1, region["cue_pos"])) + 1))
    if region["kind"] == "mayor-opening":
        window = doc.text[max(0, region["cue_pos"] - 700):region["cue_pos"]]
        k = window.rfind("MAYOR")
        if k >= 0:
            idx.add(doc.row_index(region["cue_pos"] - len(window) + k))
        if region["bounded"]:
            idx.add(doc.row_index(region["end"]))
    return [list(doc.rows[i]) for i in sorted(idx)]


def scan(conn, meeting_ids=None, donor_ids=None):
    """Look for new candidates in the stored meetings (all, or `meeting_ids`) for the donors with entered
    priorities (all, or `donor_ids`). Returns the number of candidates added; candidates already there, and what
    a person decided about them, are left as they are."""
    roster = speakers.Roster(db.roster_for_cues(conn))
    ids = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM officials")}
    plans = []
    for d in conn.execute("SELECT * FROM donors ORDER BY id"):
        if donor_ids is not None and d["id"] not in donor_ids:
            continue
        pris = [(p, term_rx(priority_terms(p))) for p in conn.execute(
            "SELECT * FROM priorities WHERE donor_id=? ORDER BY id", (d["id"],))]
        pris = [(p, rx) for p, rx in pris if rx]
        funded = money.funded_official_ids(conn, d["id"]) if pris else set()
        if pris and funded:
            plans.append((d, pris, funded, term_rx(sorted({t for p, _ in pris for t in priority_terms(p)}))))
    if not plans:
        return 0
    if meeting_ids is None:
        meeting_ids = [r["id"] for r in conn.execute("SELECT id FROM meetings ORDER BY date, id")]
    added = 0
    conn.execute("BEGIN IMMEDIATE")
    try:
        added = _scan_meetings(conn, meeting_ids, roster, ids, plans)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return added


def _scan_meetings(conn, meeting_ids, roster, ids, plans):
    added = 0
    for mid in meeting_ids:
        doc = load_doc(conn, mid)
        regions = speakers.find_regions(doc, roster)
        for d, pris, funded, union_rx in plans:
            for reg in regions:
                if ids.get(reg["official"]) not in funded:
                    continue
                for p in find_passages(doc, reg, union_rx):
                    doubt, why = speakers.credit_tier(doc, reg, p["start"])
                    named = [pr["id"] for pr, rx in pris if rx.search(p["text"])]
                    cur = conn.execute(
                        "INSERT OR IGNORE INTO candidates (donor_id, official_id, meeting_id, priority_ids, hits, first_idx, "
                        "last_idx, start_off, end_off, region_start, region_end, text, first_stamp, last_stamp, doubt, "
                        "doubt_why, cue_text, cue_stamp, cue_lines, created_at) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (d["id"], ids[reg["official"]], mid, json.dumps(named), json.dumps(p["hits"]), p["first_idx"],
                         p["last_idx"], p["start"], p["end"], reg["start"], reg["end"], p["text"],
                         doc.rows[p["first_idx"]][0], doc.rows[p["last_idx"]][0], doubt, json.dumps(why), reg["cue"],
                         reg["cue_stamp"], json.dumps(cue_rows(doc, reg)), db.now()))
                    added += cur.rowcount
    return added
