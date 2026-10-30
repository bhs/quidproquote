"""Take the snapshot the matching trial runs on.

Run (needs network):  python collect.py

Fetches caption transcripts of San Francisco Board of Supervisors meetings from
Legistar, and the priority statements that donors publish on their own sites,
and writes them under data/. analyze.py reads only data/, so the trial can be
re-run on the same snapshot without a network.

  data/meetings.json            which meetings, with body and date
  data/transcripts/<id>.tsv     one caption row per line: HH:MM:SS <tab> text
  data/priorities.json          donor priority statements with their page URL
"""

import html
import json
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
UA = "Mozilla/5.0 (compatible; matching-trial-run research script)"
RETRIEVED = time.strftime("%Y-%m-%d", time.gmtime())

LEGISTAR = "https://sfgov.legistar.com/Transcript.aspx?ID1=%d"
MEETINGS = [
    (51452, "Board of Supervisors", "2026-01-06"),
    (52251, "Board of Supervisors", "2026-04-21"),
    (52800, "Board of Supervisors", "2026-07-07"),
    (52849, "Board of Supervisors", "2026-07-14"),
    (52901, "Board of Supervisors", "2026-07-21"),
    (52804, "Budget and Finance Committee", "2026-07-08"),
    (52816, "Public Safety and Neighborhood Services Committee", "2026-07-09"),
    (52831, "Rules Committee", "2026-07-13"),
    (52838, "Land Use and Transportation Committee", "2026-07-13"),
    (52853, "Budget and Finance Committee", "2026-07-15"),
    (52871, "Government Audit and Oversight Committee", "2026-07-16"),
]

GROWSF = "https://growsf.org/voter-guide/san-francisco-voter-guide-november-2026-election/measures/prop-%s/"
# GrowSF's endorsed side of each November 2026 city measure (its hub page).
GROWSF_SIDE = {"a": "Yes", "b": "No", "c": "Yes", "d": "Yes", "e": "Yes",
               "f": "Yes", "g": "No", "h": "Yes", "i": "No", "j": "Yes"}

MAX_WORDS = 90


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception:
            if attempt == 2:
                raise
            time.sleep(3 * (attempt + 1))


