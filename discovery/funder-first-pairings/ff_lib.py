"""Shared logic for the funder-first pairings: funded pairs from the funding map's money snapshot, speaker
credit from caption text, the search of an official's turns for the donor's stated subject, the meeting minutes
check, and the money for a pair by committee and filing.

Nothing here decides that a remark is on the donor's subject or that a quote belongs to an official: it proposes
(candidates, a doubt level, a minutes check) and a person's review (data/reviews.json) decides. Nothing here
says why anyone said or gave anything. Standard library only (the minutes PDFs are read with pypdf in
legistar.py, outside this module).
"""

import bisect
import collections
import json
import os
import re

import fmap_lib as fl

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

TIED = ("own", "own-other", "measure")  # committees the official's own or a measure committee carrying the name
REGION_MAX_CHARS = 4200  # about 700 words of captions after an opening cue
PASSAGE_MAX_ROWS = 16
HIT_GAP_ROWS = 3

# --------------------------------------------------------------------------- officials and name cues

# The surname as the captions spell it when they get it right, and the spellings the earlier surveys saw the
# captions produce for it. 'CHIN' is a garble of Chen; Chan and Chen differ by one letter, so a credit to either
# is never better than medium doubt unless a district cue backs it (see credit_tier).
VARIANTS = {
    "Daniel Lurie": (["LURIE"], []),
    "Connie Chan": (["CHAN"], []),
    "Chyanne Chen": (["CHEN"], ["CHIN"]),
    "Matt Dorsey": (["DORSEY"], []),
    "Jackie Fielder": (["FIELDER"], []),
    "Bilal Mahmood": (["MAHMOOD"], ["MAMU"]),
    "Rafael Mandelman": (["MANDELMAN"], []),
    "Myrna Melgar": (["MELGAR"], []),
    "Danny Sauter": (["SAUTER"], ["SADR", "SAUDER", "SARDAR", "SOLDER"]),
    "Stephen Sherrill": (["SHERRILL"], ["SHERRELL", "CHERYL", "SHERYL"]),
    "Shamann Walton": (["WALTON"], []),
    "Alan Wong": (["WONG"], ["WANG", "HUANG", "ONE"]),
}
DISTRICT_WORDS = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5, "SIX": 6, "SEVEN": 7, "EIGHT": 8,
                  "NINE": 9, "TEN": 10, "ELEVEN": 11}
AMBIGUOUS_PAIR = ("Connie Chan", "Chyanne Chen")


def token_map():
    out = {}
    for official, (exact, garbled) in VARIANTS.items():
        for t in exact:
            out[t] = (official, True)
        for t in garbled:
            out[t] = (official, False)
    return out


TOKENS = token_map()
NAMES_RX = "|".join(sorted(TOKENS, key=len, reverse=True))
CUE_RX = re.compile(r"(?:DISTRICT\s+(?P<dist>\w+)\s+)?(?P<title>(?:VICE[\s-]+)?CHAIR|SUPERVISOR|PRESIDENT|MEMBER)\s+(?P<name>%s)\b"
                    % NAMES_RX)
ROLL_AFTER = re.compile(r"^[\s,.]*(?:(?:%s)[\s,.]*)?(?:I|I'M|EYES|EYE|AYE|AYES|NO|NOS|PRESENT|YES|HI)\b" % NAMES_RX)
OPEN_BEFORE = re.compile(r"(?:>>|[.?!]|NEXT UP|FIRST UP|WE HAVE|\b(?:OH|OKAY|ALL RIGHT|YES|YEAH|SO),?)\s*$")
CLOSER_RX = re.compile(r"(?:>>|[.?!])\s*MADAM CLERK\b|\bPLEASE CALL THE ROLL\b|\bWITHOUT OBJECTION\b")
# A new speaker introducing themselves (a department presenter, a member of the public) ends a member's turn
# even when no cue names the next speaker.
SELF_INTRO_RX = re.compile(r"\bMY NAME IS\b|\b(?:I'M|I AM)\s+(?:[A-Z.',-]+\s+){1,3}(?:[A-Z]+\s+)?(?:GOVERNMENT AFFAIRS|"
                           r"DIRECTOR|DEPUTY|MANAGER|LEGISLATIVE AIDE|ANALYST|COUNSEL|ATTORNEY|SENIOR|COMMISSIONER|EXECUTIVE)\b")
