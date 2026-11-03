"""Funder-first pairings: start from where a donor's money reached an official and look for what the official said.

    python run.py              # reads the sampled meetings in data/, then the city's calendar for more (network)
    python run.py --offline    # the sampled meetings only, and only the minutes excerpts kept in data/minutes/

For every funded pair (a donor family that gave Schedule A money to a committee of an official) it searches the
meetings for passages, in turns credited to that official from the caption text, that hit the terms of the
donor's stated subject (data/subjects.json); sets each credit against the meeting minutes; applies the reviews a
person made of those passages (data/reviews.json); and writes results.json, results.md and pairings.md.
Every funded pair with no fitting remark is recorded, with the reason.

Settings (environment): FF_YEAR (calendar year to read, default 2026), FF_MAX_NEW_MEETINGS (meetings beyond the
sampled ones, default 60), FF_TIME_BUDGET_S (seconds each of the two collecting steps may take, default 300),
FF_CACHE_DIR (where fetched transcripts and minutes are kept between runs).
A meeting or minutes document that cannot be fetched is recorded with the error; it is never replaced by an
empty answer, and the figures say how many meetings they rest on.
"""

import argparse
import collections
import json
import os
import sys
import time

import ff_lib as ff
import fmap_lib as fl
import legistar as lg
import report

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
TRANSCRIPT_URL = "https://sfgov.legistar.com/Transcript.aspx?ID1=%d"
DOUBT_ORDER = {"low": 0, "medium": 1, "high": 2}


class Timer:
    def __init__(self):
        self.t = collections.OrderedDict()

    def step(self, name):
        timer = self

        class _S:
            def __enter__(self):
                self.t0 = time.perf_counter()

            def __exit__(self, *a):
                timer.t[name] = round(time.perf_counter() - self.t0, 2)
        return _S()


def log(msg):
    print(msg, flush=True)


def read_excerpt(mid):
    path = os.path.join(DATA, "minutes", "%d.txt" % mid)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    return None


def over_budget(t0):
    return time.perf_counter() - t0 > float(os.environ.get("FF_TIME_BUDGET_S", "300"))


def load_meetings(offline, timer):
    """The meetings read: the sampled ones from data/, and (unless offline) the ones the city's calendar adds.
    Returns (meetings, extension) where each meeting is {id, body, date, source, doc, minutes, minutes_source,
    minutes_note}."""
    with open(os.path.join(DATA, "meetings.json"), encoding="utf-8") as f:
        sampled = json.load(f)
    meetings = []
    for m in sampled:
        meetings.append({"id": m["id"], "body": m["body"], "date": m["date"], "source": "sampled",
                         "doc": ff.Doc(fl.load_rows(DATA, m["id"])), "minutes_url": "", "minutes_text": None,
                         "minutes_source": "", "minutes_note": ""})
    ext = {"attempted": not offline, "route": "", "year": None, "notes": [], "errors": [], "calendar_rows": 0,
           "calendar_rows_with_transcript": 0, "added": 0, "wanted": 0}
    by_id = {m["id"]: m for m in meetings}
    if not offline:
        year = int(os.environ.get("FF_YEAR", "2026"))
        max_new = int(os.environ.get("FF_MAX_NEW_MEETINGS", "60"))
        ext["year"], ext["wanted"] = year, max_new
        with timer.step("collect: calendar"):
            try:
                srows, nrows, notes, seen, with_t, route = lg.discover(set(by_id), year, max_new)
                ext.update(route=route, notes=notes, calendar_rows=seen, calendar_rows_with_transcript=with_t)
            except lg.FetchError as exc:
                srows, nrows = [], []
                ext["errors"].append("calendar and feeds: %s" % exc)
        t0 = time.perf_counter()
        with timer.step("collect: transcripts and minutes"):
            for r in srows:
                by_id[r["transcript_id"]]["minutes_url"] = r["minutes_url"]
            for r in nrows:
                if over_budget(t0):
                    ext["errors"].append("time budget (FF_TIME_BUDGET_S) reached before transcript %s (%s %s) and later ones" % (
                        r["transcript_id"], r["body"], r["date"]))
                    break
                try:
                    rows = lg.fetch_transcript(r["transcript_id"])
                except lg.FetchError as exc:
                    ext["errors"].append("transcript %s (%s %s): %s" % (r["transcript_id"], r["body"], r["date"], exc))
                    continue
                m = {"id": r["transcript_id"], "body": r["body"], "date": r["date"], "source": "beyond the sample",
                     "doc": ff.Doc(rows), "minutes_url": r["minutes_url"], "minutes_text": None, "minutes_source": "",
                     "minutes_note": ""}
                meetings.append(m)
                by_id[m["id"]] = m
                ext["added"] += 1
    t1 = time.perf_counter()
    with timer.step("collect: minutes"):
        for m in meetings:
            text = None
            if m["minutes_url"] and not offline and over_budget(t1):
                m["minutes_note"] = "minutes not read: time budget reached"
            elif m["minutes_url"] and not offline:
                try:
                    text = lg.fetch_minutes(m["id"], m["minutes_url"])
                    m["minutes_source"] = "minutes PDF " + m["minutes_url"]
                except lg.FetchError as exc:
                    m["minutes_note"] = "minutes not read: %s" % exc
                    ext["errors"].append("minutes of %s %s: %s" % (m["body"], m["date"], exc))
            if text is None:
                text = read_excerpt(m["id"])
                if text is not None:
                    m["minutes_source"] = "excerpts typed from the minutes (data/minutes/%d.txt)" % m["id"]
            if text is None and not m["minutes_note"]:
                m["minutes_note"] = "no minutes link" if not offline else "offline: no minutes read"
            m["minutes_text"] = text
            m["minutes"] = ff.parse_minutes(text) if text else None
    meetings.sort(key=lambda m: (m["date"], m["id"]))
    return meetings, ext


