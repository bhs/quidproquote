"""Pairing cards: each approved pairing as one self-contained card (presentation only; no analysis is done here).

Adapted from discovery/official-funding-map/pairing_cards.py. The card keeps its three zones. Left: the money in
(one line per receiving committee, each with its own Schedule A total, never summed across committees), outside
spending kept apart, and the donor's stated priority as its own bubble. Centre: the official's name and role.
Right: the official's exact caption words. Beneath: a 'reading, not a finding' strip carrying the speaker-credit
doubt as a badge, and a sources row.

Highlighting marks only words literally shared by the quote and the donor's own words: the measure names and
phrases of the shown statements that occur in both. Nothing is rewritten. `build_card` reads the database each time
a card is shown; nothing about a card is stored beyond what a person approved. Standard library plus markupsafe.
"""

import json

from markupsafe import Markup, escape

from . import candidates
from . import db
from . import fmap_lib as fl
from . import money

NO_CAUSE = "No cause is claimed."
DOUBT_LEVELS = ("low", "medium", "high")
ROW_KINDS = {"A": "Schedule A", "only": "24-hour report, no Schedule A row yet (apart, not in the total)",
             "repeat": "24-hour report repeating a Schedule A row (listed, not counted)"}


def marked(text, terms):
    """`text` escaped, with each literal occurrence of a term wrapped in <mark>. The text itself is never
    altered: only the tags are added around it."""
    rx = candidates.term_rx(terms)
    if not rx:
        return escape(text)
    out, pos = [], 0
    for m in rx.finditer(text):
        out.append(escape(text[pos:m.start()]))
        out.append(Markup("<mark>%s</mark>") % m.group(0))
        pos = m.end()
    out.append(escape(text[pos:]))
    return Markup("").join(out)


def shared_terms(quote, donor_texts, terms):
    """The words of `terms` that occur literally in the quote and in the donor's own words, as the donor writes
    them (first occurrence), without repeats."""
    rx = candidates.term_rx(terms)
    out = []
    for m in (rx.finditer(quote) if rx else ()):
        one = candidates.term_rx([m.group(0)])
        for t in donor_texts:
            hit = one.search(t)
            if hit:
                if hit.group(0).lower() not in [x.lower() for x in out]:
                    out.append(hit.group(0))
                break
    return out


def committee_kind(c):
    """The kind of committee in the card's words: ballot-measure committee carrying the official's name,
    officeholder committee or own committee. A committee for another office says so."""
    rel, name = c["relation"], c["filer_name"]
    if rel == "measure":
        return "ballot-measure committee carrying the official's name"
    kind = "officeholder committee" if ("OFFICEHOLDER" in name.upper() or c["filer_type"] == "470 [Officeholder]") \
        else "own committee"
    if rel == "own-other":
        kind += ", for another office (%s)" % fl.office_of(name)
    return kind


def _ver(r):
    v = r.get("filing_version")
    try:
        return str(int(float(v)))
    except (TypeError, ValueError):
        return str(v or "")


def tie_note(per, fams, records):
    """How the givers in this pairing are recognised as the donor's: by the FPPC id they carry that the Filers
    dataset resolves, or by name only. Rows are grouped by giver name as filed."""
    seen = {}
    for c in per.values():
        for r in c["a"] + c["repeat"] + c["only"]:
            name, cid = fl.donor_name(r), r.get("committee_id") or ""
            seen[(name, cid)] = fl.family_of(fams, name, cid)[1]
    by_id = sorted({"%s (%s)" % (cid, records.get(cid, "not in Filers")) for (n, cid), h in seen.items() if h == "id"})
    by_name = sorted({n for (n, cid), h in seen.items() if h == "name"})
    ids_name = sorted({cid for (n, cid), h in seen.items() if h == "name" and cid})
    resolved = sorted({cid for cid in ids_name if cid in records})
    parts = []
    if by_id:
        parts.append("by Filers id: %s" % "; ".join(by_id))
    if by_name:
        s = "by name only (%d giver name%s as filed)" % (len(by_name), "" if len(by_name) == 1 else "s")
        if ids_name and not resolved:
            s += "; the FPPC ids on those rows do not resolve in the Filers dataset"
        elif resolved:
            s += "; FPPC id%s that resolve%s in the Filers dataset: %s" % (
                "" if len(resolved) == 1 else "s", "s" if len(resolved) == 1 else "",
                ", ".join("%s ('%s')" % (cid, records[cid]) for cid in resolved))
        elif not ids_name:
            s += "; the rows carry no FPPC id"
        parts.append(s)
    return "Tie to the donor recognised " + "; ".join(parts) + "."


def committee_line(c):
    cm = c["committee"]
    d = sorted(r["calculated_date"][:10] for r in c["a"])
    givers = sorted({fl.donor_name(r) for r in c["a"] + c["repeat"] + c["only"]})
    rows = []
    for kind, rs in (("A", c["a"]), ("only", c["only"]), ("repeat", c["repeat"])):
        for r in rs:
            rows.append({"kind": ROW_KINDS[kind], "date": r["calculated_date"][:10], "filing": r["filing_id_number"],
                         "version": _ver(r), "filing_date": r["filing_date"], "amount": fl.dollars(r["calculated_amount"]),
                         "giver": fl.donor_name(r), "counted": kind == "A"})
    return {"committee": cm["filer_name"], "filer": cm["filer_nid"], "kind": committee_kind(cm),
            "schedule_a_total_text": fl.dollars(c["a_sum"]), "rows": len(c["a"]),
            "first": d[0] if d else "", "last": d[-1] if d else "", "givers_as_filed": givers, "filing_rows": rows,
            "repeats_not_counted": len(c["repeat"]), "h24_only_total_text": fl.dollars(c["only_sum"]) if c["only"] else "",
            "h24_only_rows": len(c["only"])}


