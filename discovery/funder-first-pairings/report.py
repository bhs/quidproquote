"""Renders the results of run.py: the figures behind the charter questions, the table of every funded pair, and
the pairings laid out as leads for a reporter to check. Nothing here claims a cause; every pairing says so.
Standard library only."""

import collections

import fmap_lib as fl

NO_CAUSE = ("A lead, not a finding. The two are shown side by side for a reader to check. Nothing here says why "
            "anyone said or gave anything, and the order of the dates is not an explanation.")
DOUBT_WORDS = {"low": "low doubt", "medium": "medium doubt", "high": "high doubt"}


def pct(n, d):
    return "%d of %d (%d%%)" % (n, d, round(100.0 * n / d)) if d else "0 of 0"


def complete(p):
    """The five parts a pairing needs: exact words with meeting and time, the speaker credit, the donor's words
    with link and date, the money by committee and filing, and the statement that no cause is claimed (which
    render_pairings always carries)."""
    q, c, m = p["quote"], p["speaker_credit"], p["money"]
    return bool(q["text"] and q["body"] and q["date"] and q["first_stamp"] and q["transcript_url"]
                and c["doubt"] and p["donor_words"]
                and all(d["text"] and d["url"] and (d["page_date"] or d["retrieved"]) for d in p["donor_words"])
                and m["per_committee"] and all(x["filings"] for x in m["per_committee"]))


def metrics(table, cands, per_meeting, pairings, reviews_doc):
    tied = [r for r in table if r["tied"]]
    status = collections.Counter(r["status"] for r in tied)
    reviewed = [c for c in cands if c["decision"] != "unreviewed"]
    agree = collections.defaultdict(collections.Counter)
    for c in reviewed:
        agree[c["credit"]["doubt"]][(c["review"] or {}).get("credit", "not judged")] += 1
    minutes_all = collections.Counter(c["minutes"]["status"] for c in cands)
    accepted = [c for c in cands if c["decision"] == "accept"]
    minutes_acc = collections.Counter(c["minutes"]["status"] for c in accepted)
    uniq = {}
    for c in cands:
        uniq.setdefault((c["meeting_id"], c["official"], c["first_stamp"]), c)
    u = list(uniq.values())
    u_agree = collections.defaultdict(collections.Counter)
    for c in u:
        if c["decision"] != "unreviewed":
            u_agree[c["credit"]["doubt"]][(c["review"] or {}).get("credit", "not judged")] += 1
    with_minutes = [c for c in u if c["minutes"]["status"] != "no_minutes"]
    return {
        "unique_passages": len(u), "credit_doubt_unique": dict(collections.Counter(c["credit"]["doubt"] for c in u)),
        "reviewer_vs_rule_credit_unique": {k: dict(v) for k, v in u_agree.items()},
        "unique_passages_in_meetings_with_minutes": len(with_minutes),
        "minutes_status_unique_with_minutes": dict(collections.Counter(c["minutes"]["status"] for c in with_minutes)),
        "meetings_read": len(per_meeting),
        "meetings_sampled": sum(1 for m in per_meeting if m["source"] == "sampled"),
        "meetings_beyond_sample": sum(1 for m in per_meeting if m["source"] != "sampled"),
        "meetings_with_minutes": sum(1 for m in per_meeting if m["minutes_parsed"]),
        "funded_pairs": len(table), "funded_pairs_tied_committees": len(tied),
        "tied_pairs_by_status": dict(status),
        "tied_pairs_with_any_candidate": sum(1 for r in tied if r["candidates"]),
        "tied_pairs_with_specific_candidate": sum(1 for r in tied if r["specific"]),
        "tied_pairs_with_fitting_remark": sum(1 for r in tied if r["decisions"].get("accept")),
        "tied_pairs_with_fitting_or_broad": sum(1 for r in tied if r["decisions"].get("accept") or r["decisions"].get("loose")),
        "candidates": len(cands), "candidates_specific": sum(1 for c in cands if c["tier"] == "specific"),
        "candidates_by_decision": dict(collections.Counter(c["decision"] for c in cands)),
        "credit_doubt_all": dict(collections.Counter(c["credit"]["doubt"] for c in cands)),
        "reviewer_vs_rule_credit_by_doubt": {k: dict(v) for k, v in agree.items()},
        "minutes_status_all": dict(minutes_all), "minutes_status_accepted": dict(minutes_acc),
        "pairings": len(pairings), "pairings_complete": sum(1 for p in pairings if complete(p))}


