"""Fills an empty database with the surveyed sources, for a demo and for trying the site:

    python -m pairing_site.seed            # refuses a database that already holds pairings
    python -m pairing_site.seed --reset    # empties the data tables first

It loads the roster, donor families and donors' own statements (reference.ensure), the campaign finance rows
and the eleven caption transcripts of the survey, the five pairings the earlier hop showed (published, with the
quote re-read word for word from the transcript and the money by committee and filing), and, from the earlier
hop's hand readings of the same transcripts, passages waiting in the review queue and pairs dropped with their
reasons. Everything is read from files under discovery/; nothing is fetched and no model is called. Never run at
startup.
"""

import collections
import datetime
import json
import os
import sys

from . import db, pipeline, priorities, reference, sources

import build_map as bm  # noqa: E402
import ff_lib as ff  # noqa: E402
import fmap_lib as fl  # noqa: E402
import pairing_cards as pc  # noqa: E402

SEED_ACTOR = "seed"
DATA_TABLES = ("audit_log", "progress", "dropped_pairs", "pairings", "donor_priorities", "meetings", "source_data")


def _ffp(name):
    with open(os.path.join(sources.FFP_DATA, name), encoding="utf-8") as f:
        return json.load(f)


def _trim(tr, p, trim):
    """The reviewer's quote boundaries applied to a passage: a copy of it cut at the words named (looked for in
    the transcript, never altered)."""
    if not trim:
        return p
    doc = tr.doc
    lo = max(p["start"] - 3000, 0)
    window = doc.text[lo:p["start"] + 2500]
    b = window.find(trim["begin_at"]) if trim.get("begin_at") else p["start"] - lo
    if b < 0:
        raise ValueError("begin_at %r not found" % trim.get("begin_at"))
    e = len(window)
    if trim.get("end_at"):
        i = window.find(trim["end_at"], b)
        if i < 0:
            raise ValueError("end_at %r not found" % trim.get("end_at"))
        e = i + len(trim["end_at"])
    text = window[b:e].strip()
    pos = lo + b
    return dict(p, text=text, first_stamp=doc.stamp(pos), last_stamp=doc.stamp(pos + len(text) - 1))


def news_statement(entry):
    """A news report of the donor survey's reported priorities, in the shape of a donor statement: its kind is
    'news report' and it names its outlet. The words are the outlet's, not the donor's own."""
    day = str(entry.get("published") or "")[:10]
    return {"id": entry["id"], "family": entry["family"], "url": entry["url"], "kind": priorities.KIND_NEWS,
            "outlet": entry["outlet"], "section": "", "page_date": day if priorities.ISO_DAY.fullmatch(day) else "",
            "retrieved": entry["retrieved"], "text": entry["quote"]}