def apply_review(c, reviews):
    r = reviews.get(c["id"])
    c["review"] = r
    c["decision"] = r["decision"] if r else "unreviewed"
    return c


def candidates_for(pairs, subjects, meetings, regions, reviews, timer):
    out = []
    with timer.step("search and credit"):
        for (off, fam), money in pairs.items():
            for subj in (s for s in subjects if s["family"] == fam):
                for m in meetings:
                    doc = m["doc"]
                    for reg in regions[m["id"]]:
                        if reg["official"] != off:
                            continue
                        for p in ff.candidate_passages(doc, reg, subj):
                            doubt, why = ff.credit_tier(doc, reg, p["start"])
                            cid = ff.review_id(m["id"], p["first_stamp"], off, subj["id"])
                            out.append({
                                "id": cid, "official": off, "family": fam, "subject": subj["id"], "meeting_id": m["id"],
                                "body": m["body"], "date": m["date"], "first_stamp": p["first_stamp"],
                                "last_stamp": p["last_stamp"], "text": p["text"], "tier": p["tier"],
                                "anchor_hits": p["anchor_hits"], "topic_hits": p["topic_hits"],
                                "credit": {"doubt": doubt, "why": why, "cue": reg["cue"], "cue_stamp": reg["cue_stamp"],
                                           "exact_spelling": reg["exact"], "closed_by_a_cue": reg["bounded"]},
                                "_pos": (p["start"], p["end"])})
    by_id = {m["id"]: m for m in meetings}
    for c in out:
        apply_review(c, reviews)
        c["final_text"], c["final_first"], c["final_last"] = trimmed(c, by_id[c["meeting_id"]]["doc"])
    with timer.step("minutes check"):
        for c in out:
            c["minutes"] = ff.check_minutes(by_id[c["meeting_id"]]["minutes"], c["official"], c["final_text"])
    return out


def trimmed(c, doc):
    """The reviewer's quote boundaries applied: (text, first_stamp, last_stamp). The reviewer names the words
    the quote begins and ends at; they are looked for from 3000 characters before the machine's passage to 2500
    after its start, and the cut must be word for word in the transcript (it is cut from it)."""
    t = (c["review"] or {}).get("trim")
    if not t:
        return c["text"], c["first_stamp"], c["last_stamp"]
    start = c["_pos"][0]
    lo = max(start - 3000, 0)
    window = doc.text[lo:start + 2500]
    b = window.find(t["begin_at"]) if t.get("begin_at") else (start - lo)
    if b < 0:
        raise ValueError("review %s: begin_at not found" % c["id"])
    e = len(window)
    if t.get("end_at"):
        i = window.find(t["end_at"], b)
        if i < 0:
            raise ValueError("review %s: end_at not found" % c["id"])
        e = i + len(t["end_at"])
    text = window[b:e].strip()
    pos = lo + b
    return text, doc.stamp(pos), doc.stamp(pos + len(text) - 1)


