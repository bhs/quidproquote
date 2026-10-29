"""Matching trial run: quotes from San Francisco Board meetings against donor priorities.

Run once:  python analyze.py
Reads data/ (a snapshot made by collect.py), tries five ways of comparing a quote with a
priority, counts the candidate pairings each finds, counts how many a random-word model finds
at the same settings, estimates what a nightly run would produce and how long one person
would take to review it, and prints the result. Writes results.md and results.json beside it,
and label_sample.json (the pairs two judges read; data/labels.json holds one reader's judgements
and data/labels_model.json a language model's, both against the same written rubric).
"""

import json
import math
import os
import random
import statistics
from collections import Counter, defaultdict

import trial_lib as lib

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

NULL_DRAWS = 20          # random-word runs per chance model
SEED = 20261029
SAMPLE_LOOSE = 8         # pairs drawn at random at each way's loosest level, for a reader
SAMPLE_CALIBRATED = 32   # pairs drawn at random at each way's calibrated level (all 32 for TF-IDF)
TOP_PER_METHOD = 4       # plus the best-scoring pairs of each way

# Reviewer-time model. READ_WPM is a published figure; the rest are stated assumptions,
# not measurements (nobody has timed a reviewer on this task).
READ_WPM = 238           # silent reading of English non-fiction (Brysbaert 2019, meta-analysis)
SPEECH_WPM = 150         # assumed pace of speech when listening to the recording
TRIAGE_OVERHEAD_S = 15   # assumed: decide keep or drop once both texts are read
VERIFY_FIXED_S = {"low": 120, "mid": 270, "high": 480}   # assumed: open video at the stamp, find the
                         # words, identify the speaker, open the donor page, copy citation
WEEKLY_MEETINGS = {"board": 1, "committee": 3}           # about 4 a week (speech survey, Oct 2026)
POOL_SIZES = [None, 300, 1000]   # priority statements in the pool (None: this snapshot's)


def load():
    with open(os.path.join(DATA, "meetings.json"), encoding="utf-8") as f:
        meetings = json.load(f)
    quotes = []
    for m in meetings:
        rows = []
        with open(os.path.join(DATA, "transcripts", "%d.tsv" % m["id"]), encoding="utf-8") as f:
            for line in f:
                stamp, _, text = line.rstrip("\n").partition("\t")
                rows.append((stamp, text))
        m["_rows"] = rows
        for p in lib.build_passages(m["id"], rows):
            p["all_index"] = None
            quotes.append(p)
    with open(os.path.join(DATA, "priorities.json"), encoding="utf-8") as f:
        priorities = json.load(f)
    labels = {}
    for judge, name in (("reader", "labels.json"), ("model", "labels_model.json")):
        labels[judge] = {}
        path = os.path.join(DATA, name)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                labels[judge] = json.load(f).get("labels", {})
    return meetings, quotes, priorities, labels


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)


CLASSES = ("meaningful", "topical", "coincidental", "not_a_quote")


def kappa(pairs):
    """Cohen's kappa for two judges' labels, a list of (label_a, label_b)."""
    n = len(pairs)
    if n == 0:
        return None
    observed = sum(1 for a, b in pairs if a == b) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    expected = sum(ca[c] * cb[c] for c in CLASSES) / (n * n)
    return (observed - expected) / (1 - expected) if expected < 1 else None


def fisher_two_sided(a, n1, b, n2):
    """Two-sided Fisher exact p for a of n1 against b of n2 (small samples, no libraries)."""
    k = a + b
    total = math.comb(n1 + n2, k)

    def prob(x):
        return math.comb(n1, x) * math.comb(n2, k - x) / total

    p_obs = prob(a)
    lo, hi = max(0, k - n2), min(n1, k)
    return min(1.0, sum(prob(x) for x in range(lo, hi + 1) if prob(x) <= p_obs + 1e-12))


def pct(x):
    return "%.0f%%" % (100 * x)


