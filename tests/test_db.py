"""The data layer on SQLite: schema creation on a fresh file, the column types, the write paths, the worker lease,
and the site and the worker (two processes) on one file."""

import datetime
import os
import sqlite3
import subprocess
import sys
import threading
import unittest

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from pairing_site import db, lease, reference, status
from pairing_site.tables import (TABLE_NAMES, audit_log, donor_priorities, pairings, progress, source_data,
                                 worker_state)
from pairing_site.tables import now as db_now, today as db_today

from helpers import temp_database

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EIGHT = {"meetings", "donor_priorities", "source_data", "pairings", "dropped_pairs", "audit_log", "progress",
         "worker_state"}


def pairing_values(slug, **extra):
    values = dict(slug=slug, status="pending", source="test", official="A. Official", donor_key="k", donor_name="Donor",
                  meeting_id=1, meeting_date="2025-03-04", first_stamp="00:01:02", quote_text="words",
                  card={"title": "t", "speaker_credit": {"doubt": "low"}}, recording_url="https://example.org/r")
    values.update(extra)
    return values


class DbCase(unittest.TestCase):
    def setUp(self):
        ctx = temp_database()
        self.path = ctx.__enter__()
        self.addCleanup(ctx.__exit__, None, None, None)


class FreshFile(DbCase):
    def test_a_missing_file_gets_its_directory_file_and_eight_tables(self):
        self.assertFalse(os.path.exists(os.path.dirname(self.path)))
        self.assertEqual(set(db.setup()), EIGHT)
        self.assertEqual(set(TABLE_NAMES), EIGHT)
        self.assertTrue(os.path.isfile(self.path))
        with db.reader() as conn:
            self.assertEqual(set(sa.inspect(conn).get_table_names()) - {"sqlite_sequence"}, EIGHT)
            row = conn.execute(sa.select(worker_state)).mappings().one()
            self.assertEqual(conn.exec_driver_sql("PRAGMA journal_mode").scalar(), "wal")
            self.assertEqual(conn.exec_driver_sql("PRAGMA busy_timeout").scalar(), db.BUSY_TIMEOUT_MS)
        self.assertEqual((row["id"], row["last_error"], row["lease_owner"], row["next_run_at"]), (1, "", None, None))

    def test_setup_is_idempotent_and_keeps_data(self):
        db.setup()
        with db.session() as conn:
            conn.execute(sa.update(worker_state).values(last_error="kept"))
            db.audit(conn, "tester", "did something")
        self.assertEqual(db.setup(), [])
        with db.reader() as conn:
            self.assertEqual(conn.execute(sa.select(worker_state.c.last_error)).scalar_one(), "kept")
            self.assertEqual(conn.execute(sa.select(sa.func.count()).select_from(audit_log)).scalar_one(), 1)
            self.assertEqual(conn.execute(sa.select(sa.func.count()).select_from(worker_state)).scalar_one(), 1)

    def test_a_file_missing_one_table_gets_only_that_table(self):
        db.setup()
        db.dispose()
        raw = sqlite3.connect(self.path)
        raw.execute("DROP TABLE progress")
        raw.commit()
        raw.close()
        self.assertEqual(db.setup(), ["progress"])

    def test_constraints_are_in_the_file(self):
        db.setup()
        with self.assertRaises(IntegrityError):
            with db.session() as conn:
                conn.execute(sa.insert(pairings).values(**pairing_values("bad", status="maybe")))
        with self.assertRaises(IntegrityError):
            with db.session() as conn:
                conn.execute(sa.insert(worker_state).values(id=2))
        with db.session() as conn:
            conn.execute(sa.insert(pairings).values(**pairing_values("one", candidate_key=None)))
            conn.execute(sa.insert(pairings).values(**pairing_values("two", candidate_key=None)))  # NULLs never clash
        with self.assertRaises(IntegrityError):
            with db.session() as conn:
                conn.execute(sa.insert(pairings).values(**pairing_values("one")))
        with db.reader() as conn:
            names = set(conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type = 'index'")).scalars())
        self.assertTrue({"pairings_status_idx", "progress_run_idx"} <= names)


class ColumnTypes(DbCase):
    def setUp(self):
        super().setUp()
        db.setup()

    def test_json_dates_moments_and_booleans_round_trip(self):
        moment = datetime.datetime(2025, 6, 1, 12, 30, 15, 250000, tzinfo=datetime.timezone.utc)
        with db.session() as conn:
            conn.execute(sa.insert(pairings).values(**pairing_values("a", card={"money": [499000.0, 2], "k": "é"},
                                                                     ai=None, decided_at=moment,
                                                                     published_at=datetime.date(2025, 6, 2))))
        with db.reader() as conn:
            row = conn.execute(sa.select(pairings).where(pairings.c.slug == "a")).mappings().one()
            raw = conn.execute(sa.text("SELECT card, meeting_date, decided_at, recording_checked FROM pairings")).one()
        self.assertEqual(row["card"], {"money": [499000.0, 2], "k": "é"})
        self.assertIsNone(row["ai"])
        self.assertEqual(row["meeting_date"], datetime.date(2025, 3, 4))  # an ISO string in, a date out
        self.assertEqual(row["published_at"], datetime.date(2025, 6, 2))
        self.assertEqual(row["decided_at"], moment)
        self.assertIs(row["recording_checked"], False)
        self.assertEqual(raw[1], "2025-03-04")
        self.assertEqual(raw[2], "2025-06-01T12:30:15.250Z")
        self.assertIsInstance(raw[0], str)  # JSON is plain text in the file

    def test_database_defaults_and_functions_read_back_as_aware_utc(self):
        with db.session() as conn:
            db.audit(conn, "tester", "acted")
            conn.execute(sa.insert(pairings).values(**pairing_values("b")))
            conn.execute(sa.update(pairings).values(decided_at=db_now(), published_at=db_today()))
        with db.reader() as conn:
            at = conn.execute(sa.select(audit_log.c.at)).scalar_one()
            row = conn.execute(sa.select(pairings.c.created_at, pairings.c.decided_at, pairings.c.published_at)).one()
        now = datetime.datetime.now(datetime.timezone.utc)
        for value in (at, row.created_at, row.decided_at):
            self.assertEqual(value.utcoffset(), datetime.timedelta(0))
            self.assertLess(abs((now - value).total_seconds()), 60)
        self.assertEqual(row.published_at, now.date())

    def test_upsert_replaces_a_source_and_donor_statements_are_added_once(self):
        with db.session() as conn:
            reference.put_source(conn, "meta", {"v": 1}, datetime.date(2025, 1, 1))
            reference.put_source(conn, "meta", {"v": 2}, datetime.date(2025, 2, 2))
        with db.reader() as conn:
            rows = conn.execute(sa.select(source_data)).mappings().all()
        self.assertEqual([(r["name"], r["payload"], r["retrieved"]) for r in rows],
                         [("meta", {"v": 2}, datetime.date(2025, 2, 2))])
        with db.session() as conn:
            first = reference.ensure(conn)
        with db.session() as conn:
            second = reference.ensure(conn)
        self.assertTrue(any("donor statements" in x for x in first))
        self.assertEqual(second, [])
        with db.reader() as conn:
            self.assertGreater(conn.execute(sa.select(sa.func.count()).select_from(donor_priorities)).scalar_one(), 0)


class Lease(DbCase):
    def setUp(self):
        super().setUp()
        db.setup()

    def test_one_holder_at_a_time_until_the_heartbeat_goes_stale(self):
        t0 = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)
        self.assertTrue(lease.acquire("first", ttl_s=60, now=t0))
        self.assertTrue(lease.acquire("first", ttl_s=60, now=t0 + datetime.timedelta(seconds=5)))
        self.assertFalse(lease.acquire("second", ttl_s=60, now=t0 + datetime.timedelta(seconds=30)))
        self.assertTrue(lease.refresh("first", now=t0 + datetime.timedelta(seconds=40)))
        self.assertFalse(lease.acquire("second", ttl_s=60, now=t0 + datetime.timedelta(seconds=90)))
        self.assertTrue(lease.acquire("second", ttl_s=60, now=t0 + datetime.timedelta(seconds=101)))
        self.assertFalse(lease.refresh("first", now=t0 + datetime.timedelta(seconds=102)))  # taken over

    def test_release_frees_it_and_the_summary_names_the_holder(self):
        self.assertTrue(lease.acquire("w1"))
        with db.reader() as conn:
            held = lease.holder(conn)
            self.assertEqual((held["owner"], held["held"]), ("w1", True))
            self.assertEqual(status.summary(conn)["lease"]["owner"], "w1")
        lease.release("w1")
        self.assertTrue(lease.acquire("w2"))

    def test_lease_object_takes_holds_and_gives_up(self):
        mine = lease.Lease(owner="mine", heartbeat_s=0.05)
        other = lease.Lease(owner="other", heartbeat_s=0.05)
        self.addCleanup(mine.close)
        self.addCleanup(other.close)
        self.assertTrue(mine.try_acquire())
        self.assertFalse(other.try_acquire())
        mine.close()
        self.assertFalse(mine.held())
        self.assertTrue(other.try_acquire())


