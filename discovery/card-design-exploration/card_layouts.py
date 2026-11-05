"""The four card layouts, the pages that show them and the gallery that sets them side by side.

    from card_layouts import OPTIONS, card_page, list_page, gallery_page

Each layout is a function of one card (from card_design_lib.load_cards) and a view: "list" (one of many) or "card"
(alone on its own page). The fragments they are made of are in card_design_lib, so the fixed content is the same.
"""

import re

import card_design_lib as L

BASE_CSS = """
*{box-sizing:border-box}
body{font:15px/1.45 system-ui,sans-serif;margin:0;background:#f4f1ea;color:#222}
main{max-width:1180px;margin:0 auto;padding:.8rem}
h1{font-size:1.25rem;margin:.2rem 0} a{color:#1b4f9c}
.pagenote{font-size:.85rem;color:#444;max-width:75ch}
ol.cards{list-style:none;padding:0;margin:0}
.card{background:#fff;border:1px solid #bbb;border-radius:8px;margin:1rem 0;padding:.8rem 1rem;overflow-wrap:anywhere}
.card h2{font-size:1.05rem;margin:.1rem 0 .5rem}
.small{font-size:.85rem;color:#444} .cite{margin:.2rem 0}
.stress{display:inline-block;background:#fff3d6;border:1px solid #d9b04a;border-radius:3px;padding:0 .4rem;font-size:.78rem;margin-bottom:.4rem}
.zone-h{font-size:.78rem;text-transform:uppercase;letter-spacing:.04em;color:#555;margin:.1rem 0 .4rem}
.money{border-left:4px solid #2f6f4f;padding:.25rem .6rem;margin:.4rem 0;background:#f3f8f5}
.amt{font-weight:700;font-size:1.05rem} .amt-l{font-size:.78rem;color:#2f6f4f}
.outside{border:2px dashed #a33;background:#fbf1f1;padding:.4rem .6rem;margin:.8rem 0 .2rem;border-radius:4px}
.outside-h{font-weight:700;color:#a33} .ox{margin:.35rem 0}
.bubble{background:#eef2fb;border:1px solid #9fb3e0;border-radius:14px;padding:.55rem .8rem;margin-top:.7rem}
.bubble-h{font-weight:700} .bubble blockquote{margin:.3rem 0;font-family:Georgia,serif}
.official .name{font-size:1.1rem;font-weight:700} .official .role{color:#444}
blockquote.quote,blockquote.hero{margin:.3rem 0;border-left:4px solid #777;padding-left:.7rem;font-family:Georgia,serif}
blockquote.hero{font-size:1.2rem;line-height:1.5}
mark{background:#ffe066;padding:0 .1em}
.strip{margin-top:.8rem;background:#f7f7f7;border:1px dashed #999;padding:.5rem .7rem}
.badge{display:inline-block;border-radius:3px;padding:.05rem .45rem;font-weight:700;font-size:.78rem;color:#fff;margin-right:.3rem}
.badge.low{background:#2f6f4f}.badge.medium{background:#b07a00}.badge.high{background:#a33}
.sources{margin-top:.6rem;font-size:.85rem;color:#333;border-top:1px solid #ddd;padding-top:.4rem}
.chip{display:inline-block;border:1px solid #d9b04a;border-radius:12px;padding:0 .5rem;margin:0 .3rem .2rem 0;font-size:.85rem}
.chip.none{border-color:#bbb;color:#555}
.single{display:none}.single:target{display:block}
.nav{font-size:.85rem;margin:.4rem 0}
"""

