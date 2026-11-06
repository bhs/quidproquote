"""The pairing site: FastAPI with Jinja templates and HTMX.

Public:  /               approved pairings as cards, filterable by official or donor (a little JavaScript)
         /pairings/<slug>  one card at its own URL
         /status          the worker's summary as JSON
Sign-in: /login           the ADMIN_TOKEN sets a signed session cookie
Admin:   /review          the queue: approve (needs the recording check ticked) or reject, inline through HTMX
         /review/dropped  pairs the AI filter dropped, with reasons
         /priority        add a donor's priority: the page is fetched and the pasted words must be on it

Every approval, rejection, sign-in and priority added is written to the audit log with its time and action.
"""

import contextlib
import datetime
import html
import os
import time
import urllib.parse

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from . import auth, config, db, logs, priorities, sources, status  # noqa: F401  (sources: discovery libraries on the path)

import pairing_cards as pc  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


DOUBT_ORDER = {"low": 0, "medium": 1, "high": 2}  # the queue lists the least doubtful speaker credit first


class LoginRequired(Exception):
    def __init__(self, next_path):
        self.next_path = next_path


def is_htmx(request):
    return request.headers.get("hx-request") == "true"


def local_path(path, default="/review"):
    """A redirect target on this site only."""
    return path if path.startswith("/") and not path.startswith("//") and "\\" not in path else default


def marked(text, terms):
    return Markup(pc.marked(text, terms or [], lambda t: html.escape(t, quote=True)))


def quoted(text):
    return pc.quoted(text)


