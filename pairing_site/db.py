"""SQLite access: a connection per unit of work, and the migrations (the numbered SQL files beside this module)
applied in order. The site and the worker share one database file on one disk (DATABASE_PATH).

Every connection opens in WAL mode with a busy timeout, so readers never wait for the writer and two writers wait
for each other instead of failing. A session that writes is declared with write=True and starts with BEGIN
IMMEDIATE: it takes the write lock first, so its reads and writes are one atomic step (this is what an advisory
lock and SELECT ... FOR UPDATE did before) and it never fails halfway on a lock it could not upgrade to.

Rows come back as dicts. Column types decide how a value is read back (see 001_init.sql): DATE and TIMESTAMP
text become date and timezone-aware datetime values, BOOLEAN becomes a bool and JSON_TEXT is decoded from JSON.
"""

import contextlib
import datetime
import json
import os
import sqlite3
import time

from . import config

MIGRATIONS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrations")
BUSY_TIMEOUT_S = 30
WAL_TRIES = 50


# --------------------------------------------------------------------------- values in and out

def json_value(value):
    """The JSON text stored in a JSON_TEXT column. Reading decodes it again (the converter below)."""
    return json.dumps(value)


def now():
    return datetime.datetime.now(datetime.timezone.utc)


def today():
    return now().date()


def _timestamp_text(value):
    if value.tzinfo is None:
        value = value.replace(tzinfo=datetime.timezone.utc)
    return value.astimezone(datetime.timezone.utc).isoformat(timespec="milliseconds")


def _timestamp_value(raw):
    value = datetime.datetime.fromisoformat(raw.decode("ascii"))
    return value if value.tzinfo else value.replace(tzinfo=datetime.timezone.utc)


sqlite3.register_adapter(datetime.datetime, _timestamp_text)
sqlite3.register_adapter(datetime.date, datetime.date.isoformat)
sqlite3.register_converter("date", lambda raw: datetime.date.fromisoformat(raw.decode("ascii")))
sqlite3.register_converter("timestamp", _timestamp_value)
sqlite3.register_converter("boolean", lambda raw: bool(int(raw)))
sqlite3.register_converter("json_text", lambda raw: json.loads(raw.decode("utf-8")))


def _dict_row(cursor, row):
    return {col[0]: value for col, value in zip(cursor.description, row)}


# --------------------------------------------------------------------------- connections

def connect(path=None):
    """A connection to the database file, creating the file (and its folder) when it is missing. Transactions are
    explicit (session), so statements outside one commit at once."""
    path = path or config.database_path()
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    conn = sqlite3.connect(path, timeout=BUSY_TIMEOUT_S, isolation_level=None,
                           detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = _dict_row
    conn.execute("PRAGMA busy_timeout = %d" % (BUSY_TIMEOUT_S * 1000))
    for attempt in range(WAL_TRIES):  # the first switch to WAL can meet another process doing the same
        try:
            conn.execute("PRAGMA journal_mode = WAL")
            break
        except sqlite3.OperationalError:
            if attempt == WAL_TRIES - 1:
                conn.close()
                raise
            time.sleep(0.1)
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


@contextlib.contextmanager
def session(path=None, write=False):
    """A connection in one transaction that commits when the block ends and rolls back when it raises. A reader
    sees one consistent snapshot; with write=True the write lock is taken at the start."""
    conn = connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE" if write else "BEGIN")
        yield conn
        conn.commit()
    except BaseException:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()


# --------------------------------------------------------------------------- migrations

def migration_files():
    return sorted(f for f in os.listdir(MIGRATIONS) if f.endswith(".sql"))


def statements(sql):
    """The statements of a SQL script, one at a time, so a migration runs inside the caller's transaction."""
    buf = ""
    for line in sql.splitlines(keepends=True):
        buf += line
        if sqlite3.complete_statement(buf):
            yield buf
            buf = ""
    if buf.strip():
        yield buf


def migrate(path=None):
    """Creates the database file when missing and applies each migration file not yet recorded, all under the
    write lock so the site and the worker can both start at once. Returns the names applied."""
    applied = []
    with session(path, write=True) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY, applied_at TIMESTAMP "
                     "NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now')))")
        done = {r["name"] for r in conn.execute("SELECT name FROM schema_migrations")}
        for name in migration_files():
            if name in done:
                continue
            with open(os.path.join(MIGRATIONS, name), encoding="utf-8") as f:
                for statement in statements(f.read()):
                    conn.execute(statement)
            conn.execute("INSERT INTO schema_migrations (name) VALUES (?)", (name,))
            applied.append(name)
    return applied


def audit(conn, actor, action, pairing_id=None, detail=""):
    conn.execute("INSERT INTO audit_log (actor, action, pairing_id, detail) VALUES (?, ?, ?, ?)",
                 (actor, action, pairing_id, detail))
