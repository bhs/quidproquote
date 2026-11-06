"""Priorities entered from two sources, edited without losing the earlier wording, and cards drawn from the
current wording with the quote exactly as the stored transcript has it."""

import html
import os
import re
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from pairing_site import app as app_module, cards, db, pipeline, priorities, seed

from helpers import temp_database

import pairing_cards as pc

HX = {"HX-Request": "true"}
GOOD = {"url": "https://news.example.org/story", "outlet": "Example News", "whose_words": "reporter",
        "page_date": "2026-10-01", "section": "", "words": "The union says it will oppose the measure on the November ballot"}


class Clean(unittest.TestCase):
    def test_reported_needs_outlet_whose_words_date_and_link(self):
        self.assertEqual(priorities.clean("reported", GOOD)["outlet"], "Example News")
        for field, message in (("outlet", "outlet"), ("whose_words", "whose words"), ("page_date", "date"), ("url", "link")):
            with self.assertRaises(priorities.PriorityError) as ctx:
                priorities.clean("reported", dict(GOOD, **{field: "  "}))
            self.assertIn(message, str(ctx.exception).lower())

    def test_dates_must_be_real_year_month_day_and_not_in_the_future(self):
        for bad in ("2026-13-01", "2026-02-30", "10/08/2026", "20261008", "next week", "2999-01-01"):
            with self.assertRaises(priorities.PriorityError, msg=bad):
                priorities.clean("reported", dict(GOOD, page_date=bad))
        with self.assertRaises(priorities.PriorityError):  # an own-site date is optional but never free text
            priorities.clean("own", dict(GOOD, page_date="sometime in October"))
        self.assertEqual(priorities.clean("own", dict(GOOD, page_date=""))["page_date"], "")

    def test_link_must_be_a_web_address_and_whose_words_one_of_the_three(self):
        for bad in ("ftp://example.org/x", "example.org/story", "javascript:alert(1)"):
            with self.assertRaises(priorities.PriorityError, msg=bad):
                priorities.clean("reported", dict(GOOD, url=bad))
        with self.assertRaises(priorities.PriorityError):
            priorities.clean("reported", dict(GOOD, whose_words="the mayor's"))

    def test_own_site_entry_carries_no_outlet_or_whose_words(self):
        f = priorities.clean("own", GOOD)
        self.assertEqual((f["outlet"], f["whose_words"]), ("", ""))

    def test_short_words_and_long_fields_are_refused(self):
        with self.assertRaises(priorities.PriorityError):
            priorities.clean("reported", dict(GOOD, words="too few words"))
        with self.assertRaises(priorities.PriorityError):
            priorities.clean("reported", dict(GOOD, section="x" * 201))


PAGE = "<p>The union says it will oppose the measure on the November ballot, its president said.</p>"


class Verify(unittest.TestCase):
    def down(self, url):
        raise OSError("connection refused")

    def test_an_unfetchable_report_is_saved_unchecked_but_an_own_site_entry_is_refused(self):
        with mock.patch.object(priorities, "check_public_url"):
            found = priorities.verify(GOOD["url"], GOOD["words"], fetch=self.down, strict=False)
            self.assertFalse(found["checked"])
            self.assertIn("connection refused", found["why"])
            with self.assertRaises(priorities.PageUnavailable):
                priorities.verify(GOOD["url"], GOOD["words"], fetch=self.down, strict=True)

    def test_an_unresolvable_address_counts_as_unfetchable_but_a_private_one_is_always_refused(self):
        def unresolved(url):
            raise priorities.PageUnavailable("did not resolve")
        with mock.patch.object(priorities, "check_public_url", unresolved):
            self.assertFalse(priorities.verify(GOOD["url"], GOOD["words"], strict=False)["checked"])
        with self.assertRaises(priorities.PriorityError):
            priorities.verify("http://127.0.0.1/admin", GOOD["words"], fetch=lambda u: PAGE, strict=False)

    def test_a_fetched_page_without_the_words_is_refused_for_both_types(self):
        with mock.patch.object(priorities, "check_public_url"):
            for strict in (True, False):
                with self.assertRaises(priorities.PriorityError):
                    priorities.verify(GOOD["url"], "Words that are nowhere on that page at all", fetch=lambda u: PAGE, strict=strict)
            self.assertTrue(priorities.verify(GOOD["url"], GOOD["words"], fetch=lambda u: PAGE, strict=False)["checked"])


