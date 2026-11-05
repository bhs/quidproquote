"""Card design mockups: several layouts of the same pairing card, filled with the pairings already built.

Standard library only. Presentation only: no analysis is done here, and no text is rewritten. Every layout is
made of the same fragments (words, donor priority, money, outside spending, reading strip, sources), so what each
card must carry is fixed in one place and only the arrangement differs.

What every card carries, in every layout:
  - the official's words exactly as the transcript has them, in quotation marks, with meeting, date and stamp
  - the donor's priority in the donor's own words, with organisation, page date and a source link
  - one line per receiving committee, each with its own Schedule A total; no total across committees anywhere
  - outside spending in its own container, labelled as a different record; never beside or inside a total
  - highlights only on words literally in both the quote and the donor's words
  - the 'reading, not a finding' strip, 'No cause is claimed.' and the speaker-credit doubt badge
  - a sources row with the transcript, the donor page, the filing ids and the money retrieval date
"""

import html
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
NO_CAUSE = "No cause is claimed."
READING = "Reading, not a finding."
OUTSIDE_LABEL = "Outside spending, kept apart"
OUTSIDE_NOTE = ("A different record from the gifts above: money a committee spent itself on reports naming the "
                "official. It is not a gift to any committee above and is not added to one.")
NO_SUM_NOTE = "One line per committee. Each total is that committee's own; none is added to another."


def esc(t):
    return html.escape(str(t), quote=True)


def term_regex(terms):
    if not terms:
        return None
    alt = "|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True))
    return re.compile(r"(?<!\w)(?:%s)(?!\w)" % alt, re.I)


def marked(text, terms):
    """`text` escaped, each literal occurrence of a term wrapped in <mark>. The text is never altered."""
    rx = term_regex(terms)
    if not rx:
        return esc(text)
    out, pos = [], 0
    for m in rx.finditer(text):
        out += [esc(text[pos:m.start()]), "<mark>%s</mark>" % esc(m.group(0))]
        pos = m.end()
    out.append(esc(text[pos:]))
    return "".join(out)


def dollars(x):
    return "${:,.2f}".format(x) if abs(x - round(x)) > 1e-9 else "${:,.0f}".format(x)


def check_terms(terms, quote, donor_texts, label):
    for t in terms:
        rx = term_regex([t])
        if not rx.search(quote):
            raise ValueError("%s: highlight %r is not in the quote" % (label, t))
        if not any(rx.search(x) for x in donor_texts):
            raise ValueError("%s: highlight %r is not in the donor's words" % (label, t))


# --------------------------------------------------------------------------- the cards, from the data on file

def _load(name):
    with open(os.path.join(HERE, "data", name), encoding="utf-8") as f:
        return json.load(f)


def _from_built(c):
    """A card of the Official funding map's pairing-cards.json, as the mockups use it."""
    q, m, d = c["quote"], c["money"], c["donor"]
    outside = [{"spender": o["spender"], "line": "%s; %d filing%s, %s to %s" % (
        o["stance"], o["filings"], "" if o["filings"] == 1 else "s", o["first"], o["last"]),
        "amount_text": o["amount_text"]} for o in m["outside_spending"]]
    return {
        "n": c["n"], "slug": c["slug"], "stress": "", "title": c["title"], "official": c["official"],
        "quote": {k: q[k] for k in ("text", "meeting", "date", "first_stamp", "last_stamp", "transcript_url")},
        "highlight": c["highlight"], "committees": m["committees"], "outside": outside, "no_money_note": "",
        "donor": {"name": d["name"], "statements": d["statements"], "tie": d["tie"]["text"],
                  "giver_names": d["tie"]["giver_names"]},
        "reading": {"in_common": c["reading"]["in_common"], "differs": c["reading"]["differs"]},
        "doubt": c["speaker_credit"]["doubt"], "doubt_reason": c["speaker_credit"]["reason"],
        "sources": {"transcript": q["transcript_url"], "donor_pages": c["sources"]["donor_pages"],
                    "filing_ids": c["sources"]["filing_ids"], "dataset_url": c["sources"]["dataset_url"],
                    "money_retrieved": c["sources"]["money_retrieved"]},
    }


