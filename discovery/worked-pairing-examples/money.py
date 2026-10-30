"""The one part of the worked pairings that reaches the network: the Ethics Commission's campaign
finance Transactions dataset on DataSF (public, no key).

One query per donor and official, over the committees tied to that official. A failed query is
reported, never replaced by an empty answer.
"""

import datetime
import json
import urllib.error
import urllib.parse
import urllib.request

import pairing_lib as pl

# Words that must all appear (upper-cased) in the contributor's name, one list per spelling. As in
# the matching methods comparison; a match by name can include other organisations with the same words.
# The names these words catch and miss are read from the dataset itself by fetch_census (written up under
# "Names read in the filings" in pairings.md). The same words are applied to a committee's name when
# looking for the independent expenditures it reported.
DONOR_NAME_WORDS = {
    "San Francisco Chamber of Commerce": [["SAN FRANCISCO CHAMBER OF COMMERCE"], ["SF CHAMBER"], ["SF FORWARD"]],
    "GrowSF": [["GROWSF"], ["GROW SF"]],
    "SEIU Local 1021": [["SEIU", "1021"]],
    "Neighbors for a Better San Francisco (Blueprint)": [["NEIGHBORS FOR A BETTER SAN FRANCISCO"]],
    "San Francisco Police Officers Association": [["POLICE OFFICERS ASSOCIATION"], ["SFPOA"]],
    "Airbnb": [["AIRBNB"]],
}


# Looser patterns, any one of which puts a name in the census of names read in the filings.
NEAR_PATTERNS = {
    "San Francisco Chamber of Commerce": ["CHAMBER OF COMMERCE", "SF FORWARD", "SAN FRANCISCO FORWARD"],
    "GrowSF": ["GROWSF", "GROW SF", "GROW SAN FRANCISCO"],
    "SEIU Local 1021": ["SEIU"],
    "Neighbors for a Better San Francisco (Blueprint)": ["NEIGHBORS FOR A BETTER", "BLUEPRINT"],
    "San Francisco Police Officers Association": ["POLICE OFFICERS ASSOC", "SFPOA"],
    "Airbnb": ["AIRBNB"],
}


def name_words_text(donor):
    return "; ".join(" + ".join(words) for words in DONOR_NAME_WORDS[donor])


def _query(params, timeout=90):
    """(rows, url, error): the rows of one DataSF query. A failure is returned as error, never as no rows."""
    url = pl.DATASET_URL + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/json"}),
                                    timeout=timeout) as resp:
            rows = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return [], url, "%s: %s" % (type(exc).__name__, exc)
    if not isinstance(rows, list):
        return [], url, "unexpected reply: %s" % str(rows)[:200]
    return rows, url, None


def fetch_money(donor, filer_nids, timeout=90):
    """{'rows', 'url', 'error', 'data_loaded_at'} for one donor over a set of committees."""
    words = DONOR_NAME_WORDS.get(donor)
    if not words:
        return {"rows": [], "url": None, "error": "no name words defined for %s" % donor, "data_loaded_at": None}
    rows, url, error = _query(pl.build_money_query(words, sorted(filer_nids)), timeout)
    if error:
        return {"rows": [], "url": url, "error": error, "data_loaded_at": None}
    loaded = max(((r.get("data_loaded_at") or "")[:10] for r in rows), default="") or None
    return {"rows": rows, "url": url, "error": None, "data_loaded_at": loaded}


def fetch_independent(donor, surname, timeout=90):
    """{'rows', 'url', 'error'}: independent expenditure reports naming the surname, filed by committees named like the donor."""
    words = DONOR_NAME_WORDS.get(donor)
    if not words:
        return {"rows": [], "url": None, "error": "no name words defined for %s" % donor}
    rows, url, error = _query(pl.build_independent_query(words, surname), timeout)
    return {"rows": rows, "url": url, "error": error}


def fetch_control(filer_nids, timeout=90):
    """{'by_committee': {filer_nid: Schedule A row count}, 'url', 'error'}."""
    rows, url, error = _query(pl.build_control_query(sorted(filer_nids)), timeout)
    if error:
        return {"by_committee": {}, "url": url, "error": error}
    return {"by_committee": {str(r["filer_nid"]): int(r["rows_a"]) for r in rows},
            "url": url, "error": None}


def fetch_loose(donor, filer_nids, surname, given, timeout=90):
    """How many rows the looser patterns of NEAR_PATTERNS find where the name words found none or some:
    contributions to the committees and independent expenditure rows naming the official."""
    patterns = NEAR_PATTERNS.get(donor)
    if not patterns:
        return {"error": "no patterns defined for %s" % donor}
    words = [[w] for w in patterns]
    contrib, url1, err1 = _query(pl.build_money_query(words, sorted(filer_nids)), timeout)
    ind, url2, err2 = _query(pl.build_independent_query(words, surname), timeout)
    if err1 or err2:
        return {"error": err1 or err2}
    named = [r for r in ind if pl.names_official(r.get("candidate_last_name"), surname, given)]
    others, url3, err3 = _query(pl.build_surname_committees_query(surname), timeout)
    if err3:
        return {"error": err3}
    known = {str(n) for n in filer_nids}
    unlisted = sorted({(str(r["filer_nid"]), r["filer_name"], r.get("filer_type", "")) for r in others
                       if str(r["filer_nid"]) not in known})
    return {"error": None, "patterns": patterns, "contribution_rows": len(contrib),
            "independent_rows": len(named), "urls": [url1, url2],
            "unlisted_committees": [{"filer_nid": a, "filer_name": b, "filer_type": c} for a, b, c in unlisted],
            "unlisted_url": url3}


def fetch_census(donor, timeout=90):
    """The contributor names and committee names the dataset holds that look like the donor, each marked
    with whether the donor's name words match it."""
    patterns = NEAR_PATTERNS.get(donor)
    words = DONOR_NAME_WORDS.get(donor)
    if not patterns or not words:
        return {"error": "no patterns defined for %s" % donor}
    q_contrib, q_comm = pl.build_census_queries(patterns)
    contributors, url1, err1 = _query(q_contrib, timeout)
    committees, url2, err2 = _query(q_comm, timeout)
    if err1 or err2:
        return {"error": err1 or err2}
    for r in contributors:
        r["used"] = pl.name_matches(words, r["name"])
    for r in committees:
        r["used"] = pl.name_matches(words, r["filer_name"])
    return {"error": None, "patterns": patterns, "urls": [url1, url2],
            "contributors": contributors, "committees": committees}


def today():
    return datetime.date.today().isoformat()