def build():
    """Everything the seed writes, as plain data (no database)."""
    data = bm.load_all()
    snap, fams = data["snap"], data["fams"]
    snap["dataset"] = fl.DATASET_PAGE
    fam_by = {f["key"]: f for f in fams}
    today = datetime.date.today()

    meetings, transcripts = {}, {}
    for mid, m in data["meetings"].items():
        rows = fl.load_rows(sources.OFM_DATA, mid)
        meetings[mid] = {"id": mid, "body": m["body"], "meeting_date": datetime.date.fromisoformat(m["date"]),
                         "url": m["url"], "recording_url": pipeline.recording_url(mid, m["body"]),
                         "retrieved": datetime.date.fromisoformat(m["retrieved"]), "row_count": len(rows),
                         "captions": pipeline.captions_text(rows)}
        transcripts[mid] = pipeline.Transcript(meetings[mid])

    indep = bm.independent_for(data)
    pairs = bm.build_pairings(data, indep)
    for p in pairs:  # money with identical rows dropped and repeats listed, not counted
        p["money"] = pipeline.money_for_pair(snap, fams, p["pk"]["official"], p["pk"]["family"])
    cards = pc.build_cards(pairs, snap, fams)
    published = []
    shown = set()
    for p, card in zip(pairs, cards):
        mid = p["pk"]["meeting_id"]
        pipeline.extend_card(card, p, p["pk"]["speaker"]["text_support"], [[s, t] for s, t in p["cues"]],
                             meetings[mid]["recording_url"])
        shown.add((p["pk"]["official"], p["pk"]["family"], mid))
        published.append({"slug": p["pk"]["slug"], "candidate_key": None, "status": "approved", "source": "seed",
                          "official": p["pk"]["official"], "donor_key": p["pk"]["family"], "donor_name": p["family"]["name"],
                          "meeting_id": mid, "meeting_date": meetings[mid]["meeting_date"],
                          "first_stamp": p["quote"]["first_stamp"], "quote_text": p["quote"]["text"], "card": card,
                          "ai": None, "recording_url": meetings[mid]["recording_url"], "published_at": today,
                          "decision_note": "Shown by hand in the earlier hop (Pairings end to end); the wording was "
                                           "re-read from the transcript word for word, not checked against the recording."})

    subjects = {s["id"]: s for s in _ffp("subjects.json")["subjects"]}
    reported = {e["id"]: e for e in data["reported"]}
    news = {e["id"]: news_statement(e) for e in data["reported"] if e.get("tier") == "news report"}
    reviews = _ffp("reviews.json")["reviews"]
    pending, dropped, skipped = [], [], collections.Counter()
    queued = {p["slug"] for p in published}
    for r in reviews:
        mid_s, stamp, official, subject_id = r["id"].split("|")
        mid, subj = int(mid_s), subjects[subject_id]
        family = fam_by[subj["family"]]
        tr = transcripts.get(mid)
        found = None
        if tr:
            for reg in tr.regions:
                if reg["official"] != official:
                    continue
                for p in ff.candidate_passages(tr.doc, reg, subj):
                    if p["first_stamp"] == stamp:
                        found = (reg, p)
        if not found:
            skipped["passage not found again"] += 1
            continue
        reg, p = found
        doubt, why = ff.credit_tier(tr.doc, reg, p["start"])
        m = meetings[mid]
        ids = r.get("donor_statements") or subj["statements"][:2]
        if r["decision"] == "accept":
            if (official, family["key"], mid) in shown:
                skipped["already one of the five"] += 1
                continue
            if not all(i in data["prio"] or i in news for i in ids):
                skipped["donor words are a city record or league guide, not its own or a news report"] += 1
                continue
            money = ff.pair_money(snap, official, family["key"])
            if not money["tied"]:
                skipped["no money through a committee tied to the official"] += 1
                continue
            p2 = _trim(tr, p, r.get("trim"))
            sts = [dict(data["prio"].get(i) or news[i]) for i in ids]
            c = {"key": r["id"], "official": official, "family": family["key"], "meeting": m, "transcript": tr,
                 "passage": p2, "region": reg, "doubt": doubt, "why": why, "statement": sts[0], "statements": sts}
            record = {"stance": "no_position", "reason": r.get("in_common", "")}
            card, slug = pipeline.build_card(c, record, snap, fams, family, reading=(
                "Same subject, in a person's reading: " + r.get("in_common", ""), r.get("differs", "") + " (A person's reading.)"))
            if slug in queued:  # reviews of overlapping windows trimmed to the same words: one queue item
                skipped["same trimmed passage already queued"] += 1
                continue
            queued.add(slug)
            pending.append({"slug": slug, "candidate_key": r["id"], "status": "pending", "source": "seed",
                            "official": official, "donor_key": family["key"], "donor_name": family["name"],
                            "meeting_id": mid, "meeting_date": m["meeting_date"], "first_stamp": p2["first_stamp"],
                            "quote_text": p2["text"], "card": card,
                            "ai": {"source": "the earlier hop's reading of this passage (data/reviews.json)",
                                   "decision": r["decision"], "reason": r.get("in_common", "")},
                            "recording_url": m["recording_url"], "published_at": None, "decision_note": ""})
        else:
            sid = ids[0]
            st = data["prio"].get(sid) or reported.get(sid)
            if not st:
                skipped["statement missing"] += 1
                continue
            loose = r["decision"] == "loose"
            dropped.append({"candidate_key": r["id"], "official": official, "donor_key": family["key"],
                            "donor_name": family["name"], "meeting_id": mid, "meeting_body": m["body"],
                            "meeting_date": m["meeting_date"], "first_stamp": p["first_stamp"],
                            "last_stamp": p["last_stamp"], "quote_text": p["text"],
                            "priority_text": st.get("text") or st.get("quote"), "priority_url": st["url"],
                            "reason_kind": "topic-only" if loose else "not-comparable",
                            "reason": ("Shares only the broad subject, no shared measure or position: " if loose
                                       else "Words in common by chance, or not the official's words: ") + r.get("note", ""),
                            "stage": "hand reading in the earlier hop", "model": ""})
    return {"data": data, "snap": snap, "meetings": list(meetings.values()), "published": published,
            "pending": pending, "dropped": dropped, "skipped": dict(skipped),
            "news_priorities": [n for n in news.values() if n["page_date"] and n["family"] in fam_by]}


