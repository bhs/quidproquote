"""What the glance row of a card shows, cut from the card's own data (presentation only; nothing is added).

window()       an exact stretch of the quote centred on its first shared word, cut at word boundaries;
shorten()      the start of a text, cut at a word boundary;
topic_label()  the donor's own heading for the passage the card rests on, with the page it comes from.

Every cut is a substring of the text it came from, so a highlighted excerpt can be checked against the quote.
"""

from . import sources  # noqa: F401  (puts the discovery libraries on the path)

import pairing_cards as pc  # noqa: E402

WINDOW = 230  # characters of quote shown in the glance row
DONOR_EXCERPT = 150


def window(text, terms, width=WINDOW):
    """(excerpt, cut_before, cut_after): `text` itself when it fits in `width`, else the stretch of about `width`
    characters centred on the first word of the quote that is one of `terms` (the start when there is none)."""
    if len(text) <= width:
        return text, False, False
    rx = pc.term_regex(terms)
    hit = rx.search(text) if rx else None
    centre = (hit.start() + hit.end()) // 2 if hit else width // 2
    start = max(0, min(centre - width // 2, len(text) - width))
    end = min(len(text), start + width)
    first = hit.start() if hit else len(text)  # the cuts never fall inside the shared word
    last = hit.end() if hit else 0
    if start and text[start - 1] != " ":  # begin at a word, never inside one
        space = text.find(" ", start)
        start = space + 1 if 0 <= space < first else text.rfind(" ", 0, start) + 1
    if end < len(text) and text[end] != " ":
        space = text.rfind(" ", start, end)
        if space >= last and space != -1:
            end = space
        else:
            end = text.find(" ", end) if " " in text[end:] else len(text)
    return text[start:end].strip(), start > 0, end < len(text)


def shorten(text, width=DONOR_EXCERPT):
    """(excerpt, cut): the start of `text`, ending at a word."""
    text = " ".join((text or "").split())
    if len(text) <= width:
        return text, False
    cut = text.rfind(" ", 0, width)
    return text[:cut if cut > 0 else width], True


def topic_label(card):
    """{'label', 'page', 'kind'} from the first donor statement that has a heading on the donor's page, or None."""
    for s in card["donor"]["statements"]:
        if (s.get("section") or "").strip():
            return {"label": s["section"].strip(), "page": s["url"], "kind": s.get("kind") or ""}
    return None
