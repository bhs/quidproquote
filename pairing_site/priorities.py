"""The priority form's check: fetch the donor's page, and accept the pasted words only when they appear on it
word for word (typographic quotes and dashes straightened, whitespace collapsed). The retrieval date is the
day the check ran, set here and never taken from the form."""

import datetime
import ipaddress
import re
import socket
import urllib.parse

from . import sources  # noqa: F401

import fmap_lib as fl  # noqa: E402

MIN_WORDS = 6

OWN_SITE = "own-site"
NEWS = "news report"  # the `kind` of a reported priority; the other kinds name a page on the organisation's own site
OWN_KIND = "page on the organisation's own site"
WHOSE_WORDS = {  # what the pasted words are, for a news report
    "reporter": "The reporter's description of the donor's position",
    "donor-quoted": "The donor's own words, quoted in the report",
    "third-party": "Someone else's words, quoted in the report",
}
PAGE_DATE = re.compile(r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$")


class PriorityError(ValueError):
    """The form's input cannot be accepted; the message says why, for the person who filled it in."""


def check_public_url(url):
    """The URL's parts, refusing anything that is not an http(s) page on a public address."""
    parts = urllib.parse.urlsplit((url or "").strip())
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise PriorityError("The link must be a full web address starting with http:// or https://.")
    try:
        infos = socket.getaddrinfo(parts.hostname, parts.port or (443 if parts.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise PriorityError("The address %s did not resolve (%s)." % (parts.hostname, exc))
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise PriorityError("The address %s is not a public web page." % parts.hostname)
    return parts


def check_page_date(text, required, today=None):
    """The page date as typed (the column stays text): empty, or a real YYYY, YYYY-MM or YYYY-MM-DD that is not in
    the future. A news report needs one."""
    text = (text or "").strip()
    if not text:
        if required:
            raise PriorityError("Enter the date the report was published, like 2026-10-08.")
        return ""
    m = PAGE_DATE.match(text)
    try:
        if not m:
            raise ValueError(text)
        day = datetime.date(int(m.group(1)), int(m.group(2) or 1), int(m.group(3) or 1))
    except ValueError:
        raise PriorityError("The page date %r is not a date; write it like 2026-10-08 (or 2026-10, or 2026)." % text[:40])
    if day > (today or datetime.date.today()):
        raise PriorityError("The page date %s is in the future." % text)
    return text


def check_source(source_type, outlet, whose_words, page_date, today=None):
    """{'kind', 'outlet', 'whose_words', 'page_date'} for the form's source fields, or PriorityError with a
    one-line reason. A page on the organisation's own site carries no outlet and no whose-words choice."""
    if source_type not in (OWN_SITE, NEWS):
        raise PriorityError("Choose whether the source is the organisation's own site or a news report.")
    if source_type == OWN_SITE:
        return {"kind": OWN_KIND, "outlet": "", "whose_words": "", "page_date": check_page_date(page_date, False, today)}
    outlet = " ".join((outlet or "").split())
    if not outlet:
        raise PriorityError("Name the outlet that published the report.")
    if len(outlet) > 120:
        raise PriorityError("The outlet's name is too long (120 characters at most).")
    if whose_words not in WHOSE_WORDS:
        raise PriorityError("Say whose words the pasted text is: the reporter's, the donor's quoted, or someone else's.")
    return {"kind": NEWS, "outlet": outlet, "whose_words": whose_words,
            "page_date": check_page_date(page_date, True, today)}


def words_on_page(page_html, words):
    """True when `words` (squashed) occur verbatim in the visible text of the page."""
    needle = fl.squash(words)
    return bool(needle) and needle in fl.page_text(page_html)


def verify(url, words, fetch=None):
    """{'url', 'text', 'retrieved'} for words found verbatim on the page. Raises PriorityError otherwise."""
    words = fl.squash(words)
    if len(words.split()) < MIN_WORDS:
        raise PriorityError("Paste the donor's sentence or two, at least %d words, exactly as the page shows them." % MIN_WORDS)
    if not (url or "").strip():
        raise PriorityError("Give the link to the page that shows the words.")
    check_public_url(url)
    try:
        raw = (fetch or fl.fetch_page)(url.strip())
    except OSError as exc:
        raise PriorityError("The page could not be fetched (%s: %s); nothing was saved." % (type(exc).__name__, exc))
    if not words_on_page(raw, words):
        raise PriorityError("Those words are not on the page as fetched just now, word for word; nothing was saved. "
                            "Copy them from the page itself.")
    return {"url": url.strip(), "text": words, "retrieved": fl.today()}
