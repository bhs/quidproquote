"""Builds the worked pairings: each an official's exact caption words, the donor's own words and the
money by committee and filing, laid out as a lead for a reporter's look.

    python build_pairings.py                      # reads the sources in data/, queries DataSF, writes pairings.md
    python build_pairings.py --no-money           # no network: the money sections say they were not retrieved
    python build_pairings.py --from-snapshot      # re-render from data/money_snapshot.json, no network

For each pairing it reads three things from the Ethics Commission's DataSF dataset: contributions by
contributors named like the donor to committees tied to the official, independent expenditure reports that
name the official and were filed by committees named like the donor, and (once per donor) the contributor and
committee names the dataset holds that look like the donor.

Writes pairings.md (the write-up, comparable output), pairings.json (the same as data) and, when it
queried, data/money_snapshot.json (the raw rows). Exits 1 when a quote is not found verbatim in the
transcript or a money query fails; nothing stands in for either.
"""

import argparse
import json
import os
import sys

import compare_lib as cl
import money as mn
import pairing_lib as pl

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
SNAPSHOT = os.path.join(DATA, "money_snapshot.json")


def assemble(picks_doc, data_dir):
    """The pairings, with every word re-read from the sources. Raises ValueError on anything missing."""
    meetings, quotes, priorities = cl.load_snapshot(data_dir)
    with open(os.path.join(data_dir, "committees.json"), encoding="utf-8") as f:
        committees_doc = json.load(f)
    roster = [{"name": o["name"], "surname": o["surname"], "district": o["district"], "office": o["office"]}
              for o in committees_doc["officials"]]
    ctx = pl.lexical_context(quotes, priorities)
    meeting_by_id = {m["id"]: m for m in meetings}
    prio_by_id = {p["id"]: p for p in priorities}
    pairs = []
    for pick in picks_doc["pairings"]:
        meeting = meeting_by_id[pick["meeting_id"]]
        rows = pl.load_rows(data_dir, pick["meeting_id"])
        q = pl.extract_quote(rows, pick["quote"]["start"], pick["quote"]["end"],
                             pick["quote"].get("begin_at"), pick["quote"].get("end_at"))
        if not pl.is_verbatim(rows, q["text"]):
            raise ValueError("pairing %s: quote is not verbatim in the transcript" % pick["id"])
        prio = prio_by_id[pick["priority_id"]]
        official, committees = pl.official_committees(committees_doc, pick["official"])
        p = {
            "n": pick["id"], "id_label": str(pick["id"]), "slug": pick["slug"], "subject": pick["subject"],
            "official": official["name"], "surname": official["surname"], "given": official["name"].split()[0], "office": official["office"], "district": official["district"],
            "body": meeting["body"], "date": meeting["date"], "meeting_id": meeting["id"],
            "transcript_url": meeting["url"], "transcript_retrieved": meeting["retrieved"],
            "quote_text": q["text"], "first_stamp": q["first_stamp"], "last_stamp": q["last_stamp"],
            "time": "%s to %s" % (q["first_stamp"], q["last_stamp"]),
            "cue_rows": pl.cue_rows(rows, pick["speaker"]["cue_stamps"]),
            "speaker": pick["speaker"],
            "auto_speaker": pl.auto_speaker(rows, q["first_stamp"], q["text"], roster),
            "read_on": picks_doc["read_on"],
            "donor": prio["donor"], "priority_id": prio["id"], "priority_text": prio["text"],
            "priority_section": prio.get("section") or "(none)", "priority_kind": prio.get("kind") or "",
            "priority_page_date": prio.get("page_date"), "priority_url": prio["url"],
            "priority_retrieved": prio["retrieved"],
            "overlap": pick["overlap"], "stance": pick["stance"],
            "lexical": pl.lexical_evidence(ctx, priorities, q["text"], prio["id"]),
            "judgement": pick["judgement"], "check_next": pick["check_next"],
            "committees": committees,
            "name_words_text": mn.name_words_text(prio["donor"]),
        }
        p["lead"] = pl.lead_text(p)
        pairs.append(p)
    return pairs


