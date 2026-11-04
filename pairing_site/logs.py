"""One line of JSON per request on standard output, and one per unhandled error, each with the request's id."""

import datetime
import json
import logging
import sys

ACCESS = "pairing_site.access"


class StdoutHandler(logging.Handler):
    """Writes each record's message as one line to whatever standard output is when it is written, flushed at
    once (not held in a buffer until the process exits)."""

    def emit(self, record):
        try:
            sys.stdout.write(self.format(record) + "\n")
            sys.stdout.flush()
        except Exception:
            self.handleError(record)


def setup():
    logger = logging.getLogger(ACCESS)
    if not any(isinstance(h, StdoutHandler) for h in logger.handlers):
        handler = StdoutHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def emit(level, msg, **fields):
    """Log one JSON line: time, level and msg, then the fields."""
    record = {"time": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds"),
              "level": level, "msg": msg}
    record.update(fields)
    logging.getLogger(ACCESS).log(logging.ERROR if level == "error" else logging.INFO, json.dumps(record, default=str))
