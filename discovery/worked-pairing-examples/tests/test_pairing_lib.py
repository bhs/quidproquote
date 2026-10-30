import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)

import build_pairings as bp  # noqa: E402
import money as mn  # noqa: E402
import pairing_lib as pl  # noqa: E402

ROWS = [("00:00:01", "THANK YOU, MADAM CLERK."), ("00:00:05", ">> SUPERVISOR MELGAR THANK YOU."),
        ("00:00:09", "THIS IS ONE SENTENCE. >> AND THIS"), ("00:00:12", "IS ANOTHER ONE.")]


class Quotes(unittest.TestCase):
    def test_extract_drops_leading_mark_and_keeps_words(self):
        q = pl.extract_quote(ROWS, "00:00:09", "00:00:12", begin_at="AND THIS", end_at="ANOTHER ONE.")
        self.assertEqual(q["text"], "AND THIS IS ANOTHER ONE.")
        self.assertEqual((q["first_stamp"], q["last_stamp"]), ("00:00:09", "00:00:12"))
        self.assertTrue(pl.is_verbatim(ROWS, q["text"]))

    def test_missing_phrase_or_rows_raise(self):
        with self.assertRaises(ValueError):
            pl.extract_quote(ROWS, "00:00:01", "00:00:05", end_at="NOT THERE")
        with self.assertRaises(ValueError):
            pl.extract_quote(ROWS, "01:00:00", "01:00:05")
        with self.assertRaises(ValueError):
            pl.cue_rows(ROWS, ["09:09:09"])

    def test_text_not_in_transcript_is_not_verbatim(self):
        self.assertFalse(pl.is_verbatim(ROWS, "THIS IS ANOTHER SENTENCE."))


class Money(unittest.TestCase):
    COMMITTEES = [{"filer_nid": "1", "filer_name": "A for Supervisor 2024", "filer_type": "Candidate or Officeholder",
                   "status": "ACTIVE", "role": "own"}]

    def row(self, form, date, amount, memo=False, name="DONOR"):
        return {"filer_nid": "1", "form_type": form, "calculated_date": date + "T00:00:00.000",
                "calculated_amount": str(amount), "memo_code": memo, "transaction_last_name": name}

    def test_24_hour_row_repeating_schedule_a_is_not_added(self):
        rows = [self.row("A", "2024-05-01", 500), self.row("F497P1", "2024-05-01", 500),
                self.row("F497P1", "2024-10-20", 250), self.row("A", "2024-06-01", 100, memo=True)]
        s = pl.summarise_money(rows, self.COMMITTEES)["1"]
        self.assertEqual(s["schedule_a_total"], 500.0)
        self.assertEqual(len(s["repeats"]), 1)
        self.assertEqual(s["twentyfour_only_total"], 250.0)
        self.assertEqual(len(s["memo"]), 1)

    def test_rows_of_other_committees_are_ignored(self):
        rows = [dict(self.row("A", "2024-05-01", 500), filer_nid="999")]
        self.assertEqual(pl.summarise_money(rows, self.COMMITTEES)["1"]["schedule_a_total"], 0.0)

    def test_committee_roles(self):
        self.assertEqual(pl.committee_role({"filer_type": "Candidate or Officeholder", "filer_name": "X"}), "own")
        self.assertEqual(pl.committee_role({"filer_type": "Primarily Formed Candidate",
                                            "filer_name": "Grow SF PAC Opposing Chan for Supervisor"}), "oppose")
        self.assertEqual(pl.committee_role({"filer_type": "Primarily Formed Candidate",
                                            "filer_name": "United Club Supporting Walton"}), "support")

    def test_query_asks_only_schedule_a_and_24_hour_rows_for_the_committees(self):
        q = pl.build_money_query(mn.DONOR_NAME_WORDS["GrowSF"], ["209865652"])
        self.assertIn("form_type in ('A','F497P1')", q["$where"])
        self.assertIn("'209865652'", q["$where"])
        self.assertIn("upper(transaction_last_name) like '%GROWSF%'", q["$where"])

    def test_independent_expenditure_query_reads_reports_naming_the_candidate(self):
        q = pl.build_independent_query(mn.DONOR_NAME_WORDS["GrowSF"], "Mahmood")
        self.assertIn("form_type in ('F496','F465P3')", q["$where"])
        self.assertIn("upper(candidate_last_name) like '%MAHMOOD%'", q["$where"])
        self.assertIn("upper(filer_name) like '%GROWSF%'", q["$where"])

    def test_candidate_with_the_same_surname_but_another_given_name_is_left_out(self):
        self.assertTrue(pl.names_official("Bilal Mahmood", "Mahmood", "Bilal"))
        self.assertTrue(pl.names_official("MAHMOOD", "Mahmood", "Bilal"))
        self.assertFalse(pl.names_official("Mike Chen", "Chen", "Chyanne"))
        self.assertFalse(pl.names_official("Chenette", "Chen", "Chyanne"))

    def test_independent_expenditures_are_grouped_by_committee_and_office_and_never_repeat(self):
        def ie(form, date, amount, office="Supervisor", filer="7", memo=False):
            return {"filer_nid": filer, "filer_name": "C", "form_type": form, "calculated_date": date + "T00:00:00.000",
                    "calculated_amount": str(amount), "candidate_last_name": "Bilal Mahmood",
                    "office_description": office, "district_number": "5", "memo_code": memo}
        rows = [ie("F496", "2024-10-01", 100), ie("F496", "2024-10-02", 50, memo=True), ie("F465P3", "2024-10-01", 100),
                ie("F465P3", "2024-10-09", 25), ie("F496", "2024-01-01", 10, office="Board Member")]
        groups = pl.summarise_independent(rows, "Mahmood", "Bilal")
        self.assertEqual(len(groups), 2)
        sup = [g for g in groups if g["office"] == "Supervisor"][0]
        self.assertEqual((sup["total"], len(sup["memo"]), len(sup["repeats"]), sup["apart_total"]), (100.0, 1, 1, 25.0))

    def test_name_words_are_checked_against_names_as_filed(self):
        words = mn.DONOR_NAME_WORDS["San Francisco Chamber of Commerce"]
        self.assertTrue(pl.name_matches(words, "SF Forward sponsored by San Francisco Chamber of Commerce"))
        self.assertFalse(pl.name_matches(words, "SAN FRANCISCO BLACK CHAMBER OF COMMERCE"))
        self.assertFalse(pl.name_matches(words, "SAN FRANCISCO FORWARD"))

    def test_census_and_control_queries(self):
        contrib, comm = pl.build_census_queries(mn.NEAR_PATTERNS["GrowSF"])
        self.assertIn("upper(transaction_last_name) like '%GROW SAN FRANCISCO%'", contrib["$where"])
        self.assertIn("upper(filer_name) like '%GROWSF%'", comm["$where"])
        self.assertIn("form_type = 'A'", pl.build_control_query(["1"])["$where"])

    def test_a_failed_query_is_listed_as_a_failure(self):
        money = {"k": {"error": None, "independent": {"error": "down"}, "control": {"error": None}}}
        self.assertEqual(bp.failures(money, {"GrowSF": {"error": "down"}}),
                         ["k (independent expenditures)", "GrowSF (names read)"])

    def test_failed_money_is_said_in_the_write_up(self):
        p = {"n": 1, "donor": "GrowSF", "official": "X", "committees": self.COMMITTEES, "name_words_text": "GROWSF"}
        text = "\n".join(pl.render_money_section(p, {"error": "URLError: down", "rows": []}, "2026-10-30"))
        self.assertIn("The money query failed", text)
        self.assertNotIn("No row found", text)