def speaker_rates(data_dir):
    """How often the spoken-cue rule proposes anybody: over all substantive passages and over the passages
    the earlier trial's model labelled 'meaningful' against a donor statement."""
    _, quotes, _ = cl.load_snapshot(data_dir)
    with open(os.path.join(data_dir, "committees.json"), encoding="utf-8") as f:
        doc = json.load(f)
    roster = [{"name": o["name"], "surname": o["surname"], "district": o["district"], "office": o["office"]}
              for o in doc["officials"]]
    with open(os.path.join(data_dir, "labels_model.json"), encoding="utf-8") as f:
        labels = json.load(f)["labels"]
    by_id = {q["id"]: q for q in quotes}
    proposals = {q["id"]: cl.propose_speaker(q["before"], q["text"], roster)["name"] for q in quotes}
    meaningful = sorted({cl.split_pair(pid)[0] for pid, v in labels.items() if v["label"] == "meaningful"})
    named = {qid: proposals[qid] for qid in meaningful if proposals.get(qid)}
    return {"passages": len(quotes), "with_proposal": sum(1 for v in proposals.values() if v),
            "meaningful_passages": len(meaningful), "meaningful_with_proposal": len(named),
            "meaningful_proposals": {qid: [by_id[qid]["meeting_body"], by_id[qid]["meeting_date"], by_id[qid]["start"], name]
                                     for qid, name in named.items()}}


def money_key(p):
    return "%s|%s" % (p["donor"], p["official"])


def gather_money(pairs, mode):
    """(money, retrieved, census). money is {key: {'rows','url','error','data_loaded_at','independent','control'}},
    census is {donor: names read}; both empty when not asked."""
    if mode == "none":
        return {}, None, {}
    if mode == "snapshot":
        with open(SNAPSHOT, encoding="utf-8") as f:
            snap = json.load(f)
        return snap["money"], snap["retrieved"], snap.get("census", {})
    out, census = {}, {}
    for p in pairs:
        key = money_key(p)
        nids = [c["filer_nid"] for c in p["committees"]]
        if key not in out:
            out[key] = mn.fetch_money(p["donor"], nids)
            out[key]["independent"] = mn.fetch_independent(p["donor"], p["surname"])
            out[key]["control"] = mn.fetch_control(nids)
            out[key]["loose"] = mn.fetch_loose(p["donor"], nids, p["surname"], p["given"])
        if p["donor"] not in census:
            census[p["donor"]] = mn.fetch_census(p["donor"])
    return out, mn.today(), census


def failures(money, census):
    """Every query that failed, as text; empty when all were read."""
    out = []
    for k, m in money.items():
        for part, d in (("contributions", m), ("independent expenditures", m.get("independent") or {}),
                        ("control count", m.get("control") or {}),
                        ("looser patterns", m.get("loose") or {})):
            if d.get("error"):
                out.append("%s (%s)" % (k, part))
    for donor, c in (census or {}).items():
        if c.get("error"):
            out.append("%s (names read)" % donor)
    return out


def render(pairs, picks_doc, money, retrieved, rates=None, census=None):
    out = ["# Worked pairings: San Francisco officials' exact words, a donor's own priority and the money, as leads", ""]
    out.append("Six pairings put together from the city's caption transcripts, donors' own published statements and the "
               "Ethics Commission's campaign finance data. Each is a lead worth a reporter's look. " + pl.NO_CAUSATION)
    out.append("")
    out.append("Quotes are the transcript's text as published, not checked against the recording. Every speaker credit "
               "is a person's reading of the transcript text, with its doubt stated. Money is per committee and filing, "
               "never added across committees, filings or forms.")
    out.append("")
    out.append("| # | Official | Meeting and transcript time | Donor and statement | Doubt in speaker credit |")
    out.append("|---|---|---|---|---|")
    for p in pairs:
        out.append("| [%d](#%s) | %s | %s %s, %s | %s (%s) | %s |" % (
            p["n"], pl.anchor_of("Pairing %d: %s and %s on %s" % (p["n"], p["official"], p["donor"], p["subject"])),
            p["official"], p["body"], p["date"], p["first_stamp"], p["donor"], p["priority_id"],
            p["speaker"]["doubt"]))
    out.append("")
    for p in pairs:
        out.extend(pl.render_pairing(p, len(pairs)))
    out.append("## Money")
    out.append("")
    out.append("One section per pairing, so that the pairings above keep their place. Each has two parts. The first "
               "searches every committee tied to the official in `data/committees.json` for contributions from "
               "contributors whose name holds the donor's name words. The second lists independent expenditure reports "
               "that name the official, filed by committees whose own name holds the same words: money the donor's "
               "committee spent itself, which is not money given to the official's committees. The name words come from "
               "`money.py` and were checked against the names read in the filings (section \"Names read in the "
               "filings\" below).")
    out.append("")
    for p in pairs:
        out.extend(pl.render_money_section(p, money.get(money_key(p)) if money else None, retrieved))
    out.extend(render_census_for(pairs, census, retrieved))
    out.append("## Candidates looked at and not used")
    out.append("")
    for d in picks_doc["dropped"]:
        out.append("- `%s` against %s: %s" % (d["passage"], ", ".join(d["priorities"]), d["why"]))
    out.append("")
    if rates:
        out.append("## How often the spoken-cue rule proposes a speaker")
        out.append("")
        out.append("The rule of the matching methods comparison (`compare_lib.propose_speaker`) reads a name cue such as "
                   "'Supervisor X' in the 40 caption words before a passage. Over the %d substantive passages of the 11 "
                   "transcripts it proposes a speaker for %d. Over the %d passages the earlier trial's model labelled "
                   "'meaningful' against a donor statement it proposes a speaker for %d:" % (
                       rates["passages"], rates["with_proposal"], rates["meaningful_passages"],
                       rates["meaningful_with_proposal"]))
        out.append("")
        for qid, (body, date, stamp, name) in sorted(rates["meaningful_proposals"].items()):
            out.append("- %s, %s, %s: proposes %s" % (body, date, stamp, name))
        out.append("")
        out.append("Whether each proposal is right was read only for the passages used in the pairings above.")
        out.append("")
    return "\n".join(out)