def store_snapshot(conn, snap):
    for fam, rows in snap["family_rows"].items():
        reference.put_source(conn, "family_rows:" + fam, rows, datetime.date.fromisoformat(snap["retrieved"]))
    reference.put_source(conn, "independent", snap["independent"], datetime.date.fromisoformat(snap["retrieved"]))
    reference.put_source(conn, "filers_lookup", snap["filers_lookup"], datetime.date.fromisoformat(snap["retrieved"]))
    reference.put_source(conn, "meta", {"retrieved": snap["retrieved"], "data_loaded_at": snap["data_loaded_at"]},
                         datetime.date.fromisoformat(snap["retrieved"]))


def store_news_priorities(conn, built):
    """The news reports as donor priorities with their outlet, as the priority form saves them. One of them is
    filed first with the wrong page date and then corrected through the same edit the form uses, so its
    'Earlier wording' page has a superseded version to show. Returns how many were stored."""
    fams = {f["key"]: f for f in built["data"]["fams"]}
    for n, st in enumerate(built["news_priorities"]):
        fam = fams[st["family"]]
        found = {"url": st["url"], "text": st["text"], "retrieved": st["retrieved"]}
        source = {"kind": priorities.KIND_NEWS, "outlet": st["outlet"], "page_date": st["page_date"]}
        key = "reported-" + st["id"].lower()
        if n == 0:
            first = dict(source, page_date=(datetime.date.fromisoformat(st["page_date"]) - datetime.timedelta(days=1)).isoformat())
            pid = priorities.add(conn, fam, key, found, first, SEED_ACTOR)
            priorities.update(conn, pid, found, source, SEED_ACTOR)
        else:
            priorities.add(conn, fam, key, found, source, SEED_ACTOR)
    return len(built["news_priorities"])


def insert_pairing(conn, row):
    cur = conn.execute(
        "INSERT INTO pairings (slug, candidate_key, status, source, official, donor_key, donor_name, meeting_id, "
        "meeting_date, first_stamp, quote_text, card, ai, recording_url, published_at, decided_at, decision_note) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (row["slug"], row["candidate_key"], row["status"], row["source"], row["official"], row["donor_key"],
         row["donor_name"], row["meeting_id"], row["meeting_date"], row["first_stamp"], row["quote_text"],
         db.json_value(row["card"]), db.json_value(row["ai"]) if row["ai"] is not None else None,
         row["recording_url"], row["published_at"],
         db.now() if row["status"] != "pending" else None, row["decision_note"]))
    return cur.lastrowid


def run(reset=False):
    db.migrate()
    built = build()
    with db.session(write=True) as conn:
        if conn.execute("SELECT count(*) AS n FROM pairings").fetchone()["n"]:
            if not reset:
                print("The database already holds pairings; run with --reset to empty it first.", file=sys.stderr)
                return 1
        if reset:  # ids start again from 1: nothing is AUTOINCREMENT, so an emptied table reuses its keys
            for table in DATA_TABLES:
                conn.execute("DELETE FROM " + table)
        loaded = reference.ensure(conn)
        store_snapshot(conn, built["snap"])
        news_stored = store_news_priorities(conn, built)
        for m in built["meetings"]:
            conn.execute(
                "INSERT INTO meetings (id, body, meeting_date, url, recording_url, retrieved, row_count, captions) "
                "VALUES (:id, :body, :meeting_date, :url, :recording_url, :retrieved, :row_count, "
                ":captions)", m)
        for row in built["published"]:
            pid = insert_pairing(conn, row)
            db.audit(conn, SEED_ACTOR, "published from the earlier hop's hand-shown pairings", pid,
                     "Quote re-read word for word from the transcript; not checked against the recording.")
        for row in built["pending"]:
            insert_pairing(conn, row)
        for d in built["dropped"]:
            conn.execute(
                "INSERT INTO dropped_pairs (candidate_key, official, donor_key, donor_name, meeting_id, meeting_body, "
                "meeting_date, first_stamp, last_stamp, quote_text, priority_text, priority_url, reason_kind, reason, "
                "stage, model) VALUES (:candidate_key, :official, :donor_key, :donor_name, :meeting_id, "
                ":meeting_body, :meeting_date, :first_stamp, :last_stamp, :quote_text, "
                ":priority_text, :priority_url, :reason_kind, :reason, :stage, :model) "
                "ON CONFLICT DO NOTHING", d)
    print("Seeded: %d meetings with transcripts, %d published pairings, %d pairs waiting in the review queue, "
          "%d pairs dropped with reasons; %d news-report priorities (one with an earlier wording kept); loaded %s. "
          "Left out: %s." % (
              len(built["meetings"]), len(built["published"]), len(built["pending"]), len(built["dropped"]), news_stored,
              ", ".join(loaded) or "nothing new", built["skipped"] or "nothing"))
    return 0


if __name__ == "__main__":
    sys.exit(run(reset="--reset" in sys.argv[1:]))