class TheWorkedPairings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, "picks.json"), encoding="utf-8") as f:
            cls.picks = json.load(f)
        cls.pairs = bp.assemble(cls.picks, os.path.join(ROOT, "data"))

    def test_every_pairing_is_complete(self):
        self.assertGreaterEqual(len(self.pairs), 5)
        for p in self.pairs:
            self.assertTrue(p["quote_text"] and not p["quote_text"].startswith(">"))
            self.assertTrue(p["priority_url"].startswith("http") and p["priority_retrieved"])
            self.assertTrue(p["transcript_url"].startswith("http"))
            self.assertTrue(p["committees"])
            self.assertTrue(p["cue_rows"])
            self.assertIn(p["speaker"]["doubt"], ("low", "medium", "high"))

    def test_quotes_are_verbatim_in_the_transcripts(self):
        for p in self.pairs:
            rows = pl.load_rows(os.path.join(ROOT, "data"), p["meeting_id"])
            self.assertTrue(pl.is_verbatim(rows, p["quote_text"]), p["n"])

    def test_leads_do_not_suggest_a_cause(self):
        for p in self.pairs:
            lead = p["lead"].replace(pl.NO_CAUSATION, "").lower()
            for word in pl.CAUSAL_WORDS:
                self.assertNotIn(word, lead)
            text = (p["overlap"] + p["stance"] + " ".join(p["check_next"])).lower()
            for word in pl.CAUSAL_WORDS:
                self.assertNotIn(word, text)

    def test_unretrieved_money_is_said_not_filled(self):
        text = bp.render(self.pairs, self.picks, {}, None)
        self.assertIn("Not retrieved in this build", text)
        self.assertEqual(text.count("\n### Money "), len(self.pairs))
        self.assertIn("Not retrieved in this build.", "\n".join(pl.render_census(None, ["GrowSF"], None)))


if __name__ == "__main__":
    unittest.main()
