import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import ff_lib as ff  # noqa: E402
import fmap_lib as fl  # noqa: E402
import legistar as lg  # noqa: E402
import run  # noqa: E402

CAUSAL = ("because of the money", "in return", "bought", "paid for", "influence", "caused", "quid pro quo",
          "in exchange for the", "payback", "pay-to-play", "pay to play")


def doc_of(text):
    """A Doc of one caption row per sentence, stamped one second apart."""
    rows = [("00:00:%02d" % i, t.strip()) for i, t in enumerate(text.split("|"))]
    return ff.Doc(rows)


class Cues(unittest.TestCase):
    def test_opener_roll_call_and_mention(self):
        d = doc_of(">> SUPERVISOR DORSEY THANK YOU PRESIDENT. I WANT TO THANK SUPERVISOR WONG FOR THIS. "
                   "ON THE ROLL SUPERVISOR WALTON WALTON I")
        regs = ff.find_regions(d)
        self.assertEqual([r["official"] for r in regs], ["Matt Dorsey"])  # Wong is only mentioned, Walton only answers a roll
        self.assertIn("SUPERVISOR WONG", d.text[regs[0]["start"]:regs[0]["end"]])
        self.assertNotIn("WALTON", d.text[regs[0]["start"]:regs[0]["end"]])

    def test_region_runs_to_next_cue_and_doubt_is_low(self):
        d = doc_of("GOOD AFTERNOON. >> SUPERVISOR MELGAR THANK YOU MR. PRESIDENT. COLLEAGUES, I AM EXCITED ABOUT THE "
                   "HOUSING TRUST FUND.|IT WILL SECURE FUNDING.|>> SUPERVISOR WONG THANK YOU. COLLEAGUES, HELLO.")
        regs = ff.find_regions(d)
        self.assertEqual([r["official"] for r in regs], ["Myrna Melgar", "Alan Wong"])
        self.assertTrue(regs[0]["bounded"])
        subj = {"anchor": ["HOUSING TRUST FUND"], "topic": []}
        ps = ff.candidate_passages(d, regs[0], subj)
        self.assertEqual(len(ps), 1)
        self.assertEqual(ps[0]["tier"], "specific")
        self.assertEqual(ff.credit_tier(d, regs[0], ps[0]["start"])[0], "low")
        self.assertIn(ps[0]["text"], d.text)

    def test_garbled_spelling_is_never_low(self):
        d = doc_of(">> SUPERVISOR SARDAR THANK YOU. COLLEAGUES, THE PARCEL TAX.|>> SUPERVISOR WONG THANK YOU.")
        reg = ff.find_regions(d)[0]
        p = ff.candidate_passages(d, reg, {"anchor": ["PARCEL TAX"], "topic": []})[0]
        self.assertEqual(ff.credit_tier(d, reg, p["start"])[0], "medium")

    def test_chan_is_capped_at_medium_without_a_district_cue(self):
        d = doc_of(">> SUPERVISOR CHAN THANK YOU. COLLEAGUES, THE PARCEL TAX.|>> SUPERVISOR WONG THANK YOU.")
        reg = ff.find_regions(d)[0]
        p = ff.candidate_passages(d, reg, {"anchor": ["PARCEL TAX"], "topic": []})[0]
        self.assertEqual(ff.credit_tier(d, reg, p["start"])[0], "medium")

    def test_a_self_introduction_closes_a_chairs_turn(self):
        d = doc_of(">> CHAIR DORSEY THANK YOU. COLLEAGUES, WELCOME.|>> GOOD MORNING. MY NAME IS ANN LEE AND I SPEAK ON FIREWORKS.")
        reg = ff.find_regions(d)[0]
        self.assertNotIn("FIREWORKS", d.text[reg["start"]:reg["end"]])

    def test_mayor_opening_remarks_are_one_region(self):
        d = doc_of("WELCOME, MR. MAYOR. DO YOU HAVE ANY OPENING|REMARKS? I DO. GOOD AFTERNOON. MUNI RIDERSHIP IS UP.|>> THANK YOU, MAYOR LURIE. NEXT.")
        reg = [r for r in ff.find_regions(d) if r["kind"] == "mayor-opening"]
        self.assertEqual(len(reg), 1)
        self.assertIn("MUNI RIDERSHIP", d.text[reg[0]["start"]:reg[0]["end"]])

    def test_terms_match_whole_words_and_prefixes(self):
        rx = ff.term_rx(["PROP I", "LAYOFF*"])
        self.assertTrue(rx.search("ON PROP I AND LAYOFFS"))
        self.assertFalse(rx.search("PROPOSITION INFRA"))


class Minutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ff.DATA, "minutes", "52849.txt"), encoding="utf-8") as f:
            cls.mn = ff.parse_minutes(f.read())

    def test_votes_motions_and_sponsors_are_read(self):
        self.assertEqual(len(self.mn["present"]), 11)
        amend = [v for v in self.mn["votes"] if v["mover"] == "Fielder"][0]
        self.assertEqual(amend["noes"], ["Dorsey", "Mandelman", "Sauter", "Sherrill", "Wong"])
        self.assertEqual(len(amend["ayes"]), 6)
        self.assertTrue(any(s["primary"] == "Melgar" for s in self.mn["sponsors"]))

    def test_a_stated_no_is_confirmed_by_the_noes(self):
        rows = fl.load_rows(ff.DATA, 52849)
        q = fl.extract_quote(rows, "01:47:19", "01:48:25", "COLLEAGUES, I WILL RESPECTFULLY BE VOTING NO", "MAKING HOUSING PRODUCTION FEASIBLE.")
        self.assertEqual(ff.check_minutes(self.mn, "Matt Dorsey", q["text"])["status"], "confirmed")

    def test_a_stated_yes_against_the_noes_is_a_conflict(self):
        out = ff.check_minutes(self.mn, "Matt Dorsey", "I WILL BE SUPPORTING THIS AMENDMENT OF THE MISSION AREA PLAN FOR AFFORDABLE HOUSING ONSITE")
        self.assertEqual(out["status"], "conflict")

    def test_an_official_the_minutes_never_name_is_a_conflict(self):
        mn = ff.parse_minutes("Members Present: Connie Chan, Matt Dorsey\n\nThe Board of Supervisors met.")
        self.assertEqual(ff.check_minutes(mn, "Alan Wong", "ANYTHING AT ALL HERE")["status"], "conflict")

    def test_the_mayors_address_is_confirmed(self):
        self.assertEqual(ff.check_minutes(self.mn, "Daniel Lurie", "MUNI WEEKEND RIDERSHIP")["status"], "confirmed")

    def test_no_minutes_is_said(self):
        self.assertEqual(ff.check_minutes(None, "Alan Wong", "X")["status"], "no_minutes")

    def test_names_wrapping_over_lines(self):
        self.assertEqual(ff.read_names("Chan, Chen, Dorsey, \nWong\n\nNoes: 4 - Chan", 4), ["Chan", "Chen", "Dorsey", "Wong"])


