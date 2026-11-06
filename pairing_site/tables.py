"""The eight tables of the pairing site, described once in SQLAlchemy Core, and the column types that keep
SQLite's plain storage out of the code that reads and writes them.

Dates are ISO text that reads back as datetime.date, moments are UTC text (fixed width, so it sorts in time
order) that reads back as an aware datetime, and JSON is plain TEXT encoded and decoded here: no query reaches
inside it. Booleans are 0/1 with a check.
"""

import datetime
import json

import sqlalchemy as sa
from sqlalchemy.types import TypeDecorator

MOMENT_FORMAT = "%Y-%m-%dT%H:%M:%fZ"  # SQLite's strftime form of what UtcMoment writes, to the millisecond


class IsoDate(TypeDecorator):
    """A calendar day: stored as YYYY-MM-DD, read as datetime.date. Accepts a date or an ISO string."""

    impl = sa.String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, datetime.datetime):
            return value.date().isoformat()
        if isinstance(value, datetime.date):
            return value.isoformat()
        return datetime.date.fromisoformat(str(value)[:10]).isoformat()

    def process_result_value(self, value, dialect):
        return None if value is None else datetime.date.fromisoformat(value)


class UtcMoment(TypeDecorator):
    """A moment: stored as UTC text 'YYYY-MM-DDTHH:MM:SS.mmmZ', read as an aware datetime in UTC. A naive
    datetime is taken as UTC."""

    impl = sa.String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            value = datetime.datetime.fromisoformat(value)
        if value.tzinfo is None:
            value = value.replace(tzinfo=datetime.timezone.utc)
        return value.astimezone(datetime.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    def process_result_value(self, value, dialect):
        return None if value is None else datetime.datetime.fromisoformat(value)


class JsonText(TypeDecorator):
    """JSON kept as TEXT. None is SQL NULL."""

    impl = sa.Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else json.dumps(value)

    def process_result_value(self, value, dialect):
        return None if value is None else json.loads(value)


def now():
    """The current moment as the database computes it, in the form UtcMoment stores."""
    return sa.func.strftime(MOMENT_FORMAT, "now", type_=UtcMoment)


def today():
    """The current UTC day as the database computes it."""
    return sa.func.date("now", type_=IsoDate)


NOW_DEFAULT = sa.text("(strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))")

metadata = sa.MetaData()

meetings = sa.Table(
    "meetings", metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=False),
    sa.Column("body", sa.Text, nullable=False),
    sa.Column("meeting_date", IsoDate, nullable=False),
    sa.Column("url", sa.Text, nullable=False),
    sa.Column("recording_url", sa.Text, nullable=False),
    sa.Column("retrieved", IsoDate, nullable=False),
    sa.Column("row_count", sa.Integer, nullable=False),
    sa.Column("captions", sa.Text, nullable=False),
)

donor_priorities = sa.Table(
    "donor_priorities", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("key", sa.Text, nullable=False, unique=True),
    sa.Column("family", sa.Text, nullable=False),
    sa.Column("donor", sa.Text, nullable=False),
    sa.Column("url", sa.Text, nullable=False),
    sa.Column("section", sa.Text, nullable=False, server_default=""),
    sa.Column("text", sa.Text, nullable=False),
    sa.Column("page_date", sa.Text, nullable=False, server_default=""),
    sa.Column("retrieved", IsoDate, nullable=False),
    sa.Column("kind", sa.Text, nullable=False),
    sa.Column("added_by", sa.Text, nullable=False),
    sa.Column("added_at", UtcMoment, nullable=False, server_default=NOW_DEFAULT),
    sqlite_autoincrement=True,
)

source_data = sa.Table(
    "source_data", metadata,
    sa.Column("name", sa.Text, primary_key=True),
    sa.Column("retrieved", IsoDate, nullable=False),
    sa.Column("payload", JsonText, nullable=False),
)

