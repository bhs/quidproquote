"""Matching methods comparison: six ways of proposing quote-to-priority pairings, on identical inputs.

Run once:  python compare.py
Inputs: raw live captions of 11 San Francisco meetings (not confirmed against any recording; a
speaker is only ever a proposal) and 133 class-A donor priority statements, each with its link
and retrieval date (data/). Methods: keyword overlap (two strictnesses), shared named things,
embedding similarity, an AI judge, and an embedding shortlist confirmed by the AI judge. Each is
scored against labelled pairs (data/labels*.json, or data/person_labels/ when people have
labelled). Writes results.md, results.json, pairs-review.md and labelling-sheet.json.

A stage that cannot run (no model key, no embedding model, no network) is reported as NOT RUN
in the results and the exit status is 1; nothing substitutes for it.
"""

import hashlib
import json
import os
import random
import statistics
import sys
import time
import traceback
from collections import Counter

import compare_lib as cl
import embed as em
import judge as jd
import money as mn
import render
import report as rp
import trial_lib as lib

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = os.environ.get("COMPARE_OUT_DIR", HERE)

SEED = 20261030
N_RANDOM = int(os.environ.get("RANDOM_PAIRS", "150"))
N_SHORTLIST = int(os.environ.get("SHORTLIST_N", "100"))
NULL_DRAWS = int(os.environ.get("NULL_DRAWS", "5"))
EMB_NULL_QUOTES = int(os.environ.get("EMB_NULL_QUOTES", "500"))
ERROR_RATE = float(os.environ.get("CAPTION_ERROR_RATE", "0.5"))
EMB_LEVELS = [round(0.30 + 0.01 * i, 2) for i in range(66)]

METHODS = [
    ("keyword", "Keyword overlap: TF-IDF cosine over content words"),
    ("keyword_phrase", "Keyword overlap, tighter: cosine with a shared rare two-word phrase"),
    ("anchor", "Shared named thing (measure, name, acronym); added because the earlier trial found it the most selective lexical way"),
    ("embedding", "Embedding similarity (cosine of sentence embeddings)"),
    ("ai_judge", "AI judge reading each pair"),
    ("embed_ai", "Embedding shortlist (top pairs), each confirmed by the AI judge"),
]


def stage_lexical(quotes, priorities):
    """Scores for every pair, chance counts from random-word quotes, and each way's calibrated level."""
    q_tokens = [lib.tokenize(q["text"]) for q in quotes]
    meeting_of = [q["meeting"] for q in quotes]
    ctx = lib.Context(priorities, q_tokens)
    t0 = time.time()
    scores = lib.score_quotes(ctx, q_tokens)
    seconds = time.time() - t0
    real = lib.counts_at_levels(scores)
    null = {}
    for model, within in (("pooled", False), ("within_meeting", True)):
        rng = random.Random(SEED + (1 if within else 0))
        runs = [lib.counts_at_levels(lib.score_quotes(ctx, lib.draw_null(q_tokens, meeting_of, rng, within)))
                for _ in range(NULL_DRAWS)]
        null[model] = {m: [statistics.mean(v) for v in zip(*[r[m] for r in runs])] for m, _ in lib.METHODS}
    calibrated, worst = {}, {}
    for m, _ in lib.METHODS:
        worst[m] = [max(null["pooled"][m][i], null["within_meeting"][m][i]) for i in range(len(lib.LEVELS[m]))]
        i, lv = lib.calibrated_level(m, real[m], worst[m])
        calibrated[m] = lv
    return {"ctx": ctx, "scores": scores, "real": real, "null_worst": worst, "calibrated": calibrated,
            "seconds": seconds, "q_tokens": q_tokens}