def render_census_for(pairs, census, retrieved):
    donors = []
    for p in pairs:
        if p["donor"] not in donors:
            donors.append(p["donor"])
    return pl.render_census(census, donors, retrieved)


def to_json(pairs, money, retrieved, rates=None, census=None):
    docs = []
    for p in pairs:
        d = {k: v for k, v in p.items() if k not in ("committees",)}
        d["committees"] = [{k: c[k] for k in ("filer_nid", "filer_name", "filer_type", "status", "role")} for c in p["committees"]]
        d["cue_rows"] = [list(r) for r in p["cue_rows"]]
        m = money.get(money_key(p)) if money else None
        if m is not None and not m.get("error"):
            summary = pl.summarise_money(m["rows"], p["committees"])
            ind = m.get("independent") or {}
            groups = pl.summarise_independent(ind.get("rows", []), p["surname"], p["given"]) if not ind.get("error") else []
            d["independent_expenditures"] = [
                {"filer_nid": g["filer_nid"], "filer_name": g["filer_name"], "office": g["office"],
                 "district": g["district"], "rows_24_hour": len(g["counted"]), "total_24_hour": g["total"],
                 "rows_listed_apart": len(g["apart"]), "total_listed_apart": g["apart_total"]} for g in groups]
            d["money"] = {"retrieved": retrieved, "url": m["url"], "data_loaded_at": m["data_loaded_at"],
                          "control_schedule_a_rows": (m.get("control") or {}).get("by_committee"),
                          "by_committee": {nid: {"schedule_a_total": s["schedule_a_total"], "schedule_a_rows": len(s["schedule_a"]),
                                                 "memo_rows": len(s["memo"]), "twentyfour_repeats": len(s["repeats"]),
                                                 "twentyfour_only_total": s["twentyfour_only_total"]}
                                           for nid, s in summary.items()}}
        else:
            d["money"] = {"retrieved": None, "error": (m or {}).get("error") or "not retrieved"}
        docs.append(d)
    return {"pairings": docs, "speaker_rates": rates,
            "names_read": {donor: {"contributors": c.get("contributors"), "committees": c.get("committees")}
                           for donor, c in (census or {}).items() if not c.get("error")}}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--no-money", action="store_true", help="do not query DataSF")
    ap.add_argument("--from-snapshot", action="store_true", help="use data/money_snapshot.json instead of querying")
    ap.add_argument("--out", default=HERE, help="where to write pairings.md and pairings.json")
    args = ap.parse_args(argv)
    with open(os.path.join(HERE, "picks.json"), encoding="utf-8") as f:
        picks_doc = json.load(f)
    try:
        pairs = assemble(picks_doc, DATA)
    except (ValueError, KeyError, StopIteration) as exc:
        print("cannot build: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 1
    mode = "none" if args.no_money else "snapshot" if args.from_snapshot else "live"
    money, retrieved, census = gather_money(pairs, mode)
    if mode == "live":
        with open(SNAPSHOT, "w", encoding="utf-8") as f:
            json.dump({"retrieved": retrieved, "money": money, "census": census}, f, indent=1)
            f.write("\n")
    rates = speaker_rates(DATA)
    text = render(pairs, picks_doc, money, retrieved, rates, census)
    with open(os.path.join(args.out, "pairings.md"), "w", encoding="utf-8") as f:
        f.write(text + "\n")
    with open(os.path.join(args.out, "pairings.json"), "w", encoding="utf-8") as f:
        json.dump(to_json(pairs, money, retrieved, rates, census), f, indent=1)
        f.write("\n")
    print(text)
    failed = failures(money, census)
    if failed:
        print("money query failed for: %s" % "; ".join(failed), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
