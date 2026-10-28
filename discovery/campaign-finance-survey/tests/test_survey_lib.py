import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

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


if __name__ == "__main__":
    unittest.main()