def donor_words(subject, ids, prio, reported):
    out = []
    for sid in ids:
        if sid in prio:
            s = prio[sid]
            out.append({"id": sid, "kind": "the donor's own words", "section": s["section"], "text": s["text"],
                        "url": s["url"], "page_date": s.get("page_date"), "retrieved": s["retrieved"],
                        "source_kind": s["kind"]})
        elif sid in reported:
            e = reported[sid]
            out.append({"id": sid, "kind": "reported by others, not the donor's own words", "section": e["outlet"],
                        "text": e["quote"], "url": e["url"], "page_date": e["published"], "retrieved": e["retrieved"],
                        "source_kind": e["tier"], "speaker": e["speaker"], "suggests": e["suggests"],
                        "caveat": e.get("caveat", ""), "read": e.get("read", "")})
        else:
            raise ValueError("subject %s: statement %s is in neither priorities file" % (subject["id"], sid))
    return out


def build_pairings(cands, pairs, subjects_by_id, meetings, snap, fams, prio, reported, reviews, limit=5):
    """Pairings from the accepted reviews: one per funded pair, no two sharing a quote. Ranked by whether the
    reviewer preferred the passage, how specific the hit is, whether the donor's words are its own, the credit
    doubt and whether the minutes confirm it."""
    chosen = {}
    for c in cands:
        if c["decision"] != "accept" or not pairs[(c["official"], c["family"])]["tied"]:
            continue
        key = (c["official"], c["family"])
        rank = (0 if (c["review"] or {}).get("prefer") else 1, 0 if c["tier"] == "specific" else 1,
                0 if subjects_by_id[c["subject"]]["statements"][0] in prio else 1,
                DOUBT_ORDER[c["credit"]["doubt"]], {"confirmed": 0, "consistent": 1}.get(c["minutes"]["status"], 2))
        if key not in chosen or rank < chosen[key][0]:
            chosen[key] = (rank, c)
    ranked = sorted(chosen.values(), key=lambda x: (x[0], x[1]["id"]))
    out, used = [], set()
    by_id = {m["id"]: m for m in meetings}
    for _, c in ranked:
        if len(out) == limit:
            break
        quote_key = (c["meeting_id"], c["official"], c["final_first"])
        if quote_key in used:
            continue
        used.add(quote_key)
        pk = (c["official"], c["family"])
        subj = subjects_by_id[c["subject"]]
        r = c["review"]
        text, first, last = c["final_text"], c["final_first"], c["final_last"]
        money = pairs[pk]
        fam = next(f for f in fams if f["key"] == c["family"])
        c0 = next(x for x in snap["committees"] if x["official"] == c["official"])
        out.append({
            "id": len(out) + 1, "official": c["official"], "office": c0["office"], "district": c0["district"],
            "donor": fam["name"], "donor_kind": fam["kind"], "subject": subj["label"], "candidate_id": c["id"],
            "quote": {"text": text, "meeting_id": c["meeting_id"], "body": c["body"], "date": c["date"],
                      "first_stamp": first, "last_stamp": last, "transcript_url": TRANSCRIPT_URL % c["meeting_id"],
                      "words_of_the_machine_passage": len(c["text"].split())},
            "speaker_credit": {"doubt": c["credit"]["doubt"], "rule": c["credit"]["why"], "cue": c["credit"]["cue"],
                               "cue_stamp": c["credit"]["cue_stamp"], "reviewer": r.get("credit", "unreviewed"),
                               "reviewer_note": r.get("credit_note", ""), "minutes": c["minutes"],
                               "minutes_source": by_id[c["meeting_id"]]["minutes_source"]},
            "donor_words": donor_words(subj, r.get("donor_statements") or subj["statements"][:2], prio, reported),
            "money": {"retrieved": snap["retrieved"], "data_loaded_through": snap["data_loaded_at"],
                      "dataset": snap["dataset"], "per_committee": ff.money_summary(money),
                      "outside_spending_apart": ff.outside_spending(snap, fams, c["official"], c["family"]),
                      "tie": ff.tie_note(money, fams), "duplicates_dropped": len(money["dropped"])},
            "reading": {"in_common": r.get("in_common", ""), "differs": r.get("differs", ""),
                        "match": r["decision"], "hit": c["tier"], "terms": c["anchor_hits"] + c["topic_hits"]},
            "judgement": r.get("judgement_notes", [])})
    return out


