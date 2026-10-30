"""Pure functions for the person-labelled matching check.

No network and no third-party packages. They build the blind labelling sheet (which carries no
method's name, score or reading), read what people labelled, and turn those labels into the
figures the charter asks for: the share of each method's proposals a person judges real, the real
overlaps each misses, how often a proposal takes the opposite side, the time a label takes, and
where two labelers differ. run.py drives them.
"""

import hashlib
import json
import os
import statistics
from collections import Counter, defaultdict

import compare_lib as cl

METHODS = ["keyword", "keyword_phrase", "anchor", "embedding", "ai_judge", "embed_ai"]
NAMES = {
    "keyword": "Keyword (TF-IDF cosine)",
    "keyword_phrase": "Keyword, tighter (cosine + shared phrase)",
    "anchor": "Shared named thing",
    "embedding": "Embedding similarity",
    "ai_judge": "AI judge",
    "embed_ai": "Embedding shortlist + AI",
}
# A method whose chance count at its setting is measured by random-word quotes over the whole corpus.
CHANCE_BY_RANDOM_WORDS = ("keyword", "keyword_phrase", "anchor", "embedding")

OVERLAP = ("none", "loose", "real")
SIDES = ("same", "opposite", "unclear")
SPEAKERS = ("official", "other", "unclear")
IDLE_CAP_MS = 5 * 60 * 1000


# --------------------------------------------------------------------------- the blind sheet

def stable_pick(keys, n, salt):
    """n of the keys, chosen by a hash order that depends only on the keys and the salt."""
    ordered = sorted(keys, key=lambda k: hashlib.md5((salt + "|" + k).encode()).hexdigest())
    return ordered[:n]


def sample_sheet(proposals, looser, random_ids, per_method, per_looser, n_random, salt="sheet-v1"):
    """Choose the pairs people label. Returns {pair id: [strata]} in a hash order.

    proposals: {method: set of pair ids, or None when the method did not run}.
    looser: {method: set of pair ids at the next looser setting that the method does not propose}.
    random_ids: pair ids drawn at random from all pairs.
    Strata are 'proposed:<method>', 'looser:<method>' and 'random'; they go in the key file only.
    """
    strata = defaultdict(list)
    for m in METHODS:
        ids = proposals.get(m)
        if ids:
            for pid in stable_pick(ids, per_method, salt + "|p|" + m):
                strata[pid].append("proposed:" + m)
        ids = looser.get(m)
        if ids:
            for pid in stable_pick(ids, per_looser, salt + "|l|" + m):
                strata[pid].append("looser:" + m)
    for pid in stable_pick(random_ids, n_random, salt + "|r"):
        strata[pid].append("random")
    order = sorted(strata, key=lambda k: hashlib.md5((salt + "|o|" + k).encode()).hexdigest())
    return {pid: strata[pid] for pid in order}


def blind_entry(pid, quote, priority):
    """What a labeler sees for one pair: the exact words, their sources, nothing about any method."""
    return {
        "pair": pid,
        "quote": {"meeting": "%s, %s" % (quote["meeting_body"], quote["meeting_date"]), "stamp": quote["start"],
                  "url": quote["url"], "text": quote["text"], "before": quote.get("before", "")},
        "priority": {"donor": priority["donor"], "section": priority.get("section") or "", "url": priority["url"],
                     "retrieved": priority["retrieved"], "text": priority["text"]},
    }


SHEET_INSTRUCTIONS = (
    "For each pair, say whether the passage (a raw live caption of a San Francisco meeting, in capitals, with "
    "transcription errors) and the donor's published priority overlap, whether they take the same side, and who "
    "seems to be speaking. Read the caption as spoken. Do not look up any method's or judge's output first."
)


def make_sheet(entries, built):
    return {"format": 1, "built": built, "instructions": SHEET_INSTRUCTIONS, "pairs": entries}


def leaks_method(entry):
    """True when a blind entry carries a field or key that could say how it was found."""
    text = json.dumps(entry).lower()
    keys = set()

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                keys.add(k)
                walk(v)
    walk(entry)
    allowed = {"pair", "quote", "priority", "meeting", "stamp", "url", "text", "before", "donor", "section",
               "retrieved"}
    return bool(keys - allowed) or any(('"%s"' % w) in text for w in ("strata", "stratum", "methods", "score"))


# --------------------------------------------------------------------------- reading people's labels

