"""Pure functions for the matching trial: passages, four ways of matching, a chance model.

Copied unchanged from ../matching-trial-run/trial_lib.py so this directory builds on its own.

No network and no third-party packages. analyze.py drives these over the snapshot in data/.
"""

import bisect
import hashlib
import math
import random
import re
from collections import Counter, defaultdict

# --------------------------------------------------------------------------- text

STOPWORDS = set("""
a about above after again against all also am an and any are aren't as at be because been before being
below between both but by can can't cannot could couldn't did didn't do does doesn't doing don't down
during each few for from further get got had hadn't has hasn't have haven't having he he'd he'll he's her
here here's hers herself him himself his how how's i i'd i'll i'm i've if in into is isn't it it's its
itself just let's like me more most mustn't my myself no nor not of off on once only or other ought our
ours ourselves out over own same shan't she she'd she'll she's should shouldn't so some such than that
that's the their theirs them themselves then there there's these they they'd they'll they're they've this
those through to too under until up very was wasn't we we'd we'll we're we've were weren't what what's
when when's where where's which while who who's whom why why's will with won't would wouldn't you you'd
you'll you're you've your yours yourself yourselves
um uh okay ok yeah yes thank thanks please right well going know think want make made one two three
also really said say says thing things way lot kind sort back come comes look see us let much many
san francisco sf city supervisor supervisors chair president colleagues colleague madam clerk item items
mr ms mrs today tonight sir morning afternoon evening good
""".split())

_TOKEN = re.compile(r"[a-z0-9]+(?:['\u2019][a-z]+)?")


def tokenize(text):
    """Lower-case word tokens; 'proposition' reads as 'prop'; apostrophes dropped."""
    out = []
    for t in _TOKEN.findall(text.lower()):
        t = t.replace("'", "").replace("\u2019", "")
        out.append("prop" if t == "proposition" else t)
    return out


