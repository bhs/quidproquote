"""One line of JSON per event on standard output, written as it happens: a line per request when the response
is complete, and a line per unhandled error carrying the same request id and the traceback. Request bodies and
secrets are never logged."""

import datetime
import json
import sys
import time
import traceback
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import PlainTextResponse


def emit(level, msg, **fields):
    line = {"time": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds"),
            "level": level, "msg": msg}
    line.update(fields)
    sys.stdout.write(json.dumps(line, default=str) + "\n")
    sys.stdout.flush()


def new_request_id(header=None):
    header = (header or "").strip()
    return header[:80] if header else uuid.uuid4().hex


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        rid = new_request_id(request.headers.get("x-request-id"))
        request.state.request_id = rid
        t0 = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:  # unhandled: logged with its traceback, answered as a plain 500
            emit("error", "unhandled error", request_id=rid, error=str(exc) or type(exc).__name__,
                 stack="".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
            response = PlainTextResponse("Internal server error (request %s)" % rid, status_code=500)
        response.headers["X-Request-Id"] = rid
        emit("info", "request", request_id=rid, method=request.method, path=request.url.path,
             status=response.status_code, duration_ms=round((time.perf_counter() - t0) * 1000, 2))
        return response
