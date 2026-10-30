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
REPORTED = os.path.join(DATA, "priorities_reported.json")
REPORTED_CHECK = os.path.join(DATA, "reported_check.json")


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


def plain(text):
    """Letters and digits only, lower case: a quote is found on a page whatever its spacing, quotes or dashes."""
    return re.sub(r"[^a-z0-9]", "", fl.squash(text).lower())


def check_reported():
    """Re-fetches each page behind a reported priority (data/priorities_reported.json) and records whether the
    quote is on it (data/reported_check.json). A page that cannot be fetched or does not hold the quote is
    recorded as such and the entry stays marked, never silently kept as re-read. Returns nothing: these are
    reports by others, shown with their check status."""
    with open(REPORTED, encoding="utf-8") as f:
        entries = json.load(f)["entries"]
    pages, out = {}, []
    for e in entries:
        if e["url"] not in pages:
            try:
                pages[e["url"]] = plain(fl.page_text(fl.fetch_page(e["url"])))
            except (OSError, ValueError) as exc:
                pages[e["url"]] = "ERR %s: %s" % (type(exc).__name__, exc)
        page = pages[e["url"]]
        if page.startswith("ERR "):
            status = "page not fetched (%s)" % page[4:]
        elif plain(e["quote"]) in page:
            status = "quote found on the page"
        else:
            status = "quote not found on the page as fetched"
        out.append({"id": e["id"], "checked": fl.today(), "status": status})
        print("  %s: %s" % (e["id"], status))
    with open(REPORTED_CHECK, "w", encoding="utf-8") as f:
        json.dump({"checked": fl.today(), "results": out}, f, indent=1)


if __name__ == "__main__":
    ok = collect_pages()
    check_reported()
    sys.exit(0 if ok else 1)
