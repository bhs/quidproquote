"""The data layer on SQLite: a fresh file, the types read back, atomic writes and two writers on one file."""

import datetime
import os
import sqlite3
import threading
import unittest

from pairing_site import db, reference, status, worker

from helpers import temp_database

TABLES = {"meetings", "donor_priorities", "source_data", "pairings", "dropped_pairs", "audit_log", "progress",
          "worker_state", "schema_migrations"}


def pairing_row(slug, **extra):
    row = {"slug": slug, "status": "pending", "source": "test", "official": "A. Official", "donor_key": "k",
           "donor_name": "Donor", "meeting_id": 1, "meeting_date": datetime.date(2025, 3, 4), "first_stamp": "00:01:02",
           "quote_text": "words", "card": {"speaker_credit": {"doubt": "low"}}, "recording_url": "https://example.org/r"}
    row.update(extra)
    return row


def insert_pairing(conn, row):
    return conn.execute(
        "INSERT INTO pairings (slug, status, source, official, donor_key, donor_name, meeting_id, meeting_date, "
        "first_stamp, quote_text, card, recording_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (row["slug"], row["status"], row["source"], row["official"], row["donor_key"], row["donor_name"],
         row["meeting_id"], row["meeting_date"], row["first_stamp"], row["quote_text"], db.json_value(row["card"]),
         row["recording_url"])).lastrowid


class FreshFile(unittest.TestCase):
    def test_first_start_creates_the_file_and_the_schema_and_later_starts_change_nothing(self):
        with temp_database() as path:
            self.assertFalse(os.path.exists(path))
            self.assertEqual(db.migrate(), ["001_init.sql", "002_priority_versions.sql"])
            self.assertTrue(os.path.exists(path))
            self.assertEqual(db.migrate(), [])
            with db.session() as conn:
                names = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
                self.assertTrue(TABLES <= names)
                self.assertEqual([r["id"] for r in conn.execute("SELECT id FROM worker_state")], [1])
                self.assertEqual(conn.execute("PRAGMA journal_mode").fetchone()["journal_mode"], "wal")
                self.assertEqual(conn.execute("SELECT count(*) AS n FROM schema_migrations").fetchone()["n"], 2)

    def test_worker_state_holds_one_row_only(self):
        with temp_database():
            db.migrate()
            with self.assertRaises(sqlite3.IntegrityError):
                with db.session(write=True) as conn:
                    conn.execute("INSERT INTO worker_state (id) VALUES (2)")

    def test_a_missing_path_setting_fails_loudly(self):
        old = os.environ.pop("DATABASE_PATH", None)
        try:
            with self.assertRaises(RuntimeError):
                db.connect()
        finally:
            if old is not None:
                os.environ["DATABASE_PATH"] = old


class Types(unittest.TestCase):
    def test_values_read_back_as_python_types(self):
        with temp_database():
            db.migrate()
            stamp = datetime.datetime(2025, 5, 6, 7, 8, 9, 123000, tzinfo=datetime.timezone.utc)
            with db.session(write=True) as conn:
                pid = insert_pairing(conn, pairing_row("one"))
                conn.execute("UPDATE pairings SET recording_checked = 1, recording_checked_at = ?, published_at = ?, "
                             "ai = ? WHERE id = ?", (stamp, datetime.date(2025, 5, 6), db.json_value({"a": [1, 2]}), pid))
                db.audit(conn, "tester", "did", pid, "detail")
            with db.session() as conn:
                row = conn.execute("SELECT * FROM pairings WHERE id = ?", (pid,)).fetchone()
                log = conn.execute("SELECT at FROM audit_log").fetchone()
            self.assertIs(row["recording_checked"], True)
            self.assertEqual(row["recording_checked_at"], stamp)
            self.assertEqual(row["published_at"], datetime.date(2025, 5, 6))
            self.assertEqual(row["meeting_date"], datetime.date(2025, 3, 4))
            self.assertEqual(row["card"], {"speaker_credit": {"doubt": "low"}})
            self.assertEqual(row["ai"], {"a": [1, 2]})
            self.assertIsNone(row["decided_at"])
            self.assertIs(row["created_at"].tzinfo, datetime.timezone.utc)
            self.assertIs(log["at"].tzinfo, datetime.timezone.utc)

    def test_constraints_hold(self):
        with temp_database():
            db.migrate()
            with db.session(write=True) as conn:
                insert_pairing(conn, pairing_row("dup"))
            for bad in (pairing_row("dup"), pairing_row("other", status="maybe")):
                with self.assertRaises(sqlite3.IntegrityError):
                    with db.session(write=True) as conn:
                        insert_pairing(conn, bad)

    def test_upsert_replaces_a_source_and_keeps_one_row(self):
        with temp_database():
            db.migrate()
            with db.session(write=True) as conn:
                reference.put_source(conn, "meta", {"n": 1}, datetime.date(2025, 1, 1))
                reference.put_source(conn, "meta", {"n": 2}, datetime.date(2025, 2, 1))
                self.assertEqual(reference.get_sources(conn), {"meta": {"n": 2}})
                row = conn.execute("SELECT retrieved FROM source_data").fetchone()
            self.assertEqual(row["retrieved"], datetime.date(2025, 2, 1))


