"""Settings read from the environment, each where it is used. A setting the code cannot run without raises
ConfigError naming it; nothing here has a stand-in value for a secret or for a project setting."""

import os


class ConfigError(RuntimeError):
    """A required setting is missing."""


def required(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError("%s is not set" % name)
    return value


def database_path():
    """The SQLite file both the site and the worker open: it lives on the application's attached disk."""
    return required("DATABASE_PATH")


def admin_token():
    return required("ADMIN_TOKEN")


def fetch_contact_email():
    return required("FETCH_CONTACT_EMAIL")


def optional(name, default=""):
    return os.environ.get(name, default).strip()


def number(name, default):
    raw = os.environ.get(name, "").strip()
    return float(raw) if raw else float(default)


def port(name="PORT", default=8080):
    return int(number(name, default))
