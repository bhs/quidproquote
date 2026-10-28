"""Profile San Francisco campaign finance data on DataSF (data.sf.gov).

Run once:  python profile.py
Writes data-profile.md (comparable output) and data-profile.json beside it and
prints the markdown. DataSF is queried anonymously, retrying when throttled.
"""

import collections
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import calaccess
import survey_lib as lib

HOST = "https://data.sf.gov"
HERE = os.path.dirname(os.path.abspath(__file__))

TX = "pitq-e56w"        # Campaign Finance - Transactions
FILERS = "4c8t-ngau"    # San Francisco Campaign Filers
FILINGS = "qizs-bwft"   # Filings Received by SFEC
SUMMARY = "9ggq-m8hp"   # Summary Totals
DATASETS = [
    (TX, "Transactions"),
    (FILERS, "San Francisco Campaign Filers"),
    (FILINGS, "Filings Received by SFEC"),
    (SUMMARY, "Summary Totals"),
    ("dbak-p2fq", "Public Funds Approved"),
    ("9gib-7p8x", "Individual Expenditure Ceilings (IEC)"),
    ("s9b2-abj2", "Local Non-Primarily Formed Committees"),
    ("3n88-2rrb", "State Filer Data"),
    ("wygs-cc76", "Data Key (historical)"),
]
OWN_FORMS = ["A", "F460ALine2", "C", "B1", "I", "F497P1", "F497P2", "D"]


class DataSFError(RuntimeError):
    pass


def _get(url):
    headers = {"User-Agent": "campaign-finance-survey"}
    last = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            body = exc.read()[:300].decode("utf-8", "replace")
            last = "HTTP %s %s" % (exc.code, body)
            if exc.code not in (429, 500, 502, 503, 504):
                break
        except (urllib.error.URLError, TimeoutError) as exc:
            last = str(exc)
        time.sleep(2 * (attempt + 1))
    raise DataSFError("%s failed: %s" % (url, last))


def q(dataset, **params):
    url = "%s/resource/%s.json?%s" % (HOST, dataset, urllib.parse.urlencode(params))
    return _get(url)


def q_all(dataset, page=50000, **params):
    rows, offset = [], 0
    while True:
        chunk = q(dataset, **dict(params, **{"$limit": str(page), "$offset": str(offset)}))
        rows.extend(chunk)
        if len(chunk) < page:
            return rows
        offset += page


def view(dataset):
    return _get("%s/api/views/%s.json" % (HOST, dataset))


def one(dataset, **params):
    rows = q(dataset, **params)
    return rows[0] if rows else {}


def f(value):
    return float(value) if value not in (None, "") else 0.0


def in_list(values):
    return "(" + ",".join(lib.soql_quote(v) for v in values) + ")"


def profile_datasets():
    out = []
    for ds, label in DATASETS:
        meta = view(ds)
        cols = [c["fieldName"] for c in meta.get("columns", [])]
        row = {
            "id": ds, "name": meta.get("name"), "label": label, "columns": len(cols),
            "rows": int(one(ds, **{"$select": "count(*) as n"}).get("n", 0)),
            "rows_updated_at": time.strftime("%Y-%m-%d", time.gmtime(meta.get("rowsUpdatedAt", 0))),
            "publishing_frequency": (meta.get("metadata", {}).get("custom_fields", {})
                                     .get("Publishing Details", {}).get("Publishing frequency", "")),
            "max_loaded": "",
        }
        if "data_loaded_at" in cols:
            row["max_loaded"] = lib.date_only(one(ds, **{"$select": "max(data_loaded_at) as m"}).get("m"))
        out.append(row)
    return out


