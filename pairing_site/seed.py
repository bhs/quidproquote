"""Fills an empty database with the five pairings the Pairings end to end hop showed, through the same code a
maintainer's clicks reach:

    python -m pairing_site.seed

It loads the donors, the filings the earlier work retrieved (2026-10-30), the eleven caption transcripts and the
donors' own words with their sources, finds the candidates with candidates.scan, and then approves the five
whose remarks the hop showed (seed_data/approvals.json), with the quote's edges, the doubt level and the reading
notes. Every other candidate the finder proposes stays in the queue. Never run at startup.
"""

import json
import os
import sys

from . import candidates
from . import config
from . import db
from . import fetcher
from . import fmap_lib as fl
from . import money
from . import review

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = os.path.join(HERE, "seed_data")

# What a maintainer would enter beside each statement: the distinctive phrases to look for, read from the
# donor's own words and the subject they speak to. Measures (Prop H...) are read from the words themselves.
PHRASES = {
    "CHAMBER-H": ["parcel tax", "Muni operations", "Muni", "SFMTA"],
    "POA-I-TIMING": ["first responder*"],
    "POA-I-WONG": ["police staffing"],
    "POA-I-C": ["Housing Trust Fund", "inclusionary", "budget"],
    "GFC-J": ["transfer tax", "foreclosure*", "real estate market"],
    "GFC-C": ["Housing Trust Fund", "inclusionary"],
    "SEIU-D": ["signature threshold", "ballot measure process"],
    "SEIU-E": ["City Administrator*", "charter reform"],
    "SEIU-F": ["charter reform", "executive branch"],
}


def jload(*parts):
    with open(os.path.join(SEED, *parts), encoding="utf-8") as f:
        return json.load(f)


def load_donors(conn):
    for fam in jload("families.json")["families"]:
        conn.execute("INSERT INTO donors (key, name, kind, patterns, exclude, committee_ids, link_note) VALUES (?,?,?,?,?,?,?)",
                     (fam["key"], fam["name"], fam["kind"], json.dumps(fam["patterns"]),
                      json.dumps(fam.get("exclude", [])), json.dumps(fam.get("committee_ids", [])), fam.get("link_note", "")))


def load_money(conn):
    snap = jload("money.json")
    n = 0
    for d in conn.execute("SELECT * FROM donors ORDER BY id").fetchall():
        n += money.replace_contributions(conn, d, snap["family_rows"].get(d["key"], []))
    outside = money.replace_outside(conn, snap["independent"])
    money.replace_filer_records(conn, {fid: recs[0]["filer_name"] for fid, recs in snap["filers_lookup"].items() if recs})
    db.set_meta(conn, "money_retrieved", snap["retrieved"])
    db.set_meta(conn, "money_loaded_through", snap["data_loaded_at"])
    return n, outside


def load_meetings(conn):
    meetings = jload("meetings.json")
    for m in meetings:
        rows = []
        with open(os.path.join(SEED, "transcripts", "%d.tsv" % m["id"]), encoding="utf-8") as f:
            for line in f:
                stamp, _, text = line.rstrip("\n").partition("\t")
                rows.append((stamp, " ".join(text.split())))
        fetcher.store_meeting(conn, m["id"], m["body"], m["date"], rows, retrieved=m["retrieved"])
    return len(meetings)


def load_priorities(conn):
    """The donors' own words, entered through review.save_priority (so the same refusals apply)."""
    donors = {d["key"]: d["id"] for d in conn.execute("SELECT id, key FROM donors")}
    ids = {}
    for s in jload("priorities.json")["statements"]:
        if s["id"] not in PHRASES:
            continue
        ids[s["id"]] = review.save_priority(conn, {
            "donor_id": donors[s["family"]], "label": s["id"], "section": s["section"], "words": s["text"],
            "source_type": s["kind"], "url": s["url"], "page_date": s["page_date"], "retrieved": s["retrieved"],
            "phrases": "\n".join(PHRASES[s["id"]])}, scan=False)
    return ids


def approve_shown(conn, priority_ids):
    """Approve the candidate holding each remark the hop showed."""
    approved = []
    for a in jload("approvals.json")["approvals"]:
        donor = conn.execute("SELECT id FROM donors WHERE key=?", (a["donor"],)).fetchone()
        official = conn.execute("SELECT id FROM officials WHERE name=?", (a["official"],)).fetchone()
        doc = candidates.load_doc(conn, a["meeting_id"])
        cands = conn.execute("SELECT * FROM candidates WHERE donor_id=? AND official_id=? AND meeting_id=? AND status='pending' "
                             "ORDER BY start_off", (donor["id"], official["id"], a["meeting_id"])).fetchall()
        for c in cands:
            try:
                review.cut_quote(doc, c, a["begin_at"], a["end_at"])
            except ValueError:
                continue
            slug = review.approve(conn, c["id"], {
                "begin_at": a["begin_at"], "end_at": a["end_at"], "doubt": a["doubt"], "doubt_note": a["doubt_note"],
                "in_common": a["in_common"], "differs": a["differs"],
                "statements": [priority_ids[p] for p in a["priorities"]]})
            approved.append(slug)
            break
        else:
            raise RuntimeError("no candidate holds the remark of pairing %s (%s)" % (a["id"], a["official"]))
    return approved


def main():
    settings = config.load()
    conn = db.init(settings["database_path"])
    if conn.execute("SELECT COUNT(*) AS n FROM donors").fetchone()["n"]:
        print("The database already holds donors; the seed fills an empty one. Nothing written.")
        return 1
    load_donors(conn)
    rows, outside = load_money(conn)
    meetings = load_meetings(conn)
    ids = load_priorities(conn)
    found = candidates.scan(conn)
    approved = approve_shown(conn, ids)
    fetcher.record_run(conn, "seed", True, "loaded the snapshot retrieved %s: %d filing rows, %d outside-spending groups, "
                       "%d transcripts" % (db.get_meta(conn, "money_retrieved"), rows, outside, meetings))
    pending = conn.execute("SELECT COUNT(*) AS n FROM candidates WHERE status='pending'").fetchone()["n"]
    n_donors = conn.execute("SELECT COUNT(*) AS n FROM donors").fetchone()["n"]
    print("Seeded %d donors, %d priorities, %d transcripts (%d caption lines), %d filing rows and %d outside-spending groups."
          % (n_donors, len(ids), meetings, conn.execute("SELECT COUNT(*) AS n FROM lines").fetchone()["n"], rows, outside))
    print("The finder proposed %d candidates; %d approved as cards (%s) and %d wait in the queue."
          % (found, len(approved), ", ".join(approved), pending))
    return 0


if __name__ == "__main__":
    sys.exit(main())