LAYOUT_CSS = {
    "a": """
.zones{display:grid;grid-template-columns:1.25fr .6fr 1fr;gap:.9rem}
.zones .official{text-align:center;align-self:center}
@media(max-width:640px){.zones{grid-template-columns:1fr}.zones .official{text-align:left}}
""",
    "b": """
.bhead{display:flex;gap:.6rem;align-items:baseline;flex-wrap:wrap}
.bcols{display:grid;grid-template-columns:1fr 1fr;gap:.9rem;margin-top:.6rem}
@media(max-width:640px){.bcols{grid-template-columns:1fr}}
""",
    "c": """
.chead{background:#25303f;color:#fff;margin:-.8rem -1rem .6rem;padding:.5rem 1rem;border-radius:8px 8px 0 0}
.chead .role{color:#d6dbe4}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:.9rem}
.pair>div{min-width:0}
.shared{text-align:center;margin:.5rem 0}
.ledger{width:100%;border-collapse:collapse;margin-top:.3rem}
.ledger th,.ledger td{text-align:left;vertical-align:top;border-top:1px solid #cfe0d6;padding:.3rem .4rem;font-size:.9rem}
.ledger th{font-size:.75rem;text-transform:uppercase;color:#2f6f4f}
.ledger td.num{font-weight:700;white-space:nowrap}
.ledgerbox{border:1px solid #2f6f4f;border-radius:6px;padding:.4rem .6rem;background:#f3f8f5;margin-top:.7rem}
@media(max-width:640px){.pair{grid-template-columns:1fr}
.ledger thead{display:none}.ledger,.ledger tbody,.ledger tr,.ledger td{display:block;width:100%}
.ledger tr{border-top:2px solid #2f6f4f;margin-top:.3rem}.ledger td{border:0;padding:.1rem .2rem}}
""",
    "d": """
details.glance{background:#fff;border:1px solid #bbb;border-radius:8px;margin:.6rem 0;padding:0}
details.glance>summary{list-style:none;cursor:pointer;padding:.6rem .8rem}
details.glance>summary::-webkit-details-marker{display:none}
.sum-top{display:flex;justify-content:space-between;gap:.5rem;flex-wrap:wrap;align-items:baseline}
.sum-line{margin:.25rem 0}
.sum-money{display:flex;flex-direction:column;gap:.15rem;margin:.3rem 0}
.sum-money div{border-left:4px solid #2f6f4f;padding-left:.5rem}
.flag{display:inline-block;border:2px dashed #a33;color:#a33;border-radius:4px;padding:0 .4rem;font-size:.8rem;font-weight:700}
.opener{font-size:.8rem;color:#1b4f9c}
.more{padding:0 .8rem .8rem}
""",
}


# --------------------------------------------------------------------------- the layouts

def layout_a(c, view):
    """Three zones side by side: money in then the donor's priority | the official | the official's words."""
    return ('<div class="zones"><div class="zone">%s%s</div><div class="zone">%s</div><div class="zone">'
            '<div class="zone-h">The official\'s exact words</div>%s</div></div>%s%s' % (
                L.f_money(c, "Money in, then the donor's priority"), L.f_priority(c),
                L.f_official(c), L.f_words(c), L.f_reading(c), L.f_sources(c)))


def layout_b(c, view):
    """Words first: the official and the words as the headline, then priority and money side by side."""
    return ('<div class="bhead">%s</div><blockquote class="hero">&ldquo;%s&rdquo;</blockquote>'
            '<div class="small cite">%s, %s, transcript time %s &middot; <a href="%s">transcript</a></div>'
            '<div class="bcols"><div>%s</div><div>%s</div></div>%s%s' % (
                L.f_official(c), L.marked(c["quote"]["text"], c["highlight"]), L.esc(c["quote"]["meeting"]),
                c["quote"]["date"], L.stamp(c["quote"]), L.esc(c["quote"]["transcript_url"]),
                L.f_priority(c), L.f_money(c, "Money in"), L.f_reading(c), L.f_sources(c)))


def f_ledger(c):
    if not c["committees"]:
        note = '<div class="small">%s</div>' % L.esc(c["no_money_note"]) if c["no_money_note"] else ""
        return '<div class="ledgerbox"><div class="zone-h">Gifts to the official\'s committees</div>%s</div>%s' % (note, L.f_outside(c))
    rows = "".join(
        '<tr><td class="num">%s<div class="small">this committee only</div></td><td><b>%s</b><div class="small">filer %s</div></td>'
        '<td>%s</td><td>%d row%s<div class="small">%s</div></td><td>%s</td></tr>' % (
            L.esc(m["schedule_a_total_text"]), L.esc(m["committee"]), L.esc(m["filer"]), L.esc(m["kind"]), m["rows"],
            "" if m["rows"] == 1 else "s", L.span(m),
            L.names_html(m["givers_as_filed"]))
        for m in c["committees"])
    return ('<div class="ledgerbox"><div class="zone-h">Money in: a separate record from the words</div>'
            '<table class="ledger"><thead><tr><th>Schedule A total</th><th>Committee</th><th>Kind</th><th>Rows, dates</th>'
            '<th>Giver as filed</th></tr></thead><tbody>%s</tbody></table><div class="small nosum">%s</div></div>%s' % (
                rows, L.NO_SUM_NOTE, L.f_outside(c)))


