import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import calaccess  # noqa: E402
import survey_lib as lib  # noqa: E402

CHEN = next(o for o in lib.OFFICIALS if o["last"] == "Chen")
CHAN = next(o for o in lib.OFFICIALS if o["last"] == "Chan")
LURIE = next(o for o in lib.OFFICIALS if o["last"] == "Lurie")


class MatchTests(unittest.TestCase):
    def test_roster_is_mayor_and_eleven_supervisors(self):
        self.assertEqual(len(lib.OFFICIALS), 12)
        self.assertEqual(sum(1 for o in lib.OFFICIALS if o["office"] == "Supervisor"), 11)

    def test_strong_match_on_candidate_name(self):
        f = {"candidate_name": "Chan, Connie", "filer_type": "Candidate or Officeholder", "filer_name": "Connie Chan for Supervisor 2024"}
        self.assertEqual(lib.match_filer(CHAN, f), "strong")

    def test_preferred_name_in_parentheses(self):
        f = {"candidate_name": "Chen, Xiao Yan (Chyanne)", "filer_type": "Candidate or Officeholder", "filer_name": "x"}
        self.assertEqual(lib.match_filer(CHEN, f), "strong")

    def test_other_person_same_surname_is_not_matched(self):
        f = {"candidate_name": "Chan, Robert", "filer_type": "Person", "filer_name": "Robert H. Chan"}
        self.assertIsNone(lib.match_filer(CHAN, f))

    def test_measure_committee_naming_mayor_is_weak(self):
        f = {"candidate_name": None, "filer_type": "Primarily Formed Measure", "filer_name": "Mayor Lurie's Yes on H Committee"}
        self.assertEqual(lib.match_filer(LURIE, f), "weak")
        self.assertEqual(lib.classify_committee(f, "weak"), "ballot-measure committee naming the official")

    def test_opposing_committee_is_not_support(self):
        f = {"candidate_name": "Chan, Connie", "filer_type": "Primarily Formed Candidate", "filer_name": "Grow SF PAC Opposing Chan for Supervisor 2024"}
        self.assertEqual(lib.classify_committee(f, "strong"), "primarily formed committee opposing the official")

    def test_dccc_committee_is_other_office(self):
        f = {"candidate_name": "Chan, Connie", "filer_type": "Candidate or Officeholder", "filer_name": "Connie Chan for Democratic County Central Committee 2028"}
        self.assertEqual(lib.classify_committee(f, "strong"), "official's committee for another office")

    def test_ie_name_typo_tolerated_but_not_other_first_name(self):
        self.assertTrue(lib.ie_name_matches(CHAN, "Conne", "Chan"))
        self.assertFalse(lib.ie_name_matches(CHAN, "Doug", "Chan"))
        self.assertFalse(lib.ie_name_matches(CHAN, "Connie", "Chang"))


class IdentityTests(unittest.TestCase):
    def test_org_variants_collapse(self):
        a = lib.normalize_org("PACIFIC GAS AND ELECTRIC COMPANY")
        b = lib.normalize_org("Pacific Gas & Electric")
        self.assertEqual(a, "pacific gas and electric")
        self.assertEqual(b, "pacific gas and electric")

    def test_pac_wording_only_dropped_when_aggressive(self):
        self.assertNotEqual(lib.normalize_org("Recology Inc. PAC"), lib.normalize_org("Recology Inc."))
        self.assertEqual(lib.normalize_org("Recology Inc. PAC", True), lib.normalize_org("Recology Inc.", True))

    def test_person_key_ignores_case_punctuation_and_middle_name(self):
        self.assertEqual(lib.normalize_person("O'Brien", "Mary Ann"), lib.normalize_person("OBRIEN", "mary"))

    def test_zip5(self):
        self.assertEqual(lib.zip5("94110-1234"), "94110")
        self.assertEqual(lib.zip5("941"), "")


class FormatTests(unittest.TestCase):
    def test_soql_quote_escapes(self):
        self.assertEqual(lib.soql_quote("O'Brien"), "'O''Brien'")

    def test_percentile(self):
        self.assertEqual(lib.percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 50), 5)
        self.assertIsNone(lib.percentile([], 50))

    def test_money(self):
        self.assertEqual(lib.money(1234.5), "$1,234")
        self.assertEqual(lib.money(None), "-")


