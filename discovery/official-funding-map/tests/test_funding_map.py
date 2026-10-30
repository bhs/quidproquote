import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import build_map as bm  # noqa: E402
import fmap_lib as fl  # noqa: E402


class Names(unittest.TestCase):
    def setUp(self):
        self.fams = bm.jload("families.json")["families"]

    def test_bare_sf_forward_is_the_chambers_by_id(self):
        key, how = fl.family_of(self.fams, "SF Forward", "891575")
        self.assertEqual((key, how), ("sf-chamber", "id"))

    def test_sponsor_words(self):
        self.assertEqual(fl.sponsor_of("San Francisco Forward sponsored by San Francisco Chamber of Commerce"),
                         "SAN FRANCISCO CHAMBER OF COMMERCE")
        self.assertIsNone(fl.sponsor_of("Daniel Lurie for Mayor 2024"))

    def test_other_union_local_is_excluded(self):
        key, _ = fl.family_of(self.fams, "Operating Engineers Stationary Engineers Local 39")
        self.assertIsNone(key)

    def test_same_surname_other_given_name(self):
        self.assertTrue(fl.names_official("Chen", "Chen", "Chyanne"))
        self.assertFalse(fl.names_official("Mike Chen", "Chen", "Chyanne"))

    def test_relations(self):
        rel = lambda t, n: fl.relation_of({"filer_type": t, "filer_name": n})[0]
        self.assertEqual(rel("Primarily Formed Measure", "Mayor Lurie's Yes on H Committee"), "measure")
        self.assertEqual(rel("Primarily Formed Candidate", "GrowSF Opposing Chan for Supervisor"), "opposing")
        self.assertEqual(rel("Candidate or Officeholder", "Matt Dorsey for Supervisor 2026"), "own")
        self.assertEqual(rel("Candidate or Officeholder", "Matt Dorsey for DCCC Member 2024"), "own-other")


class Money(unittest.TestCase):
    def test_repeat_not_counted(self):
        snap = {"committees": [{"filer_nid": "1"}], "a_summary": [], "unitemized": [],
                "a_for_match": [{"filer_nid": "1", "calculated_date": "2026-01-01T00:00:00", "calculated_amount": "1000"}],
                "f497": [{"filer_nid": "1", "calculated_date": "2026-01-01T00:00:00", "calculated_amount": "1000"},
                         {"filer_nid": "1", "calculated_date": "2026-01-02T00:00:00", "calculated_amount": "2000"}]}
        st = bm.committee_stats(snap)["1"]
        self.assertEqual((st["h24_repeat_n"], st["h24_only_n"], st["h24_only_sum"]), (1, 1, 2000.0))


class Pairings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = bm.load_all()
        cls.indep = bm.independent_for(cls.data)
        cls.pairs = bm.build_pairings(cls.data, cls.indep)

    def test_at_least_five_complete_pairings(self):
        self.assertGreaterEqual(len(self.pairs), 5)
        for p in self.pairs:
            self.assertTrue(p["quote"]["text"])
            self.assertTrue(p["statements"])
            for s in p["statements"]:
                self.assertTrue(s["url"].startswith("http") and s["retrieved"])
            self.assertTrue(p["money"]["per"])
            self.assertTrue(p["cues"])

    def test_quotes_verbatim(self):
        for p in self.pairs:
            rows = fl.load_rows(bm.DATA, p["pk"]["meeting_id"])
            self.assertTrue(fl.is_verbatim(rows, p["quote"]["text"]))

    def test_no_causal_words_in_text(self):
        text = bm.render_pairings_md(self.pairs, self.data["snap"]).lower()
        for w in ("because of the money", "in return", "bought", "paid for", "caused", "quid pro quo", "payback"):
            self.assertNotIn(w, text)


class Sources(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = bm.load_all()
        cls.map_md = open(os.path.join(bm.HERE, "funding-map.md"), encoding="utf-8").read()

    def test_every_statement_has_link_and_date(self):
        for s in self.data["prio"].values():
            self.assertTrue(s["url"].startswith("http") and s["retrieved"] and s["text"])

    def test_families_with_statements_include_blueprint_realtors_and_apartment_association(self):
        fams = {s["family"] for s in self.data["prio"].values()}
        for key in ("blueprint", "sf-realtors", "sf-apartment-association"):
            self.assertIn(key, fams)

    def test_every_family_has_an_own_statement_or_a_reported_priority(self):
        own = {s["family"] for s in self.data["prio"].values()}
        reported = {s["family"] for s in self.data["reported"]}
        for f in self.data["fams"]:
            self.assertIn(f["key"], own | reported, f["key"])

    def test_reported_priorities_are_sourced_short_and_kept_apart(self):
        keys = {f["key"] for f in self.data["fams"]}
        ids = set()
        for r in self.data["reported"]:
            self.assertIn(r["family"], keys)
            self.assertNotIn(r["id"], ids)
            ids.add(r["id"])
            self.assertTrue(r["url"].startswith("http") and r["retrieved"] and r["outlet"] and r["speaker"] and r["read"])
            self.assertTrue(r["quote"] and len(r["quote"].split()) < 25, r["id"])
            self.assertNotIn(r["id"], self.data["prio"])
        self.assertIn("### 4a. Priorities reported by others", self.map_md)

    def test_reported_quote_check_ignores_spacing_and_punctuation(self):
        import collect_pages as cp
        self.assertEqual(cp.plain("San Francisco, Proposition H\u00a0 Yes on Prop H"), cp.plain("San Francisco, Proposition HYes on Prop H"))

    def test_govern_for_california_tie_names_its_sources(self):
        fam = next(f for f in self.data["fams"] if f["key"] == "govern-for-california")
        for url in ("governforcalifornia.org/who-we-are", "transparencyusa.org", "missionlocal.org"):
            self.assertIn(url, fam["link_note"])
        self.assertIn("Form 410", fam["link_note"])

    def test_commission_vote_cited_to_the_commission(self):
        self.assertIn("sfethics.org/ethics/2026/08/meeting-summary", self.map_md)
        self.assertNotIn("growsf.org/news", self.map_md)

    def test_committee_control_basis_stated(self):
        self.assertIn("18402(c)(1)", self.map_md)
        self.assertIn("Form 410", self.map_md)


if __name__ == "__main__":
    unittest.main()
