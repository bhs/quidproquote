"""Speaker proposals from the chair's spoken cue, matched to the roster by spelling.

Copied from discovery/matching-methods-comparison/compare_lib.py (the speaker-proposal section; the scorers,
caption-error injection and measures of the comparison were left out). The scoring of a spelling against the
roster is now its own function, `match_roster`, so the site's turn finder can use it for a cue whose spelling
is not one it has seen. Always a proposal, never a record. Standard library only.
"""

import difflib
import re

_CUE = re.compile(r"\b(?:DISTRICT\s+(\w+)\s+)?(SUPERVISOR|MAYOR|CHAIR|SUPERVISORS)\s+([A-Z]{3,})\b")
_DISTRICT_WORDS = {"ONE": "1", "TWO": "2", "THREE": "3", "FOUR": "4", "FIVE": "5", "SIX": "6", "SEVEN": "7",
                   "EIGHT": "8", "NINE": "9", "TEN": "10", "ELEVEN": "11"}
_NOT_NAMES = {"THANK", "THANKS", "THE", "WILL", "PLEASE", "AND", "FOR", "THAT", "THIS", "WHO", "HAS", "HAVE",
              "COMMISSION", "COMMITTEE", "SORRY", "MADAM", "CLERK", "MISTER", "CHAIR", "PRESIDENT", "SUPERVISOR", "SUPERVISORS"}


def match_roster(word, roster):
    """(official, ratio, runner-up ratio) for a surname as the captions spell it, by spelling similarity to the
    roster's surnames; official is None below 0.7. roster: [{'name', 'surname', 'district', 'office'}]."""
    scored = sorted(((difflib.SequenceMatcher(None, word.upper(), o["surname"].upper()).ratio(), o) for o in roster),
                    key=lambda t: -t[0])
    if not scored:
        return None, 0.0, 0.0
    best, official = scored[0]
    second = scored[1][0] if len(scored) > 1 else 0.0
    return (official if best >= 0.7 else None), best, second


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
    official, best, second = match_roster(word, roster)
    if official is None:
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
