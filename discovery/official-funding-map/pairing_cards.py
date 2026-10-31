"""Pairing cards: each pairing shown as one self-contained card (presentation only; no analysis is done here).

    from pairing_cards import build_cards, render_cards_md, render_cards_html

A card has three zones. Left: the money in (one line per receiving committee, each with its own Schedule A
total, never summed across committees) and, beneath it, the donor's stated priority as its own bubble. Centre:
the official's name and role. Right: the official's exact caption words. Beneath: a 'reading, not a finding'
strip carrying the speaker-credit doubt as a badge, and a sources row.

Highlighting marks only words literally shared by the quote and the donor's own words (terms listed per pairing
in picks.json as `highlight`); `build_cards` refuses a term that is not literally in both. Nothing is rewritten.
A pairing with no money found is not a card. Standard library only.
"""

import html
import re

import fmap_lib as fl

NO_CAUSE = "No cause is claimed."
DOUBT_LEVELS = ("low", "medium", "high")


def term_regex(terms):
    """Whole-word, case-insensitive match of any term (longest first); None when there are no terms."""
    if not terms:
        return None
    alt = "|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True))
    return re.compile(r"(?<!\w)(?:%s)(?!\w)" % alt, re.I)


def marked(text, terms, esc):
    """`text` escaped by `esc`, with each literal occurrence of a term wrapped in <mark>. The text itself is
    never altered: only the tags are added around it."""
    rx = term_regex(terms)
    if not rx:
        return esc(text)
    out, pos = [], 0
    for m in rx.finditer(text):
        out.append(esc(text[pos:m.start()]))
        out.append("<mark>%s</mark>" % esc(m.group(0)))
        pos = m.end()
    out.append(esc(text[pos:]))
    return "".join(out)


def check_terms(terms, quote, donor_texts, pid):
    """Every highlighted term must be literally in the quote and in the donor's own words."""
    rx_all = [(t, term_regex([t])) for t in terms]
    for t, rx in rx_all:
        if not rx.search(quote):
            raise ValueError("pairing %s: highlight %r is not in the quote" % (pid, t))
        if not any(rx.search(x) for x in donor_texts):
            raise ValueError("pairing %s: highlight %r is not in the donor's words" % (pid, t))


def committee_kind(c):
    """The kind of committee in the card's three words: ballot-measure carrying the official's name,
    officeholder, or own. A committee for another office says so."""
    rel, name = c["relation"], c["filer_name"]
    if rel == "measure":
        return "ballot-measure committee carrying the official's name"
    kind = "officeholder committee" if ("OFFICEHOLDER" in name.upper() or c["filer_type"] == "470 [Officeholder]") \
        else "own committee"
    if rel == "own-other":
        kind += ", for another office (%s)" % fl.office_of(name)
    return kind


def tie_note(p, snap, fams):
    """How the givers in this pairing are recognised as the donor's: by Filers id, or by name only. Rows are
    grouped by giver name as filed; a donor with chapter or sub-committees is one bubble, many names."""
    seen = {}
    for c in p["money"]["per"].values():
        for r in c["a"] + c["repeat"] + c["only"]:
            name, cid = fl.donor_name(r), r.get("committee_id") or ""
            _, how = fl.family_of(fams, name, cid)
            seen[(name, cid)] = how
    by_id = sorted({"%s (%s)" % (cid, snap["filers_lookup"][cid][0]["filer_name"] if cid in snap["filers_lookup"] else "not in Filers")
                    for (n, cid), h in seen.items() if h == "id"})
    by_name = sorted({n for (n, cid), h in seen.items() if h == "name"})
    ids_name = sorted({cid for (n, cid), h in seen.items() if h == "name" and cid})
    resolved = sorted({cid for cid in ids_name if cid in snap["filers_lookup"]})
    parts = []
    if by_id:
        parts.append("by Filers id: %s" % "; ".join(by_id))
    if by_name:
        s = "by name only (%d giver name%s as filed)" % (len(by_name), "" if len(by_name) == 1 else "s")
        if ids_name and not resolved:
            s += "; the FPPC ids on those rows do not resolve in the Filers dataset"
        elif resolved:
            s += "; FPPC id%s that resolve%s in the Filers dataset: %s" % (
                "" if len(resolved) == 1 else "s", "s" if len(resolved) == 1 else "", ", ".join(
                    "%s ('%s')" % (cid, snap["filers_lookup"][cid][0]["filer_name"]) for cid in resolved))
        elif not ids_name:
            s += "; the rows carry no FPPC id"
        parts.append(s)
    n_names = len({n for (n, cid) in seen})
    return {"how": parts, "giver_names": n_names, "text": "Tie to the donor recognised " + "; ".join(parts) + "."}


