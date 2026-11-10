"""The spot check: card quotes against the stored transcript, highlights on shared words only, and what the check
does to a card that fails."""

import html
import io
import os
import re
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from pairing_site import app as app_module, db, seed, spotcheck

from helpers import temp_database

import pairing_cards as pc


def esc(text):
    return html.escape(text, quote=True)


def card_quote(conn, slug):
    row = conn.execute("SELECT * FROM pairings WHERE slug = ?", (slug,)).fetchone()
    return row


class Rendering(unittest.TestCase):
    """The highlighted quote is the stored text with tags added around whole shared words, nothing else."""

    def plain(self, text, terms):
        return html.unescape(re.sub(r"</?mark>", "", pc.marked(text, terms, esc)))

    def test_text_is_unchanged_whatever_it_holds(self):
        texts = ['Prop H, "transit" & <b>housing</b>;  two  spaces\tand a tab',
                 "It\u2019s the mayor\u2014 not the \u201cboard\u201d; caf\u00e9 na\u00efve",
                 "  leading and trailing space  ", "TRANSIT Transit transit", "50% of $1,000,000.00 (2025)..."]
        for text in texts:
            for terms in ([], ["transit"], ["Prop H", "housing"], ["caf\u00e9"], ["1,000,000.00"]):
                self.assertEqual(self.plain(text, terms), text, msg=(text, terms))

    def test_only_whole_words_are_marked_and_case_is_kept(self):
        out = pc.marked("Transit, transits and TRANSIT.", ["transit"], esc)
        self.assertEqual(out, "<mark>Transit</mark>, transits and <mark>TRANSIT</mark>.")

    def test_special_characters_are_escaped_not_dropped(self):
        out = pc.marked("a <script> & b", ["b"], esc)
        self.assertEqual(out, "a &lt;script&gt; &amp; <mark>b</mark>")


class Check(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = mock.patch.dict(os.environ, {"ADMIN_TOKEN": "tok-123", "FETCH_CONTACT_EMAIL": "maintainer@example.org"})
        cls.env.start()

    @classmethod
    def tearDownClass(cls):
        cls.env.stop()

    def setUp(self):
        self.dbctx = temp_database()
        self.dbctx.__enter__()
        self.assertEqual(seed.run(reset=True), 0)

    def tearDown(self):
        self.dbctx.__exit__(None, None, None)

    def change_quote(self, slug, fn, stored=False):
        with db.session(write=True) as conn:
            row = conn.execute("SELECT * FROM pairings WHERE slug = ?", (slug,)).fetchone()
            card = row["card"]
            card["quote"]["text"] = fn(card["quote"]["text"])
            conn.execute("UPDATE pairings SET card = ?, quote_text = ? WHERE id = ?",
                         (db.json_value(card), fn(row["quote_text"]) if stored else row["quote_text"], row["id"]))

    def test_the_seeded_cards_all_pass(self):
        out = io.StringIO()
        self.assertEqual(spotcheck.run(out=out), [])
        self.assertIn("0 failed", out.getvalue())

    def test_one_changed_character_fails_each_way_it_can(self):
        edits = {"case": lambda t: t.swapcase(), "space": lambda t: t.replace(" ", "  ", 1),
                 "punctuation": lambda t: t + ".", "curly quote": lambda t: t + "\u2019",
                 "dropped letter": lambda t: t[:-1]}
        with db.session() as conn:
            row = conn.execute("SELECT * FROM pairings WHERE status = 'approved' ORDER BY id").fetchone()
        for name, fn in edits.items():
            with self.subTest(name):
                card = dict(row["card"], quote=dict(row["card"]["quote"], text=fn(row["quote_text"])))
                with db.session() as conn:
                    found = spotcheck.problems(conn, dict(row, card=card))
                self.assertTrue(found, name)
        with db.session() as conn:
            self.assertEqual(spotcheck.problems(conn, row), [])

    def test_a_quote_changed_in_both_places_still_fails_against_the_transcript(self):
        with db.session() as conn:
            slug = conn.execute("SELECT slug FROM pairings WHERE status = 'approved' ORDER BY id").fetchone()["slug"]
        self.change_quote(slug, lambda t: t.replace(" the ", " THE ", 1) if " the " in t else t + " x", stored=True)
        with db.session() as conn:
            found = spotcheck.problems(conn, card_quote(conn, slug))
        self.assertEqual(len(found), 1)
        self.assertIn("transcript", found[0])

    def test_a_highlight_not_in_the_donor_words_fails(self):
        with db.session(write=True) as conn:
            row = conn.execute("SELECT * FROM pairings WHERE status = 'approved' ORDER BY id").fetchone()
            card = row["card"]
            word = card["quote"]["text"].split()[0].strip(",.;:\"'")
            donor = " ".join(s["text"] + " " + (s["section"] or "") for s in card["donor"]["statements"])
            if re.search(r"(?<!\w)%s(?!\w)" % re.escape(word), donor, re.I):
                self.skipTest("the first word is shared")
            card["highlight"] = [word]
            conn.execute("UPDATE pairings SET card = ? WHERE id = ?", (db.json_value(card), row["id"]))
            found = spotcheck.problems(conn, conn.execute("SELECT * FROM pairings WHERE id = ?", (row["id"],)).fetchone())
        self.assertTrue(any("donor" in f for f in found))

    def test_a_failing_published_card_is_hidden_and_requeued_and_logged(self):
        with db.session() as conn:
            slug = conn.execute("SELECT slug FROM pairings WHERE status = 'approved' ORDER BY id").fetchone()["slug"]
        self.change_quote(slug, lambda t: t + " extra")
        report = io.StringIO()
        failed = spotcheck.run(out=report)
        self.assertEqual([f[0] for f in failed], [slug])
        self.assertIn("FAIL " + slug, report.getvalue())
        with db.session() as conn:
            row = card_quote(conn, slug)
            log = conn.execute("SELECT actor, action FROM audit_log WHERE pairing_id = ? ORDER BY id DESC", (row["id"],)).fetchone()
        self.assertEqual((row["status"], row["published_at"], row["recording_checked"]), ("pending", None, False))
        self.assertEqual(log["actor"], "spot check")
        client = TestClient(app_module.create_app(), follow_redirects=False)
        with client:
            self.assertEqual(client.get("/pairings/" + slug).status_code, 404)
            self.assertNotIn('id="card-%s"' % slug, client.get("/").text)

    def test_report_only_changes_nothing(self):
        with db.session() as conn:
            slug = conn.execute("SELECT slug FROM pairings WHERE status = 'approved' ORDER BY id").fetchone()["slug"]
        self.change_quote(slug, lambda t: t + " extra")
        self.assertEqual(len(spotcheck.run(requeue=False, out=io.StringIO())), 1)
        with db.session() as conn:
            self.assertEqual(card_quote(conn, slug)["status"], "approved")

    def test_approval_is_blocked_on_a_mismatch_and_nothing_is_published(self):
        with db.session() as conn:
            pid, slug = [(r["id"], r["slug"]) for r in conn.execute("SELECT id, slug FROM pairings WHERE status = 'pending'")][0]
        self.change_quote(slug, lambda t: t + " extra")
        client = TestClient(app_module.create_app(), follow_redirects=False)
        with client:
            client.post("/login", data={"token": "tok-123", "next": "/review"})
            res = client.post("/review/%d/approve" % pid, data={"recording_checked": "on"})
            self.assertEqual(res.status_code, 303)
            self.assertIn("does%20not%20match", res.headers["location"])
        with db.session() as conn:
            self.assertEqual(card_quote(conn, slug)["status"], "pending")


if __name__ == "__main__":
    unittest.main()
