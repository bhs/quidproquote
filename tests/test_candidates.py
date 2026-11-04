import json
import unittest

from pairing_site import candidates, db, fetcher, money, review

from . import support


class Terms(unittest.TestCase):
    def test_measures_are_read_from_the_words(self):
        self.assertEqual(candidates.derive_measures("Proposition H - Parcel Tax", "Vote NO on Prop I and Measure J."),
                         ["Prop H", "Prop I", "Prop J"])

    def test_terms_match_whole_words_and_prefixes(self):
        rx = candidates.term_rx(["PROP I", "LAYOFF*"])
        self.assertTrue(rx.search("ON PROP I AND LAYOFFS"))
        self.assertFalse(rx.search("PROPOSITION INFRA"))


class Finder(unittest.TestCase):
    def setUp(self):
        self.conn, self.ids = support.make_db()

    def test_only_the_funded_officials_turn_gives_a_candidate(self):
        rows = self.conn.execute("SELECT c.*, o.name FROM candidates c JOIN officials o ON o.id=c.official_id").fetchall()
        self.assertEqual([r["name"] for r in rows], ["Matt Dorsey"])  # Wong spoke of the same words but is not funded by the donor
        c = rows[0]
        self.assertEqual(c["status"], "pending")
        self.assertEqual(c["doubt"], "low")
        self.assertIn("PARCEL TAX", json.loads(c["hits"]))
        self.assertEqual(json.loads(c["priority_ids"]), [self.ids["priority"]])
        self.assertIn(c["text"], " ".join(t for _, t in support.MEETING))
        self.assertEqual(json.loads(c["cue_lines"])[0][0], "00:00:09")

    def test_no_priority_no_candidate(self):
        conn, _ = support.make_db(with_priority=False)
        self.assertEqual(conn.execute("SELECT COUNT(*) AS n FROM candidates").fetchone()["n"], 0)

    def test_no_money_no_candidate(self):
        conn, ids = support.make_db(with_priority=False)
        conn.execute("DELETE FROM contributions")
        review.save_priority(conn, support.priority_form(ids["donor"]))
        self.assertEqual(conn.execute("SELECT COUNT(*) AS n FROM candidates").fetchone()["n"], 0)

    def test_a_remark_that_names_nothing_of_the_priority_is_not_a_candidate(self):
        conn, ids = support.make_db(with_priority=False)
        review.save_priority(conn, support.priority_form(ids["donor"], section="", words="The union backs Prop Z strongly.",
                                                         phrases="fireworks"))
        self.assertEqual(conn.execute("SELECT COUNT(*) AS n FROM candidates").fetchone()["n"], 0)

    def test_a_second_scan_adds_nothing_and_keeps_decisions(self):
        cand = self.conn.execute("SELECT id FROM candidates").fetchone()["id"]
        review.reject(self.conn, cand, "not on the subject")
        self.assertEqual(candidates.scan(self.conn), 0)
        self.assertEqual(self.conn.execute("SELECT status FROM candidates WHERE id=?", (cand,)).fetchone()["status"], "rejected")

    def test_a_new_transcript_is_searched_when_stored(self):
        rows = [("00:00:01", ">> SUPERVISOR DORSEY THANK YOU. THE PARCEL TAX IS ON THE BALLOT.")] + \
               [("00:00:%02d" % i, "FILLER WORDS HERE") for i in range(2, 6)]
        fetcher.store_meeting(self.conn, 900002, "Board of Supervisors", "2026-07-21", rows)
        self.assertEqual(candidates.scan(self.conn, meeting_ids=[900002]), 1)

    def test_money_for_a_pair_is_per_committee_and_counts_each_gift_once(self):
        dorsey = self.conn.execute("SELECT id FROM officials WHERE name='Matt Dorsey'").fetchone()["id"]
        pm = money.pair_money(self.conn, dorsey, self.ids["donor"])
        self.assertEqual(list(pm["per"]), [support.DORSEY_OWN])
        c = pm["per"][support.DORSEY_OWN]
        self.assertEqual(c["a_sum"], 750.0)           # the other giver's $999 is not the donor's
        self.assertEqual(len(c["repeat"]), 1)         # the 24-hour report repeating the $250 row is listed, not counted
        self.assertEqual(c["only_sum"], 100.0)        # the 24-hour report with no Schedule A row is apart
        self.assertEqual(money.funded_official_ids(self.conn, self.ids["donor"]), {dorsey})


if __name__ == "__main__":
    unittest.main()
