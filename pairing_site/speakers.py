"""Who is speaking in a caption transcript: the turns the chair's (or clerk's) spoken cue hands to an official,
and how much doubt the credit carries.

Adapted from discovery/funder-first-pairings/ff_lib.py (the turn finder and the credit tiers). The spellings of
each surname now come from the roster in the database, and a cue spelled in a way the roster does not list is
matched to it by spelling (compare_lib.match_roster). Nothing here decides that a quote belongs to an official:
it proposes a speaker and a doubt level, and a person approves, edits the doubt or rejects.
"""

import bisect
import re

from . import compare_lib

REGION_MAX_CHARS = 4200  # about 700 words of captions after an opening cue
DISTRICT_WORDS = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5, "SIX": 6, "SEVEN": 7, "EIGHT": 8,
                  "NINE": 9, "TEN": 10, "ELEVEN": 11}
# Chan and Chen differ by one letter, so a credit to either is never better than medium without a district cue.
AMBIGUOUS_PAIR = ("Connie Chan", "Chyanne Chen")
NOT_A_GIVEN_NAME = {"THANK", "THANKS", "THE", "AND", "FOR", "THAT", "THIS", "WITH", "FROM", "SAID", "SAYS", "WILL",
                    "PLEASE", "MADAM", "CLERK", "MISTER", "PRESIDENT", "SUPERVISOR", "SUPERVISORS", "CHAIR"}

ROLL_AFTER_TAIL = r"(?:I|I'M|EYES|EYE|AYE|AYES|NO|NOS|PRESENT|YES|HI)\b"
OPEN_BEFORE = re.compile(r"(?:>>|[.?!]|NEXT UP|FIRST UP|WE HAVE|\b(?:OH|OKAY|ALL RIGHT|YES|YEAH|SO),?)\s*$")
CLOSER_RX = re.compile(r"(?:>>|[.?!])\s*MADAM CLERK\b|\bPLEASE CALL THE ROLL\b|\bWITHOUT OBJECTION\b")
# A new speaker introducing themselves (a department presenter, a member of the public) ends a member's turn
# even when no cue names the next speaker.
SELF_INTRO_RX = re.compile(r"\bMY NAME IS\b|\b(?:I'M|I AM)\s+(?:[A-Z.',-]+\s+){1,3}(?:[A-Z]+\s+)?(?:GOVERNMENT AFFAIRS|"
                           r"DIRECTOR|DEPUTY|MANAGER|LEGISLATIVE AIDE|ANALYST|COUNSEL|ATTORNEY|SENIOR|COMMISSIONER|EXECUTIVE)\b")
MAYOR_OPEN_RX = re.compile(r"ANY OPENING\s+REMARKS")
MAYOR_CLOSE_RX = re.compile(r"THANK YOU,?\s+(?:MR\.?\s+)?MAYOR(?:\s+[A-Z]+)?")


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


