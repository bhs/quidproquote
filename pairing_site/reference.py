"""The reference data the pipeline starts from, loaded from the discovery survey's files when the database
does not hold it yet: the roster of officials and their committees, the donor families and each donor's own
stated priorities (read from the donors' pages and re-checked then). Safe to run again: it fills only what is
missing and never overwrites a priority added through the site."""

import datetime
import json
import os

from . import db, sources

import collect  # noqa: E402  (discovery/official-funding-map: the roster table of officials' committees)


def _load(name):
    with open(os.path.join(sources.OFM_DATA, name), encoding="utf-8") as f:
        return json.load(f)


def put_source(conn, name, payload, retrieved=None):
    conn.execute(
        "INSERT INTO source_data (name, retrieved, payload) VALUES (%s, %s, %s) "
        "ON CONFLICT (name) DO UPDATE SET retrieved = EXCLUDED.retrieved, payload = EXCLUDED.payload",
        (name, retrieved or datetime.date.today(), db.json_value(payload)))


def get_sources(conn):
    return {r["name"]: r["payload"] for r in conn.execute("SELECT name, payload FROM source_data")}


def ensure(conn):
    """Loads the roster, the families and the donors' statements when absent. Returns what it loaded."""
    have = {r["name"] for r in conn.execute("SELECT name FROM source_data WHERE name IN ('committees', 'families')")}
    loaded = []
    if "committees" not in have:
        seed = _load("committees_seed.json")
        put_source(conn, "committees", collect.committees_table(seed))
        loaded.append("committees")
    if "families" not in have:
        put_source(conn, "families", _load("families.json"))
        loaded.append("families")
    statements = _load("priorities.json")["statements"]
    fams = {f["key"]: f for f in _load("families.json")["families"]}
    n = 0
    for s in statements:
        cur = conn.execute(
            "INSERT INTO donor_priorities (key, family, donor, url, section, text, page_date, retrieved, kind, added_by) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'survey') ON CONFLICT (key) DO NOTHING",
            (s["id"], s["family"], fams[s["family"]]["name"], s["url"], s.get("section") or "", s["text"],
             s.get("page_date") or "", s["retrieved"], s["kind"]))
        n += cur.rowcount
    if n:
        loaded.append("%d donor statements" % n)
    return loaded
