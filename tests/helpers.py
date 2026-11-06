"""A throwaway SQLite file for the tests that need a database."""

import contextlib
import os
import tempfile


@contextlib.contextmanager
def temp_database():
    """Points DATABASE_PATH at a new file in a temporary folder for the block and deletes the folder afterwards.
    The file does not exist yet: the first db.migrate creates it."""
    old = os.environ.get("DATABASE_PATH")
    with tempfile.TemporaryDirectory(prefix="pairing-test-") as folder:
        path = os.path.join(folder, "data", "pairing.db")
        os.environ["DATABASE_PATH"] = path
        try:
            yield path
        finally:
            if old is None:
                os.environ.pop("DATABASE_PATH", None)
            else:
                os.environ["DATABASE_PATH"] = old
