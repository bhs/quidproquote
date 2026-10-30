import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import check_lib as ck  # noqa: E402
import labeller  # noqa: E402

QUOTE = {"meeting_body": "Board of Supervisors", "meeting_date": "2026-07-07", "start": "00:10:00",
         "url": "https://example.org/t", "text": "WE SUPPORT THE HOUSING TRUST FUND", "before": ">> THANK YOU"}
PRIORITY = {"donor": "Donor A", "section": "Prop C", "url": "https://example.org/p", "retrieved": "2026-10-29",
            "text": "Vote yes on C."}


def person(labels, sides=None, speakers=None, ms=None, blind=True):
    return {"labels": labels, "sides": sides or {}, "speakers": speakers or {}, "ms": ms or {}, "ms_hidden": {},
            "file": "x.json"}


class Sheet(unittest.TestCase):
    def test_stable_pick_does_not_depend_on_input_order(self):
        ids = ["a|1", "b|2", "c|3", "d|4", "e|5"]
        self.assertEqual(ck.stable_pick(ids, 3, "s"), ck.stable_pick(list(reversed(ids)), 3, "s"))
        self.assertEqual(len(ck.stable_pick(ids, 10, "s")), 5)

    def test_sample_sheet_strata_and_missing_methods(self):
        props = {"keyword": {"a|1", "b|2", "c|3"}, "anchor": {"c|3", "d|4"}, "embedding": None, "ai_judge": set()}
        looser = {"keyword": {"e|5"}}
        out = ck.sample_sheet(props, looser, ["r|9", "s|9"], per_method=2, per_looser=1, n_random=1)
        self.assertIn("looser:keyword", out["e|5"])
        self.assertTrue(any("random" in v for v in out.values()))
        self.assertTrue(all(not k.startswith("embedding") for v in out.values() for k in v))
        sizes = sum(1 for v in out.values() for s in v if s == "proposed:keyword")
        self.assertEqual(sizes, 2)
        self.assertEqual(out, ck.sample_sheet(props, looser, ["r|9", "s|9"], 2, 1, 1))

    def test_blind_entry_carries_nothing_about_a_method(self):
        e = ck.blind_entry("1@00:10:00|P1", QUOTE, PRIORITY)
        self.assertFalse(ck.leaks_method(e))
        self.assertTrue(ck.leaks_method(dict(e, methods=["keyword"])))
        self.assertTrue(ck.leaks_method(dict(e, score=0.4)))

    def test_page_embeds_the_sheet_and_cannot_be_closed_by_a_caption(self):
        e = ck.blind_entry("1@00:10:00|P1", dict(QUOTE, text="</script><b>x"), PRIORITY)
        html = labeller.build_html(ck.make_sheet([e], "2026-10-30"))
        self.assertIn("1@00:10:00|P1", html)
        self.assertNotIn("</script><b>", html)
        self.assertNotIn("strata", html)


class Labels(unittest.TestCase):
    def test_a_file_counts_only_with_the_attestation_and_allowed_values(self):
        with tempfile.TemporaryDirectory() as d:
            for name, doc in (("a.json", {"labeler": "A", "blind": True, "labels": {"p1": "real", "p2": "maybe"},
                                          "sides": {"p1": "same"}, "ms": {"p1": 4000}}),
                              ("b.json", {"labeler": "B", "labels": {"p1": "real"}})):
                with open(os.path.join(d, name), "w") as f:
                    json.dump(doc, f)
            with open(os.path.join(d, "README.md"), "w") as f:
                f.write("x")
            people, skipped = ck.load_people(d)
        self.assertEqual(list(people), ["A"])
        self.assertEqual(people["A"]["labels"], {"p1": "real"})
        self.assertEqual(people["A"]["ms"], {"p1": 4000.0})
        self.assertEqual(len(skipped), 1)

    def test_consensus_is_conservative(self):
        people = {"A": person({"p": "real", "q": "real", "r": "none"}, {"p": "same", "q": "same"},
                              {"p": "official", "q": "official"}),
                  "B": person({"p": "loose", "q": "real", "r": "none"}, {"p": "same", "q": "opposite"},
                              {"p": "other", "q": "official"})}
        c = ck.consensus(people)
        self.assertEqual(c["p"]["overlap"], "loose")
        self.assertEqual(c["p"]["speaker"], "other")
        self.assertEqual((c["q"]["overlap"], c["q"]["side"]), ("real", "opposite"))
        self.assertEqual(c["r"]["side"], "unclear")
        self.assertEqual(ck.consensus(people, {"p"}).keys(), {"p"})