def judgement_steps(reviews_doc, subjects, cands, pairings, timings):
    rv = reviews_doc["reviews"]
    dec = collections.Counter(r["decision"] for r in rv)
    cr = collections.Counter(r.get("credit", "not judged") for r in rv)
    trims = sum(1 for r in rv if r.get("trim"))
    readings = sum(1 for r in rv if r.get("in_common"))
    return [
        {"step": "Recognise a giver as the donor", "decides": "that the committee or name in the filing is the donor's own",
         "done_by": "a person, once per donor, in the funding map (data/families.json); applied here by rule",
         "items": "17 donor families; none added here", "machine_seconds": timings.get("load data"), "judgement_time": "not timed"},
        {"step": "Read the donor's words into search terms", "decides": "which measure names and phrases stand for the donor's subject",
         "done_by": "the agent that wrote this hop (data/subjects.json)", "items": "%d subjects" % len(subjects),
         "machine_seconds": None, "judgement_time": "not timed"},
        {"step": "Find candidate passages", "decides": "nothing: every turn credited to the official is searched for the terms",
         "done_by": "the program", "items": "%d candidate passages" % len(cands),
         "machine_seconds": timings.get("search and credit"), "judgement_time": "none"},
        {"step": "Say whether a passage is on the donor's subject", "decides": "accept (the same measure or specific proposal), loose (the same broad subject), reject (a term in common by chance, or not the official's words)",
         "done_by": "the agent that wrote this hop (data/reviews.json)",
         "items": "%d passages: %d accept, %d loose, %d reject" % (len(rv), dec["accept"], dec["loose"], dec["reject"]),
         "machine_seconds": None, "judgement_time": "not timed"},
        {"step": "Credit the passage to the official", "decides": "whether the speaker is who the rule says, reading the words around the passage",
         "done_by": "the program proposes a doubt level; the agent that wrote this hop agrees or disagrees",
         "items": "%d judged: %d agree, %d disagree, %d unclear" % (sum(cr[k] for k in ("agree", "disagree", "unclear")), cr["agree"], cr["disagree"], cr["unclear"]),
         "machine_seconds": timings.get("credit: find turns"), "judgement_time": "not timed"},
        {"step": "Set the credit against the minutes", "decides": "when the minutes are silent or conflict, which vote or item the words are about",
         "done_by": "the program checks vote, motion, sponsor and presence; the agent reads each conflict",
         "items": "%d of %d candidates have a minutes status other than 'no_minutes'" % (sum(1 for c in cands if c["minutes"]["status"] != "no_minutes"), len(cands)),
         "machine_seconds": timings.get("minutes check"), "judgement_time": "not timed"},
        {"step": "Cut the quote", "decides": "where the quote begins and ends, as whole sentences, without altering a word",
         "done_by": "the agent that wrote this hop; the program refuses a cut that is not word for word in the transcript",
         "items": "%d cuts" % trims, "machine_seconds": None, "judgement_time": "not timed"},
        {"step": "Write what the two have in common and where they differ", "decides": "the reading shown beside the pair, with no cause claimed",
         "done_by": "the agent that wrote this hop", "items": "%d readings" % readings, "machine_seconds": None,
         "judgement_time": "not timed"},
        {"step": "Watch the video at the stamp", "decides": "that the words were said, by whom, as captioned",
         "done_by": "nobody: no recording was played", "items": "0", "machine_seconds": None, "judgement_time": "not done"}]