def _from_outside_example(e, n):
    """The one earlier worked pairing whose money is outside spending only, as a card with no committee lines."""
    st = dict(e["donor"]["statement"])
    outside = []
    for o in e["independent_expenditures"]:
        outside.append({"spender": o["filer_name"], "amount_text": dollars(o["total_24_hour"]),
                        "line": "%s the official; reports naming the candidate for %s, district %s, as filed; "
                                "%d 24-hour rows in %d filings, filed %s to %s" % (
                                    o["stance"], o["office"], o["district"], o["rows_24_hour"], len(o["filing_ids"]),
                                    o["first_filed"], o["last_filed"])})
    q = e["quote"]
    filings = sorted({f for o in e["independent_expenditures"] for f in o["filing_ids"]})
    return {
        "n": n, "slug": "mahmood-growsf-outside", "stress": "Stress case: money is outside spending only",
        "title": "%s \u00d7 %s" % (e["official"]["name"], e["donor"]["name"]), "official": e["official"],
        "quote": {k: q[k] for k in ("text", "meeting", "date", "first_stamp", "last_stamp", "transcript_url")},
        "highlight": ["transfer tax"], "committees": [], "outside": outside,
        "no_money_note": "No Schedule A row from this donor's names was found in the official's two committees "
                         "(%s)." % "; ".join(e["committees_searched"]),
        "donor": {"name": e["donor"]["name"], "statements": [st],
                  "tie": "Tie to the donor recognised by name only (committee names holding: %s)." % e["donor"]["name_words"],
                  "giver_names": 1},
        "reading": e["reading"], "doubt": e["speaker_credit"]["doubt"], "doubt_reason": e["speaker_credit"]["reason"],
        "sources": {"transcript": q["transcript_url"], "donor_pages": [st["url"]], "filing_ids": filings,
                    "dataset_url": "https://data.sf.gov/d/pitq-e56w", "money_retrieved": e["money_retrieved"]},
    }


def load_cards():
    cards = [_from_built(c) for c in _load("pairing-cards.json")["cards"]]
    cards.append(_from_outside_example(_load("outside-spending-example.json"), len(cards) + 1))
    for c in cards:
        texts = [s["section"] + " " + s["text"] for s in c["donor"]["statements"]]
        check_terms(c["highlight"], c["quote"]["text"], texts, "card %d" % c["n"])
        if c["doubt"] not in ("low", "medium", "high"):
            raise ValueError("card %d: doubt %r" % (c["n"], c["doubt"]))
    return cards


def stamp(q):
    return q["first_stamp"] + (" to %s" % q["last_stamp"] if q["last_stamp"] != q["first_stamp"] else "")


def span(m):
    return m["first"] + (" to %s" % m["last"] if m["last"] != m["first"] else "")


def short_cut(text, limit=170):
    """The words cut at a word boundary for a list row. The cut is marked outside the quotation marks."""
    if len(text) <= limit:
        return text, False
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut, True


# --------------------------------------------------------------------------- fragments (same in every layout)

def f_badge(c):
    return '<span class="badge %s">SPEAKER-CREDIT DOUBT: %s</span>' % (c["doubt"], c["doubt"].upper())


def f_official(c, cls=""):
    return '<div class="official %s"><div class="name">%s</div><div class="role">%s</div></div>' % (
        cls, esc(c["official"]["name"]), esc(c["official"]["role"]))


def f_words(c, cls="quote"):
    q, T = c["quote"], c["highlight"]
    return ('<blockquote class="%s">&ldquo;%s&rdquo;</blockquote><div class="small cite">%s, %s, transcript time %s '
            '&middot; <a href="%s">transcript</a></div>' % (
                cls, marked(q["text"], T), esc(q["meeting"]), q["date"], stamp(q), esc(q["transcript_url"])))


def f_priority(c):
    T, d = c["highlight"], c["donor"]
    out = ['<div class="bubble"><div class="bubble-h">%s: stated priority</div><div class="small tie">%s</div>' % (
        esc(d["name"]), esc(d["tie"]))]
    pages = []
    for s in d["statements"]:
        out.append('<div class="small sect">%s</div><blockquote>&ldquo;%s&rdquo;</blockquote>' % (
            marked(s["section"], T), marked(s["text"], T)))
        if s["url"] not in pages:
            pages.append(s["url"])
            out.append('<div class="small cite">%s %s; <a href="%s">source page</a>; retrieved %s</div>' % (
                esc(d["name"]), "page dated %s" % s["page_date"] if s["page_date"] else "page undated",
                esc(s["url"]), s["retrieved"]))
    out.append("</div>")
    return "".join(out)


