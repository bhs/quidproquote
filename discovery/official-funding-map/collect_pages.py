"""Fetches the donors' own pages and writes the statements the pairings quote (data/priorities.json).

A statement is a line of a page, taken exactly as the page shows it (typographic quotes and dashes
straightened). The run refuses to write one it cannot find on the page as fetched today: a donor's page can
change, and a quotation that is no longer there must not be shown as current.
"""

import json
import os
import re
import sys

import fmap_lib as fl

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(DATA, "priorities.json")


def first_sentences(line, n):
    parts = re.split(r"(?<=[.!?])\s+", line.strip())
    return " ".join(parts[:n])


def collect_pages():
    """True when every statement was found; the file is written either way, with what was found."""
    with open(os.path.join(DATA, "priority_sources.json"), encoding="utf-8") as f:
        sources = json.load(f)["pages"]
    retrieved = fl.today()
    out, missing = [], []
    for page in sources:
        try:
            lines = fl.page_lines(fl.fetch_page(page["url"]))
        except OSError as exc:
            for st in page["statements"]:
                missing.append("%s: page not fetched (%s: %s)" % (st["id"], type(exc).__name__, exc))
            continue
        for st in page["statements"]:
            start = fl.squash(st["starts"])
            line = next((ln for ln in lines if ln.startswith(start)), None)
            if line is None:
                missing.append("%s: no line starting %r on %s" % (st["id"], st["starts"], page["url"]))
                continue
            out.append({"id": st["id"], "family": page["family"], "url": page["url"], "kind": page["kind"],
                        "section": st["section"], "page_date": page["page_date"], "retrieved": retrieved,
                        "text": first_sentences(line, st["sentences"])})
            print("  %s: %d words" % (st["id"], len(out[-1]["text"].split())))
    if missing and os.path.exists(OUT):
        # keep the statements read earlier for what could not be re-read, marked as not re-read today
        with open(OUT, encoding="utf-8") as f:
            old = {s["id"]: s for s in json.load(f)["statements"]}
        have = {s["id"] for s in out}
        for m in missing:
            sid = m.split(":")[0]
            if sid in old and sid not in have:
                kept = dict(old[sid])
                kept["not_reread"] = True
                out.append(kept)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"retrieved": retrieved, "statements": out, "missing": missing}, f, indent=1)
    for m in missing:
        print("NOT FOUND: " + m, file=sys.stderr)
    return not missing


if __name__ == "__main__":
    sys.exit(0 if collect_pages() else 1)