def stem(word):
    """A deliberately crude suffix stripper: housing, houses and house all become 'hous'."""
    for suffix in ("ing", "ed", "es", "s", "ly"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            word = word[:-len(suffix)]
            break
    if word.endswith("e") and len(word) > 4:
        word = word[:-1]
    return word


def content_terms(tokens):
    """Stemmed content words in order, with stop words and one- or two-letter words dropped."""
    return [stem(t) for t in tokens if t not in STOPWORDS and len(t) >= 3]


def bigrams(terms):
    return {(terms[i], terms[i + 1]) for i in range(len(terms) - 1)}


# --------------------------------------------------------------------------- passages

PROCEDURAL = [
    "roll call", "madam clerk", "please call", "call the roll", "item number", "seconded", "second by",
    "without objection", "adjourn", "pledge of allegiance", "public comment", "three minutes",
    "two minutes", "unmute", "next speaker", "line up", "microphone", "moved by", "consent agenda",
    "mr president", "will the clerk", "motion", "roll", "minutes", "please state your name",
    "next item", "item number", "legislative clerk", "on that motion",
]


def build_passages(meeting_id, rows, min_words=45, max_words=90):
    """Cut caption rows into passages of about one to three sentences.

    A turn ends at '>>' (the captions' only speaker-change mark, which is unreliable). Inside a
    turn a passage closes at the first sentence end after min_words, or at max_words. Each
    passage keeps the stamp of the row its first word came from.
    """
    words, turn = [], 0
    for stamp, text in rows:
        for k, part in enumerate(text.split(">>")):
            if k > 0:
                turn += 1
            words.extend((w, stamp, turn) for w in part.split())
    passages, cur = [], []

    def close():
        if cur:
            passages.append({
                "id": "%s@%s" % (meeting_id, cur[0][1]),
                "meeting": meeting_id,
                "start": cur[0][1],
                "end": cur[-1][1],
                "text": " ".join(w for w, _, _ in cur),
            })
            del cur[:]

    for w, stamp, t in words:
        if cur and cur[-1][2] != t:
            close()
        cur.append((w, stamp, t))
        if (len(cur) >= min_words and re.search(r"[.?!]$", w)) or len(cur) >= max_words:
            close()
    close()
    return passages


def procedural_hits(text):
    low = " " + " ".join(tokenize(text)) + " "
    return sum(1 for p in PROCEDURAL if " " + p + " " in low)


def is_substantive(passage, min_words=25, min_terms=12):
    text = passage["text"]
    if len(text.split()) < min_words:
        return False
    if procedural_hits(text) >= 2:
        return False
    return len(set(content_terms(tokenize(text)))) >= min_terms


# --------------------------------------------------------------------------- priorities

def priority_match_text(p):
    """What a reader sees for a priority: its heading (if the text does not repeat it) and text."""
    sec = p.get("section") or ""
    if sec and not p["text"].startswith(sec):
        return sec + ". " + p["text"]
    return p["text"]


GENERIC_CAPS = {
    "san francisco", "california", "city", "county", "board", "supervisors", "mayor", "chamber",
    "commerce", "yes", "no", "we", "our", "the", "federal", "state", "june", "november", "january",
    "february", "march", "april", "may", "july", "august", "september", "october", "december",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "read", "see",
    "since", "to", "for", "and", "of", "in", "a", "an", "it", "this", "that", "these", "those",
    "prop", "proposition", "why", "vote", "what", "how", "when", "where",
}
_CONNECTORS = {"of", "for", "and", "the", "to", "&"}


def _is_cap(word):
    return bool(re.match(r"^[A-Z][A-Za-z0-9&'\u2019.-]*$", word)) or word == "&"


def _trim(tokens):
    """Drop stop words from both ends of a run of tokens."""
    lo, hi = 0, len(tokens)
    while lo < hi and tokens[lo] in STOPWORDS:
        lo += 1
    while hi > lo and tokens[hi - 1] in STOPWORDS:
        hi -= 1
    return tokens[lo:hi]


_PUNCT = ".,;:!?()\"'\u201c\u201d\u2018\u2019"


def extract_anchors(text):
    """Named things a priority points at: 'Prop H', capitalised names, acronyms.

    Returns a set of token tuples. A one-word anchor needs four letters and must not open a
    sentence. Anchors that are common words in the quotes are dropped later (see Context).
    """
    text = re.sub(r"['\u2019]s\b", "", text)
    anchors = set()
    for m in re.finditer(r"\b(?:Prop(?:osition)?|Measure)\s+([A-J]|\d{1,2})\b", text):
        anchors.add(("prop", m.group(1).lower()))
    for m in re.finditer(r"\b[A-Z]{3,}\b", text):
        toks = tuple(tokenize(m.group(0)))
        if toks and toks[0] != "prop":
            anchors.add(toks)
    raw = text.split()
    sentence_start = True
    i = 0
    while i < len(raw):
        bare = raw[i].strip(_PUNCT)
        if _is_cap(bare) and not (sentence_start and bare.lower() in STOPWORDS):
            j = i + 1
            run_end = i + 1
            while j < len(raw):
                b = raw[j].strip(_PUNCT)
                if _is_cap(b):
                    j += 1
                    run_end = j
                elif b.lower() in _CONNECTORS and j + 1 < len(raw) and _is_cap(raw[j + 1].strip(_PUNCT)):
                    j += 1
                else:
                    break
            run = [r.strip(_PUNCT) for r in raw[i:run_end]]
            toks = _trim([t for r in run for t in tokenize(r)])
            if len(toks) == 1:
                if not sentence_start and len(toks[0]) >= 4:
                    anchors.add((toks[0],))
            elif len(toks) <= 3:
                anchors.add(tuple(toks))
            elif toks:
                for n in (2, 3):
                    for k in range(len(toks) - n + 1):
                        win = toks[k:k + n]
                        if win[0] not in STOPWORDS and win[-1] not in STOPWORDS:
                            anchors.add(tuple(win))
            sentence_start = bool(re.search(r"[.!?:]$", raw[run_end - 1]))
            i = run_end
            continue
        sentence_start = bool(re.search(r"[.!?:]$", raw[i]))
        i += 1
    return {a for a in anchors if " ".join(a) not in GENERIC_CAPS
            and not all(t in STOPWORDS for t in a)}


def ngrams_upto(tokens, n=3):
    out = set()
    for size in range(1, n + 1):
        for k in range(len(tokens) - size + 1):
            out.add(tuple(tokens[k:k + size]))
    return out


# --------------------------------------------------------------------------- topics

TOPICS = {
    "housing": "housing home homes rent renter tenant tenants zoning affordable evict eviction construction "
               "apartment apartments permit permits developer development unit units landlord mortgage",
    "homelessness": "homeless homelessness encampment encampments shelter shelters supportive unhoused "
                    "navigation tent",
    "public safety": "police sfpd officer officers crime crimes safety sheriff dispatcher dispatchers 911 "
                     "firefighter firefighters fire theft arrest arrests enforcement",
    "drugs and health": "drug drugs fentanyl overdose overdoses treatment addiction mental hospital health "
                        "clinic clinics medicaid recovery sobering",
    "transit and streets": "muni transit bus buses bart sfmta street streets bike bicycle pedestrian pedestrians "
                           "highway traffic parking vehicle vehicles transportation rider riders",
    "budget and taxes": "budget tax taxes deficit revenue bond bonds funding fund controller spending "
                        "million billion appropriation fiscal",
    "business and downtown": "business businesses retail merchant merchants restaurant restaurants permitsf "
                             "downtown office tourism commercial economy economic jobs",
    "city government": "charter commission commissions ballot amendment amendments administrator contracting "
                       "contract contracts accountability transparency bureaucracy departments department "
                       "ordinance legislation",
    "schools": "school schools sfusd student students education teacher teachers college district",
    "labor": "worker workers union unions labor wage wages employee employees pension benefits bargaining",
    "climate and resilience": "climate seawall seismic resilience earthquake water energy environmental "
                              "flooding emergency",
    "arts and culture": "art arts culture cultural nightlife music festival museum artists",
    "federal policy": "federal trump congress immigrant immigrants immigration washington",
}
TOPIC_STEMS = {name: {stem(w) for w in words.split()} for name, words in TOPICS.items()}


def active_topics(terms, min_distinct=3):
    """Topics with at least min_distinct different keywords present."""
    have = set(terms)
    return {name for name, kws in TOPIC_STEMS.items() if len(kws & have) >= min_distinct}


# --------------------------------------------------------------------------- the ways of matching

METHODS = [
    ("tfidf", "TF-IDF cosine over content words"),
    ("phrase", "Shared two-word phrases (rare ones only)"),
    ("topic", "Shared topic from a 13-topic keyword list"),
    ("anchor", "Shared named thing (measure letter, name, acronym)"),
    ("both", "TF-IDF cosine and a shared phrase, together"),
]


class Context:
    """Everything the matchers need from the priorities and the real quotes, fixed once."""

    def __init__(self, priorities, quote_tokens, generic_phrase_share=0.02, generic_anchor_share=0.01):
        self.priorities = priorities
        self.n_quotes = len(quote_tokens)
        p_tokens = [tokenize(priority_match_text(p)) for p in priorities]
        self.p_terms = [content_terms(t) for t in p_tokens]
        q_terms = [content_terms(t) for t in quote_tokens]
        df = Counter()
        for terms in self.p_terms + q_terms:
            df.update(set(terms))
        n_docs = len(self.p_terms) + len(q_terms)
        self.idf = {t: math.log((n_docs + 1) / (c + 1)) + 1.0 for t, c in df.items()}
        self.p_vec = [self._vector(terms) for terms in self.p_terms]
        self.p_index = defaultdict(list)
        for pi, vec in enumerate(self.p_vec):
            for term, w in vec.items():
                self.p_index[term].append((pi, w))
        # two-word phrases that are too common in the quotes to point at anything
        qb_df = Counter()
        for terms in q_terms:
            qb_df.update(bigrams(terms))
        limit = generic_phrase_share * len(q_terms)
        self.generic_phrases = {b for b, c in qb_df.items() if c > limit}
        self.p_bigrams = [bigrams(terms) - self.generic_phrases for terms in self.p_terms]
        self.bigram_index = defaultdict(list)
        for pi, bs in enumerate(self.p_bigrams):
            for b in bs:
                self.bigram_index[b].append(pi)
        # topics
        self.p_topics = [active_topics(terms) for terms in self.p_terms]
        self.topic_index = defaultdict(list)
        for pi, ts in enumerate(self.p_topics):
            for t in ts:
                self.topic_index[t].append(pi)
        # named anchors, minus any that are common words in the quotes
        q_gram_df = Counter()
        for toks in quote_tokens:
            q_gram_df.update(ngrams_upto(toks))
        limit = generic_anchor_share * len(quote_tokens)
        self.p_anchors = []
        self.anchor_index = defaultdict(list)
        for pi, p in enumerate(priorities):
            raw = (p.get("section") or "") + ". " + p["text"]
            kept = {a for a in extract_anchors(raw) if q_gram_df.get(a, 0) <= limit}
            self.p_anchors.append(kept)
            for a in kept:
                self.anchor_index[a].append(pi)

    def _vector(self, terms):
        tf = Counter(terms)
        vec = {t: (1.0 + math.log(c)) * self.idf.get(t, 1.0) for t, c in tf.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}


def score_quotes(ctx, quote_tokens, floor=0.10):
    """Score every quote against every priority with each way. Returns {method: {(qi, pi): score}}."""
    out = {m: {} for m, _ in METHODS}
    for qi, toks in enumerate(quote_tokens):
        terms = content_terms(toks)
        # TF-IDF cosine
        tf = Counter(terms)
        vec = {t: (1.0 + math.log(c)) * ctx.idf.get(t, 1.0) for t, c in tf.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        acc = defaultdict(float)
        for t, w in vec.items():
            for pi, pw in ctx.p_index.get(t, ()):
                acc[pi] += (w / norm) * pw
        for pi, s in acc.items():
            if s >= floor:
                out["tfidf"][(qi, pi)] = s
        # shared rare two-word phrases
        shared = Counter()
        for b in bigrams(terms):
            for pi in ctx.bigram_index.get(b, ()):
                shared[pi] += 1
        for pi, n in shared.items():
            out["phrase"][(qi, pi)] = float(n)
        # shared topic
        qt = active_topics(terms)
        count = Counter()
        for t in qt:
            for pi in ctx.topic_index.get(t, ()):
                count[pi] += 1
        for pi, n in count.items():
            out["topic"][(qi, pi)] = float(n)
        # shared named thing
        found = Counter()
        for g in ngrams_upto(toks):
            for pi in ctx.anchor_index.get(g, ()):
                found[pi] += 1
        for pi, n in found.items():
            out["anchor"][(qi, pi)] = float(n)
    # both: cosine, but only where a rare phrase is also shared
    out["both"] = {k: s for k, s in out["tfidf"].items() if k in out["phrase"]}
    return out


LEVELS = {
    "tfidf": [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50],
    "phrase": [1, 2, 3],
    "topic": [1, 2, 3],
    "anchor": [1, 2, 3],
    "both": [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50],
}


def counts_at_levels(scores):
    """{method: [number of pairs scoring at or above each level]}."""
    out = {}
    for m, _ in METHODS:
        vals = sorted(scores[m].values())
        out[m] = [len(vals) - bisect.bisect_left(vals, lv - 1e-12) for lv in LEVELS[m]]
    return out


# --------------------------------------------------------------------------- chance model

def draw_null(quote_tokens, meeting_of, rng, within_meeting):
    """Quotes of the same lengths whose words are drawn at random.

    Pooled: every word comes from all quotes' words. Within meeting: from the quote's own
    meeting, so a meeting's vocabulary survives but no quote is coherent.
    """
    pools = {}
    groups = defaultdict(list)
    for toks, mid in zip(quote_tokens, meeting_of):
        groups[mid if within_meeting else None].extend(toks)
    for key, toks in groups.items():
        counts = Counter(toks)
        words = sorted(counts)
        cum, total = [], 0
        for w in words:
            total += counts[w]
            cum.append(total)
        pools[key] = (words, cum, total)
    out = []
    for toks, mid in zip(quote_tokens, meeting_of):
        words, cum, total = pools[mid if within_meeting else None]
        out.append([words[bisect.bisect_right(cum, rng.random() * total)] for _ in toks])
    return out


def calibrated_level(method, real_counts, null_means):
    """Lowest level at which a random-word run yields fewer than one pair on average."""
    for i, lv in enumerate(LEVELS[method]):
        if null_means[i] < 1.0:
            return i, lv
    return None, None


# --------------------------------------------------------------------------- samples

def stable_order(keys, salt):
    return sorted(keys, key=lambda k: hashlib.md5((salt + "|" + repr(k)).encode()).hexdigest())
