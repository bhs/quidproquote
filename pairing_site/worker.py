"""The nightly worker: a process that loops once a day, fetches slowly, shortlists, filters with the AI model and
writes progress rows as it goes. It also answers 200 on / with a JSON summary of what it did and does next.

    python -m pairing_site.worker            # loops; the first run is WORKER_INITIAL_DELAY_S after start
    python -m pairing_site.worker --once     # one run now, then exit

Only one worker runs the cycle at a time: it takes the lease kept in the worker_state row (see lease.py), refreshes
it while it lives, and a second worker waits (still answering on its port) until the first lets it go or stops
refreshing. The site shares the same SQLite file and needs no lease.

Settings (environment): DATABASE_PATH, FETCH_CONTACT_EMAIL (named in the user agent of every fetch),
ANTHROPIC_API_KEY and MATCH_JUDGE_MODEL (the filter; see judge.py), DATASF_APP_TOKEN (optional),
WORKER_INTERVAL_S (default 86400), WORKER_INITIAL_DELAY_S (default 60), WORKER_PAUSE_S (seconds between fetches,
default 5), WORKER_MAX_TRANSCRIPTS (new transcripts per run, default 3), WORKER_MAX_CANDIDATES (pairs sent to the
model per run, default 40), WORKER_MONEY_MAX_AGE_DAYS (default 7), WORKER_YEAR, PORT (the summary, default 8080).

A step that fails is recorded as an error row, kept in the summary as the last error and logged; the steps after
it still run on what is stored. A failed model call is never turned into an answer: its pairs stay undecided
and are tried again on the next run.
"""

import datetime
import http.server
import json
import signal
import sys
import threading
import time
import traceback
import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.sqlite import insert

from . import config, db, lease as lease_mod, logs, money, pipeline, reference, sources, status
from .tables import donor_priorities, dropped_pairs, meetings, now as db_now, pairings, progress, source_data, worker_state

import fmap_lib as fl  # noqa: E402
import judge as judge_mod  # noqa: E402
import legistar as lg  # noqa: E402


def now():
    return datetime.datetime.now(datetime.timezone.utc)


class Progress:
    """Progress rows, each committed at once so the summary shows a step while it runs."""

    def __init__(self, run_id):
        self.run_id = run_id

    def start(self, step, detail=""):
        with db.session() as conn:
            row_id = conn.execute(sa.insert(progress).values(run_id=self.run_id, step=step, status="running",
                                                             detail=detail)).inserted_primary_key[0]
        logs.emit("info", "worker step started", run_id=self.run_id, step=step)
        return row_id

    def finish(self, row_id, status_, detail="", counts=None):
        with db.session() as conn:
            conn.execute(sa.update(progress).where(progress.c.id == row_id).values(
                status=status_, detail=detail, counts=counts or {}, finished_at=db_now()))
        logs.emit("error" if status_ == "error" else "info", "worker step finished", run_id=self.run_id,
                  status=status_, detail=detail[:300], counts=counts or {})


def settings():
    return {
        "interval_s": config.number("WORKER_INTERVAL_S", 86400),
        "initial_delay_s": config.number("WORKER_INITIAL_DELAY_S", 60),
        "pause_s": config.number("WORKER_PAUSE_S", 5),
        "max_transcripts": int(config.number("WORKER_MAX_TRANSCRIPTS", 3)),
        "max_candidates": int(config.number("WORKER_MAX_CANDIDATES", 40)),
        "money_max_age_days": config.number("WORKER_MONEY_MAX_AGE_DAYS", 7),
        "year": int(config.number("WORKER_YEAR", datetime.date.today().year)),
    }


# --------------------------------------------------------------------------- steps

def step_meetings(cfg):
    """New transcripts from the Legistar calendar, a few per run, with a pause between fetches."""
    with db.reader() as conn:
        known = set(conn.execute(sa.select(meetings.c.id)).scalars())
    _, new, notes, seen, with_t, route = lg.discover(known, cfg["year"], cfg["max_transcripts"])
    added, problems = 0, []
    for r in new:
        time.sleep(cfg["pause_s"])
        try:
            rows = lg.fetch_transcript(r["transcript_id"])
        except lg.FetchError as exc:
            problems.append("transcript %s (%s %s): %s" % (r["transcript_id"], r["body"], r["date"], exc))
            continue
        with db.session() as conn:
            conn.execute(insert(meetings).values(
                id=r["transcript_id"], body=r["body"], meeting_date=r["date"],
                url=pipeline.transcript_url(r["transcript_id"]),
                recording_url=pipeline.recording_url(r["transcript_id"], r["body"]), retrieved=fl.today(),
                row_count=len(rows), captions=pipeline.captions_text(rows)).on_conflict_do_nothing())
        added += 1
    counts = {"calendar_rows": seen, "with_transcript": with_t, "already_stored": len(known), "added": added,
              "route": route}
    detail = "; ".join(notes + problems)
    return ("error" if problems else "ok"), detail, counts


