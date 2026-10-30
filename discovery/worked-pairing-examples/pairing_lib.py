"""Pure functions for the worked pairings: quotes, speaker evidence, money rules and the write-up.

No network and no third-party packages. build_pairings.py drives these; money.py holds the one
part that reaches the network. Nothing here says why anyone gave money or spoke.
"""

import json
import os
import re

import compare_lib as cl
import trial_lib as lib

DATASET_URL = "https://data.sf.gov/resource/pitq-e56w.json"
DATASET_PAGE = "https://data.sf.gov/d/pitq-e56w"

# The settings at which the matching trial found chance under one pair per run, per way.
CALIBRATED = {"tfidf": 0.25, "phrase": 2, "anchor": 3, "both": 0.20}

NO_CAUSATION = ("Two things shown side by side for a reporter to check. Nothing here says why anyone "
                "gave money or said anything, or that one led to the other.")

# Words a lead must never use about the money and the words (checked by the tests).
CAUSAL_WORDS = ("because of the money", "in return", "bought", "paid for", "influence", "caused",
                "quid pro quo", "in exchange", "thanks to", "payoff", "pay-to-play", "result of")


# --------------------------------------------------------------------------- transcript

def load_rows(data_dir, meeting_id):
    """[(stamp, text)] for one caption transcript, as published."""
    rows = []
    with open(os.path.join(data_dir, "transcripts", "%d.tsv" % meeting_id), encoding="utf-8") as f:
        for line in f:
            stamp, _, text = line.rstrip("\n").partition("\t")
            rows.append((stamp, " ".join(text.split())))
    return rows


def extract_quote(rows, start, end, begin_at=None, end_at=None):
    """The words of the caption rows from stamp `start` to `end`, exactly as published.

    begin_at / end_at cut the first and last row at a phrase that must occur in them. A leading
    '>>' (the captions' speaker-change mark) is dropped. Returns text and the stamps of the rows
    holding its first and last word. Raises ValueError when anything asked for is not there.
    """
    sel = [(s, t) for s, t in rows if start <= s <= end]
    if not sel:
        raise ValueError("no caption rows between %s and %s" % (start, end))
    joined, offsets = "", []
    for s, t in sel:
        offsets.append((len(joined), s))
        joined += t + " "
    b, e = 0, len(joined.rstrip())
    if begin_at:
        b = joined.find(begin_at)
        if b < 0:
            raise ValueError("begin_at %r not found" % begin_at)
    if end_at:
        i = joined.find(end_at, b)
        if i < 0:
            raise ValueError("end_at %r not found" % end_at)
        e = i + len(end_at)
    while b < e and joined[b] in "> ":
        b += 1
    text = joined[b:e].strip()
    first = [s for off, s in offsets if off <= b][-1]
    last = [s for off, s in offsets if off <= max(e - 1, 0)][-1]
    return {"text": text, "first_stamp": first, "last_stamp": last}


def is_verbatim(rows, text):
    """True when `text` occurs word for word in the transcript's caption text."""
    whole = " ".join(t for _, t in rows)
    return text in whole


def cue_rows(rows, stamps):
    """[(stamp, text)] for each stamp asked for; ValueError if a stamp is not in the transcript."""
    out = []
    for stamp in stamps:
        hits = [(s, t) for s, t in rows if s == stamp]
        if not hits:
            raise ValueError("stamp %s not in the transcript" % stamp)
        out.extend(hits)
    return out


def auto_speaker(rows, first_stamp, text, roster):
    """What the spoken-cue rule of the comparison proposes for this passage (a proposal only)."""
    idx = next(i for i, (s, _) in enumerate(rows) if s == first_stamp)
    return cl.propose_speaker(cl.words_before(rows, idx), text, roster)


# --------------------------------------------------------------------------- matching evidence

def lexical_context(quotes, priorities):
    q_tokens = [lib.tokenize(q["text"]) for q in quotes]
    return lib.Context(priorities, q_tokens)


def lexical_evidence(ctx, priorities, text, priority_id):
    """Scores of one pair under the trial's three lexical ways and which calibrated settings it clears."""
    pi = next(i for i, p in enumerate(priorities) if p["id"] == priority_id)
    s = cl.lexical_scores(ctx, text, pi)
    clears = {
        "tfidf": s["tfidf"] >= CALIBRATED["tfidf"],
        "phrase": s["phrase"] >= CALIBRATED["phrase"],
        "anchor": s["anchor"] >= CALIBRATED["anchor"],
        "both": s["tfidf"] >= CALIBRATED["both"] and s["phrase"] >= 1,
    }
    return {"scores": {k: round(v, 3) for k, v in s.items()}, "clears": clears}


