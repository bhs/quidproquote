"""The site and the worker against a real Postgres (a throwaway database on the server DATABASE_URL names)."""

import json
import os
import unittest
import urllib.request
from unittest import mock

from fastapi.testclient import TestClient

from pairing_site import app as app_module, db, priorities, seed, status, worker

from helpers import temp_database

import judge as judge_mod


class SiteCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = mock.patch.dict(os.environ, {"ADMIN_TOKEN": "tok-123", "FETCH_CONTACT_EMAIL": "maintainer@example.org"})
        cls.env.start()
        cls.dbctx = temp_database()
        cls.dbctx.__enter__()
        assert seed.run(reset=True) == 0
        cls.client = TestClient(app_module.create_app(), follow_redirects=False)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        cls.dbctx.__exit__(None, None, None)
        cls.env.stop()

    def sign_in(self):
        res = self.client.post("/login", data={"token": "tok-123", "next": "/review"})
        self.assertEqual(res.status_code, 303)

    def pending_ids(self):
        with db.session() as conn:
            return [r["id"] for r in conn.execute("SELECT id FROM pairings WHERE status = 'pending' ORDER BY id")]


class Public(SiteCase):
    def test_front_page_shows_the_five_cards_with_filters(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.text.count('<article class="card"'), 5)
        for needle in ("Daniel Lurie", "Matt Dorsey", "Bilal Mahmood", "Shamann Walton", 'id="filter-official"',
                       'id="filter-donor"', "Copy link", "Meeting recording", "No cause is claimed."):
            self.assertIn(needle, res.text)

    def test_a_card_has_its_own_url(self):
        res = self.client.get("/pairings/lurie-chamber-muni")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Published", res.text)
        self.assertIn("499,000", res.text)
        self.assertIn("<mark>", res.text)
        self.assertEqual(self.client.get("/pairings/nothing-here").status_code, 404)

    def test_pending_cards_are_not_public(self):
        with db.session() as conn:
            slug = conn.execute("SELECT slug FROM pairings WHERE status = 'pending' LIMIT 1").fetchone()["slug"]
        self.assertEqual(self.client.get("/pairings/" + slug).status_code, 404)

    def test_status_is_json(self):
        res = self.client.get("/status")
        self.assertEqual(res.status_code, 200)
        self.assertIn("next_run_at", res.json())