def step_money(cfg):
    with db.reader() as conn:
        src = reference.get_sources(conn)
        retrieved = conn.execute(sa.select(source_data.c.retrieved).where(source_data.c.name == "meta")).scalar_one_or_none()
    if retrieved and (datetime.date.today() - retrieved).days < cfg["money_max_age_days"]:
        return "skipped", "campaign finance rows retrieved %s are newer than %d days" % (
            retrieved, cfg["money_max_age_days"]), {}
    pieces = {}
    counts = money.refresh(src["committees"], src["families"]["families"], cfg["pause_s"],
                           lambda name, payload: pieces.__setitem__(name, payload))
    with db.session() as conn:  # stored together, so a failed query leaves the earlier rows whole
        for name, payload in pieces.items():
            reference.put_source(conn, name, payload)
    return "ok", "campaign finance rows retrieved %s" % fl.today(), counts


def load_state():
    with db.reader() as conn:
        src = reference.get_sources(conn)
        stored = conn.execute(sa.select(meetings).order_by(meetings.c.meeting_date, meetings.c.id)).mappings().all()
        prios = conn.execute(sa.select(donor_priorities).order_by(donor_priorities.c.id)).mappings().all()
        seen = set(conn.execute(sa.union(
            sa.select(pairings.c.candidate_key).where(pairings.c.candidate_key.is_not(None)),
            sa.select(dropped_pairs.c.candidate_key))).scalars())
    return src, stored, prios, seen


def step_shortlist(cfg, found):
    src, stored, prios, seen = load_state()
    if "family_rows:sf-chamber" not in src:
        return "skipped", "no campaign finance rows stored yet, so no donor has money to pair", {}
    snap = pipeline.load_snapshot(src, src["families"])
    pairs = pipeline.funded_pairs(snap)
    transcripts = [pipeline.Transcript(m) for m in stored]
    cands, total, capped = pipeline.shortlist(transcripts, pairs, pipeline.group_priorities(prios), seen,
                                              cfg["max_candidates"])
    found.update(cands=cands, snap=snap, fams=src["families"]["families"])
    counts = {"meetings_read": len(stored), "funded_pairs": len(pairs), "new_candidates": total,
              "sent_to_filter": len(cands), "left_for_next_run": total - len(cands) if capped else 0}
    return "ok", "%d new passages hit a donor's stated priority" % total, counts


def step_filter(cfg, found):
    cands = found.get("cands") or []
    if not cands:
        return "skipped", "no new passages to filter", {}
    judge = judge_mod.Judge()  # raises JudgeError without ANTHROPIC_API_KEY
    fams = {f["key"]: f for f in found["fams"]}
    prompts = {c["key"]: pipeline.prompt_for(c, fams[c["family"]]["name"]) for c in cands}
    records = judge.judge_many(prompts)
    counts = {"judged": 0, "kept_for_review": 0, "dropped": 0, "undecided_errors": 0}
    errors = []
    for c in cands:
        rec = records[c["key"]]
        if "error" in rec:
            counts["undecided_errors"] += 1
            errors.append("%s: %s" % (c["key"], rec["error"]))
            continue
        counts["judged"] += 1
        keep, kind, reason = pipeline.decide(rec)
        family = fams[c["family"]]
        m, p = c["meeting"], c["passage"]
        card = slug = None
        if keep:
            try:
                card, slug = pipeline.build_card(c, rec, found["snap"], found["fams"], family)
            except ValueError as exc:  # a quote that is not word for word, a highlight not in both: not published
                counts["judged"] -= 1
                counts["undecided_errors"] += 1
                errors.append("%s: %s" % (c["key"], exc))
                continue
        with db.session() as conn:
            if keep:
                conn.execute(insert(pairings).values(
                    slug=slug, candidate_key=c["key"], status="pending", source="worker", official=c["official"],
                    donor_key=family["key"], donor_name=family["name"], meeting_id=m["id"],
                    meeting_date=m["meeting_date"], first_stamp=p["first_stamp"], quote_text=p["text"], card=card,
                    ai=rec, recording_url=m["recording_url"]).on_conflict_do_nothing())
                counts["kept_for_review"] += 1
            else:
                conn.execute(insert(dropped_pairs).values(
                    candidate_key=c["key"], official=c["official"], donor_key=family["key"], donor_name=family["name"],
                    meeting_id=m["id"], meeting_body=m["body"], meeting_date=m["meeting_date"],
                    first_stamp=p["first_stamp"], last_stamp=p["last_stamp"], quote_text=p["text"],
                    priority_text=c["statement"]["text"], priority_url=c["statement"]["url"], reason_kind=kind,
                    reason=reason, stage="AI filter", model=rec.get("model", "")).on_conflict_do_nothing())
                counts["dropped"] += 1
    if judge.fatal:
        raise judge.fatal
    if errors:
        return "error", "; ".join(errors)[:600], counts
    return "ok", "%d kept for review, %d dropped with reasons" % (counts["kept_for_review"], counts["dropped"]), counts