def money_line(c):
    rng = c["first_date"] if c["first_date"] == c["last_date"] else "%s to %s" % (c["first_date"], c["last_date"])
    return "%s Schedule A, %s (filer %s); %s; %d row%s, %s" % (
        fl.dollars(c["schedule_a_total"]), c["committee"], c["filer_nid"], c["kind"], c["schedule_a_rows"],
        "" if c["schedule_a_rows"] == 1 else "s", rng)


def render_results(res):
    m, ext = res["metrics"], res["extension"]
    L = ["# Funder-first pairings: results of the run", ""]
    L.append("Mode: %s. Money retrieved %s, data loaded through %s (Ethics Commission Transactions dataset, %s)." % (
        res["mode"], res["money"]["retrieved"], res["money"]["data_loaded_through"], res["money"]["dataset"]))
    L.append("")
    L.append("## Meetings read")
    L.append("")
    L.append("%d meetings: %d sampled in earlier hops, %d beyond the sample; minutes parsed for %d." % (
        m["meetings_read"], m["meetings_sampled"], m["meetings_beyond_sample"], m["meetings_with_minutes"]))
    if ext["attempted"]:
        L.append("")
        L.append("Beyond the sample: read the %s for %s; the calendar listed %d meetings of the Board and its standing "
                 "committees, %d with a transcript; asked for up to %d beyond the sample; added %d." % (
                     ext["route"] or "(no route answered)", ext["year"], ext["calendar_rows"],
                     ext["calendar_rows_with_transcript"], ext["wanted"], ext["added"]))
        for n in ext["notes"]:
            L.append("- note: " + n)
        for e in ext["errors"]:
            L.append("- NOT READ: " + e)
    else:
        L.append("")
        L.append("Offline run: nothing beyond the sample was requested.")
    L += ["", "| Meeting | Date | Source | Caption words | Words credited to a named official | Turns | Minutes |", "|---|---|---|---|---|---|---|"]
    for x in res["meetings"]:
        L.append("| [%s](%s) | %s | %s | %d | %d (%d%%) | %d | %s |" % (
            x["body"], x["transcript_url"], x["date"], x["source"], x["caption_words"], x["credited_words"],
            round(100.0 * x["credited_words"] / max(x["caption_words"], 1)), x["turns_credited"],
            (x["minutes"] or "none")[:70]))
    L += ["", "## 1. How often does the official say something on the donor's subject?", ""]
    L.append("Funded pairs (a donor family with Schedule A money in a committee of the official): %d, of which %d reached a "
             "committee that is the official's own or a measure committee carrying the official's name (the other %d reached only a "
             "committee formed to support or oppose the official). Counts below are over the %d." % (
                 m["funded_pairs"], m["funded_pairs_tied_committees"], m["funded_pairs"] - m["funded_pairs_tied_committees"],
                 m["funded_pairs_tied_committees"]))
    L.append("")
    t = m["funded_pairs_tied_committees"]
    L.append("- Pairs with at least one passage that hit the donor's subject terms: %s." % pct(m["tied_pairs_with_any_candidate"], t))
    L.append("- Pairs with a passage that hit a specific term (a measure name or a phrase particular to the proposal): %s." % pct(m["tied_pairs_with_specific_candidate"], t))
    L.append("- Pairs with a passage a person judged on the donor's subject (accept): %s." % pct(m["tied_pairs_with_fitting_remark"], t))
    L.append("- Pairs with an accepted or a broad-subject (loose) passage: %s." % pct(m["tied_pairs_with_fitting_or_broad"], t))
    L.append("- Candidate passages: %d (%d specific); decisions: %s." % (m["candidates"], m["candidates_specific"], m["candidates_by_decision"]))
    L.append("- Status of the pairs: %s." % m["tied_pairs_by_status"])
    L += ["", "### Every funded pair, with the outcome", "",
          "| Official | Donor | Money by committee (Schedule A, not added across committees) | Outcome | Why |", "|---|---|---|---|---|"]
    for r in res["pairs"]:
        money = "<br>".join("%s %s (%s)" % (fl.dollars(c["schedule_a_total"]), c["committee"], c["kind"]) for c in r["committees"])
        L.append("| %s | %s | %s | %s%s | %s |" % (r["official"], r["family"], money, r["status"],
                                                  "" if r["tied"] else " (third-party committee only)", r["reason"]))
    L += ["", "### Credited words by official", ""]
    L.append("; ".join("%s %d" % (k, v) for k, v in res["credited_words_by_official"].items()) or "none")
    L += ["", "## 2. How is each quote credited, and do the minutes confirm it?", ""]
    L.append("Credit comes from the caption text: a cue that names the official as about to speak ('SUPERVISOR X THANK YOU', "
             "'>> VICE CHAIR X', the clerk's introduction of the Mayor's appearance) opens a turn, and the next cue, roll call, "
             "clerk call or self-introduction closes it. Doubt: low = the surname is spelled as the roster has it, a cue closes the turn, "
             "at most one '>>' lies between cue and passage, within 400 words; medium = a garbled spelling, no closing cue, a few "
             "'>>' marks or up to 700 words, and any Chan or Chen credit without a district cue; high = otherwise.")
    L.append("")
    L.append("- Distinct passages (one passage can hit several donors' subjects): %d. By rule doubt: %s. Reviewer's reading of the credit, by rule doubt: %s." % (
        m["unique_passages"], m["credit_doubt_unique"], m["reviewer_vs_rule_credit_unique"]))
    L.append("- Distinct passages in a meeting whose minutes were read: %d; minutes status: %s." % (
        m["unique_passages_in_meetings_with_minutes"], m["minutes_status_unique_with_minutes"]))
    L.append("- Candidates by rule doubt (each donor subject counted separately): %s." % m["credit_doubt_all"])
    L.append("- Where the reviewer judged the credit (rule doubt: reviewer's judgement): %s." % m["reviewer_vs_rule_credit_by_doubt"])
    L.append("- Minutes status of all candidates: %s; of the accepted ones: %s." % (m["minutes_status_all"], m["minutes_status_accepted"]))
    L.append("")
    L.append("Minutes status: `confirmed` = the minutes record an act by the credited official that fits (a vote on the side the words state, a motion, a summary of addressing the Board); `consistent` = the minutes list the official as a sponsor of the item the words are about (fits, but does not say who spoke); `conflict` = the minutes put the official on the other side of the best-matching vote or do not name them; `silent` = nothing recorded (ordinary for floor remarks; the minutes are action minutes); `no_minutes` = none read.")
    L += ["", "### The earlier hop's five pairings, searched for again", "",
          "| Pairing | Meeting | Quote | Earlier doubt | Rule doubt | Outcome |", "|---|---|---|---|---|---|"]
    for e in res["earlier_pairings_check"]:
        L.append("| %s, %s | %s | %s to %s | %s | %s | %s |" % (e["official"], e["family"], e["meeting_id"], e["quote_from"], e["quote_to"],
                                                              e["earlier_doubt"], e.get("rule_doubt", ""), e["outcome"]))
    L += ["", "## 3. Which steps needed judgement, and how long did each take?", "",
          "| Step | What is decided | Done by | Items | Machine seconds | Judgement time |", "|---|---|---|---|---|---|"]
    for s in res["judgement_steps"]:
        L.append("| %s | %s | %s | %s | %s | %s |" % (s["step"], s["decides"], s["done_by"], s["items"],
                                                    "" if s["machine_seconds"] is None else s["machine_seconds"], s["judgement_time"]))
    L += ["", "Timings of the whole run, in seconds: %s." % res["timings_seconds"], ""]
    L += ["## Candidate passages", "", "| Id | Tier | Rule doubt | Minutes | Decision | Passage |", "|---|---|---|---|---|---|"]
    for c in res["candidates"]:
        L.append("| %s | %s | %s | %s | %s | %s |" % (c["id"], c["tier"], c["credit"]["doubt"], c["minutes"]["status"],
                                                      c["decision"], c["text"][:150].replace("|", "/")))
    if res["stale_reviews"]:
        L += ["", "Reviews that match no candidate in this run (their meeting may not have been read): %s." % ", ".join(res["stale_reviews"])]
    return "\n".join(L) + "\n"


