import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import analyze  # noqa: E402
import trial_lib as lib  # noqa: E402

PRIORITIES = [
    {"id": "P1", "donor": "A", "section": "Proposition C - Contributions to the Housing Trust Fund",
     "text": "Prop C would raise the Housing Trust Fund to $125 million a year for affordable housing."},
    {"id": "P2", "donor": "B", "section": "Transit Infrastructure",
     "text": "Secure stable, long-term funding for local transit systems to keep Muni reliable."},
    {"id": "P3", "donor": "B", "section": "Arts", "text": "Treat arts and culture as economic drivers."},
]
QUOTES = [
    "THE HOUSING TRUST FUND HAS HELPED CREATE AFFORDABLE HOMES AND THIS MEASURE WILL STRENGTHEN THE "
    "FUND OVER TIME FOR AFFORDABLE HOUSING",
    "MUNI NEEDS STABLE FUNDING SO TRANSIT STAYS RELIABLE FOR RIDERS ACROSS THE CITY AND THE REGION",
    "THANK YOU MADAM CLERK PLEASE CALL THE NEXT ITEM",
]


class TextTests(unittest.TestCase):
    def test_tokenize_lowercases_and_reads_proposition_as_prop(self):
        self.assertEqual(lib.tokenize("PROPOSITION H, it's"), ["prop", "h", "its"])

    def test_stem_joins_forms_of_a_word(self):
        self.assertEqual(lib.stem("housing"), lib.stem("houses"))
        self.assertEqual(lib.stem("rents"), lib.stem("rent"))

    def test_content_terms_drop_stop_words_and_short_words(self):
        terms = lib.content_terms(lib.tokenize("THE CITY OF SAN FRANCISCO HAS A HOUSING FUND"))
        self.assertEqual(terms, [lib.stem("housing"), lib.stem("fund")])


class PassageTests(unittest.TestCase):
    def test_passages_split_at_turn_marker_and_keep_first_stamp(self):
        rows = [("00:00:01", "ONE TWO THREE >> FOUR FIVE"), ("00:00:09", "SIX SEVEN.")]
        got = lib.build_passages(7, rows, min_words=2, max_words=50)
        self.assertEqual([p["text"] for p in got], ["ONE TWO THREE", "FOUR FIVE SIX SEVEN."])
        self.assertEqual([p["start"] for p in got], ["00:00:01", "00:00:01"])
        self.assertEqual(got[1]["id"], "7@00:00:01")

    def test_passage_closes_at_sentence_end_after_minimum(self):
        words = " ".join(["WORD"] * 5) + ". " + " ".join(["MORE"] * 5)
        got = lib.build_passages(1, [("00:00:00", words)], min_words=4, max_words=50)
        self.assertEqual(len(got), 2)

    def test_procedural_passage_is_not_substantive(self):
        text = ("MADAM CLERK PLEASE CALL THE ROLL ON THIS ITEM AND ROLL CALL WILL BE TAKEN NOW "
                "THANK YOU FOR THAT MOTION AND THE SECOND BY SUPERVISOR CHEN ON THE MOTION")
        self.assertFalse(lib.is_substantive({"text": text}))

    def test_short_passage_is_not_substantive(self):
        self.assertFalse(lib.is_substantive({"text": "HOUSING FUND TRANSIT BUDGET"}))


class AnchorTests(unittest.TestCase):
    def test_measure_letter_and_names_are_anchors(self):
        found = lib.extract_anchors("Prop H would fund Muni. The Great Highway stays closed to the ESER bond.")
        self.assertIn(("prop", "h"), found)
        self.assertIn(("great", "highway"), found)
        self.assertIn(("eser",), found)

    def test_sentence_opening_word_is_not_an_anchor(self):
        found = lib.extract_anchors("Housing is hard. We want more.")
        self.assertNotIn(("housing",), found)

    def test_generic_names_are_dropped(self):
        found = lib.extract_anchors("Support the Board of Supervisors in San Francisco.")
        self.assertNotIn(("san", "francisco"), found)


class TopicTests(unittest.TestCase):
    def test_topic_needs_three_distinct_keywords(self):
        terms = lib.content_terms(lib.tokenize("rent tenants and zoning for housing"))
        self.assertIn("housing", lib.active_topics(terms))
        self.assertEqual(lib.active_topics(lib.content_terms(lib.tokenize("housing housing housing"))), set())


