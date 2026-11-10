"""The shortlist, the AI filter and the cards.

shortlist()   passages in turns credited to an official that hit the measure names, phrases and named things
              of a donor's stated priority (a wide net: topic words count too);
decide()      what the model's reading of a pair means: kept, or dropped with a reason
              (it shares only topic words, or takes the opposite position, or is not an official speaking);
auto_publish() whether a kept pair is published at once (labelled as not reviewed by a person) or held for review;
build_card()  one card from a kept pair: the exact words with meeting, date and transcript time, the speaker
              credit with how the captions support it, the donor's own words with link and retrieval date, and
              the money by committee and filing, 24-hour repeats listed and not counted.

Nothing here says why anyone said or gave anything.
"""

import collections
import re

from . import priorities as donor_priorities, sources  # noqa: F401  (sources puts the discovery libraries on the path)

import ff_lib as ff  # noqa: E402
import fmap_lib as fl  # noqa: E402
import judge as judge_mod  # noqa: E402
import legistar as lg  # noqa: E402
import pairing_cards as pc  # noqa: E402
import trial_lib as tl  # noqa: E402

DOUBT_ORDER = {"low": 0, "medium": 1, "high": 2}
GRANICUS_VIEWS = {"Board of Supervisors": 10, "Land Use and Transportation Committee": 177, "Rules Committee": 13,
                  "Government Audit and Oversight Committee": 11}
OPPOSING_NOTE = ("No agreement or disagreement is claimed beyond the model's reading, which a person checks "
                 "before anything is published.")


# --------------------------------------------------------------------------- meetings and captions

def recording_url(meeting_id, body):
    """The recording of a meeting. The transcript id is the Granicus clip id of the same recording."""
    view = GRANICUS_VIEWS.get(body)
    if view:
        return "https://sanfrancisco.granicus.com/MediaPlayer.php?view_id=%d&clip_id=%d" % (view, meeting_id)
    return "https://sanfrancisco.granicus.com/player/clip/%d" % meeting_id


def transcript_url(meeting_id):
    return lg.TRANSCRIPT % meeting_id


def captions_text(rows):
    return "".join("%s\t%s\n" % (s, t) for s, t in rows)


def parse_captions(text):
    rows = []
    for line in text.splitlines():
        stamp, sep, body = line.partition("\t")
        if sep:
            rows.append((stamp, " ".join(body.split())))
    return rows


class Transcript:
    """One stored meeting: its row, its caption rows, and the credited regions found in it (once)."""

    def __init__(self, meeting):
        self.meeting = meeting
        self.rows = parse_captions(meeting["captions"])
        self.doc = ff.Doc(self.rows)
        self._regions = None

    @property
    def regions(self):
        if self._regions is None:
            self._regions = ff.find_regions(self.doc)
        return self._regions


# --------------------------------------------------------------------------- the donor's stated subject

def priority_text(statement):
    return tl.priority_match_text({"section": statement.get("section") or "", "text": statement["text"]})


def subject_terms(statements):
    """Search terms read from a donor's own words: its measure names, phrases and named things (anchors), and the
    keywords of every broad topic its words speak of (topic words). Not tuned to any transcript."""
    text = " ".join(priority_text(s) for s in statements)
    anchors = set()
    for a in tl.extract_anchors(text):
        if a[0] == "prop" and len(a) == 2:
            anchors.add("PROP " + a[1].upper())
            anchors.add("PROPOSITION " + a[1].upper())
        else:
            anchors.add(" ".join(a).upper())
    stems = {tl.stem(w) for w in tl.tokenize(text)}
    topic = set()
    for words in tl.TOPICS.values():
        kws = words.split()
        if len({tl.stem(w) for w in kws} & stems) >= 3:
            topic.update(w.upper() for w in kws if tl.stem(w) in stems)
    return {"anchor": sorted(anchors), "topic": sorted(topic - anchors)}