def pair_table(pairs, cands, words_by_official, family_kinds):
    rows = []
    for (off, fam), m in pairs.items():
        cs = [c for c in cands if c["official"] == off and c["family"] == fam]
        dec = collections.Counter(c["decision"] for c in cs)
        if dec["accept"]:
            status, reason = "fitting remark found", "%d passage(s) judged on the donor's subject" % dec["accept"]
        elif dec["loose"]:
            status = "same broad subject only"
            reason = "%d passage(s) on the same broad subject, none on the donor's specific one" % dec["loose"]
        elif dec["unreviewed"]:
            status, reason = "candidates awaiting review", "%d passage(s) hit the subject's terms and no person has read them" % dec["unreviewed"]
        elif cs:
            status = "no fitting remark"
            reason = "%d passage(s) hit the subject's terms; each was judged not to be on the donor's subject" % len(cs)
        elif not words_by_official.get(off):
            status, reason = "no fitting remark", "no turn of the official was credited in the meetings read"
        else:
            status = "no fitting remark"
            reason = "no passage in the %d words credited to the official hit the donor's subject terms" % words_by_official[off]
        per = ff.money_summary(m)
        rows.append({"official": off, "family": fam, "tied": m["tied"], "status": status, "reason": reason,
                     "statement_kinds": sorted(family_kinds.get(fam, ())),
                     "candidates": len(cs), "specific": sum(1 for c in cs if c["tier"] == "specific"),
                     "decisions": dict(dec), "committees": [
                         {"committee": p["committee"], "kind": p["kind"], "schedule_a_total": p["schedule_a_total"],
                          "rows": p["schedule_a_rows"]} for p in per]})
    return rows