def profile_transactions():
    res = {}
    res["by_form"] = q(TX, **{
        "$select": "form_type,record_type,count(*) as n,sum(calculated_amount) as s,"
                   "min(calculated_date) as a,max(calculated_date) as b",
        "$group": "form_type,record_type", "$order": "n desc"})
    res["by_filing_type"] = q(TX, **{
        "$select": "filing_type,count(*) as n", "$group": "filing_type", "$order": "n desc"})
    res["versions"] = q(TX, **{
        "$select": "filing_version,count(*) as n", "$group": "filing_version", "$order": "n desc", "$limit": "8"})
    res["a_by_year"] = q(TX, **{
        "$select": "date_extract_y(calculated_date) as y,count(*) as n,sum(calculated_amount) as s",
        "$where": "form_type='A'", "$group": "y", "$order": "y"})
    res["a_entity"] = q(TX, **{
        "$select": "entity_code,count(*) as n,sum(calculated_amount) as s,count(transaction_first_name) as fn,"
                   "count(transaction_employer) as emp,count(transaction_occupation) as occ,"
                   "count(transaction_zip) as zip,count(committee_id) as cid",
        "$where": "form_type='A'", "$group": "entity_code", "$order": "n desc"})
    res["a_negative"] = one(TX, **{"$select": "count(*) as n,sum(calculated_amount) as s",
                                   "$where": "form_type='A' and calculated_amount<0"})
    res["bad_dates"] = one(TX, **{
        "$select": "count(*) as n",
        "$where": "calculated_date<'1998-01-01' or calculated_date>'%s'" % time.strftime("%Y-%m-%d", time.gmtime(time.time() + 86400))})
    res["null_filing_id"] = one(TX, **{"$select": "count(*) as n", "$where": "filing_id_number is null"})
    res["distinct_filings"] = one(TX, **{"$select": "count(distinct filing_nid) as n"})
    res["distinct_filers"] = one(TX, **{"$select": "count(distinct filer_nid) as n"})
    return res


def profile_filings():
    res = {}
    res["by_status"] = q(FILINGS, **{
        "$select": "filing_type,mechanism_type,rejected,count(*) as n",
        "$group": "filing_type,mechanism_type,rejected", "$order": "n desc"})
    res["superseded"] = one(FILINGS, **{"$select": "count(*) as n", "$where": "current_status like 'Superseded%'"})
    res["current"] = one(FILINGS, **{"$select": "count(*) as n", "$where": "current_status like 'Most Recent%'"})
    res["distinct_filing_nid"] = one(FILINGS, **{"$select": "count(distinct filing_nid) as n"})
    res["by_year_mech"] = q(FILINGS, **{
        "$select": "date_extract_y(filing_date) as y,mechanism_type,count(*) as n",
        "$where": "date_extract_y(filing_date)>=2012 and current_status like 'Most Recent%'",
        "$group": "y,mechanism_type", "$order": "y"})
    res["by_form"] = q(FILINGS, **{
        "$select": "form_type,count(*) as n,min(filing_date) as a,max(filing_date) as b",
        "$group": "form_type", "$order": "n desc", "$limit": "12"})
    return res


def profile_filers():
    return q(FILERS, **{
        "$select": "filer_type,status,count(*) as n,count(candidate_name) as with_candidate",
        "$group": "filer_type,status", "$order": "n desc", "$limit": "14"})


