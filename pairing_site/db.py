"""Postgres access: a connection per unit of work, and the migrations (the numbered SQL files beside this
module) applied in order under an advisory lock, so the site and the worker can both start safely."""

import contextlib
import os
import time

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from . import config

MIGRATIONS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrations")
LOCK_KEY = 7340211


def json_value(value):
    return Jsonb(value)


def connect(url=None):
    return psycopg.connect(url or config.database_url(), row_factory=dict_row)


@contextlib.contextmanager
def session(url=None):
    """A connection that commits when the block ends and rolls back when it raises."""
    conn = connect(url)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def wait_for_database(url=None, seconds=30):
    """Connects, retrying for a while: the database may still be starting. Raises when it never answers."""
    deadline = time.time() + seconds
    while True:
        try:
            connect(url).close()
            return
        except psycopg.OperationalError:
            if time.time() > deadline:
                raise
            time.sleep(1)


def migration_files():
    return sorted(f for f in os.listdir(MIGRATIONS) if f.endswith(".sql"))


def migrate(url=None):
    """Applies each migration file not yet recorded. Returns the names applied."""
    wait_for_database(url)
    applied = []
    with session(url) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK_KEY,))
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name text PRIMARY KEY, "
                     "applied_at timestamptz NOT NULL DEFAULT now())")
        done = {r["name"] for r in conn.execute("SELECT name FROM schema_migrations")}
        for name in migration_files():
            if name in done:
                continue
            with open(os.path.join(MIGRATIONS, name), encoding="utf-8") as f:
                conn.execute(f.read())
            conn.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (name,))
            applied.append(name)
    return applied


def audit(conn, actor, action, pairing_id=None, detail=""):
    conn.execute("INSERT INTO audit_log (actor, action, pairing_id, detail) VALUES (%s, %s, %s, %s)",
                 (actor, action, pairing_id, detail))