class Figures(unittest.TestCase):
    def setUp(self):
        self.people = {"A": person({"a": "real", "b": "real", "c": "none", "d": "loose", "e": "real"},
                                   {"a": "same", "b": "opposite", "d": "same", "e": "same"},
                                   ms={"a": 30000, "b": 60000, "c": 10000, "d": 20000, "e": 900000})}
        self.cons = ck.consensus(self.people)

    def test_method_row_precision_misses_and_opposites(self):
        r = ck.method_row({"a", "b", "c", "zz"}, 40, self.cons)
        self.assertEqual((r["labelled_proposals"], r["real"], r["loose"], r["none"]), (3, 2, 0, 1))
        self.assertEqual(r["real_known"], 3)
        self.assertEqual(r["real_missed"], 1)
        self.assertEqual(r["opposite_among_real"]["k"], 1)
        self.assertAlmostEqual(r["precision_real"]["share"], 2 / 3)
        self.assertGreater(r["estimated_real_among_proposals"]["high"], r["estimated_real_among_proposals"]["mid"])

    def test_method_row_with_no_labelled_proposals(self):
        r = ck.method_row({"zz"}, 1, self.cons)
        self.assertIsNone(r["precision_real"]["share"])
        self.assertIsNone(r["estimated_real_among_proposals"])

    def test_timing_sets_aside_idle_labels(self):
        t = ck.timing(self.people)
        self.assertEqual(t["set_aside_over_cap"], 1)
        self.assertEqual(t["overall"]["n"], 4)
        self.assertEqual(t["overall"]["median"], 25.0)
        self.assertEqual(t["projection"]["10"]["median_minutes"], 4.2)

    def test_disagreements_list_the_pairs_that_differ(self):
        people = dict(self.people, B=person({"a": "loose", "b": "real", "c": "none"}, {"b": "same"}))
        (d,) = ck.disagreements(people)
        self.assertEqual((d["shared"], d["agree"]), (3, 2))
        self.assertEqual(d["differ"][0]["pair"], "a")
        self.assertTrue(d["neighbouring_only"])
        self.assertEqual(len(d["side_differ"]), 1)

    def test_instances_need_same_side_a_real_label_and_a_method_under_chance(self):
        props = {"keyword": {"a", "b", "c"}, "embedding": {"a"}, "ai_judge": {"a", "e"}}
        ok = {"keyword": True, "embedding": False, "ai_judge": False}
        inst = ck.qualifying_instances(props, self.cons, ok)
        self.assertEqual([i["pair"] for i in inst], ["a"])
        self.assertEqual(inst[0]["methods"], ["keyword"])

    def test_machine_row_counts_the_ai_reading(self):
        ai = {"a": {"overlap": "real", "stance": "opposes", "speaker_type": "official"},
              "b": {"overlap": "none", "stance": "not_comparable", "speaker_type": "clerk_or_agenda"},
              "c": {"error": "x"}}
        r = ck.machine_row({"a", "b", "c", "d"}, ai)
        self.assertEqual((r["proposals"], r["read"], r["real"], r["opposes"], r["real_and_may_be_official"]),
                         (4, 2, 1, 1, 1))

    def test_ai_against_people(self):
        ai = {"a": {"overlap": "real", "stance": "agrees", "speaker_type": "official"},
              "c": {"overlap": "loose", "stance": "mixed", "speaker_type": "official"}}
        t = ck.ai_against_people(ai, self.cons)
        self.assertEqual(t["overlap"]["real"], {"real": 1})
        self.assertEqual(t["overlap"]["none"], {"loose": 1})
        self.assertEqual(t["stance"], {"same|agrees": 1})


if __name__ == "__main__":
    unittest.main()