class AmendmentTests(unittest.TestCase):
    @staticmethod
    def sub(nid, date, kind, mech="Electronic"):
        return {"filing_nid": nid, "filing_date": date + "T00:00:00.000", "filing_type": kind, "mechanism_type": mech}

    def test_only_filed_amendments_count_and_cohort_is_by_first_filing(self):
        rows = [
            self.sub("new-amended", "2022-03-01", "FiledOriginal"),
            self.sub("new-amended", "2022-06-10", "FiledAmendment"),
            self.sub("new-amended", "2022-09-01", "FiledAmendment", "Paper"),
            self.sub("new-attach", "2023-01-01", "FiledOriginal"),
            self.sub("new-attach", "2023-02-01", "AttachmentsAdded"),
            self.sub("new-plain", "2024-01-01", "FiledOriginal"),
            # first filed before the cutoff: amended later, but not in the cohort
            self.sub("old", "2021-12-01", "FiledOriginal"),
            self.sub("old", "2022-05-01", "FiledAmendment"),
        ]
        out = lib.summarise_amendments(rows, "2022-01-01")
        self.assertEqual(out["form460_reports_first_filed_since"], 3)
        self.assertEqual(out["reports_with_a_filed_amendment"], 1)
        self.assertEqual(out["filed_amendments_per_amended_report"], {2: 1})
        self.assertEqual(out["reports_with_only_attachments_or_contents_changes"], 1)
        self.assertEqual(out["amended_reports_with_a_paper_amendment"], 1)
        self.assertEqual(out["days_first_to_last_amendment_max"], 184)

    def test_days_between(self):
        self.assertEqual(lib.days_between("2022-01-01", "2022-03-01"), 59)


class CommitteeIdTests(unittest.TestCase):
    TSV = (
        "XREF_FILER_ID\tFILER_ID\tFILER_TYPE\tSTATUS\tEFFECT_DT\tNAML\tNAMF\n"
        "1001001\t1001001\tRECIPIENT COMMITTEE\tACTIVE\t1/1/2020 12:00:00 AM\tOLD NAME\t\n"
        "1001001\t1001001\tRECIPIENT COMMITTEE\tACTIVE\t1/1/2024 12:00:00 AM\tNEW NAME, SPONSORED BY ACME\t\n"
        "999999\t2002002\tRECIPIENT COMMITTEE\tTERMINATED\t5/5/2019 12:00:00 AM\tOTHER PAC\t\n"
    )

    def test_shapes(self):
        self.assertEqual(lib.committee_id_shape("1344506"), "state")
        self.assertEqual(lib.committee_id_shape("C00123456"), "fec")
        self.assertEqual(lib.committee_id_shape("Pending"), "other")

    def test_parse_keeps_latest_name_and_xref(self):
        by_id, by_xref = calaccess.parse_filer_names(self.TSV.splitlines(True))
        self.assertEqual(by_id["1001001"]["name"], "NEW NAME, SPONSORED BY ACME")
        self.assertEqual(by_xref["999999"], "2002002")

    def test_resolve(self):
        by_id, by_xref = calaccess.parse_filer_names(self.TSV.splitlines(True))
        out = lib.resolve_committee_ids(
            {"1001001": 100.0, "9999900": 5.0, "099999": 7.0, "999999": 1.0, "Pending": 50.0, "C00000001": 3.0}, by_id, by_xref)
        self.assertEqual(out["state_ids_found_as_filer_id"], 1)
        self.assertEqual(out["state_ids_found_as_legacy_xref"], 1)
        self.assertEqual(out["state_ids_not_found"], 2)  # 9999900 and 099999 have no record
        self.assertEqual(out["shapes"]["other"]["ids"], 1)
        self.assertEqual(out["shapes"]["fec"]["ids"], 1)
        self.assertEqual(out["found_names_saying_sponsored_by"], 1)


if __name__ == "__main__":
    unittest.main()