def committee_line(c):
    cm = c["committee"]
    d = sorted(fl.day(r["calculated_date"]) for r in c["a"])
    givers = sorted({fl.donor_name(r) for r in c["a"] + c["repeat"] + c["only"]})
    line = {"committee": cm["filer_name"], "filer": cm["filer_nid"], "kind": committee_kind(cm),
            "schedule_a_total": c["a_sum"], "schedule_a_total_text": fl.dollars(c["a_sum"]),
            "rows": len(c["a"]), "first": d[0] if d else "", "last": d[-1] if d else "",
            "givers_as_filed": givers,
            "filings": sorted({"%s (v%s)" % (r["filing_id_number"], _ver(r)) for r in c["a"]}),
            "filing_ids": sorted({r["filing_id_number"] for r in c["a"] + c["only"]}),
            "repeats_not_counted": len(c["repeat"]), "h24_only_total": c["only_sum"] if c["only"] else None,
            "h24_only_rows": len(c["only"])}
    return line


def _ver(r):
    v = r.get("filing_version")
    try:
        return str(int(float(v)))
    except (TypeError, ValueError):
        return str(v or "")


def build_cards(pairs, snap, fams):
    """One card per pairing that has money. Raises ValueError when a highlight is not literally shared."""
    cards = []
    for n, p in enumerate(pairs, 1):
        if not p["money"]["per"]:
            continue
        pk, mt, q, off = p["pk"], p["meeting"], p["quote"], p["official"]
        terms = pk.get("highlight", [])
        donor_texts = [s["section"] + " " + s["text"] for s in p["statements"]]
        check_terms(terms, q["text"], donor_texts, pk["id"])
        role = off["office"] + (", District %s" % off["district"] if off["district"] else "")
        money = [committee_line(c) for c in p["money"]["per"].values()]
        outside = [{"spender": o["payer"], "stance": "supporting" if o["stance"] == "S" else "opposing",
                    "amount": o["amount"], "amount_text": fl.dollars(o["amount"]), "filings": o["filings"],
                    "first": o["d0"], "last": o["d1"]} for o in p["money"]["outside"]]
        statements = [{"section": s["section"], "text": s["text"], "url": s["url"], "page_date": s["page_date"],
                       "retrieved": s["retrieved"], "kind": s["kind"]} for s in p["statements"]]
        filings = sorted({f for m in money for f in m["filing_ids"]})
        cards.append({
            "n": n, "id": pk["id"], "slug": pk["slug"],
            "title": "%s \u00d7 %s" % (off["official"], p["family"]["name"]),
            "official": {"name": off["official"], "role": role},
            "quote": {"text": q["text"], "meeting": mt["body"], "date": mt["date"], "first_stamp": q["first_stamp"],
                      "last_stamp": q["last_stamp"], "transcript_url": mt["url"], "retrieved": mt["retrieved"]},
            "highlight": terms,
            "money": {"committees": money, "outside_spending": outside, "retrieved": snap["retrieved"],
                      "data_loaded_at": snap["data_loaded_at"], "dataset_url": fl.DATASET_PAGE,
                      "note": "One line per receiving committee. Each Schedule A total is that committee's own and is "
                              "never added to another's."},
            "donor": {"name": p["family"]["name"], "kind": p["family"]["kind"], "statements": statements,
                      "tie": tie_note(p, snap, fams)},
            "reading": {"in_common": pk["overlap"], "differs": pk["stance"], "cause": NO_CAUSE},
            "speaker_credit": {"doubt": pk["speaker"]["doubt"], "reason": pk["speaker"]["doubt_reason"]},
            "sources": {"transcript": mt["url"], "donor_pages": sorted({s["url"] for s in p["statements"]}),
                        "filing_ids": filings, "dataset_url": fl.DATASET_PAGE, "money_retrieved": snap["retrieved"]},
        })
        if cards[-1]["speaker_credit"]["doubt"] not in DOUBT_LEVELS:
            raise ValueError("pairing %s: doubt %r is not low, medium or high" % (pk["id"], pk["speaker"]["doubt"]))
    return cards


