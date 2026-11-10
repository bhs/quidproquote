"""One-off: give every pairing stored before the confidence chips existed its four chips.

    python -m pairing_site.backfill

The chips are read from what each stored card already holds (pipeline.confidence), so no pairing, quote, analysis
or caveat changes. A pairing a person has already checked against the recording gets its speaker credit and topic
match marked VERIFIED, as a fresh verification would, and the log says so. Safe to run again: it rewrites the same
chips, keeps the verified marks and logs a pairing's marks once.
"""

import sys

from . import db, pipeline

ACTOR = "backfill"


def run(out=sys.stdout):
    """Writes the chips of every pairing. Returns (pairings written, pairings newly marked verified)."""
    db.migrate()
    written = verified = 0
    with db.session(write=True) as conn:
        for row in conn.execute("SELECT id, card, recording_checked, first_stamp FROM pairings ORDER BY id").fetchall():
            card = row["card"]
            already = any(c["verified"] for c in card.get("chips") or [])
            card["chips"] = pipeline.confidence(card)
            if row["recording_checked"]:
                marked = pipeline.mark_verified(card)
                if not already:
                    db.audit(conn, ACTOR, "chips verified", row["id"],
                             "%s marked VERIFIED by the backfill: the pairing was already checked against the recording "
                             "(transcript time %s)" % (" and ".join(marked), row["first_stamp"]))
                    verified += 1
            conn.execute("UPDATE pairings SET card = ? WHERE id = ?", (db.json_value(card), row["id"]))
            written += 1
    out.write("Chips written for %d pairing%s; %d marked verified.\n" % (written, "" if written == 1 else "s", verified))
    return written, verified


if __name__ == "__main__":
    run()