# --------------------------------------------------------------------------- committees and money

def committee_role(committee):
    """own | support | oppose | third_party | measure | other, from the filer type and the name."""
    ftype = committee.get("filer_type", "")
    name = committee.get("filer_name", "").lower()
    if ftype in ("Candidate or Officeholder", "470 [Officeholder]"):
        return "own"
    if ftype == "Primarily Formed Candidate":
        if "oppos" in name:
            return "oppose"
        if "support" in name:
            return "support"
        return "third_party"
    if ftype == "Primarily Formed Measure":
        return "measure"
    return "other"


ROLE_TEXT = {
    "own": "the official's own candidate or officeholder committee",
    "support": "a committee formed to support the official (not controlled by the official)",
    "oppose": "a committee formed to oppose the official (money against, not for)",
    "third_party": "a committee formed about the official, support or oppose not stated in its name",
    "measure": "a ballot-measure committee naming the official",
    "other": "a committee of another kind",
}


def official_committees(committees_doc, name):
    for o in committees_doc["officials"]:
        if o["name"] == name:
            return o, [dict(c, role=committee_role(c)) for c in o["committees"]]
    raise KeyError(name)


def _lit(s):
    return "'" + s.replace("'", "''") + "'"


def build_money_query(name_words, filer_nids):
    """SoQL parameters: every Schedule A and 24-hour (497 part 1) row of the donor in these committees."""
    groups = ["(" + " AND ".join("upper(transaction_last_name) like %s" % _lit("%" + w + "%") for w in words) + ")"
              for words in name_words]
    where = "form_type in ('A','F497P1') AND filer_nid in (%s) AND (%s)" % (
        ",".join(_lit(str(n)) for n in filer_nids), " OR ".join(groups))
    return {
        "$select": "filer_nid, filer_name, form_type, filing_id_number, filing_date, filing_type, "
                   "filing_version, calculated_date, calculated_amount, transaction_first_name, "
                   "transaction_last_name, memo_code, data_loaded_at",
        "$where": where,
        "$order": "filer_nid, calculated_date",
        "$limit": "5000",
    }


def _amount(row):
    try:
        return round(float(row.get("calculated_amount") or 0.0), 2)
    except (TypeError, ValueError):
        return 0.0


def _is_memo(row):
    return str(row.get("memo_code", "")).lower() == "true"


def summarise_money(rows, committees):
    """Per committee: Schedule A rows that count, memo rows, 24-hour rows that repeat Schedule A
    and 24-hour rows with no Schedule A counterpart. Nothing is added across committees.

    Rules (campaign-finance survey, sections 3 and 4): Transactions holds only the latest
    submission of each report, so one reported contribution is one row; a 24-hour report repeats
    the Schedule A row of the periodic report that follows it (same committee, date and amount), so
    it never adds; a memo row is information inside another entry and is not summed.
    """
    by_committee = {}
    for c in committees:
        by_committee[str(c["filer_nid"])] = {"committee": c, "schedule_a": [], "memo": [],
                                             "repeats": [], "twentyfour_only": []}
    for r in rows:
        nid = str(r.get("filer_nid"))
        if nid not in by_committee:
            continue
        slot = by_committee[nid]
        if r.get("form_type") == "A":
            (slot["memo"] if _is_memo(r) else slot["schedule_a"]).append(r)
    for r in rows:
        nid = str(r.get("filer_nid"))
        if nid not in by_committee or r.get("form_type") != "F497P1":
            continue
        slot = by_committee[nid]
        key = ((r.get("calculated_date") or "")[:10], _amount(r))
        a_keys = {((a.get("calculated_date") or "")[:10], _amount(a)) for a in slot["schedule_a"] + slot["memo"]}
        (slot["repeats"] if key in a_keys else slot["twentyfour_only"]).append(r)
    for slot in by_committee.values():
        slot["schedule_a_total"] = round(sum(_amount(r) for r in slot["schedule_a"]), 2)
        slot["twentyfour_only_total"] = round(sum(_amount(r) for r in slot["twentyfour_only"]), 2)
    return by_committee


