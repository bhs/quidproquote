"""The daily fetch: new Legistar caption transcripts and the DataSF filings, one request at a time.

A run re-reads the donors' filings, looks up the city's calendar for meetings it does not hold yet, fetches each
new transcript, stores it, and looks for candidates in what is new. A source that cannot be read is recorded with
its error and the run is marked failed: nothing replaces a failed read with an empty answer, and what was stored
before stays. The last run shows on the admin status page.
"""

import datetime
import threading

from . import candidates
from . import db
from . import fmap_lib as fl
from . import legistar
from . import money

RUN_LOCK = threading.Lock()


def store_meeting(conn, meeting_id, body, date, rows, retrieved=None):
    """Keep a meeting and its caption lines (replacing any earlier copy)."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute("DELETE FROM lines WHERE meeting_id=?", (meeting_id,))
        conn.execute(
            "INSERT INTO meetings (id, body, date, url, retrieved, line_count) VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET body=excluded.body, date=excluded.date, url=excluded.url, "
            "retrieved=excluded.retrieved, line_count=excluded.line_count",
            (meeting_id, body, date, legistar.TRANSCRIPT % meeting_id, retrieved or fl.today(), len(rows)))
        conn.executemany("INSERT INTO lines (meeting_id, idx, stamp, text) VALUES (?,?,?,?)",
                         [(meeting_id, i, s, t) for i, (s, t) in enumerate(rows)])
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def record_run(conn, kind, ok, summary, error="", started=None):
    """Write a finished run to the log (used by the seed for the data it loaded from the bundled snapshot)."""
    now = db.now()
    conn.execute("INSERT INTO fetch_runs (kind, started_at, finished_at, ok, summary, error) VALUES (?,?,?,?,?,?)",
                 (kind, started or now, now, 1 if ok else 0, summary, error))


def run(conn, settings, kind="scheduled"):
    """One fetch run. Returns {ok, summary, errors}. Only one run at a time: a second call while one is running
    returns at once with ok False and says so."""
    if not RUN_LOCK.acquire(blocking=False):
        return {"ok": False, "summary": "", "errors": ["a fetch run is already in progress"]}
    started = db.now()
    cur = conn.execute("INSERT INTO fetch_runs (kind, started_at) VALUES (?, ?)", (kind, started))
    run_id = cur.lastrowid
    parts, errors = [], []
    try:
        try:
            fl.user_agent()
            parts.append("filings: " + money.refresh_money(conn))
        except (fl.QueryError, fl.ContactMissing) as exc:
            errors.append("DataSF filings not refreshed: %s" % exc)
        new_ids = []
        try:
            known = {r["id"] for r in conn.execute("SELECT id FROM meetings")}
            year = settings.get("fetch_year") or datetime.date.today().year
            _, new, notes, seen, with_t, route = legistar.discover(known, year, settings.get("fetch_max_new_meetings", 10))
            parts.append("calendar (%s): %d meeting rows, %d with a transcript, %d new to fetch" % (
                route, seen, with_t, len(new)))
            parts.extend(notes)
            for r in new:
                try:
                    rows = legistar.fetch_transcript(r["transcript_id"])
                except legistar.FetchError as exc:
                    errors.append("transcript %s (%s %s): %s" % (r["transcript_id"], r["body"], r["date"], exc))
                    continue
                store_meeting(conn, r["transcript_id"], r["body"], r["date"], rows)
                new_ids.append(r["transcript_id"])
            parts.append("%d new transcripts stored" % len(new_ids))
        except (legistar.FetchError, fl.ContactMissing) as exc:
            errors.append("Legistar calendar not read: %s" % exc)
        added = candidates.scan(conn)
        parts.append("%d new candidates in the queue" % added)
    except Exception as exc:  # recorded, then raised: an unexpected failure must not look like a quiet run
        conn.execute("UPDATE fetch_runs SET finished_at=?, ok=0, summary=?, error=? WHERE id=?",
                     (db.now(), "; ".join(parts), "%s: %s" % (type(exc).__name__, exc), run_id))
        raise
    finally:
        RUN_LOCK.release()
    conn.execute("UPDATE fetch_runs SET finished_at=?, ok=?, summary=?, error=? WHERE id=?",
                 (db.now(), 0 if errors else 1, "; ".join(parts), "; ".join(errors), run_id))
    return {"ok": not errors, "summary": "; ".join(parts), "errors": errors}
