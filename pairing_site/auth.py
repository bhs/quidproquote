"""Sign-in with the ADMIN_TOKEN. A correct token sets a signed, expiring session cookie; the signing key is
derived from the token, so changing the token signs everyone out. The token itself is never stored or logged."""

import hashlib
import hmac
import secrets
import time

from . import config

COOKIE = "pairing_session"
TTL_S = 12 * 3600
ACTOR = "maintainer"


def _key():
    return hashlib.sha256(("pairing-site-session|" + config.admin_token()).encode("utf-8")).digest()


def _sign(payload):
    return hmac.new(_key(), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def token_ok(given):
    return hmac.compare_digest(hashlib.sha256((given or "").encode("utf-8")).digest(),
                               hashlib.sha256(config.admin_token().encode("utf-8")).digest())


def make_session(now=None):
    payload = "v1.%d.%s" % (int(now if now is not None else time.time()) + TTL_S, secrets.token_hex(8))
    return payload + "." + _sign(payload)


def session_ok(value, now=None):
    parts = (value or "").split(".")
    if len(parts) != 4 or parts[0] != "v1":
        return False
    payload = ".".join(parts[:3])
    if not hmac.compare_digest(parts[3], _sign(payload)):
        return False
    try:
        return int(parts[1]) > (now if now is not None else time.time())
    except ValueError:
        return False
