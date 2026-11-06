"""A throwaway SQLite file for the tests that need a database."""

import contextlib
import os
import shutil
import tempfile

from pairing_site import db


@contextlib.contextmanager
def temp_database():
    """Points DATABASE_PATH at a new file in a new temporary directory for the block and removes it afterwards.
    The file is not created: the code under test creates it, as it does on a first start."""
    folder = tempfile.mkdtemp(prefix="pairing-test-")
    path = os.path.join(folder, "data", "app.db")
    old = os.environ.get("DATABASE_PATH")
    os.environ["DATABASE_PATH"] = path
    try:
        yield path
    finally:
        db.dispose(path)
        if old is None:
            os.environ.pop("DATABASE_PATH", None)
        else:
            os.environ["DATABASE_PATH"] = old
        shutil.rmtree(folder, ignore_errors=True)
