"""Refreshes the stored campaign finance rows from the Ethics Commission's Transactions and Filers datasets on
DataSF (public; DATASF_APP_TOKEN, when given, only raises the rate limit).

For each donor family: every Schedule A and 24-hour (form 497 part 1) row under the family's names in the
committees tied to the officials. Also the independent expenditure reports (form 496) naming the officials, and
the registered record of each committee that gave. The queries are the ones collect.py in
discovery/official-funding-map makes, one at a time with a pause between them. A failed query raises
fmap_lib.QueryError; nothing stands in for it.
"""

import datetime
import time

from . import sources  # noqa: F401

import fmap_lib as fl  # noqa: E402


def refresh(committees, families, pause_s, store, log=lambda msg: None):
    """Queries DataSF and calls store(name, payload) for each piece. Returns the counts."""
    nids = sorted({c["filer_nid"] for c in committees})
    inl = fl.in_list(nids)
    T = fl.TRANSACTIONS
    loaded = fl.query(T, {"$select": "max(data_loaded_at) as m"})[0]["m"][:10]
    counts = {"families": 0, "rows": 0}
    all_ids = set()
    for fam in families:
        time.sleep(pause_s)
        clause = fl.family_clause("transaction_last_name", fam, "committee_id")
        rows = fl.query_all(T, {
            "$select": "filer_nid, form_type, filing_id_number, filing_date, filing_type, filing_version, "
                       "calculated_date, calculated_amount, entity_code, committee_id, "
                       "transaction_first_name as fn, transaction_last_name as ln, memo_code",
            "$where": "form_type in ('A','F497P1') AND filer_nid in (%s) AND %s" % (inl, clause),
            "$order": "filer_nid, calculated_date, filing_id_number"})
        store("family_rows:" + fam["key"], rows)
        counts["families"] += 1
        counts["rows"] += len(rows)
        all_ids.update(r["committee_id"] for r in rows if r.get("committee_id"))
        log("%s: %d rows" % (fam["key"], len(rows)))
    time.sleep(pause_s)
    surnames = sorted({c["surname"] for c in committees})
    like = " OR ".join("upper(candidate_last_name) like %s" % fl.lit("%" + s.upper() + "%") for s in surnames)
    independent = fl.query_all(T, {
        "$select": "filer_nid, filer_name, filing_id_number, filing_date, filing_version, candidate_last_name, "
                   "candidate_first_name, support_oppose_code, office_code, office_description, district_number, "
                   "count(*) as n, sum(calculated_amount) as amt, min(calculated_date) as d0, max(calculated_date) as d1",
        "$where": "form_type='F496' AND (%s)" % like,
        "$group": "filer_nid, filer_name, filing_id_number, filing_date, filing_version, candidate_last_name, "
                  "candidate_first_name, support_oppose_code, office_code, office_description, district_number",
        "$order": "filer_nid, filing_id_number, candidate_last_name, candidate_first_name"})
    store("independent", independent)
    counts["independent_reports"] = len(independent)
    lookup = {}
    ids = sorted(all_ids)
    for i in range(0, len(ids), 120):
        time.sleep(pause_s)
        for r in fl.query(fl.FILERS, {"$where": "fppc_id in (%s)" % fl.in_list(ids[i:i + 120]), "$limit": "2000"}):
            lookup.setdefault(r["fppc_id"], []).append({k: r.get(k, "") for k in ("filer_nid", "filer_name", "filer_type", "status")})
    store("filers_lookup", lookup)
    store("meta", {"retrieved": datetime.date.today().isoformat(), "data_loaded_at": loaded})
    return counts