def stage_embedding(quotes, priorities):
    """Embeddings of every quote and priority, the similarity matrix and a chance-calibrated level."""
    emb = em.Embedder()
    np = emb.np
    qv = emb.embed([q["text"] for q in quotes])
    pv = emb.embed([lib.priority_match_text(p) for p in priorities])
    matrix = qv @ pv.T
    real_flat = np.sort(matrix.ravel())

    def counts(flat):
        return [int(flat.size - np.searchsorted(flat, lv, side="left")) for lv in EMB_LEVELS]

    real = counts(real_flat)
    q_tokens = [lib.tokenize(q["text"]) for q in quotes]
    rng = random.Random(SEED + 7)
    runs = []
    meeting_of = [q["meeting"] for q in quotes]
    for _ in range(NULL_DRAWS):
        # embedding on the CPU is the slow part: embed a random sample of the chance quotes and scale
        fake = lib.draw_null(q_tokens, meeting_of, rng, False)
        fake = rng.sample(fake, min(EMB_NULL_QUOTES, len(fake)))
        fv = emb.embed([" ".join(t) for t in fake])
        scale = len(quotes) / len(fake)
        runs.append([c * scale for c in counts(np.sort((fv @ pv.T).ravel()))])
    null_mean = [statistics.mean(v) for v in zip(*runs)]
    calibrated = next((lv for lv, n in zip(EMB_LEVELS, null_mean) if n < 1.0), None)
    return {"emb": emb, "np": np, "pv": pv, "qv": qv, "matrix": matrix, "real": real,
            "null_mean": null_mean, "calibrated": calibrated}


def make_items(quotes, priorities, gold, lex):
    """Identical inputs for every method: labelled pairs, random pairs and synthetic probes."""
    q_by_id = {q["id"]: i for i, q in enumerate(quotes)}
    p_by_id = {p["id"]: i for i, p in enumerate(priorities)}
    items, skipped = [], 0
    used = set()
    for pid in sorted(gold):
        qid, prid = cl.split_pair(pid)
        if qid not in q_by_id or prid not in p_by_id:
            skipped += 1
            continue
        qi, pi = q_by_id[qid], p_by_id[prid]
        used.add((qi, pi))
        items.append({"id": pid, "kind": "labelled", "qi": qi, "pi": pi, "text": quotes[qi]["text"]})
    for qi, pi in cl.random_pairs(N_RANDOM, len(quotes), len(priorities), used, SEED):
        items.append({"id": cl.pair_id(quotes[qi]["id"], priorities[pi]["id"]), "kind": "random",
                      "qi": qi, "pi": pi, "text": quotes[qi]["text"]})
    for pr in cl.probe_items(p_by_id):
        items.append({"id": cl.pair_id(pr["id"], pr["priority_id"]), "kind": "probe", "qi": None,
                      "pi": p_by_id[pr["priority_id"]], "text": pr["text"], "side": pr["side"]})
    roster = [o["surname"] for o in json.load(open(os.path.join(DATA, "committees.json")))["officials"]]
    names = cl.name_tokens(lex["ctx"], roster)
    twins = []
    for it in items:
        if it["kind"] == "random":
            continue
        text, counts = cl.inject_caption_errors(it["text"], ERROR_RATE, it["id"], names)
        if text != it["text"]:
            twins.append({"id": it["id"] + "~err", "kind": "perturbed", "of": it["id"], "qi": it["qi"],
                          "pi": it["pi"], "text": text, "errors": counts})
    items.extend(twins)
    for it in items:
        it["lex"] = cl.lexical_scores(lex["ctx"], it["text"], it["pi"])
        it["emb"] = None
        it["ai"] = None
    return items, skipped


def attach_embeddings(items, emb_stage):
    """Embedding score per item: the matrix entry for an unchanged corpus quote, else embedded now."""
    np, emb, pv, matrix = emb_stage["np"], emb_stage["emb"], emb_stage["pv"], emb_stage["matrix"]
    fresh = [it for it in items if it["qi"] is None or it["kind"] == "perturbed"]
    vecs = emb.embed([it["text"] for it in fresh]) if fresh else []
    for it, v in zip(fresh, vecs):
        it["emb"] = float(v @ pv[it["pi"]])
    for it in items:
        if it["emb"] is None:
            it["emb"] = float(matrix[it["qi"], it["pi"]])


