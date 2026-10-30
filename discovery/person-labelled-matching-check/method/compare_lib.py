"""Pure functions for the matching methods comparison.

No network and no third-party packages: snapshot loading, labels and their disagreements, the
lexical scorers, caption-error injection, speaker proposals, probes and the measures. compare.py
drives these; embed.py, judge.py and money.py hold the parts that need a model or the network.
"""

import difflib
import hashlib
import json
import math
import os
import random
import re
from collections import Counter, defaultdict

import trial_lib as lib

# --------------------------------------------------------------------------- snapshot

PAIR_SEP = "|"


def pair_id(quote_id, priority_id):
    return quote_id + PAIR_SEP + priority_id


def split_pair(pid):
    quote_id, _, priority_id = pid.rpartition(PAIR_SEP)
    return quote_id, priority_id


def load_snapshot(data_dir):
    """Meetings, substantive passages (with the caption words just before each) and priorities."""
    with open(os.path.join(data_dir, "meetings.json"), encoding="utf-8") as f:
        meetings = json.load(f)
    quotes = []
    for m in meetings:
        rows = []
        with open(os.path.join(data_dir, "transcripts", "%d.tsv" % m["id"]), encoding="utf-8") as f:
            for line in f:
                stamp, _, text = line.rstrip("\n").partition("\t")
                rows.append((stamp, text))
        first_row = {}
        for i, (stamp, _) in enumerate(rows):
            first_row.setdefault(stamp, i)
        for p in lib.build_passages(m["id"], rows):
            if not lib.is_substantive(p):
                continue
            p["meeting_body"] = m["body"]
            p["meeting_date"] = m["date"]
            p["url"] = m["url"]
            p["retrieved"] = m["retrieved"]
            p["before"] = words_before(rows, first_row.get(p["start"], 0))
            quotes.append(p)
    with open(os.path.join(data_dir, "priorities.json"), encoding="utf-8") as f:
        priorities = json.load(f)
    return meetings, quotes, priorities


def words_before(rows, index, n_words=40):
    """The last n_words caption words before row `index`, with '>>' marks kept."""
    out = []
    i = index - 1
    while i >= 0 and len(out) < n_words:
        out = rows[i][1].split() + out
        i -= 1
    return " ".join(out[-n_words:])


# --------------------------------------------------------------------------- labels

LEVELS3 = ("none", "loose", "real")
_ORDER = {"none": 0, "loose": 1, "real": 2}

# The trial's four classes onto the three levels this hop scores against. "not_a_quote" has no
# overlap level in the trial's files (related, but a clerk, a commenter or staff): it is left
# out of the overlap view and counted as "none" in the review-ready view, since it would be
# rejected at review.
TRIAL_TO_VIEWS = {
    "meaningful": ("real", "real"),
    "topical": ("loose", "loose"),
    "coincidental": ("none", "none"),
    "not_a_quote": (None, "none"),
}


def load_judge_labels(data_dir):
    """{'reader': {pair: {'label':..., 'note':...}}, 'model': {...}} from the trial's files."""
    out = {}
    for judge, name in (("reader", "labels.json"), ("model", "labels_model.json")):
        path = os.path.join(data_dir, name)
        out[judge] = {}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                out[judge] = json.load(f).get("labels", {})
    return out


def load_person_labels(data_dir):
    """{labeler: {pair: 'real'|'loose'|'none'}} from data/person_labels/*.json."""
    folder = os.path.join(data_dir, "person_labels")
    out = {}
    if not os.path.isdir(folder):
        return out
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(folder, name), encoding="utf-8") as f:
            doc = json.load(f)
        labels = {k: v for k, v in doc.get("labels", {}).items() if v in _ORDER}
        out[doc.get("labeler") or name[:-5]] = labels
    return out