class Versions(unittest.TestCase):
    """Edits against a real file: the earlier row keeps its wording and source, and is hidden from lists."""

    def setUp(self):
        self.ctx = temp_database()
        self.ctx.__enter__()
        self.addCleanup(self.ctx.__exit__, None, None, None)
        db.migrate()
        self.fam = {"key": "sf-poa", "name": "SF Police Officers Association"}
        self.page = patch = mock.patch.object(priorities, "check_public_url")
        patch.start()
        self.addCleanup(patch.stop)

    def add(self, **over):
        row, _ = priorities.add("reported", self.fam, dict(GOOD, **over), "maintainer", fetch=lambda u: PAGE)
        return row

    def test_edit_inserts_a_new_row_and_keeps_the_old_one_whole(self):
        old = self.add()
        new = priorities.edit(old["id"], dict(GOOD, words="The union says it will oppose the measure", section="Ballot"),
                              "maintainer", fetch=lambda u: PAGE)
        with db.session() as conn:
            kept = priorities.get(conn, old["id"])
            self.assertEqual((kept["text"], kept["url"], kept["outlet"], kept["section"]),
                             (old["text"], old["url"], old["outlet"], old["section"]))
            self.assertIsNotNone(kept["replaced_at"])
            self.assertEqual(new["supersedes_key"], old["key"])
            self.assertIsNone(new["replaced_at"])
            self.assertEqual(new["text"], "The union says it will oppose the measure")
            self.assertEqual([r["id"] for r in priorities.current_rows(conn)], [new["id"]])
            self.assertEqual([r["id"] for r in priorities.earlier_versions(conn, new)], [old["id"]])
            self.assertEqual(priorities.current_version(conn, kept)["id"], new["id"])
            log = conn.execute("SELECT detail FROM audit_log WHERE action = 'priority edited'").fetchone()
        self.assertIn("earlier wording is kept", log["detail"])

    def test_two_edits_make_a_chain_newest_first(self):
        first = self.add()
        second = priorities.edit(first["id"], dict(GOOD, section="One"), "maintainer", fetch=lambda u: PAGE)
        third = priorities.edit(second["id"], dict(GOOD, section="Two"), "maintainer", fetch=lambda u: PAGE)
        with db.session() as conn:
            chain = [r["section"] for r in priorities.earlier_versions(conn, third)]
            self.assertEqual(chain, ["One", ""])
            self.assertEqual(priorities.current_version(conn, priorities.get(conn, first["id"]))["id"], third["id"])
            self.assertEqual(len(priorities.current_rows(conn)), 1)

    def test_an_edit_that_changes_nothing_or_breaks_a_rule_saves_nothing(self):
        old = self.add()
        for form in (dict(GOOD), dict(GOOD, outlet=""), dict(GOOD, page_date="2026-02-31"),
                     dict(GOOD, words="Words that are nowhere on that page at all")):
            with self.assertRaises(priorities.PriorityError):
                priorities.edit(old["id"], form, "maintainer", fetch=lambda u: PAGE)
        with db.session() as conn:
            self.assertEqual(conn.execute("SELECT count(*) AS n FROM donor_priorities").fetchone()["n"], 1)
            self.assertIsNone(priorities.get(conn, old["id"])["replaced_at"])

    def test_editing_a_replaced_priority_is_refused(self):
        old = self.add()
        priorities.edit(old["id"], dict(GOOD, section="One"), "maintainer", fetch=lambda u: PAGE)
        with self.assertRaises(priorities.PriorityGone):
            priorities.edit(old["id"], dict(GOOD, section="Two"), "maintainer", fetch=lambda u: PAGE)

    def test_untouched_words_are_kept_character_for_character(self):
        """The add check straightens quotes; an edit of another field must not re-squash words left alone."""
        with db.session(write=True) as conn:
            conn.execute("INSERT INTO donor_priorities (key, family, donor, url, text, retrieved, kind, added_by) VALUES "
                         "('k1', 'sf-poa', 'SF POA', 'https://example.org/a', ?, '2026-10-30', 'page', 'survey')",
                         ("The \u201cmayor\u201d said  this  \u2014 and that, in full sentences here",))
            old = priorities.get(conn, 1)
        new = priorities.edit(old["id"], {"url": old["url"], "words": old["text"], "section": "Heading", "page_date": "",
                                          "outlet": "", "whose_words": ""}, "maintainer",
                              fetch=lambda u: self.fail("the page is checked again only when the link or words change"))
        self.assertEqual(new["text"], old["text"])
        self.assertEqual(new["section"], "Heading")
        self.assertTrue(new["page_checked"])


