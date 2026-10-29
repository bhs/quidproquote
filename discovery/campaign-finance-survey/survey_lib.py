"""Pure helpers for the campaign finance survey (no network access).

Everything here is deterministic and unit-tested; profile.py does the querying.
"""

import re

# Current San Francisco elected officials in scope: the Mayor and the eleven
# supervisors. Sources: the Board of Supervisors member listing on sfbos.org
# (a search-result excerpt of the page, 11 members by district) and
# https://www.sf.gov/profile--daniel-lurie (Mayor).
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


def committee_id_shape(value):
    """Kind of identifier written in a contribution's committee_id field.

    'state' is 6-7 digits (an FPPC / California filer id), 'fec' is the federal
    form C plus digits, anything else (Pending, N/A, SFO..., payment-app names)
    is 'other'.
    """
    v = (value or "").strip()
    if re.fullmatch(r"\d{6,7}", v):
        return "state"
    if re.fullmatch(r"C\d{8}", v):
        return "fec"
    return "other"


def resolve_committee_ids(dollars_by_id, by_id, by_xref, examples=8):
    """Look unresolved committee ids up in the state's filer records.

    `dollars_by_id` maps committee_id to Schedule A dollars. Only 'state' shaped
    ids can be looked up: directly as a filer id, or as a legacy cross-reference.
    """
    shapes = {}
    for cid, dollars in dollars_by_id.items():
        d = shapes.setdefault(committee_id_shape(cid), {"ids": 0, "dollars": 0.0})
        d["ids"] += 1
        d["dollars"] += dollars
    direct = xref = missing = 0
    found_dollars = 0.0
    types, statuses, found = {}, {}, []
    sponsored = 0
    for cid, dollars in dollars_by_id.items():
        if committee_id_shape(cid) != "state":
            continue
        key = cid.strip()
        if key in by_id:
            rec, how = by_id[key], "filer id"
            direct += 1
        elif key in by_xref and by_xref[key] in by_id:
            rec, how = by_id[by_xref[key]], "legacy cross-reference id"
            xref += 1
        else:
            missing += 1
            continue
        found_dollars += dollars
        types[rec["type"]] = types.get(rec["type"], 0) + 1
        statuses[rec["status"]] = statuses.get(rec["status"], 0) + 1
        if "sponsored by" in rec["name"].lower():
            sponsored += 1
        found.append({"committee_id": cid, "dollars": dollars, "found_as": how, "state_type": rec["type"],
                      "state_status": rec["status"], "state_name": rec["name"]})
    found.sort(key=lambda r: -r["dollars"])
    return {
        "shapes": shapes,
        "state_ids_found_as_filer_id": direct,
        "state_ids_found_as_legacy_xref": xref,
        "state_ids_not_found": missing,
        "dollars_of_found_state_ids": found_dollars,
        "found_by_state_filer_type": dict(sorted(types.items(), key=lambda kv: -kv[1])),
        "found_by_state_status": dict(sorted(statuses.items(), key=lambda kv: -kv[1])),
        "found_names_saying_sponsored_by": sponsored,
        "largest_found": found[:examples],
    }


def percentile(sorted_values, pct):
    """Nearest-rank percentile of an ascending list; None when empty."""
    if not sorted_values:
        return None
    rank = max(1, int(round(pct / 100.0 * len(sorted_values) + 0.4999999)))
    return sorted_values[min(rank, len(sorted_values)) - 1]


def summarise_amendments(rows, since):
    """Amendment behaviour of reports first submitted on or after `since`.

    `rows` are submissions (filing_nid, filing_date, filing_type, mechanism_type).
    A report is the set of submissions sharing a filing_nid; its first filing date
    is its earliest submission. Only FiledAmendment submissions count as
    amendments: AttachmentsAdded and ContentsChanged carry no new transaction data
    and are counted separately. Lag is days from the first submission to the last
    FiledAmendment.
    """
    reports = {}
    for r in rows:
        reports.setdefault(r["filing_nid"], []).append(r)
    cohort = amended = other_only = paper_amend = 0
    no_original = 0
    per_report, lags = {}, []
    for subs in reports.values():
        dates = sorted((s["filing_date"] or "")[:10] for s in subs)
        if dates[0] < since:
            continue
        cohort += 1
        if not any(s.get("filing_type") == "FiledOriginal" for s in subs):
            no_original += 1
        amends = [s for s in subs if s.get("filing_type") == "FiledAmendment"]
        others = [s for s in subs if s.get("filing_type") in ("AttachmentsAdded", "ContentsChanged")]
        if not amends:
            if others:
                other_only += 1
            continue
        amended += 1
        per_report[len(amends)] = per_report.get(len(amends), 0) + 1
        if any(s.get("mechanism_type") == "Paper" for s in amends):
            paper_amend += 1
        last = max((s["filing_date"] or "")[:10] for s in amends)
        lags.append(days_between(dates[0], last))
    lags.sort()
    return {
        "since": since,
        "form460_reports_first_filed_since": cohort,
        "reports_with_a_filed_amendment": amended,
        "filed_amendments_per_amended_report": dict(sorted(per_report.items())),
        "reports_with_only_attachments_or_contents_changes": other_only,
        "reports_without_a_filed_original_row": no_original,
        "amended_reports_with_a_paper_amendment": paper_amend,
        "days_first_to_last_amendment_p50": percentile(lags, 50),
        "days_first_to_last_amendment_p90": percentile(lags, 90),
        "days_first_to_last_amendment_max": lags[-1] if lags else None,
        "amended_over_365_days": sum(1 for x in lags if x > 365),
    }


def days_between(first, last):
    """Whole days from one YYYY-MM-DD date to a later one."""
    import datetime
    a = datetime.date.fromisoformat(first)
    b = datetime.date.fromisoformat(last)
    return (b - a).days


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
