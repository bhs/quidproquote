"""A card as it is drawn: the stored card read against what is current.

The card is a snapshot built when the pairing was found. When it is drawn, two things are looked at again:

quote       the official's words are compared with the stored transcript text. When they differ the transcript's
            text is shown (never the other way round) and the difference is logged. The text is only ever
            replaced whole, never trimmed or normalised; highlighting adds markup around it at render time.
priorities  each donor statement on the card is replaced by the version of that priority now in force (an edit
            inserts a new version, see priorities.py). The highlighted words are worked out again whenever the
            quote or a statement is not what the stored card has, and are always words literally in both.
"""

from . import logs, pipeline, priorities

import fmap_lib as fl  # noqa: E402

SAME, REPLACED, UNVERIFIED = "same", "replaced", "unverified"


def transcript_quote(captions, card_text, quote_text, first_stamp, last_stamp):
    """(text, state): the quote as the stored transcript has it, and whether the card's copy was the same
    (SAME), differed so the transcript's text is returned (REPLACED), or could not be found in the transcript at
    all so the card's text is returned as it is (UNVERIFIED)."""
    rows = pipeline.parse_captions(captions)
    whole = " ".join(t for _, t in rows)
    if quote_text and quote_text in whole:
        truth = quote_text
    elif card_text in whole:
        truth = card_text
    else:
        try:
            truth = fl.extract_quote(rows, first_stamp, last_stamp)["text"]
        except ValueError:
            return card_text, UNVERIFIED
    return truth, SAME if card_text == truth else REPLACED


def statement_of(row):
    """A donor statement of a card, from a donor_priorities row."""
    return {"section": row["section"], "text": row["text"], "url": row["url"], "page_date": row["page_date"],
            "retrieved": str(row["retrieved"]), "kind": row["kind"], "key": row["key"],
            "reported": bool(row["whose_words"]), "outlet": row["outlet"],
            "whose": priorities.whose_label(row["whose_words"]), "page_checked": bool(row["page_checked"]),
            "updated": row["added_at"].date() if row["supersedes_key"] else None}


def _shape(s):
    return (s["section"], s["text"], s["url"], s["page_date"])


def current_statements(conn, card, family):
    """The card's donor statements as the priorities now in force have them. A statement that matches no stored
    priority is kept as the card has it."""
    out, seen = [], set()
    for s in card["donor"]["statements"]:
        row = None
        if s.get("key"):
            row = conn.execute("SELECT * FROM donor_priorities WHERE key = ?", (s["key"],)).fetchone()
        if not row:
            row = conn.execute("SELECT * FROM donor_priorities WHERE family = ? AND url = ? AND text = ? "
                               "ORDER BY id LIMIT 1", (family, s["url"], s["text"])).fetchone()
        if not row:
            out.append(dict(s, reported=False, outlet="", whose="", page_checked=True, updated=None))
            continue
        cur = priorities.current_version(conn, row)
        if cur["id"] not in seen:
            seen.add(cur["id"])
            out.append(statement_of(cur))
    return out


def live_card(conn, row, cache=None):
    """(card, note): the card of a pairing row as it is drawn now; note is the quote's state (SAME, REPLACED or
    UNVERIFIED). The stored card is not changed."""
    stored = row["card"]
    if not stored.get("quote") or not stored.get("donor"):
        return stored, SAME
    card = dict(stored, quote=dict(stored["quote"]), donor=dict(stored["donor"]), sources=dict(stored.get("sources", {})))
    cache = {} if cache is None else cache
    mid = row["meeting_id"]
    if mid not in cache:
        found = conn.execute("SELECT captions FROM meetings WHERE id = ?", (mid,)).fetchone()
        cache[mid] = found["captions"] if found else None
    note = UNVERIFIED
    if cache[mid] is not None:
        text, note = transcript_quote(cache[mid], stored["quote"]["text"], row.get("quote_text"),
                                      stored["quote"]["first_stamp"], stored["quote"]["last_stamp"])
        if note == REPLACED:
            logs.emit("warning", "card quote differs from the stored transcript text; showing the transcript text",
                      slug=row["slug"], card_quote=stored["quote"]["text"][:300], transcript_text=text[:300])
            card["quote"]["text"] = text
        elif note == UNVERIFIED:
            logs.emit("warning", "card quote not found in the stored transcript", slug=row["slug"])
    statements = current_statements(conn, stored, row["donor_key"])
    card["donor"]["statements"] = statements
    card["sources"]["donor_pages"] = sorted({s["url"] for s in statements})
    if note == REPLACED or [_shape(s) for s in statements] != [_shape(s) for s in stored["donor"]["statements"]]:
        subject = pipeline.subject_terms(statements)
        candidates = list(stored.get("highlight", [])) + subject["anchor"] + subject["topic"]
        card["highlight"] = pipeline.highlight_terms(card["quote"]["text"], statements, candidates)
    return card, note


def live_row(conn, row, cache=None):
    """The pairing row with its card replaced by the card as drawn now, and quote_note set."""
    card, note = live_card(conn, row, cache)
    return dict(row, card=card, quote_note=note)