def main():
    meetings, passages, priorities, labels = load()
    mtg = {m["id"]: m for m in meetings}
    quotes = [p for p in passages if lib.is_substantive(p)]
    q_tokens = [lib.tokenize(q["text"]) for q in quotes]
    meeting_of = [q["meeting"] for q in quotes]
    pool_sizes = [len(priorities) if n is None else n for n in POOL_SIZES]
    ctx = lib.Context(priorities, q_tokens)
    scores = lib.score_quotes(ctx, q_tokens)
    real = lib.counts_at_levels(scores)

    # ---- chance: two random-word models
    null = {}
    for model, within in (("pooled", False), ("within_meeting", True)):
        rng = random.Random(SEED + (1 if within else 0))
        runs = []
        for _ in range(NULL_DRAWS):
            fake = lib.draw_null(q_tokens, meeting_of, rng, within)
            runs.append(lib.counts_at_levels(lib.score_quotes(ctx, fake)))
        null[model] = {}
        for m, _ in lib.METHODS:
            per_level = list(zip(*[r[m] for r in runs]))
            null[model][m] = {"mean": [statistics.mean(v) for v in per_level],
                              "max": [max(v) for v in per_level]}

    # ---- calibrated level per method
    calibrated = {}
    for m, _ in lib.METHODS:
        worst = [max(null["pooled"][m]["mean"][i], null["within_meeting"][m]["mean"][i])
                 for i in range(len(lib.LEVELS[m]))]
        i, lv = lib.calibrated_level(m, real[m], worst)
        calibrated[m] = {"index": i, "level": lv}

    def candidates(m, point):
        idx = 0 if point == "loose" else calibrated[m]["index"]
        if idx is None:
            return {}
        lv = lib.LEVELS[m][idx]
        return {k: s for k, s in scores[m].items() if s >= lv - 1e-12}

    loose = {m: candidates(m, "loose") for m, _ in lib.METHODS}
    cands = {m: candidates(m, "calibrated") for m, _ in lib.METHODS}

    def pair_key(k):
        return "%s|%s" % (quotes[k[0]]["id"], priorities[k[1]]["id"])

    # ---- shape of each method's candidates
    shape = {}
    for m, _ in lib.METHODS:
        c = cands[m]
        qs = {k[0] for k in c}
        ps = Counter(k[1] for k in c)
        donors = Counter(priorities[k[1]]["donor"] for k in c)
        bodies = Counter("Board" if mtg[quotes[k[0]]["meeting"]]["body"] == "Board of Supervisors"
                         else "Committee" for k in c)
        top3 = sum(n for _, n in ps.most_common(3))
        shape[m] = {
            "pairs": len(c), "quotes": len(qs), "priorities": len(ps),
            "pairs_per_quote": (len(c) / len(qs)) if qs else 0.0,
            "top3_priority_share": (top3 / len(c)) if c else 0.0,
            "by_donor": dict(donors.most_common()),
            "by_body": dict(bodies),
        }
    names = [m for m, _ in lib.METHODS]
    overlap = {}
    for a in names:
        for b in names:
            sa, sb = set(cands[a]), set(cands[b])
            overlap["%s|%s" % (a, b)] = (len(sa & sb) / len(sa | sb)) if (sa | sb) else 0.0

    # ---- pairs for a reader: random at the loosest level, random at the calibrated level,
    # and the best-scoring pairs of each way
    sample = {}
    for m in names:
        picks = (("loose", lib.stable_order(list(loose[m]), "loose-" + m)[:SAMPLE_LOOSE]),
                 ("calibrated", lib.stable_order(list(cands[m]), "cal-" + m)[:SAMPLE_CALIBRATED]),
                 ("top", sorted(cands[m], key=lambda k: (-cands[m][k], k))[:TOP_PER_METHOD]))
        for point, ks in picks:
            for k in ks:
                sample.setdefault(k, {"tags": set()})["tags"].add((m, point))
    sample_rows = []
    for k, e in sorted(sample.items(), key=lambda kv: pair_key(kv[0])):
        q, p = quotes[k[0]], priorities[k[1]]
        mt = mtg[q["meeting"]]
        sample_rows.append({
            "pair": pair_key(k),
            "drawn_for": sorted("%s/%s" % t for t in e["tags"]),
            "scores": {m: round(scores[m][k], 3) for m in names if k in scores[m]},
            "quote": {"meeting": "%s, %s" % (mt["body"], mt["date"]), "stamp": q["start"],
                      "url": mt["url"], "text": q["text"]},
            "priority": {"donor": p["donor"], "section": p["section"], "url": p["url"],
                         "text": p["text"]},
        })
    with open(os.path.join(HERE, "label_sample.json"), "w", encoding="utf-8") as f:
        json.dump(sample_rows, f, indent=1, ensure_ascii=False)

    # ---- judges' labels, per way and operating point (pairs drawn at random only)
    def judge_tables(lab):
        judged = {}
        for m in names:
            for point in ("loose", "calibrated"):
                tag = "%s/%s" % (m, point)
                rows = [r for r in sample_rows if tag in r["drawn_for"]]
                tally = Counter(lab[r["pair"]]["label"] for r in rows if r["pair"] in lab)
                n = sum(tally.values())
                entry = {"sampled": len(rows), "judged": n, "tally": dict(tally)}
                for c in CLASSES:
                    lo, hi = wilson(tally.get(c, 0), n)
                    entry[c + "_share"] = [tally.get(c, 0) / n if n else None, lo, hi]
                judged[tag] = entry
        top = {}
        for m in names:
            rows = [r for r in sample_rows if "%s/top" % m in r["drawn_for"]]
            top[m] = dict(Counter(lab[r["pair"]]["label"] for r in rows if r["pair"] in lab))
        return judged, top

    judges = ("reader", "model")
    judged_by, top_by = {}, {}
    for j in judges:
        judged_by[j], top_by[j] = judge_tables(labels[j])
    judged, top_judged = judged_by["model"], top_by["model"]

    # ---- agreement of the two judges on the pairs both labelled
    both_labelled = [r["pair"] for r in sample_rows
                     if r["pair"] in labels["reader"] and r["pair"] in labels["model"]]
    lab_pairs = [(labels["reader"][k]["label"], labels["model"][k]["label"]) for k in both_labelled]
    confusion = Counter(lab_pairs)
    mean_pairs = [("meaningful" if a == "meaningful" else "other",
                   "meaningful" if b == "meaningful" else "other") for a, b in lab_pairs]
    agreement = {
        "pairs": len(lab_pairs),
        "same_label": sum(1 for a, b in lab_pairs if a == b),
        "kappa_four_labels": kappa(lab_pairs),
        "same_on_meaningful_or_not": sum(1 for a, b in mean_pairs if a == b),
        "kappa_meaningful_or_not": None,
        "confusion": {"%s|%s" % k: v for k, v in sorted(confusion.items())},
    }
    if mean_pairs:
        po = agreement["same_on_meaningful_or_not"] / len(mean_pairs)
        ca = Counter(a for a, _ in mean_pairs)
        cb = Counter(b for _, b in mean_pairs)
        pe = sum(ca[c] * cb[c] for c in ("meaningful", "other")) / len(mean_pairs) ** 2
        agreement["kappa_meaningful_or_not"] = (po - pe) / (1 - pe) if pe < 1 else None
    # does one way's share of meaningful pairs differ from another's? (model judge, calibrated setting)
    working = [m for m in names if judged["%s/calibrated" % m]["judged"] >= 10]
    way_tests = {}
    for i, a_ in enumerate(working):
        for b_ in working[i + 1:]:
            ja, jb = judged["%s/calibrated" % a_], judged["%s/calibrated" % b_]
            way_tests["%s|%s" % (a_, b_)] = fisher_two_sided(
                ja["tally"].get("meaningful", 0), ja["judged"], jb["tally"].get("meaningful", 0), jb["judged"])
    # how many different quotes and priorities the meaningful pairs rest on, per way
    clusters = {}
    for m in names:
        rows = [r for r in sample_rows if "%s/calibrated" % m in r["drawn_for"]
                and labels["model"].get(r["pair"], {}).get("label") == "meaningful"]
        clusters[m] = {"meaningful_pairs": len(rows),
                       "distinct_quotes": len({r["pair"].split("|")[0] for r in rows}),
                       "distinct_priorities": len({r["pair"].split("|")[1] for r in rows})}
    disagreements = [{"pair": k, "reader": labels["reader"][k]["label"], "model": labels["model"][k]["label"]}
                     for k in both_labelled if labels["reader"][k]["label"] != labels["model"][k]["label"]]
    # pairs both judges labelled meaningful, per way at the calibrated setting
    sample_by_pair = {r["pair"]: r for r in sample_rows}
    both_meaningful = {}
    for m in names:
        keys = [r["pair"] for r in sample_rows if "%s/calibrated" % m in r["drawn_for"]
                and r["pair"] in labels["reader"]]
        both_meaningful[m] = {
            "judged_by_both": len(keys),
            "both_meaningful": sum(1 for k in keys if labels["reader"][k]["label"] == "meaningful"
                                   and labels["model"].get(k, {}).get("label") == "meaningful"),
        }

    # ---- volume of a nightly run
    def volume_for(cset):
        per_meeting = {}
        out = {}
        for m in names:
            cnt = Counter(quotes[k[0]]["meeting"] for k in cset[m])
            per_meeting[m] = {mid: cnt.get(mid, 0) for mid in mtg}
            board = [n for mid, n in per_meeting[m].items() if mtg[mid]["body"] == "Board of Supervisors"]
            comm = [n for mid, n in per_meeting[m].items() if mtg[mid]["body"] != "Board of Supervisors"]
            b, c = statistics.mean(board), statistics.mean(comm)
            weekly = b * WEEKLY_MEETINGS["board"] + c * WEEKLY_MEETINGS["committee"]
            out[m] = {"per_board_meeting": b, "per_committee_meeting": c, "weekly": weekly,
                      "nightly_average": weekly / 7.0, "busy_night": max(board) + max(comm),
                      "per_priority_per_week": weekly / len(priorities)}
        return out, per_meeting

    volume, per_meeting = volume_for(cands)
    volume_loose, per_meeting_loose = volume_for(loose)

    # ---- reviewer time
    review = {}
    for m in names:
        c = cands[m]
        if not c:
            continue
        triage = []
        verify_audio = []
        for k in c:
            qw = len(quotes[k[0]]["text"].split())
            pw = len(lib.priority_match_text(priorities[k[1]]).split())
            triage.append((qw + pw) / READ_WPM * 60 + TRIAGE_OVERHEAD_S)
            verify_audio.append(qw / SPEECH_WPM * 60)
        keep = judged["%s/calibrated" % m]["meaningful_share"][0]
        if keep is None:
            keep = 0.0
        review[m] = {"triage_s_per_pair": statistics.mean(triage),
                     "audio_s_per_pair": statistics.mean(verify_audio),
                     "kept_share": keep}

    def minutes(m, pairs, fixed):
        r = review[m]
        n_keep = pairs * r["kept_share"]
        return (pairs * r["triage_s_per_pair"] + n_keep * (fixed + r["audio_s_per_pair"])) / 60.0

    budget_min = 30
    capacity = {}
    for m in review:
        r = review[m]
        capacity[m] = {}
        for tag, fixed in VERIFY_FIXED_S.items():
            per_pair_s = r["triage_s_per_pair"] + r["kept_share"] * (fixed + r["audio_s_per_pair"])
            capacity[m][tag] = budget_min * 60.0 / per_pair_s

    result = {
        "snapshot": {
            "meetings": [{"id": m["id"], "body": m["body"], "date": m["date"], "caption_rows": m["rows"]}
                         for m in meetings],
            "passages": len(passages), "quotes_substantive": len(quotes),
            "priorities": len(priorities),
            "priorities_by_donor": dict(Counter(p["donor"] for p in priorities).most_common()),
            "pairs_compared": len(quotes) * len(priorities),
        },
        "levels": lib.LEVELS,
        "real_counts": real,
        "null": null,
        "null_draws_per_model": NULL_DRAWS,
        "calibrated": calibrated,
        "shape": shape,
        "overlap_jaccard": overlap,
        "judged_random_draws": judged_by,
        "judged_top_ranked": top_by,
        "judge_agreement": agreement,
        "judge_disagreements": disagreements,
        "way_comparison_fisher_p": way_tests,
        "meaningful_pair_clusters": clusters,
        "both_judges_meaningful_at_calibrated": both_meaningful,
        "volume": volume,
        "volume_at_loosest_level": volume_loose,
        "per_meeting_candidates": per_meeting,
        "per_meeting_candidates_loosest": per_meeting_loose,
        "review": review,
        "review_capacity_pairs_in_30_min": capacity,
        "parameters": {"READ_WPM": READ_WPM, "SPEECH_WPM": SPEECH_WPM,
                       "TRIAGE_OVERHEAD_S": TRIAGE_OVERHEAD_S, "VERIFY_FIXED_S": VERIFY_FIXED_S,
                       "WEEKLY_MEETINGS": WEEKLY_MEETINGS, "POOL_SIZES": pool_sizes},
    }
    with open(os.path.join(HERE, "results.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1)

    # ---- the readable report
    out = []
    w = out.append
    w("# Matching trial run: results\n")
    s = result["snapshot"]
    w("Generated by `analyze.py` from the snapshot in `data/`. %d meetings, %d caption rows, "
      "%d passages (%d substantive), %d donor priority statements, %d pairs compared per way.\n"
      % (len(meetings), sum(m["rows"] for m in meetings), s["passages"], s["quotes_substantive"],
         s["priorities"], s["pairs_compared"]))
    w("## Candidate pairings per way, against chance\n")
    w("Chance = the same rule run on quotes of the same lengths whose words are drawn at random "
      "(%d draws per model; 'pooled' draws from all quotes' words, 'meeting' from the quote's own "
      "meeting). Each cell: real count / chance mean (chance max).\n" % NULL_DRAWS)
    for m, label in lib.METHODS:
        w("### %s: %s\n" % (m, label))
        w("| level | real | chance, pooled | chance, meeting |")
        w("|---|---|---|---|")
        for i, lv in enumerate(lib.LEVELS[m]):
            mark = " **<- calibrated**" if calibrated[m]["index"] == i else ""
            w("| >= %s%s | %d | %.1f (%d) | %.1f (%d) |" % (
                lv, mark, real[m][i], null["pooled"][m]["mean"][i], null["pooled"][m]["max"][i],
                null["within_meeting"][m]["mean"][i], null["within_meeting"][m]["max"][i]))
        if calibrated[m]["level"] is None:
            w("\nNo level reached a chance mean below one pair.")
        w("")
    w("## Shape of the candidates at each way's calibrated level\n")
    w("| way | level | pairs | quotes | priorities | pairs per quote | top-3 priorities' share |")
    w("|---|---|---|---|---|---|---|")
    for m in names:
        sh = shape[m]
        w("| %s | %s | %d | %d | %d | %.2f | %s |" % (
            m, calibrated[m]["level"], sh["pairs"], sh["quotes"], sh["priorities"],
            sh["pairs_per_quote"], pct(sh["top3_priority_share"])))
    w("")
    w("Candidates by donor:\n")
    for m in names:
        w("- %s: %s" % (m, "; ".join("%s %d" % (d, n) for d, n in shape[m]["by_donor"].items()) or "none"))
    w("\nOverlap (Jaccard) of candidate sets:\n")
    w("| | " + " | ".join(names) + " |")
    w("|---|" + "---|" * len(names))
    for a in names:
        w("| %s | " % a + " | ".join("%.2f" % overlap["%s|%s" % (a, b)] for b in names) + " |")
    w("\n## What two judges made of the sampled pairs\n")
    w("%d pairs were drawn (see `label_sample.json`). Two judges labelled them against the same "
      "rubric: a reader (`data/labels.json`, the pairs drawn at %d per way at the calibrated level "
      "and %d at the loosest) and a language model (`data/labels_model.json`, every pair drawn, "
      "%d per way at the calibrated level). 'loose' is the way's loosest level and 'calibrated' the "
      "level where a random-word run yields under one pair. Random draws only; share with 95%% range.\n"
      % (len(sample_rows), 14, SAMPLE_LOOSE, SAMPLE_CALIBRATED))
    for j, title in (("model", "Language model judge"), ("reader", "Reader")):
        w("### %s\n" % title)
        w("| way / point | judged | meaningful | topical only | coincidental | not a quote | meaningful share (95% range) |")
        w("|---|---|---|---|---|---|---|")
        for m in names:
            for point in ("loose", "calibrated"):
                e = judged_by[j]["%s/%s" % (m, point)]
                t = e["tally"]
                sh_, lo, hi = e["meaningful_share"]
                w("| %s / %s | %d of %d | %d | %d | %d | %d | %s |" % (
                    m, point, e["judged"], e["sampled"], t.get("meaningful", 0), t.get("topical", 0),
                    t.get("coincidental", 0), t.get("not_a_quote", 0),
                    "n/a" if sh_ is None else "%s (%s to %s)" % (pct(sh_), pct(lo), pct(hi))))
        w("")
    w("### Agreement of the two judges\n")
    ag = agreement
    w("%d pairs were labelled by both. Same label on %d (%s); Cohen's kappa %.2f on the four labels. "
      "On meaningful against everything else: same on %d (%s), kappa %.2f.\n" % (
          ag["pairs"], ag["same_label"], pct(ag["same_label"] / ag["pairs"]), ag["kappa_four_labels"],
          ag["same_on_meaningful_or_not"], pct(ag["same_on_meaningful_or_not"] / ag["pairs"]),
          ag["kappa_meaningful_or_not"]))
    w("| reader \\ model | " + " | ".join(CLASSES) + " |")
    w("|---|" + "---|" * len(CLASSES))
    for a_ in CLASSES:
        w("| %s | " % a_ + " | ".join(str(confusion.get((a_, b_), 0)) for b_ in CLASSES) + " |")
    w("\nPairs where the two differ:\n")
    for d in disagreements:
        w("- %s: reader %s, model %s" % (d["pair"], d["reader"], d["model"]))
    w("\nAt the calibrated setting, pairs the reader labelled that both judges called meaningful:\n")
    for m in names:
        bm = both_meaningful[m]
        w("- %s: %d of %d" % (m, bm["both_meaningful"], bm["judged_by_both"]))
    w("\nThe two judges are not independent: the reader's labels were reconciled with the model's "
      "where the transcript showed who was speaking, so agreement overstates how reliably a second "
      "person would label the same pairs. No person outside the trial labelled any pair.\n")
    w("### Do the ways differ?\n")
    w("Share meaningful at the calibrated setting, model judge, two ways compared by Fisher's exact test "
      "(two-sided p; TF-IDF's 32 pairs are all of its candidates, the others are random draws of 32):\n")
    for k, v in sorted(way_tests.items()):
        w("- %s: p = %.3f" % (k.replace("|", " against "), v))
    w("\nWhat the meaningful pairs rest on (model judge, calibrated setting):\n")
    for m in names:
        c = clusters[m]
        w("- %s: %d meaningful pairs, %d different quotes, %d different priorities" % (
            m, c["meaningful_pairs"], c["distinct_quotes"], c["distinct_priorities"]))
    w("\nBest-scoring pairs of each way (not a random draw), model judge:\n")
    for m in names:
        w("- %s: %s" % (m, ", ".join("%s %d" % (k, v) for k, v in sorted(top_judged[m].items())) or "none"))
    w("\n## A nightly run\n")
    w("| way | per Board meeting | per committee meeting | per week | per night, average | busy night |")
    w("|---|---|---|---|---|---|")
    for m in names:
        v = volume[m]
        w("| %s | %.1f | %.1f | %.1f | %.1f | %d |" % (
            m, v["per_board_meeting"], v["per_committee_meeting"], v["weekly"],
            v["nightly_average"], v["busy_night"]))
    w("\nAt each way's loosest level (candidates including those chance would also produce):\n")
    w("| way | per week | per night, average | busy night | chance per run (pooled mean) |")
    w("|---|---|---|---|---|")
    for m in names:
        v = volume_loose[m]
        w("| %s | %.1f | %.1f | %d | %.1f |" % (m, v["weekly"], v["nightly_average"], v["busy_night"],
                                             null["pooled"][m]["mean"][0]))
    w("\nWith the pool of priorities scaled (candidates per week = per-priority rate x pool size):\n")
    w("| way | " + " | ".join("%d statements" % n for n in pool_sizes) + " |")
    w("|---|" + "---|" * len(pool_sizes))
    for m in names:
        w("| %s | " % m + " | ".join("%.0f" % (volume[m]["per_priority_per_week"] * n)
                                      for n in pool_sizes) + " |")
    w("\nReview time for one person. Triage reads both texts at %d words a minute plus %d s; pairs "
      "judged meaningful are then verified (listening at the stamp at %d words a minute, plus a fixed "
      "%s s for navigation, speaker and donor-page checks). Fixed times are assumptions, not measurements.\n"
      % (READ_WPM, TRIAGE_OVERHEAD_S, SPEECH_WPM,
         "/".join(str(v) for v in VERIFY_FIXED_S.values())))
    w("| way | triage s per pair | kept share | minutes on an average night (low/mid/high) | "
      "minutes on a busy night (low/mid/high) | pairs reviewable in 30 min (high/mid/low) |")
    w("|---|---|---|---|---|---|")
    for m in names:
        if m not in review:
            w("| %s | - | - | - | - | - |" % m)
            continue
        r = review[m]
        avg = [minutes(m, volume[m]["nightly_average"], f) for f in VERIFY_FIXED_S.values()]
        busy = [minutes(m, volume[m]["busy_night"], f) for f in VERIFY_FIXED_S.values()]
        cap = [capacity[m][t] for t in ("high", "mid", "low")]
        w("| %s | %.0f | %s | %s | %s | %s |" % (
            m, r["triage_s_per_pair"], pct(r["kept_share"]),
            "/".join("%.0f" % x for x in avg), "/".join("%.0f" % x for x in busy),
            "/".join("%.0f" % x for x in cap)))
    text = "\n".join(out) + "\n"
    with open(os.path.join(HERE, "results.md"), "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    print("## Pairs the judges read, with their labels\n")
    for r in sample_rows:
        rl, ml = labels["reader"].get(r["pair"], {}), labels["model"].get(r["pair"], {})
        print("[reader: %s | model: %s] %s  ways=%s scores=%s" % (
            rl.get("label", "-"), ml.get("label", "-"), r["pair"], ",".join(r["drawn_for"]), r["scores"]))
        print("  QUOTE (%s, %s): %s" % (r["quote"]["meeting"], r["quote"]["stamp"],
                                       r["quote"]["text"]))
        print("  PRIORITY (%s, %s): %s" % (r["priority"]["donor"], r["priority"]["section"],
                                          r["priority"]["text"]))
        for who, lab in (("reader", rl), ("model", ml)):
            if lab.get("note"):
                print("  NOTE (%s): %s" % (who, lab["note"]))


if __name__ == "__main__":
    main()
