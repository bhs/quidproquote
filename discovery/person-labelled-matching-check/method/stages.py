"""The heavy stages: lexical scoring with chance counts, and embedding with chance counts.

Adapted from ../matching-methods-comparison/compare.py (same arithmetic, same chance models and
the same definition of a calibrated setting: the loosest level at which random-word quotes yield
fewer than one pair per run on average), so that figures here are comparable with that hop's.
"""

import random
import statistics
import time

import embed as em
import trial_lib as lib

EMB_LEVELS = [round(0.30 + 0.01 * i, 2) for i in range(66)]
LEX_KEYS = {"keyword": "tfidf", "keyword_phrase": "both", "anchor": "anchor"}


def stage_lexical(quotes, priorities, seed, null_draws):
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
        rng = random.Random(seed + (1 if within else 0))
        runs = [lib.counts_at_levels(lib.score_quotes(ctx, lib.draw_null(q_tokens, meeting_of, rng, within)))
                for _ in range(null_draws)]
        null[model] = {m: [statistics.mean(v) for v in zip(*[r[m] for r in runs])] for m, _ in lib.METHODS}
    calibrated, worst = {}, {}
    for m, _ in lib.METHODS:
        worst[m] = [max(null["pooled"][m][i], null["within_meeting"][m][i]) for i in range(len(lib.LEVELS[m]))]
        i, lv = lib.calibrated_level(m, real[m], worst[m])
        calibrated[m] = lv
    return {"ctx": ctx, "scores": scores, "real": real, "null_worst": worst, "calibrated": calibrated,
            "seconds": seconds, "q_tokens": q_tokens, "meeting_of": meeting_of}


def stage_embedding(quotes, priorities, lex, seed, null_draws, null_quotes):
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
    rng = random.Random(seed + 7)
    runs = []
    for _ in range(null_draws):
        # embedding on the CPU is the slow part: embed a random sample of the chance quotes and scale
        fake = lib.draw_null(lex["q_tokens"], lex["meeting_of"], rng, False)
        fake = rng.sample(fake, min(null_quotes, len(fake)))
        fv = emb.embed([" ".join(t) for t in fake])
        scale = len(quotes) / len(fake)
        runs.append([c * scale for c in counts(np.sort((fv @ pv.T).ravel()))])
    null_mean = [statistics.mean(v) for v in zip(*runs)]
    calibrated = next((lv for lv, n in zip(EMB_LEVELS, null_mean) if n < 1.0), None)
    return {"emb": emb, "np": np, "matrix": matrix, "real": real, "null_mean": null_mean,
            "calibrated": calibrated}