def add_shortlist(items, quotes, priorities, emb_stage, lex):
    """The top-N pairs by embedding similarity become items (or tag items already there)."""
    cutoff, top = em.top_n_cutoff(emb_stage["np"], emb_stage["matrix"], N_SHORTLIST)
    by_id = {it["id"]: it for it in items}
    for qi, pi in top:
        pid = cl.pair_id(quotes[qi]["id"], priorities[pi]["id"])
        if pid in by_id:
            by_id[pid]["shortlisted"] = True
            continue
        it = {"id": pid, "kind": "shortlist", "qi": qi, "pi": pi, "text": quotes[qi]["text"],
              "shortlisted": True, "emb": float(emb_stage["matrix"][qi, pi]), "ai": None,
              "lex": cl.lexical_scores(lex["ctx"], quotes[qi]["text"], pi)}
        items.append(it)
        by_id[pid] = it
    return cutoff


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def meeting_label(quotes, it):
    if it["qi"] is None:
        return "synthetic probe"
    q = quotes[it["qi"]]
    return "%s, %s" % (q["meeting_body"], q["meeting_date"])


def run_ai(items, quotes, priorities, errors):
    """Judge every item once. Returns the Judge (or None when it cannot run)."""
    try:
        judge = jd.Judge(cache_path=os.path.join(OUT, "cache", "judge_cache.json"))
    except jd.JudgeError as exc:
        errors["ai_judge and embed_ai"] = str(exc)
        return None
    prompts = {it["id"]: jd.build_prompt(it["text"], meeting_label(quotes, it), priorities[it["pi"]]) for it in items}
    log("judging %d pairs with %s" % (len(prompts), judge.cfg["model"]))
    recs = judge.judge_many(prompts)
    for it in items:
        it["ai"] = recs[it["id"]]
    bad = [k for k, v in recs.items() if "error" in v]
    if judge.fatal:
        errors["ai_judge and embed_ai"] = "stopped: %s" % judge.fatal
    elif bad:
        errors["ai_judge and embed_ai"] = "%d of %d calls failed, first: %s" % (len(bad), len(recs), recs[bad[0]]["error"])
    return judge