def lower_middle(levels):
    """The lower middle level of a list of levels (the conservative reading where labelers differ)."""
    ordered = sorted(levels, key=lambda v: _ORDER[v])
    return ordered[(len(ordered) - 1) // 2]


def gold_from_judges(judge_labels, primary="model"):
    """{pair: {'overlap': level or None, 'ready': level}} from one judge's four classes."""
    gold = {}
    for pid, rec in judge_labels.get(primary, {}).items():
        overlap, ready = TRIAL_TO_VIEWS[rec["label"]]
        gold[pid] = {"overlap": overlap, "ready": ready, "source": primary + " (trial)"}
    return gold


def gold_from_people(person_labels):
    """Consensus of person labelers: the lower middle level per pair."""
    by_pair = defaultdict(list)
    for labels in person_labels.values():
        for pid, lv in labels.items():
            by_pair[pid].append(lv)
    return {pid: {"overlap": lower_middle(v), "ready": lower_middle(v), "source": "people"}
            for pid, v in by_pair.items()}


def cohen_kappa(a, b):
    """Cohen's kappa for two equal-length label lists (None when undefined)."""
    n = len(a)
    if n == 0:
        return None
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    if pe >= 1.0:
        return None
    return (po - pe) / (1 - pe)


def disagreements(labels_a, labels_b, key=lambda r: r):
    """Pairs both labelled with different labels: [(pair, a, b)]."""
    return [(pid, key(labels_a[pid]), key(labels_b[pid])) for pid in sorted(labels_a)
            if pid in labels_b and key(labels_a[pid]) != key(labels_b[pid])]


# --------------------------------------------------------------------------- measures

def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - r) / d), min(1.0, (c + r) / d))


def auc(positive_scores, negative_scores):
    """Chance that a random positive outscores a random negative (ties count half); None if empty."""
    if not positive_scores or not negative_scores:
        return None
    neg = sorted(negative_scores)
    total = 0.0
    import bisect
    for s in positive_scores:
        lo = bisect.bisect_left(neg, s)
        hi = bisect.bisect_right(neg, s)
        total += lo + 0.5 * (hi - lo)
    return total / (len(positive_scores) * len(neg))


def evaluate(proposed, gold, view):
    """Score one method's proposals against gold labels in one view ('overlap' or 'ready').

    proposed: {pair: bool}. gold: {pair: {'overlap':..., 'ready':...}}. Pairs without a level in
    the view are left out. Returns counts and the shares the charter asks for.
    """
    rows = [(pid, gold[pid][view]) for pid in proposed if pid in gold and gold[pid][view] is not None]
    prop = [lv for pid, lv in rows if proposed[pid]]
    real_total = sum(1 for _, lv in rows if lv == "real")
    real_found = sum(1 for lv in prop if lv == "real")
    loose_found = sum(1 for lv in prop if lv == "loose")
    out = {
        "labelled": len(rows),
        "gold_real": real_total,
        "proposed": len(prop),
        "proposed_real": real_found,
        "proposed_loose": loose_found,
        "proposed_none": len(prop) - real_found - loose_found,
        "real_missed": real_total - real_found,
    }
    out["precision_real"] = real_found / len(prop) if prop else None
    out["precision_real_ci"] = wilson(real_found, len(prop)) if prop else None
    out["precision_real_or_loose"] = (real_found + loose_found) / len(prop) if prop else None
    out["recall_real"] = real_found / real_total if real_total else None
    out["recall_real_ci"] = wilson(real_found, real_total) if real_total else None
    return out


# --------------------------------------------------------------------------- lexical scorers

def lexical_scores(ctx, text, pi):
    """TF-IDF cosine, shared rare two-word phrases and shared named things for one pair.

    The same arithmetic as trial_lib.score_quotes, for one pair of arbitrary text.
    """
    toks = lib.tokenize(text)
    terms = lib.content_terms(toks)
    tf = Counter(terms)
    vec = {t: (1.0 + math.log(c)) * ctx.idf.get(t, 1.0) for t, c in tf.items()}
    norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
    pv = ctx.p_vec[pi]
    cos = sum((w / norm) * pv.get(t, 0.0) for t, w in vec.items())
    phrases = len(lib.bigrams(terms) & ctx.p_bigrams[pi])
    anchors = len(lib.ngrams_upto(toks) & ctx.p_anchors[pi])
    return {"tfidf": cos, "phrase": float(phrases), "anchor": float(anchors),
            "both": cos if phrases >= 1 else 0.0}


# --------------------------------------------------------------------------- caption errors

NUMBER_WORDS = {"one": "won", "two": "to", "four": "for", "eight": "ate", "ten": "then",
                "million": "billion", "billion": "million", "hundred": "thousand", "thousand": "hundred"}
VOTE_WORDS = {"aye": "eye", "nay": "neigh", "no": "know", "yes": "yet", "oppose": "a pose",
              "opposed": "supposed", "against": "again", "support": "supports"}
_PROP_REF = re.compile(r"^(prop|proposition|measure)$", re.I)


