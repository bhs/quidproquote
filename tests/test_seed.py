"""The five pairings the Pairings end to end hop showed come out of the same code a maintainer's clicks reach."""

import json
import os
import unittest

from pairing_site import db, pairing_cards, seed

from . import support

EXPECTED = {  # slug: (official, donor, meeting date, transcript time, doubt, Schedule A total per committee)
    "lurie-sf-chamber-2026-07-14-000346": ("Daniel Lurie", "San Francisco Chamber of Commerce", "2026-07-14", "00:03:46", "low",
                                           {"Mayor Lurie's Yes on H Committee": "$499,000"}),
    "lurie-sf-poa-2026-07-14-000436": ("Daniel Lurie", "San Francisco Police Officers Association", "2026-07-14", "00:04:36", "low",
                                       {"Mayor Lurie's Yes on D, E & F Committee": "$10,000"}),
    "dorsey-sf-poa-2026-07-14-014719": ("Matt Dorsey", "San Francisco Police Officers Association", "2026-07-14", "01:47:19", "low",
                                        {"Matt Dorsey for Supervisor 2022": "$500",
                                         "Matt Dorsey for DCCC Member 2024 Officeholder Committee": "$7,500"}),
    "mahmood-govern-for-california-2026-07-15-025231": ("Bilal Mahmood", "Govern For California", "2026-07-15", "02:52:31", "high",
                                                        {"Bilal Mahmood for DCCC Member 2024": "$10,500",
                                                         "Bilal Mahmood for Supervisor 2024": "$7,500"}),
    "walton-seiu-1021-2026-07-14-023958": ("Shamann Walton", "SEIU Local 1021", "2026-07-14", "02:39:58", "low",
                                           {"Committee to Elect Shamann Walton for SF Board of Education 2012": "$500",
                                            "Shamann Walton for School Board 2014": "$500"}),
}


class Seed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = support.make_env()
        os.environ.update(cls.env)
        assert seed.main() == 0
        cls.conn = db.connect(cls.env["DATABASE_PATH"])
        cls.cards = {c["slug"]: c for c in pairing_cards.approved_cards(cls.conn)}

    def test_the_five_pairings_are_cards(self):
        self.assertEqual(set(self.cards), set(EXPECTED))

    def test_each_card_has_what_the_hop_showed(self):
        for slug, (official, donor, date, stamp, doubt, totals) in EXPECTED.items():
            card = self.cards[slug]
            self.assertEqual(card["official"]["name"], official)
            self.assertIn(donor.lower(), card["donor"]["name"].lower())
            q = card["quote"]
            self.assertEqual((q["date"], q["first_stamp"]), (date, stamp))
            self.assertTrue(q["meeting"] and q["transcript_url"].startswith("https://sfgov.legistar.com/Transcript.aspx?ID1="))
            self.assertEqual(card["speaker_credit"]["doubt"], doubt)
            self.assertTrue(card["speaker_credit"]["cue_lines"])
            for s in card["donor"]["statements"]:
                self.assertTrue(s["url"].startswith("https://") and s["retrieved"] and s["text"])
            self.assertEqual({m["committee"]: m["schedule_a_total_text"] for m in card["money"]["committees"]}, totals)
            for m in card["money"]["committees"]:
                self.assertTrue(all(r["filing"] and r["filing_date"] for r in m["filing_rows"]))
                counted = sum(float(r["amount"].replace("$", "").replace(",", "")) for r in m["filing_rows"] if r["counted"])
                self.assertEqual(fmt(counted), m["schedule_a_total_text"])

    def test_every_quote_is_word_for_word_in_the_transcript(self):
        for card in self.cards.values():
            mid = int(card["quote"]["transcript_url"].rsplit("=", 1)[1])
            whole = " ".join(r["text"] for r in self.conn.execute("SELECT text FROM lines WHERE meeting_id=? ORDER BY idx", (mid,)))
            self.assertIn(card["quote"]["text"], whole)
            path = os.path.join(seed.SEED, "transcripts", "%d.tsv" % mid)
            with open(path, encoding="utf-8") as f:
                published = " ".join(" ".join(ln.rstrip("\n").partition("\t")[2].split()) for ln in f)
            self.assertIn(card["quote"]["text"], published)

    def test_24_hour_repeats_are_listed_but_not_counted(self):
        card = self.cards["mahmood-govern-for-california-2026-07-15-025231"]
        dccc = card["money"]["committees"][0]
        self.assertEqual(dccc["repeats_not_counted"], 4)
        self.assertEqual(len([r for r in dccc["filing_rows"] if not r["counted"]]), 4)

    def test_nothing_in_a_card_says_the_money_caused_the_words(self):
        from pairing_site.review import CAUSAL
        for card in self.cards.values():
            text = json.dumps(card).lower()
            self.assertEqual([w for w in CAUSAL if w in text], [], card["slug"])
            self.assertEqual(card["reading"]["cause"], "No cause is claimed.")

    def test_the_rest_wait_in_the_queue_unpublished(self):
        pending = self.conn.execute("SELECT COUNT(*) AS n FROM candidates WHERE status='pending'").fetchone()["n"]
        self.assertGreater(pending, 5)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) AS n FROM candidates WHERE status='approved'").fetchone()["n"], 5)

    def test_the_seed_does_not_fill_a_database_that_has_donors(self):
        self.assertEqual(seed.main(), 1)


def fmt(x):
    return "$" + "{:,.0f}".format(x)


if __name__ == "__main__":
    unittest.main()
