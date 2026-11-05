"""Writes the card mockups from the pairings already built (data/). Standard library only.

    python build_mockups.py

Writes, under mockups/: index.html (the four layouts side by side, each on a phone-sized and a computer-sized
screen, as a list and as one card), option-<a-d>-list.html and option-<a-d>-card.html, and reading-order.json
(what each layout puts first in a list, counted in characters of visible text). Refuses to write when a card
breaks one of the fixed rules (see check_fixed_rules).
"""

import json
import os
import re

import card_design_lib as L
import card_layouts as ly

OUT = os.path.join(L.HERE, "mockups")


def plain(h):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))


def check_fixed_rules(opt, card, html_text):
    """What every card must carry, checked on the page text of one card in one layout. Returns the problems."""
    bad, t = [], plain(html_text)
    t_unesc = L.html.unescape(t)
    q = card["quote"]["text"]
    if "\u201c%s\u201d" % q not in re.sub(r"\s+", " ", L.html.unescape(re.sub(r"<[^>]+>", "", html_text))).replace("\u201c ", "\u201c"):
        # the quote is split by <mark> tags; compare with tags removed
        bad.append("exact words in quotation marks missing")
    if L.NO_CAUSE not in t_unesc:
        bad.append("'No cause is claimed.' missing")
    if L.READING not in t_unesc:
        bad.append("'Reading, not a finding.' missing")
    if "SPEAKER-CREDIT DOUBT: %s" % card["doubt"].upper() not in t_unesc:
        bad.append("speaker-credit badge missing")
    for s in card["donor"]["statements"]:
        if s["url"] not in html_text:
            bad.append("donor source link missing")
    for u in (card["sources"]["transcript"],):
        if u not in html_text:
            bad.append("transcript link missing")
    for m in card["committees"]:
        if m["schedule_a_total_text"] not in t_unesc or m["committee"] not in t_unesc:
            bad.append("committee line missing: %s" % m["committee"])
    if len(card["committees"]) > 1:
        total = sum(m["schedule_a_total"] for m in card["committees"])
        if L.dollars(total) in t_unesc:
            bad.append("a total across committees appears: %s" % L.dollars(total))
    if card["outside"]:
        i = html_text.find('class="outside"')
        if i < 0:
            bad.append("outside spending not in its own container")
        else:
            for m in card["committees"]:
                j = html_text.find('class="money"')
                if j > i and j < html_text.find("</div></div>", i):
                    bad.append("a committee line sits inside the outside-spending box")
    return bad


def build():
    cards = L.load_cards()
    os.makedirs(OUT, exist_ok=True)
    order, problems = {}, []
    for opt in ly.OPTIONS:
        k = opt["key"]
        for c in cards:
            for view in ("list", "card"):
                problems += ["option %s, card %d, %s: %s" % (k, c["n"], view, p)
                             for p in check_fixed_rules(opt, c, opt["fn"](c, view))]
        order[k] = {str(c["n"]): ly.reading_order(opt, c) for c in cards}
    if problems:
        raise SystemExit("fixed rules broken:\n" + "\n".join(problems))
    for opt in ly.OPTIONS:
        k = opt["key"]
        with open(os.path.join(OUT, "option-%s-list.html" % k), "w", encoding="utf-8") as f:
            f.write(ly.list_page(opt, cards))
        with open(os.path.join(OUT, "option-%s-card.html" % k), "w", encoding="utf-8") as f:
            f.write(ly.card_page(opt, cards))
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(ly.gallery_page(cards))
    with open(os.path.join(OUT, "reading-order.json"), "w", encoding="utf-8") as f:
        json.dump({"unit": "characters of visible text before the item, in one card of the list view; null = not shown in the list",
                   "options": order}, f, indent=1)
    return cards, order


if __name__ == "__main__":
    cards, order = build()
    print("wrote %d cards in %d layouts to %s" % (len(cards), len(ly.OPTIONS), OUT))
    for k, v in order.items():
        for n in ("1", "3", "4", "6"):
            print("option %s card %s: %s" % (k, n, v[n]))