def _unit(seed, i, salt):
    h = hashlib.md5(("%s|%d|%s" % (seed, i, salt)).encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def _one_letter_edit(word, u):
    """A deterministic one-letter change inside a word (the kind a caption engine makes to a name)."""
    if len(word) < 4:
        return word + "s"
    k = 1 + int(u * (len(word) - 2))
    if u < 0.5:
        return word[:k - 1] + word[k] + word[k - 1] + word[k + 1:]   # swap two letters
    return word[:k] + word[k + 1:]                                    # drop one letter


def name_tokens(ctx, roster_surnames):
    """Words that count as names: tokens of the priorities' named things plus the roster's surnames."""
    out = {s.lower() for s in roster_surnames}
    for anchors in ctx.p_anchors:
        for a in anchors:
            for t in a:
                if t not in lib.STOPWORDS and t != "prop" and len(t) >= 4:
                    out.add(t)
    return out


def inject_caption_errors(text, rate, seed, names):
    """Caption-style errors in names, numbers and vote words, at `rate` of eligible words.

    Deterministic for a given seed. These are injected, not observed: the rates of real caption
    errors per quote are not known. Returns (new text, {'name': n, 'number': n, 'vote': n}).
    """
    words = text.split()
    counts = {"name": 0, "number": 0, "vote": 0}
    prev_bare = ""
    for i, w in enumerate(words):
        m = re.match(r"^(\W*)([A-Za-z0-9']+)(\W*)$", w)
        if not m:
            prev_bare = ""
            continue
        pre, core, post = m.groups()
        low = core.lower()
        new = None
        category = None
        if _PROP_REF.match(prev_bare) and (re.fullmatch(r"[A-Ja-j]", core) or core.isdigit()):
            category = "number"
            if core.isdigit():
                new = str((int(core) + 1) % 100)
            else:
                new = chr((ord(core.upper()) - 65 + 1) % 10 + 65)
        elif low in VOTE_WORDS:
            category = "vote"
            new = VOTE_WORDS[low]
        elif low in NUMBER_WORDS:
            category = "number"
            new = NUMBER_WORDS[low]
        elif core.isdigit() and len(core) >= 2:
            category = "number"
            new = core[:-1] + str((int(core[-1]) + 3) % 10)
        elif low in names:
            category = "name"
            new = _one_letter_edit(low, _unit(seed, i, "edit"))
        prev_bare = core
        if category and _unit(seed, i, "hit") < rate:
            if core.isupper():
                new = new.upper()
            words[i] = pre + new + post
            counts[category] += 1
    return " ".join(words), counts


# --------------------------------------------------------------------------- speaker proposals

_CUE = re.compile(r"\b(?:DISTRICT\s+(\w+)\s+)?(SUPERVISOR|MAYOR|CHAIR|SUPERVISORS)\s+([A-Z]{3,})\b")
_DISTRICT_WORDS = {"ONE": "1", "TWO": "2", "THREE": "3", "FOUR": "4", "FIVE": "5", "SIX": "6", "SEVEN": "7",
                   "EIGHT": "8", "NINE": "9", "TEN": "10", "ELEVEN": "11"}
_NOT_NAMES = {"THANK", "THANKS", "THE", "WILL", "PLEASE", "AND", "FOR", "THAT", "THIS", "WHO", "HAS", "HAVE",
              "COMMISSION", "COMMITTEE", "SORRY", "MADAM", "CLERK", "MISTER", "CHAIR", "PRESIDENT", "SUPERVISOR", "SUPERVISORS"}


def propose_speaker(before, passage_text, roster):
    """A proposed speaker from the spoken cue near a passage. Always a proposal, never a record.

    roster: [{'name', 'surname', 'district', 'office'}]. Looks for 'SUPERVISOR X', 'DISTRICT N
    SUPERVISOR X' or 'MAYOR X' in the last words before the passage and in its first words; a
    name read by the captions is matched to the roster by spelling. Several different cues close
    together are treated as a roll call (no speaker). Returns a dict with name (or None), basis
    and a caution.
    """
    window = (before + " >> " + " ".join(passage_text.split()[:14])).upper().replace(">>", " ")
    cues = []
    for m in _CUE.finditer(window):
        word = m.group(3)
        if word in _NOT_NAMES:
            continue
        cues.append((m.start(), m.group(0), m.group(1), word))
    if not cues:
        return {"name": None, "basis": "no spoken cue ('Supervisor X') near the passage",
                "caution": "speaker unknown"}
    if len({c[3] for c in cues}) >= 3:
        return {"name": None, "basis": "three or more names read close together (a roll call or list)",
                "caution": "names in a roll call are not speakers"}
    pos, text, district_word, word = cues[-1]
    scored = sorted(((difflib.SequenceMatcher(None, word, o["surname"].upper()).ratio(), o) for o in roster),
                    key=lambda t: -t[0])
    best, official = scored[0]
    second = scored[1][0] if len(scored) > 1 else 0.0
    if best < 0.7:
        return {"name": None, "basis": "cue '%s' matches no roster surname" % text,
                "caution": "the captions garble names"}
    caution = "unconfirmed; the name comes from the captions"
    if best < 1.0 and best - second < 0.1:
        caution = "ambiguous spelling (close to more than one surname); unconfirmed"
    district = _DISTRICT_WORDS.get((district_word or "").upper(), (district_word or "").upper())
    basis = "cue '%s'" % text
    if district and official["district"] == district:
        basis += ", district %s agrees" % district
    elif district:
        basis += ", but district %s does not agree" % district
        caution = "name and district disagree; unconfirmed"
    return {"name": official["name"], "basis": basis, "caution": caution}


# --------------------------------------------------------------------------- probes

# Hand-written, synthetic test inputs (not quotes from anyone): for each of seven measure
# statements, a passage taking the same side as the priority and one taking the opposite side,
# both using the priority's own topic words. A method that finds the same score for both pairs
# is blind to position.
PROBES = [
    ("H", "P041",
     "I will be voting yes on Prop H, the parcel tax to fund Muni operations, because public transit is a critical driver of our economy and keeps workers, residents and businesses connected.",
     "I will be voting no on Prop H, the parcel tax to fund Muni operations, because a new parcel tax on homeowners is the wrong way to fund transit and does nothing to keep workers and businesses connected."),
    ("B", "P055",
     "I am opposed to Prop B, the Municipal Finance Corporation and public bank, because the Bank of North Dakota is a weak comparison and our deficit comes from overspending.",
     "I strongly support Prop B, the Municipal Finance Corporation and public bank, because the Bank of North Dakota shows a public bank can work for a city and keep our money local."),
    ("D", "P057",
     "I support Prop D on the ballot measure process because San Francisco has the lowest signature threshold and residents face overly long and complex ballots.",
     "I oppose Prop D on the ballot measure process because raising the signature threshold would shut residents out and our long ballots are the voters' choice."),
    ("E", "P058",
     "Prop E gives the City Administrator the power to standardize purchasing rules and fix contracting, like the notorious Noe Valley toilet, and I will vote yes.",
     "Prop E gives the City Administrator too much power over contracting and purchasing rules and weakens Board oversight, so I will vote no."),
    ("I", "P062",
     "Prop I moves General Fund money into an earmarked fund, and with the city already facing a budget deficit that makes it worse, so I urge a no vote on I.",
     "Prop I dedicates transfer tax revenue to affordable housing and stable funding is what the city needs even in a budget deficit, so I urge a yes vote on I."),
    ("A", "P068",
     "Prop A is a common-sense fix for City Hall bureaucracy: commissions shield individuals from accountability and the Mayor should be able to hold departments to account.",
     "Prop A is a power grab that strips commissions of their oversight of City Hall departments, and the Mayor should not be able to override them, so vote no."),
    ("C", "P036",
     "Prop C raising the Housing Trust Fund contribution to $125 million helps build affordable housing and keeps workers in the city, and I support it.",
     "Prop C raising the Housing Trust Fund contribution to $125 million locks in a set-aside that does not build affordable housing, and I oppose it."),
]


def probe_items(priorities_by_id):
    """[{'id', 'priority_id', 'side', 'text'}] for the synthetic probes; side is 'same' or 'opposite'."""
    out = []
    for letter, pid, same, opposite in PROBES:
        for side, text in (("same", same), ("opposite", opposite)):
            if pid in priorities_by_id:
                out.append({"id": "PROBE-%s-%s" % (letter, side), "priority_id": pid, "side": side,
                            "text": text})
    return out


# --------------------------------------------------------------------------- samples

def random_pairs(n, n_quotes, n_priorities, exclude, seed):
    """n distinct (quote index, priority index) pairs drawn with a fixed seed, skipping `exclude`."""
    rng = random.Random(seed)
    out = []
    seen = set(exclude)
    while len(out) < n:
        k = (rng.randrange(n_quotes), rng.randrange(n_priorities))
        if k in seen:
            continue
        seen.add(k)
        out.append(k)
    return out


def level_counts(scores_flat, levels):
    """[number of scores at or above each level]."""
    return [sum(1 for s in scores_flat if s >= lv - 1e-12) for lv in levels]


def money(amount):
    return "${:,.0f}".format(amount)
