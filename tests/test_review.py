import unittest

from pairing_site import candidates, pairing_cards, review

from . import support


class PriorityForm(unittest.TestCase):
    def setUp(self):
        self.conn, self.ids = support.make_db(with_priority=False)

    def refused(self, **over):
        with self.assertRaises(review.FormError) as cm:
            review.save_priority(self.conn, support.priority_form(self.ids["donor"], **over))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) AS n FROM priorities").fetchone()["n"], 0)
        return " ".join(cm.exception.errors)

    def test_refused_without_the_exact_words(self):
        self.assertIn("exact words", self.refused(words=""))

    def test_refused_without_a_source_type(self):
        self.assertIn("source type", self.refused(source_type=" "))

    def test_refused_without_a_url_or_with_a_bad_one(self):
        self.assertIn("URL", self.refused(url=""))
        self.assertIn("URL", self.refused(url="example.org/page"))

    def test_refused_without_a_retrieval_date_or_one_in_the_future(self):
        self.assertIn("retrieval date", self.refused(retrieved=""))
        self.assertIn("future", self.refused(retrieved="2999-01-01"))

    def test_refused_when_nothing_is_given_to_look_for(self):
        self.assertIn("measure", self.refused(section="", words="The union supports better service for riders.", phrases=""))

    def test_saved_with_all_four_and_measures_are_read_from_the_words(self):
        pid = review.save_priority(self.conn, support.priority_form(self.ids["donor"]))
        row = self.conn.execute("SELECT * FROM priorities WHERE id=?", (pid,)).fetchone()
        self.assertIn("Prop H", row["measures"])
        self.assertEqual(row["retrieved"], "2026-10-01")
        self.assertEqual(row["url"], "https://example.org/voter-guide")


class Approval(unittest.TestCase):
    def setUp(self):
        self.conn, self.ids = support.make_db()
        self.cand = self.conn.execute("SELECT * FROM candidates").fetchone()

    def test_nothing_is_published_before_approval(self):
        self.assertEqual(pairing_cards.approved_cards(self.conn), [])

    def test_approval_publishes_the_exact_words_as_a_card(self):
        slug = review.approve(self.conn, self.cand["id"], {"doubt": "medium", "doubt_note": "The cue is two rows up."})
        card = pairing_cards.card_by_slug(self.conn, slug)
        whole = " ".join(t for _, t in support.MEETING)
        self.assertIn(card["quote"]["text"], whole)
        self.assertEqual(card["speaker_credit"]["doubt"], "medium")
        self.assertEqual(card["official"]["name"], "Matt Dorsey")
        self.assertEqual(card["money"]["committees"][0]["schedule_a_total_text"], "$750")
        self.assertEqual(card["quote"]["meeting"], "Board of Supervisors")
        self.assertEqual(card["donor"]["statements"][0]["retrieved"], "2026-10-01")
        self.assertEqual([c["committee"] for c in card["money"]["committees"]], ["Matt Dorsey for Supervisor 2022"])
        self.assertIn("Muni", card["highlight"])

    def test_the_quote_can_be_cut_at_words_the_reviewer_names(self):
        slug = review.approve(self.conn, self.cand["id"], {"begin_at": "COLLEAGUES, TODAY", "end_at": "WHY IT MATTERS."})
        card = pairing_cards.card_by_slug(self.conn, slug)
        self.assertEqual(card["quote"]["text"], "COLLEAGUES, TODAY I SPEAK ABOUT THE PARCEL TAX FOR MUNI OPERATIONS AND WHY IT MATTERS.")
        self.assertEqual(card["quote"]["first_stamp"], "00:00:09")

    def test_a_cut_at_words_not_in_the_turn_is_refused(self):
        with self.assertRaises(review.FormError):
            review.approve(self.conn, self.cand["id"], {"begin_at": "THE WEATHER IS FINE. THANK YOU FOR YOUR TIME AND MORE"})
        self.assertEqual(self.conn.execute("SELECT status FROM candidates").fetchone()["status"], "pending")

    def test_a_cut_that_misses_the_flagged_remark_is_refused(self):
        self.conn.execute("UPDATE candidates SET end_off = start_off + 20")  # the flagged words only
        with self.assertRaises(review.FormError) as cm:
            review.approve(self.conn, self.cand["id"], {"begin_at": "THANK YOU FOR YOUR TIME", "end_at": "COLLEAGUES."})
        self.assertIn("flagged remark", " ".join(cm.exception.errors))

    def test_a_note_that_says_the_money_caused_the_words_is_refused(self):
        with self.assertRaises(review.FormError) as cm:
            review.approve(self.conn, self.cand["id"], {"in_common": "He said it because of the money."})
        self.assertIn("caused", " ".join(cm.exception.errors))

    def test_a_doubt_level_outside_low_medium_high_is_refused(self):
        with self.assertRaises(review.FormError):
            review.approve(self.conn, self.cand["id"], {"doubt": "certain"})

    def test_reject_publishes_nothing_and_cannot_be_approved_after(self):
        review.reject(self.conn, self.cand["id"], "off topic")
        self.assertEqual(pairing_cards.approved_cards(self.conn), [])
        with self.assertRaises(review.FormError):
            review.approve(self.conn, self.cand["id"], {})

    def test_the_doubt_level_can_be_edited_after_approval(self):
        slug = review.approve(self.conn, self.cand["id"], {})
        review.set_doubt(self.conn, self.cand["id"], "high", "Name garbled.")
        self.assertEqual(pairing_cards.card_by_slug(self.conn, slug)["speaker_credit"]["doubt"], "high")

    def test_cut_quote_is_always_a_substring_of_the_transcript(self):
        doc = candidates.load_doc(self.conn, self.ids["meeting"])
        q = review.cut_quote(doc, self.cand, "", "")
        self.assertIn(q["text"], doc.text)


if __name__ == "__main__":
    unittest.main()