def extras(m):
    out = []
    if m["h24_only_rows"]:
        out.append("Also on 24-hour reports with no Schedule A row yet, apart and not in the total: %s." % m["h24_only_total_text"])
    if m["repeats_not_counted"]:
        out.append("%d 24-hour repeat%s of a Schedule A row, listed in the filing, not counted." % (
            m["repeats_not_counted"], "" if m["repeats_not_counted"] == 1 else "s"))
    return out


def build_card(conn, cand):
    """The card of an approved candidate row, built from what the database holds now."""
    official = conn.execute("SELECT * FROM officials WHERE id=?", (cand["official_id"],)).fetchone()
    donor = conn.execute("SELECT * FROM donors WHERE id=?", (cand["donor_id"],)).fetchone()
    meeting = conn.execute("SELECT * FROM meetings WHERE id=?", (cand["meeting_id"],)).fetchone()
    pris = conn.execute("SELECT p.* FROM priorities p JOIN card_statements s ON s.priority_id = p.id "
                        "WHERE s.candidate_id=? ORDER BY p.id", (cand["id"],)).fetchall()
    pm = money.pair_money(conn, official["id"], donor["id"])
    if not pm["per"]:
        raise ValueError("candidate %s has no money found" % cand["id"])
    records = {r["fppc_id"]: r["filer_name"] for r in conn.execute("SELECT * FROM filer_records")}
    quote = cand["quote_text"]
    donor_texts = [p["section"] + " " + p["words"] for p in pris]
    terms = sorted({t for p in pris for t in candidates.priority_terms(p)})
    highlight = shared_terms(quote, donor_texts, terms)
    role = official["office"] + (", District %s" % official["district"] if official["district"] else "")
    committees = [committee_line(c) for c in pm["per"].values()]
    outside = [{"spender": o["payer"], "stance": o["stance"], "amount_text": fl.dollars(o["amount"]),
                "filings": len(o["filings"]), "first": o["first_date"], "last": o["last_date"]}
               for o in money.outside_for(conn, official["id"], donor["id"])]
    statements = [{"label": p["label"], "section": p["section"], "text": p["words"], "url": p["url"],
                   "page_date": p["page_date"], "retrieved": p["retrieved"], "kind": p["source_type"]} for p in pris]
    filing_ids = sorted({r["filing"] for c in committees for r in c["filing_rows"]})
    why = db.jl(cand["doubt_why"])
    return {
        "id": cand["id"], "slug": cand["slug"],
        "title": "%s \u00d7 %s" % (official["name"], donor["name"]),
        "official": {"name": official["name"], "role": role},
        "quote": {"text": quote, "meeting": meeting["body"], "date": meeting["date"], "first_stamp": cand["quote_first_stamp"],
                  "last_stamp": cand["quote_last_stamp"], "transcript_url": meeting["url"], "retrieved": meeting["retrieved"]},
        "highlight": highlight,
        "money": {"committees": committees, "outside_spending": outside,
                  "retrieved": db.get_meta(conn, "money_retrieved"), "loaded_through": db.get_meta(conn, "money_loaded_through"),
                  "dataset_url": fl.DATASET_PAGE,
                  "note": "One line per receiving committee. Each Schedule A total is that committee's own and is "
                          "never added to another's."},
        "donor": {"name": donor["name"], "kind": donor["kind"], "statements": statements,
                  "tie": tie_note(pm["per"], money.all_families(conn), records), "link_note": donor["link_note"]},
        "reading": {"in_common": cand["in_common"], "differs": cand["differs"], "cause": NO_CAUSE},
        "speaker_credit": {"doubt": cand["doubt"], "official": official["name"], "role": role, "cue": cand["cue_text"],
                           "cue_stamp": cand["cue_stamp"], "cue_lines": json.loads(cand["cue_lines"]), "why": why,
                           "note": cand["doubt_note"]},
        "sources": {"transcript": meeting["url"], "meeting": meeting["body"], "date": meeting["date"],
                    "donor_pages": sorted({s["url"] for s in statements}), "filing_ids": filing_ids,
                    "dataset_url": fl.DATASET_PAGE, "money_retrieved": db.get_meta(conn, "money_retrieved")},
    }


def approved_cards(conn):
    """Every approved card, newest meeting first."""
    rows = conn.execute("SELECT c.* FROM candidates c JOIN meetings m ON m.id = c.meeting_id "
                        "WHERE c.status='approved' ORDER BY m.date DESC, c.quote_first_stamp, c.id").fetchall()
    return [build_card(conn, r) for r in rows]


def card_by_slug(conn, slug):
    row = conn.execute("SELECT * FROM candidates WHERE slug=? AND status='approved'", (slug,)).fetchone()
    return build_card(conn, row) if row else None