MAYOR_OPEN_RX = re.compile(r"ANY OPENING\s+REMARKS")
MAYOR_CLOSE_RX = re.compile(r"THANK YOU,?\s+(?:MR\.?\s+)?MAYOR(?:\s+LURIE)?")


class Doc:
    """One caption transcript as rows and as one text, with the offset of every row."""

    def __init__(self, rows):
        self.rows = rows
        self.starts, parts, pos = [], [], 0
        for _, t in rows:
            self.starts.append(pos)
            parts.append(t)
            pos += len(t) + 1
        self.text = " ".join(parts)

    def row_index(self, pos):
        return max(bisect.bisect_right(self.starts, pos) - 1, 0)

    def stamp(self, pos):
        return self.rows[self.row_index(pos)][0]


def find_regions(doc):
    """The stretches of a transcript opened by a cue that names an official as about to speak.

    A cue opens a turn when a member's title and name follow a '>>', a sentence end, 'NEXT UP' or 'WE HAVE' and
    are not a roll-call answer. A region runs to the next opening cue, roll call or clerk call, or 700 words.
    The Mayor's opening remarks are one region, from the presiding officer's question to 'THANK YOU, MAYOR'."""
    cues = []
    for m in CUE_RX.finditer(doc.text):
        official, exact = TOKENS[m.group("name")]
        before = doc.text[max(0, m.start() - 24):m.start()]
        after = doc.text[m.end():m.end() + 44]
        if ROLL_AFTER.match(after):
            kind = "rollcall"
        elif m.group("title").endswith(("SUPERVISOR", "CHAIR")) and OPEN_BEFORE.search(before):
            kind = "opener"
        else:
            kind = "mention"
        dist = DISTRICT_WORDS.get((m.group("dist") or "").upper())
        cues.append({"kind": kind, "official": official, "exact": exact, "start": m.start(), "end": m.end(),
                     "text": m.group(0), "district": dist})
    stops = sorted([c["start"] for c in cues if c["kind"] in ("opener", "rollcall")]
                   + [m.start() for m in CLOSER_RX.finditer(doc.text)]
                   + [m.start() for m in SELF_INTRO_RX.finditer(doc.text)])
    regions = []
    for c in cues:
        if c["kind"] != "opener":
            continue
        i = bisect.bisect_right(stops, c["end"] - 1)
        # the first stop strictly after the cue's own text
        nxt = next((s for s in stops[i:] if s >= c["end"]), None)
        end = min(nxt, c["end"] + REGION_MAX_CHARS) if nxt is not None else min(len(doc.text), c["end"] + REGION_MAX_CHARS)
        regions.append({"official": c["official"], "start": c["end"], "end": end, "cue": c["text"],
                        "cue_stamp": doc.stamp(c["start"]), "exact": c["exact"], "district": c["district"],
                        "bounded": nxt is not None and nxt < c["end"] + REGION_MAX_CHARS, "kind": "cue"})
    mo = MAYOR_OPEN_RX.search(doc.text)
    if mo and "MAYOR" in doc.text[max(0, mo.start() - 500):mo.start()]:
        mc = MAYOR_CLOSE_RX.search(doc.text, mo.end())
        if mc:
            regions.append({"official": "Daniel Lurie", "start": mo.end(), "end": mc.start(), "cue": "the presiding "
                            "officer asks the Mayor for opening remarks", "cue_stamp": doc.stamp(mo.start()),
                            "exact": True, "district": None, "bounded": True, "kind": "mayor-opening"})
    return sorted(regions, key=lambda r: r["start"])


