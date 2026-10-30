"""Person-labelled matching check: run every method over real captions and donor priorities, build (or
reuse) the blind labelling sheet, and score the methods against what people labelled.

Run once:  python method/run.py        (from the directory that holds method/; outputs go there)

Inputs: raw live captions of 11 San Francisco meetings and 133 class-A donor priority statements
(method/data). Methods: keyword overlap (two strictnesses), shared named things, embedding
similarity, an AI judge, and an embedding shortlist confirmed by the AI judge, each at the setting
where random-word quotes yield fewer than one pair per run (the AI judge is described in results.md).

Writes results.md, results.json and matches-that-stand-out.md to CHECK_OUT_DIR (default: the working
directory), and, only when no sheet exists yet, labelling/{blind-sheet.json, sheet-key.json,
label.html}. An existing sheet is never rebuilt, so people's labels stay valid; set REBUILD_SHEET=1
to start a new one. Labels come from labelling/person_labels/*.json (see its README).

A stage that cannot run (no model key, no embedding model, no network) is reported in the results and
the exit status is 1; nothing substitutes for it.
"""

import json
import os
import random
import sys
import tempfile
import time
import traceback

import check_lib as ck
import compare_lib as cl
import embed as em
import judge as jd
import labeller
import render_check as rc
import stages
import trial_lib as lib

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = os.environ.get("CHECK_OUT_DIR", os.getcwd())
LABELLING = os.environ.get("CHECK_LABELLING_DIR", os.path.join(OUT, "labelling"))
PEOPLE = os.environ.get("CHECK_PEOPLE_DIR", os.path.join(LABELLING, "person_labels"))

SEED = 20261030
N_RANDOM = int(os.environ.get("RANDOM_PAIRS", "150"))
N_AI_NULL = int(os.environ.get("AI_NULL_PAIRS", "100"))
N_SHORTLIST = int(os.environ.get("SHORTLIST_N", "100"))
EMB_POOL_CAP = int(os.environ.get("EMB_POOL_CAP", "300"))
NULL_DRAWS = int(os.environ.get("NULL_DRAWS", "15"))
EMB_NULL_DRAWS = int(os.environ.get("EMB_NULL_DRAWS", "8"))
EMB_NULL_QUOTES = int(os.environ.get("EMB_NULL_QUOTES", "500"))
SHEET_PER_METHOD = int(os.environ.get("SHEET_PER_METHOD", "12"))
SHEET_PER_LOOSER = int(os.environ.get("SHEET_PER_LOOSER", "5"))
SHEET_RANDOM = int(os.environ.get("SHEET_RANDOM", "12"))