def page_lines(raw):
    raw = re.sub(r"<(script|style|noscript|svg|nav|footer|header)\b.*?</\1>", "", raw,
                 flags=re.S | re.I)
    raw = re.sub(r"</(p|div|li|h[1-6]|tr|section|article)>|<br\s*/?>", "\n", raw, flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", "", raw))
    return [re.sub(r"\s+", " ", ln).strip() for ln in text.split("\n") if ln.strip()]


def transcript_rows(raw):
    rows = re.findall(r"(\d\d:\d\d:\d\d)\s*</[^>]+>\s*(?:<[^>]+>\s*)*([^<]+)", raw)
    return [(stamp, re.sub(r"\s+", " ", html.unescape(t)).strip()) for stamp, t in rows]


def clip(text, max_words=MAX_WORDS):
    """Keep whole sentences up to max_words; never cut a sentence in the middle."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    out, n = [], 0
    for s in sentences:
        w = len(s.split())
        if out and n + w > max_words:
            break
        out.append(s)
        n += w
    return " ".join(out)


def unit(donor, url, kind, section, text, page_date=None):
    return {"donor": donor, "url": url, "kind": kind, "section": section,
            "text": clip(text), "page_date": page_date, "retrieved": RETRIEVED}


def chamber_agenda():
    url = "https://sfchamber.com/agenda/"
    lines = page_lines(fetch(url))
    start = lines.index("Legislative Agenda")
    end = next(i for i, ln in enumerate(lines) if ln.startswith("Manage Cookie"))
    lines = lines[start + 1:end]
    out, section, i = [], "", 0
    while i < len(lines):
        ln = lines[i]
        if ln == "See Action":
            i += 1
            continue
        if ln.endswith("Expand") and i + 1 < len(lines):
            out.append(unit("San Francisco Chamber of Commerce", url, "agenda page", section,
                            ln[:-len("Expand")] + " " + lines[i + 1][0].lower() + lines[i + 1][1:]))
            i += 2
            continue
        if len(ln.split()) >= 9:
            out.append(unit("San Francisco Chamber of Commerce", url, "agenda page", section, ln))
        else:
            section = ln
        i += 1
    return out


def chamber_voter_guide():
    url = "https://sfchamber.com/november-2026-voter-guide/"
    lines = page_lines(fetch(url))
    out, section = [], ""
    for ln in lines:
        if re.match(r"(Proposition|Regional Transit Measure)", ln) and len(ln.split()) < 18:
            section = ln
        elif section and len(ln.split()) >= 25 and "Chamber" in ln:
            out.append(unit("San Francisco Chamber of Commerce", url, "voter guide", section, ln,
                            "2026-10-08"))
            section = ""
    return out


def blueprint():
    out = []
    url = "https://www.sfblueprint.org"
    lines = page_lines(fetch(url))
    for title in ("Road to Recovery", "Good Government", "Vision of Vibrancy"):
        j = lines.index(title)
        out.append(unit("Neighbors for a Better San Francisco (Blueprint)", url, "issue page",
                        title, title + ". " + lines[j + 1]))
    k = lines.index("What We\u2019re About") + 1
    out.append(unit("Neighbors for a Better San Francisco (Blueprint)", url, "about page",
                    "What We're About", lines[k]))
    url = "https://sfblueprint.org/advocacy/november-2026-voter-guide"
    lines = page_lines(fetch(url))
    section = ""
    for ln in lines:
        if re.match(r"Prop [A-J] ", ln):
            section = ln
        elif section and re.match(r"We (recommend voting|are neutral)", ln):
            out.append(unit("Neighbors for a Better San Francisco (Blueprint)", url, "voter guide",
                            section, ln, "2026-10"))
            section = ""
    return out


def growsf():
    out = []
    url = "https://growsf.org/voter-guide/"
    lines = page_lines(fetch(url))
    i = lines.index("We love San Francisco. So we\u2019re fighting for it.")
    for ln in lines[i + 1:i + 5]:
        out.append(unit("GrowSF", url, "priorities (voter guide hub)", "What we fight for", ln,
                        "2026-10-22"))
    for p, side in GROWSF_SIDE.items():
        url = GROWSF % p
        lines = page_lines(fetch(url))
        title = next(ln for ln in lines if ln.startswith("San Francisco Proposition"))
        title = title.split(" | ")[0].replace("San Francisco ", "")
        start = lines.index("Why vote %s?" % side)
        end = next(j for j in range(start + 1, len(lines)) if lines[j].startswith("Read the full"))
        for ln in lines[start + 1:end]:
            # "Claim:" lines quote the measure's backers, so they are not GrowSF's own words
            if len(ln.split()) >= 12 and not ln.lower().startswith(("vote ", "claim:")):
                out.append(unit("GrowSF", url, "voter guide (%s)" % side, title, ln, "2026-09-24"))
    return out


def seiu():
    url = "https://www.seiu1021.org/issues-legislation"
    lines = page_lines(fetch(url))
    out = []
    for i, ln in enumerate(lines):
        m = re.match(r"Article (\w+ \d+, \d{4})$", ln)
        if not m:
            continue
        title = lines[i + 1]
        body = []
        for nxt in lines[i + 2:]:
            if nxt == "Read more":
                break
            body.append(nxt)
        text = title + ". " + " ".join(body)
        out.append(unit("SEIU Local 1021", url, "issues article", title, text, m.group(1)))
    return out


def sfpoa():
    url = "https://sfpoa.org/"
    lines = page_lines(fetch(url))
    out = []
    i = next(i for i, ln in enumerate(lines) if ln.startswith("The SFPOA focuses on"))
    out.append(unit("San Francisco Police Officers Association", url, "about page", "Mission",
                    lines[i]))
    for j, ln in enumerate(lines):
        if ln.startswith(("SFPOA Urges", "Mayor Lurie Joined")):
            teaser = lines[j + 1].split("... read more")[0]
            teaser = re.sub(r"^By Louis Wong,?\s*(SFPOA\s+)?(President,?\s*)?(San Francisco Police Officers Association\s*)?", "", teaser)
            out.append(unit("San Francisco Police Officers Association", url, "own-voice article",
                            ln, ln + ". " + teaser, lines[j + 2]))
    return out


def airbnb():
    url = "https://news.airbnb.com/an-update-about-our-community-in-san-francisco"
    lines = page_lines(fetch(url))
    out = []
    for ln in lines:
        if ln.startswith(("The establishment of clear", "We are appreciative of the City")):
            out.append(unit("Airbnb", url, "newsroom post", "An Update About Our Community in San Francisco",
                            ln, "2019-02-24"))
    return out


def snapshot_transcripts():
    os.makedirs(os.path.join(DATA, "transcripts"), exist_ok=True)
    meetings = []
    for mid, body, date in MEETINGS:
        rows = transcript_rows(fetch(LEGISTAR % mid))
        if not rows:
            raise SystemExit("no caption rows for transcript %d" % mid)
        with open(os.path.join(DATA, "transcripts", "%d.tsv" % mid), "w", encoding="utf-8") as f:
            for stamp, text in rows:
                f.write("%s\t%s\n" % (stamp, text))
        meetings.append({"id": mid, "body": body, "date": date, "rows": len(rows),
                         "url": LEGISTAR % mid, "retrieved": RETRIEVED})
        print("transcript %d: %d rows" % (mid, len(rows)))
    with open(os.path.join(DATA, "meetings.json"), "w", encoding="utf-8") as f:
        json.dump(meetings, f, indent=1)


def snapshot_priorities():
    units = []
    for fn in (chamber_agenda, chamber_voter_guide, blueprint, growsf, seiu, sfpoa, airbnb):
        got = fn()
        print("%s: %d statements" % (fn.__name__, len(got)))
        units.extend(got)
    for n, u in enumerate(units, 1):
        u["id"] = "P%03d" % n
    with open(os.path.join(DATA, "priorities.json"), "w", encoding="utf-8") as f:
        json.dump(units, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    os.makedirs(DATA, exist_ok=True)
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("all", "transcripts"):
        snapshot_transcripts()
    if what in ("all", "priorities"):
        snapshot_priorities()