def layout_c(c, view):
    """Matched pair: the words and the donor's priority in two columns with shared words between, money as a ledger."""
    return ('<div class="chead">%s</div><div class="pair"><div><div class="zone-h">What the official said</div>%s</div>'
            '<div><div class="zone-h">What the donor says it wants</div>%s</div></div>'
            '<div class="shared small">Words in both: %s</div>%s%s%s' % (
                L.f_official(c), L.f_words(c), L.f_priority(c), L.f_chips(c), f_ledger(c), L.f_reading(c), L.f_sources(c)))


def layout_d(c, view):
    """Glance row that opens: the list shows a row, the card's own page shows the same card open."""
    cut, was_cut = L.short_cut(c["quote"]["text"])
    q = c["quote"]
    money = "".join('<div><span class="amt">%s</span> %s <span class="small">(this committee only)</span></div>' % (
        L.esc(m["schedule_a_total_text"]), L.esc(m["committee"])) for m in c["committees"]) or \
        '<div class="small">No gift to the official\'s committees found.</div>'
    flag = '<span class="flag">Outside spending, kept apart: open the card</span>' if c["outside"] else ""
    summary = ('<summary><div class="sum-top"><span><b>%s</b> <span class="small">%s</span> &times; %s</span>'
               '<span>%s</span></div><div class="sum-line">%s</div>'
               '<div class="sum-line quote">&ldquo;%s&rdquo;%s <span class="small">%s, %s, %s</span></div>'
               '<div class="sum-money">%s</div><div>%s <span class="opener">Open the whole card</span></div></summary>' % (
                   L.esc(c["official"]["name"]), L.esc(c["official"]["role"]), L.esc(c["donor"]["name"]), L.f_badge(c),
                   "Words in both: " + L.f_chips(c), L.marked(cut, c["highlight"]),
                   " &hellip; <i class=\"small\">(cut for the list; the full words are on the card)</i>" if was_cut else "",
                   L.esc(q["meeting"]), q["date"], L.stamp(q), money, flag))
    body = ('<div class="more">%s%s%s%s%s%s</div>' % (
        L.f_official(c), L.f_words(c), L.f_priority(c), L.f_money(c, "Money in"), L.f_reading(c), L.f_sources(c)))
    return '<details class="glance"%s>%s%s</details>' % (" open" if view == "card" else "", summary, body)


OPTIONS = [
    {"key": "a", "name": "Three zones", "fn": layout_a,
     "blurb": "Money and the donor's priority on the left, the official in the middle, the words on the right (the layout the maintainer described). On a phone the zones stack in that order."},
    {"key": "b", "name": "Words first", "fn": layout_b,
     "blurb": "The official's words are the headline; the donor's priority and the money sit beneath, side by side on a computer, stacked on a phone."},
    {"key": "c", "name": "Matched pair with a money ledger", "fn": layout_c,
     "blurb": "The words and the donor's priority face each other with the shared words between them; the money is a ledger in its own box beneath."},
    {"key": "d", "name": "Glance row that opens", "fn": layout_d,
     "blurb": "In a list each card is a short row (names, shared words, cut words, one line per committee); the card's page, or a tap, shows everything."},
]


# --------------------------------------------------------------------------- pages

def _doc(title, css, body, note=""):
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
            'content="width=device-width,initial-scale=1"><title>%s</title><style>%s</style></head><body><main>'
            '<h1>%s</h1>%s%s</main></body></html>\n' % (L.esc(title), BASE_CSS + css, L.esc(title), note, body))


def _article(opt, c, view):
    inner = opt["fn"](c, view)
    if opt["key"] == "d":
        return "<li>%s%s</li>" % (L.f_stress(c), inner) if view == "list" else inner
    return '<li class="card" id="card-%d">%s<h2>Card %d: %s</h2>%s</li>' % (
        c["n"], L.f_stress(c), c["n"], L.esc(c["title"]), inner)


def list_page(opt, cards):
    body = '<ol class="cards">%s</ol>' % "\n".join(_article(opt, c, "list") for c in cards)
    note = '<p class="pagenote">Option %s, a list of %d cards. Mockup filled with the pairings already built; each card is a reading, not a finding.</p>' % (
        opt["key"].upper(), len(cards))
    return _doc("Option %s: %s, list" % (opt["key"].upper(), opt["name"]), LAYOUT_CSS[opt["key"]], body, note)


