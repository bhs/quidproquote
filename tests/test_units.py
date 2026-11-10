import os
import time
import unittest
from unittest import mock

from pairing_site import auth, pipeline, priorities

import fmap_lib as fl


class Session(unittest.TestCase):
    def setUp(self):
        env = mock.patch.dict(os.environ, {"ADMIN_TOKEN": "right-token"})
        env.start()
        self.addCleanup(env.stop)

    def test_token(self):
        self.assertTrue(auth.token_ok("right-token"))
        self.assertFalse(auth.token_ok("wrong"))
        self.assertFalse(auth.token_ok(""))

    def test_session_signed_and_expiring(self):
        cookie = auth.make_session()
        self.assertTrue(auth.session_ok(cookie))
        self.assertFalse(auth.session_ok(cookie[:-1] + ("0" if cookie[-1] != "0" else "1")))
        self.assertFalse(auth.session_ok(cookie, now=time.time() + auth.TTL_S + 5))
        self.assertFalse(auth.session_ok("garbage"))

    def test_session_from_another_token_is_refused(self):
        cookie = auth.make_session()
        with mock.patch.dict(os.environ, {"ADMIN_TOKEN": "other"}):
            self.assertFalse(auth.session_ok(cookie))


PAGE = "<html><body><h1>Voter guide</h1><p>The Chamber supports Prop H as public transit is a critical driver of the \u201cSan Francisco\u201d economy.</p></body></html>"


class PriorityCheck(unittest.TestCase):
    def test_words_must_be_verbatim(self):
        self.assertTrue(priorities.words_on_page(PAGE, 'The Chamber supports Prop H as public transit is a critical driver of the "San Francisco" economy.'))
        self.assertFalse(priorities.words_on_page(PAGE, "The Chamber strongly supports Prop H as public transit is a critical driver"))

    def test_retrieval_date_is_the_servers(self):
        with mock.patch.object(priorities, "check_public_url"):
            found = priorities.verify("https://example.org/guide", "The Chamber supports Prop H as public transit is a critical driver",
                                      fetch=lambda url: PAGE)
        self.assertEqual(found["retrieved"], fl.today())

    def test_not_found_saves_nothing(self):
        with mock.patch.object(priorities, "check_public_url"):
            with self.assertRaises(priorities.PriorityError):
                priorities.verify("https://example.org/guide", "A sentence that is nowhere on this page at all", fetch=lambda url: PAGE)

    def test_too_short_and_private_addresses_refused(self):
        with self.assertRaises(priorities.PriorityError):
            priorities.verify("https://example.org/", "too short", fetch=lambda url: PAGE)
        with self.assertRaises(priorities.PriorityError):
            priorities.check_public_url("http://127.0.0.1/admin")
        with self.assertRaises(priorities.PriorityError):
            priorities.check_public_url("file:///etc/passwd")


class Decide(unittest.TestCase):
    def rec(self, **kw):
        base = {"overlap": "real", "speaker_type": "official", "stance": "agrees", "reason": "Both speak of Prop H."}
        base.update(kw)
        return base

    def test_kept(self):
        self.assertEqual(pipeline.decide(self.rec())[:2], (True, "kept"))
        self.assertTrue(pipeline.decide(self.rec(stance="no_position", speaker_type="unclear"))[0])

    def test_topic_only_is_dropped_with_a_reason(self):
        keep, kind, why = pipeline.decide(self.rec(overlap="loose"))
        self.assertEqual((keep, kind), (False, "topic-only"))
        self.assertIn("topic words only", why)
        self.assertIn("Both speak of Prop H.", why)

    def test_opposing_is_dropped(self):
        self.assertEqual(pipeline.decide(self.rec(stance="opposes"))[:2], (False, "opposing"))

    def test_not_an_official_is_dropped(self):
        self.assertEqual(pipeline.decide(self.rec(speaker_type="public_comment"))[:2], (False, "not-an-official"))


class AutoPublish(unittest.TestCase):
    def card(self, doubt="low"):
        return {"speaker_credit": {"doubt": doubt}}

    def rec(self, stance="agrees"):
        return {"overlap": "real", "speaker_type": "official", "stance": stance}

    def test_ordinary_pairs_are_published(self):
        for doubt in ("low", "medium"):
            publish, why = pipeline.auto_publish(self.card(doubt), self.rec())
            self.assertTrue(publish)
            self.assertIn("automated match", why)

    def test_high_doubt_in_the_speaker_credit_is_held(self):
        publish, why = pipeline.auto_publish(self.card("high"), self.rec())
        self.assertFalse(publish)
        self.assertIn("high doubt", why)

    def test_mixed_or_absent_position_is_held(self):
        for stance in ("mixed", "no_position"):
            self.assertFalse(pipeline.auto_publish(self.card("low"), self.rec(stance))[0])