# --------------------------------------------------------------------------- shared small pieces

def esc_html(t):
    return html.escape(t, quote=False)


def esc_md(t):
    """HTML escape, and the characters markdown tables and math would misread."""
    return html.escape(t, quote=False).replace("|", "&#124;").replace("$", "&#36;")


def donor_groups(card):
    """The donor's statements grouped by page (several statements on one page share one source line)."""
    groups = []
    for s in card["donor"]["statements"]:
        for g in groups:
            if g["url"] == s["url"]:
                g["items"].append(s)
                break
        else:
            groups.append({"url": s["url"], "page_date": s["page_date"], "retrieved": s["retrieved"], "items": [s]})
    return groups


def quoted(text):
    return text if text.startswith('"') else '"%s"' % text


def extras(m, money_fmt):
    out = []
    if m["h24_only_rows"]:
        out.append("Also on 24-hour reports with no Schedule A row yet, apart and not in the total: %s." % money_fmt(m["h24_only_total"]))
    if m["repeats_not_counted"]:
        out.append("%d 24-hour repeat%s of a Schedule A row, listed in the filing, not counted." % (
            m["repeats_not_counted"], "" if m["repeats_not_counted"] == 1 else "s"))
    return out


# --------------------------------------------------------------------------- markdown (for findings.md)

def card_md(card):
    E, T = esc_md, card["highlight"]
    L = []
    for m in card["money"]["committees"]:
        extra = " ".join(extras(m, fl.dollars))
        rng = m["first"] + (" to %s" % m["last"] if m["last"] != m["first"] else "")
        L.append("<b>%s</b> Schedule A, %s (filer %s)<br>%s; %d row%s, %s<br>Giver%s as filed: %s%s" % (
            E(m["schedule_a_total_text"]), E(m["committee"]), m["filer"], E(m["kind"]), m["rows"],
            "" if m["rows"] == 1 else "s", rng, "" if len(m["givers_as_filed"]) == 1 else "s",
            E("; ".join(m["givers_as_filed"])), (" <i>" + E(extra) + "</i>") if extra else ""))
    money = "<b>Money in</b> (one line per committee; totals are never summed across committees)<br><br>" + "<br><br>".join(L)
    for o in card["money"]["outside_spending"]:
        money += ("<br><br><i>Outside spending, kept apart (form 496; not a gift to a committee above):</i> %s, %s, %s, "
                  "%d filings, %s to %s" % (E(o["spender"]), o["stance"], E(o["amount_text"]), o["filings"], o["first"], o["last"]))
    bub = ["<blockquote><b>%s's stated priority</b><br><i>%s</i>" % (E(card["donor"]["name"]), E(card["donor"]["tie"]["text"]))]
    for g in donor_groups(card):
        for s in g["items"]:
            bub.append("<br><br>%s<br>%s" % (E(s["section"]) if not T else marked(s["section"], T, E),
                                              marked(quoted(s["text"]), T, E)))
        bub.append("<br><i>%s; <a href=\"%s\">%s</a>; retrieved %s</i>" % (
            "page dated %s" % g["page_date"] if g["page_date"] else "page undated", g["url"], "source page", g["retrieved"]))
    bub.append("</blockquote>")
    left = money + "<br><br>" + "".join(bub)
    mid = "<b>%s</b><br>%s" % (E(card["official"]["name"]), E(card["official"]["role"]))
    q = card["quote"]
    right = "%s<br><br><i>%s, %s, transcript time %s%s</i>" % (
        marked('"%s"' % q["text"], T, E), E(q["meeting"]), q["date"], q["first_stamp"],
        " to %s" % q["last_stamp"] if q["last_stamp"] != q["first_stamp"] else "")
    s = card["sources"]
    fil = ", ".join(s["filing_ids"])
    out = ["### Card %d: %s" % (card["n"], card["title"]), "",
           "| Money in, then the donor's priority | The official | The official's exact words |", "|---|---|---|",
           "| %s | %s | %s |" % (left.replace("\n", " "), mid, right), ""]
    out.append("> **Reading, not a finding.** `SPEAKER-CREDIT DOUBT: %s` In common: %s Where they differ: %s %s" % (
        card["speaker_credit"]["doubt"].upper(), esc_md(card["reading"]["in_common"]), esc_md(card["reading"]["differs"]), NO_CAUSE))
    out += [">", "> Highlighted words are the ones literally in both the quote and the donor's words: %s." % (
        ", ".join('"%s"' % t for t in T) if T else "none of substance, so nothing is highlighted")]
    out += ["", "**Sources:** [transcript](%s) (%s, %s); donor page%s: %s; filing ids (Schedule A and 24-hour, [Transactions dataset](%s)): %s; money retrieved %s." % (
        s["transcript"], q["meeting"], q["date"], "" if len(s["donor_pages"]) == 1 else "s",
        ", ".join("[%s](%s)" % (u.split("//", 1)[-1].split("/")[0], u) for u in s["donor_pages"]), s["dataset_url"], fil,
        s["money_retrieved"]), ""]
    return out