def load_people(folder):
    """({labeler: record}, [notes about files not counted]) from person_labels/*.json.

    A file counts only when it attests that a person made the labels without seeing any method's
    output (blind: true) and every value is one of the allowed ones.
    """
    people, skipped = {}, []
    if not os.path.isdir(folder):
        return people, skipped
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(folder, name), encoding="utf-8") as f:
                doc = json.load(f)
        except ValueError as exc:
            skipped.append("%s: unreadable JSON (%s)" % (name, exc))
            continue
        if doc.get("blind") is not True:
            skipped.append("%s: no attestation (blind: true) that a person labelled it without seeing any output" % name)
            continue
        labels = {k: v for k, v in (doc.get("labels") or {}).items() if v in OVERLAP}
        who = doc.get("labeler") or name[:-5]
        people[who] = {
            "labels": labels,
            "sides": {k: v for k, v in (doc.get("sides") or {}).items() if v in SIDES and k in labels},
            "speakers": {k: v for k, v in (doc.get("speakers") or {}).items() if v in SPEAKERS and k in labels},
            "ms": {k: float(v) for k, v in (doc.get("ms") or {}).items() if k in labels and _num(v)},
            "ms_hidden": {k: float(v) for k, v in (doc.get("ms_hidden") or {}).items() if k in labels and _num(v)},
            "file": name,
        }
    return people, skipped


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0


def consensus(people, valid_ids=None):
    """{pair: {'overlap', 'side', 'speaker', 'n'}}: the conservative reading across labelers.

    Overlap is the lower middle level. Side is 'opposite' when any labeler who judged some overlap
    says so, 'same' when all who gave a side say same, else 'unclear'. Speaker is 'other' when any
    labeler says someone other than an official, 'official' when all who gave one say so.
    """
    by_pair = defaultdict(list)
    for who, rec in people.items():
        for pid, lv in rec["labels"].items():
            if valid_ids is None or pid in valid_ids:
                by_pair[pid].append(who)
    out = {}
    for pid, whos in by_pair.items():
        levels = [people[w]["labels"][pid] for w in whos]
        sides = [people[w]["sides"][pid] for w in whos if pid in people[w]["sides"]]
        speakers = [people[w]["speakers"][pid] for w in whos if pid in people[w]["speakers"]]
        if "opposite" in sides:
            side = "opposite"
        elif sides and all(s == "same" for s in sides):
            side = "same"
        else:
            side = "unclear"
        if "other" in speakers:
            speaker = "other"
        elif speakers and all(s == "official" for s in speakers):
            speaker = "official"
        else:
            speaker = "unclear"
        out[pid] = {"overlap": cl.lower_middle(levels), "side": side, "speaker": speaker, "n": len(whos),
                    "labelers": sorted(whos)}
    return out


# --------------------------------------------------------------------------- the figures

def share(k, n):
    return {"k": k, "n": n, "share": (k / n) if n else None, "ci": cl.wilson(k, n) if n else None}


def method_row(proposed, n_proposed, cons):
    """One method's proposals against the people's consensus on the pairs they labelled."""
    lab = [i for i in proposed if i in cons]
    real = [i for i in lab if cons[i]["overlap"] == "real"]
    loose = [i for i in lab if cons[i]["overlap"] == "loose"]
    judged_some = [i for i in lab if cons[i]["overlap"] in ("real", "loose")]
    all_real = {i for i, c in cons.items() if c["overlap"] == "real"}
    precision = share(len(real), len(lab))
    est = None
    if lab:
        lo, hi = precision["ci"]
        est = {"low": lo * n_proposed, "mid": precision["share"] * n_proposed, "high": hi * n_proposed}
    return {
        "proposals": n_proposed,
        "labelled_proposals": len(lab),
        "real": len(real), "loose": len(loose), "none": len(lab) - len(real) - len(loose),
        "precision_real": precision,
        "estimated_real_among_proposals": est,
        "opposite_among_real_or_loose": share(sum(1 for i in judged_some if cons[i]["side"] == "opposite"), len(judged_some)),
        "opposite_among_real": share(sum(1 for i in real if cons[i]["side"] == "opposite"), len(real)),
        "real_known": len(all_real),
        "real_missed": len(all_real - set(proposed)),
        "recall_of_known_real": share(len(all_real & set(proposed)), len(all_real)),
        "speaker_other_among_real": share(sum(1 for i in real if cons[i]["speaker"] == "other"), len(real)),
    }