os.environ.setdefault("MATCH_JUDGE_TIME_BUDGET_S", "480")
os.environ.setdefault("MATCH_JUDGE_WORKERS", "16")
JUDGE_TAIL_S = 180  # extra time for the random-word passages and the sheet's pairs, after the pool's budget


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def main():
    t_run = time.time()
    errors = {}
    meetings, quotes, priorities = cl.load_snapshot(DATA)
    q_index = {q["id"]: i for i, q in enumerate(quotes)}
    p_index = {p["id"]: i for i, p in enumerate(priorities)}
    pid_of = lambda qi, pi: cl.pair_id(quotes[qi]["id"], priorities[pi]["id"])
    parse = lambda pid: tuple(q_index[x] if k == 0 else p_index[x] for k, x in enumerate(cl.split_pair(pid)))

    log("lexical stage")
    lex = stages.stage_lexical(quotes, priorities, SEED, NULL_DRAWS)
    th = {m: lex["calibrated"][key] for m, key in stages.LEX_KEYS.items()}
    props = {m: None for m in ck.METHODS}
    looser = {}
    for m, key in stages.LEX_KEYS.items():
        lv, levels = th[m], lib.LEVELS[key]
        sc = lex["scores"][key]
        props[m] = {pid_of(*k) for k, s in sc.items() if lv is not None and s >= lv - 1e-12}
        looser[m] = set()
        if lv is not None and levels.index(lv) > 0:
            lo = levels[levels.index(lv) - 1]
            looser[m] = {pid_of(*k) for k, s in sc.items() if lo - 1e-12 <= s < lv - 1e-12}

    emb_stage, emb_scores, shortlist, cutoff = None, {}, [], None
    try:
        log("embedding stage")
        emb_stage = stages.stage_embedding(quotes, priorities, lex, SEED, EMB_NULL_DRAWS, EMB_NULL_QUOTES)
        np, matrix, cal = emb_stage["np"], emb_stage["matrix"], emb_stage["calibrated"]
        th["embedding"] = cal
        props["embedding"], looser["embedding"] = set(), set()
        if cal is not None:
            hits = np.argwhere(matrix >= cal - 1e-9)
            props["embedding"] = {pid_of(int(a), int(b)) for a, b in hits}
            near = np.argwhere((matrix >= cal - 0.05 - 1e-9) & (matrix < cal - 1e-9))
            looser["embedding"] = {pid_of(int(a), int(b)) for a, b in near}
            ranked = sorted(((float(matrix[a, b]), int(a), int(b)) for a, b in hits), reverse=True)
            emb_scores = {pid_of(a, b): s for s, a, b in ranked}
        cutoff, top = em.top_n_cutoff(np, matrix, N_SHORTLIST)
        shortlist = [pid_of(a, b) for a, b in top]
    except Exception as exc:  # reported, never replaced by another scorer
        errors["embedding and embed_ai"] = "%s: %s" % (type(exc).__name__, exc)
        log(traceback.format_exc())

    _write_chance_counts(OUT, lex, emb_stage, th, props, errors)

    def emb_score(pid):
        qi, pi = parse(pid)
        return float(emb_stage["matrix"][qi, pi]) if emb_stage else None

    # random pairs (false alarms) and the frozen sheet, if any
    rng = random.Random(SEED + 11)
    random_ids = []
    seen = set()
    while len(random_ids) < N_RANDOM:
        k = (rng.randrange(len(quotes)), rng.randrange(len(priorities)))
        if k not in seen:
            seen.add(k)
            random_ids.append(pid_of(*k))
    sheet_path = os.path.join(LABELLING, "blind-sheet.json")
    key_path = os.path.join(LABELLING, "sheet-key.json")
    frozen = os.path.exists(sheet_path) and os.environ.get("REBUILD_SHEET") != "1"
    sheet_doc = key_doc = None
    if frozen:
        with open(sheet_path, encoding="utf-8") as f:
            sheet_doc = json.load(f)
        with open(key_path, encoding="utf-8") as f:
            key_doc = json.load(f)
        missing = [e["pair"] for e in sheet_doc["pairs"]
                   if cl.split_pair(e["pair"])[0] not in q_index or cl.split_pair(e["pair"])[1] not in p_index]
        if missing:
            raise SystemExit("the frozen sheet names pairs that are not in the snapshot (first: %s); rebuild it with "
                             "REBUILD_SHEET=1 and relabel" % missing[0])

    # the pool the AI judge reads: every lexical proposal, the top of the embedding proposals, the shortlist, random pairs
    base = set(props["keyword"]) | set(props["keyword_phrase"]) | set(props["anchor"]) | set(shortlist) | set(random_ids)
    base |= set(list(emb_scores)[:EMB_POOL_CAP])
    ai, judge = {}, None
    null_pairs = []
    nrng = random.Random(SEED + 13)
    null_quotes = lib.draw_null(lex["q_tokens"], lex["meeting_of"], nrng, False)
    for _ in range(N_AI_NULL):
        qi, pi = nrng.randrange(len(quotes)), nrng.randrange(len(priorities))
        null_pairs.append(("NULL-%03d" % len(null_pairs), pi, " ".join(null_quotes[qi])))

    def pair_prompt(pid):
        qi, pi = parse(pid)
        q = quotes[qi]
        return jd.build_prompt(q["text"], "%s, %s" % (q["meeting_body"], q["meeting_date"]), priorities[pi])

    def judge_pairs(ids):
        nonlocal judge
        todo = {pid: pair_prompt(pid) for pid in ids if pid not in ai}
        if not todo or errors.get("ai_judge and embed_ai"):
            return
        try:
            if judge is None:
                judge = jd.Judge(cache_path=os.environ.get(
                    "CHECK_JUDGE_CACHE", os.path.join(tempfile.gettempdir(), "judge_cache.json")))
        except jd.JudgeError as exc:
            errors["ai_judge and embed_ai"] = str(exc)
            return
        log("judging %d pairs with %s" % (len(todo), judge.cfg["model"]))
        recs = judge.judge_many(todo)
        ai.update(recs)
        bad = [k for k, v in recs.items() if "error" in v]
        if judge.fatal:
            errors["ai_judge and embed_ai"] = "stopped: %s" % judge.fatal
        elif bad:
            errors["ai_judge and embed_ai"] = "%d of %d calls failed, first: %s" % (len(bad), len(recs), recs[bad[0]]["error"])

    t0 = time.time()
    judge_pairs(sorted(base | ({e["pair"] for e in sheet_doc["pairs"]} if frozen else set())))
    ai_wall = time.time() - t0
    if judge is not None:
        # the pool may have used the whole budget; the null passages and the sheet's pairs get their own tail
        judge.started = time.time() - judge.cfg["time_budget_s"] + JUDGE_TAIL_S
    ai_ok = lambda pid: pid in ai and "error" not in ai[pid]
    if judge is not None and not errors.get("ai_judge and embed_ai"):
        props["ai_judge"] = {pid for pid in base if ai_ok(pid) and jd.is_proposed(ai[pid])}
        props["embed_ai"] = {pid for pid in shortlist if ai_ok(pid) and jd.is_proposed(ai[pid])} if emb_stage else None
    # the AI judge's false alarms on random-word passages
    ai_null = {"pairs": 0, "flagged": 0}
    if judge is not None and not errors.get("ai_judge and embed_ai"):
        recs = judge.judge_many({n: jd.build_prompt(t, "random words, no meeting", priorities[pi])
                                 for n, pi, t in null_pairs})
        ok = [r for r in recs.values() if "error" not in r]
        ai_null = {"pairs": len(ok), "flagged": sum(1 for r in ok if jd.is_proposed(r))}
        if len(ok) < len(recs):
            errors["ai_judge null pairs"] = "%d of %d calls failed" % (len(recs) - len(ok), len(recs))

    # the blind sheet
    if not frozen:
        strata = ck.sample_sheet({m: props[m] for m in ck.METHODS}, looser, random_ids,
                                 SHEET_PER_METHOD, SHEET_PER_LOOSER, SHEET_RANDOM)
        judge_pairs(list(strata))
        entries = []
        for pid in strata:
            qi, pi = parse(pid)
            entries.append(ck.blind_entry(pid, quotes[qi], priorities[pi]))
        assert not any(ck.leaks_method(e) for e in entries)
        built = time.strftime("%Y-%m-%d")
        sheet_doc = ck.make_sheet(entries, built)
        key_doc = {"built": built, "note": "Which method's proposals each pair was drawn from. Labelers must not open "
                   "this file or results.md before labelling.", "pairs": strata,
                   "settings": {"per_method": SHEET_PER_METHOD, "per_looser": SHEET_PER_LOOSER, "random": SHEET_RANDOM,
                                "thresholds": th, "embedding_model": em.model_name()}}
        os.makedirs(LABELLING, exist_ok=True)
        for path, doc in ((sheet_path, sheet_doc), (key_path, key_doc)):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(doc, f, indent=1, ensure_ascii=False)
        with open(os.path.join(LABELLING, "label.html"), "w", encoding="utf-8") as f:
            f.write(labeller.build_html(sheet_doc))
    sheet_ids = [e["pair"] for e in sheet_doc["pairs"]]

    # people's labels and the figures
    people, skipped = ck.load_people(PEOPLE)
    cons = ck.consensus(people, set(sheet_ids))
    chance_ok = {m: th.get(m) is not None for m in ck.CHANCE_BY_RANDOM_WORDS if m in props and props[m] is not None}
    chance_ok["ai_judge"] = False
    emb_null = dict(zip(stages.EMB_LEVELS, emb_stage["null_mean"])) if emb_stage else {}
    cut_chance = None
    if emb_stage and cutoff is not None:
        grid = max([lv for lv in stages.EMB_LEVELS if lv <= cutoff], default=None)
        cut_chance = emb_null.get(grid) if grid is not None else None
    chance_ok["embed_ai"] = cut_chance is not None and cut_chance < 1.0
    for m in ck.METHODS:
        if props.get(m) is None:
            chance_ok[m] = False

    scores_of = {}
    for pid in sheet_ids:
        qi, pi = parse(pid)
        s = cl.lexical_scores(lex["ctx"], quotes[qi]["text"], pi)
        scores_of[pid] = {"keyword": s["tfidf"], "keyword_phrase": s["both"], "anchor": s["anchor"],
                          "embedding": emb_score(pid)}

    R = {
        "run_date": time.strftime("%Y-%m-%d"), "errors": errors, "n_quotes": len(quotes), "n_meetings": len(meetings),
        "n_priorities": len(priorities), "n_pairs": len(quotes) * len(priorities), "thresholds": th,
        "embedding_model": em.model_name(), "judge": jd.settings(), "seed": SEED, "null_draws": NULL_DRAWS, "emb_null_draws": EMB_NULL_DRAWS,
        "emb_null_quotes": EMB_NULL_QUOTES, "n_random": N_RANDOM, "n_shortlist": N_SHORTLIST, "cutoff": cutoff,
        "cutoff_chance_upper": cut_chance, "emb_pool_cap": EMB_POOL_CAP, "pool_size": len(base),
        "lex_real": {m: dict(zip(lib.LEVELS[k], lex["real"][k])) for m, k in stages.LEX_KEYS.items()},
        "lex_chance": {m: dict(zip(lib.LEVELS[k], [round(v, 2) for v in lex["null_worst"][k]]))
                       for m, k in stages.LEX_KEYS.items()},
        "emb_real": dict(zip(stages.EMB_LEVELS, emb_stage["real"])) if emb_stage else {},
        "emb_chance": {lv: round(v, 2) for lv, v in emb_null.items()},
        "ai_null": ai_null, "chance_ok": chance_ok,
        "sheet": {"pairs": len(sheet_ids), "built": sheet_doc["built"], "frozen_reused": frozen,
                  "per_method": key_doc.get("settings", {}).get("per_method"),
                  "strata": _strata_counts(key_doc["pairs"], sheet_ids)},
        "proposal_counts": {m: (None if props[m] is None else len(props[m])) for m in ck.METHODS},
        "machine": {m: ck.machine_row(props[m], ai) for m in ck.METHODS if props[m] is not None},
        "random_flagged": {m: sum(1 for pid in random_ids if pid in props[m]) for m in ck.METHODS
                           if props[m] is not None and m not in ("ai_judge", "embed_ai")},
        "random_ai_flagged": sum(1 for pid in random_ids if ai_ok(pid) and jd.is_proposed(ai[pid])),
        "people": sorted(people), "people_skipped": skipped, "labelled_pairs": len(cons),
        "ai_wall_s": round(ai_wall), "run_s": round(time.time() - t_run),
    }
    R["ai_stats"] = _ai_stats(ai, base)
    if people:
        R["person"] = {m: ck.method_row(props[m], len(props[m]), cons) for m in ck.METHODS if props[m] is not None}
        R["timing"] = ck.timing(people)
        R["disagreements"] = ck.disagreements(people)
        R["ai_against_people"] = ck.ai_against_people(ai, cons)
        R["instances"] = ck.qualifying_instances(props, cons, chance_ok)
        R["sweep"] = _people_sweep(R, scores_of, cons)
    else:
        R["person"] = R["timing"] = R["disagreements"] = R["ai_against_people"] = R["sweep"] = None
        R["instances"] = []

    ctx = {"quotes": quotes, "priorities": priorities, "parse": parse, "ai": ai, "props": props, "cons": cons,
           "people": people, "scores_of": scores_of, "sheet_ids": sheet_ids, "emb_score": emb_score}
    os.makedirs(OUT, exist_ok=True)
    text = rc.results_markdown(R)
    stand = rc.stand_out_markdown(R, ctx)
    for name, body in (("results.md", text), ("matches-that-stand-out.md", stand)):
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(body + "\n")
    with open(os.path.join(OUT, "results.json"), "w", encoding="utf-8") as f:
        json.dump(R, f, indent=1, default=str)
    print(text)
    print("\n\n" + stand)
    print("\nrun took %.0f s (AI stage %.0f s)" % (time.time() - t_run, ai_wall))
    return 1 if errors else 0


