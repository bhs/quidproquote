import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import compare_lib as cl  # noqa: E402
import judge as jd  # noqa: E402
import money as mn  # noqa: E402
import report as rp  # noqa: E402

ROSTER = [{"name": "Myrna Melgar", "surname": "Melgar", "district": "7", "office": "Supervisor"},
          {"name": "Connie Chan", "surname": "Chan", "district": "1", "office": "Supervisor"},
          {"name": "Chyanne Chen", "surname": "Chen", "district": "11", "office": "Supervisor"},
          {"name": "Matt Dorsey", "surname": "Dorsey", "district": "6", "office": "Supervisor"}]


class LabelsAndMeasures(unittest.TestCase):
    def test_trial_classes_map_to_views(self):
        gold = cl.gold_from_judges({"model": {"a|P1": {"label": "not_a_quote"}, "b|P2": {"label": "meaningful"}}})
        self.assertEqual(gold["a|P1"]["overlap"], None)
        self.assertEqual(gold["a|P1"]["ready"], "none")
        self.assertEqual(gold["b|P2"]["ready"], "real")

    def test_lower_middle_is_conservative(self):
        self.assertEqual(cl.lower_middle(["real", "loose"]), "loose")
        self.assertEqual(cl.lower_middle(["real", "loose", "real"]), "real")

    def test_kappa_and_wilson_and_auc(self):
        self.assertAlmostEqual(cl.cohen_kappa(list("aabb"), list("aabb")), 1.0)
        lo, hi = cl.wilson(5, 10)
        self.assertTrue(lo < 0.5 < hi)
        self.assertEqual(cl.auc([2, 3], [1]), 1.0)
        self.assertEqual(cl.auc([1], [1]), 0.5)

    def test_evaluate_counts_missed_and_precision(self):
        gold = {"p1": {"overlap": "real", "ready": "real"}, "p2": {"overlap": "none", "ready": "none"},
                "p3": {"overlap": "real", "ready": "real"}}
        e = cl.evaluate({"p1": True, "p2": True, "p3": False}, gold, "ready")
        self.assertEqual((e["proposed"], e["proposed_real"], e["real_missed"]), (2, 1, 1))
        self.assertAlmostEqual(e["precision_real"], 0.5)


class CaptionErrors(unittest.TestCase):
    def test_errors_are_deterministic_and_change_words(self):
        text = "SUPERVISOR MELGAR SAID AYE ON PROP C FOR TWO MILLION"
        a = cl.inject_caption_errors(text, 1.0, "s", {"melgar"})
        b = cl.inject_caption_errors(text, 1.0, "s", {"melgar"})
        self.assertEqual(a, b)
        self.assertNotEqual(a[0], text)
        self.assertEqual(a[1]["vote"], 1)
        self.assertIn("PROP D", a[0])
        self.assertEqual(cl.inject_caption_errors(text, 0.0, "s", {"melgar"})[0], text)


class Speakers(unittest.TestCase):
    def test_cue_gives_a_proposal_with_caution(self):
        sp = cl.propose_speaker("NEXT UP DISTRICT SEVEN SUPERVISOR MELGAR", "THANK YOU", ROSTER)
        self.assertEqual(sp["name"], "Myrna Melgar")
        self.assertIn("district 7 agrees", sp["basis"])
        self.assertIn("unconfirmed", sp["caution"])

    def test_no_cue_and_roll_call_propose_nobody(self):
        self.assertIsNone(cl.propose_speaker("THE ITEM IS", "I THINK", ROSTER)["name"])
        roll = "SUPERVISOR CHAN SUPERVISOR DORSEY SUPERVISOR MELGAR"
        self.assertIsNone(cl.propose_speaker(roll, "I", ROSTER)["name"])


class Judge(unittest.TestCase):
    def test_parse_reply(self):
        rec = jd.parse_reply('x {"overlap": "real", "speaker_type": "official", "stance": "opposes", "reason": "r"} y')
        self.assertTrue(jd.is_proposed(rec))
        with self.assertRaises(jd.JudgeParseError):
            jd.parse_reply('{"overlap": "maybe", "speaker_type": "official", "stance": "agrees"}')
        with self.assertRaises(jd.JudgeParseError):
            jd.parse_reply("no json")

    def test_clerk_is_not_proposed_and_cost(self):
        rec = {"overlap": "real", "speaker_type": "clerk_or_agenda", "stance": "no_position",
               "input_tokens": 1000000, "output_tokens": 1000000}
        self.assertFalse(jd.is_proposed(rec))
        self.assertAlmostEqual(jd.cost_dollars(rec, {"price_in": 0.1, "price_out": 0.5}), 0.6)

    def test_missing_key_fails_loudly(self):
        old = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            with self.assertRaises(jd.JudgeError):
                jd.Judge()
        finally:
            if old is not None:
                os.environ["ANTHROPIC_API_KEY"] = old


class ReportAndMoney(unittest.TestCase):
    def test_proposals_none_when_stage_missing(self):
        it = {"id": "q|P1", "kind": "labelled", "lex": {"tfidf": 0.3, "both": 0.3, "anchor": 3.0}, "emb": None, "ai": None}
        rp.assign_proposals([it], {"keyword": 0.25, "keyword_phrase": 0.2, "anchor": 3, "embedding": None, "cutoff": None})
        self.assertTrue(it["prop"]["keyword"])
        self.assertIsNone(it["prop"]["embedding"])
        self.assertIsNone(it["prop"]["ai_judge"])
        self.assertIsNone(it["prop"]["embed_ai"])

    def test_embed_ai_needs_shortlist_and_confirmation(self):
        ai = {"overlap": "real", "speaker_type": "official", "stance": "agrees"}
        it = {"id": "q|P1", "kind": "labelled", "lex": {"tfidf": 0, "both": 0, "anchor": 0}, "emb": 0.8, "ai": ai}
        rp.assign_proposals([it], {"embedding": 0.9, "cutoff": 0.7})
        self.assertFalse(it["prop"]["embedding"])
        self.assertTrue(it["prop"]["embed_ai"])

    def test_money_query_names_form_a_and_committees(self):
        q = mn.build_query([["SEIU", "1021"]], ["123"])
        self.assertIn("form_type='A'", q["$where"])
        self.assertIn("'123'", q["$where"])
        self.assertIn("like '%1021%'", q["$where"])
        rows = mn.parse_rows([{"filer_nid": "1", "total": "5.5", "n": "2", "first": "2020-01-01T00:00:00"}])
        self.assertEqual(rows[0]["total"], 5.5)

    def test_probes_pair_same_and_opposite(self):
        ids = {pid: {} for _, pid, _, _ in cl.PROBES}
        items = cl.probe_items(ids)
        self.assertEqual(len(items), 2 * len(cl.PROBES))


if __name__ == "__main__":
    unittest.main()