def earlier_check(meetings, regions, cands):
    """Where the five pairings of the earlier hop (read by a person) stand against this search: whether the rule
    credited the quote to the official, at what doubt, and whether a candidate passage overlaps it."""
    by_id = {m["id"]: m for m in meetings}
    out = []
    for pk in ff.load_json("earlier_picks.json")["pairings"]:
        m = by_id.get(pk["meeting_id"])
        row = {"slug": pk["slug"], "official": pk["official"], "family": pk["family"], "meeting_id": pk["meeting_id"],
               "quote_from": pk["start"], "quote_to": pk["end"], "earlier_doubt": pk["doubt"]}
        if m is None:
            row["outcome"] = "meeting not read in this run"
            out.append(row)
            continue
        doc = m["doc"]
        pos = doc.starts[next(k for k, (s, _) in enumerate(doc.rows) if s == pk["start"])]
        reg = next((r for r in regions[m["id"]] if r["official"] == pk["official"] and r["start"] <= pos < r["end"]), None)
        hits = [c for c in cands if c["meeting_id"] == m["id"] and c["official"] == pk["official"]
                and c["family"] == pk["family"] and c["first_stamp"] <= pk["end"] and c["last_stamp"] >= pk["start"]]
        if reg is None:
            row["outcome"] = "missed: no cue credits the quote's first row to the official"
        else:
            row["rule_doubt"] = ff.credit_tier(doc, reg, pos)[0]
            row["outcome"] = ("found as a candidate (%s)" % ", ".join(sorted({c["decision"] for c in hits}))) if hits else \
                "credited, but no passage hit the donor's subject terms"
        out.append(row)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="read only data/: no network")
    ap.add_argument("--out", default=HERE)
    args = ap.parse_args(argv)
    timer = Timer()
    with timer.step("load data"):
        snap, fams = ff.load_snapshot()
        subjects = ff.load_json("subjects.json")["subjects"]
        prio = {s["id"]: s for s in ff.load_json("priorities.json")["statements"]}
        reported = {e["id"]: e for e in ff.load_json("priorities_reported.json")["entries"]}
        reviews_doc = ff.load_json("reviews.json")
        reviews = {r["id"]: r for r in reviews_doc["reviews"]}
        pairs = ff.funded_pairs(snap)
    for s in subjects:
        for sid in s["statements"]:
            if sid not in prio and sid not in reported:
                raise SystemExit("subject %s names statement %s, which is in neither priorities file" % (s["id"], sid))
    meetings, ext = load_meetings(args.offline, timer)
    log("meetings read: %d (%d sampled, %d beyond the sample)" % (
        len(meetings), sum(1 for m in meetings if m["source"] == "sampled"), ext["added"]))
    for e in ext["errors"][:10]:
        log("NOT READ: " + e)
    with timer.step("credit: find turns"):
        regions = {m["id"]: ff.find_regions(m["doc"]) for m in meetings}
    cands = candidates_for(pairs, subjects, meetings, regions, reviews, timer)
    stale = sorted(set(reviews) - {c["id"] for c in cands})
    subjects_by_id = {s["id"]: s for s in subjects}
    words, words_sampled, per_meeting = collections.Counter(), collections.Counter(), []
    for m in meetings:
        total = len(m["doc"].text.split())
        cw = 0
        for r in regions[m["id"]]:
            n = len(m["doc"].text[r["start"]:r["end"]].split())
            words[r["official"]] += n
            if m["source"] == "sampled":
                words_sampled[r["official"]] += n
            cw += n
        per_meeting.append({"id": m["id"], "body": m["body"], "date": m["date"], "source": m["source"],
                            "caption_rows": len(m["doc"].rows), "caption_words": total, "credited_words": cw,
                            "turns_credited": len(regions[m["id"]]), "transcript_url": TRANSCRIPT_URL % m["id"],
                            "minutes": m["minutes_source"] or m["minutes_note"],
                            "minutes_parsed": ({"present": len(m["minutes"]["present"]), "votes": len(m["minutes"]["votes"]),
                                                "motions": len(m["minutes"]["motions"]),
                                                "usable": ff.minutes_usable(m["minutes"])}
                                               if m["minutes"] else None)})
    with timer.step("pairings"):
        pairings = build_pairings(cands, pairs, subjects_by_id, meetings, snap, fams, prio, reported, reviews)
    kinds = report.subject_kinds(subjects, prio)
    family_kinds = collections.defaultdict(set)
    for sub in subjects:
        family_kinds[sub["family"]].add(kinds[sub["id"]])
    table = pair_table(pairs, cands, words, family_kinds)
    sampled_ids = {m["id"] for m in meetings if m["source"] == "sampled"}
    cands_sampled = [c for c in cands if c["meeting_id"] in sampled_ids]
    table_sampled = pair_table(pairs, cands_sampled, words_sampled, family_kinds)
    for c in cands:
        c.pop("_pos")
    results = {
        "about": "Funder-first pairings. Every figure rests on the meetings listed under `meetings`; `extension` says what "
                 "was and was not read beyond the sampled eleven. Nothing here says why anyone said or gave anything.",
        "mode": "offline (sampled meetings and minutes excerpts only)" if args.offline else "live",
        "money": {"retrieved": snap["retrieved"], "data_loaded_through": snap["data_loaded_at"], "dataset": snap["dataset"]},
        "extension": ext, "meetings": per_meeting,
        "credited_words_by_official": dict(sorted(words.items())),
        "earlier_pairings_check": earlier_check(meetings, regions, cands),
        "pairs": table, "pairs_sampled": table_sampled, "candidates": cands, "stale_reviews": stale,
        "pairings": pairings,
        "metrics": report.metrics(table, cands, per_meeting, pairings, reviews_doc),
        "scopes": {"sampled": report.scope_figures(table_sampled, cands_sampled, kinds),
                   "all": report.scope_figures(table, cands, kinds)},
        "weekly": report.weekly(per_meeting, cands, table),
        "minutes_by_meeting": report.minutes_by_meeting(per_meeting, cands),
        "judgement_steps": report.judgement_steps(reviews_doc, subjects, cands, pairings, timer.t),
        "timings_seconds": dict(timer.t)}
    with timer.step("write"):
        os.makedirs(args.out, exist_ok=True)
        with open(os.path.join(args.out, "results.json"), "w", encoding="utf-8") as f:
            json.dump(results, f, indent=1)
            f.write("\n")
        with open(os.path.join(args.out, "results.md"), "w", encoding="utf-8") as f:
            f.write(report.render_results(results))
        with open(os.path.join(args.out, "pairings.md"), "w", encoding="utf-8") as f:
            f.write(report.render_pairings(results))
    print(report.render_results(results))
    print(report.render_pairings(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
