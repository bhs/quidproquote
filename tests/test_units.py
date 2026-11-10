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
    def card(self, doubt="low", shared=("Prop H", "transit"), kind="policy page on the organisation's own site",
             tie="Tie to the donor recognised by Filers id: A1 (Chamber).", whose=""):
        return {"speaker_credit": {"doubt": doubt, "reason": "the cue names the surname"}, "highlight": list(shared),
                "quote": {"text": "We met on Tuesday. I support Prop H and transit service. Thank you all."},
                "donor": {"name": "Chamber", "tie": {"text": tie},
                          "statements": [{"section": "Prop H", "text": "The Chamber backs Prop H. Transit matters.",
                                          "kind": kind, "whose_words": whose, "url": "https://example.org"}]},
                "money": {"committees": [{"kind": "officeholder committee", "committee": "Friends of A",
                                          "schedule_a_total_text": "$10,000"}]}}

    def levels(self, card, checked=False):
        return {c["key"]: c["level"] for c in pipeline.confidence(card, checked)}

    def test_four_chips_always_in_order_each_with_a_reason(self):
        chips = pipeline.confidence(self.card(shared=()))
        self.assertEqual([c["key"] for c in chips], ["speaker", "topic", "priority", "money"])
        self.assertTrue(all(c["reason"] for c in chips))

    def test_speaker_credit_inverts_the_stored_doubt(self):
        for doubt, level in (("high", "low"), ("medium", "med"), ("low", "high")):
            self.assertEqual(self.levels(self.card(doubt))["speaker"], level)

    def test_verified_only_when_the_recording_is_checked(self):
        self.assertEqual(self.levels(self.card("high"), True)["speaker"], "verified")
        self.assertNotEqual(self.levels(self.card("low"))["speaker"], "verified")

    def test_topic_match_follows_the_shared_words(self):
        self.assertEqual(self.levels(self.card(shared=()))["topic"], "low")
        self.assertEqual(self.levels(self.card(shared=("Prop H",)))["topic"], "med")
        self.assertEqual(self.levels(self.card())["topic"], "high")

    def test_donor_priority_follows_the_statement_kind(self):
        self.assertEqual(self.levels(self.card())["priority"], "high")
        news = pipeline.donor_priorities.NEWS
        self.assertEqual(self.levels(self.card(kind=news, whose="donor-quoted"))["priority"], "med")
        self.assertEqual(self.levels(self.card(kind=news, whose="reporter"))["priority"], "low")

    def test_money_tie_follows_the_tie_text(self):
        by_name = "Tie to the donor recognised by name only (1 giver name as filed)"
        self.assertEqual(self.levels(self.card(tie=by_name + "; the rows carry no FPPC id."))["money"], "low")
        self.assertEqual(self.levels(self.card(tie=by_name + "; FPPC id that resolves in the Filers dataset: 1 ('X')."))["money"], "med")
        self.assertEqual(self.levels(self.card(tie=by_name + "; the FPPC ids on those rows do not resolve in the Filers dataset."))["money"], "low")

    def test_the_excerpt_is_the_sentence_with_most_shared_words_and_is_cut_with_ellipses(self):
        cut = pipeline.best_sentence(self.card()["quote"]["text"], ["Prop H", "transit"])
        self.assertEqual(cut, {"text": "I support Prop H and transit service.", "before": True, "after": True, "found": 2})

    def test_nothing_shared_is_reported(self):
        self.assertEqual(pipeline.best_sentence("One. Two.", [])["found"], 0)

    def test_money_lines_are_per_committee_with_a_short_label(self):
        g = pipeline.glance(self.card())
        self.assertEqual(g["money"], [{"label": "Officeholder committee", "committee": "Friends of A", "amount": "$10,000"}])


if __name__ == "__main__":
    unittest.main()