class Highlights(unittest.TestCase):
    def test_only_words_literally_in_both_are_highlighted(self):
        quote = "We must fund Muni service, and the Parcel Tax is how."
        statements = [{"section": "Prop H", "text": "The Chamber backs the parcel tax for Municipal Transportation."}]
        got = pipeline.highlight_terms(quote, statements, ["Muni", "parcel tax", "PARCEL TAX", "fund", "Municipal"])
        self.assertEqual(got, ["parcel tax"])  # "Muni" is not a whole word of the priority; "fund" is not in it

    def test_punctuation_and_case_decide_nothing_but_whole_words(self):
        got = pipeline.highlight_terms("Prop H, again: prop h!", [{"section": "", "text": "Vote on PROP H."}], ["Prop H"])
        self.assertEqual(got, ["Prop H"])
        self.assertEqual(pipeline.highlight_terms("Props", [{"section": "", "text": "Prop H"}], ["Prop"]), [])

    def test_marking_adds_tags_around_the_text_and_changes_nothing_in_it(self):
        text = 'He said \u201cProp H\u201d  &  <b>Prop H</b>\u2019s  "tax"\ttoday...  '
        out = pc.marked(text, ["Prop H"], lambda t: html.escape(t, quote=True))
        self.assertIn("<mark>Prop H</mark>", out)
        self.assertEqual(html.unescape(re.sub(r"</?mark>", "", out)), text)
        self.assertNotIn("<b>", out)  # the markup in the words is escaped, not interpreted
        self.assertEqual(pc.marked(text, [], lambda t: html.escape(t, quote=True)), html.escape(text, quote=True))


class Quote(unittest.TestCase):
    CAPTIONS = "00:00:01\tIt's 100% about Muni,\n00:00:05\t\u201cMuni\u201d   &  <the> bus \u2014 ok?\n00:00:09\tthe end.\n"

    def test_same_text_is_kept_and_any_difference_returns_the_transcript_text(self):
        truth = "It's 100% about Muni, \u201cMuni\u201d & <the> bus \u2014 ok?"
        text, state = cards.transcript_quote(self.CAPTIONS, truth, truth, "00:00:01", "00:00:05")
        self.assertEqual((text, state), (truth, cards.SAME))
        for tampered in (truth + " ", " " + truth, truth.replace("\u201c", '"'), truth.lower(), truth.replace("&", "and"),
                         truth.replace("\u2014", "-"), truth[:-1], truth.replace(" ", "  ", 1)):
            text, state = cards.transcript_quote(self.CAPTIONS, tampered, truth, "00:00:01", "00:00:05")
            self.assertEqual((text, state), (truth, cards.REPLACED), msg=repr(tampered))

    def test_the_stamps_stand_in_when_the_stored_quote_is_not_in_the_transcript(self):
        text, state = cards.transcript_quote(self.CAPTIONS, "words that were never said", "words never said", "00:00:09", "00:00:09")
        self.assertEqual((text, state), ("the end.", cards.REPLACED))

    def test_a_quote_found_nowhere_is_unverified_and_left_as_it_is(self):
        text, state = cards.transcript_quote(self.CAPTIONS, "never said", "never said", "23:00:00", "23:00:01")
        self.assertEqual((text, state), ("never said", cards.UNVERIFIED))


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
        assert cls.client.post("/login", data={"token": "tok-123", "next": "/review"}).status_code == 303

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        cls.dbctx.__exit__(None, None, None)
        cls.env.stop()

    def one(self, sql, *args):
        with db.session() as conn:
            return conn.execute(sql, args).fetchone()