def credit_tier(doc, region, ps):
    """(doubt, why) for a passage starting at offset ps inside a region.

    low: the opening cue spells the surname as the captions' own roster does, the region is closed by another
    cue, no further '>>' mark lies between the cue and the passage, and the passage starts within 400 words.
    medium: a garbled spelling, an unclosed region, a few '>>' marks or up to 700 words. high: otherwise. Chan and
    Chen are never better than medium without a district cue. The Mayor's opening remarks are low (named by the
    clerk's introduction and thanked by name when they end)."""
    gap = doc.text[region["start"]:ps]
    words, arrows = len(gap.split()), gap.count(">>")
    why = ["%d words after the cue '%s' (%s)" % (words, region["cue"], region["cue_stamp"])]
    if region["kind"] == "mayor-opening":
        return "low", ["inside the Mayor's opening remarks, which the presiding officer's question opens and "
                       "'THANK YOU, MAYOR' closes (%s)" % region["cue_stamp"]]
    if arrows:
        why.append("%d '>>' mark(s) between the cue and the passage" % arrows)
    if not region["exact"]:
        why.append("the caption garbles the surname")
    if not region["bounded"]:
        why.append("no cue closes the turn")
    if region["exact"] and region["bounded"] and arrows <= 1 and words <= 400:
        tier = "low"
    elif arrows <= 4 and words <= 700:
        tier = "medium"
    else:
        tier = "high"
    if tier == "low" and region["official"] in AMBIGUOUS_PAIR and not region["district"]:
        tier = "medium"
        why.append("Chan and Chen differ by one letter and no district cue is given")
    return tier, why


# --------------------------------------------------------------------------- the donor's stated subject

def term_rx(terms):
    """Whole-word, case-insensitive pattern for a list of terms; a term ending in '*' matches any word that
    starts with it."""
    if not terms:
        return None
    parts = []
    for t in sorted(terms, key=len, reverse=True):
        parts.append(re.escape(t[:-1]) + r"[A-Z]*" if t.endswith("*") else re.escape(t))
    return re.compile(r"(?<![A-Za-z0-9])(?:%s)(?![A-Za-z0-9])" % "|".join(parts), re.I)


def load_json(name, folder=DATA):
    with open(os.path.join(folder, name), encoding="utf-8") as f:
        return json.load(f)


def candidate_passages(doc, region, subject):
    """Passages of a credited region that hit the subject's terms: [{start, end, rows, anchor_hits, topic_hits,
    tier}]. Rows holding a hit are grouped when at most three rows apart; a passage runs from the row before
    the first hit to the row after the last, never past the region or 16 rows."""
    a_rx, t_rx = term_rx(subject.get("anchor", [])), term_rx(subject.get("topic", []))
    r0, r1 = doc.row_index(region["start"]), doc.row_index(max(region["end"] - 1, region["start"]))
    hits = []
    for i in range(r0, r1 + 1):
        lo = max(doc.starts[i], region["start"])
        hi = min(doc.starts[i] + len(doc.rows[i][1]), region["end"])
        seg = doc.text[lo:hi]
        a = sorted({m.group(0).upper() for m in a_rx.finditer(seg)}) if a_rx else []
        t = sorted({m.group(0).upper() for m in t_rx.finditer(seg)}) if t_rx else []
        if a or t:
            hits.append((i, a, t))
    groups, cur = [], []
    for h in hits:
        if cur and h[0] - cur[-1][0] > HIT_GAP_ROWS:
            groups.append(cur)
            cur = []
        cur.append(h)
    if cur:
        groups.append(cur)
    out = []
    for g in groups:
        i0 = max(g[0][0] - 1, r0)
        i1 = min(g[-1][0] + 1, r1, i0 + PASSAGE_MAX_ROWS - 1)
        start = max(doc.starts[i0], region["start"])
        end = min(doc.starts[i1] + len(doc.rows[i1][1]), region["end"])
        text = doc.text[start:end].strip()
        while text[:1] in ".>, ":
            text = text[1:]
        anchor = sorted({x for h in g for x in h[1]})
        topic = sorted({x for h in g for x in h[2]})
        out.append({"start": start, "end": end, "text": text, "first_stamp": doc.stamp(start),
                    "last_stamp": doc.stamp(max(end - 1, start)), "anchor_hits": anchor, "topic_hits": topic,
                    "tier": "specific" if anchor else "topic"})
    return out