def best_statement(passage_text, statements):
    """The donor statement that shares the most content words with the passage."""
    have = {w for w in tl.tokenize(passage_text) if w not in tl.STOPWORDS}

    def score(s):
        return len(have & {w for w in tl.tokenize(priority_text(s)) if w not in tl.STOPWORDS})
    return max(statements, key=score)


def candidate_key(meeting_id, first_stamp, official, family):
    return ff.review_id(meeting_id, first_stamp, official, family)


def shortlist(transcripts, pairs, priorities, seen, limit):
    """New candidates, specific hits first. pairs is {(official, family): money}; priorities {family: [rows]};
    seen the candidate keys already decided. Returns (candidates, found, capped)."""
    out = []
    for (official, family), money in pairs.items():
        statements = priorities.get(family)
        if not statements or not money["tied"]:
            continue
        subject = subject_terms(statements)
        for tr in transcripts:
            for reg in tr.regions:
                if reg["official"] != official:
                    continue
                for p in ff.candidate_passages(tr.doc, reg, subject):
                    key = candidate_key(tr.meeting["id"], p["first_stamp"], official, family)
                    if key in seen:
                        continue
                    doubt, why = ff.credit_tier(tr.doc, reg, p["start"])
                    out.append({"key": key, "official": official, "family": family, "meeting": tr.meeting,
                                "transcript": tr, "passage": p, "region": reg, "doubt": doubt, "why": why,
                                "statement": best_statement(p["text"], statements)})
    out.sort(key=lambda c: (0 if c["passage"]["tier"] == "specific" else 1, DOUBT_ORDER[c["doubt"]],
                            str(c["meeting"]["meeting_date"]), c["key"]))
    # one passage per key; a passage that overlaps another of the same pair on the same stamps is the same remark
    unique, keys = [], set()
    for c in out:
        if c["key"] not in keys:
            keys.add(c["key"])
            unique.append(c)
    return unique[:limit], len(unique), len(unique) > limit


# --------------------------------------------------------------------------- the AI filter

def judge_label(c):
    return c["key"]


def prompt_for(c, donor_name):
    m = c["meeting"]
    priority = {"donor": donor_name, "section": c["statement"].get("section") or "", "text": c["statement"]["text"]}
    return judge_mod.build_prompt(c["passage"]["text"], "%s, %s" % (m["body"], m["meeting_date"]), priority)


def decide(record):
    """(keep, reason_kind, reason) for the model's record of a pair. A pair is kept only when the model reads a
    real overlap on a specific measure or position, the words are an official's, and the positions do not oppose."""
    why = record.get("reason", "")
    if record["overlap"] != "real":
        return False, "topic-only", "Shares topic words only (the model read the overlap as %s): %s" % (record["overlap"], why)
    if record["speaker_type"] not in judge_mod.ELIGIBLE_SPEAKERS:
        return False, "not-an-official", "The words do not read as an official speaking for themselves (read as %s): %s" % (
            record["speaker_type"].replace("_", " "), why)
    if record["stance"] == "opposes":
        return False, "opposing", "The official's words take the opposite position to the donor's: %s" % why
    return True, "kept", why


HOLD_STANCES = ("mixed", "no_position")  # the model could not read a clear position for the official


def auto_publish(card, record):
    """(publish, reason) for a kept pair. A card is published at once, labelled as not reviewed by a person, unless
    it is low-confidence: the speaker credit is in high doubt, or the model read the official's position as mixed or
    absent. A held card waits in the review queue for an admin."""
    doubt = card.get("speaker_credit", {}).get("doubt")
    if doubt == "high":
        return False, "the speaker credit is in high doubt"
    if record.get("stance") in HOLD_STANCES:
        return False, "the model read the official's position as %s" % record["stance"].replace("_", " ")
    return True, "automated match: speaker-credit doubt %s, the model read the positions as %s" % (
        doubt or "not stated", record.get("stance", "not stated").replace("_", " "))


