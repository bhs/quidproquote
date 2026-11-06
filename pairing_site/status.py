"""What the worker has done and will do next, as one JSON-ready summary read from the database. The worker
serves it at /, and the site serves it at /status."""

import datetime

import sqlalchemy as sa

from . import db, lease
from .tables import audit_log, donor_priorities, dropped_pairs, meetings, pairings, progress, worker_state


def _iso(value):
    return value.isoformat(timespec="seconds") if value else None


def summary(conn, now=None):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    state = conn.execute(sa.select(worker_state).where(worker_state.c.id == 1)).mappings().first() or {}
    run_id = state.get("last_run_id")
    steps = []
    if run_id:
        steps = conn.execute(sa.select(progress.c.step, progress.c.status, progress.c.detail, progress.c.counts,
                                       progress.c.started_at, progress.c.finished_at)
                             .where(progress.c.run_id == run_id).order_by(progress.c.id)).mappings().all()
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
    for row in conn.execute(sa.select(pairings.c.status, sa.func.count().label("n")).group_by(pairings.c.status)):
        counts["pairings_" + row.status] = row.n
    for key, table in (("meetings_stored", meetings), ("dropped_pairs_kept_with_reasons", dropped_pairs),
                       ("donor_statements", donor_priorities), ("approvals_logged", audit_log)):
        counts[key] = conn.execute(sa.select(sa.func.count()).select_from(table)).scalar_one()
    nxt = state.get("next_run_at")
    return {
        "service": "pairing worker",
        "now": _iso(now),
        "does": ("Once a day, slowly: fetches new Board and committee transcripts from Legistar and the officials' "
                 "campaign filings from DataSF, shortlists passages that touch a donor's stated priority, asks the "
                 "AI filter to drop pairs that share only topic words or take opposing positions (kept with "
                 "reasons), and puts what is left in the review queue."),
        "last_run": last_run,
        "next_run_at": _iso(nxt),
        "next_run_in_seconds": max(0, int((nxt - now).total_seconds())) if nxt else None,
        "next": ("a run of the steps meetings, money, shortlist, filter" if nxt else "waiting for the worker to schedule its first run"),
        "last_error": state.get("last_error") or None,
        "lease": lease.holder(conn, now),
        "counts": counts,
    }


def current():
    with db.reader() as conn:
        return summary(conn)