def review_id(meeting_id, first_stamp, official, subject_id):
    return "%s|%s|%s|%s" % (meeting_id, first_stamp, official, subject_id)


# --------------------------------------------------------------------------- minutes

SURNAMES = {o: v[0][0].title() for o, v in VARIANTS.items()}
STOP = set("""THE AND FOR THAT THIS WITH THAT HAVE FROM WILL THEIR THERE THEY WERE BEEN WHICH WOULD ABOUT THESE THOSE
WHEN WHAT WHERE THEM THAN THEN ALSO INTO OVER SUCH ONLY MORE SOME VERY JUST WANT SUPERVISOR COLLEAGUES PRESIDENT
THANK ITEM BOARD CITY SAN FRANCISCO COUNTY""".split())

AYES_RX = re.compile(r"Ayes:\s*(\d+)\s*-\s*")
NOES_RX = re.compile(r"Noes:\s*(\d+)\s*-\s*")
MOTION_RX = re.compile(r"Supervisors?\s+(?P<mover>[A-Z][a-z]+),\s+seconded\s+by\s+Supervisors?\s+(?P<second>[A-Z][a-z]+),"
                       r"\s+moved\s+(?P<what>.{0,1500}?)(?:The\s+motion\s+(?P<res>carried|FAILED|failed)|\Z)", re.S)
SPONSOR_RX = re.compile(r"Sponsors?:\s*(?P<names>[^\n]+(?:\n\s*and\s+[A-Z][a-z]+[^\n]*)?)")
PRESENT_RX = re.compile(r"Members\s+Present:\s*(?P<names>.{0,400}?)(?=\bThe\s+Board\s+of\s+Supervisors\b|\n\s*\n|\Z)", re.S)
ADDRESSED_RX = re.compile(r"(?P<who>Mayor\s+[A-Z][a-z]+\s+[A-Z][a-z]+|Supervisor\s+[A-Z][a-z]+)\s+"
                          r"(?:addressed the Board(?:\s+of Supervisors)?\s+regarding|reported to the Board)"
                          r"(?P<what>.{0,700}?)(?:\n\s*\n|President\s+Mandelman\s+then|\Z)", re.S)


def read_names(chunk, n):
    """The first n surnames of a comma-separated list that may wrap over lines ('Chan, Chen, Dorsey, ...')."""
    names = []
    for part in " ".join(chunk.split()).split(","):
        m = re.match(r"\s*([A-Z][a-z]+)", part)
        if not m:
            break
        names.append(m.group(1))
        if len(names) == n or part.strip() != m.group(1):
            break
    return names


def names_in(chunk):
    return sorted({n.strip(" .\n") for n in re.split(r",|\band\b", re.sub(r"\s+", " ", chunk or "")) if n.strip(" .")})


def surname_list(names):
    return sorted({n.split()[-1].title() for n in names if n.split()})