def profile_official(off, all_filers):
    """Committees tied to one official and what each holds."""
    matched = []
    for filer in all_filers:
        m = lib.match_filer(off, filer)
        if m:
            role = lib.classify_committee(filer, m)
            matched.append(dict(filer, match=m, role=role))
    nids = [m["filer_nid"] for m in matched]
    res = {"official": off, "committees": matched, "public_funds": [], "ie": []}
    if nids:
        where = "filer_nid in " + in_list(nids)
        tx = q(TX, **{
            "$select": "filer_nid,form_type,count(*) as n,sum(calculated_amount) as s,"
                       "min(calculated_date) as a,max(calculated_date) as b",
            "$where": where + " and form_type in " + in_list(OWN_FORMS),
            "$group": "filer_nid,form_type", "$limit": "50000"})
        yrs = q(TX, **{
            "$select": "filer_nid,date_extract_y(calculated_date) as y,sum(calculated_amount) as s",
            "$where": where + " and form_type in ('A','F460ALine2')", "$group": "filer_nid,y", "$limit": "50000"})
        fil = q(FILINGS, **{
            "$select": "filer_nid,mechanism_type,count(*) as n,min(filing_date) as a,max(filing_date) as b",
            "$where": where + " and current_status like 'Most Recent%' and form_type in ('FPPC460','FPPC461','FPPC450','FPPC470','FPPC410')",
            "$group": "filer_nid,mechanism_type", "$limit": "50000"})
        sup = q(FILINGS, **{
            "$select": "filer_nid,count(*) as n",
            "$where": where + " and current_status like 'Superseded%'", "$group": "filer_nid", "$limit": "50000"})
        summ = q(SUMMARY, **{
            "$select": "filer_nid,count(*) as n,sum(schedulea_line_3) as sa,min(start_date) as a,max(end_date) as b",
            "$where": where + " and form_type='FPPC460'", "$group": "filer_nid", "$limit": "50000"})
        res.update(tx=tx, years=yrs, filings=fil, superseded=sup, summary=summ)
    last_prefix = off["last"]
    ie = q(TX, **{
        "$select": "form_type,candidate_first_name,candidate_last_name,office_code,support_oppose_code,"
                   "count(*) as n,sum(calculated_amount) as s,count(distinct filer_nid) as payers,"
                   "min(calculated_date) as a,max(calculated_date) as b",
        "$where": "upper(candidate_last_name)=%s and form_type in ('F496','F461P5','D')" % lib.soql_quote(last_prefix.upper()),
        "$group": "form_type,candidate_first_name,candidate_last_name,office_code,support_oppose_code",
        "$limit": "50000"})
    res["ie"] = [r for r in ie if lib.ie_name_matches(off, r.get("candidate_first_name"), r.get("candidate_last_name"))]
    # Public funds are published under 'Last, First' names.
    pf = q("dbak-p2fq", **{"$where": "upper(candidate) like %s" % lib.soql_quote(off["last"].upper() + ", " + off["first"][:3].upper() + "%")})
    res["public_funds"] = pf
    return res


def summarise_official(res):
    """Roll the per-committee rows up to the numbers shown in the report."""
    tx = collections.defaultdict(dict)
    for r in res.get("tx", []):
        tx[r["filer_nid"]][r["form_type"]] = r
    fil = collections.defaultdict(lambda: {"Electronic": 0, "Paper": 0, "first": None, "last": None})
    for r in res.get("filings", []):
        d = fil[r["filer_nid"]]
        d[r["mechanism_type"]] += int(r["n"])
        d["first"] = min(filter(None, [d["first"], r["a"]]))
        d["last"] = max(filter(None, [d["last"], r["b"]]))
    sup = {r["filer_nid"]: int(r["n"]) for r in res.get("superseded", [])}
    summ = {r["filer_nid"]: r for r in res.get("summary", [])}
    rows = []
    for c in res["committees"]:
        nid = c["filer_nid"]
        t = tx.get(nid, {})
        a = f(t.get("A", {}).get("s"))
        un = f(t.get("F460ALine2", {}).get("s"))
        sa = f(summ.get(nid, {}).get("sa"))
        rows.append({
            "filer_nid": nid, "name": c["filer_name"], "type": c["filer_type"], "status": c["status"],
            "match": c["match"], "role": c["role"],
            "itemized_rows": int(t.get("A", {}).get("n", 0)), "itemized": a, "unitemized": un,
            "nonmonetary": f(t.get("C", {}).get("s")), "loans": f(t.get("B1", {}).get("s")),
            "f497_received": f(t.get("F497P1", {}).get("s")),
            "first_tx": t.get("A", {}).get("a"), "last_tx": t.get("A", {}).get("b"),
            "e_filings": fil[nid]["Electronic"], "p_filings": fil[nid]["Paper"],
            "superseded": sup.get(nid, 0), "last_filing": fil[nid]["last"],
            "summary_filings": int(summ.get(nid, {}).get("n", 0)),
            "summary_sched_a": sa, "summary_last_end": summ.get(nid, {}).get("b"),
            "reconciliation_gap": round(a + un - sa, 2),
        })
    return rows


def amendment_behaviour(since="2022-01-01"):
    """How Form 460 reports first filed on or after `since` were amended.

    A report period keeps its filing_nid; every submission is a new
    filing_activity_nid. Submissions are typed by filing_type: FiledOriginal,
    FiledAmendment (new data), and AttachmentsAdded / ContentsChanged (no new
    transaction data). Reports are grouped by their first submission date, so an
    amendment filed after `since` to a report first filed earlier is not counted.
    Rejected submissions are left out.
    """
    rows = q_all(FILINGS, **{
        "$select": "filing_nid,filing_activity_nid,filing_date,filing_type,mechanism_type",
        "$where": "form_type='FPPC460' and (rejected is null or rejected=false) and filing_date is not null",
        "$order": "filing_nid,filing_activity_nid"})
    return lib.summarise_amendments(rows, since)


