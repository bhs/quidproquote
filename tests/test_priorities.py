"""Reported priorities, the edit history, and the card checks: the quote on a card is the stored transcript's text,
and highlights fall only on words both the quote and the priority text on the card hold."""

import contextlib
import html
import io
import json
import re
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from pairing_site import app as app_module, db, pipeline, priorities

from helpers import temp_database
from test_site import SiteCase

import fmap_lib as fl

WORDS = "The Chamber supports Prop H as public transit is a critical driver of the San Francisco economy"
MORE = "Second sentence that the page holds as well for the edit test"
PAGE = ('<html><head><meta property="og:site_name" content="Mission Local">'
        '<meta property="article:published_time" content="2026-10-08T09:00:00-07:00"></head>'
        "<body><p>%s, helping workers.</p><p>%s.</p></body></html>" % (WORDS, MORE))


class PageDetails(unittest.TestCase):
    def test_outlet_is_og_site_name_else_the_domain(self):
        self.assertEqual(priorities.page_details(PAGE, "https://missionlocal.org/a")["outlet"], "Mission Local")
        self.assertEqual(priorities.page_details("<html></html>", "https://www.sfexaminer.com/a")["outlet"], "sfexaminer.com")

    def test_date_comes_from_the_pages_metadata(self):
        self.assertEqual(priorities.page_details(PAGE, "https://x.org/")["page_date"], "2026-10-08")
        ld = '<script type="application/ld+json">{"@type":"NewsArticle","datePublished":"2026-03-04T10:00:00Z"}</script>'
        self.assertEqual(priorities.page_details(ld, "https://x.org/")["page_date"], "2026-03-04")
        self.assertEqual(priorities.page_details('<time datetime="2026-07-06">July 6</time>', "https://x.org/")["page_date"], "2026-07-06")
        self.assertEqual(priorities.page_details('<meta name="date" content="October 8, 2026">', "https://x.org/")["page_date"], "2026-10-08")

    def test_no_date_or_an_impossible_one_gives_none(self):
        self.assertEqual(priorities.page_details("<p>no dates</p>", "https://x.org/")["page_date"], "")
        self.assertEqual(priorities.page_details('<meta name="date" content="2026-02-31">', "https://x.org/")["page_date"], "")

    def test_lookup_refuses_private_addresses_and_reports_fetch_failures(self):
        with self.assertRaises(priorities.PriorityError):
            priorities.lookup("http://127.0.0.1/admin")
        with mock.patch.object(priorities, "check_public_url"):
            with self.assertRaises(priorities.PriorityError):
                priorities.lookup("https://example.org/", fetch=mock.Mock(side_effect=OSError("refused")))


class SourceFields(unittest.TestCase):
    def test_a_news_report_needs_outlet_and_date(self):
        with self.assertRaisesRegex(priorities.PriorityError, "outlet"):
            priorities.clean_source("", "2026-10-08", "news")
        with self.assertRaisesRegex(priorities.PriorityError, "date"):
            priorities.clean_source("Mission Local", "", "news")
        ok = priorities.clean_source("  Mission   Local ", "2026-10-08", "news")
        self.assertEqual(ok, {"outlet": "Mission Local", "page_date": "2026-10-08", "kind": priorities.KIND_NEWS})

    def test_dates_must_be_real_and_not_in_the_future(self):
        for bad in ("10/08/2026", "2026-02-30", "2026-1-5", "yesterday", "20261008"):
            with self.assertRaisesRegex(priorities.PriorityError, "not a real day"):
                priorities.clean_source("Mission Local", bad, "news")
        with self.assertRaisesRegex(priorities.PriorityError, "future"):
            priorities.clean_source("Mission Local", "2999-01-01", "news")
        self.assertEqual(priorities.clean_source("Mission Local", "2026-10-08", "news", today="2026-10-08")["page_date"], "2026-10-08")

    def test_own_page_needs_neither_but_a_given_date_is_checked(self):
        self.assertEqual(priorities.clean_source("ignored", "", "own"),
                         {"outlet": "", "page_date": "", "kind": priorities.KIND_OWN})
        with self.assertRaises(priorities.PriorityError):
            priorities.clean_source("", "2026-02-30", "own")
        with self.assertRaises(priorities.PriorityError):
            priorities.clean_source("x", "2026-10-08", "whose-words")


