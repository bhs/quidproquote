"""SQLite access through SQLAlchemy Core: one file, shared by the site and the worker (two processes on one
disk).

* WAL journal, so readers never wait for the writer and the writer never waits for readers; a 30 second busy
  timeout, so a second writer waits its turn instead of failing.
* session() is a write transaction that takes the write lock when it begins (BEGIN IMMEDIATE), so a
  read-then-write block, such as a decision on a pairing, can never find its read gone stale. reader() is a
  plain snapshot for pages that only read. Keep a session short: never fetch or call a model inside one.
* setup() creates the file's directory, the file and its tables when they are absent, and does nothing to a
  file that already has them. The site and the worker both call it at start; the write lock makes that safe.
"""

import contextlib
import os
import threading

import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.dialects.sqlite import insert

from . import config
from .tables import audit_log, metadata, worker_state

BUSY_TIMEOUT_MS = 30000

_engines = {}
_engines_lock = threading.Lock()


def _make_engine(path, begin_sql):
    engine = sa.create_engine(sa.engine.URL.create("sqlite", database=path),
                              connect_args={"timeout": BUSY_TIMEOUT_MS / 1000, "check_same_thread": False})

    @event.listens_for(engine, "connect")
    def on_connect(dbapi_conn, record):
        dbapi_conn.isolation_level = None  # the driver starts no transaction of its own; begin() below does
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA busy_timeout = %d" % BUSY_TIMEOUT_MS)  # before the journal mode: switching it locks
        cur.execute("PRAGMA journal_mode = WAL")
        cur.execute("PRAGMA synchronous = NORMAL")
        cur.close()

    @event.listens_for(engine, "begin")
    def on_begin(conn):
        conn.exec_driver_sql(begin_sql)

    return engine


def _engine(path, write):
    path = os.path.abspath(path or config.database_path())
    key = (path, write)
    with _engines_lock:
        if key not in _engines:
            _engines[key] = _make_engine(path, "BEGIN IMMEDIATE" if write else "BEGIN")
        return _engines[key]


def dispose(path=None):
    """Closes every pooled connection to the file (a test removing its file calls this first)."""
    path = os.path.abspath(path or config.database_path())
    with _engines_lock:
        for key in [k for k in _engines if k[0] == path]:
            _engines.pop(key).dispose()


@contextlib.contextmanager
def session(path=None):
    """A write transaction: the write lock is taken at once, the block commits when it ends and rolls back when
    it raises."""
    with _engine(path, True).begin() as conn:
        yield conn


@contextlib.contextmanager
def reader(path=None):
    """A read-only snapshot of the file; it never blocks, and is never blocked by, a writer."""
    with _engine(path, False).connect() as conn:
        yield conn


def setup(path=None):
    """Creates the database file and any table it lacks. Returns the names of the tables created, empty when
    the file was already complete. The single worker_state row is inserted when it is not there."""
    path = path or config.database_path()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with session(path) as conn:
        have = set(sa.inspect(conn).get_table_names())
        missing = [t for t in metadata.sorted_tables if t.name not in have]
        if missing:
            metadata.create_all(conn, tables=missing)
        conn.execute(insert(worker_state).values(id=1).on_conflict_do_nothing())
    return [t.name for t in missing]


def audit(conn, actor, action, pairing_id=None, detail=""):
    conn.execute(insert(audit_log).values(actor=actor, action=action, pairing_id=pairing_id, detail=detail))
