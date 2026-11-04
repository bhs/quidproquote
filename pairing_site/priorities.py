"""The priority form's check: fetch the donor's page, and accept the pasted words only when they appear on it
word for word (typographic quotes and dashes straightened, whitespace collapsed). The retrieval date is the
day the check ran, set here and never taken from the form."""

import ipaddress
import socket
import urllib.parse

from . import sources  # noqa: F401

import fmap_lib as fl  # noqa: E402

MIN_WORDS = 6


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


def words_on_page(page_html, words):
    """True when `words` (squashed) occur verbatim in the visible text of the page."""
    needle = fl.squash(words)
    return bool(needle) and needle in fl.page_text(page_html)


def verify(url, words, fetch=None):
    """{'url', 'text', 'retrieved'} for words found verbatim on the page. Raises PriorityError otherwise."""
    words = fl.squash(words)
    if len(words.split()) < MIN_WORDS:
        raise PriorityError("Paste the donor's sentence or two, at least %d words, exactly as the page shows them." % MIN_WORDS)
    check_public_url(url)
    try:
        raw = (fetch or fl.fetch_page)(url.strip())
    except OSError as exc:
        raise PriorityError("The page could not be fetched (%s: %s); nothing was saved." % (type(exc).__name__, exc))
    if not words_on_page(raw, words):
        raise PriorityError("Those words are not on the page as fetched just now, word for word; nothing was saved. "
                            "Copy them from the page itself.")
    return {"url": url.strip(), "text": words, "retrieved": fl.today()}
