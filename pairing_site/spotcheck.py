"""The spot check of the cards' quotes against the stored transcripts:

    python -m pairing_site.spotcheck                 # check every published and waiting card; hide and requeue failures
    python -m pairing_site.spotcheck --report-only   # only report, change nothing

A card passes when its quote is exactly the text stored with the pairing, that text is word for word in the
meeting's stored caption transcript, each highlighted word is in both the quote and a donor statement on the card,
and the highlighted rendering gives back the quote unchanged once its <mark> tags are taken out. A published card
that fails goes back to the review queue (so the public pages no longer show it) and the failure is written to the
audit log. The same check blocks the approval of a card that fails (see app.decide). Exits 1 when any card fails.
"""

import html
import re
import sys

from . import db, pipeline, sources  # noqa: F401

import fmap_lib as fl  # noqa: E402
import pairing_cards as pc  # noqa: E402

ACTOR = "spot check"


def problems(conn, row, rows_cache=None):
    """Sentences saying how the card of this pairing row differs from the stored transcript; empty when it passes."""
    card = row["card"] or {}
    quote = (card.get("quote") or {}).get("text")
    if not isinstance(quote, str) or not quote:
        return ["the card has no quote text"]
    out = []
    if quote != row["quote_text"]:
        out.append("the card's quote is not the quote text stored with the pairing")
    cache = rows_cache if rows_cache is not None else {}
    if row["meeting_id"] not in cache:
        meeting = conn.execute("SELECT captions FROM meetings WHERE id = ?", (row["meeting_id"],)).fetchone()
        cache[row["meeting_id"]] = pipeline.parse_captions(meeting["captions"]) if meeting else None
    rows = cache[row["meeting_id"]]
    if rows is None:
        out.append("the meeting's transcript is not stored")
    elif not fl.is_verbatim(rows, quote):
        out.append("the quote is not word for word in the stored transcript")
    terms = card.get("highlight") or []
    donor_texts = [(s.get("section") or "") + " " + s["text"] for s in card.get("donor", {}).get("statements", [])]
    try:
        pc.check_terms(terms, quote, donor_texts, row["slug"])
    except ValueError as exc:
        out.append(str(exc).split(": ", 1)[-1])
    shown = pc.marked(quote, terms, lambda t: html.escape(t, quote=True))
    if html.unescape(re.sub(r"</?mark>", "", shown)) != quote:
        out.append("the highlighted rendering changes the quote's words")
    return out


def run(requeue=True, out=sys.stdout):
    """Checks every published and waiting card. Returns [(slug, status, [problems])] for the cards that fail."""
    failed = []
    with db.session(write=requeue) as conn:
        cache = {}
        rows = conn.execute("SELECT * FROM pairings WHERE status IN ('approved', 'pending') ORDER BY id").fetchall()
        for row in rows:
            found = problems(conn, row, cache)
            if not found:
                continue
            failed.append((row["slug"], row["status"], found))
            if requeue and row["status"] == "approved":
                conn.execute("UPDATE pairings SET status = 'pending', recording_checked = 0, recording_checked_at = NULL, "
                             "published_at = NULL, decided_at = NULL WHERE id = ?", (row["id"],))
                db.audit(conn, ACTOR, "spot check failed: card hidden and requeued", row["id"], "; ".join(found))
        total = len(rows)
    for slug, status, found in failed:
        hidden = " (hidden and back in the review queue)" if requeue and status == "approved" else ""
        out.write("FAIL %s [%s]%s: %s\n" % (slug, status, hidden, "; ".join(found)))
    out.write("Spot check: %d card%s checked, %d failed.\n" % (total, "" if total == 1 else "s", len(failed)))
    return failed


if __name__ == "__main__":
    sys.exit(1 if run(requeue="--report-only" not in sys.argv[1:]) else 0)