def timing(people, idle_cap_ms=IDLE_CAP_MS):
    """Seconds a label took: overall, by the overlap given, and per labeler. Over-cap times are set aside."""
    def stats(vals):
        if not vals:
            return None
        s = sorted(vals)
        q = lambda p: s[min(len(s) - 1, int(p * (len(s) - 1) + 0.5))]
        return {"n": len(s), "median": statistics.median(s), "mean": statistics.mean(s), "p25": q(0.25),
                "p75": q(0.75), "p90": q(0.9), "max": s[-1]}
    allv, by_overlap, per, set_aside = [], defaultdict(list), {}, 0
    for who, rec in people.items():
        mine = []
        for pid, ms in rec["ms"].items():
            if ms > idle_cap_ms:
                set_aside += 1
                continue
            sec = ms / 1000.0
            mine.append(sec)
            by_overlap[rec["labels"][pid]].append(sec)
        per[who] = stats(mine)
        allv += mine
    overall = stats(allv)
    projection = {}
    if overall:
        for n in (10, 25, 50, 100):
            projection[str(n)] = {"median_minutes": round(n * overall["median"] / 60, 1),
                                  "p90_minutes": round(n * overall["p90"] / 60, 1)}
    return {"overall": overall, "by_overlap": {k: stats(v) for k, v in by_overlap.items()}, "per_labeler": per,
            "set_aside_over_cap": set_aside, "idle_cap_s": idle_cap_ms / 1000.0, "projection": projection}


def disagreements(people):
    """Per pair of labelers: shared pairs, agreement and kappa on overlap and side, and the pairs that differ."""
    out = []
    names = sorted(people)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            la, lb = people[a]["labels"], people[b]["labels"]
            both = sorted(set(la) & set(lb))
            kap = cl.cohen_kappa([la[p] for p in both], [lb[p] for p in both]) if both else None
            sa, sb = people[a]["sides"], people[b]["sides"]
            side_both = sorted(set(sa) & set(sb))
            diffs = [{"pair": p, a: la[p], b: lb[p]} for p in both if la[p] != lb[p]]
            side_diffs = [{"pair": p, a: sa[p], b: sb[p]} for p in side_both if sa[p] != sb[p]]
            out.append({"labelers": [a, b], "shared": len(both), "agree": len(both) - len(diffs), "kappa": kap,
                        "differ": diffs, "side_shared": len(side_both),
                        "side_agree": len(side_both) - len(side_diffs), "side_differ": side_diffs,
                        "neighbouring_only": all(abs(cl._ORDER[d[a]] - cl._ORDER[d[b]]) == 1 for d in diffs)})
    return out


def ai_against_people(ai, cons):
    """AI judge's overlap and stance readings against the people's consensus, on pairs both read."""
    table = {lv: Counter() for lv in OVERLAP}
    stance = Counter()
    for pid, c in cons.items():
        rec = ai.get(pid)
        if not rec or "error" in rec:
            continue
        table[c["overlap"]][rec["overlap"]] += 1
        if c["overlap"] != "none":
            stance[(c["side"], rec["stance"])] += 1
    return {"overlap": {k: dict(v) for k, v in table.items()},
            "stance": {"%s|%s" % k: v for k, v in sorted(stance.items())}}


def qualifying_instances(proposals, cons, chance_ok):
    """Pairs that show 'matches stand out': a method proposed it, a person who is not the run judged it a real
    overlap on the same side, and the proposing method's chance count at its setting is under one per run.

    chance_ok: {method: True/False}. Returns [{'pair', 'methods', ...}] by number of methods, then id.
    """
    out = []
    for pid, c in cons.items():
        if c["overlap"] != "real" or c["side"] != "same":
            continue
        ms = [m for m in METHODS if proposals.get(m) and pid in proposals[m] and chance_ok.get(m)]
        if ms:
            out.append({"pair": pid, "methods": ms, "labelers": c["labelers"], "speaker": c["speaker"]})
    return sorted(out, key=lambda r: (-len(r["methods"]), r["pair"]))


def machine_row(proposed, ai):
    """The AI judge's reading of everything a method proposes that the judge read (not a person's reading)."""
    rows = [ai[i] for i in proposed if i in ai and "error" not in ai[i]]
    c = Counter(r["overlap"] for r in rows)
    st = Counter(r["stance"] for r in rows if r["overlap"] != "none")
    sp = Counter(r["speaker_type"] for r in rows)
    eligible = [r for r in rows if r["overlap"] == "real" and r["speaker_type"] in ("official", "unclear")]
    return {"proposals": len(proposed), "read": len(rows), "real": c["real"], "loose": c["loose"], "none": c["none"],
            "real_and_may_be_official": len(eligible),
            "opposes": st["opposes"], "agrees": st["agrees"], "mixed": st["mixed"], "no_position": st["no_position"],
            "speaker_types": dict(sp)}