# --------------------------------------------------------------------------- money

def load_snapshot(source, fams_payload):
    """The snapshot dict the money functions read, from the stored source data: {name: payload}."""
    fams = fams_payload["families"]
    committees = [dict(c) for c in source["committees"]]
    for c in committees:
        c["relation"], c["relation_words"] = fl.relation_of(c)
    family_rows = {}
    for fam in fams:
        rows = source.get("family_rows:" + fam["key"], [])
        family_rows[fam["key"]] = [r for r in rows if fl.family_of(fams, fl.donor_name(r), r.get("committee_id"))[0] == fam["key"]]
    meta = source.get("meta", {})
    return {"committees": committees, "family_rows": family_rows, "filers_lookup": source.get("filers_lookup", {}),
            "independent": source.get("independent", []), "retrieved": meta.get("retrieved", ""),
            "data_loaded_at": meta.get("data_loaded_at", ""), "dataset": fl.DATASET_PAGE}


def money_for_pair(snap, fams, official, family):
    """Money in the shape pairing_cards reads: per committee Schedule A (identical rows dropped, a row repeating
    another filing's row and 24-hour repeats listed and not counted) and outside spending kept apart."""
    m = ff.pair_money(snap, official, family)
    outside = [{"payer": o["payer"], "stance": "S" if o["stance"] == "supporting" else "O", "amount": o["amount"],
                "filings": len(o["filings"]), "d0": o["first"], "d1": o["last"]}
               for o in ff.outside_spending(snap, fams, official, family)]
    return {"per": m["per"], "outside": outside, "dropped": m["dropped"], "tied": m["tied"]}


def row_detail(r, kind):
    return {"kind": kind, "contribution_date": fl.day(r["calculated_date"]), "amount": float(r["calculated_amount"]),
            "amount_text": fl.dollars(r["calculated_amount"]), "filing_id": r["filing_id_number"],
            "version": ff.vnum(r), "filing_date": fl.day(r["filing_date"]), "giver": fl.donor_name(r)}


# --------------------------------------------------------------------------- cards

def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:90]


def highlight_terms(quote, statements, hits):
    """Words literally in both the quote and the donor's words, from the terms the shortlist hit."""
    texts = [(s.get("section") or "") + " " + s["text"] for s in statements]
    out = []
    for t in hits:
        rx = pc.term_regex([t])
        if rx.search(quote) and any(rx.search(x) for x in texts) and t.lower() not in {o.lower() for o in out}:
            out.append(t)
    return out


def speaker_support(region, official, roster_line, rows):
    """How the captions support the credit: the cue that opens the turn, matched to the roster."""
    cue_rows = [[s, t] for s, t in fl.cue_rows(rows, [region["cue_stamp"]])]
    if region["kind"] == "mayor-opening":
        text = ("At %s the presiding officer asks the Mayor for opening remarks; the roster has one Mayor, %s." % (
            region["cue_stamp"], official))
    else:
        text = ("The turn is opened at %s by the cue '%s'; the cue's surname is matched to the roster's %s (%s)." % (
            region["cue_stamp"], region["cue"], official, roster_line))
    return text, cue_rows


def extend_card(card, p, support, cue_rows, recording):
    """Adds to a built card what its reader needs beyond pairing_cards' summary: each Schedule A row with its
    filing date, the 24-hour rows apart, how the transcript supports the speaker credit and the recording."""
    for line, c in zip(card["money"]["committees"], p["money"]["per"].values()):
        line["rows_detail"] = [row_detail(r, "Schedule A") for r in c["a"]]
        line["repeats_detail"] = [row_detail(r, "24-hour report repeating a Schedule A row (not counted)") for r in c["repeat"]]
        line["h24_only_detail"] = [row_detail(r, "24-hour report, no Schedule A row yet (apart, not in the total)") for r in c["only"]]
    card["money"]["duplicates_dropped"] = len(p["money"].get("dropped", []))
    card["speaker_credit"].update({"support": support, "cue_rows": cue_rows, "official": card["official"]["name"],
                                   "role": card["official"]["role"]})
    card["quote"]["recording_url"] = recording
    return card


