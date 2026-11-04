"""The in-process daily scheduler: a thread that wakes every minute and runs the fetch when a day has passed
since the last run. With no priority entered there is nothing to look for, so it does not fetch."""

import datetime
import logging
import threading

from . import db
from . import fetcher

log = logging.getLogger("pairing_site.scheduler")
POLL_S = 60
GRACE_S = 60  # after startup, before a first run


def last_finished(conn):
    row = conn.execute("SELECT MAX(finished_at) AS t FROM fetch_runs WHERE finished_at IS NOT NULL").fetchone()
    return row["t"]


def next_run_at(conn, interval_hours):
    """The UTC time of the next scheduled run as 'YYYY-MM-DD HH:MM:SS', 'when the first priority is entered' when
    there is nothing to look for, or 'at the next check' when no run has happened yet."""
    if conn.execute("SELECT COUNT(*) AS n FROM priorities").fetchone()["n"] == 0:
        return "when the first priority is entered"
    last = last_finished(conn)
    if last is None:
        return "at the next check"
    t = datetime.datetime.strptime(last, "%Y-%m-%d %H:%M:%S") + datetime.timedelta(hours=interval_hours)
    return t.strftime("%Y-%m-%d %H:%M:%S")


def due(conn, interval_hours):
    if conn.execute("SELECT COUNT(*) AS n FROM priorities").fetchone()["n"] == 0:
        return False
    last = last_finished(conn)
    if last is None:
        return True
    age = datetime.datetime.strptime(db.now(), "%Y-%m-%d %H:%M:%S") - datetime.datetime.strptime(last, "%Y-%m-%d %H:%M:%S")
    return age.total_seconds() >= interval_hours * 3600


class Scheduler(threading.Thread):
    def __init__(self, settings):
        super().__init__(name="daily-fetch", daemon=True)
        self.settings = settings
        self.stop_event = threading.Event()

    def run(self):
        if self.stop_event.wait(GRACE_S):
            return
        conn = db.connect(self.settings["database_path"])
        while not self.stop_event.is_set():
            try:
                if due(conn, self.settings["fetch_interval_hours"]):
                    result = fetcher.run(conn, self.settings, "scheduled")
                    log.info("scheduled fetch finished: ok=%s %s", result["ok"], result["summary"])
            except Exception:  # the run is already recorded as failed; the loop goes on to the next day
                log.exception("scheduled fetch failed")
            self.stop_event.wait(POLL_S)

    def stop(self):
        self.stop_event.set()