def profile_cadence():
    res = {}
    res["loaded_by_day"] = q(TX, **{
        "$select": "data_loaded_at,count(*) as n,count(distinct filing_nid) as filings",
        "$where": "data_loaded_at is not null", "$group": "data_loaded_at",
        "$order": "data_loaded_at desc", "$limit": "14"})
    res["filed_by_day"] = q(FILINGS, **{
        "$select": "filing_date,count(*) as n", "$where": "filing_date is not null", "$group": "filing_date",
        "$order": "filing_date desc", "$limit": "14"})
    lag = {}
    base = "form_type='A' and calculated_date>='2024-01-01'"
    total = int(one(TX, **{"$select": "count(*) as n", "$where": base})["n"])
    prev = 0
    for days in (7, 30, 90, 180):
        n = int(one(TX, **{"$select": "count(*) as n",
                           "$where": base + " and date_diff_d(filing_date,calculated_date)<=%d" % days})["n"])
        lag["<=%d days" % days] = n
    lag["total"] = total
    res["tx_to_filing_lag"] = lag
    res["amendments"] = amendment_behaviour()
    return res


def ie_overlap():
    """Do Form 496 and Schedule D report the same money? Compare per payer and candidate."""
    rows = q_all(TX, **{
        "$select": "filer_nid,form_type,candidate_last_name,support_oppose_code,sum(calculated_amount) as s",
        "$where": "form_type in ('F496','D') and candidate_last_name is not null and calculated_date>='2018-01-01'",
        "$group": "filer_nid,form_type,candidate_last_name,support_oppose_code"})
    groups = collections.defaultdict(dict)
    for r in rows:
        key = (r["filer_nid"], r["candidate_last_name"].upper(), r.get("support_oppose_code"))
        groups[key][r["form_type"]] = f(r["s"])
    both = [g for g in groups.values() if "F496" in g and "D" in g]
    same = sum(1 for g in both if abs(g["F496"] - g["D"]) < 1.0)
    return {"payer_candidate_pairs_with_both": len(both), "equal_within_1_dollar": same,
            "pairs_496_only": sum(1 for g in groups.values() if "F496" in g and "D" not in g),
            "pairs_d_only": sum(1 for g in groups.values() if "D" in g and "F496" not in g)}


def f497_overlap():
    """Are 24-hour contribution reports (Form 497 part 1) also on Schedule A of the 460?"""
    sel = "filer_nid,calculated_amount,calculated_date,transaction_last_name"
    r497 = q_all(TX, **{"$select": sel, "$where": "form_type='F497P1' and calculated_date>='2022-01-01'"})
    a_rows = q_all(TX, **{"$select": sel, "$where": "form_type='A' and calculated_date>='2022-01-01'"})
    key = lambda r: (r["filer_nid"], r.get("calculated_amount"), (r.get("calculated_date") or "")[:10],
                     (r.get("transaction_last_name") or "").strip().lower())
    a_keys = {key(r) for r in a_rows}
    matched = [r for r in r497 if key(r) in a_keys]
    return {"f497p1_rows_since_2022": len(r497), "also_on_schedule_a": len(matched),
            "dollars_497": sum(f(r["calculated_amount"]) for r in r497),
            "dollars_also_on_a": sum(f(r["calculated_amount"]) for r in matched)}