class History(unittest.TestCase):
    def setUp(self):
        ctx = temp_database()
        ctx.__enter__()
        self.addCleanup(ctx.__exit__, None, None, None)
        db.migrate()
        self.fam = {"key": "sf-chamber", "name": "SF Chamber"}
        self.news = priorities.clean_source("Mission Local", "2026-10-08", "news")
        self.found = {"url": "https://x.org/a", "text": WORDS, "retrieved": "2026-10-30"}

    def test_an_edit_keeps_the_whole_old_row_and_the_new_one_is_current(self):
        with db.session(write=True) as conn:
            pid = priorities.add(conn, self.fam, "k1", self.found, self.news, "maintainer")
            priorities.update(conn, pid, dict(self.found, text=MORE, url="https://x.org/b", retrieved="2026-11-02"),
                              dict(self.news, outlet="The Real Deal", page_date="2026-10-09"), "maintainer", expected_version=1)
        with db.session() as conn:
            current, earlier = priorities.history(conn, pid)
            snap = conn.execute("SELECT snapshot FROM audit_log WHERE priority_id = ? AND snapshot IS NOT NULL", (pid,)).fetchone()["snapshot"]
        self.assertEqual((current["version"], current["text"], current["outlet"]), (2, MORE, "The Real Deal"))
        self.assertEqual(len(earlier), 1)
        old = earlier[0]
        self.assertEqual((old["version"], old["text"], old["url"], old["outlet"], old["page_date"], old["retrieved"], old["kind"]),
                         (1, WORDS, "https://x.org/a", "Mission Local", "2026-10-08", "2026-10-30", priorities.KIND_NEWS))
        self.assertEqual(snap["key"], "k1")
        self.assertIsNotNone(old["superseded_at"])

    def test_several_edits_list_newest_first(self):
        with db.session(write=True) as conn:
            pid = priorities.add(conn, self.fam, "k1", self.found, self.news, "maintainer")
            for n, text in enumerate((MORE, WORDS, MORE), 2):
                priorities.update(conn, pid, dict(self.found, text=text), self.news, "maintainer")
        with db.session() as conn:
            current, earlier = priorities.history(conn, pid)
            counts = priorities.edit_counts(conn)
        self.assertEqual([e["version"] for e in earlier], [3, 2, 1])
        self.assertEqual(current["version"], 4)
        self.assertEqual(counts[pid], 3)

    def test_a_stale_form_cannot_overwrite_a_newer_edit(self):
        with db.session(write=True) as conn:
            pid = priorities.add(conn, self.fam, "k1", self.found, self.news, "maintainer")
            priorities.update(conn, pid, self.found, self.news, "maintainer")
        with self.assertRaisesRegex(priorities.PriorityError, "edited after you opened"):
            with db.session(write=True) as conn:
                priorities.update(conn, pid, dict(self.found, text=MORE), self.news, "maintainer", expected_version=1)
        with db.session() as conn:
            self.assertEqual(priorities.history(conn, pid)[0]["text"], WORDS)

    def test_unchanged_ignores_the_retrieval_date_and_squashes_the_words(self):
        row = {"url": "https://x.org/a", "text": WORDS, "page_date": "2026-10-08", "kind": priorities.KIND_NEWS,
               "outlet": "Mission Local"}
        self.assertTrue(priorities.unchanged(row, " https://x.org/a ", "  " + WORDS.replace(" ", "  ") + " ", self.news))
        self.assertFalse(priorities.unchanged(row, "https://x.org/a", WORDS.lower(), self.news))