def parse_minutes(text):
    """What the action minutes record, from their text: who was present, each vote with its motion and the
    surnames on each side, sponsors by file, and the minutes' own summaries of who addressed the Board."""
    text = text.replace("\r", "")
    present = []
    m = PRESENT_RX.search(text)
    if m:
        present = surname_list(names_in(m.group("names")))
    ayes_at = [a.start() for a in AYES_RX.finditer(text)]
    votes, prev_end = [], 0
    for k, a in enumerate(AYES_RX.finditer(text)):
        limit = ayes_at[k + 1] if k + 1 < len(ayes_at) else len(text)
        ayes = read_names(text[a.end():a.end() + 500], int(a.group(1)))
        noes = []
        nm = NOES_RX.search(text, a.end(), min(a.end() + 700, limit))
        if nm:
            noes = read_names(text[nm.end():nm.end() + 500], int(nm.group(1)))
        pre = text[max(prev_end, a.start() - 3500):a.start()]
        prev_end = (nm.end() if nm else a.end()) + 120  # past the names of this vote
        motion = None
        for mm in MOTION_RX.finditer(pre):
            motion = mm
        kind = "motion" if re.search(r"motion\s+(?:carried|FAILED|failed)[^.]{0,60}$", pre[-160:], re.I) else "passage"
        votes.append({"pos": a.start(), "ayes": ayes, "noes": noes, "kind": kind,
                      "mover": motion.group("mover").title() if motion else "",
                      "seconder": motion.group("second").title() if motion else "",
                      "motion": re.sub(r"\s+", " ", motion.group("what"))[:300] if motion else "",
                      "context": re.sub(r"\s+", " ", pre[-1200:])})
    motions = [{"mover": mm.group("mover").title(), "seconder": mm.group("second").title(),
                "what": re.sub(r"\s+", " ", mm.group("what"))[:300], "pos": mm.start()}
               for mm in MOTION_RX.finditer(text)]
    sponsors = []
    for s in SPONSOR_RX.finditer(text):
        first = re.split(r"[;,]|\band\b", s.group("names"))[0].split()
        sponsors.append({"names": surname_list(re.split(r"[;,]|\band\b", s.group("names"))),
                         "primary": first[-1].title() if first else "",
                         "context": re.sub(r"\s+", " ", text[max(0, s.start() - 300):s.end() + 500])})
    spoke = [{"who": a.group("who").split()[-1].title(), "text": re.sub(r"\s+", " ", a.group("what"))[:700]}
             for a in ADDRESSED_RX.finditer(text)]
    mentioned = sorted(sn for sn in SURNAMES.values() if re.search(r"\b%s\b" % sn, text))
    return {"present": present, "votes": votes, "motions": motions, "sponsors": sponsors, "spoke": spoke,
            "mentioned": mentioned, "length": len(text)}


def content_words(text, minimum=5):
    return {w for w in re.findall(r"[A-Za-z]+", text.upper()) if len(w) >= minimum and w not in STOP}


def stance_of(passage):
    """'no', 'yes' or None: the vote the passage states for its speaker, when it states one."""
    t = " " + passage.upper() + " "
    no = re.search(r"\b(?:VOTING|VOTE|VOTED)\s+(?:NO|AGAINST)\b|\bWILL NOT (?:BE ABLE TO )?SUPPORT\b|\bNOT SUPPORT\b|"
                   r"\bCANNOT SUPPORT\b|\bAM NOT GOING TO BE VOTING IN SUPPORT\b", t)
    yes = re.search(r"\b(?:VOTING|VOTE|VOTED)\s+(?:YES|AYE|IN SUPPORT|FOR)\b|\bI(?:'LL| WILL| AM|'M)\s+"
                    r"(?:BE\s+)?SUPPORT(?:ING)?\b|\bHAPPY TO SUPPORT\b|\bI WILL BE SUPPORTING\b", t)
    if bool(no) == bool(yes):
        return None
    return "no" if no else "yes"


