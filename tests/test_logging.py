import contextlib
import io
import json
import os
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from pairing_site import app as app_module


def lines(buf):
    return [json.loads(x) for x in buf.getvalue().splitlines() if x.strip()]


class RequestLog(unittest.TestCase):
    def setUp(self):
        env = mock.patch.dict(os.environ, {"ADMIN_TOKEN": "t", "DATABASE_PATH": "/nonexistent/unused.db"})
        env.start()
        self.addCleanup(env.stop)
        self.app = app_module.create_app()

        @self.app.get("/boom")
        def boom():
            raise RuntimeError("the filter exploded")

        self.client = TestClient(self.app, raise_server_exceptions=False)

    def test_request_line_has_the_fields(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            res = self.client.get("/static/style.css", headers={"X-Request-Id": "abc123"})
        self.assertEqual(res.status_code, 200)
        entry = [x for x in lines(buf) if x.get("path") == "/static/style.css"][0]
        self.assertEqual((entry["request_id"], entry["method"], entry["status"]), ("abc123", "GET", 200))
        self.assertIsInstance(entry["duration_ms"], (int, float))
        for field in ("time", "level", "msg"):
            self.assertIn(field, entry)

    def test_unhandled_error_is_logged_with_request_id_and_stack(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            res = self.client.get("/boom?secret=1", headers={"X-Request-Id": "rid-9"})
        self.assertEqual(res.status_code, 500)
        out = lines(buf)
        err = [x for x in out if x["level"] == "error"][0]
        self.assertEqual(err["request_id"], "rid-9")
        self.assertEqual(err["error"], "the filter exploded")
        self.assertIn("RuntimeError", err["stack"])
        req = [x for x in out if x.get("msg") == "request"][0]
        self.assertEqual((req["request_id"], req["status"], req["path"]), ("rid-9", 500, "/boom"))

    def test_request_id_is_generated_when_absent(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            res = self.client.get("/static/app.js")
        self.assertTrue(res.headers["x-request-id"])


if __name__ == "__main__":
    unittest.main()