class Money(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snap, cls.fams = ff.load_snapshot()

    def test_funded_pairs_cover_the_funding_map(self):
        pairs = ff.funded_pairs(self.snap)
        self.assertGreaterEqual(len(pairs), 60)
        self.assertTrue(pairs[("Bilal Mahmood", "govern-for-california")]["tied"])

    def test_totals_are_per_committee_and_repeats_not_counted(self):
        m = ff.pair_money(self.snap, "Matt Dorsey", "sf-poa")
        totals = sorted(c["a_sum"] for c in m["per"].values())
        self.assertEqual(totals, [500.0, 7500.0])
        for c in m["per"].values():
            self.assertEqual(c["a_sum"], sum(float(r["calculated_amount"]) for r in c["a"]))
        self.assertEqual(sum(len(c["repeat"]) for c in m["per"].values()), 1)

    def test_a_row_repeated_in_another_filing_is_dropped_once(self):
        snap = {"committees": [{"filer_nid": "1", "official": "A", "relation": "own", "filer_name": "A for X",
                                "filer_type": "Candidate or Officeholder"}],
                "family_rows": {"f": [
                    {"filer_nid": "1", "form_type": "A", "calculated_date": "2026-01-01T00:00:00", "calculated_amount": "500",
                     "filing_id_number": "10", "filing_date": "2026-02-01T00:00:00", "filing_version": "1", "ln": "Org"},
                    {"filer_nid": "1", "form_type": "A", "calculated_date": "2026-01-01T00:00:00", "calculated_amount": "500",
                     "filing_id_number": "11", "filing_date": "2026-03-01T00:00:00", "filing_version": "2", "ln": "Org"}]}}
        m = ff.pair_money(snap, "A", "f")
        self.assertEqual(list(m["per"].values())[0]["a_sum"], 500.0)
        self.assertEqual(len(m["dropped"]), 1)


class Legistar(unittest.TestCase):
    def test_calendar_rows(self):
        page = ('<table><tr><td><a>Board of Supervisors</a></td><td>7/14/2026</td><td>2:00 PM</td><td>Chambers</td>'
                '<td><a href="MeetingDetail.aspx?ID=1&amp;GUID=A">Details</a></td>'
                '<td><a href="View.ashx?M=M&amp;ID=1&amp;GUID=A">Minutes</a></td>'
                '<td><a href="Transcript.aspx?ID1=52849&amp;G=1">Transcript</a></td></tr></table>')
        rows = lg.parse_calendar(page)
        self.assertEqual((rows[0]["date"], rows[0]["transcript_id"]), ("2026-07-14", 52849))
        self.assertTrue(rows[0]["minutes_url"].startswith("https://sfgov.legistar.com/View.ashx?M=M"))

    def test_granicus_feed(self):
        xml = ("<item><title>BOS Board of Supervisors - Regular Meeting dated Tuesday, 14 July 2026 has been archived"
               "</title><link>https://sanfrancisco.granicus.com/MediaPlayer.php?view_id=10&amp;clip_id=52849</link></item>")
        self.assertEqual(lg.parse_rss(xml, "Board of Supervisors")[0]["transcript_id"], 52849)

    def test_a_transcript_with_no_captions_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = os.environ.get("FF_CACHE_DIR")
            os.environ["FF_CACHE_DIR"] = tmp
            try:
                with mock.patch.object(lg, "get_text", return_value="<html></html>"):
                    with self.assertRaises(lg.FetchError):
                        lg.fetch_transcript(1)
            finally:
                if old is None:
                    del os.environ["FF_CACHE_DIR"]
                else:
                    os.environ["FF_CACHE_DIR"] = old

    def test_identify_reads_date_and_body(self):
        rows = [("00:00:01", "WELCOME TO THE JULY 14TH 2026 REGULAR MEETING OF THE SAN FRANCISCO BOARD OF SUPERVISORS.")]
        self.assertEqual(lg.identify(rows), ("2026-07-14", "Board of Supervisors"))


class Pairings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        run.main(["--offline", "--out", cls.tmp])
        with open(os.path.join(cls.tmp, "results.json"), encoding="utf-8") as f:
            cls.res = json.load(f)

    def test_five_complete_pairings(self):
        self.assertGreaterEqual(len(self.res["pairings"]), 5)
        self.assertEqual(self.res["metrics"]["pairings_complete"], len(self.res["pairings"]))

    def test_every_quote_is_word_for_word_in_its_transcript(self):
        for p in self.res["pairings"]:
            rows = fl.load_rows(ff.DATA, p["quote"]["meeting_id"])
            self.assertTrue(fl.is_verbatim(rows, p["quote"]["text"]), p["id"])
            stamps = {s for s, _ in rows}
            self.assertIn(p["quote"]["first_stamp"], stamps)

    def test_money_is_per_committee_with_filings_and_no_cross_committee_total(self):
        for p in self.res["pairings"]:
            for c in p["money"]["per_committee"]:
                self.assertTrue(c["filings"])
                self.assertAlmostEqual(c["schedule_a_total"], sum(r["amount"] for r in c["rows"]))
            self.assertNotIn("total_all_committees", p["money"])

    def test_every_funded_pair_has_an_outcome_and_a_reason(self):
        self.assertEqual(len(self.res["pairs"]), self.res["metrics"]["funded_pairs"])
        for r in self.res["pairs"]:
            self.assertTrue(r["status"] and r["reason"])

    def test_every_review_matches_a_candidate(self):
        self.assertEqual(self.res["stale_reviews"], [])

    def test_no_text_claims_a_cause(self):
        text = (open(os.path.join(self.tmp, "pairings.md"), encoding="utf-8").read()
                + open(os.path.join(self.tmp, "results.md"), encoding="utf-8").read()).lower()
        for w in CAUSAL:
            self.assertNotIn(w, text)

    def test_each_pairing_says_no_cause_is_claimed(self):
        text = open(os.path.join(self.tmp, "pairings.md"), encoding="utf-8").read()
        self.assertEqual(text.count("No cause is claimed."), len(self.res["pairings"]))

    def test_no_two_pairings_share_a_quote(self):
        keys = [(p["quote"]["meeting_id"], p["official"], p["quote"]["first_stamp"]) for p in self.res["pairings"]]
        self.assertEqual(len(keys), len(set(keys)))

    def test_the_earlier_pairings_are_all_accounted_for(self):
        self.assertEqual(len(self.res["earlier_pairings_check"]), 5)


if __name__ == "__main__":
    unittest.main()