def profile_donors(all_filers):
    res = {}
    orgs = q_all(TX, **{
        "$select": "transaction_last_name,entity_code,count(*) as n,sum(calculated_amount) as s",
        "$where": "form_type='A' and entity_code in ('OTH','COM','SCC','PTY') and transaction_last_name is not null",
        "$group": "transaction_last_name,entity_code"})
    raw_names = {r["transaction_last_name"].strip() for r in orgs}
    keys1, keys2 = collections.defaultdict(set), collections.defaultdict(set)
    dollars1 = collections.Counter()
    for r in orgs:
        nm = r["transaction_last_name"].strip()
        k1 = lib.normalize_org(nm)
        keys1[k1].add(nm)
        keys2[lib.normalize_org(nm, aggressive=True)].add(nm)
        dollars1[k1] += f(r["s"])
    multi = [k for k, v in keys1.items() if len(v) > 1]
    res["orgs"] = {
        "raw_distinct_names": len(raw_names), "after_level1": len(keys1), "after_level2": len(keys2),
        "level1_keys_with_several_spellings": len(multi),
        "dollars_in_multi_spelling_keys": sum(dollars1[k] for k in multi),
        "dollars_total": sum(dollars1.values()),
        "top_variant_examples": [
            {"key": k, "spellings": len(keys1[k]), "dollars": dollars1[k]}
            for k in sorted(multi, key=lambda k: -dollars1[k])[:8]],
    }
    people = q_all(TX, **{
        "$select": "transaction_last_name,transaction_first_name,transaction_zip,count(*) as n",
        "$where": "form_type='A' and entity_code='IND' and calculated_date>='2018-01-01'",
        "$group": "transaction_last_name,transaction_first_name,transaction_zip"})
    raw_keys = {(r.get("transaction_last_name"), r.get("transaction_first_name"), r.get("transaction_zip")) for r in people}
    norm_zip = {(*lib.normalize_person(r.get("transaction_last_name"), r.get("transaction_first_name")),
                 lib.zip5(r.get("transaction_zip"))) for r in people}
    zips_per_name = collections.defaultdict(set)
    for last, first, z in norm_zip:
        zips_per_name[(last, first)].add(z)
    res["people"] = {
        "since": "2018-01-01", "raw_name_zip_combinations": len(raw_keys),
        "normalized_name_zip5_keys": len(norm_zip), "normalized_names": len(zips_per_name),
        "names_seen_in_several_zip5": sum(1 for v in zips_per_name.values() if len(v) > 1),
    }
    cids = q_all(TX, **{
        "$select": "committee_id,count(*) as n,sum(calculated_amount) as s",
        "$where": "form_type='A' and committee_id is not null", "$group": "committee_id"})
    fppc = {x.get("fppc_id") for x in all_filers}
    state = {r["filer_id"] for r in q_all("3n88-2rrb", **{"$select": "filer_id", "$group": "filer_id"})}
    ids = {r["committee_id"] for r in cids}
    res["committee_ids"] = {
        "distinct_committee_ids_on_schedule_a": len(ids),
        "in_sf_filers_dataset": len(ids & fppc), "in_state_filer_dataset_only": len((ids & state) - fppc),
        "in_neither": len(ids - fppc - state)}
    # The ids in neither dataset, looked up in California's own committee records (CAL-ACCESS).
    unresolved = ids - fppc - state
    by_id, by_xref = calaccess.filer_names()
    res["committee_ids"]["unresolved_in_state_records"] = lib.resolve_committee_ids(
        {r["committee_id"]: f(r["s"]) for r in cids if r["committee_id"] in unresolved}, by_id, by_xref)
    res["com_rows_without_id"] = one(TX, **{
        "$select": "count(*) as n,sum(calculated_amount) as s",
        "$where": "form_type='A' and entity_code='COM' and committee_id is null"})
    res["filers_pending_id"] = one(FILERS, **{"$select": "count(*) as n", "$where": "fppc_id in ('pending','unavailable','n/a')"})
    return res