def names_html(givers):
    """The giver names as filed: listed when there are few, else a count that opens to the whole list."""
    if len(givers) <= 3:
        return esc("; ".join(givers))
    return "<details><summary>%d giver names as filed</summary>%s</details>" % (len(givers), esc("; ".join(givers)))


def f_committee_line(m):
    givers = m["givers_as_filed"]
    shown = names_html(givers)
    return ('<div class="money"><div class="amt-row"><span class="amt">%s</span> <span class="amt-l">Schedule A, this committee only</span></div>'
            '<div class="cm"><b>%s</b> <span class="small">(filer %s)</span></div>'
            '<div class="small">%s; %d row%s, %s</div><div class="small">Giver%s as filed: %s</div></div>' % (
                esc(m["schedule_a_total_text"]), esc(m["committee"]), esc(m["filer"]), esc(m["kind"]), m["rows"],
                "" if m["rows"] == 1 else "s", span(m), "" if len(givers) == 1 else "s", shown))


def f_outside(c):
    if not c["outside"]:
        return ""
    rows = "".join('<div class="ox"><span class="amt">%s</span> %s<div class="small">%s</div></div>' % (
        esc(o["amount_text"]), esc(o["spender"]), esc(o["line"])) for o in c["outside"])
    return ('<div class="outside"><div class="outside-h">%s</div><div class="small">%s</div>%s'
            '<div class="small">These lines are separate reports; they are not added to each other.</div></div>' % (
                OUTSIDE_LABEL, OUTSIDE_NOTE, rows))


def f_money(c, heading="Money in"):
    out = ['<div class="moneyzone"><div class="zone-h">%s</div>' % esc(heading)]
    if c["committees"]:
        out += [f_committee_line(m) for m in c["committees"]]
        extra = [m for m in c["committees"] if m["repeats_not_counted"] or m["h24_only_rows"]]
        for m in extra:
            if m["repeats_not_counted"]:
                out.append('<div class="small">%s: %d 24-hour repeat%s of a Schedule A row, listed in the filing, not counted.</div>' % (
                    esc(m["committee"]), m["repeats_not_counted"], "" if m["repeats_not_counted"] == 1 else "s"))
        out.append('<div class="small nosum">%s</div>' % NO_SUM_NOTE)
    elif c["no_money_note"]:
        out.append('<div class="small">%s</div>' % esc(c["no_money_note"]))
    out.append(f_outside(c) + "</div>")
    return "".join(out)


def f_reading(c, reason=True):
    shared = ", ".join("&ldquo;%s&rdquo;" % esc(t) for t in c["highlight"]) or "none of substance, so nothing is highlighted"
    return ('<div class="strip">%s <b>%s</b> In common: %s Where they differ: %s %s'
            '<div class="small">Highlighted: words literally in both the quote and the donor\'s words (%s).%s</div></div>' % (
                f_badge(c), READING, esc(c["reading"]["in_common"]), esc(c["reading"]["differs"]), NO_CAUSE, shared,
                (" Speaker credit: %s" % esc(c["doubt_reason"])) if reason else ""))


def f_sources(c):
    s = c["sources"]
    pages = ", ".join('<a href="%s">%s</a>' % (esc(u), esc(u.split("//", 1)[-1].split("/")[0])) for u in s["donor_pages"])
    return ('<div class="sources"><b>Sources:</b> <a href="%s">transcript</a>; donor page: %s; filing ids (<a href="%s">'
            'Transactions dataset</a>): %s; money retrieved %s.</div>' % (
                esc(s["transcript"]), pages, esc(s["dataset_url"]), esc(", ".join(s["filing_ids"])), s["money_retrieved"]))


def f_chips(c):
    return "".join('<span class="chip"><mark>%s</mark></span>' % esc(t) for t in c["highlight"]) or \
        '<span class="chip none">no shared words highlighted</span>'


def f_stress(c):
    return '<div class="stress">%s</div>' % esc(c["stress"]) if c["stress"] else ""
