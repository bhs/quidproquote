"""Reported priorities and editing: the source fields, the re-check on edit, and the old row kept in the log."""

import datetime
import json
import os
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from pairing_site import app as app_module, db, priorities, seed

from helpers import temp_database

WORDS = "The Chamber supports Prop H as public transit is a critical driver of the San Francisco economy"
NEWS_FORM = {"family": "sf-chamber", "source_type": "news report", "outlet": "Example Daily", "whose_words": "reporter",
             "url": "https://example.org/report", "words": WORDS, "page_date": "2024-10-08"}


class CheckSource(unittest.TestCase):
    today = datetime.date(2026, 11, 1)

    def test_own_site_has_no_outlet_and_an_optional_date(self):
        got = priorities.check_source("own-site", "ignored", "reporter", "", self.today)
        self.assertEqual(got, {"kind": priorities.OWN_KIND, "outlet": "", "whose_words": "", "page_date": ""})

    def test_news_report_needs_outlet_whose_words_and_a_date(self):
        ok = priorities.check_source("news report", "  Example   Daily ", "donor-quoted", "2026-10", self.today)
        self.assertEqual((ok["kind"], ok["outlet"], ok["whose_words"], ok["page_date"]),
                         ("news report", "Example Daily", "donor-quoted", "2026-10"))
        for args in (("news report", "", "reporter", "2026-10-08"), ("news report", "X", "", "2026-10-08"),
                     ("news report", "X", "somebody", "2026-10-08"), ("news report", "X", "reporter", ""),
                     ("news report", "X" * 121, "reporter", "2026-10-08"), ("blog", "", "", "")):
            with self.assertRaises(priorities.PriorityError, msg=str(args)):
                priorities.check_source(*args, today=self.today)

    def test_page_dates_must_be_real_and_not_in_the_future(self):
        for bad in ("2026-13-01", "2026-02-30", "last Tuesday", "2026-10-8", "2027-01-01", "2026-11-02"):
            with self.assertRaises(priorities.PriorityError, msg=bad):
                priorities.check_page_date(bad, False, self.today)
        for good in ("2026", "2026-10", "2026-11-01", "2024-02-29"):
            self.assertEqual(priorities.check_page_date(good, False, self.today), good)


class EditFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = mock.patch.dict(os.environ, {"ADMIN_TOKEN": "tok-123", "FETCH_CONTACT_EMAIL": "maintainer@example.org"})
        cls.env.start()
        cls.dbctx = temp_database()
        cls.dbctx.__enter__()
        assert seed.run(reset=True) == 0
        cls.client = TestClient(app_module.create_app(), follow_redirects=False)
        cls.client.__enter__()
        assert cls.client.post("/login", data={"token": "tok-123", "next": "/review"}).status_code == 303

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        cls.dbctx.__exit__(None, None, None)
        cls.env.stop()

    def row(self, key):
        with db.session() as conn:
            return conn.execute("SELECT * FROM donor_priorities WHERE key = ?", (key,)).fetchone()

    def test_a_news_report_is_saved_with_its_source_fields_and_shown_apart(self):
        with _Fetching("<p>%s, helping workers.</p>" % WORDS):
            res = self.client.post("/priority", data=dict(NEWS_FORM, retrieved="1999-01-01"))
        self.assertEqual(res.status_code, 200)
        with db.session() as conn:
            row = conn.execute("SELECT * FROM donor_priorities WHERE outlet = 'Example Daily' AND added_by = 'maintainer'").fetchone()
        self.assertEqual((row["kind"], row["whose_words"], row["page_date"], row["url"]),
                         ("news report", "reporter", "2024-10-08", "https://example.org/report"))
        self.assertEqual(str(row["retrieved"]), priorities.fl.today())
        self.assertIn("News report: Example Daily", self.client.get("/priority").text)

    def test_a_news_report_without_outlet_or_with_a_bad_date_is_refused_and_not_saved(self):
        before = _count()
        with _Fetching("<p>%s</p>" % WORDS):
            no_outlet = self.client.post("/priority", data=dict(NEWS_FORM, outlet=""))
            bad_date = self.client.post("/priority", data=dict(NEWS_FORM, page_date="2026-02-31"))
            no_link = self.client.post("/priority", data=dict(NEWS_FORM, url=""))
        for res in (no_outlet, bad_date, no_link):
            self.assertEqual(res.status_code, 422)
        self.assertIn("Name the outlet", no_outlet.text)
        self.assertEqual(_count(), before)

    def test_edit_is_prefilled_rechecked_and_writes_the_old_row_to_the_log(self):
        key = "demo-report-sf-chamber"
        page = self.client.get("/priority/%s/edit" % key)
        self.assertEqual(page.status_code, 200)
        self.assertIn("Example Daily", page.text)
        self.assertIn("Superseded", page.text)  # the seed's one earlier version
        old = self.row(key)
        new_words = "Demo entry, not a real report: the outlet describes the chamber as backing transit and housing measures."
        form = dict(NEWS_FORM, words=new_words, url=old["url"])
        with _Fetching("<p>something else entirely on this page</p>"):
            refused = self.client.post("/priority/%s/edit" % key, data=form)
        self.assertEqual(refused.status_code, 422)
        self.assertEqual(self.row(key)["text"], old["text"])
        with _Fetching("<p>%s</p>" % new_words):
            done = self.client.post("/priority/%s/edit" % key, data=form)
        self.assertEqual(done.status_code, 303)
        self.assertEqual(self.row(key)["text"], new_words)
        with db.session() as conn:
            entries = conn.execute("SELECT detail FROM audit_log WHERE action = 'priority edited' "
                                   "AND json_extract(detail, '$.key') = ? ORDER BY id DESC", (key,)).fetchall()
        self.assertEqual(len(entries), 2)  # the seed's and this one
        before = json.loads(entries[0]["detail"])["before"]
        self.assertEqual((before["text"], before["url"], before["outlet"], before["kind"]),
                         (old["text"], old["url"], old["outlet"], old["kind"]))
        self.assertIn(old["text"], self.client.get("/priority/%s/edit" % key).text)
        self.assertIn("edited 2 times", self.client.get("/priority").text)

    def test_edit_of_a_missing_priority_is_404_and_needs_sign_in(self):
        self.assertEqual(self.client.get("/priority/nothing/edit").status_code, 404)
        anon = TestClient(app_module.create_app(), follow_redirects=False)
        self.assertEqual(anon.get("/priority/demo-report-sf-chamber/edit").status_code, 303)


def _count():
    with db.session() as conn:
        return conn.execute("SELECT count(*) AS n FROM donor_priorities").fetchone()["n"]


class _Fetching:
    """The priority check with the page replaced by `page` and the address check skipped."""

    def __init__(self, page):
        self.patches = [mock.patch.object(priorities, "check_public_url"),
                        mock.patch.object(priorities.fl, "fetch_page", return_value=page)]

    def __enter__(self):
        for p in self.patches:
            p.start()

    def __exit__(self, *exc):
        for p in self.patches:
            p.stop()


if __name__ == "__main__":
    unittest.main()