# --------------------------------------------------------------------------- the run and the loop

def run_cycle(cfg, lease=None):
    """One run of the steps. With a lease, the run stops between steps once the lease has been lost: another
    worker may be running by then."""
    run_id = uuid.uuid4().hex[:12]
    prog = Progress(run_id)
    with db.session() as conn:
        conn.execute(sa.update(worker_state).where(worker_state.c.id == 1).values(last_run_id=run_id, updated_at=db_now()))
        reference.ensure(conn)
    found, errors = {}, []
    plan = (("meetings", lambda: step_meetings(cfg)), ("money", lambda: step_money(cfg)),
            ("shortlist", lambda: step_shortlist(cfg, found)), ("filter", lambda: step_filter(cfg, found)))
    for name, fn in plan:
        if lease and not lease.held():
            errors.append("%s: not run, the worker lease was lost to another worker" % name)
            break
        row = prog.start(name)
        try:
            outcome, detail, counts = fn()
        except Exception as exc:  # recorded, never turned into an ordinary answer
            outcome, detail, counts = "error", "%s: %s" % (type(exc).__name__, exc), {}
            logs.emit("error", "worker step failed", run_id=run_id, step=name, error=str(exc),
                      stack=traceback.format_exc())
        if outcome == "error":
            errors.append("%s: %s" % (name, detail))
        prog.finish(row, outcome, detail, counts)
    with db.session() as conn:
        conn.execute(sa.update(worker_state).where(worker_state.c.id == 1).values(
            last_error="; ".join(errors)[:1000], updated_at=db_now()))
    return run_id, errors


def schedule(next_run):
    with db.session() as conn:
        conn.execute(sa.update(worker_state).where(worker_state.c.id == 1).values(next_run_at=next_run,
                                                                                  updated_at=db_now()))


def loop(cfg, lease):
    """Waits for the lease, then runs once the schedule says so, again every interval. A worker that loses the
    lease goes back to waiting for it and plans its next run afresh."""
    next_run = None
    while True:
        if not lease.held():
            lease.wait()
            next_run = None
        if next_run is None:
            next_run = now() + datetime.timedelta(seconds=cfg["initial_delay_s"])
            schedule(next_run)
        while now() < next_run and lease.held():
            time.sleep(min(5.0, max(0.1, (next_run - now()).total_seconds())))
        if not lease.held():
            continue
        try:
            run_id, errors = run_cycle(cfg, lease)
            logs.emit("error" if errors else "info", "worker run finished", run_id=run_id, errors=len(errors))
        except Exception as exc:
            logs.emit("error", "worker run failed", error=str(exc), stack=traceback.format_exc())
        next_run = now() + datetime.timedelta(seconds=cfg["interval_s"])
        schedule(next_run)


# --------------------------------------------------------------------------- the summary on /

class SummaryHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        t0 = time.perf_counter()
        rid = logs.new_request_id(self.headers.get("X-Request-Id"))
        path = self.path.split("?", 1)[0]
        if path == "/":
            try:
                body, code = status.current(), 200
            except Exception as exc:  # the process is alive; the summary says the database is not answering
                logs.emit("error", "summary failed", request_id=rid, error=str(exc), stack=traceback.format_exc())
                body, code = {"service": "pairing worker", "database_error": str(exc)}, 200
        else:
            body, code = {"error": "not found"}, 404
        data = json.dumps(body, indent=1, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Request-Id", rid)
        self.end_headers()
        self.wfile.write(data)
        logs.emit("info", "request", request_id=rid, method="GET", path=path, status=code,
                  duration_ms=round((time.perf_counter() - t0) * 1000, 2))

    def log_message(self, *args):  # the request line above replaces the default access log
        pass


def serve_summary(port):
    server = http.server.ThreadingHTTPServer(("0.0.0.0", port), SummaryHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    sources.identify_fetcher(config.fetch_contact_email())
    db.setup()
    cfg = settings()
    lease = lease_mod.Lease()
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))  # so the lease is given up when the container stops
    try:
        if "--once" in argv:
            if not lease.try_acquire():
                logs.emit("error", "another worker holds the lease; no run started", owner=lease.owner)
                return 1
            _, errors = run_cycle(cfg, lease)
            return 1 if errors else 0
        serve_summary(config.port("WORKER_PORT" if config.optional("WORKER_PORT") else "PORT", 8080))
        loop(cfg, lease)
        return 0
    finally:
        lease.close()


if __name__ == "__main__":
    sys.exit(main())
