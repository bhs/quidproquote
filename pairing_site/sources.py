"""Puts the discovery libraries on the import path and names how the site's fetching identifies itself.

The libraries are the ones the earlier hops wrote and left under discovery/: fmap_lib and pairing_cards (money
by committee and filing, donor families, caption quotes, cards), ff_lib and legistar (the Legistar calendar and
transcripts, the chair's spoken cue matched to the roster, passages that hit a subject), trial_lib (measure
names, phrases and named things in a text) and judge (the Anthropic model call).
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DISCOVERY = os.path.join(ROOT, "discovery")
OFM = os.path.join(DISCOVERY, "official-funding-map")
FFP = os.path.join(DISCOVERY, "funder-first-pairings")
MMC = os.path.join(DISCOVERY, "matching-methods-comparison")
OFM_DATA = os.path.join(OFM, "data")
FFP_DATA = os.path.join(FFP, "data")

for _path in (MMC, FFP, OFM):  # official-funding-map first: its fmap_lib is the one used
    if _path not in sys.path:
        sys.path.insert(0, _path)

import fmap_lib  # noqa: E402
import legistar  # noqa: E402


def identify_fetcher(contact_email):
    """Every request to the city, the Ethics Commission's data or a donor's page names who to write to."""
    agent = "Mozilla/5.0 (compatible; pairing-site fetcher; contact: %s)" % contact_email
    fmap_lib.UA = agent
    legistar.UA = agent
    return agent