class Admin(SiteCase):
    def test_queue_needs_sign_in(self):
        anon = TestClient(self.client.app, follow_redirects=False)
        res = anon.get("/review")
        self.assertEqual(res.status_code, 303)
        self.assertTrue(res.headers["location"].startswith("/login"))
        self.assertEqual(anon.post("/review/1/approve", data={}).status_code, 303)

    def test_wrong_token_is_refused(self):
        res = TestClient(self.client.app, follow_redirects=False).post("/login", data={"token": "nope"})
        self.assertEqual(res.status_code, 401)
        self.assertNotIn("pairing_session", res.cookies)

    def test_approve_needs_the_recording_check_and_is_logged(self):
        self.sign_in()
        pid = self.pending_ids()[0]
        hx = {"HX-Request": "true"}
        res = self.client.post("/review/%d/approve" % pid, data={}, headers=hx)
        self.assertEqual(res.status_code, 200)
        self.assertIn("Tick the recording check first", res.text)
        with db.session() as conn:
            self.assertEqual(conn.execute("SELECT status FROM pairings WHERE id = %s", (pid,)).fetchone()["status"], "pending")
        res = self.client.post("/review/%d/approve" % pid, data={"recording_checked": "on"}, headers=hx)
        self.assertEqual(res.status_code, 200)
        self.assertIn("Approved at", res.text)
        with db.session() as conn:
            row = conn.execute("SELECT status, recording_checked, published_at FROM pairings WHERE id = %s", (pid,)).fetchone()
            log = conn.execute("SELECT action, at, pairing_id FROM audit_log WHERE pairing_id = %s AND action = 'approved'", (pid,)).fetchall()
        self.assertEqual((row["status"], row["recording_checked"]), ("approved", True))
        self.assertIsNotNone(row["published_at"])
        self.assertEqual(len(log), 1)
        self.assertIsNotNone(log[0]["at"])
        again = self.client.post("/review/%d/approve" % pid, data={"recording_checked": "on"}, headers=hx)
        self.assertIn("already approved", again.text)

    def test_reject_inline_is_logged(self):
        self.sign_in()
        pid = self.pending_ids()[-1]
        res = self.client.post("/review/%d/reject" % pid, data={"note": "not the same measure"}, headers={"HX-Request": "true"})
        self.assertIn("Rejected at", res.text)
        with db.session() as conn:
            log = conn.execute("SELECT detail FROM audit_log WHERE pairing_id = %s AND action = 'rejected'", (pid,)).fetchall()
        self.assertEqual([r["detail"] for r in log], ["not the same measure"])

    def test_review_and_dropped_pages_render_for_the_maintainer(self):
        self.sign_in()
        page = self.client.get("/review")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Review queue", page.text)
        self.assertIn('id="audit-log"', page.text)
        self.assertIn("topic-only", self.client.get("/review/dropped").text)

    def test_priority_form_records_the_retrieval_date_itself(self):
        self.sign_in()
        words = "The Chamber supports Prop H as public transit is a critical driver of the San Francisco economy"
        page = "<p>%s, helping workers.</p>" % words
        with mock.patch.object(priorities, "check_public_url"), mock.patch.object(priorities.fl, "fetch_page", return_value=page):
            res = self.client.post("/priority", data={"family": "sf-chamber", "url": "https://example.org/guide",
                                                       "words": words, "retrieved": "1999-01-01"})
            bad = self.client.post("/priority", data={"family": "sf-chamber", "url": "https://example.org/guide",
                                                       "words": "Words that are not anywhere on that page at all"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("recorded as retrieved", res.text)
        self.assertEqual(bad.status_code, 422)
        with db.session() as conn:
            row = conn.execute("SELECT retrieved, text FROM donor_priorities WHERE added_by = 'maintainer'").fetchone()
        self.assertEqual(str(row["retrieved"]), priorities.fl.today())
        self.assertEqual(row["text"], words)


class Worker(SiteCase):
    def test_filter_keeps_drops_and_records_reasons(self):
        found = {}
        cfg = dict(worker.settings(), max_candidates=6)
        outcome, _, counts = worker.step_shortlist(cfg, found)
        self.assertEqual(outcome, "ok")
        self.assertTrue(found["cands"])
        verdicts = [
            {"overlap": "real", "speaker_type": "official", "stance": "agrees", "reason": "Same measure.", "model": "fake"},
            {"overlap": "loose", "speaker_type": "official", "stance": "no_position", "reason": "Only housing in general.", "model": "fake"},
            {"overlap": "real", "speaker_type": "official", "stance": "opposes", "reason": "Opposite sides of Prop J.", "model": "fake"},
        ]

        class FakeJudge:
            fatal = None

            def judge_many(self, prompts):
                return {k: dict(verdicts[i % 3]) for i, k in enumerate(prompts)}

        with mock.patch.object(worker.judge_mod, "Judge", FakeJudge):
            outcome, _, counts = worker.step_filter(cfg, found)
        self.assertEqual(outcome, "ok")
        self.assertGreater(counts["kept_for_review"], 0)
        self.assertGreater(counts["dropped"], 0)
        with db.session() as conn:
            kinds = {r["reason_kind"] for r in conn.execute("SELECT reason_kind FROM dropped_pairs WHERE stage = 'AI filter'")}
            kept = conn.execute("SELECT status, card FROM pairings WHERE source = 'worker'").fetchall()
        self.assertTrue(kinds <= {"topic-only", "opposing"} and kinds)
        self.assertTrue(all(r["status"] == "pending" and r["card"]["speaker_credit"]["doubt"] for r in kept))

    def test_a_failed_model_is_an_error_row_not_an_answer(self):
        def no_key(*a, **k):
            raise judge_mod.JudgeError("ANTHROPIC_API_KEY is not set; the AI judge cannot run")

        quick = lambda *a, **k: ("skipped", "not under test", {})
        found_cands = {"cands": [object()]}
        with mock.patch.object(worker, "step_meetings", quick), mock.patch.object(worker, "step_money", quick), \
                mock.patch.object(worker, "step_shortlist", lambda cfg, found: found.update(found_cands) or ("ok", "x", {})), \
                mock.patch.object(worker.judge_mod, "Judge", no_key):
            run_id, errors = worker.run_cycle(worker.settings())
        self.assertEqual(len(errors), 1)
        self.assertIn("ANTHROPIC_API_KEY", errors[0])
        with db.session() as conn:
            summary = status.summary(conn)
        self.assertEqual(summary["last_run"]["status"], "finished with errors")
        self.assertIn("ANTHROPIC_API_KEY", summary["last_error"])

    def test_worker_answers_200_with_a_json_summary(self):
        server = worker.serve_summary(0)
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/" % server.server_address[1], timeout=10) as res:
                self.assertEqual(res.status, 200)
                body = json.loads(res.read())
        finally:
            server.shutdown()
        for key in ("last_run", "next_run_at", "counts", "last_error", "does"):
            self.assertIn(key, body)
        self.assertGreaterEqual(body["counts"]["pairings_approved"], 5)


if __name__ == "__main__":
    unittest.main()