class Priorities(SiteCase):
    def test_two_buttons_open_the_same_form_with_only_the_fields_each_type_needs(self):
        page = self.client.get("/priority").text
        self.assertIn("Add from the donor's own site", page)
        self.assertIn("Add from a news report", page)
        own = self.client.get("/priority/form?type=own", headers=HX).text
        rep = self.client.get("/priority/form?type=reported", headers=HX).text
        self.assertNotIn('name="outlet"', own)
        self.assertNotIn('name="whose_words"', own)
        for name in ('name="outlet"', 'name="whose_words"', 'name="page_date"', 'name="url"', 'name="words"'):
            self.assertIn(name, rep)
        self.assertIn('value="reported"', rep)
        self.assertEqual(self.client.get("/priority/form?type=other", headers=HX).status_code, 404)

    def test_reported_priority_missing_a_source_field_is_not_saved(self):
        before = self.one("SELECT count(*) AS n FROM donor_priorities")["n"]
        base = {"type": "reported", "family": "sf-poa", "url": "https://news.example.org/s", "outlet": "Example News",
                "whose_words": "reporter", "page_date": "2026-10-01", "words": GOOD["words"]}
        for field, shown in (("outlet", "Name the outlet"), ("page_date", "Enter the date"), ("url", "Add the link"),
                             ("whose_words", "Say whose words")):
            res = self.client.post("/priority", data=dict(base, **{field: ""}))
            self.assertEqual(res.status_code, 422, field)
            self.assertIn(shown, res.text)
            self.assertIn('id="priority-form"', res.text)  # the form stays open with what was typed
        res = self.client.post("/priority", data=dict(base, page_date="2026-02-30"))
        self.assertEqual(res.status_code, 422)
        self.assertEqual(self.one("SELECT count(*) AS n FROM donor_priorities")["n"], before)

    def test_unfetchable_report_is_saved_with_the_plain_label_and_own_site_stays_strict(self):
        data = {"family": "sf-poa", "url": "https://news.example.org/gone", "words": GOOD["words"]}
        with mock.patch.object(priorities, "check_public_url"), \
                mock.patch.object(priorities.fl, "fetch_page", side_effect=OSError("HTTP 403")):
            rep = self.client.post("/priority", data=dict(data, type="reported", outlet="Test Gazette",
                                                          whose_words="third_party", page_date="2026-09-30"))
            own = self.client.post("/priority", data=dict(data, type="own"))
        self.assertEqual(rep.status_code, 200)
        self.assertIn("not checked against page", rep.text)
        self.assertEqual(own.status_code, 422)
        row = self.one("SELECT * FROM donor_priorities WHERE outlet = 'Test Gazette'")
        self.assertEqual((row["whose_words"], row["page_date"], bool(row["page_checked"]), row["kind"]),
                         ("third_party", "2026-09-30", False, priorities.REPORTED_KIND))
        self.assertEqual(str(row["retrieved"]), priorities.fl.today())
        self.assertIn("Reported by Test Gazette; words are a third party&#39;s", rep.text)
        self.assertIsNone(self.one("SELECT 1 AS x FROM donor_priorities WHERE url = ? AND whose_words = ''", data["url"]))

    def test_own_site_rows_and_reported_rows_are_told_apart_in_the_list(self):
        page = self.client.get("/priority").text
        self.assertIn('class="prow reported"', page)
        self.assertIn('class="prow "', page)
        self.assertIn("Reported by Mission Local; words are a named person at the donor, quoted", page)

    def test_edit_swaps_a_row_for_a_prefilled_form_and_back_and_keeps_the_earlier_wording(self):
        old = self.one("SELECT * FROM donor_priorities WHERE key = 'POA-I-TIMING'")
        form = self.client.get("/priority/%d/edit" % old["id"], headers=HX).text
        self.assertIn('hx-post="/priority/%d/edit"' % old["id"], form)
        self.assertIn(wording, form)
        new_words = priorities.fl.squash(old["text"].split(". ")[0] + ".")
        wording = old["text"][:40]  # plain characters, so escaping cannot change how it appears on the page
        page = "<p>%s</p>" % html.escape(old["text"])
        with mock.patch.object(priorities, "check_public_url"), mock.patch.object(priorities.fl, "fetch_page", return_value=page):
            bad = self.client.post("/priority/%d/edit" % old["id"], headers=HX, data={
                "url": old["url"], "words": "Not anywhere on that page, none of these words are", "section": old["section"],
                "page_date": old["page_date"]})
            res = self.client.post("/priority/%d/edit" % old["id"], headers=HX, data={
                "url": old["url"], "words": new_words, "section": old["section"], "page_date": old["page_date"]})
        self.assertEqual(bad.status_code, 200)
        self.assertIn("role=\"alert\"", bad.text)
        self.assertIn("<li", res.text)
        self.assertIn("Earlier wording", res.text)
        self.assertIn("Saved as a new version", res.text)
        new = self.one("SELECT * FROM donor_priorities WHERE supersedes_key = 'POA-I-TIMING'")
        self.assertEqual(new["text"], new_words)
        kept = self.one("SELECT * FROM donor_priorities WHERE key = 'POA-I-TIMING'")
        self.assertEqual(kept["text"], old["text"])
        self.assertIsNotNone(kept["replaced_at"])
        listing = self.client.get("/priority").text
        self.assertIn("priority-%d" % new["id"], listing)
        self.assertNotIn('id="priority-%d"' % old["id"], listing)
        history = self.client.get("/priority/%d/history" % new["id"], headers=HX).text
        self.assertIn(wording, history)
        self.assertIn("replaced %s" % kept["replaced_at"].date(), history)

    def test_a_card_reads_the_current_priority_and_says_when_it_was_updated(self):
        text = self.client.get("/pairings/lurie-chamber-muni").text
        self.assertIn("priority updated", text)
        self.assertRegex(text, r"(?i)<mark>muni</mark>")
        self.assertNotIn("The anticipated revenue", text)  # the earlier wording is not on the card
        self.assertTrue(self.one("SELECT 1 AS x FROM donor_priorities WHERE key = 'CHAMBER-H' AND replaced_at IS NOT NULL"))

    def test_a_reported_priority_is_marked_on_the_review_screen_and_on_the_card(self):
        review = self.client.get("/review").text
        self.assertIn('class="stmt reported"', review)
        self.assertIn("Reported by Mission Local; words are a named person at the donor, quoted", review)