class Cards(unittest.TestCase):
    ROWS = [("00:00:01", "HELLO THERE"), ("00:00:05", "GENERAL  KENOBI \u201cYOU ARE A BOLD ONE\u201d"),
            ("00:00:09", "THE END")]

    def stored(self):
        return [(s, " ".join(t.split())) for s, t in self.ROWS]

    def test_exact_text_matches(self):
        text = "HELLO THERE GENERAL KENOBI \u201cYOU ARE A BOLD ONE\u201d THE END"
        self.assertEqual(pipeline.check_quote(self.stored(), text, "00:00:01", "00:00:09")[0], "matches")
        self.assertEqual(pipeline.check_quote(self.stored(), "THERE GENERAL", "00:00:01", "00:00:05")[0], "matches")

    def test_any_difference_is_a_mismatch_and_returns_the_stored_text(self):
        stored = "HELLO THERE GENERAL KENOBI \u201cYOU ARE A BOLD ONE\u201d"
        for changed in ("hello there general kenobi \u201cYOU ARE A BOLD ONE\u201d",       # case
                        "HELLO  THERE GENERAL KENOBI \u201cYOU ARE A BOLD ONE\u201d",      # whitespace
                        'HELLO THERE GENERAL KENOBI "YOU ARE A BOLD ONE"',                 # straightened quotes
                        "HELLO THERE GENERAL KENOBI \u201cYOU ARE A BOLD ONE\u201d.",      # punctuation
                        "HELLO THERE GENERAL KENOBI \u201cYOU ARE A BOLD ONE\u201d\u200b",  # invisible character
                        "HELLO THERE GENERAL KENOBI \u201cYOU ARE A BOLD ONE\u201d "):     # trailing space
            status, shown = pipeline.check_quote(self.stored(), changed, "00:00:01", "00:00:05")
            self.assertEqual((status, shown), ("mismatch", stored), changed)

    def test_a_quote_outside_its_stamps_or_with_no_transcript_is_not_a_match(self):
        self.assertEqual(pipeline.check_quote(self.stored(), "THE END", "00:00:01", "00:00:05")[0], "mismatch")
        self.assertEqual(pipeline.check_quote(self.stored(), "THE END", "00:09:99", "00:00:09")[0], "unavailable")
        self.assertEqual(pipeline.check_quote(self.stored(), "THE END", "00:00:09", "00:00:01")[0], "unavailable")
        self.assertEqual(pipeline.check_quote(None, "THE END", "00:00:09", "00:00:09")[0], "unavailable")
        self.assertEqual(pipeline.check_quote(self.stored(), "", "00:00:01", "00:00:01")[0], "mismatch")

    CARD = {"highlight": ["PROP H", "housing", "R&D"],
            "donor": {"statements": [{"section": "Housing and R&D", "text": "The Chamber supports Prop H and R&D."}]}}

    def test_highlights_are_only_words_in_both(self):
        self.assertEqual(pipeline.shared_terms("I back prop h, and R&D too", self.CARD), ["PROP H", "R&D"])
        self.assertEqual(pipeline.shared_terms("I back it", self.CARD), [])
        # "Prop  H" (two spaces) is not literally the term, and R and D is not R&D
        self.assertEqual(pipeline.shared_terms("a Prop  H and R and D", self.CARD), [])
        # the section the card shows counts as priority text, and a hyphen ends a word
        self.assertEqual(pipeline.shared_terms("a housing-related remark", self.CARD), ["housing"])
        self.assertEqual(pipeline.shared_terms("Prop Hx", self.CARD), [])

    def test_a_term_the_priority_no_longer_holds_is_dropped(self):
        card = {"highlight": ["PROP H"], "donor": {"statements": [{"section": "", "text": "The Chamber supports Prop J."}]}}
        self.assertEqual(pipeline.shared_terms("Prop H passes", card), [])

    def test_marking_wraps_text_without_changing_it(self):
        text = '"Tom & Jerry <b>PROP h</b> it\'s"  spaced\u00a0here \u201cq\u201d'
        out = str(app_module.marked(text, ["prop h", "Tom"]))
        self.assertIn("<mark>PROP h</mark>", out)
        self.assertIn("<mark>Tom</mark>", out)
        self.assertEqual(html.unescape(re.sub(r"</?mark>", "", out)), text)