def check_minutes(minutes, official, passage):
    """Set one credit against the minutes. Returns {status, checks, ...}.

    status: 'confirmed' (the minutes record an act by the credited official that fits the passage: a vote on the
    side the words state, a motion, addressing the Board), 'consistent' (the minutes list the official as sponsor of
    an item the passage is about, which fits but does not show who spoke),
    'conflict' (they record the official on the other side of the best-matching vote, or as not present: a
    person must decide which vote the words are about), 'silent' (the minutes record nothing on it; ordinary
    for floor remarks), 'no_minutes' (none read)."""
    if not minutes:
        return {"status": "no_minutes", "checks": []}
    sn = SURNAMES[official]
    checks, status = [], "silent"
    if official != "Daniel Lurie" and minutes["present"] and sn not in minutes["present"]:
        if sn not in minutes["mentioned"]:
            return {"status": "conflict", "checks": ["The minutes name %s nowhere, and list the members present "
                                                      "without them." % sn]}
        checks.append("%s is not in the minutes' list of members present but is named elsewhere in them." % sn)
    elif official != "Daniel Lurie" and minutes["present"]:
        checks.append("%s is listed present." % sn)
    words = content_words(passage)
    stance = stance_of(passage)
    if stance:
        scored = []
        about_amendment = "AMENDMENT" in passage.upper()
        for v in minutes["votes"]:
            if sn in v["ayes"] or sn in v["noes"]:
                ctx = content_words(v["context"] + " " + v["motion"])
                shared = len(words & ctx)
                bonus = 4 if (about_amendment and v["kind"] == "motion") or (not about_amendment and v["kind"] == "passage") else 0
                scored.append((shared + bonus, shared, v))
        scored.sort(key=lambda x: -x[0])
        if scored and scored[0][1] >= 3:
            best = scored[0][2]
            side = "no" if sn in best["noes"] else "yes"
            tied = [x for x in scored[1:] if x[0] == scored[0][0] and (sn in x[2]["noes"]) != (sn in best["noes"])]
            shared_w = sorted(words & content_words(best["context"] + " " + best["motion"]))[:6]
            if tied:
                checks.append("Passage states a vote of %s; two votes in the minutes fit it equally and %s is on "
                              "opposite sides of them: a person must say which vote the words are about." % (stance.upper(), sn))
            else:
                line = "Passage states a vote of %s; the best-matching vote in the minutes (words shared: %s) lists %s on the %s side" % (
                    stance.upper(), ", ".join(shared_w), sn, "Noes" if side == "no" else "Ayes")
                if best["motion"]:
                    line += " (motion: %s)" % best["motion"][:140]
                checks.append(line + ".")
                status = "confirmed" if side == stance else "conflict"
        else:
            checks.append("Passage states a vote of %s; no vote in the minutes shares enough words with it to be "
                          "matched." % stance.upper())
    mv = re.search(r"\bI(?:'D)? (?:WOULD LIKE TO )?MOVE\b|\bI(?:'LL)? MAKE A MOTION\b|\bI(?: WOULD LIKE TO)? MAKE A MOTION\b", passage.upper())
    if mv:
        w4 = content_words(passage, 4)
        by = [m for m in minutes["motions"] if m["mover"] == sn and len(w4 & content_words(m["what"], 4)) >= 2]
        if by:
            checks.append("The minutes record a motion moved by %s (%s...)." % (sn, by[0]["what"][:100]))
            if status != "conflict":
                status = "confirmed"
        else:
            checks.append("The passage moves something; the minutes record no motion moved by %s that shares enough "
                          "words with it." % sn)
            status = "conflict"
    up = passage.upper()
    own = re.search(r"\bMY (?:CO-?SPONSORS|LEGISLATION)\b|\bI(?:'M| AM) (?:INTRODUCING|CO-?SPONSORING)\b|\bI(?:'M| AM) PROUD TO CO-?SPONSOR\b", up)
    present_item = re.search(r"\bTHIS (?:MEASURE|ORDINANCE|LEGISLATION|RESOLUTION|ITEM|CHARTER AMENDMENT)\b", up)
    if own or present_item:
        mine = [s for s in minutes["sponsors"] if sn in s["names"] and (own or s["primary"] == sn)
                and len(words & content_words(s["context"])) >= 3]
        if mine:
            checks.append("The minutes list %s as %s of an item whose title shares words with the passage; that fits "
                          "a sponsor presenting it, but the minutes do not say who spoke." % (
                              sn, "a sponsor" if own else "the first-named sponsor"))
            if status == "silent":
                status = "consistent"
        elif own:
            checks.append("The passage speaks as a sponsor; no item the minutes list under %s's sponsorship shares "
                          "enough words with it." % sn)
    for s in minutes["spoke"]:
        if s["who"] == sn:
            shared = sorted(words & content_words(s["text"], 4))[:5]
            checks.append("The minutes summarise %s addressing the Board%s." % (
                sn, (" (words shared with the passage: %s)" % ", ".join(shared)) if shared else ""))
            if status != "conflict":
                status = "confirmed"
    return {"status": status, "checks": checks}


