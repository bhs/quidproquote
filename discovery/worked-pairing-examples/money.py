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
DONOR_NAME_WORDS = {
    "San Francisco Chamber of Commerce": [["SAN FRANCISCO CHAMBER OF COMMERCE"], ["SF CHAMBER"], ["SF FORWARD"]],
    "GrowSF": [["GROWSF"], ["GROW SF"]],
    "SEIU Local 1021": [["SEIU", "1021"]],
    "Neighbors for a Better San Francisco (Blueprint)": [["NEIGHBORS FOR A BETTER SAN FRANCISCO"]],
    "San Francisco Police Officers Association": [["POLICE OFFICERS ASSOCIATION"], ["SFPOA"]],
    "Airbnb": [["AIRBNB"]],
}


def name_words_text(donor):
    return "; ".join(" + ".join(words) for words in DONOR_NAME_WORDS[donor])


def fetch_money(donor, filer_nids, timeout=90):
    """{'rows', 'url', 'error', 'data_loaded_at'} for one donor over a set of committees."""
    words = DONOR_NAME_WORDS.get(donor)
    if not words:
        return {"rows": [], "url": None, "error": "no name words defined for %s" % donor, "data_loaded_at": None}
    url = pl.DATASET_URL + "?" + urllib.parse.urlencode(pl.build_money_query(words, sorted(filer_nids)))
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/json"}),
                                    timeout=timeout) as resp:
            rows = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return {"rows": [], "url": url, "error": "%s: %s" % (type(exc).__name__, exc), "data_loaded_at": None}
    if not isinstance(rows, list):
        return {"rows": [], "url": url, "error": "unexpected reply: %s" % str(rows)[:200], "data_loaded_at": None}
    loaded = max(((r.get("data_loaded_at") or "")[:10] for r in rows), default="") or None
    return {"rows": rows, "url": url, "error": None, "data_loaded_at": loaded}


def today():
    return datetime.date.today().isoformat()
