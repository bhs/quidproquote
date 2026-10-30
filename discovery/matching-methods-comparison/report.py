"""Turns scored items into the comparison tables and the markdown report.

Pure functions over the item dicts that compare.py builds (no model, no network), so the tests
can run them on small made-up items.
"""

import compare_lib as cl
import judge as jd
import trial_lib as lib

METHOD_ORDER = ["keyword", "keyword_phrase", "anchor", "embedding", "ai_judge", "embed_ai"]


def ai_ok(it):
    return bool(it.get("ai")) and "error" not in it["ai"]


def assign_proposals(items, th):
    """it['prop'][method] is True/False, or None when that method has no score for the item.

    th: {'keyword', 'keyword_phrase', 'anchor', 'embedding'} levels (None: nothing calibrated) and
    'cutoff' (the shortlist's lowest embedding score, None when the embedding stage did not run).
    """
    for it in items:
        lex, p = it["lex"], {}
        for method, key in (("keyword", "tfidf"), ("keyword_phrase", "both"), ("anchor", "anchor")):
            lv = th.get(method)
            p[method] = (lex[key] >= lv - 1e-12) if lv is not None else False
        emb = it.get("emb")
        lv = th.get("embedding")
        p["embedding"] = None if emb is None else (emb >= lv - 1e-12 if lv is not None else False)
        p["ai_judge"] = jd.is_proposed(it["ai"]) if ai_ok(it) else None
        cutoff = th.get("cutoff")
        if emb is None or cutoff is None or not ai_ok(it):
            p["embed_ai"] = None
        else:
            p["embed_ai"] = emb >= cutoff - 1e-12 and jd.is_proposed(it["ai"])
        it["prop"] = p


def proposals_for(items, method, kinds):
    return {it["id"]: it["prop"][method] for it in items
            if it["kind"] in kinds and it["prop"][method] is not None}


def evaluation(items, gold, th):
    """Per method: both views on the labelled items, false alarms on random pairs, probe results."""
    out = {}
    random_items = [it for it in items if it["kind"] == "random"]
    for m in METHOD_ORDER:
        prop = proposals_for(items, m, ("labelled",))
        row = {"ready": cl.evaluate(prop, gold, "ready"), "overlap": cl.evaluate(prop, gold, "overlap"),
               "unscored_labelled": sum(1 for it in items if it["kind"] == "labelled" and it["prop"][m] is None)}
        rp = [it["prop"][m] for it in random_items if it["prop"][m] is not None]
        row["random_n"] = len(rp)
        row["random_flagged"] = sum(rp)
        row["random_ci"] = cl.wilson(sum(rp), len(rp)) if rp else None
        probes = [it for it in items if it["kind"] == "probe" and it["prop"][m] is not None]
        row["probe_same"] = sum(1 for it in probes if it["side"] == "same" and it["prop"][m])
        row["probe_opposite"] = sum(1 for it in probes if it["side"] == "opposite" and it["prop"][m])
        row["probe_n_each"] = sum(1 for it in probes if it["side"] == "same")
        out[m] = row
    return out


def stance_by_method(items):
    """Among each method's proposed pairs that carry an AI reading, how many the AI reads as opposing."""
    out = {}
    for m in METHOD_ORDER:
        rows = [it for it in items if it["kind"] in ("labelled", "shortlist", "random")
                and it["prop"][m] and ai_ok(it)]
        out[m] = {"proposed_with_reading": len(rows),
                  "opposes": sum(1 for it in rows if it["ai"]["stance"] == "opposes"),
                  "agrees": sum(1 for it in rows if it["ai"]["stance"] == "agrees"),
                  "mixed": sum(1 for it in rows if it["ai"]["stance"] == "mixed"),
                  "no_position": sum(1 for it in rows if it["ai"]["stance"] == "no_position")}
    return out


def score_of(it, method):
    if method == "embedding":
        return it.get("emb")
    return it["lex"][{"keyword": "tfidf", "keyword_phrase": "both", "anchor": "anchor"}[method]]


def sweep(items, gold, method, levels):
    """For each level: gold-real, other labelled and random pairs at or above it; AUCs of the score."""
    lab = [it for it in items if it["kind"] == "labelled" and it["id"] in gold and score_of(it, method) is not None]
    rnd = [it for it in items if it["kind"] == "random" and score_of(it, method) is not None]
    real = [score_of(it, method) for it in lab if gold[it["id"]]["ready"] == "real"]
    other = [score_of(it, method) for it in lab if gold[it["id"]]["ready"] != "real"]
    rand = [score_of(it, method) for it in rnd]
    rows = []
    for lv in levels:
        rows.append({"level": lv,
                     "real": sum(1 for s in real if s >= lv - 1e-12),
                     "other": sum(1 for s in other if s >= lv - 1e-12),
                     "random": sum(1 for s in rand if s >= lv - 1e-12)})
    return {"rows": rows, "n_real": len(real), "n_other": len(other), "n_random": len(rand),
            "auc_vs_other": cl.auc(real, other), "auc_vs_random": cl.auc(real, rand)}


def verdict_table(items, gold):
    """AI overlap verdict against the gold level (review-ready view) on labelled items, and on random pairs."""
    table = {g: {v: 0 for v in jd.OVERLAP} for g in cl.LEVELS3}
    for it in items:
        if it["kind"] == "labelled" and it["id"] in gold and ai_ok(it):
            table[gold[it["id"]]["ready"]][it["ai"]["overlap"]] += 1
    rnd = {v: 0 for v in jd.OVERLAP}
    for it in items:
        if it["kind"] == "random" and ai_ok(it):
            rnd[it["ai"]["overlap"]] += 1
    return table, rnd


def error_effect(items, gold):
    """Per method: how proposals change when the injected caption errors are in the quote."""
    by_id = {it["id"]: it for it in items}
    twins = [it for it in items if it["kind"] == "perturbed"]
    out = {"twins": len(twins),
           "categories": {c: sum(t["errors"][c] for t in twins) for c in ("name", "number", "vote")},
           "labelled_twins": sum(1 for t in twins if by_id[t["of"]]["kind"] == "labelled"), "methods": {}}
    for m in METHOD_ORDER:
        lost = gained = same = lost_real = 0
        stance_changed = 0
        for t in twins:
            a, b = by_id[t["of"]]["prop"][m], t["prop"][m]
            if a is None or b is None:
                continue
            if a and not b:
                lost += 1
                if t["of"] in gold and gold[t["of"]]["ready"] == "real":
                    lost_real += 1
            elif b and not a:
                gained += 1
            else:
                same += 1
            ia, ib = by_id[t["of"]].get("ai"), t.get("ai")
            if m == "ai_judge" and ai_ok(by_id[t["of"]]) and ib and "error" not in ib \
                    and ia["stance"] != ib["stance"]:
                stance_changed += 1
        out["methods"][m] = {"lost": lost, "gained": gained, "unchanged": same, "lost_real": lost_real,
                             "stance_changed": stance_changed}
    return out


def judge_costs(items, cfg):
    """Mean dollars and seconds per judged pair, from the records of unperturbed items."""
    recs = [it["ai"] for it in items if ai_ok(it) and it["kind"] != "perturbed"]
    if not recs:
        return None
    return {"n": len(recs),
            "dollars": sum(jd.cost_dollars(r, cfg) for r in recs) / len(recs),
            "seconds": sum(r["latency_s"] for r in recs) / len(recs),
            "input_tokens": sum(r["input_tokens"] for r in recs) / len(recs),
            "output_tokens": sum(r["output_tokens"] for r in recs) / len(recs)}