def build_card(c, record, snap, fams, family, reading=None):
    """The card of a kept candidate (c from shortlist, record from the model). `reading` is (in common, where they
    differ) when a person's reading stands in for the model's. Returns (card, slug)."""
    m, p0, off = c["meeting"], c["passage"], c["official"]
    rows = c["transcript"].rows
    quote = {"text": p0["text"], "first_stamp": p0["first_stamp"], "last_stamp": p0["last_stamp"]}
    if not fl.is_verbatim(rows, quote["text"]):
        raise ValueError("candidate %s: the quote is not word for word in the transcript" % c["key"])
    c0 = next(x for x in snap["committees"] if x["official"] == off)
    sts = c.get("statements") or [c["statement"]]
    hits = highlight_terms(quote["text"], sts, p0["anchor_hits"] + p0["topic_hits"])
    slug = slugify("%s-%s-%s-%s" % (off, family["key"], m["meeting_date"], p0["first_stamp"]))
    support, cue_rows = speaker_support(c["region"], off, roster_line(snap, off), rows)
    stance = record["stance"].replace("_", " ")
    pk = {"id": c["key"], "slug": slug, "highlight": hits,
          "overlap": "Model's reading of what the two have in common: %s" % record["reason"],
          "stance": "Model's reading of the positions: the official's words %s the donor's statement. %s" % (
              {"agrees": "agree with", "mixed": "agree with in part", "no_position": "take no position on",
               "not_comparable": "are not comparable with"}.get(record["stance"], stance), OPPOSING_NOTE),
          "speaker": {"doubt": c["doubt"], "doubt_reason": "; ".join(c["why"])}}
    if reading:
        pk["overlap"], pk["stance"] = reading
    meeting = {"body": m["body"], "date": str(m["meeting_date"]), "url": m["url"], "retrieved": str(m["retrieved"])}
    p = {"pk": pk, "meeting": meeting, "quote": quote, "official": c0,
         "statements": [{"section": st.get("section") or "", "text": st["text"], "url": st["url"],
                         "page_date": st.get("page_date") or "", "retrieved": str(st["retrieved"]), "kind": st["kind"]}
                        for st in sts],
         "family": family, "money": money_for_pair(snap, fams, off, family["key"])}
    card = pc.build_cards([p], snap, fams)[0]
    for shown, st in zip(card["donor"]["statements"], sts):  # pairing_cards keeps no outlet: add it beside the kind
        shown["outlet"], shown["whose_words"] = st.get("outlet") or "", st.get("whose_words") or ""
    return extend_card(card, p, support, cue_rows, m["recording_url"]), slug


def roster_line(snap, official):
    c0 = next(x for x in snap["committees"] if x["official"] == official)
    return "%s%s" % (c0["office"], ", District %s" % c0["district"] if c0["district"] else "")


def funded_pairs(snap):
    return ff.funded_pairs(snap)


def group_priorities(rows):
    out = collections.defaultdict(list)
    for r in rows:
        out[r["family"]].append(r)
    return out


# --------------------------------------------------------------------------- the glance row

LEVELS = ("low", "med", "high")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
CREDIT_LEVEL = {"high": "low", "medium": "med", "low": "high"}  # the stored value is doubt: confidence is its inverse
COMMITTEE_LABELS = (("ballot-measure committee", "Ballot-measure committee"),
                    ("officeholder committee", "Officeholder committee"), ("own committee", "Own committee"))
RESOLVES = re.compile(r"that resolves? in the Filers dataset")