class OneFileTwoProcesses(DbCase):
    def setUp(self):
        super().setUp()
        db.setup()

    def test_overlapping_read_then_write_sessions_do_not_lose_updates(self):
        with db.session() as conn:
            reference.put_source(conn, "counter", {"n": 0})
        errors = []

        def bump():
            try:
                for _ in range(5):
                    with db.session() as conn:
                        n = conn.execute(sa.select(source_data.c.payload).where(source_data.c.name == "counter")).scalar_one()["n"]
                        conn.execute(sa.update(source_data).where(source_data.c.name == "counter").values(payload={"n": n + 1}))
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=bump) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        with db.reader() as conn:
            self.assertEqual(conn.execute(sa.select(source_data.c.payload)).scalar_one(), {"n": 30})

    def test_a_second_process_writes_while_this_one_writes_and_reads(self):
        code = ("from pairing_site import db\n"
                "import sqlalchemy as sa\n"
                "db.setup()\n"
                "for i in range(40):\n"
                "    with db.session() as conn:\n"
                "        db.audit(conn, 'worker-process', 'step %d' % i)\n")
        proc = subprocess.Popen([sys.executable, "-c", code], cwd=ROOT, env=dict(os.environ),
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for i in range(40):
            with db.session() as conn:
                conn.execute(sa.insert(progress).values(run_id="r", step="s%d" % i, status="ok"))
            self.assertIn("pairing worker", status.current()["service"])  # a reader is never blocked
        out, _ = proc.communicate(timeout=120)
        self.assertEqual(proc.returncode, 0, out)
        with db.reader() as conn:
            self.assertEqual(conn.execute(sa.select(sa.func.count()).select_from(audit_log)
                                          .where(audit_log.c.actor == "worker-process")).scalar_one(), 40)
            self.assertEqual(conn.execute(sa.select(sa.func.count()).select_from(progress)).scalar_one(), 40)
            self.assertEqual(conn.exec_driver_sql("PRAGMA integrity_check").scalar(), "ok")


if __name__ == "__main__":
    unittest.main()
