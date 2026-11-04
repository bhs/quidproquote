"""Settings read from the environment. A setting the site cannot run without fails loudly at startup."""

import os

REQUIRED = {
    "ADMIN_PASSWORD": "the password for the review queue and priority form",
    "FETCH_CONTACT_EMAIL": "the contact email put in the user agent of the site's fetching",
    "DATABASE_PATH": "the path of the SQLite file that keeps every record",
}


class ConfigError(RuntimeError):
    """A required setting is missing."""


def load(env=None):
    env = os.environ if env is None else env
    missing = [k for k in REQUIRED if not (env.get(k) or "").strip()]
    if missing:
        raise ConfigError("missing settings: %s" % "; ".join("%s (%s)" % (k, REQUIRED[k]) for k in missing))
    return {
        "admin_password": env["ADMIN_PASSWORD"],
        "fetch_contact_email": env["FETCH_CONTACT_EMAIL"].strip(),
        "database_path": env["DATABASE_PATH"].strip(),
        # how the daily job reads the city's calendar; ordinary tuning with working defaults
        "fetch_year": int(env.get("FETCH_YEAR") or 0) or None,
        "fetch_max_new_meetings": int(env.get("FETCH_MAX_NEW_MEETINGS") or 10),
        "fetch_interval_hours": float(env.get("FETCH_INTERVAL_HOURS") or 24),
    }
