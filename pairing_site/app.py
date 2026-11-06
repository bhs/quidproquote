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

import sqlalchemy as sa
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from . import auth, config, db, logs, priorities, sources, status  # noqa: F401  (sources: discovery libraries on the path)
from .tables import audit_log, donor_priorities, dropped_pairs, now, pairings, source_data, today

import pairing_cards as pc  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DOUBT_RANK = {"low": 0, "medium": 1, "high": 2}  # the queue lists the least doubtful speaker credit first


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
        db.setup()
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
        with db.reader() as conn:
            rows = conn.execute(
                sa.select(pairings.c.id, pairings.c.slug, pairings.c.official, pairings.c.donor_name, pairings.c.card,
                          pairings.c.published_at, pairings.c.recording_checked, pairings.c.recording_checked_at)
                .where(pairings.c.status == "approved")
                .order_by(pairings.c.published_at.desc(), pairings.c.id)).mappings().all()
        return render(request, "index.html", rows=rows,
                      officials=sorted({r["official"] for r in rows}), donors=sorted({r["donor_name"] for r in rows}))

    @app.get("/pairings/{slug}", response_class=HTMLResponse)
    def pairing(request: Request, slug: str):
        with db.reader() as conn:
            row = conn.execute(sa.select(pairings).where(pairings.c.slug == slug)).mappings().first()
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
        with db.session() as conn:
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
        pending = conn.execute(sa.select(pairings).where(pairings.c.status == "pending")
                               .order_by(pairings.c.meeting_date.desc(), pairings.c.id)).mappings().all()
        # the JSON card is not queried: the stable sort puts the least doubtful credit first, newest meeting first
        pending = sorted(pending, key=lambda r: DOUBT_RANK.get((r["card"].get("speaker_credit") or {}).get("doubt"), 3))
        decided = conn.execute(
            sa.select(pairings.c.id, pairings.c.slug, pairings.c.official, pairings.c.donor_name, pairings.c.status,
                      pairings.c.decided_at, pairings.c.decision_note)
            .where(pairings.c.status != "pending", pairings.c.source != "seed")
            .order_by(pairings.c.decided_at.desc()).limit(10)).mappings().all()
        log = conn.execute(
            sa.select(audit_log.c.at, audit_log.c.actor, audit_log.c.action, audit_log.c.detail, audit_log.c.pairing_id,
                      pairings.c.slug)
            .select_from(audit_log.outerjoin(pairings, pairings.c.id == audit_log.c.pairing_id))
            .order_by(audit_log.c.id.desc()).limit(30)).mappings().all()
        dropped = conn.execute(sa.select(sa.func.count()).select_from(dropped_pairs)).scalar_one()
        return {"pending": pending, "decided": decided, "log": log, "dropped_count": dropped}

    @app.get("/review", response_class=HTMLResponse)
    def review(request: Request, done: str = "", error: str = ""):
        require_admin(request)
        with db.reader() as conn:
            ctx = queue_context(conn)
        return render(request, "review.html", done=done, error=error, **ctx)

    def decide(request, pairing_id, action, checked, note):
        """Records a decision. Returns (row, error): error is a sentence when nothing was changed."""
        with db.session() as conn:  # the write lock is taken at once: the check and the decision are one step
            row = conn.execute(sa.select(pairings).where(pairings.c.id == pairing_id)).mappings().first()
            if not row:
                raise HTTPException(404, "No such pairing")
            if row["status"] != "pending":
                return row, "This pairing was already %s." % row["status"]
            if action == "approve":
                if not checked:
                    return row, "Tick the recording check first: play the recording at the transcript time and confirm the words."
                conn.execute(sa.update(pairings).where(pairings.c.id == pairing_id).values(
                    status="approved", recording_checked=True, recording_checked_at=now(), published_at=today(),
                    decided_at=now(), decision_note=note))
                db.audit(conn, auth.ACTOR, "approved", pairing_id,
                         "recording checked at transcript time %s" % row["first_stamp"] + ("; " + note if note else ""))
            else:
                conn.execute(sa.update(pairings).where(pairings.c.id == pairing_id).values(
                    status="rejected", decided_at=now(), decision_note=note))
                db.audit(conn, auth.ACTOR, "rejected", pairing_id, note)
            return conn.execute(sa.select(pairings).where(pairings.c.id == pairing_id)).mappings().first(), ""

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
        with db.reader() as conn:
            rows = conn.execute(sa.select(dropped_pairs).order_by(
                dropped_pairs.c.reason_kind, dropped_pairs.c.meeting_date.desc(), dropped_pairs.c.id)).mappings().all()
        return render(request, "dropped.html", rows=rows)

    # ------------------------------------------------------------------ the priority form

    def priority_context(conn):
        fams = conn.execute(sa.select(source_data.c.payload).where(source_data.c.name == "families")).scalar_one_or_none()
        rows = conn.execute(sa.select(donor_priorities).order_by(donor_priorities.c.added_at.desc(),
                                                                 donor_priorities.c.id.desc()).limit(12)).mappings().all()
        return {"families": fams["families"] if fams else [], "recent": rows}

    @app.get("/priority", response_class=HTMLResponse)
    def priority_page(request: Request):
        require_admin(request)
        with db.reader() as conn:
            return render(request, "priority.html", form={}, error="", saved=None, **priority_context(conn))

    @app.post("/priority", response_class=HTMLResponse)
    def priority_save(request: Request, family: str = Form(""), url: str = Form(""), words: str = Form(""),
                      section: str = Form(""), page_date: str = Form("")):
        require_admin(request)
        same_origin(request)
        form = {"family": family, "url": url, "words": words, "section": section, "page_date": page_date}
        with db.reader() as conn:
            ctx = priority_context(conn)
        fam = next((f for f in ctx["families"] if f["key"] == family), None)
        error, saved = "", None
        if not fam:
            error = "Choose the donor this priority belongs to."
        else:
            try:
                found = priorities.verify(url, words)  # fetches the page: no database transaction is open meanwhile
                key = "form-%s-%s" % (family, int(time.time()))
                with db.session() as conn:  # the statement and its audit line are written together
                    conn.execute(sa.insert(donor_priorities).values(
                        key=key, family=family, donor=fam["name"], url=found["url"], section=section.strip()[:200],
                        text=found["text"], page_date=page_date.strip()[:40], retrieved=found["retrieved"],
                        kind="page on the organisation's own site", added_by=auth.ACTOR))
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
