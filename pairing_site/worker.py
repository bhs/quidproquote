"""The nightly worker: a process that loops once a day, fetches slowly, shortlists, filters with the AI model and
writes progress rows as it goes. It also answers 200 on / with a JSON summary of what it did and does next.

    python -m pairing_site.worker            # loops; the first run is WORKER_INITIAL_DELAY_S after start
    python -m pairing_site.worker --once     # one run now, then exit

Settings (environment): DATABASE_PATH (the SQLite file the site shares), FETCH_CONTACT_EMAIL (named in the user agent of every fetch),
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
import sys
import threading
import time
import traceback
import uuid

from . import config, db, logs, money, pipeline, reference, sources, status

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
        with db.session(write=True) as conn:
            cur = conn.execute("INSERT INTO progress (run_id, step, status, detail) VALUES (?, ?, 'running', ?)",
                               (self.run_id, step, detail))
        logs.emit("info", "worker step started", run_id=self.run_id, step=step)
        return cur.lastrowid

    def finish(self, row_id, status_, detail="", counts=None):
        with db.session(write=True) as conn:
            conn.execute("UPDATE progress SET status = ?, detail = ?, counts = ?, finished_at = ? WHERE id = ?",
                         (status_, detail, db.json_value(counts or {}), db.now(), row_id))
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
    with db.session() as conn:
        known = {r["id"] for r in conn.execute("SELECT id FROM meetings")}
    _, new, notes, seen, with_t, route = lg.discover(known, cfg["year"], cfg["max_transcripts"])
    added, problems = 0, []
    for r in new:
        time.sleep(cfg["pause_s"])
        try:
            rows = lg.fetch_transcript(r["transcript_id"])
        except lg.FetchError as exc:
            problems.append("transcript %s (%s %s): %s" % (r["transcript_id"], r["body"], r["date"], exc))
            continue
        with db.session(write=True) as conn:
            conn.execute(
                "INSERT INTO meetings (id, body, meeting_date, url, recording_url, retrieved, row_count, captions) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT (id) DO NOTHING",
                (r["transcript_id"], r["body"], r["date"], pipeline.transcript_url(r["transcript_id"]),
                 pipeline.recording_url(r["transcript_id"], r["body"]), fl.today(), len(rows),
                 pipeline.captions_text(rows)))
        added += 1
    counts = {"calendar_rows": seen, "with_transcript": with_t, "already_stored": len(known), "added": added,
              "route": route}
    detail = "; ".join(notes + problems)
    return ("error" if problems else "ok"), detail, counts


def step_money(cfg):
    with db.session() as conn:
        src = reference.get_sources(conn)
        meta = conn.execute("SELECT retrieved FROM source_data WHERE name = 'meta'").fetchone()
    if meta and (db.today() - meta["retrieved"]).days < cfg["money_max_age_days"]:
        return "skipped", "campaign finance rows retrieved %s are newer than %d days" % (
            meta["retrieved"], cfg["money_max_age_days"]), {}
    pieces = {}
    counts = money.refresh(src["committees"], src["families"]["families"], cfg["pause_s"],
                           lambda name, payload: pieces.__setitem__(name, payload))
    with db.session(write=True) as conn:  # stored together, so a failed query leaves the earlier rows whole
        for name, payload in pieces.items():
            reference.put_source(conn, name, payload)
    return "ok", "campaign finance rows retrieved %s" % fl.today(), counts


def load_state():
    with db.session() as conn:
        src = reference.get_sources(conn)
        meetings = conn.execute("SELECT * FROM meetings ORDER BY meeting_date, id").fetchall()
        prios = conn.execute("SELECT * FROM donor_priorities ORDER BY id").fetchall()
        seen = {r["k"] for r in conn.execute("SELECT candidate_key AS k FROM pairings WHERE candidate_key IS NOT NULL "
                                             "UNION SELECT candidate_key FROM dropped_pairs")}
    return src, meetings, prios, seen


def step_shortlist(cfg, found):
    src, meetings, prios, seen = load_state()
    if "family_rows:sf-chamber" not in src:
        return "skipped", "no campaign finance rows stored yet, so no donor has money to pair", {}
    snap = pipeline.load_snapshot(src, src["families"])
    pairs = pipeline.funded_pairs(snap)
    transcripts = [pipeline.Transcript(m) for m in meetings]
    cands, total, capped = pipeline.shortlist(transcripts, pairs, pipeline.group_priorities(prios), seen,
                                              cfg["max_candidates"])
    found.update(cands=cands, snap=snap, fams=src["families"]["families"])
    counts = {"meetings_read": len(meetings), "funded_pairs": len(pairs), "new_candidates": total,
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
        with db.session(write=True) as conn:
            if keep:
                conn.execute(
                    "INSERT INTO pairings (slug, candidate_key, status, source, official, donor_key, donor_name, "
                    "meeting_id, meeting_date, first_stamp, quote_text, card, ai, recording_url) "
                    "VALUES (?, ?, 'pending', 'worker', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT DO NOTHING",
                    (slug, c["key"], c["official"], family["key"], family["name"], m["id"], m["meeting_date"],
                     p["first_stamp"], p["text"], db.json_value(card), db.json_value(rec), m["recording_url"]))
                counts["kept_for_review"] += 1
            else:
                conn.execute(
                    "INSERT INTO dropped_pairs (candidate_key, official, donor_key, donor_name, meeting_id, "
                    "meeting_body, meeting_date, first_stamp, last_stamp, quote_text, priority_text, priority_url, "
                    "reason_kind, reason, stage, model) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
                    "?, 'AI filter', ?) ON CONFLICT DO NOTHING",
                    (c["key"], c["official"], family["key"], family["name"], m["id"], m["body"], m["meeting_date"],
                     p["first_stamp"], p["last_stamp"], p["text"], c["statement"]["text"], c["statement"]["url"],
                     kind, reason, rec.get("model", "")))
                counts["dropped"] += 1
    if judge.fatal:
        raise judge.fatal
    if errors:
        return "error", "; ".join(errors)[:600], counts
    return "ok", "%d kept for review, %d dropped with reasons" % (counts["kept_for_review"], counts["dropped"]), counts


# --------------------------------------------------------------------------- the run and the loop

def run_cycle(cfg):
    run_id = uuid.uuid4().hex[:12]
    progress = Progress(run_id)
    with db.session(write=True) as conn:
        conn.execute("UPDATE worker_state SET last_run_id = ?, updated_at = ? WHERE id = 1", (run_id, db.now()))
        reference.ensure(conn)
    found, errors = {}, []
    plan = (("meetings", lambda: step_meetings(cfg)), ("money", lambda: step_money(cfg)),
            ("shortlist", lambda: step_shortlist(cfg, found)), ("filter", lambda: step_filter(cfg, found)))
    for name, fn in plan:
        row = progress.start(name)
        try:
            outcome, detail, counts = fn()
        except Exception as exc:  # recorded, never turned into an ordinary answer
            outcome, detail, counts = "error", "%s: %s" % (type(exc).__name__, exc), {}
            logs.emit("error", "worker step failed", run_id=run_id, step=name, error=str(exc),
                      stack=traceback.format_exc())
        if outcome == "error":
            errors.append("%s: %s" % (name, detail))
        progress.finish(row, outcome, detail, counts)
    with db.session(write=True) as conn:
        conn.execute("UPDATE worker_state SET last_error = ?, updated_at = ? WHERE id = 1",
                     ("; ".join(errors)[:1000], db.now()))
    return run_id, errors


def schedule(next_run):
    with db.session(write=True) as conn:
        conn.execute("UPDATE worker_state SET next_run_at = ?, updated_at = ? WHERE id = 1", (next_run, db.now()))


def loop(cfg):
    next_run = now() + datetime.timedelta(seconds=cfg["initial_delay_s"])
    while True:
        schedule(next_run)
        while now() < next_run:
            time.sleep(min(5.0, max(0.1, (next_run - now()).total_seconds())))
        try:
            run_id, errors = run_cycle(cfg)
            logs.emit("error" if errors else "info", "worker run finished", run_id=run_id, errors=len(errors))
        except Exception as exc:
            logs.emit("error", "worker run failed", error=str(exc), stack=traceback.format_exc())
        next_run = now() + datetime.timedelta(seconds=cfg["interval_s"])


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
    db.migrate()
    cfg = settings()
    if "--once" in argv:
        _, errors = run_cycle(cfg)
        return 1 if errors else 0
    serve_summary(config.port("WORKER_PORT" if config.optional("WORKER_PORT") else "PORT", 8080))
    loop(cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