def dollars(x):
    return "${:,.2f}".format(x)


# --------------------------------------------------------------------------- write-up

def lead_text(p):
    """One neutral paragraph. It names what sits beside what and never says why."""
    return ("%s (%s%s) is recorded in the %s transcript of %s, at %s, saying the words in %s.1. "
            "The published statement from %s, in %s.3, is on the same subject (%s). "
            "%s.5 lists what contributors named like %s reported giving to committees tied to %s, "
            "by committee and filing. %s" % (
                p["official"], p["office"], (", District %s" % p["district"]) if p["district"] else "",
                p["body"], p["date"], p["time"], p["id_label"],
                p["donor"], p["id_label"], p["subject"], p["id_label"], p["donor"], p["official"],
                NO_CAUSATION))


def money_heading(p):
    return "Money %d: %s, contributions reported to committees tied to %s" % (p["n"], p["donor"], p["official"])


def render_money_section(p, money, retrieved):
    out = ["### " + money_heading(p), ""]
    out.append("Committees tied to the official (from `data/committees.json`; searched together in one query):")
    out.append("")
    for c in p["committees"]:
        out.append("- %s (filer %s, %s, %s): %s" % (c["filer_name"], c["filer_nid"], c["filer_type"],
                                                    c["status"].lower(), ROLE_TEXT[c["role"]]))
    out.append("")
    if money is None:
        out.append("**Not retrieved in this build.** Run `python build_pairings.py` with network access to the "
                   "Ethics Commission dataset to fill this section.")
        out.append("")
        return out
    if money.get("error"):
        out.append("**The money query failed:** `%s`. Nothing is shown in its place." % money["error"])
        out.append("")
        return out
    out.append("Source: San Francisco Ethics Commission campaign finance Transactions dataset on DataSF "
               "([%s](%s)), queried by contributor name (the dataset has no donor identifier); retrieved %s; "
               "rows last loaded %s. Query: <%s>" % (DATASET_PAGE, DATASET_PAGE, retrieved,
                                                      money.get("data_loaded_at") or "not given", money["url"]))
    out.append("")
    summary = summarise_money(money["rows"], p["committees"])
    any_rows = False
    for c in p["committees"]:
        s = summary[str(c["filer_nid"])]
        if not (s["schedule_a"] or s["memo"] or s["repeats"] or s["twentyfour_only"]):
            continue
        any_rows = True
        out.append("**%s** (filer %s, %s)" % (c["filer_name"], c["filer_nid"], ROLE_TEXT[c["role"]]))
        out.append("")
        out.append("| Form | Filing id | Filing date | Filed as | Contribution date | Amount | Contributor name as filed | Counted |")
        out.append("|---|---|---|---|---|---|---|---|")
        for label, key, counted in (("Schedule A", "schedule_a", "yes"),
                                    ("Schedule A memo", "memo", "no, memo entry"),
                                    ("24-hour report", "repeats", "no, repeats Schedule A"),
                                    ("24-hour report", "twentyfour_only", "listed apart, no Schedule A row yet")):
            for r in s[key]:
                name = " ".join(x for x in (r.get("transaction_first_name"), r.get("transaction_last_name")) if x)
                out.append("| %s | %s | %s | %s v%s | %s | %s | %s | %s |" % (
                    label, r.get("filing_id_number", ""), (r.get("filing_date") or "")[:10],
                    r.get("filing_type", ""), r.get("filing_version", ""),
                    (r.get("calculated_date") or "")[:10], dollars(_amount(r)), name, counted))
        out.append("")
        out.append("Schedule A total for this committee: **%s** over %d rows. 24-hour rows listed apart "
                   "(not in that total): %s." % (dollars(s["schedule_a_total"]), len(s["schedule_a"]),
                                                  dollars(s["twentyfour_only_total"])))
        out.append("")
    if not any_rows:
        out.append("**No row found.** No Schedule A or 24-hour row in these committees carries a contributor name "
                   "matching the donor's name words. That is a complete answer for these committees and these name "
                   "words only: unitemized contributions carry no name, other spellings would be missed, and "
                   "committees not in the list are not searched.")
        out.append("")
    out.append("Not added together across committees, filings or forms. Contributors named like the donor were "
               "matched on words in the name (%s); read the names above before using any row." % p["name_words_text"])
    out.append("")
    return out