class Roster:
    """The officials a cue can name, with the surname spellings the captions give them."""

    def __init__(self, officials):
        """officials: [{name, surname, district, office, exact: [..], garbled: [..]}]"""
        self.officials = officials
        self.tokens = {}
        for o in officials:
            for t in o["exact"]:
                self.tokens[t.upper()] = (o["name"], True)
            for t in o["garbled"]:
                self.tokens[t.upper()] = (o["name"], False)
        names = "|".join(sorted(self.tokens, key=len, reverse=True))
        title = r"(?P<title>(?:VICE[\s-]+)?CHAIR|SUPERVISOR|PRESIDENT|MEMBER)"
        self.cue_rx = re.compile(
            r"(?:DISTRICT\s+(?P<dist>\w+)\s+)?%s\s+(?:(?!(?:%s)\b)(?P<given>[A-Z]{3,})\s+)?(?P<name>%s)\b" % (title, names, names))
        self.generic_rx = re.compile(r"(?:DISTRICT\s+(?P<dist>\w+)\s+)?(?P<title>SUPERVISOR|CHAIR)\s+(?P<name>[A-Z]{4,})\b")
        self.roll_after = re.compile(r"^[\s,.]*(?:(?:%s)[\s,.]*)?%s" % (names, ROLL_AFTER_TAIL))
        self.mayor = next((o["name"] for o in officials if o["office"] == "Mayor"), None)

    def cues(self, text):
        """[{kind, official, exact, start, end, text, district}] for every cue naming a roster official. kind is
        'opener' (a turn handed to the official), 'rollcall' (an answer to the roll) or 'mention'."""
        found = []
        for m in self.cue_rx.finditer(text):
            official, exact = self.tokens[m.group("name")]
            found.append(self._cue(text, m, official, exact and not m.group("given")))
        taken = [(c["start"], c["end"]) for c in found]
        for m in self.generic_rx.finditer(text):
            word = m.group("name")
            if word in self.tokens or word in NOT_A_GIVEN_NAME or any(a <= m.start() < b for a, b in taken):
                continue
            official, ratio, second = compare_lib.match_roster(word, self.officials)
            if official is None or ratio < 0.8 or ratio - second < 0.1:
                continue
            found.append(self._cue(text, m, official["name"], False))
        return sorted(found, key=lambda c: c["start"])

    def _cue(self, text, m, official, exact):
        before = text[max(0, m.start() - 24):m.start()]
        after = text[m.end():m.end() + 44]
        if self.roll_after.match(after):
            kind = "rollcall"
        elif m.group("title").endswith(("SUPERVISOR", "CHAIR")) and OPEN_BEFORE.search(before):
            kind = "opener"
        else:
            kind = "mention"
        return {"kind": kind, "official": official, "exact": exact, "start": m.start(), "end": m.end(),
                "text": m.group(0), "district": DISTRICT_WORDS.get((m.group("dist") or "").upper())}


def find_regions(doc, roster):
    """The stretches of a transcript opened by a cue that names an official as about to speak.

    A cue opens a turn when a member's title and name follow a '>>', a sentence end, 'NEXT UP' or 'WE HAVE' and
    are not a roll-call answer. A region runs to the next opening cue, roll call or clerk call, or 700 words.
    The Mayor's opening remarks are one region, from the presiding officer's question to 'THANK YOU, MAYOR'."""
    cues = roster.cues(doc.text)
    stops = sorted([c["start"] for c in cues if c["kind"] in ("opener", "rollcall")]
                   + [m.start() for m in CLOSER_RX.finditer(doc.text)]
                   + [m.start() for m in SELF_INTRO_RX.finditer(doc.text)])
    regions = []
    for c in cues:
        if c["kind"] != "opener":
            continue
        nxt = next((s for s in stops[bisect.bisect_left(stops, c["end"]):] if s >= c["end"]), None)
        end = min(nxt, c["end"] + REGION_MAX_CHARS) if nxt is not None else min(len(doc.text), c["end"] + REGION_MAX_CHARS)
        regions.append({"official": c["official"], "start": c["end"], "end": end, "cue": c["text"],
                        "cue_stamp": doc.stamp(c["start"]), "cue_pos": c["start"], "exact": c["exact"],
                        "district": c["district"],
                        "bounded": nxt is not None and nxt < c["end"] + REGION_MAX_CHARS, "kind": "cue"})
    mo = MAYOR_OPEN_RX.search(doc.text)
    if roster.mayor and mo and "MAYOR" in doc.text[max(0, mo.start() - 500):mo.start()]:
        mc = MAYOR_CLOSE_RX.search(doc.text, mo.end())
        if mc:
            regions.append({"official": roster.mayor, "start": mo.end(), "end": mc.start(),
                            "cue": "the presiding officer asks the Mayor for opening remarks",
                            "cue_stamp": doc.stamp(mo.start()), "cue_pos": mo.start(), "exact": True,
                            "district": None, "bounded": True, "kind": "mayor-opening"})
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
        why.append("the caption spells the surname in a way that is not the roster's own, or adds a word before it")
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