class Terms(unittest.TestCase):
    def test_measure_names_and_named_things_become_anchors(self):
        st = [{"section": "Proposition H - Parcel Tax to Fund Public Muni Operations",
               "text": "Prop H would introduce a parcel tax to assist in funding San Francisco Municipal Transportation Agency operations. "
                       "The Chamber supports Prop H as public transit is a critical driver of the San Francisco economy."}]
        terms = pipeline.subject_terms(st)
        self.assertIn("PROP H", terms["anchor"])
        self.assertIn("PROPOSITION H", terms["anchor"])
        self.assertTrue(terms["topic"])


class Glance(unittest.TestCase):
    def card(self, **kw):
        card = {"quote": {"text": " ".join("word%d" % i for i in range(40)) + " Muni"}, "highlight": ["Muni"],
                "official": {"name": "A. Official", "role": "Mayor"},
                "donor": {"name": "Donor", "statements": [{"section": "Prop H", "text": "The donor supports Prop H.",
                                                           "url": "https://example.org/g", "kind": "voter guide on the organisation's own site"}]},
                "money": {"committees": [{"committee": "Committee %d with a rather long name indeed" % i, "kind": "officeholder committee",
                                          "schedule_a_total": 100.0 * i, "schedule_a_total_text": "$%d" % (100 * i)} for i in (1, 3, 2, 4)],
                          "outside_spending": [{"spender": "A PAC", "stance": "supporting", "amount_text": "$9"}]},
                "speaker_credit": {"doubt": "low", "reason": "The cue names the speaker. A second sentence."}}
        card.update(kw)
        return card

    def test_excerpt_is_the_first_words_with_a_cut_flag(self):
        self.assertEqual(pipeline.excerpt("a  b c", 2), ("a  b", True))
        self.assertEqual(pipeline.excerpt("a b", 2), ("a b", False))

    def test_shared_words_are_marked_only_inside_the_excerpt(self):
        g = pipeline.glance(self.card())
        self.assertEqual(g["shared"], [])
        self.assertTrue(g["quote_cut"])
        self.assertIn("Nothing shared in this excerpt", g["nothing_shared"])
        self.assertEqual(pipeline.glance(self.card(highlight=[]))["nothing_shared"][:15], "Nothing shared:")
        short = self.card(quote={"text": "Muni rides are up"})
        self.assertEqual(pipeline.glance(short)["shared"], ["Muni"])

    def test_largest_committees_first_with_a_count_and_nothing_summed(self):
        g = pipeline.glance(self.card())
        self.assertEqual([m["amount"] for m in g["committees"]], ["$400", "$300"])
        self.assertEqual(g["more_committees"], 2)
        self.assertTrue(all(len(m["label"]) <= pipeline.LABEL_CHARS + 1 for m in g["committees"]))
        self.assertEqual(g["outside"][0]["amount"], "$9")

    def test_four_chips_invert_doubt_and_cite_their_evidence(self):
        chips = pipeline.confidence_chips(self.card())
        self.assertEqual([c["area"] for c in chips], ["Speaker credit", "Topic match", "Donor priority", "Money tie"])
        self.assertEqual([c["level"] for c in chips], ["high", "medium", "high", "high"])
        self.assertTrue(all(c["reason"] for c in chips))
        self.assertNotIn("second sentence", chips[0]["reason"])
        for doubt, level in (("medium", "medium"), ("high", "low")):
            self.assertEqual(pipeline.confidence_chips(self.card(speaker_credit={"doubt": doubt, "reason": "x"}))[0]["level"], level)

    def test_verified_replaces_the_speaker_level_only(self):
        chips = pipeline.confidence_chips(self.card(), verified=True)
        self.assertEqual((chips[0]["level"], chips[0]["word"]), ("verified", "VERIFIED"))
        self.assertEqual(chips[1]["level"], "medium")

    def test_levels_from_shared_words_source_kind_and_committee_tie(self):
        none = pipeline.confidence_chips(self.card(highlight=[]))[1]
        two = pipeline.confidence_chips(self.card(highlight=["Muni", "Prop H"]))[1]
        self.assertEqual((none["level"], two["level"]), ("low", "high"))
        news = {"section": "", "text": "x", "url": "u", "kind": priorities.NEWS, "outlet": "Daily", "whose_words": "reporter"}
        card = self.card()
        card["donor"]["statements"].append(news)
        self.assertEqual(pipeline.confidence_chips(card)[2]["level"], "low")
        news["whose_words"] = "donor-quoted"
        self.assertEqual(pipeline.confidence_chips(card)[2]["level"], "medium")
        card["money"]["committees"][0]["kind"] = "ballot-measure committee carrying the official's name"
        self.assertEqual(pipeline.confidence_chips(card)[3]["level"], "medium")
        card["money"]["committees"][1]["kind"] = "own committee, for another office (School Board)"
        self.assertEqual(pipeline.confidence_chips(card)[3]["level"], "low")
        card["money"]["committees"] = []
        self.assertEqual(pipeline.confidence_chips(card)[3]["level"], "low")


if __name__ == "__main__":
    unittest.main()