def main():
    t_run = time.time()
    errors = {}
    meetings, quotes, priorities = cl.load_snapshot(DATA)
    judge_labels = cl.load_judge_labels(DATA)
    person = cl.load_person_labels(DATA)
    gold = cl.gold_from_people(person) if person else cl.gold_from_judges(judge_labels)
    committees = json.load(open(os.path.join(DATA, "committees.json"), encoding="utf-8"))
    roster = [{"name": o["name"], "surname": o["surname"], "district": o["district"], "office": o["office"]}
              for o in committees["officials"]]
    log("lexical stage")
    lex = stage_lexical(quotes, priorities)
    items, skipped = make_items(quotes, priorities, gold, lex)
    th = {"keyword": lex["calibrated"]["tfidf"], "keyword_phrase": lex["calibrated"]["both"],
          "anchor": lex["calibrated"]["anchor"], "embedding": None, "cutoff": None}
    emb_stage = None
    try:
        log("embedding stage")
        emb_stage = stage_embedding(quotes, priorities)
        attach_embeddings(items, emb_stage)
        th["embedding"] = emb_stage["calibrated"]
        th["cutoff"] = add_shortlist(items, quotes, priorities, emb_stage, lex)
    except Exception as exc:  # reported, never replaced by another scorer
        errors["embedding and embed_ai"] = "%s: %s" % (type(exc).__name__, exc)
        log(traceback.format_exc())
    t0 = time.time()
    judge = run_ai(items, quotes, priorities, errors)
    ai_wall = time.time() - t0
    rp.assign_proposals(items, th)
    cfg = jd.settings()
    n_pairs = len(quotes) * len(priorities)
    costs = rp.judge_costs(items, cfg)
    emb_seconds = emb_stage["emb"].embed_seconds + emb_stage["emb"].load_seconds if emb_stage else None

    # volume, cost and time per method
    full_counts, ppc, ppt, rcost, rtime = {}, {}, {}, {}, {}
    for m, key in (("keyword", "tfidf"), ("keyword_phrase", "both"), ("anchor", "anchor")):
        lv = th[m]
        full_counts[m] = sum(1 for s in lex["scores"][key].values() if lv is not None and s >= lv - 1e-12)
        ppc[m], rcost[m] = "$0", "$0"
        ppt[m] = render_secs(lex["seconds"] / n_pairs)
        rtime[m] = render_secs(lex["seconds"])
    if emb_stage and th["embedding"] is not None:
        full_counts["embedding"] = int((emb_stage["matrix"] >= th["embedding"]).sum())
    elif emb_stage:
        full_counts["embedding"] = 0
    ppc["embedding"], rcost["embedding"] = "$0", "$0"
    ppt["embedding"] = render_secs(emb_seconds / n_pairs) if emb_seconds else "not run"
    rtime["embedding"] = render_secs(emb_seconds) if emb_seconds else "not run"
    shortlisted = [it for it in items if it["kind"] != "perturbed" and th["cutoff"] is not None
                   and it.get("emb") is not None and it["emb"] >= th["cutoff"] - 1e-12 and it["qi"] is not None]
    confirmed = sum(1 for it in shortlisted if it["prop"]["embed_ai"])
    full_counts["ai_judge"] = "not run on all pairs (%d judged)" % sum(1 for it in items if rp.ai_ok(it))
    full_counts["embed_ai"] = "%d shortlisted, %d confirmed" % (N_SHORTLIST, confirmed) if emb_stage else "not run"
    if costs:
        ppc["ai_judge"], rcost["ai_judge"] = render_usd(costs["dollars"]), render_usd(costs["dollars"] * n_pairs)
        ppt["ai_judge"] = render_secs(costs["seconds"])
        rtime["ai_judge"] = render_secs(costs["seconds"] * n_pairs / cfg["workers"])
        if emb_stage:
            ppc["embed_ai"] = render_usd(costs["dollars"] * N_SHORTLIST / n_pairs)
            rcost["embed_ai"] = render_usd(costs["dollars"] * N_SHORTLIST)
            ppt["embed_ai"] = render_secs((emb_seconds + costs["seconds"] * N_SHORTLIST / cfg["workers"]) / n_pairs)
            rtime["embed_ai"] = render_secs(emb_seconds + costs["seconds"] * N_SHORTLIST / cfg["workers"])
    for m in ("ai_judge", "embed_ai"):
        for d in (ppc, ppt, rcost, rtime):
            d.setdefault(m, "not run")

    # sweeps
    sweeps, full_by, null_by = {}, {}, {}
    for m, key, levels in (("keyword", "tfidf", lib.LEVELS["tfidf"]), ("keyword_phrase", "both", lib.LEVELS["both"]),
                           ("anchor", "anchor", lib.LEVELS["anchor"])):
        sweeps[m] = rp.sweep(items, gold, m, levels)
        full_by[m] = dict(zip(levels, lex["real"][key]))
        null_by[m] = {lv: round(v, 1) for lv, v in zip(levels, lex["null_worst"][key])}
    if emb_stage:
        coarse = sorted({round(0.45 + 0.05 * i, 2) for i in range(9)} | ({th["embedding"]} if th["embedding"] else set()))
        sweeps["embedding"] = rp.sweep(items, gold, "embedding", coarse)
        full_by["embedding"] = dict(zip(EMB_LEVELS, emb_stage["real"]))
        null_by["embedding"] = {lv: round(v, 1) for lv, v in zip(EMB_LEVELS, emb_stage["null_mean"])}
    else:
        sweeps["embedding"], full_by["embedding"], null_by["embedding"] = None, {}, {}

    # speakers (proposals) for the pairs shown
    speakers = {}
    for it in items:
        if it["qi"] is not None and it["kind"] != "random" and it["qi"] not in speakers:
            q = quotes[it["qi"]]
            speakers[it["qi"]] = cl.propose_speaker(q["before"], q["text"], roster)

    donors = sorted({p["donor"] for p in priorities})
    try:
        money, money_date = mn.fetch(donors, committees)
    except Exception as exc:
        money, money_date = {}, ""
        errors["money by committee"] = "%s: %s" % (type(exc).__name__, exc)
    for d, v in money.items():
        if v["error"]:
            errors["money by committee (%s)" % d] = v["error"]

    lab_ready = Counter(gold[it["id"]]["ready"] for it in items if it["kind"] == "labelled")
    lab_overlap = Counter(str(gold[it["id"]]["overlap"]) for it in items if it["kind"] == "labelled")
    vt, rnd = rp.verdict_table(items, gold)
    R = {
        "settings": cfg, "embedding_model": em.model_name(), "seed": SEED, "n_random": N_RANDOM,
        "n_shortlist": N_SHORTLIST, "null_draws": NULL_DRAWS, "error_rate": ERROR_RATE,
        "run_date": time.strftime("%Y-%m-%d"), "errors": errors, "quotes": quotes, "priorities": priorities,
        "n_quotes": len(quotes), "n_meetings": len(meetings), "n_priorities": len(priorities), "n_pairs": n_pairs,
        "gold": gold, "gold_source": "people (data/person_labels)" if person else "the language model's labels from the earlier trial",
        "person_labels": person, "n_labelled": sum(1 for it in items if it["kind"] == "labelled"),
        "labels_skipped": skipped, "gold_counts_ready": dict(lab_ready), "gold_counts_overlap": dict(lab_overlap),
        "thresholds": th, "cutoff": th["cutoff"], "evaluation": rp.evaluation(items, gold, th),
        "stance": rp.stance_by_method(items), "costs": costs, "full_counts": full_counts,
        "per_pair_cost": ppc, "per_pair_time": ppt, "run_cost": rcost, "run_time": rtime,
        "sweeps": sweeps, "sweeps_order": [(m, None) for m in ("keyword", "keyword_phrase", "anchor", "embedding")],
        "full_by_level": full_by, "null_by_level": null_by, "verdicts": (vt, rnd),
        "disagreement_lines": render.disagreement_lines(judge_labels, person, items, gold),
        "error_effect": rp.error_effect(items, gold), "items": items, "speakers": speakers,
        "money": money, "money_date": money_date,
    }
    os.makedirs(OUT, exist_ok=True)
    text = render.results_markdown(R)
    review = render.review_markdown(R)
    for name, body in (("results.md", text), ("pairs-review.md", review)):
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(body + "\n")
    with open(os.path.join(OUT, "labelling-sheet.json"), "w", encoding="utf-8") as f:
        json.dump(render.labelling_sheet(R), f, indent=1)
    summary = {k: R[k] for k in ("settings", "thresholds", "evaluation", "stance", "costs", "full_counts", "errors",
                                 "sweeps", "error_effect", "n_pairs", "gold_counts_ready")}
    summary["verdicts"] = {"gold_by_ai": vt, "random_pairs": rnd}
    with open(os.path.join(OUT, "results.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1, default=str)
    print(text)
    print("\n\n" + review)
    print("\nrun took %.0f s (AI stage %.0f s)" % (time.time() - t_run, ai_wall))
    return 1 if errors else 0


def render_secs(x):
    return render.secs(x)


def render_usd(x):
    return render.usd(x)


if __name__ == "__main__":
    sys.exit(main())
