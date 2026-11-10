"""The glance row's pieces: the quote window, the four confidence chips and the backfill."""

import io
import os
import unittest
from unittest import mock

from pairing_site import backfill, db, glance, pipeline, seed

from helpers import temp_database


def card(doubt="low", highlight=("transit",), statements=None, committees=None):
    return {"speaker_credit": {"doubt": doubt, "reason": "The cue names the speaker."}, "highlight": list(highlight),
            "donor": {"statements": statements or [{"kind": "voter guide on the organisation's own site", "section": "Transit"}]},
            "money": {"committees": committees if committees is not None else
                      [{"committee": "Committee A", "kind": "officeholder committee"}]}}


class Window(unittest.TestCase):
    TEXT = ("alpha beta gamma delta " * 30) + "transit " + ("epsilon zeta eta theta " * 30).strip()

    def test_a_short_quote_is_whole(self):
        self.assertEqual(glance.window("a short remark", ["short"]), ("a short remark", False, False))

    def test_the_window_is_exact_whole_words_around_the_first_shared_word(self):
        excerpt, before, after = glance.window(self.TEXT, ["transit"])
        self.assertIn("transit", excerpt)
        self.assertIn(excerpt, self.TEXT)
        self.assertTrue(before and after)
        self.assertLessEqual(len(excerpt), glance.WINDOW + 20)
        index = self.TEXT.index(excerpt)
        self.assertIn(self.TEXT[index - 1], " ")
        self.assertIn((self.TEXT + " ")[index + len(excerpt)], " ")

    def test_without_a_shared_word_the_window_starts_the_quote(self):
        excerpt, before, after = glance.window(self.TEXT, [])
        self.assertTrue(self.TEXT.startswith(excerpt) and not before and after)

    def test_donor_excerpt_ends_at_a_word(self):
        text, cut = glance.shorten("word " * 100)
        self.assertTrue(cut and text.endswith("word") and len(text) <= glance.DONOR_EXCERPT)
        self.assertEqual(glance.shorten("few words"), ("few words", False))

    def test_topic_label_is_the_donors_heading_with_its_page(self):
        c = card(statements=[{"kind": "k", "section": "", "url": "u1"}, {"kind": "k", "section": " Prop H ", "url": "u2"}])
        self.assertEqual(glance.topic_label(c), {"label": "Prop H", "page": "u2", "kind": "k"})
        self.assertIsNone(glance.topic_label(card(statements=[{"kind": "k", "section": "", "url": "u"}])))


class Chips(unittest.TestCase):
    def level(self, c, key):
        return next(x for x in pipeline.confidence(c) if x["key"] == key)

    def test_always_four_chips_in_order_with_a_reason(self):
        chips = pipeline.confidence(card())
        self.assertEqual([c["key"] for c in chips], ["speaker_credit", "topic_match", "donor_priority", "money_tie"])
        self.assertTrue(all(c["reason"] and c["level"] in pipeline.LEVELS and not c["verified"] for c in chips))

    def test_speaker_credit_inverts_the_doubt(self):
        self.assertEqual([self.level(card(d), "speaker_credit")["level"] for d in ("low", "medium", "high")],
                         ["high", "medium", "low"])
        self.assertIn("Doubt in the credit is high", self.level(card("high"), "speaker_credit")["reason"])

    def test_topic_match_follows_the_shared_words(self):
        self.assertEqual(self.level(card(highlight=()), "topic_match")["level"], "low")
        self.assertEqual(self.level(card(highlight=("transit",)), "topic_match")["level"], "medium")
        self.assertEqual(self.level(card(highlight=("transfer tax",)), "topic_match")["level"], "high")
        self.assertIn('"transit"', self.level(card(), "topic_match")["reason"])

    def test_donor_priority_follows_where_the_words_were_found(self):
        news = lambda whose: [{"kind": pipeline.priorities.NEWS, "outlet": "Example Daily", "whose_words": whose}]
        self.assertEqual(self.level(card(), "donor_priority")["level"], "high")
        self.assertEqual(self.level(card(statements=news("donor-quoted")), "donor_priority")["level"], "medium")
        self.assertEqual(self.level(card(statements=news("reporter")), "donor_priority")["level"], "low")
        self.assertIn("Example Daily", self.level(card(statements=news("reporter")), "donor_priority")["reason"])

    def test_money_tie_takes_the_weakest_committee(self):
        own = {"committee": "Own", "kind": "own committee"}
        measure = {"committee": "Measure", "kind": "ballot-measure committee carrying the official's name"}
        other = {"committee": "Other", "kind": "officeholder committee, for another office (School Board)"}
        self.assertEqual(self.level(card(committees=[own]), "money_tie")["level"], "high")
        self.assertEqual(self.level(card(committees=[own, measure]), "money_tie")["level"], "medium")
        self.assertEqual(self.level(card(committees=[own, other]), "money_tie")["level"], "medium")
        self.assertEqual(self.level(card(committees=[]), "money_tie")["level"], "low")
        self.assertIn("Measure", self.level(card(committees=[own, measure]), "money_tie")["reason"])

    def test_verifying_marks_speaker_credit_and_topic_match_only(self):
        c = card()
        marked = pipeline.mark_verified(c)
        self.assertEqual(marked, ["speaker credit", "topic match"])
        self.assertEqual({x["key"] for x in c["chips"] if x["verified"]}, {"speaker_credit", "topic_match"})


class Backfill(unittest.TestCase):
    def test_old_pairings_get_chips_and_checked_ones_are_marked_verified_once(self):
        with mock.patch.dict(os.environ, {"ADMIN_TOKEN": "t", "FETCH_CONTACT_EMAIL": "maintainer@example.org"}), temp_database():
            self.assertEqual(seed.run(reset=True), 0)
            with db.session(write=True) as conn:
                for r in conn.execute("SELECT id, card FROM pairings").fetchall():
                    r["card"].pop("chips")
                    conn.execute("UPDATE pairings SET card = ? WHERE id = ?", (db.json_value(r["card"]), r["id"]))
                conn.execute("UPDATE pairings SET recording_checked = 1 WHERE slug = 'lurie-chamber-muni'")
            written, verified = backfill.run(io.StringIO())
            self.assertGreaterEqual(written, 5)
            self.assertEqual(verified, 1)
            self.assertEqual(backfill.run(io.StringIO())[1], 0)
            with db.session() as conn:
                rows = conn.execute("SELECT slug, card FROM pairings").fetchall()
                logged = conn.execute("SELECT count(*) AS n FROM audit_log WHERE action = 'chips verified'").fetchone()["n"]
            self.assertTrue(all(len(r["card"]["chips"]) == 4 for r in rows))
            self.assertEqual(logged, 1)
            lurie = next(r for r in rows if r["slug"] == "lurie-chamber-muni")
            self.assertEqual({c["key"] for c in lurie["card"]["chips"] if c["verified"]}, {"speaker_credit", "topic_match"})


if __name__ == "__main__":
    unittest.main()
