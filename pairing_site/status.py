"""What the worker has done and will do next, as one JSON-ready summary read from the database. The worker
serves it at /, and the site serves it at /status."""

import datetime

from . import db


def _iso(value):
    return value.isoformat(timespec="seconds") if value else None


def summary(conn, now=None):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    state = conn.execute("SELECT * FROM worker_state WHERE id = 1").fetchone() or {}
    run_id = state.get("last_run_id")
    steps = []
    if run_id:
        steps = conn.execute("SELECT step, status, detail, counts, started_at, finished_at FROM progress "
                             "WHERE run_id = ? ORDER BY id", (run_id,)).fetchall()
    running = [s for s in steps if s["status"] == "running"]
    failed = [s for s in steps if s["status"] == "error"]
    last_run = None
    if steps:
        last_run = {
            "run_id": run_id, "started_at": _iso(min(s["started_at"] for s in steps)),
            "finished_at": None if running else _iso(max(s["finished_at"] or s["started_at"] for s in steps)),
            "status": "running" if running else ("finished with errors" if failed else "finished"),
            "steps": [{"step": s["step"], "status": s["status"], "detail": s["detail"], "counts": s["counts"]}
                      for s in steps]}
    counts = {}
    for row in conn.execute("SELECT status, count(*) AS n FROM pairings GROUP BY status"):
        counts["pairings_" + row["status"]] = row["n"]
    for key, sql in (("meetings_stored", "SELECT count(*) AS n FROM meetings"),
                     ("dropped_pairs_kept_with_reasons", "SELECT count(*) AS n FROM dropped_pairs"),
                     ("donor_statements", "SELECT count(*) AS n FROM donor_priorities"),
                     ("approvals_logged", "SELECT count(*) AS n FROM audit_log")):
        counts[key] = conn.execute(sql).fetchone()["n"]
    nxt = state.get("next_run_at")
    return {
        "service": "pairing worker",
        "now": _iso(now),
        "does": ("Once a day, slowly: fetches new Board and committee transcripts from Legistar and the officials' "
                 "campaign filings from DataSF, shortlists passages that touch a donor's stated priority, asks the "
                 "AI filter to drop pairs that share only topic words or take opposing positions (kept with "
                 "reasons), publishes the rest at once labelled as not reviewed by a person, and holds low-confidence pairs "
                 "for review."),
        "last_run": last_run,
        "next_run_at": _iso(nxt),
        "next_run_in_seconds": max(0, int((nxt - now).total_seconds())) if nxt else None,
        "next": ("a run of the steps meetings, money, shortlist, filter" if nxt else "waiting for the worker to schedule its first run"),
        "last_error": state.get("last_error") or None,
        "counts": counts,
    }


def current():
    with db.session() as conn:
        return summary(conn)
