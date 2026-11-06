"""The reference data the pipeline starts from, loaded from the discovery survey's files when the database
does not hold it yet: the roster of officials and their committees, the donor families and each donor's own
stated priorities (read from the donors' pages and re-checked then). Safe to run again: it fills only what is
missing and never overwrites a priority added through the site."""

import datetime
import json
import os

import sqlalchemy as sa
from sqlalchemy.dialects.sqlite import insert

from . import sources
from .tables import donor_priorities, source_data

import collect  # noqa: E402  (discovery/official-funding-map: the roster table of officials' committees)


def _load(name):
    with open(os.path.join(sources.OFM_DATA, name), encoding="utf-8") as f:
        return json.load(f)


def put_source(conn, name, payload, retrieved=None):
    stmt = insert(source_data).values(name=name, retrieved=retrieved or datetime.date.today(), payload=payload)
    conn.execute(stmt.on_conflict_do_update(
        index_elements=[source_data.c.name],
        set_={"retrieved": stmt.excluded.retrieved, "payload": stmt.excluded.payload}))


def get_sources(conn):
    return {r.name: r.payload for r in conn.execute(sa.select(source_data.c.name, source_data.c.payload))}


def ensure(conn):
    """Loads the roster, the families and the donors' statements when absent. Returns what it loaded."""
    have = set(conn.execute(sa.select(source_data.c.name)
                            .where(source_data.c.name.in_(("committees", "families")))).scalars())
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
        cur = conn.execute(insert(donor_priorities).values(
            key=s["id"], family=s["family"], donor=fams[s["family"]]["name"], url=s["url"],
            section=s.get("section") or "", text=s["text"], page_date=s.get("page_date") or "",
            retrieved=s["retrieved"], kind=s["kind"], added_by="survey").on_conflict_do_nothing(
                index_elements=[donor_priorities.c.key]))
        n += cur.rowcount
    if n:
        loaded.append("%d donor statements" % n)
    return loaded
