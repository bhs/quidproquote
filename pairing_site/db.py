"""The SQLite file that keeps every record: connection, migrations and the bundled roster."""

import datetime
import json
import os
import sqlite3

from . import fmap_lib as fl

HERE = os.path.dirname(os.path.abspath(__file__))
MIGRATIONS = os.path.join(HERE, "migrations")
ROSTER = os.path.join(HERE, "data", "roster.json")


def connect(path):
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path, timeout=15, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=15000")
    return conn


def migrate(conn):
    """Apply every migrations/NNNN_*.sql not yet applied, in order, each in one transaction."""
    conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
    done = {r["name"] for r in conn.execute("SELECT name FROM schema_migrations")}
    for name in sorted(n for n in os.listdir(MIGRATIONS) if n.endswith(".sql")):
        if name in done:
            continue
        with open(os.path.join(MIGRATIONS, name), encoding="utf-8") as f:
            script = f.read()
        conn.execute("BEGIN IMMEDIATE")
        try:
            for stmt in split_statements(script):
                conn.execute(stmt)
            conn.execute("INSERT INTO schema_migrations (name, applied_at) VALUES (?, ?)", (name, now()))
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise


def split_statements(script):
    """The statements of a script with '--' comments removed (the migrations hold no semicolons in strings)."""
    lines = [ln.split("--", 1)[0] for ln in script.splitlines()]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


def load_roster(conn):
    """Insert or refresh the Mayor, the supervisors and the committees tied to each, from the bundled roster."""
    with open(ROSTER, encoding="utf-8") as f:
        roster = json.load(f)
    conn.execute("BEGIN IMMEDIATE")
    try:
        for o in roster["officials"]:
            conn.execute(
                "INSERT INTO officials (name, office, district, surname, given, exact_spellings, garbled_spellings) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(name) DO UPDATE SET office=excluded.office, "
                "district=excluded.district, surname=excluded.surname, given=excluded.given, "
                "exact_spellings=excluded.exact_spellings, garbled_spellings=excluded.garbled_spellings",
                (o["name"], o["office"], o["district"], o["surname"], o["given"], json.dumps(o["exact"]),
                 json.dumps(o["garbled"])))
            oid = conn.execute("SELECT id FROM officials WHERE name=?", (o["name"],)).fetchone()["id"]
            for c in o["committees"]:
                rel, words = fl.relation_of(c)
                conn.execute(
                    "INSERT INTO committees (filer_nid, official_id, filer_name, filer_type, status, fppc_id, relation, "
                    "relation_words) VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(filer_nid) DO UPDATE SET "
                    "official_id=excluded.official_id, filer_name=excluded.filer_name, filer_type=excluded.filer_type, "
                    "status=excluded.status, fppc_id=excluded.fppc_id, relation=excluded.relation, "
                    "relation_words=excluded.relation_words",
                    (c["filer_nid"], oid, c["filer_name"], c["filer_type"], c["status"], c.get("fppc_id", ""), rel, words))
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def init(path):
    """Open the database at `path`, bring its schema up to date and load the roster. Returns the connection."""
    conn = connect(path)
    migrate(conn)
    load_roster(conn)
    return conn


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def jl(text):
    return json.loads(text) if text else []


def get_meta(conn, key, default=""):
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_meta(conn, key, value):
    conn.execute("INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                 (key, value))


def roster_for_cues(conn):
    """The officials as the turn finder reads them."""
    return [{"name": r["name"], "surname": r["surname"], "district": r["district"], "office": r["office"],
             "exact": jl(r["exact_spellings"]), "garbled": jl(r["garbled_spellings"])}
            for r in conn.execute("SELECT * FROM officials ORDER BY id")]
