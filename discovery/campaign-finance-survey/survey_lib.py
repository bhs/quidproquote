"""Pure helpers for the campaign finance survey (no network access).

Everything here is deterministic and unit-tested; profile.py does the querying.
"""

import re

# Current San Francisco elected officials in scope: the Mayor and the eleven
# supervisors. Sources: https://sfbos.org/ (supervisors), Ballotpedia's
# "San Francisco, California" page (Mayor Daniel Lurie, in office since
# 2025-01-08), Ballotpedia's 2026 Board of Supervisors page (Sherrill and Wong
# re-elected 2026-06-02 to serve through January 2027).
OFFICIALS = [
    {"name": "Daniel Lurie", "office": "Mayor", "district": "", "first": "Daniel", "last": "Lurie"},
    {"name": "Connie Chan", "office": "Supervisor", "district": "1", "first": "Connie", "last": "Chan"},
    {"name": "Stephen Sherrill", "office": "Supervisor", "district": "2", "first": "Stephen", "last": "Sherrill"},
    {"name": "Danny Sauter", "office": "Supervisor", "district": "3", "first": "Danny", "last": "Sauter"},
    {"name": "Alan Wong", "office": "Supervisor", "district": "4", "first": "Alan", "last": "Wong"},
    {"name": "Bilal Mahmood", "office": "Supervisor", "district": "5", "first": "Bilal", "last": "Mahmood"},
    {"name": "Matt Dorsey", "office": "Supervisor", "district": "6", "first": "Matt", "last": "Dorsey"},
    {"name": "Myrna Melgar", "office": "Supervisor", "district": "7", "first": "Myrna", "last": "Melgar"},
    {"name": "Rafael Mandelman", "office": "Supervisor", "district": "8", "first": "Rafael", "last": "Mandelman"},
    {"name": "Jackie Fielder", "office": "Supervisor", "district": "9", "first": "Jackie", "last": "Fielder"},
    {"name": "Shamann Walton", "office": "Supervisor", "district": "10", "first": "Shamann", "last": "Walton"},
    {"name": "Chyanne Chen", "office": "Supervisor", "district": "11", "first": "Chyanne", "last": "Chen"},
]

CANDIDATE_TYPES = {"Candidate or Officeholder", "470 [Officeholder]", "Person"}
PRIMARILY_FORMED_CANDIDATE = "Primarily Formed Candidate"
MEASURE_TYPE = "Primarily Formed Measure"

_OTHER_OFFICE = re.compile(
    r"dccc|democratic|county central|college|board of education|school board|"
    r"\bboe\b|\bbed\b|sheriff|district attorney|assembly|senate",
    re.I,
)
_CURRENT_OFFICE = re.compile(r"supervisor|mayor|officeholder", re.I)
_OPPOSING = re.compile(r"\bopposing\b|\boppose\b|\bagainst\b|\bno on\b", re.I)

_ORG_SUFFIXES = {
    "inc", "incorporated", "llc", "llp", "lp", "ltd", "corp", "corporation",
    "company", "co", "the", "of",
}
_ORG_COMMITTEE_WORDS = {"pac", "political", "action", "committee", "issues", "fund"}


def soql_quote(value):
    """Quote a string literal for SoQL."""
    return "'" + str(value).replace("'", "''") + "'"


def name_regexes(official):
    first, last = re.escape(official["first"]), re.escape(official["last"])
    return re.compile(
        r"\b%s\b.*\b%s\b|\b(mayor|supervisor|sup\.)\s+%s\b" % (first, last, last), re.I
    )


def match_filer(official, filer):
    """How a row of the Filers dataset relates to an official, or None.

    Returns 'strong' when candidate_name is the official's (Last, First...), or
    'weak' when a measure / officeholder committee only mentions the official
    by name in its own name. Callers must treat 'weak' as needing review.
    candidate_name is written 'Last, First ...' and sometimes 'Last, Legal Name
    (Preferred)', so the first three letters of the first name may appear
    anywhere after the comma.
    """
    cand = (filer.get("candidate_name") or "").upper()
    last_part, _, rest = cand.partition(",")
    if last_part.strip() == official["last"].upper() and re.search(
        r"\b" + re.escape(official["first"][:3].upper()), rest
    ):
        return "strong"
    ftype = filer.get("filer_type") or ""
    if ftype in (MEASURE_TYPE, "470 [Officeholder]", PRIMARILY_FORMED_CANDIDATE):
        if name_regexes(official).search(filer.get("filer_name") or ""):
            return "weak"
    return None


def classify_committee(filer, match):
    """Role of a committee relative to the official it was matched to."""
    ftype = filer.get("filer_type") or ""
    name = filer.get("filer_name") or ""
    if ftype == MEASURE_TYPE:
        return "ballot-measure committee naming the official"
    if ftype == PRIMARILY_FORMED_CANDIDATE:
        if _OPPOSING.search(name):
            return "primarily formed committee opposing the official"
        return "primarily formed committee supporting the official (or unspecified)"
    if match == "weak":
        return "officeholder committee naming the official"
    if _OTHER_OFFICE.search(name):
        return "official's committee for another office"
    if _CURRENT_OFFICE.search(name):
        return "official's own committee for Mayor/Supervisor"
    return "official's committee, office unclear from name"


def own_for_current_office(role):
    return role == "official's own committee for Mayor/Supervisor" or role == "officeholder committee naming the official"


def ie_name_matches(official, first_name, last_name):
    """Match a candidate named on an independent-expenditure / Schedule D row.

    Last name must match exactly (case-insensitive); first name must share the
    first three letters, which tolerates 'Conne' for 'Connie' but not 'Doug'.
    """
    if (last_name or "").strip().upper() != official["last"].upper():
        return False
    return (first_name or "").strip().upper()[:3] == official["first"][:3].upper()


def _clean(text):
    text = (text or "").lower().replace("&", " and ")
    text = re.sub(r"\(.*?\)", " ", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return text.split()


def normalize_org(name, aggressive=False):
    """Normalized key for an organisation name.

    Level 1 lowercases, drops punctuation, parenthetical notes and corporate
    suffixes. Level 2 (aggressive) also drops PAC / committee wording, which
    merges a company with its political committee: an identity choice, not a fact.
    """
    drop = set(_ORG_SUFFIXES)
    if aggressive:
        drop |= _ORG_COMMITTEE_WORDS
    words = [w for w in _clean(name) if w not in drop]
    return " ".join(words)


def normalize_person(last, first):
    """Normalized (last, first) key: lowercase letters only, first token of first name."""
    last_key = "".join(_clean(last))
    first_tokens = _clean(first)
    first_key = first_tokens[0] if first_tokens else ""
    return last_key, first_key


def zip5(value):
    digits = re.sub(r"\D", "", value or "")
    return digits[:5] if len(digits) >= 5 else ""


def percentile(sorted_values, pct):
    """Nearest-rank percentile of an ascending list; None when empty."""
    if not sorted_values:
        return None
    rank = max(1, int(round(pct / 100.0 * len(sorted_values) + 0.4999999)))
    return sorted_values[min(rank, len(sorted_values)) - 1]


def money(value):
    if value is None:
        return "-"
    return "${:,.0f}".format(float(value))


def num(value):
    if value is None:
        return "-"
    return "{:,}".format(int(float(value)))


def date_only(value):
    return (value or "")[:10] or "-"


def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out)