def render_pairing(p, n_total):
    """The pairing's own section: everything but the money, whose rows are rendered apart."""
    label = "%d" % p["n"]
    out = []
    out.append("## Pairing %s: %s and %s on %s" % (label, p["official"], p["donor"], p["subject"]))
    out.append("")
    out.append("**Lead for a reporter's look.** " + p["lead"])
    out.append("")
    out.append("### %s.1 The official's words, as the city's caption transcript publishes them" % label)
    out.append("")
    out.append("> " + p["quote_text"])
    out.append("")
    out.append("- Meeting: %s, %s. Transcript time: %s to %s (caption stamps, hours:minutes:seconds from the start of the recording)." % (
        p["body"], p["date"], p["first_stamp"], p["last_stamp"]))
    out.append("- Transcript: <%s> (Legistar caption transcript, retrieved %s). Wording is the transcript's, not checked against the recording; "
               "the stamp-to-video link was not resolved (see findings)." % (p["transcript_url"], p["transcript_retrieved"]))
    out.append("- Speaker named: **%s**, %s%s." % (p["official"], p["office"],
                                                   (", District %s" % p["district"]) if p["district"] else ""))
    out.append("")
    out.append("### %s.2 How the transcript supports that credit" % label)
    out.append("")
    for stamp, text in p["cue_rows"]:
        out.append("- Caption row `%s`: %s" % (stamp, text))
    out.append("- What the transcript shows: " + p["speaker"]["text_support"])
    auto = p["auto_speaker"]
    out.append("- What the comparison's spoken-cue rule proposes for this passage: %s (%s; %s). %s" % (
        auto["name"] or "nobody", auto["basis"], auto["caution"],
        "It agrees with the credit above." if auto["name"] == p["official"] else
        "It does not agree with the credit above, so a person made this credit."))
    out.append("- Doubt in the credit: **%s**. %s" % (p["speaker"]["doubt"], p["speaker"]["doubt_reason"]))
    if p["speaker"]["outside"]:
        out.append("- Outside the transcript (read %s):" % p["read_on"])
        for o in p["speaker"]["outside"]:
            out.append("  - <%s>: %s" % (o["url"], o["says"]))
    else:
        out.append("- Outside the transcript: nothing used; the credit rests on the caption text.")
    out.append("")
    out.append("### %s.3 The donor's priority in its own words" % label)
    out.append("")
    out.append("> " + p["priority_text"])
    out.append("")
    out.append("- Donor: %s. Page section: %s. Page type: %s%s." % (
        p["donor"], p["priority_section"], p["priority_kind"],
        (", page dated %s" % p["priority_page_date"]) if p["priority_page_date"] else ""))
    out.append("- Source: <%s>. Retrieved %s." % (p["priority_url"], p["priority_retrieved"]))
    out.append("")
    out.append("### %s.4 Why these two sit side by side" % label)
    out.append("")
    out.append("- Overlap (my reading): %s" % p["overlap"])
    out.append("- Positions (my reading): %s" % p["stance"])
    ev = p["lexical"]
    out.append("- Lexical scores of this pair (the trial's ways): TF-IDF cosine %.3f, shared rare two-word phrases %d, "
               "shared named things %d. Clears the trial's calibrated setting for: %s." % (
                   ev["scores"]["tfidf"], ev["scores"]["phrase"], ev["scores"]["anchor"],
                   ", ".join(k for k, v in ev["clears"].items() if v) or "none of the four"))
    out.append("")
    out.append("### %s.5 Money" % label)
    out.append("")
    out.append("By committee and filing, in [Money %s](#%s) below." % (label, anchor_of(money_heading(p))))
    out.append("")
    out.append("### %s.6 Where a person's judgement was needed" % label)
    out.append("")
    for j in p["judgement"]:
        out.append("- %s: **%s**. %s" % (j["step"], j["by"], j["note"]))
    out.append("")
    out.append("### %s.7 What a reporter could check next" % label)
    out.append("")
    for c in p["check_next"]:
        out.append("- " + c)
    out.append("")
    return out


def anchor_of(heading):
    """GitHub's anchor for a heading."""
    h = heading.lower()
    h = re.sub(r"[^a-z0-9 _-]", "", h)
    return h.replace(" ", "-")
