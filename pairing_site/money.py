"""The money beside a pairing: what a donor gave through the committees tied to an official, per committee and
filing, and the outside spending that names the official, kept apart.

Adapted from ff_lib.pair_money and ff_lib.outside_spending (discovery/funder-first-pairings) and the DataSF
queries of discovery/official-funding-map/collect.py, now reading and writing the site's database.

Schedule A rows are counted once: identical rows are dropped, and a 24-hour report (form 497 part 1) that
repeats a Schedule A row is listed and not counted. A 24-hour report with no Schedule A row is listed apart with
its own total. Totals are per committee and never added across committees. Outside spending (form 496) is kept
apart and never added to a gift.
"""

import collections
import json

from . import db
from . import fmap_lib as fl

TIED = ("own", "own-other", "measure")  # the official's own committees and ballot-measure committees carrying the name
ROW_FIELDS = ("filer_nid, form_type, filing_id_number, filing_version, filing_date, calculated_date, "
              "calculated_amount, committee_id, entity_code, transaction_first_name as fn, "
              "transaction_last_name as ln")


# --------------------------------------------------------------------------- donors as families

def family_of_donor(d):
    """A donor row as the dict fmap_lib's family matching reads."""
    return {"key": d["key"], "name": d["name"], "patterns": json.loads(d["patterns"]),
            "exclude": json.loads(d["exclude"] or "[]"), "committee_ids": json.loads(d["committee_ids"] or "[]")}


def all_families(conn):
    return [family_of_donor(d) for d in conn.execute("SELECT * FROM donors ORDER BY id")]


# --------------------------------------------------------------------------- storing rows

def key_a(filer, date, amt):
    return (filer, (date or "")[:10], round(float(amt or 0), 2))


def replace_contributions(conn, donor, rows):
    """Replace the donor's stored rows with `rows` (DataSF rows as the Transactions dataset gives them). Only
    rows the donor's names take, in committees of the roster, are kept. Returns the number stored."""
    fams = all_families(conn)
    key = donor["key"]
    nids = {r["filer_nid"] for r in conn.execute("SELECT filer_nid FROM committees")}
    keep = []
    for r in rows:
        if r["filer_nid"] not in nids or r.get("form_type") not in ("A", "F497P1"):
            continue
        name = fl.donor_name(r)
        if fl.family_of(fams, name, r.get("committee_id"))[0] != key:
            continue
        keep.append((donor["id"], r["filer_nid"], r["form_type"], str(r["filing_id_number"]),
                     str(r.get("filing_version") or ""), fl.day(r.get("filing_date")), fl.day(r["calculated_date"]),
                     float(r["calculated_amount"]), r.get("committee_id") or "", name, r.get("entity_code") or ""))
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute("DELETE FROM contributions WHERE donor_id=?", (donor["id"],))
        conn.executemany(
            "INSERT INTO contributions (donor_id, filer_nid, form_type, filing_id_number, filing_version, filing_date, "
            "contribution_date, amount, committee_id, giver_name, entity_code) VALUES (?,?,?,?,?,?,?,?,?,?,?)", keep)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return len(keep)


def outside_rows(conn, raw):
    """The outside-spending rows to store: form 496 rows naming an official, by committees a donor's names take.
    A bare-surname row counts only when its district is blank or the official's (or the office is Mayor)."""
    fams = all_families(conn)
    donors = {d["key"]: d["id"] for d in conn.execute("SELECT id, key FROM donors")}
    officials = list(conn.execute("SELECT * FROM officials"))
    agg = {}
    for r in raw:
        fam = fl.family_of(fams, r["filer_name"])[0]
        if fam is None:
            continue
        for o in officials:
            if not fl.names_official(r["candidate_last_name"], o["surname"], o["given"]):
                continue
            dist = (r.get("district_number") or "").strip()
            if dist and o["district"] and dist != o["district"]:
                continue
            office = (r.get("office_description") or "").upper()
            if o["office"] == "Mayor" and "SUPERVISOR" in office:
                continue
            if o["office"] != "Mayor" and "MAYOR" in office:
                continue
            a = agg.setdefault((o["id"], donors[fam], r["filer_nid"], r["support_oppose_code"]), {
                "payer": r["filer_name"], "amount": 0.0, "filings": set(), "first": "9999", "last": ""})
            a["amount"] += float(r["amt"])
            a["filings"].add(r["filing_id_number"])
            a["first"] = min(a["first"], fl.day(r["d0"]))
            a["last"] = max(a["last"], fl.day(r["d1"]))
    return [(donor_id, oid, nid, a["payer"], "supporting" if code == "S" else "opposing", a["amount"],
             json.dumps(sorted(a["filings"])), a["first"], a["last"])
            for (oid, donor_id, nid, code), a in sorted(agg.items())]