def card_page(opt, cards, default=4):
    nav = '<div class="nav">Card: %s</div>' % " ".join('<a href="#c%d">%d</a>' % (c["n"], c["n"]) for c in cards)
    secs = "".join('<section class="single" id="c%d"><ol class="cards">%s</ol></section>' % (
        c["n"], _article(opt, c, "card")) for c in cards)
    script = ("<script>if(!location.hash)location.hash='#c%d'</script><noscript><style>.single{display:block}</style></noscript>" % default)
    note = '<p class="pagenote">Option %s, one card on its own page (cards 1 to %d are the pairings already built).</p>' % (
        opt["key"].upper(), len(cards))
    return _doc("Option %s: %s, one card" % (opt["key"].upper(), opt["name"]), LAYOUT_CSS[opt["key"]],
                nav + secs + script, note)


GALLERY_CSS = """
.opt{background:#fff;border:1px solid #bbb;border-radius:8px;padding:.6rem 1rem;margin:1rem 0}
.frames{display:flex;gap:1rem;flex-wrap:wrap;align-items:flex-start}
.fr h3{font-size:.85rem;margin:.2rem 0}
.phone iframe{width:390px;height:640px;border:6px solid #333;border-radius:18px;background:#fff}
.desk .wrap{width:660px;height:400px;border:3px solid #333;overflow:hidden;background:#fff}
.desk iframe{width:1320px;height:800px;border:0;transform:scale(.5);transform-origin:0 0}
"""


def gallery_page(cards):
    parts = ['<p class="pagenote">Four card layouts filled with the same %d pairings. Each is shown on a phone-sized '
             'screen (390 px wide) and a computer-sized one (1320 px wide, shown at half size), as a list of all cards and '
             'as one card on its own page. The pages are live: scroll inside a frame. Open the links to see them full size.</p>' % len(cards)]
    for o in OPTIONS:
        k = o["key"]
        parts.append(
            '<section class="opt"><h2>Option %s: %s</h2><p class="small">%s</p><div class="frames">'
            '<div class="fr phone"><h3>Phone, list</h3><iframe src="option-%s-list.html" title="Option %s on a phone, list"></iframe></div>'
            '<div class="fr phone"><h3>Phone, one card</h3><iframe src="option-%s-card.html#c4" title="Option %s on a phone, one card"></iframe></div>'
            '<div class="fr desk"><h3>Computer, list</h3><div class="wrap"><iframe src="option-%s-list.html" title="Option %s on a computer, list"></iframe></div></div>'
            '<div class="fr desk"><h3>Computer, one card</h3><div class="wrap"><iframe src="option-%s-card.html#c4" title="Option %s on a computer, one card"></iframe></div></div>'
            '</div><p class="small">Full size: <a href="option-%s-list.html">list</a>, <a href="option-%s-card.html#c4">one card</a>.</p></section>' % (
                k.upper(), L.esc(o["name"]), L.esc(o["blurb"]), k, k.upper(), k, k.upper(), k, k.upper(), k, k.upper(), k, k))
    return _doc("Card designs side by side", GALLERY_CSS, "".join(parts))


# --------------------------------------------------------------------------- reading order, for the comparison

def _visible_len(fragment):
    """Characters of visible text; the inside of a closed <details> (the list of giver names) is not counted."""
    fragment = re.sub(r"(?<=</summary>).*?</details>", "", fragment, flags=re.S)
    return len(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fragment)).strip())


def reading_order(opt, c):
    """For one card in the list view: how many characters of visible text come before the first dollar amount, the
    words and the donor's priority (None when the list view does not show it), and how many the card shows in all.
    A rough stand-in for how far a phone reader scrolls; real heights depend on the screen."""
    h = _article(opt, c, "list")
    h = re.sub(r'<div class="more">.*</div>(?=</details>)', "", h, flags=re.S) if opt["key"] == "d" else h
    out = {"total_chars": _visible_len(h)}
    for name, pat in (("first_amount", r'class="(amt|num)"'), ("words", r'class="[^"]*\b(quote|hero)\b'),
                      ("priority", r'class="bubble"')):
        m = re.search(pat, h)
        out[name] = _visible_len(h[:m.start()]) if m else None
    return out
