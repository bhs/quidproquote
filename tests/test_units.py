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


class Terms(unittest.TestCase):
    def test_measure_names_and_named_things_become_anchors(self):
        st = [{"section": "Proposition H - Parcel Tax to Fund Public Muni Operations",
               "text": "Prop H would introduce a parcel tax to assist in funding San Francisco Municipal Transportation Agency operations. "
                       "The Chamber supports Prop H as public transit is a critical driver of the San Francisco economy."}]
        terms = pipeline.subject_terms(st)
        self.assertIn("PROP H", terms["anchor"])
        self.assertIn("PROPOSITION H", terms["anchor"])
        self.assertTrue(terms["topic"])


if __name__ == "__main__":
    unittest.main()