class Site(SiteCase):
    def post_priority(self, **fields):
        data = {"family": "sf-chamber", "url": "https://example.org/guide", "words": WORDS, "outlet": "Mission Local",
                "page_date": "2026-10-08", "kind": "news"}
        data.update(fields)
        with mock.patch.object(priorities, "check_public_url"), mock.patch.object(priorities.fl, "fetch_page", return_value=PAGE):
            return self.client.post("/priority", data=data)

    def last_priority(self):
        with db.session() as conn:
            return conn.execute("SELECT * FROM donor_priorities ORDER BY id DESC LIMIT 1").fetchone()

    def test_lookup_prefills_outlet_and_date_from_the_link(self):
        self.sign_in()
        count = "SELECT count(*) AS n FROM donor_priorities"
        with db.session() as conn:
            before = conn.execute(count).fetchone()["n"]
        with mock.patch.object(priorities, "check_public_url"), mock.patch.object(priorities.fl, "fetch_page", return_value=PAGE):
            res = self.client.post("/priority/lookup", data={"url": "https://example.org/guide", "kind": "news", "words": "kept words"})
        self.assertEqual(res.status_code, 200)
        self.assertIn('value="Mission Local"', res.text)
        self.assertIn('value="2026-10-08"', res.text)
        self.assertIn("kept words", res.text)
        with db.session() as conn:
            self.assertEqual(conn.execute(count).fetchone()["n"], before)  # a lookup saves nothing

    def test_lookup_of_a_private_address_is_refused(self):
        self.sign_in()
        res = self.client.post("/priority/lookup", data={"url": "http://127.0.0.1/x", "kind": "news"})
        self.assertEqual(res.status_code, 422)
        self.assertIn("not a public web page", res.text)

    def test_news_report_is_saved_with_outlet_link_page_date_and_server_retrieval_date(self):
        self.sign_in()
        res = self.post_priority(retrieved="1999-01-01")
        self.assertEqual(res.status_code, 200)
        row = self.last_priority()
        self.assertEqual((row["kind"], row["outlet"], row["url"], row["page_date"], row["text"]),
                         ("news report", "Mission Local", "https://example.org/guide", "2026-10-08", WORDS))
        self.assertEqual(str(row["retrieved"]), fl.today())
        self.assertIn("News report: Mission Local", self.client.get("/priority").text)

    def test_incomplete_or_invalid_input_saves_nothing(self):
        self.sign_in()
        before = self.last_priority()["id"]
        for fields, needle in (({"outlet": ""}, "Name the outlet"), ({"page_date": ""}, "Give the date the article shows"),
                               ({"page_date": "2026-02-30"}, "not a real day"), ({"family": ""}, "Choose the donor"),
                               ({"words": "Not anywhere on that page at all, none of it"}, "not on the page")):
            res = self.post_priority(**fields)
            self.assertEqual(res.status_code, 422, fields)
            self.assertIn(needle, res.text)
        self.assertEqual(self.last_priority()["id"], before)

    def test_edit_reverifies_keeps_the_old_wording_and_shows_it_under_earlier_wording(self):
        self.sign_in()
        self.post_priority()
        row = self.last_priority()
        form = self.client.get("/priority/%d/edit" % row["id"])
        self.assertIn('value="https://example.org/guide"', form.text)
        self.assertIn('name="version" value="1"', form.text)
        same = self.post_priority(priority_id=str(row["id"]), version="1")
        self.assertEqual(same.status_code, 422)
        self.assertIn("Nothing was changed", same.text)
        bad = self.post_priority(priority_id=str(row["id"]), version="1", words="Words that the page never held in any form")
        self.assertEqual(bad.status_code, 422)
        self.assertEqual(self.last_priority()["version"], 1)
        ok = self.post_priority(priority_id=str(row["id"]), version="1", words=MORE, page_date="2026-10-09")
        self.assertEqual(ok.status_code, 200)
        self.assertIn("Earlier wording", ok.text)
        now = self.last_priority()
        self.assertEqual((now["id"], now["version"], now["text"], now["page_date"]), (row["id"], 2, MORE, "2026-10-09"))
        stale = self.post_priority(priority_id=str(row["id"]), version="1", words=WORDS)
        self.assertEqual(stale.status_code, 422)
        self.assertIn("edited after you opened", stale.text)
        page = self.client.get("/priority/%d/history" % row["id"])
        self.assertEqual(page.status_code, 200)
        self.assertLess(page.text.index("Current"), page.text.index("Superseded"))
        self.assertIn(WORDS, page.text)
        self.assertIn("page dated 2026-10-08", page.text)
        self.assertIn(MORE, page.text)
        self.assertEqual(self.client.get("/priority/99999/history").status_code, 404)

    def test_priority_pages_need_sign_in(self):
        anon = TestClient(self.client.app, follow_redirects=False)
        for path in ("/priority", "/priority/1/edit", "/priority/1/history"):
            self.assertEqual(anon.get(path).status_code, 303, path)
        self.assertEqual(anon.post("/priority/lookup", data={}).status_code, 303)

    # ---- the card's quote and the review screen

    def card_of(self, slug):
        with db.session() as conn:
            return conn.execute("SELECT id, card FROM pairings WHERE slug = ?", (slug,)).fetchone()

    @contextlib.contextmanager
    def tampered(self, slug, change):
        row = self.card_of(slug)
        card = json.loads(json.dumps(row["card"]))
        change(card)
        with db.session(write=True) as conn:
            conn.execute("UPDATE pairings SET card = ? WHERE id = ?", (db.json_value(card), row["id"]))
        try:
            yield card
        finally:
            with db.session(write=True) as conn:
                conn.execute("UPDATE pairings SET card = ? WHERE id = ?", (db.json_value(row["card"]), row["id"]))

    @staticmethod
    def plain(text):
        return html.unescape(re.sub(r"</?mark>", "", text))

    def test_card_shows_the_stored_transcript_text_and_logs_a_mismatch(self):
        slug = "lurie-chamber-muni"
        original = self.card_of(slug)["card"]["quote"]["text"]
        ok = self.plain(self.client.get("/pairings/" + slug).text)
        self.assertIn('"%s"' % original, ok)
        self.assertNotIn("differed from the stored transcript", ok)

        def change(card):
            card["quote"]["text"] = original.replace(" the ", " THE ", 1) if " the " in original else original + "!"

        with db.session() as conn:
            row = conn.execute("SELECT p.card, m.captions FROM pairings p JOIN meetings m ON m.id = p.meeting_id "
                               "WHERE p.slug = ?", (slug,)).fetchone()
        q = row["card"]["quote"]
        stored = pipeline.quote_span(pipeline.parse_captions(row["captions"]), q["first_stamp"], q["last_stamp"])
        self.assertIn(original, stored)
        buf = io.StringIO()
        with self.tampered(slug, change) as card:
            self.assertNotEqual(card["quote"]["text"], original)
            with contextlib.redirect_stdout(buf):
                page = self.plain(self.client.get("/pairings/" + slug).text)
        self.assertIn('"%s"' % stored, page)
        self.assertNotIn(card["quote"]["text"], page)
        self.assertIn("differed from the stored transcript", page)
        logged = [json.loads(x) for x in buf.getvalue().splitlines() if x.strip().startswith("{")]
        self.assertTrue([x for x in logged if x.get("level") == "warn" and x.get("slug") == slug and x.get("status") == "mismatch"])

    def test_front_page_quotes_match_the_transcript_without_a_warning(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("differed from the stored transcript", res.text)
        self.assertNotIn('"level": "warn"', buf.getvalue())

    def test_a_news_report_on_a_card_has_its_badge(self):
        slug = "lurie-chamber-muni"

        def change(card):
            card["donor"]["statements"][0].update(kind="news report", outlet="Mission Local")

        self.assertNotIn("News report:", self.client.get("/pairings/" + slug).text)
        with self.tampered(slug, change):
            self.assertIn("News report: Mission Local", self.client.get("/pairings/" + slug).text)

    def test_review_ticks_matches_transcript_and_refuses_approval_when_it_does_not(self):
        self.sign_in()
        page = self.client.get("/review").text
        self.assertIn("matches transcript", page)
        self.assertIn("Priority wording:", page)
        with db.session() as conn:
            row = conn.execute("SELECT id, slug FROM pairings WHERE status = 'pending' ORDER BY id LIMIT 1").fetchone()

        def change(card):
            card["quote"]["text"] = card["quote"]["text"] + " (edited)"

        hx = {"HX-Request": "true"}
        with self.tampered(row["slug"], change):
            res = self.client.post("/review/%d/approve" % row["id"], data={"recording_checked": "on"}, headers=hx)
            self.assertIn("does not match the stored transcript", res.text)
            with db.session() as conn:
                self.assertEqual(conn.execute("SELECT status FROM pairings WHERE id = ?", (row["id"],)).fetchone()["status"], "pending")
                self.assertTrue(conn.execute("SELECT 1 FROM audit_log WHERE pairing_id = ? AND action = 'approval refused'", (row["id"],)).fetchone())
        res = self.client.post("/review/%d/approve" % row["id"], data={"recording_checked": "on"}, headers=hx)
        self.assertIn("&#10003; matches transcript", res.text)
        with db.session() as conn:
            detail = conn.execute("SELECT detail FROM audit_log WHERE pairing_id = ? AND action = 'approved'", (row["id"],)).fetchone()["detail"]
        self.assertIn("matches the stored transcript", detail)


class Seeded(SiteCase):
    def test_seed_has_news_reports_and_a_kept_earlier_wording(self):
        with db.session() as conn:
            news = conn.execute("SELECT id, outlet, version FROM donor_priorities WHERE kind = 'news report'").fetchall()
        self.assertTrue(news)
        self.assertTrue(all(r["outlet"] for r in news))
        edited = [r for r in news if r["version"] > 1]
        self.assertEqual(len(edited), 1)
        self.sign_in()
        page = self.client.get("/priority/%d/history" % edited[0]["id"]).text
        self.assertIn("Superseded", page)
        self.assertIn("Earlier wording", self.client.get("/priority").text)


if __name__ == "__main__":
    unittest.main()