def best_sentence(text, terms):
    """The sentence of `text` that holds the most distinct shared terms, cut at its own boundaries (the first on a
    tie). Returns {"text", "before", "after", "found"}: before and after say that words were left out on that side.
    With no shared term, or one that is in no single sentence, the first sentence stands and found is 0."""
    parts = [s for s in SENTENCE_END.split(text.strip()) if s]
    if not parts:
        return {"text": text, "before": False, "after": False, "found": 0}
    rxs = [pc.term_regex([t]) for t in terms]
    counts = [sum(1 for rx in rxs if rx.search(s)) for s in parts]
    at = counts.index(max(counts))
    return {"text": parts[at], "before": at > 0, "after": at < len(parts) - 1, "found": counts[at]}


def committee_label(kind):
    """A short label for the card's committee kind (the long wording stays in the detail)."""
    label = next((short for long, short in COMMITTEE_LABELS if kind.startswith(long)), kind.capitalize())
    return label + (", other office" if "for another office" in kind else "")


def tie_level(tie_text):
    """How firmly the givers are recognised as the donor's, read from the card's tie text: every giver by Filers id
    is high; a mix, or names whose FPPC ids resolve in the Filers dataset, is med; names alone are low."""
    by_id, by_name = "by Filers id" in tie_text, "by name only" in tie_text
    if by_id and not by_name:
        return "high"
    return "med" if by_id or RESOLVES.search(tie_text) else "low"


def confidence(card, recording_checked=False):
    """The four chips of a card, always in this order: speaker credit, topic match, donor priority, money tie.
    Each is {"key", "label", "level", "text", "reason"}; level is low, med or high, and the speaker credit's is
    "verified" once a person has checked the recording. Computed from what the card already holds."""
    credit = card["speaker_credit"]
    doubt = credit["doubt"]
    speaker = {"key": "speaker", "label": "Speaker credit", "level": CREDIT_LEVEL[doubt],
               "reason": "Stored doubt in the credit is %s: %s" % (doubt, credit.get("reason") or "no reason recorded")}
    if recording_checked:
        speaker.update(level="verified", reason="A person played the recording and confirmed the words; "
                       "the stored doubt in the credit is %s." % doubt)
    shared = card["highlight"]
    topic = {"key": "topic", "label": "Topic match", "level": "high" if len(shared) >= 2 else "med" if shared else "low",
             "reason": ("%d word%s in both the quote and the donor's words: %s." % (
                 len(shared), "" if len(shared) == 1 else "s", ", ".join(shared))) if shared
             else "No word of substance is in both the quote and the donor's words."}
    statements = card["donor"]["statements"]
    own = [s for s in statements if s["kind"] != donor_priorities.NEWS]
    if own:
        prio = ("high", "Stated on a %s." % own[0]["kind"])
    elif any(s.get("whose_words") == "donor-quoted" for s in statements):
        prio = ("med", "A news report quoting the donor's own words.")
    else:
        prio = ("low", "A news report in someone else's words, not the donor's own page.")
    tie = card["donor"]["tie"]["text"]
    money = {"key": "money", "label": "Money tie", "level": tie_level(tie), "reason": tie.rstrip(".") + "."}
    chips = [speaker, topic, {"key": "priority", "label": "Donor priority", "level": prio[0], "reason": prio[1]}, money]
    for chip in chips:
        chip["text"] = chip["level"].upper()
    return chips


def glance(card, recording_checked=False):
    """What the glance row of a card shows, from the card alone: the chips; the quote cut at its best sentence; the
    donor statement that shares most with the quote, cut the same way; and one money line per committee with a
    short label. Nothing is summed and no value is made up."""
    shared = card["highlight"]
    quote = best_sentence(card["quote"]["text"], shared)
    statement = best_statement(card["quote"]["text"], card["donor"]["statements"])
    donor = best_sentence(statement["text"], shared)
    money = [{"label": committee_label(m["kind"]), "committee": m["committee"], "amount": m["schedule_a_total_text"]}
             for m in card["money"]["committees"]]
    return {"chips": confidence(card, recording_checked), "quote": quote, "statement": statement, "donor": donor,
            "money": money}
