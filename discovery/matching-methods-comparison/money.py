"""Money by committee: what a donor reported giving to the committees tied to current officials.

Reads the San Francisco Ethics Commission's campaign finance Transactions dataset on DataSF
(public, no key) with one aggregate query per donor. Name-based: the dataset has no donor
identifier, so a donor is found by words in the contributor's name. Schedule A (monetary
contributions) only, per committee, never summed across committees or forms. It says nothing
about why anyone gave or what they got.
"""

import datetime
import json
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://data.sf.gov/resource/pitq-e56w.json"

# Words that must all appear (upper-cased) in the contributor's last-name field, one list per
# spelling. A match by name can include other people or organisations with the same words.
DONOR_NAME_WORDS = {
    "San Francisco Chamber of Commerce": [["SAN FRANCISCO CHAMBER OF COMMERCE"], ["SF CHAMBER"], ["SF FORWARD"]],
    "GrowSF": [["GROWSF"], ["GROW SF"]],
    "SEIU Local 1021": [["SEIU", "1021"]],
    "Neighbors for a Better San Francisco (Blueprint)": [["NEIGHBORS FOR A BETTER SAN FRANCISCO"]],
    "San Francisco Police Officers Association": [["POLICE OFFICERS ASSOCIATION"], ["SFPOA"]],
    "Airbnb": [["AIRBNB"]],
}


def _lit(s):
    return "'" + s.replace("'", "''") + "'"


def build_query(name_words, filer_nids):
    """The SoQL parameters for one donor over a set of committees."""
    groups = []
    for words in name_words:
        groups.append("(" + " AND ".join("upper(transaction_last_name) like %s" % _lit("%" + w + "%")
                                         for w in words) + ")")
    where = "form_type='A' AND filer_nid in (%s) AND (%s)" % (
        ",".join(_lit(n) for n in filer_nids), " OR ".join(groups))
    return {
        "$select": "filer_nid, sum(calculated_amount) as total, count(*) as n, "
                   "min(calculated_date) as first, max(calculated_date) as last",
        "$where": where,
        "$group": "filer_nid",
        "$limit": "5000",
    }


def parse_rows(rows):
    out = []
    for r in rows:
        out.append({"filer_nid": str(r.get("filer_nid")), "filer_name": r.get("filer_name", ""),
                    "total": float(r.get("total") or 0.0), "n": int(float(r.get("n") or 0)),
                    "first": (r.get("first") or "")[:10], "last": (r.get("last") or "")[:10]})
    return sorted(out, key=lambda r: -r["total"])


def committee_index(committees_doc):
    """{filer_nid: {official, office, district, committee info}} from data/committees.json."""
    idx = {}
    for o in committees_doc["officials"]:
        for c in o["committees"]:
            idx[str(c["filer_nid"])] = {"official": o["name"], "office": o["office"],
                                        "district": o["district"], **c}
    return idx


def fetch(donors, committees_doc, timeout=60):
    """{donor: {'rows': [...], 'url': str, 'error': str|None}} plus the retrieval date."""
    idx = committee_index(committees_doc)
    result = {}
    for donor in donors:
        words = DONOR_NAME_WORDS.get(donor)
        if not words:
            result[donor] = {"rows": [], "url": None, "error": "no name words defined for this donor"}
            continue
        url = BASE + "?" + urllib.parse.urlencode(build_query(words, sorted(idx)))
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/json"}),
                                        timeout=timeout) as resp:
                rows = parse_rows(json.loads(resp.read().decode("utf-8")))
            for r in rows:
                r.update({k: v for k, v in idx.get(r["filer_nid"], {}).items() if k != "filer_nid"})
                r["filer_name"] = idx.get(r["filer_nid"], {}).get("filer_name") or r["filer_name"] or r["filer_nid"]
            result[donor] = {"rows": rows, "url": url, "error": None}
        except (urllib.error.URLError, OSError, ValueError) as exc:
            result[donor] = {"rows": [], "url": url, "error": "%s: %s" % (type(exc).__name__, exc)}
    return result, datetime.date.today().isoformat()