class MatchingTests(unittest.TestCase):
    def setUp(self):
        self.tokens = [lib.tokenize(q) for q in QUOTES]
        self.ctx = lib.Context(PRIORITIES, self.tokens, generic_phrase_share=1.0, generic_anchor_share=1.0)
        self.scores = lib.score_quotes(self.ctx, self.tokens)

    def test_cosine_prefers_the_right_priority(self):
        s = self.scores["tfidf"]
        self.assertGreater(s[(0, 0)], s.get((0, 1), 0))
        self.assertGreater(s[(1, 1)], s.get((1, 0), 0))

    def test_unrelated_quote_matches_nothing(self):
        for m in ("tfidf", "phrase", "anchor", "both"):
            self.assertFalse([k for k in self.scores[m] if k[0] == 2], m)

    def test_shared_phrase_is_counted(self):
        self.assertGreaterEqual(self.scores["phrase"][(0, 0)], 2)

    def test_both_is_cosine_where_a_phrase_is_shared(self):
        for k, s in self.scores["both"].items():
            self.assertIn(k, self.scores["phrase"])
            self.assertEqual(s, self.scores["tfidf"][k])

    def test_counts_at_levels_are_cumulative(self):
        counts = lib.counts_at_levels(self.scores)
        for m, _ in lib.METHODS:
            self.assertEqual(counts[m], sorted(counts[m], reverse=True))


class ChanceTests(unittest.TestCase):
    def test_null_keeps_lengths_and_is_repeatable(self):
        tokens = [lib.tokenize(q) for q in QUOTES]
        a = lib.draw_null(tokens, [1, 1, 2], random.Random(5), within_meeting=False)
        b = lib.draw_null(tokens, [1, 1, 2], random.Random(5), within_meeting=False)
        self.assertEqual(a, b)
        self.assertEqual([len(x) for x in a], [len(x) for x in tokens])

    def test_within_meeting_null_only_uses_that_meetings_words(self):
        tokens = [["aaa", "bbb"], ["ccc", "ddd"]]
        out = lib.draw_null(tokens, [1, 2], random.Random(1), within_meeting=True)
        self.assertTrue(set(out[0]) <= {"aaa", "bbb"})
        self.assertTrue(set(out[1]) <= {"ccc", "ddd"})

    def test_calibrated_level_is_lowest_with_chance_under_one(self):
        self.assertEqual(lib.calibrated_level("tfidf", None, [9, 4, 0.5, 0, 0, 0, 0]), (2, 0.25))
        self.assertEqual(lib.calibrated_level("phrase", None, [9, 4, 3]), (None, None))


class SampleTests(unittest.TestCase):
    def test_stable_order_is_deterministic_and_salted(self):
        keys = [(i, i + 1) for i in range(20)]
        self.assertEqual(lib.stable_order(keys, "a"), lib.stable_order(keys, "a"))
        self.assertNotEqual(lib.stable_order(keys, "a"), lib.stable_order(keys, "b"))


class JudgeTests(unittest.TestCase):
    def test_kappa_is_one_for_identical_labels_and_zero_for_chance_level(self):
        same = [("meaningful", "meaningful"), ("topical", "topical"), ("coincidental", "coincidental")]
        self.assertAlmostEqual(analyze.kappa(same), 1.0)
        chance = [("meaningful", "meaningful"), ("meaningful", "topical"),
                  ("topical", "meaningful"), ("topical", "topical")]
        self.assertAlmostEqual(analyze.kappa(chance), 0.0)

    def test_fisher_is_one_for_equal_shares_and_small_for_a_clear_gap(self):
        self.assertAlmostEqual(analyze.fisher_two_sided(5, 10, 5, 10), 1.0)
        self.assertLess(analyze.fisher_two_sided(10, 10, 0, 10), 0.001)

    def test_every_judged_pair_is_in_the_sample_and_labels_are_from_the_rubric(self):
        import json
        here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
        with open(os.path.join(here, "label_sample.json"), encoding="utf-8") as f:
            sample = {r["pair"] for r in json.load(f)}
        for name in ("labels.json", "labels_model.json"):
            with open(os.path.join(here, "data", name), encoding="utf-8") as f:
                d = json.load(f)
            self.assertTrue(set(d["labels"]) <= sample, name)
            self.assertTrue({v["label"] for v in d["labels"].values()} <= set(analyze.CLASSES), name)


if __name__ == "__main__":
    unittest.main()
