"""Collects the sources the funding map is built from.

    python collect.py            # network: DataSF queries and the donors' own pages; writes data/*.json
    python collect.py --money    # only the campaign finance part
    python collect.py --pages    # only the donors' own pages

Money comes from the San Francisco Ethics Commission's campaign finance Transactions and Filers datasets on
DataSF (public, no key). For the Mayor and the eleven supervisors it takes every committee the survey tied to
the official (plus one opposing committee found by name), and for each committee:

  * Schedule A (monetary contributions) by giver, and by the kind of giver the filing records
  * 24-hour contribution reports (form 497 part 1), apart, with the rows that repeat a Schedule A row marked
  * independent expenditure reports (form 496) naming the official, apart, by the committee that spent
  * for each donor family (data/families.json), every row under the family's names, and a census of the names
    the whole dataset holds that look like the family

A failed query stops the run (exit 1); nothing stands in for it.
"""

import argparse
import json
import os
import sys
import time

import fmap_lib as fl

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
SNAPSHOT = os.path.join(DATA, "money_snapshot.json")

# Committees the survey's seed lacks: found by searching the Transactions and Filers datasets for each
# official's surname in committee names.
EXTRA_COMMITTEES = {
    "Daniel Lurie": [{
        "filer_nid": "212391140",
        "filer_name": "Our Future, Our SF Opposing Lurie & Farrell for Mayor 2024",
        "filer_type": "Primarily Formed Candidate", "status": "TERMINATED", "match": "weak",
    }],
}

IND_LIST_MIN = 2500.0  # individuals are listed by name from this much, summed within one committee


def log(msg):
    print(msg, flush=True)


def committees_table(seed):
    out = []
    for o in seed["officials"]:
        given = o["name"].split()[0]
        rows = list(o["committees"]) + EXTRA_COMMITTEES.get(o["name"], [])
        for c in rows:
            rel, rel_words = fl.relation_of(c)
            out.append({
                "official": o["name"], "office": o["office"], "district": o["district"],
                "surname": o["surname"], "given": given,
                "filer_nid": c["filer_nid"], "filer_name": c["filer_name"], "filer_type": c["filer_type"],
                "status": c["status"], "match": c.get("match", ""),
                "relation": rel, "relation_words": rel_words,
                "cmte_office": fl.office_of(c["filer_name"]) if rel in ("own", "own-other") else "",
            })
    return out


def refresh_filers(committees):
    """The Filers dataset's current record for each committee."""
    ids = sorted({c["filer_nid"] for c in committees})
    rows = fl.query(fl.FILERS, {"$where": "filer_nid in (%s)" % fl.in_list(ids), "$limit": "500"})
    by = {r["filer_nid"]: r for r in rows}
    for c in committees:
        r = by.get(c["filer_nid"])
        if r:
            c["status"] = r.get("status", c["status"])
            c["filer_name"] = r.get("filer_name", c["filer_name"])
            c["candidate_name"] = r.get("candidate_name", "")
            c["fppc_id"] = r.get("fppc_id", "")
        else:
            c["candidate_name"] = ""
            c["fppc_id"] = ""