def create_app():
    @contextlib.asynccontextmanager
    async def lifespan(app):
        config.admin_token()  # a site nobody can sign in to is a misconfiguration
        db.migrate()
        yield

    app = FastAPI(title="Pairings", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(logs.RequestLogMiddleware)
    app.mount("/static", StaticFiles(directory=os.path.join(HERE, "static")), name="static")
    templates = Jinja2Templates(directory=os.path.join(HERE, "templates"))
    templates.env.filters["marked"] = marked
    templates.env.filters["quoted"] = quoted

    def admin(request):
        try:
            return auth.session_ok(request.cookies.get(auth.COOKIE))
        except config.ConfigError:
            return False

    def render(request, name, status_code=200, **ctx):
        ctx.update(is_admin=admin(request), now=datetime.datetime.now(datetime.timezone.utc))
        return templates.TemplateResponse(request, name, ctx, status_code=status_code)

    def require_admin(request):
        if not admin(request):
            raise LoginRequired(request.url.path)

    def same_origin(request):
        origin = request.headers.get("origin")
        if origin and urllib.parse.urlsplit(origin).netloc != request.headers.get("host", ""):
            raise HTTPException(403, "Cross-site request refused")

    @app.exception_handler(LoginRequired)
    def login_required(request, exc):
        if is_htmx(request):
            return HTMLResponse("Sign in again", status_code=401, headers={"HX-Redirect": "/login"})
        return RedirectResponse("/login?next=" + urllib.parse.quote(exc.next_path), status_code=303)

    # ------------------------------------------------------------------ public pages

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        with db.session() as conn:
            rows = conn.execute("SELECT id, slug, official, donor_name, card, published_at, recording_checked, "
                                "recording_checked_at FROM pairings WHERE status = 'approved' "
                                "ORDER BY published_at DESC, id").fetchall()
        return render(request, "index.html", rows=rows,
                      officials=sorted({r["official"] for r in rows}), donors=sorted({r["donor_name"] for r in rows}))

    @app.get("/pairings/{slug}", response_class=HTMLResponse)
    def pairing(request: Request, slug: str):
        with db.session() as conn:
            row = conn.execute("SELECT * FROM pairings WHERE slug = ?", (slug,)).fetchone()
        if not row or (row["status"] != "approved" and not admin(request)):
            raise HTTPException(404, "No such pairing")
        return render(request, "pairing.html", row=row)

    @app.get("/status")
    def worker_status():
        try:
            return JSONResponse(status.current())
        except Exception as exc:
            logs.emit("error", "status failed", error=str(exc))
            return JSONResponse({"error": "the database did not answer: %s" % exc}, status_code=503)

    # ------------------------------------------------------------------ sign-in

    @app.get("/login", response_class=HTMLResponse)
    def login_page(request: Request, next: str = "/review"):
        return render(request, "login.html", next=local_path(next), error="")

    @app.post("/login")
    def login(request: Request, token: str = Form(""), next: str = Form("/review")):
        same_origin(request)
        if not auth.token_ok(token):
            time.sleep(0.5)
            return render(request, "login.html", status_code=401, next=local_path(next),
                          error="That token is not right.")
        with db.session(write=True) as conn:
            db.audit(conn, auth.ACTOR, "signed in")
        response = RedirectResponse(local_path(next), status_code=303)
        secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
        response.set_cookie(auth.COOKIE, auth.make_session(), max_age=auth.TTL_S, httponly=True, samesite="lax",
                            secure=secure, path="/")
        return response

    @app.post("/logout")
    def logout(request: Request):
        same_origin(request)
        response = RedirectResponse("/", status_code=303)
        response.delete_cookie(auth.COOKIE, path="/")
        return response

    # ------------------------------------------------------------------ the review queue

    def queue_context(conn):
        pending = conn.execute("SELECT * FROM pairings WHERE status = 'pending' ORDER BY meeting_date DESC, id").fetchall()
        pending.sort(key=lambda r: DOUBT_ORDER.get(r["card"].get("speaker_credit", {}).get("doubt"), len(DOUBT_ORDER)))  # stable
        decided = conn.execute("SELECT id, slug, official, donor_name, status, decided_at, decision_note FROM pairings "
                               "WHERE status <> 'pending' AND source <> 'seed' ORDER BY decided_at DESC LIMIT 10").fetchall()
        log = conn.execute("SELECT a.at, a.actor, a.action, a.detail, a.pairing_id, p.slug FROM audit_log a "
                           "LEFT JOIN pairings p ON p.id = a.pairing_id ORDER BY a.id DESC LIMIT 30").fetchall()
        dropped = conn.execute("SELECT count(*) AS n FROM dropped_pairs").fetchone()["n"]
        return {"pending": pending, "decided": decided, "log": log, "dropped_count": dropped}

    @app.get("/review", response_class=HTMLResponse)
    def review(request: Request, done: str = "", error: str = ""):
        require_admin(request)
        with db.session() as conn:
            ctx = queue_context(conn)
        return render(request, "review.html", done=done, error=error, **ctx)

    def decide(request, pairing_id, action, checked, note):
        """Records a decision. Returns (row, error): error is a sentence when nothing was changed. The write lock
        is held from the read of the row to the audit entry, so two decisions on one pairing cannot both apply."""
        with db.session(write=True) as conn:
            row = conn.execute("SELECT * FROM pairings WHERE id = ?", (pairing_id,)).fetchone()
            if not row:
                raise HTTPException(404, "No such pairing")
            if row["status"] != "pending":
                return row, "This pairing was already %s." % row["status"]
            if action == "approve":
                if not checked:
                    return row, "Tick the recording check first: play the recording at the transcript time and confirm the words."
                stamp = db.now()
                conn.execute("UPDATE pairings SET status = 'approved', recording_checked = 1, "
                             "recording_checked_at = ?, published_at = ?, decided_at = ?, "
                             "decision_note = ? WHERE id = ?", (stamp, db.today(), stamp, note, pairing_id))
                db.audit(conn, auth.ACTOR, "approved", pairing_id,
                         "recording checked at transcript time %s" % row["first_stamp"] + ("; " + note if note else ""))
            else:
                conn.execute("UPDATE pairings SET status = 'rejected', decided_at = ?, decision_note = ? WHERE id = ?",
                             (db.now(), note, pairing_id))
                db.audit(conn, auth.ACTOR, "rejected", pairing_id, note)
            return conn.execute("SELECT * FROM pairings WHERE id = ?", (pairing_id,)).fetchone(), ""

    def decision_response(request, row, error):
        if is_htmx(request):
            if error:
                return render(request, "_queue_item.html", row=row, card=row["card"], error=error)
            return render(request, "_decided.html", row=row)
        if error:
            return RedirectResponse("/review?error=" + urllib.parse.quote(error), status_code=303)
        return RedirectResponse("/review?done=" + urllib.parse.quote("%s: %s" % (row["status"], row["slug"])),
                                status_code=303)

    @app.post("/review/{pairing_id}/approve")
    def approve(request: Request, pairing_id: int, recording_checked: str = Form(""), note: str = Form("")):
        require_admin(request)
        same_origin(request)
        row, error = decide(request, pairing_id, "approve", recording_checked == "on", note.strip()[:500])
        return decision_response(request, row, error)

    @app.post("/review/{pairing_id}/reject")
    def reject(request: Request, pairing_id: int, note: str = Form("")):
        require_admin(request)
        same_origin(request)
        row, error = decide(request, pairing_id, "reject", False, note.strip()[:500])
        return decision_response(request, row, error)

    @app.get("/review/dropped", response_class=HTMLResponse)
    def dropped(request: Request):
        require_admin(request)
        with db.session() as conn:
            rows = conn.execute("SELECT * FROM dropped_pairs ORDER BY reason_kind, meeting_date DESC, id").fetchall()
        return render(request, "dropped.html", rows=rows)

    # ------------------------------------------------------------------ the priority form

    def priority_context(conn):
        fams = conn.execute("SELECT payload FROM source_data WHERE name = 'families'").fetchone()
        rows = conn.execute("SELECT * FROM donor_priorities ORDER BY added_at DESC, id DESC LIMIT 12").fetchall()
        return {"families": fams["payload"]["families"] if fams else [], "recent": rows}

    @app.get("/priority", response_class=HTMLResponse)
    def priority_page(request: Request):
        require_admin(request)
        with db.session() as conn:
            return render(request, "priority.html", form={}, error="", saved=None, **priority_context(conn))

    @app.post("/priority", response_class=HTMLResponse)
    def priority_save(request: Request, family: str = Form(""), url: str = Form(""), words: str = Form(""),
                      section: str = Form(""), page_date: str = Form("")):
        require_admin(request)
        same_origin(request)
        form = {"family": family, "url": url, "words": words, "section": section, "page_date": page_date}
        with db.session() as conn:
            ctx = priority_context(conn)
        fam = next((f for f in ctx["families"] if f["key"] == family), None)
        error, saved = "", None
        if not fam:
            error = "Choose the donor this priority belongs to."
        else:
            try:
                found = priorities.verify(url, words)  # fetches the page: done before the write lock is taken
                key = "form-%s-%s" % (family, int(time.time()))
                with db.session(write=True) as conn:
                    conn.execute(
                        "INSERT INTO donor_priorities (key, family, donor, url, section, text, page_date, retrieved, kind, "
                        "added_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (key, family, fam["name"], found["url"], section.strip()[:200], found["text"],
                         page_date.strip()[:40], found["retrieved"], "page on the organisation's own site", auth.ACTOR))
                    db.audit(conn, auth.ACTOR, "priority added", None,
                             "%s: %s (words found verbatim on the page; retrieved %s)" % (fam["name"], found["url"], found["retrieved"]))
                    ctx = priority_context(conn)
                saved = found
                form = {}
            except priorities.PriorityError as exc:
                error = str(exc)
        return render(request, "priority.html", status_code=422 if error else 200, form=form, error=error,
                      saved=saved, **ctx)

    return app


app = create_app()