pairings = sa.Table(
    "pairings", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("slug", sa.Text, nullable=False, unique=True),
    sa.Column("candidate_key", sa.Text, unique=True),
    sa.Column("status", sa.Text, nullable=False),
    sa.Column("source", sa.Text, nullable=False),
    sa.Column("official", sa.Text, nullable=False),
    sa.Column("donor_key", sa.Text, nullable=False),
    sa.Column("donor_name", sa.Text, nullable=False),
    sa.Column("meeting_id", sa.Integer, nullable=False),
    sa.Column("meeting_date", IsoDate, nullable=False),
    sa.Column("first_stamp", sa.Text, nullable=False),
    sa.Column("quote_text", sa.Text, nullable=False),
    sa.Column("card", JsonText, nullable=False),
    sa.Column("ai", JsonText),
    sa.Column("recording_url", sa.Text, nullable=False),
    sa.Column("recording_checked", sa.Boolean(create_constraint=True, name="pairings_recording_checked_bool"),
              nullable=False, server_default=sa.false()),
    sa.Column("recording_checked_at", UtcMoment),
    sa.Column("published_at", IsoDate),
    sa.Column("decided_at", UtcMoment),
    sa.Column("decision_note", sa.Text, nullable=False, server_default=""),
    sa.Column("created_at", UtcMoment, nullable=False, server_default=NOW_DEFAULT),
    sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="pairings_status_check"),
    sqlite_autoincrement=True,
)
sa.Index("pairings_status_idx", pairings.c.status, pairings.c.published_at.desc())

dropped_pairs = sa.Table(
    "dropped_pairs", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("candidate_key", sa.Text, nullable=False, unique=True),
    sa.Column("official", sa.Text, nullable=False),
    sa.Column("donor_key", sa.Text, nullable=False),
    sa.Column("donor_name", sa.Text, nullable=False),
    sa.Column("meeting_id", sa.Integer, nullable=False),
    sa.Column("meeting_body", sa.Text, nullable=False),
    sa.Column("meeting_date", IsoDate, nullable=False),
    sa.Column("first_stamp", sa.Text, nullable=False),
    sa.Column("last_stamp", sa.Text, nullable=False),
    sa.Column("quote_text", sa.Text, nullable=False),
    sa.Column("priority_text", sa.Text, nullable=False),
    sa.Column("priority_url", sa.Text, nullable=False),
    sa.Column("reason_kind", sa.Text, nullable=False),
    sa.Column("reason", sa.Text, nullable=False),
    sa.Column("stage", sa.Text, nullable=False),
    sa.Column("model", sa.Text, nullable=False, server_default=""),
    sa.Column("created_at", UtcMoment, nullable=False, server_default=NOW_DEFAULT),
    sqlite_autoincrement=True,
)

audit_log = sa.Table(
    "audit_log", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("at", UtcMoment, nullable=False, server_default=NOW_DEFAULT),
    sa.Column("actor", sa.Text, nullable=False),
    sa.Column("action", sa.Text, nullable=False),
    sa.Column("pairing_id", sa.Integer),
    sa.Column("detail", sa.Text, nullable=False, server_default=""),
    sqlite_autoincrement=True,
)

progress = sa.Table(
    "progress", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("run_id", sa.Text, nullable=False),
    sa.Column("step", sa.Text, nullable=False),
    sa.Column("status", sa.Text, nullable=False),
    sa.Column("detail", sa.Text, nullable=False, server_default=""),
    sa.Column("counts", JsonText, nullable=False, server_default="{}"),
    sa.Column("started_at", UtcMoment, nullable=False, server_default=NOW_DEFAULT),
    sa.Column("finished_at", UtcMoment),
    sa.CheckConstraint("status IN ('running', 'ok', 'error', 'skipped')", name="progress_status_check"),
    sa.Index("progress_run_idx", "run_id", "id"),
    sqlite_autoincrement=True,
)

# One row, id 1. lease_owner and lease_heartbeat_at are the worker's lease: the worker that holds it refreshes
# the heartbeat, and another worker may take it over only when the heartbeat is older than the lease allows.
worker_state = sa.Table(
    "worker_state", metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=False),
    sa.Column("next_run_at", UtcMoment),
    sa.Column("last_run_id", sa.Text),
    sa.Column("last_error", sa.Text, nullable=False, server_default=""),
    sa.Column("updated_at", UtcMoment, nullable=False, server_default=NOW_DEFAULT),
    sa.Column("lease_owner", sa.Text),
    sa.Column("lease_heartbeat_at", UtcMoment),
    sa.CheckConstraint("id = 1", name="worker_state_single_row"),
)

TABLE_NAMES = tuple(t.name for t in metadata.sorted_tables)