def collect_money():
    seed = fl.load_committees(os.path.join(DATA, "committees_seed.json"))
    families = json.load(open(os.path.join(DATA, "families.json"), encoding="utf-8"))["families"]
    committees = committees_table(seed)
    log("committees: %d for %d officials" % (len(committees), len(seed["officials"])))
    refresh_filers(committees)
    nids = sorted({c["filer_nid"] for c in committees})
    inl = fl.in_list(nids)
    T = fl.TRANSACTIONS

    loaded = fl.query(T, {"$select": "max(data_loaded_at) as m"})[0]["m"][:10]

    log("Schedule A summary per committee")
    a_summary = fl.query(T, {
        "$select": "filer_nid, count(*) as n, sum(calculated_amount) as amt, min(calculated_date) as d0, "
                   "max(calculated_date) as d1, max(filing_date) as last_filing",
        "$where": "form_type='A' AND filer_nid in (%s)" % inl, "$group": "filer_nid", "$limit": "500"})
    unitemized = fl.query(T, {
        "$select": "filer_nid, count(*) as n, sum(calculated_amount) as amt",
        "$where": "form_type='F460ALine2' AND filer_nid in (%s)" % inl, "$group": "filer_nid", "$limit": "500"})

    log("Schedule A by kind of giver")
    by_entity = fl.query(T, {
        "$select": "filer_nid, entity_code, count(*) as n, sum(calculated_amount) as amt",
        "$where": "form_type='A' AND filer_nid in (%s)" % inl, "$group": "filer_nid, entity_code",
        "$limit": "5000"})

    log("Schedule A, organisations and committees by name")
    donors_org = fl.query_all(T, {
        "$select": "filer_nid, entity_code, committee_id, transaction_last_name as ln, transaction_first_name as fn, "
                   "count(*) as n, sum(calculated_amount) as amt, min(calculated_date) as d0, "
                   "max(calculated_date) as d1",
        "$where": "form_type='A' AND entity_code in ('COM','OTH','SCC','PTY') AND filer_nid in (%s)" % inl,
        "$group": "filer_nid, entity_code, committee_id, ln, fn", "$order": "filer_nid, entity_code, committee_id, ln, fn"})
    log("Schedule A, individuals from $%d within one committee" % IND_LIST_MIN)
    donors_ind = fl.query_all(T, {
        "$select": "filer_nid, entity_code, committee_id, transaction_last_name as ln, transaction_first_name as fn, "
                   "count(*) as n, sum(calculated_amount) as amt, min(calculated_date) as d0, "
                   "max(calculated_date) as d1",
        "$where": "form_type='A' AND entity_code='IND' AND filer_nid in (%s)" % inl,
        "$group": "filer_nid, entity_code, committee_id, ln, fn",
        "$having": "sum(calculated_amount) >= %d" % IND_LIST_MIN,
        "$order": "filer_nid, entity_code, committee_id, ln, fn"})

    log("24-hour contribution reports (form 497 part 1)")
    f497 = fl.query_all(T, {
        "$select": "filer_nid, filing_id_number, filing_date, filing_version, calculated_date, calculated_amount, "
                   "entity_code, committee_id, transaction_first_name as fn, transaction_last_name as ln",
        "$where": "form_type='F497P1' AND filer_nid in (%s)" % inl,
        "$order": "filer_nid, calculated_date, filing_id_number, ln"})
    f497_nids = sorted({r["filer_nid"] for r in f497})
    a_for_match = []
    if f497_nids:
        a_for_match = fl.query_all(T, {
            "$select": "filer_nid, calculated_date, calculated_amount, transaction_first_name as fn, "
                       "transaction_last_name as ln",
            "$where": "form_type='A' AND calculated_amount >= 1000 AND filer_nid in (%s)" % fl.in_list(f497_nids),
            "$order": "filer_nid, calculated_date, ln"})

    log("independent expenditure reports (form 496) naming an official")
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

    log("who the committee donors are (FPPC ids looked up in the Filers dataset)")
    ids = sorted({r["committee_id"] for r in donors_org if r.get("committee_id")})
    filers_lookup = {}
    for i in range(0, len(ids), 120):
        chunk = ids[i:i + 120]
        for r in fl.query(fl.FILERS, {"$where": "fppc_id in (%s)" % fl.in_list(chunk), "$limit": "2000"}):
            filers_lookup.setdefault(r["fppc_id"], []).append(
                {k: r.get(k, "") for k in ("filer_nid", "filer_name", "filer_type", "status")})

    log("rows under each donor family's names, in the committees tied to the officials")
    family_rows = {}
    for fam in families:
        clause = fl.family_clause("transaction_last_name", fam, "committee_id")
        rows = fl.query_all(T, {
            "$select": "filer_nid, form_type, filing_id_number, filing_date, filing_type, filing_version, "
                       "calculated_date, calculated_amount, entity_code, committee_id, "
                       "transaction_first_name as fn, transaction_last_name as ln, memo_code",
            "$where": "form_type in ('A','F497P1') AND filer_nid in (%s) AND %s" % (inl, clause),
            "$order": "filer_nid, calculated_date, filing_id_number"})
        family_rows[fam["key"]] = rows
        log("  %s: %d rows" % (fam["key"], len(rows)))

    log("census: names the whole dataset holds that look like each family")
    census = {}
    for fam in families:
        c1 = fl.family_clause("transaction_last_name", fam, "committee_id")
        givers = fl.query(T, {
            "$select": "transaction_last_name as ln, entity_code, committee_id, count(*) as n, "
                       "sum(calculated_amount) as amt, count(distinct filer_nid) as filers",
            "$where": "form_type='A' AND %s" % c1,
            "$group": "ln, entity_code, committee_id", "$order": "amt desc", "$limit": "60"})
        c2 = fl.family_clause("filer_name", fam, "fppc_id")
        comm = fl.query(fl.FILERS, {
            "$select": "filer_nid, filer_name, filer_type, status, fppc_id",
            "$where": c2, "$order": "filer_name", "$limit": "60"})
        census[fam["key"]] = {"givers": givers, "committees_named": comm}

    snapshot = {
        "retrieved": fl.today(), "data_loaded_at": loaded, "dataset": fl.DATASET_PAGE,
        "committees": committees, "a_summary": a_summary, "unitemized": unitemized, "by_entity": by_entity,
        "donors_org": donors_org, "donors_ind": donors_ind, "ind_list_min": IND_LIST_MIN,
        "f497": f497, "a_for_match": a_for_match, "independent": independent,
        "filers_lookup": filers_lookup, "family_rows": family_rows, "census": census,
    }
    with open(SNAPSHOT, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=1, sort_keys=True)
    log("wrote %s (data loaded through %s)" % (os.path.relpath(SNAPSHOT, HERE), loaded))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--money", action="store_true")
    ap.add_argument("--pages", action="store_true")
    args = ap.parse_args(argv)
    both = not (args.money or args.pages)
    try:
        if args.money or both:
            collect_money()
        if args.pages or both:
            import collect_pages
            ok = collect_pages.collect_pages()
            collect_pages.check_reported()
            if not ok:
                return 1
    except fl.QueryError as exc:
        print("QUERY FAILED: %s" % exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