def _write_chance_counts(out_dir, lex, emb_stage, th, props, errors):
    """The machine-side figures that need no person and no AI judge: each method's setting, its corpus count and
    its chance count at every level. Written before the AI stage so they exist even if that stage is cut short."""
    doc = {"note": "Chance counts: pairs per run that random-word quotes give, the worse of the pooled and "
                   "within-meeting models (lexical) or the scaled embedding draws. Written by method/run.py before "
                   "the AI stage; results.json holds the same figures with the rest of the run.",
           "seed": SEED, "null_draws": NULL_DRAWS, "emb_null_draws": EMB_NULL_DRAWS, "emb_null_quotes": EMB_NULL_QUOTES,
           "embedding_model": em.model_name(), "settings": th,
           "proposals": {m: (None if props.get(m) is None else len(props[m])) for m in ("keyword", "keyword_phrase",
                                                                                         "anchor", "embedding")},
           "lexical": {m: {"corpus_pairs": dict(zip(lib.LEVELS[k], lex["real"][k])),
                           "chance_per_run": dict(zip(lib.LEVELS[k], [round(v, 2) for v in lex["null_worst"][k]]))}
                       for m, k in stages.LEX_KEYS.items()},
           "embedding": None, "errors": errors}
    if emb_stage:
        doc["embedding"] = {"corpus_pairs": dict(zip(stages.EMB_LEVELS, emb_stage["real"])),
                            "chance_per_run": {lv: round(v, 2) for lv, v in zip(stages.EMB_LEVELS, emb_stage["null_mean"])}}
    lines = ["# Chance counts at every setting (generated by method/run.py)", "",
             "Pairs per run that random-word quotes give against the real priorities, beside the pairs the real "
             "captions give. A method's setting is the loosest level whose chance count averages under one.", ""]
    names = {"keyword": "Keyword (cosine)", "keyword_phrase": "Keyword with a shared rare phrase",
             "anchor": "Shared named things", "embedding": "Embedding similarity"}
    for m in ("keyword", "keyword_phrase", "anchor"):
        lines += ["## %s (setting: %s)" % (names[m], th.get(m)), "", "| Level | Corpus pairs | Chance per run |", "|---|---|---|"]
        lines += ["| %s | %s | %s |" % (lv, doc["lexical"][m]["corpus_pairs"][lv], doc["lexical"][m]["chance_per_run"][lv])
                  for lv in doc["lexical"][m]["corpus_pairs"]] + [""]
    if doc["embedding"]:
        lines += ["## %s (setting: %s)" % (names["embedding"], th.get("embedding")), "",
                  "| Cosine | Corpus pairs | Chance per run |", "|---|---|---|"]
        lines += ["| %s | %s | %s |" % (lv, doc["embedding"]["corpus_pairs"][lv], doc["embedding"]["chance_per_run"][lv])
                  for lv in doc["embedding"]["corpus_pairs"]] + [""]
    else:
        lines += ["## Embedding similarity: not run", "", "- %s" % errors.get("embedding and embed_ai", "no reason recorded"), ""]
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "chance-counts.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, default=str)
    with open(os.path.join(out_dir, "chance-counts.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _strata_counts(strata, sheet_ids):
    out = {}
    for pid in sheet_ids:
        for s in strata.get(pid, []):
            out[s] = out.get(s, 0) + 1
    return dict(sorted(out.items()))


def _ai_stats(ai, base):
    recs = [r for pid, r in ai.items() if pid in base and "error" not in r]
    if not recs:
        return None
    return {"read": len(recs), "cached": sum(1 for r in recs if r.get("cached")),
            "mean_seconds": round(sum(r["latency_s"] for r in recs) / len(recs), 2),
            "mean_input_tokens": round(sum(r["input_tokens"] for r in recs) / len(recs)),
            "mean_output_tokens": round(sum(r["output_tokens"] for r in recs) / len(recs))}


def _people_sweep(R, scores_of, cons):
    """For each non-AI method and level: pairs in the corpus, chance, and the labelled sheet pairs at or above it."""
    out = {}
    levels = {"keyword": lib.LEVELS["tfidf"], "keyword_phrase": lib.LEVELS["both"], "anchor": lib.LEVELS["anchor"],
              "embedding": [lv for lv in stages.EMB_LEVELS if round(lv * 100) % 5 == 0]}
    for m, lvs in levels.items():
        if m == "embedding" and not R["emb_real"]:
            continue
        rows = []
        for lv in lvs:
            at = [pid for pid in cons if scores_of[pid].get(m) is not None and scores_of[pid][m] >= lv - 1e-12]
            full = R["emb_real"].get(lv) if m == "embedding" else R["lex_real"][m].get(lv)
            chance = R["emb_chance"].get(lv) if m == "embedding" else R["lex_chance"][m].get(lv)
            rows.append({"level": lv, "corpus_pairs": full, "chance": chance, "labelled_at_or_above": len(at),
                         "labelled_real": sum(1 for p in at if cons[p]["overlap"] == "real"),
                         "labelled_loose": sum(1 for p in at if cons[p]["overlap"] == "loose")})
        out[m] = rows
    return out


if __name__ == "__main__":
    sys.exit(main())