class CardQuote(SiteCase):
    def quote_on_page(self, text):
        found = re.search(r'<div class="quote">(.*?)</div>', text, re.S).group(1)
        return html.unescape(re.sub(r"</?mark>", "", found))

    def set_card_quote(self, slug, text):
        with db.session(write=True) as conn:
            card = conn.execute("SELECT card FROM pairings WHERE slug = ?", (slug,)).fetchone()["card"]
            card["quote"]["text"] = text
            conn.execute("UPDATE pairings SET card = ? WHERE slug = ?", (db.json_value(card), slug))

    def warnings(self, emit):
        return [c for c in emit.call_args_list if c.args and c.args[0] == "warning"]

    def test_the_card_shows_the_stored_transcript_text_whatever_the_card_copy_says(self):
        slug = "dorsey-poa-inclusionary"
        stored = self.one("SELECT quote_text FROM pairings WHERE slug = ?", slug)["quote_text"]
        self.assertEqual(self.quote_on_page(self.client.get("/pairings/" + slug).text), '"%s"' % stored)
        for tampered in (stored + " ", " " + stored, stored.replace(" ", "  ", 1), stored[:-1], stored + ".",
                         stored.swapcase(), stored.replace(" ", "\u00a0", 1)):
            self.assertNotEqual(tampered, stored)
            self.set_card_quote(slug, tampered)
            with mock.patch.object(cards.logs, "emit") as emit:
                page = self.client.get("/pairings/" + slug).text
            self.assertEqual(self.quote_on_page(page), '"%s"' % stored, msg=repr(tampered))
            self.assertIn("Shown as the stored transcript has it", page)
            logged = self.warnings(emit)
            self.assertEqual(len(logged), 1)
            self.assertEqual(logged[0].kwargs["slug"], slug)

    def test_an_untouched_card_shows_no_note_and_logs_nothing(self):
        with mock.patch.object(cards.logs, "emit") as emit:
            page = self.client.get("/pairings/lurie-poa-budget").text
        self.assertNotIn("Shown as the stored transcript has it", page)
        self.assertEqual(self.warnings(emit), [])


if __name__ == "__main__":
    unittest.main()
