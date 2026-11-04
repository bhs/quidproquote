import base64
import contextlib
import io
import json
import unittest

from pairing_site import config, review
from pairing_site.app import create_app

from . import support

AUTH = {"Authorization": "Basic " + base64.b64encode(b"admin:secret-pw").decode()}


def log_lines(text):
    out = []
    for ln in text.splitlines():
        try:
            out.append(json.loads(ln))
        except ValueError:
            pass
    return out


class Site(unittest.TestCase):
    def setUp(self):
        self.env = support.make_env()
        self.conn, self.ids = support.make_db(self.env)
        self.app = create_app(config.load(self.env), start_scheduler=False)
        self.client = self.app.test_client()
        self.cand = self.conn.execute("SELECT * FROM candidates").fetchone()

    def test_the_front_page_answers_200_and_publishes_nothing_before_approval(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"No pairings are published yet", r.data)
        line = [x for x in log_lines(buf.getvalue()) if x.get("path") == "/"][0]
        self.assertEqual(line["status"], 200)
        self.assertEqual(line["method"], "GET")
        self.assertTrue(line["request_id"])
        self.assertIsInstance(line["duration_ms"], (int, float))
        self.assertIn("msg", line)
        self.assertIn("level", line)
        self.assertIn("time", line)

    def test_an_incoming_request_id_is_kept(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            r = self.client.get("/", headers={"X-Request-Id": "req-123"})
        self.assertEqual(r.headers["X-Request-Id"], "req-123")
        self.assertEqual(log_lines(buf.getvalue())[0]["request_id"], "req-123")

    def test_admin_pages_need_the_password(self):
        for path in ("/admin", "/admin/queue", "/admin/priorities", "/admin/priorities/new", "/admin/candidates/1"):
            r = self.client.get(path)
            self.assertEqual(r.status_code, 401, path)
            self.assertIn("Basic", r.headers["WWW-Authenticate"])
            bad = self.client.get(path, headers={"Authorization": "Basic " + base64.b64encode(b"admin:wrong").decode()})
            self.assertEqual(bad.status_code, 401, path)
            self.assertEqual(self.client.get(path, headers=AUTH).status_code, 200, path)
        self.assertEqual(self.client.post("/admin/fetch").status_code, 401)
        self.assertEqual(self.client.post("/admin/candidates/1/approve").status_code, 401)

    def test_a_post_from_another_origin_is_refused(self):
        r = self.client.post("/admin/candidates/%d/reject" % self.cand["id"], headers=dict(AUTH, Origin="https://evil.example"))
        self.assertEqual(r.status_code, 403)

    def test_the_queue_shows_the_exact_caption_lines_with_context(self):
        html = self.client.get("/admin/queue", headers=AUTH).data.decode()
        self.assertIn("00:00:12", html)
        self.assertIn("<mark>PARCEL TAX</mark>", html)
        self.assertIn("SPEAKER-CREDIT DOUBT: LOW", html)
        self.assertIn("00:00:09", html)  # a context line before the flagged rows

    def test_approving_in_the_queue_publishes_a_card_on_its_own_url(self):
        r = self.client.post("/admin/candidates/%d/approve" % self.cand["id"], headers=AUTH,
                             data={"doubt": "medium", "begin_at": "THE PARCEL TAX FOR MUNI", "end_at": "WHY IT MATTERS.",
                                   "statements": [str(self.ids["priority"])]})
        self.assertEqual(r.status_code, 303)
        slug = self.conn.execute("SELECT slug FROM candidates").fetchone()["slug"]
        front = self.client.get("/").data.decode()
        self.assertIn("/pairings/%s" % slug, front)
        page = self.client.get("/pairings/%s" % slug).data.decode()
        self.assertIn("THE <mark>PARCEL TAX</mark> FOR <mark>MUNI</mark> OPERATIONS AND WHY IT MATTERS.", page)
        for expected in ("SPEAKER-CREDIT DOUBT: MEDIUM",
                         "Reading, not a finding.", "No cause is claimed.", "$750", "Matt Dorsey for Supervisor 2022",
                         "never summed across committees", "retrieved 2026-10-01", "https://example.org/voter-guide",
                         "not counted", "<mark>"):
            self.assertIn(expected, page, expected)
        self.assertEqual(self.client.get("/pairings/none-such").status_code, 404)

    def test_an_approval_that_is_refused_says_why_and_publishes_nothing(self):
        r = self.client.post("/admin/candidates/%d/approve" % self.cand["id"], headers=AUTH,
                             data={"begin_at": "WORDS THAT ARE NOT THERE"})
        self.assertEqual(r.status_code, 400)
        self.assertIn(b"Not saved", r.data)
        self.assertNotIn(b"/pairings/", self.client.get("/").data)

    def test_the_priority_form_refuses_a_missing_url(self):
        r = self.client.post("/admin/priorities/new", headers=AUTH, data=support.priority_form(self.ids["donor"], url=""))
        self.assertEqual(r.status_code, 400)
        self.assertIn(b"source URL is required", r.data)

    def test_the_priority_form_saves_and_lists_the_priority(self):
        r = self.client.post("/admin/priorities/new", headers=AUTH,
                             data=support.priority_form(self.ids["donor"], label="SECOND", phrases="weekend ridership"))
        self.assertEqual(r.status_code, 303)
        self.assertIn(b"weekend ridership", self.client.get("/admin/priorities", headers=AUTH).data)

    def test_the_status_page_shows_the_last_run(self):
        from pairing_site import fetcher
        fetcher.record_run(self.conn, "seed", True, "loaded the bundled snapshot")
        html = self.client.get("/admin", headers=AUTH).data.decode()
        self.assertIn("loaded the bundled snapshot", html)
        self.assertIn("maintainer@example.org", html)
        self.assertIn("Fetch now", html)

    def test_an_unhandled_error_is_logged_with_its_request_id_and_stack(self):
        @self.app.get("/boom")
        def boom():
            raise RuntimeError("deliberate failure")

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            r = self.client.get("/boom", headers={"X-Request-Id": "req-boom"})
        self.assertEqual(r.status_code, 500)
        lines = log_lines(buf.getvalue())
        err = [x for x in lines if x.get("level") == "error" and x.get("error")][0]
        self.assertEqual(err["request_id"], "req-boom")
        self.assertEqual(err["error"], "deliberate failure")
        self.assertIn("RuntimeError", err["stack"])
        self.assertIn("Traceback", err["stack"])
        access = [x for x in lines if x.get("path") == "/boom" and "status" in x][0]
        self.assertEqual(access["status"], 500)
        self.assertEqual(access["request_id"], "req-boom")


class Settings(unittest.TestCase):
    def test_a_missing_setting_stops_startup(self):
        env = support.make_env()
        del env["ADMIN_PASSWORD"]
        with self.assertRaises(config.ConfigError) as cm:
            config.load(env)
        self.assertIn("ADMIN_PASSWORD", str(cm.exception))

    def test_fetching_without_a_contact_email_fails_loudly(self):
        import os
        from pairing_site import fmap_lib
        old = os.environ.pop("FETCH_CONTACT_EMAIL", None)
        try:
            with self.assertRaises(fmap_lib.ContactMissing):
                fmap_lib.user_agent()
            os.environ["FETCH_CONTACT_EMAIL"] = "maintainer@example.org"
            self.assertIn("maintainer@example.org", fmap_lib.user_agent())
        finally:
            if old is None:
                os.environ.pop("FETCH_CONTACT_EMAIL", None)
            else:
                os.environ["FETCH_CONTACT_EMAIL"] = old


if __name__ == "__main__":
    unittest.main()
