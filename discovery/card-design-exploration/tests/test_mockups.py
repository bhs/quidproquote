import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import build_mockups as bm  # noqa: E402
import card_design_lib as L  # noqa: E402
import card_layouts as ly  # noqa: E402


class Fixed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cards = L.load_cards()

    def test_six_cards_from_the_built_pairings(self):
        self.assertEqual(len(self.cards), 6)
        self.assertEqual([c["n"] for c in self.cards], [1, 2, 3, 4, 5, 6])

    def test_every_layout_keeps_the_fixed_rules(self):
        for opt in ly.OPTIONS:
            for c in self.cards:
                for view in ("list", "card"):
                    self.assertEqual(bm.check_fixed_rules(opt, c, opt["fn"](c, view)), [], (opt["key"], c["n"], view))

    def test_no_total_across_committees(self):
        two = [c for c in self.cards if len(c["committees"]) > 1]
        self.assertTrue(two)
        for opt in ly.OPTIONS:
            for c in two:
                total = L.dollars(sum(m["schedule_a_total"] for m in c["committees"]))
                self.assertNotIn(total, bm.plain(L.html.unescape(opt["fn"](c, "card"))))

    def test_highlight_never_alters_text(self):
        t = "THIS MEASURE GIVES A TRANSFER TAX CODE"
        out = L.marked(t, ["transfer tax"])
        self.assertEqual(L.html.unescape(out.replace("<mark>", "").replace("</mark>", "")), t)
        self.assertIn("<mark>TRANSFER TAX</mark>", out)

    def test_highlight_must_be_in_both(self):
        with self.assertRaises(ValueError):
            L.check_terms(["muni"], "A QUOTE", ["a donor text about muni"], "x")

    def test_outside_spending_has_its_own_box(self):
        c = self.cards[5]
        self.assertFalse(c["committees"])
        self.assertIn('class="outside"', ly.layout_a(c, "card"))

    def test_list_cut_is_marked_and_card_has_full_words(self):
        c = self.cards[2]
        self.assertIn("cut for the list", ly.layout_d(c, "list"))
        self.assertIn(L.esc(c["quote"]["text"]).replace("&#x27;", "'")[:60], ly.layout_d(c, "card").replace("&#x27;", "'"))


if __name__ == "__main__":
    unittest.main()