# --------------------------------------------------------------------------- money

def key_a(filer, date, amt):
    return (filer, (date or "")[:10], round(float(amt or 0), 2))


def load_snapshot():
    snap = load_json("money_snapshot.json")
    fams = load_json("families.json")["families"]
    for key, rows in snap["family_rows"].items():
        snap["family_rows"][key] = [r for r in rows if fl.family_of(fams, fl.donor_name(r), r.get("committee_id"))[0] == key]
    for c in snap["committees"]:
        c["relation"], c["relation_words"] = fl.relation_of(c)
    return snap, fams


def committee_kind(c):
    rel = c["relation"]
    if rel == "measure":
        return "ballot-measure committee carrying the official's name"
    if rel in ("supporting", "opposing"):
        return "committee formed to %s the official (not the official's own)" % ("support" if rel == "supporting" else "oppose")
    kind = "officeholder committee" if ("OFFICEHOLDER" in c["filer_name"].upper() or c["filer_type"] == "470 [Officeholder]") \
        else "own committee"
    if rel == "own-other":
        kind += ", for another office (%s)" % fl.office_of(c["filer_name"])
    return kind


def vnum(r):
    v = r.get("filing_version")
    try:
        return str(int(float(v)))
    except (TypeError, ValueError):
        return str(v or "")


def pair_money(snap, official, family):
    """The family's Schedule A money beside an official, per receiving committee and per filing.

    Schedule A rows are counted once: identical rows are dropped, and a row that repeats another filing's row
    (same committee, date, amount and giver) is listed and not counted. A 24-hour report (form 497 part 1)
    that repeats a Schedule A row is listed and not counted; one without a Schedule A row is listed apart with
    its own total. Totals are per committee and never added across committees."""
    mine = {c["filer_nid"]: c for c in snap["committees"] if c["official"] == official}
    rows = [r for r in snap["family_rows"].get(family, []) if r["filer_nid"] in mine]
    a_all = [r for r in rows if r["form_type"] == "A"]
    a_keys = {key_a(r["filer_nid"], r["calculated_date"], r["calculated_amount"]) for r in a_all}
    per = collections.OrderedDict()
    dropped = []
    for nid, c in mine.items():
        mrows = [r for r in rows if r["filer_nid"] == nid]
        if not mrows:
            continue
        seen, counted = {}, []
        for r in (x for x in mrows if x["form_type"] == "A"):
            k = (r["calculated_date"][:10], round(float(r["calculated_amount"]), 2), fl.donor_name(r).upper())
            if k in seen:
                dropped.append({"row": r, "repeats_filing": seen[k]})
                continue
            seen[k] = r["filing_id_number"]
            counted.append(r)
        h = [r for r in mrows if r["form_type"] == "F497P1"]
        rep = [r for r in h if key_a(nid, r["calculated_date"], r["calculated_amount"]) in a_keys]
        only = [r for r in h if r not in rep]
        per[nid] = {"committee": c, "kind": committee_kind(c), "a": counted,
                    "a_sum": sum(float(r["calculated_amount"]) for r in counted), "repeat": rep, "only": only,
                    "only_sum": sum(float(r["calculated_amount"]) for r in only)}
    return {"per": per, "dropped": dropped, "tied": any(c["committee"]["relation"] in TIED for c in per.values())}