def render_cards_md(cards, level=3):
    L = []
    for c in cards:
        L += card_md(c)
    return L


# --------------------------------------------------------------------------- stand-alone HTML page

CSS = """
body{font:15px/1.45 system-ui,sans-serif;margin:0;background:#f4f1ea;color:#222}
main{max-width:1180px;margin:0 auto;padding:1rem}
h1{font-size:1.4rem} .lede{max-width:70ch}
ol.cards{list-style:none;padding:0;margin:0}
.card{background:#fff;border:1px solid #bbb;border-radius:8px;margin:1.2rem 0;padding:.8rem 1rem}
.card h2{font-size:1.1rem;margin:.1rem 0 .6rem}
.zones{display:grid;grid-template-columns:1.25fr .6fr 1fr;gap:.9rem}
@media(max-width:820px){.zones{grid-template-columns:1fr}}
.zone h3{font-size:.8rem;text-transform:uppercase;letter-spacing:.04em;color:#555;margin:.1rem 0 .4rem}
.money{border-left:4px solid #2f6f4f;padding:.2rem .6rem;margin:.4rem 0;background:#f3f8f5}
.money .amt{font-weight:700}
.small{font-size:.85rem;color:#444}
.bubble{background:#eef2fb;border:1px solid #9fb3e0;border-radius:14px;padding:.6rem .8rem;margin-top:.8rem}
.bubble blockquote,.quote{margin:.4rem 0;padding:0}
.official{text-align:center;align-self:center}
.official .name{font-size:1.15rem;font-weight:700}
.quote{border-left:4px solid #777;padding-left:.7rem;font-family:Georgia,serif}
mark{background:#ffe066;padding:0 .1em}
.strip{margin-top:.8rem;background:#f7f7f7;border:1px dashed #999;padding:.5rem .7rem}
.badge{display:inline-block;border-radius:3px;padding:.05rem .45rem;font-weight:700;font-size:.8rem;color:#fff;margin-right:.4rem}
.badge.low{background:#2f6f4f}.badge.medium{background:#b07a00}.badge.high{background:#a33}
.sources{margin-top:.6rem;font-size:.85rem;color:#333;border-top:1px solid #ddd;padding-top:.4rem}
"""