def render_pairings(res):
    L = ["# Pairings: leads for a reporter to check", ""]
    L.append("%d pairing(s), %d complete (exact words with meeting and time; speaker credit; the donor's words with link and date; "
             "money by committee and filing; no cause claimed). Each starts from a donor's money in a committee of an official and "
             "then a remark of that official on the donor's stated subject. %s" % (
                 len(res["pairings"]), res["metrics"]["pairings_complete"], NO_CAUSE))
    L.append("")
    for p in res["pairings"]:
        q, c, mo = p["quote"], p["speaker_credit"], p["money"]
        L.append("## Pairing %d: %s and %s on %s" % (p["id"], p["official"], p["donor"], p["subject"]))
        L.append("")
        L.append("**The official's exact words** (%s, %s, transcript time %s to %s; [transcript](%s)):" % (
            q["body"], q["date"], q["first_stamp"], q["last_stamp"], q["transcript_url"]))
        L.append("")
        L.append("> \"%s\"" % q["text"])
        L.append("")
        L.append("**Speaker credit: %s.** %s %s" % (DOUBT_WORDS[c["doubt"]], "; ".join(c["rule"]) + ".",
                                                    ("Reviewer: %s. %s" % (c["reviewer"], c["reviewer_note"])).strip()))
        L.append("")
        L.append("Minutes (%s): **%s.** %s" % (c["minutes_source"] or "none read", c["minutes"]["status"], " ".join(c["minutes"]["checks"])))
        L.append("")
        L.append("**The donor's words** (%s):" % p["donor"])
        L.append("")
        for d in p["donor_words"]:
            L.append("> \"%s\"" % d["text"])
            L.append(">")
            L.append("> %s; %s; page date %s, retrieved %s; [source](%s)%s" % (
                d["section"], d["kind"], d["page_date"] or "not shown on the page", d["retrieved"], d["url"],
                ("; " + d["caveat"]) if d.get("caveat") else ""))
            L.append("")
        L.append("**The money** (retrieved %s, data loaded through %s; one line per receiving committee, never added across committees):" % (
            mo["retrieved"], mo["data_loaded_through"]))
        L.append("")
        for x in mo["per_committee"]:
            L.append("- " + money_line(x))
            L.append("  - Giver(s) as filed: %s. Filings: %s." % ("; ".join(x["givers_as_filed"]), ", ".join(x["filings"])))
            if x["h24_repeats_not_counted"] or x["h24_only_rows"]:
                L.append("  - 24-hour reports: %d repeat a Schedule A row (listed in the filing, not counted); %d have no Schedule A row yet (%s, apart)." % (
                    x["h24_repeats_not_counted"], x["h24_only_rows"], fl.dollars(x["h24_only_total"])))
        if mo["outside_spending_apart"]:
            for o in mo["outside_spending_apart"]:
                L.append("- Outside spending, apart: %s %s the official, %s in %d filings (%s to %s)." % (
                    o["payer"], o["stance"], fl.dollars(o["amount"]), len(o["filings"]), o["first"], o["last"]))
        L.append("- The tie of the giver to the donor: %d row(s) by an FPPC id the Filers dataset resolves, %d by name as filed." % (
            mo["tie"]["by_id_rows"], mo["tie"]["by_name_rows"]))
        L.append("")
        L.append("**Reading, not a finding.** In common: %s Where they differ: %s %s" % (
            p["reading"]["in_common"] or "(none written)", p["reading"]["differs"] or "(none written)", "No cause is claimed."))
        L.append("")
        L.append("To check: play the recording of the meeting at the stamp (captions trail speech and can misspell names); read the donor's page; open the filings.")
        L.append("")
    return "\n".join(L)