class Writes(unittest.TestCase):
    def test_a_failed_write_session_leaves_nothing_behind(self):
        with temp_database():
            db.migrate()
            with self.assertRaises(ValueError):
                with db.session(write=True) as conn:
                    pid = insert_pairing(conn, pairing_row("gone"))
                    db.audit(conn, "tester", "approved", pid)
                    raise ValueError("stop")
            with db.session() as conn:
                self.assertEqual(conn.execute("SELECT count(*) AS n FROM pairings").fetchone()["n"], 0)
                self.assertEqual(conn.execute("SELECT count(*) AS n FROM audit_log").fetchone()["n"], 0)

    def test_a_reader_sees_the_state_before_an_open_write_and_is_not_blocked(self):
        with temp_database():
            db.migrate()
            with db.session(write=True) as writer:
                insert_pairing(writer, pairing_row("pending-write"))
                with db.session() as reader:  # WAL: the reader does not wait for the writer
                    self.assertEqual(reader.execute("SELECT count(*) AS n FROM pairings").fetchone()["n"], 0)
            with db.session() as reader:
                self.assertEqual(reader.execute("SELECT count(*) AS n FROM pairings").fetchone()["n"], 1)

    def test_site_and_worker_write_to_one_file_at_the_same_time(self):
        with temp_database():
            db.migrate()
            with db.session(write=True) as conn:
                pid = insert_pairing(conn, pairing_row("shared"))
            errors, per_thread = [], 40

            def site():  # what the site does on a decision: read, then update and audit under one write lock
                try:
                    for i in range(per_thread):
                        with db.session(write=True) as conn:
                            conn.execute("SELECT status FROM pairings WHERE id = ?", (pid,)).fetchone()
                            conn.execute("UPDATE pairings SET decision_note = ? WHERE id = ?", (str(i), pid))
                            db.audit(conn, "site", "noted", pid, str(i))
                except Exception as exc:
                    errors.append(exc)

            def worker_side():  # what the worker does: progress rows, committed one at a time
                try:
                    progress = worker.Progress("run-1")
                    for i in range(per_thread):
                        row = progress.start("step-%d" % i)
                        progress.finish(row, "ok", "", {"i": i})
                except Exception as exc:
                    errors.append(exc)

            threads = [threading.Thread(target=f) for f in (site, site, worker_side)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            self.assertEqual(errors, [])
            with db.session() as conn:
                self.assertEqual(conn.execute("SELECT count(*) AS n FROM audit_log").fetchone()["n"], 2 * per_thread)
                self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()["integrity_check"], "ok")
                summary = status.summary(conn)
            self.assertEqual(summary["last_run"], None)  # worker_state.last_run_id is set by run_cycle, not by Progress
            with db.session() as conn:
                self.assertEqual(conn.execute("SELECT count(*) AS n FROM progress WHERE status = 'ok'").fetchone()["n"],
                                 per_thread)

    def test_two_starts_at_once_apply_the_migration_once(self):
        with temp_database():
            results, errors = [], []

            def start():
                try:
                    results.append(db.migrate())
                except Exception as exc:
                    errors.append(exc)

            threads = [threading.Thread(target=start) for _ in range(4)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            self.assertEqual(errors, [])
            self.assertEqual(sorted(results), [[], [], [], ["001_init.sql", "002_priority_versions.sql"]])


class Status(unittest.TestCase):
    def test_summary_reads_the_worker_state_and_counts(self):
        with temp_database():
            db.migrate()
            nxt = datetime.datetime(2030, 1, 1, tzinfo=datetime.timezone.utc)
            worker.schedule(nxt)
            with db.session() as conn:
                summary = status.summary(conn, now=nxt - datetime.timedelta(seconds=90))
            self.assertEqual(summary["next_run_at"], "2030-01-01T00:00:00+00:00")
            self.assertEqual(summary["next_run_in_seconds"], 90)
            self.assertEqual(summary["counts"]["meetings_stored"], 0)


if __name__ == "__main__":
    unittest.main()