def card_html(card):
    E, T = esc_html, card["highlight"]
    ml = []
    for m in card["money"]["committees"]:
        rng = m["first"] + (" to %s" % m["last"] if m["last"] != m["first"] else "")
        ex = "".join('<div class="small"><i>%s</i></div>' % E(x) for x in extras(m, fl.dollars))
        ml.append('<div class="money"><span class="amt">%s</span> Schedule A to <b>%s</b> <span class="small">(filer %s)</span>'
                  '<div class="small">%s; %d row%s, %s</div><div class="small">Giver%s as filed: %s</div>%s</div>' % (
                      E(m["schedule_a_total_text"]), E(m["committee"]), m["filer"], E(m["kind"]), m["rows"],
                      "" if m["rows"] == 1 else "s", rng, "" if len(m["givers_as_filed"]) == 1 else "s",
                      E("; ".join(m["givers_as_filed"])), ex))
    ml.append('<div class="small">One line per receiving committee; totals are never summed across committees.</div>')
    for o in card["money"]["outside_spending"]:
        ml.append('<div class="money" style="border-color:#a33;background:#fbf1f1"><b>Outside spending, kept apart</b> '
                  '(form 496; not a gift to any committee above): %s, %s, %s, %d filings, %s to %s</div>' % (
                      E(o["spender"]), o["stance"], E(o["amount_text"]), o["filings"], o["first"], o["last"]))
    bub = ['<div class="bubble"><b>%s: stated priority</b><div class="small"><i>%s</i></div>' % (
        E(card["donor"]["name"]), E(card["donor"]["tie"]["text"]))]
    for g in donor_groups(card):
        for s in g["items"]:
            bub.append('<div class="small">%s</div><blockquote>%s</blockquote>' % (marked(s["section"], T, E), marked(quoted(s["text"]), T, E)))
        bub.append('<div class="small">%s; <a href="%s">source page</a>; retrieved %s</div>' % (
            "page dated %s" % g["page_date"] if g["page_date"] else "page undated", E(g["url"]), g["retrieved"]))
    bub.append("</div>")
    q = card["quote"]
    stamp = q["first_stamp"] + (" to %s" % q["last_stamp"] if q["last_stamp"] != q["first_stamp"] else "")
    s = card["sources"]
    credit = card["speaker_credit"]
    return """<li class="card" id="card-%d"><h2>Card %d: %s</h2>
<div class="zones">
<div class="zone"><h3>Money in, then the donor's priority</h3>%s%s</div>
<div class="zone official"><h3>The official</h3><div class="name">%s</div><div>%s</div></div>
<div class="zone"><h3>The official's exact words</h3><div class="quote">%s</div>
<div class="small">%s, %s, transcript time %s</div></div>
</div>
<div class="strip"><span class="badge %s">SPEAKER-CREDIT DOUBT: %s</span><b>Reading, not a finding.</b>
In common: %s Where they differ: %s %s
<div class="small">Highlighted: words literally in both the quote and the donor's words (%s). Credit: %s</div></div>
<div class="sources"><b>Sources:</b> <a href="%s">transcript</a> (%s, %s); donor page%s: %s;
filing ids, <a href="%s">Transactions dataset</a>: %s; money retrieved %s.</div></li>""" % (
        card["n"], card["n"], E(card["title"]), "".join(ml), "".join(bub), E(card["official"]["name"]),
        E(card["official"]["role"]), marked('"%s"' % q["text"], T, E), E(q["meeting"]), q["date"], stamp,
        credit["doubt"], credit["doubt"].upper(), E(card["reading"]["in_common"]), E(card["reading"]["differs"]), NO_CAUSE,
        ", ".join('"%s"' % E(t) for t in T) if T else "none of substance, so nothing is highlighted", E(credit["reason"]),
        E(s["transcript"]), E(q["meeting"]), q["date"], "" if len(s["donor_pages"]) == 1 else "s",
        ", ".join('<a href="%s">%s</a>' % (E(u), E(u.split("//", 1)[-1].split("/")[0])) for u in s["donor_pages"]),
        E(s["dataset_url"]), E(", ".join(s["filing_ids"])), s["money_retrieved"])


def render_cards_html(cards):
    body = "\n".join(card_html(c) for c in cards)
    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>Pairing cards: San Francisco officials, a donor's priority and the money</title><style>%s</style></head><body><main>"
            "<h1>Pairing cards</h1><p class=\"lede\">One card per pairing that has money found. Money, the donor's own stated "
            "priority, the official's exact caption words and the sources are shown side by side. Each card is a reading, not "
            "a finding: %s Written by <code>build_map.py</code>.</p><ol class=\"cards\">\n%s\n</ol></main></body></html>\n" % (
                CSS, "nothing here says why anyone said or gave anything.", body))