def money_summary(m):
    """A JSON-ready copy of pair_money for the results file."""
    out = []
    for nid, c in m["per"].items():
        out.append({
            "committee": c["committee"]["filer_name"], "filer_nid": nid, "relation": c["committee"]["relation"],
            "kind": c["kind"], "schedule_a_total": c["a_sum"], "schedule_a_rows": len(c["a"]),
            "first_date": min((fl.day(r["calculated_date"]) for r in c["a"]), default=""),
            "last_date": max((fl.day(r["calculated_date"]) for r in c["a"]), default=""),
            "givers_as_filed": sorted({fl.donor_name(r) for r in c["a"] + c["repeat"] + c["only"]}),
            "filings": sorted({"%s (v%s)" % (r["filing_id_number"], vnum(r)) for r in c["a"]}),
            "rows": [{"date": fl.day(r["calculated_date"]), "amount": float(r["calculated_amount"]),
                      "filing": r["filing_id_number"], "version": vnum(r), "filing_date": fl.day(r["filing_date"]),
                      "giver": fl.donor_name(r)} for r in c["a"]],
            "h24_repeats_not_counted": len(c["repeat"]), "h24_only_rows": len(c["only"]),
            "h24_only_total": c["only_sum"]})
    return out


def funded_pairs(snap):
    """Every (official, family) with Schedule A money in a committee tied to the official, as
    {(official, family): pair_money}, ordered by official then family."""
    pairs = {}
    officials = sorted({c["official"] for c in snap["committees"]})
    for fam in sorted(snap["family_rows"]):
        for off in officials:
            m = pair_money(snap, off, fam)
            if m["per"] and any(c["a"] for c in m["per"].values()):
                pairs[(off, fam)] = m
    return pairs


def outside_spending(snap, fams, official, family):
    """Form 496 spending that names the official, by committees the family's names take: kept apart from gifts
    and never added to them. [{payer, stance, amount, filings, first, last}]"""
    c0 = next(c for c in snap["committees"] if c["official"] == official)
    agg = {}
    for r in snap.get("independent", []):
        if not fl.names_official(r["candidate_last_name"], c0["surname"], c0["given"]):
            continue
        dist = (r.get("district_number") or "").strip()
        if dist and c0["district"] and dist != c0["district"]:
            continue
        office = (r.get("office_description") or "").upper()
        if c0["office"] == "Mayor" and "SUPERVISOR" in office:
            continue
        if c0["office"] != "Mayor" and "MAYOR" in office:
            continue
        if fl.family_of(fams, r["filer_name"])[0] != family:
            continue
        a = agg.setdefault((r["filer_nid"], r["support_oppose_code"]), {
            "payer": r["filer_name"], "stance": "supporting" if r["support_oppose_code"] == "S" else "opposing",
            "amount": 0.0, "filings": set(), "first": "9999", "last": ""})
        a["amount"] += float(r["amt"])
        a["filings"].add(r["filing_id_number"])
        a["first"] = min(a["first"], fl.day(r["d0"]))
        a["last"] = max(a["last"], fl.day(r["d1"]))
    return [dict(a, filings=sorted(a["filings"])) for a in agg.values()]


def tie_note(m, fams):
    """How the givers in a pair are recognised as the donor's: by the FPPC id they carry that the Filers dataset
    resolves, or by name only."""
    how = collections.Counter()
    for c in m["per"].values():
        for r in c["a"] + c["repeat"] + c["only"]:
            how[fl.family_of(fams, fl.donor_name(r), r.get("committee_id") or "")[1] or "name"] += 1
    return {"by_id_rows": how.get("id", 0), "by_name_rows": how.get("name", 0)}