def render(data):
    L = []
    w = L.append
    w("# Campaign finance data profile (generated)\n")
    w("Generated by `profile.py` from live DataSF queries. Data loaded through %s. "
      "Nothing here names an individual donor.\n" % data["as_of"])
    w("## 1. Datasets\n")
    w(lib.md_table(["Dataset", "ID", "Rows", "Columns", "Rows updated", "Max data_loaded_at", "Publishing"],
                   [[d["name"], d["id"], lib.num(d["rows"]), d["columns"], d["rows_updated_at"],
                     d["max_loaded"] or "-", d["publishing_frequency"] or "-"] for d in data["datasets"]]))
    t = data["transactions"]
    w("\n## 2. Transactions dataset (`%s`)\n" % TX)
    w("Distinct filings: %s; distinct filers: %s; rows with blank filing id: %s; rows with a transaction date "
      "before 1998 or in the future: %s; negative Schedule A rows: %s (%s).\n" % (
          lib.num(t["distinct_filings"]["n"]), lib.num(t["distinct_filers"]["n"]), lib.num(t["null_filing_id"]["n"]),
          lib.num(t["bad_dates"]["n"]), lib.num(t["a_negative"]["n"]), lib.money(t["a_negative"].get("s"))))
    w(lib.md_table(["form_type", "record_type", "Rows", "Sum calculated_amount", "First date", "Last date"],
                   [[r["form_type"], r["record_type"], lib.num(r["n"]), lib.money(r["s"]),
                     lib.date_only(r.get("a")), lib.date_only(r.get("b"))] for r in t["by_form"]]))
    w("\nRows by filing_type: " + ", ".join("%s %s" % (r.get("filing_type"), lib.num(r["n"])) for r in t["by_filing_type"]))
    w("\nRows by filing_version: " + ", ".join("v%s %s" % (r.get("filing_version"), lib.num(r["n"])) for r in t["versions"]))
    w("\nSchedule A (itemized monetary contributions) by transaction year:\n")
    w(lib.md_table(["Year", "Rows", "Sum"], [[r.get("y", "-"), lib.num(r["n"]), lib.money(r["s"])] for r in t["a_by_year"]]))
    w("\nSchedule A contributor fields by entity_code (counts of rows with the field filled):\n")
    w(lib.md_table(["entity_code", "Rows", "Sum", "first name", "employer", "occupation", "zip", "committee_id"],
                   [[r.get("entity_code", "-"), lib.num(r["n"]), lib.money(r["s"]), lib.num(r["fn"]), lib.num(r["emp"]),
                     lib.num(r["occ"]), lib.num(r["zip"]), lib.num(r["cid"])] for r in t["a_entity"]]))
    fl = data["filings"]
    w("\n## 3. Filings dataset (`%s`)\n" % FILINGS)
    w("Rows: current %s, superseded %s; distinct filing_nid %s.\n" % (
        lib.num(fl["current"]["n"]), lib.num(fl["superseded"]["n"]), lib.num(fl["distinct_filing_nid"]["n"])))
    w(lib.md_table(["filing_type", "mechanism", "rejected", "Rows"],
                   [[r.get("filing_type"), r.get("mechanism_type"), r.get("rejected"), lib.num(r["n"])] for r in fl["by_status"]]))
    w("\nCurrent filings per year, paper vs electronic (paper filings have no transaction rows):\n")
    ym = collections.defaultdict(dict)
    for r in fl["by_year_mech"]:
        ym[r["y"]][r["mechanism_type"]] = int(r["n"])
    w(lib.md_table(["Year", "Electronic", "Paper"], [[y, v.get("Electronic", 0), v.get("Paper", 0)] for y, v in sorted(ym.items())]))
    w("\nFiling forms: " + ", ".join("%s %s (%s to %s)" % (r["form_type"], lib.num(r["n"]), lib.date_only(r["a"]), lib.date_only(r["b"])) for r in fl["by_form"]))
    w("\n## 4. Filers dataset (`%s`)\n" % FILERS)
    w(lib.md_table(["filer_type", "status", "Filers", "with candidate_name"],
                   [[r["filer_type"], r["status"], lib.num(r["n"]), lib.num(r["with_candidate"])] for r in data["filers"]]))
    w("\n## 5. Current officials and the committees tied to them\n")
    w("Roster (Board of Supervisors member listing on sfbos.org; Mayor from the sf.gov profile): Mayor and 11 supervisors. Matching: `strong` = filer candidate_name is the "
      "official's; `weak` = only the committee's own name mentions the official (needs review). Money columns are "
      "Schedule A itemized + unitemized (F460ALine2) from the Transactions dataset; `gap` = that minus the sum of "
      "Form 460 summary Schedule A line 3 for the same committee (0 means the two datasets agree).\n")
    for res in data["officials"]:
        off = res["official"]
        w("### %s, %s%s\n" % (off["name"], off["office"], " D" + off["district"] if off["district"] else ""))
        rows = res["rows"]
        w(lib.md_table(
            ["Committee", "Role", "Match", "Status", "Itemized", "Unitemized", "497 (not additive)", "e/paper filings",
             "Last filing", "Last 460 period end", "gap"],
            [[r["name"], r["role"], r["match"], r["status"], lib.money(r["itemized"]), lib.money(r["unitemized"]),
              lib.money(r["f497_received"]), "%d/%d" % (r["e_filings"], r["p_filings"]), lib.date_only(r["last_filing"]),
              lib.date_only(r["summary_last_end"]), lib.money(r["reconciliation_gap"])] for r in rows]) if rows else "No committees matched.")
        own = [r for r in rows if lib.own_for_current_office(r["role"])]
        w("\nOwn Mayor/Supervisor candidate and officeholder committees, any election cycle: %d; itemized+unitemized %s; first transaction %s; last %s." % (
            len(own), lib.money(sum(r["itemized"] + r["unitemized"] for r in own)),
            lib.date_only(min([r["first_tx"] for r in own if r["first_tx"]] or [None])),
            lib.date_only(max([r["last_tx"] for r in own if r["last_tx"]] or [None]))))
        if res["ie"]:
            w("\nIndependent-expenditure style rows naming the official (name match only; forms overlap, do not add):\n")
            w(lib.md_table(["form", "first name as filed", "office_code", "S/O", "Rows", "Payers", "Sum"],
                           [[r["form_type"], r.get("candidate_first_name"), r.get("office_code") or "-",
                             r.get("support_oppose_code") or "-", r["n"], r["payers"], lib.money(r["s"])]
                            for r in sorted(res["ie"], key=lambda r: -f(r["s"]))[:8]]))
        if res["public_funds"]:
            w("\nPublic funds approved: %s across %d approvals (elections %s)." % (
                lib.money(sum(f(r["funds_approved"]) for r in res["public_funds"])), len(res["public_funds"]),
                ", ".join(sorted({lib.date_only(r["election_date"]) for r in res["public_funds"]}))))
        w("")
    w("## 6. Update cadence and amendments\n")
    c = data["cadence"]
    w("Transactions loaded per day (`data_loaded_at`):\n")
    w(lib.md_table(["Loaded", "Rows", "Filings"], [[lib.date_only(r["data_loaded_at"]), r["n"], r["filings"]] for r in c["loaded_by_day"]]))
    w("\nFilings received per day: " + ", ".join("%s: %s" % (lib.date_only(r["filing_date"]), r["n"]) for r in c["filed_by_day"]))
    w("\nSchedule A rows since 2024 by days between transaction and filing: " + json.dumps(c["tx_to_filing_lag"]))
    w("\nForm 460 reports first filed since 2022, counting only FiledAmendment submissions as amendments: " + json.dumps(c["amendments"]))
    w("\nForm 496 vs Schedule D overlap test since 2018: " + json.dumps(data["ie_overlap"]))
    w("\nForm 497 part 1 vs Schedule A overlap test since 2022: " + json.dumps(data["f497_overlap"]))
    w("\n## 7. Recognising the same donor\n")
    w("```json\n" + json.dumps(data["donors"], indent=1) + "\n```")
    return "\n".join(L) + "\n"


def main():
    started = time.time()
    data = {"datasets": profile_datasets()}
    data["as_of"] = next(d["max_loaded"] for d in data["datasets"] if d["id"] == TX)
    data["transactions"] = profile_transactions()
    data["filings"] = profile_filings()
    data["filers"] = profile_filers()
    all_filers = q_all(FILERS, **{"$select": "filer_nid,fppc_id,filer_name,filer_type,status,candidate_name"})
    data["officials"] = []
    for off in lib.OFFICIALS:
        res = profile_official(off, all_filers)
        res["rows"] = summarise_official(res)
        data["officials"].append(res)
        print("profiled", off["name"], file=sys.stderr)
    data["cadence"] = profile_cadence()
    data["ie_overlap"] = ie_overlap()
    data["f497_overlap"] = f497_overlap()
    data["donors"] = profile_donors(all_filers)
    text = render(data)
    with open(os.path.join(HERE, "data-profile.md"), "w") as fh:
        fh.write(text)
    with open(os.path.join(HERE, "data-profile.json"), "w") as fh:
        json.dump(data, fh, indent=1, default=str)
    print(text)
    print("elapsed %.0fs" % (time.time() - started), file=sys.stderr)


if __name__ == "__main__":
    main()
