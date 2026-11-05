"""The five pairings the earlier hop showed, rebuilt from the survey's sources with the site's code."""

import unittest

from pairing_site import pipeline, seed

import fmap_lib as fl


class FivePairings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.built = seed.build()
        cls.cards = {p["slug"]: p["card"] for p in cls.built["published"]}

    def test_five_published(self):
        self.assertEqual(len(self.built["published"]), 5)
        self.assertEqual({p["official"] for p in self.built["published"]},
                         {"Daniel Lurie", "Matt Dorsey", "Bilal Mahmood", "Shamann Walton"})

    def test_every_quote_is_word_for_word_with_meeting_date_and_time(self):
        for p in self.built["published"]:
            rows = fl.load_rows(seed.sources.OFM_DATA, p["meeting_id"])
            self.assertTrue(fl.is_verbatim(rows, p["quote_text"]))
            q = p["card"]["quote"]
            self.assertTrue(q["meeting"] and q["date"] and q["first_stamp"] and q["transcript_url"].startswith("https://"))

    def test_speaker_credit_has_support_and_doubt(self):
        for card in self.cards.values():
            credit = card["speaker_credit"]
            self.assertIn(credit["doubt"], ("low", "medium", "high"))
            self.assertTrue(credit["support"] and credit["cue_rows"] and credit["role"])

    def test_donor_words_have_link_and_retrieval_date(self):
        for card in self.cards.values():
            for s in card["donor"]["statements"]:
                self.assertTrue(s["url"].startswith("http") and s["retrieved"] and s["text"])

    def test_money_by_committee_and_filing_without_double_counting(self):
        lurie = self.cards["lurie-chamber-muni"] if "lurie-chamber-muni" in self.cards else next(
            c for c in self.cards.values() if c["official"]["name"] == "Daniel Lurie" and "Chamber" in c["donor"]["name"])
        line = lurie["money"]["committees"][0]
        self.assertEqual(line["schedule_a_total"], 499000.0)
        self.assertEqual(sum(r["amount"] for r in line["rows_detail"]), 499000.0)
        self.assertEqual(len(line["repeats_detail"]), 2)  # 24-hour repeats are listed, not counted
        self.assertTrue(all(r["filing_date"] and r["filing_id"] for r in line["rows_detail"]))
        mahmood = next(c for c in self.cards.values() if c["official"]["name"] == "Bilal Mahmood")
        self.assertEqual(sorted(m["schedule_a_total"] for m in mahmood["money"]["committees"]), [7500.0, 10500.0])

    def test_no_cause_is_claimed(self):
        for card in self.cards.values():
            self.assertEqual(card["reading"]["cause"], "No cause is claimed.")
            text = " ".join([card["reading"]["in_common"], card["reading"]["differs"]]).lower()
            for word in ("because of the money", "in return", "bought", "quid pro quo", "in exchange for"):
                self.assertNotIn(word, text)

    def test_queue_and_dropped_pairs_are_seeded_with_reasons(self):
        self.assertTrue(self.built["pending"])
        self.assertTrue(self.built["dropped"])
        self.assertTrue(all(d["reason"] and d["reason_kind"] for d in self.built["dropped"]))


class Shortlist(unittest.TestCase):
    def test_passages_are_in_credited_turns_and_verbatim(self):
        built = seed.build()
        data = built["data"]
        transcripts = [pipeline.Transcript(m) for m in built["meetings"]]
        pairs = pipeline.funded_pairs(built["snap"])
        prios = pipeline.group_priorities([dict(s) for s in data["prio"].values()])
        cands, total, _ = pipeline.shortlist(transcripts, pairs, prios, set(), 25)
        self.assertTrue(cands)
        self.assertLessEqual(len(cands), 25)
        for c in cands:
            self.assertIn(c["doubt"], ("low", "medium", "high"))
            self.assertTrue(fl.is_verbatim(c["transcript"].rows, c["passage"]["text"]))
        again, _, _ = pipeline.shortlist(transcripts, pairs, prios, {c["key"] for c in cands}, 500)
        self.assertFalse({c["key"] for c in cands} & {c["key"] for c in again})


if __name__ == "__main__":
    unittest.main()