def replace_outside(conn, raw):
    rows = outside_rows(conn, raw)
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute("DELETE FROM independent_spending")
        conn.executemany(
            "INSERT INTO independent_spending (donor_id, official_id, payer_nid, payer, stance, amount, filings, "
            "first_date, last_date) VALUES (?,?,?,?,?,?,?,?,?)", rows)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return len(rows)


def replace_filer_records(conn, records):
    """records: {fppc_id: filer_name}."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute("DELETE FROM filer_records")
        conn.executemany("INSERT INTO filer_records (fppc_id, filer_name) VALUES (?, ?)", sorted(records.items()))
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


# --------------------------------------------------------------------------- reading a pair's money

def funded_official_ids(conn, donor_id):
    """The officials the donor gave Schedule A money to through a committee tied to them."""
    q = ("SELECT DISTINCT c.official_id AS id FROM contributions k JOIN committees c ON c.filer_nid = k.filer_nid "
         "WHERE k.donor_id = ? AND k.form_type = 'A' AND c.relation IN (%s)" % ",".join("?" * len(TIED)))
    return {r["id"] for r in conn.execute(q, (donor_id,) + TIED)}


def _row(r):
    return {"filer_nid": r["filer_nid"], "form_type": r["form_type"], "filing_id_number": r["filing_id_number"],
            "filing_version": r["filing_version"], "filing_date": r["filing_date"],
            "calculated_date": r["contribution_date"], "calculated_amount": r["amount"],
            "committee_id": r["committee_id"], "entity_code": r["entity_code"], "fn": "", "ln": r["giver_name"]}


def pair_money(conn, official_id, donor_id):
    """The donor's Schedule A money beside an official, per receiving committee tied to the official and per
    filing: {per: {filer_nid: {committee, kind, a, a_sum, repeat, only, only_sum}}, dropped}."""
    mine = {c["filer_nid"]: dict(c) for c in conn.execute(
        "SELECT * FROM committees WHERE official_id=? ORDER BY filer_name", (official_id,)) if c["relation"] in TIED}
    rows = [_row(r) for r in conn.execute("SELECT * FROM contributions WHERE donor_id=? ORDER BY contribution_date, id",
                                          (donor_id,)) if r["filer_nid"] in mine]
    a_keys = {key_a(r["filer_nid"], r["calculated_date"], r["calculated_amount"]) for r in rows if r["form_type"] == "A"}
    per = collections.OrderedDict()
    dropped = []
    for nid, c in mine.items():
        mrows = [r for r in rows if r["filer_nid"] == nid]
        if not mrows:
            continue
        seen, counted = {}, []
        for r in (x for x in mrows if x["form_type"] == "A"):
            k = (r["calculated_date"][:10], round(float(r["calculated_amount"]), 2), fl.donor_name(r).upper())
            if k in seen:
                dropped.append({"row": r, "repeats_filing": seen[k]})
                continue
            seen[k] = r["filing_id_number"]
            counted.append(r)
        h = [r for r in mrows if r["form_type"] == "F497P1"]
        rep = [r for r in h if key_a(nid, r["calculated_date"], r["calculated_amount"]) in a_keys]
        only = [r for r in h if r not in rep]
        per[nid] = {"committee": c, "a": counted, "a_sum": sum(float(r["calculated_amount"]) for r in counted),
                    "repeat": rep, "only": only, "only_sum": sum(float(r["calculated_amount"]) for r in only)}
    return {"per": per, "dropped": dropped}


def outside_for(conn, official_id, donor_id):
    return [dict(r, filings=json.loads(r["filings"])) for r in conn.execute(
        "SELECT * FROM independent_spending WHERE official_id=? AND donor_id=? ORDER BY amount DESC",
        (official_id, donor_id))]


# --------------------------------------------------------------------------- fetching from DataSF

def fetch_donor_rows(conn, donor):
    """Every Schedule A and 24-hour row under the donor's names in the roster's committees (DataSF)."""
    nids = [r["filer_nid"] for r in conn.execute("SELECT filer_nid FROM committees ORDER BY filer_nid")]
    clause = fl.family_clause("transaction_last_name", family_of_donor(donor), "committee_id")
    return fl.query_all(fl.TRANSACTIONS, {
        "$select": ROW_FIELDS,
        "$where": "form_type in ('A','F497P1') AND filer_nid in (%s) AND %s" % (fl.in_list(nids), clause),
        "$order": "filer_nid, calculated_date, filing_id_number"})


def fetch_outside_raw(conn):
    """Form 496 rows naming any official of the roster (DataSF)."""
    surnames = sorted({r["surname"] for r in conn.execute("SELECT surname FROM officials")})
    like = " OR ".join("upper(candidate_last_name) like %s" % fl.lit("%" + s.upper() + "%") for s in surnames)
    return fl.query_all(fl.TRANSACTIONS, {
        "$select": "filer_nid, filer_name, filing_id_number, filing_date, filing_version, candidate_last_name, "
                   "candidate_first_name, support_oppose_code, office_code, office_description, district_number, "
                   "count(*) as n, sum(calculated_amount) as amt, min(calculated_date) as d0, max(calculated_date) as d1",
        "$where": "form_type='F496' AND (%s)" % like,
        "$group": "filer_nid, filer_name, filing_id_number, filing_date, filing_version, candidate_last_name, "
                  "candidate_first_name, support_oppose_code, office_code, office_description, district_number",
        "$order": "filer_nid, filing_id_number, candidate_last_name, candidate_first_name"})


def fetch_filer_records(conn):
    """The Filers dataset's record for each FPPC id the stored rows carry."""
    ids = sorted({r["committee_id"] for r in conn.execute(
        "SELECT DISTINCT committee_id FROM contributions WHERE committee_id != ''")})
    out = {}
    for i in range(0, len(ids), 120):
        for r in fl.query(fl.FILERS, {"$where": "fppc_id in (%s)" % fl.in_list(ids[i:i + 120]), "$limit": "2000"}):
            out.setdefault(r["fppc_id"], r.get("filer_name", ""))
    return out


def refresh_money(conn):
    """Re-read every donor's filings from DataSF, one request at a time. Raises fl.QueryError on a failed query:
    what was stored before stays, and nothing stands in for the missing answer. Returns a summary string."""
    donors = list(conn.execute("SELECT * FROM donors ORDER BY id"))
    fetched = [(d, fetch_donor_rows(conn, d)) for d in donors]
    raw = fetch_outside_raw(conn)
    loaded = fl.query(fl.TRANSACTIONS, {"$select": "max(data_loaded_at) as m"})[0]["m"][:10]
    total = sum(replace_contributions(conn, d, rows) for d, rows in fetched)
    outside = replace_outside(conn, raw)
    replace_filer_records(conn, fetch_filer_records(conn))
    db.set_meta(conn, "money_retrieved", fl.today())
    db.set_meta(conn, "money_loaded_through", loaded)
    return "%d filing rows for %d donors, %d outside-spending groups; data loaded through %s" % (
        total, len(donors), outside, loaded)
