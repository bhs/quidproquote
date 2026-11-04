"""A throwaway database on the server DATABASE_URL points at, for the tests that need Postgres."""

import contextlib
import os
import urllib.parse
import uuid

import psycopg


def _with_db(url, name):
    return urllib.parse.urlsplit(url)._replace(path="/" + name).geturl()


@contextlib.contextmanager
def temp_database():
    """Creates a database, points DATABASE_URL at it for the block and drops it afterwards."""
    base = os.environ["DATABASE_URL"]
    name = "test_" + uuid.uuid4().hex[:12]
    with psycopg.connect(_with_db(base, "postgres"), autocommit=True) as admin:
        admin.execute('CREATE DATABASE "%s"' % name)
    old = os.environ["DATABASE_URL"]
    os.environ["DATABASE_URL"] = _with_db(base, name)
    try:
        yield os.environ["DATABASE_URL"]
    finally:
        os.environ["DATABASE_URL"] = old
        with psycopg.connect(_with_db(base, "postgres"), autocommit=True) as admin:
            admin.execute('DROP DATABASE IF EXISTS "%s" WITH (FORCE)' % name)
