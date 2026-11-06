"""The worker's lease: one row, worker_state, says which worker process may run the nightly cycle. A worker takes
the lease by writing its own name and the time, refreshes the time every few seconds while it lives, and a
second worker (a restart that overlaps its predecessor, a second copy by mistake) waits until the time is older
than the lease allows. The lease is only about the worker: the site's writes rely on SQLite's own locking.

All of it is one UPDATE, so SQLite's write lock makes taking and refreshing safe between processes.
"""

import datetime
import os
import socket
import threading
import uuid

import sqlalchemy as sa

from . import db, logs
from .tables import worker_state

TTL_S = 60.0         # a lease whose heartbeat is older than this is up for taking over
HEARTBEAT_S = 10.0   # how often the holder refreshes it


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def new_owner():
    return "%s:%d:%s" % (socket.gethostname(), os.getpid(), uuid.uuid4().hex[:6])


def acquire(owner, ttl_s=TTL_S, now=None):
    """True when `owner` now holds the lease: it was free, expired or already this owner's."""
    now = now or utcnow()
    stale = now - datetime.timedelta(seconds=ttl_s)
    with db.session() as conn:
        res = conn.execute(
            sa.update(worker_state).where(worker_state.c.id == 1).where(sa.or_(
                worker_state.c.lease_owner.is_(None), worker_state.c.lease_owner == owner,
                worker_state.c.lease_heartbeat_at.is_(None), worker_state.c.lease_heartbeat_at < stale,
            )).values(lease_owner=owner, lease_heartbeat_at=now))
        return res.rowcount == 1


def refresh(owner, now=None):
    """True when `owner` still holds the lease and its heartbeat is now fresh; False when it was taken over."""
    with db.session() as conn:
        res = conn.execute(sa.update(worker_state).where(worker_state.c.id == 1)
                           .where(worker_state.c.lease_owner == owner)
                           .values(lease_heartbeat_at=now or utcnow()))
        return res.rowcount == 1


def release(owner):
    with db.session() as conn:
        conn.execute(sa.update(worker_state).where(worker_state.c.id == 1).where(worker_state.c.lease_owner == owner)
                     .values(lease_owner=None, lease_heartbeat_at=None))


def holder(conn, now=None, ttl_s=TTL_S):
    """Who holds the lease, for the summary: {'owner', 'heartbeat_at', 'held'} (held false when expired)."""
    row = conn.execute(sa.select(worker_state.c.lease_owner, worker_state.c.lease_heartbeat_at)
                       .where(worker_state.c.id == 1)).mappings().first()
    owner, beat = (row["lease_owner"], row["lease_heartbeat_at"]) if row else (None, None)
    now = now or utcnow()
    held = bool(owner and beat and (now - beat).total_seconds() <= ttl_s)
    return {"owner": owner if held else None, "heartbeat_at": beat.isoformat(timespec="seconds") if beat else None,
            "held": held}


class Lease:
    """A worker's hold on the lease: wait() takes it (waiting while another holds it), a thread then refreshes it,
    and held() turns false when it was lost. close() gives it up."""

    def __init__(self, owner=None, ttl_s=TTL_S, heartbeat_s=HEARTBEAT_S):
        self.owner = owner or new_owner()
        self.ttl_s = ttl_s
        self.heartbeat_s = heartbeat_s
        self._held = threading.Event()
        self._stop = threading.Event()
        self._thread = None

    def held(self):
        return self._held.is_set()

    def try_acquire(self):
        if not acquire(self.owner, self.ttl_s):
            return False
        self._held.set()
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._beat, daemon=True)
            self._thread.start()
        return True

    def wait(self, poll_s=5.0):
        """Blocks until the lease is this worker's."""
        announced = False
        while not self.try_acquire():
            if not announced:
                logs.emit("info", "worker lease held by another worker; waiting", owner=self.owner)
                announced = True
            self._stop.wait(poll_s)
        logs.emit("info", "worker lease taken", owner=self.owner)

    def _beat(self):
        while not self._stop.wait(self.heartbeat_s):
            if not self._held.is_set():
                continue
            try:
                if not refresh(self.owner):
                    self._held.clear()
                    logs.emit("error", "worker lease lost to another worker", owner=self.owner)
            except Exception as exc:  # the database is busy or unreachable: try again at the next beat
                logs.emit("error", "worker lease refresh failed", owner=self.owner, error=str(exc))

    def close(self):
        self._stop.set()
        if self._held.is_set():
            self._held.clear()
            try:
                release(self.owner)
            except Exception as exc:
                logs.emit("error", "worker lease release failed", owner=self.owner, error=str(exc))
