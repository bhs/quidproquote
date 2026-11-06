"""The pairing site: FastAPI with Jinja templates and HTMX.

Public:  /               approved pairings as cards, filterable by official or donor (a little JavaScript)
         /pairings/<slug>  one card at its own URL
         /status          the worker's summary as JSON
Sign-in: /login           the ADMIN_TOKEN sets a signed session cookie
Admin:   /review          the queue: approve (needs the recording check ticked) or reject, inline through HTMX
         /review/dropped  pairs the AI filter dropped, with reasons
         /priority        add a donor's priority from its own site (the pasted words must be on the page) or from a
                          news report (outlet, date and whose words are required); edit one in place, and read the
                          earlier wording of an edited one

Every approval, rejection, sign-in and priority added or edited is written to the audit log with its time and action.
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

from . import auth, cards, config, db, logs, priorities, sources, status  # noqa: F401  (sources: discovery libraries on the path)

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
    templates.env.filters["whose"] = priorities.whose_label

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
            rows = conn.execute("SELECT id, slug, official, donor_key, donor_name, meeting_id, quote_text, card, published_at, "
                                "recording_checked, recording_checked_at FROM pairings WHERE status = 'approved' "
                                "ORDER BY published_at DESC, id").fetchall()
            cache = {}
            rows = [cards.live_row(conn, r, cache) for r in rows]
        return render(request, "index.html", rows=rows,
                      officials=sorted({r["official"] for r in rows}), donors=sorted({r["donor_name"] for r in rows}))

    @app.get("/pairings/{slug}", response_class=HTMLResponse)
    def pairing(request: Request, slug: str):
        with db.session() as conn:
            row = conn.execute("SELECT * FROM pairings WHERE slug = ?", (slug,)).fetchone()
            if row:
                row = cards.live_row(conn, row)
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
        cache = {}
        pending = [cards.live_row(conn, r, cache) for r in pending]
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
                with db.session() as conn:
                    row = cards.live_row(conn, row)
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

    # ------------------------------------------------------------------ priorities: add, edit in place, history

    PRIORITY_TYPES = ("own", "reported")

    def priority_context(conn, **extra):
        fams = conn.execute("SELECT payload FROM source_data WHERE name = 'families'").fetchone()
        ctx = {"families": fams["payload"]["families"] if fams else [], "recent": priorities.current_rows(conn),
               "form_type": "", "form": {}, "error": "", "saved": None, "done": "", "editing": None,
               "whose_options": priorities.WHOSE}
        ctx.update(extra)
        return ctx

    def edit_form(row, form=None, error=""):
        """The values of the edit form of a priority: its own, or the ones just submitted."""
        return {"id": row["id"], "error": error, "form": form or {
            "url": row["url"], "words": row["text"], "section": row["section"], "page_date": row["page_date"],
            "outlet": row["outlet"], "whose_words": row["whose_words"]}}

    def get_priority(conn, priority_id):
        row = priorities.get(conn, priority_id)
        if not row:
            raise HTTPException(404, "No such priority")
        return row

    @app.get("/priority", response_class=HTMLResponse)
    def priority_page(request: Request, type: str = "", done: str = ""):
        require_admin(request)
        with db.session() as conn:
            return render(request, "priority.html", **priority_context(
                conn, form_type=type if type in PRIORITY_TYPES else "", done=done))

    @app.get("/priority/form", response_class=HTMLResponse)
    def priority_form(request: Request, type: str = "own"):
        """The short form for one type, swapped in under the two buttons."""
        require_admin(request)
        if type not in PRIORITY_TYPES:
            raise HTTPException(404, "No such kind of priority")
        if not is_htmx(request):
            return RedirectResponse("/priority?type=" + type, status_code=303)
        with db.session() as conn:
            return render(request, "_priority_form.html", **priority_context(conn, form_type=type))

    @app.post("/priority", response_class=HTMLResponse)
    def priority_save(request: Request, family: str = Form(""), url: str = Form(""), words: str = Form(""),
                      section: str = Form(""), page_date: str = Form(""), type: str = Form("own"),
                      outlet: str = Form(""), whose_words: str = Form("")):
        require_admin(request)
        same_origin(request)
        ptype = type if type in PRIORITY_TYPES else "own"
        form = {"family": family, "url": url, "words": words, "section": section, "page_date": page_date,
                "outlet": outlet, "whose_words": whose_words}
        with db.session() as conn:
            ctx = priority_context(conn, form_type=ptype)
        fam = next((f for f in ctx["families"] if f["key"] == family), None)
        error, saved = "", None
        if not fam:
            error = "Choose the donor this priority belongs to."
        else:
            try:
                _, saved = priorities.add(ptype, fam, form, auth.ACTOR)  # fetches the page before any write lock
                form = {}
                with db.session() as conn:
                    ctx = priority_context(conn)
            except priorities.PriorityError as exc:
                error = str(exc)
        ctx.update(form=form, error=error, saved=saved)
        return render(request, "priority.html", status_code=422 if error else 200, **ctx)

    @app.get("/priority/{priority_id}/row", response_class=HTMLResponse)
    def priority_row(request: Request, priority_id: int):
        """The row as listed: where Cancel and the history's Hide put it back."""
        require_admin(request)
        if not is_htmx(request):
            return RedirectResponse("/priority", status_code=303)
        with db.session() as conn:
            return render(request, "_priority_row.html", r=get_priority(conn, priority_id))

    @app.get("/priority/{priority_id}/edit", response_class=HTMLResponse)
    def priority_edit_page(request: Request, priority_id: int):
        require_admin(request)
        with db.session() as conn:
            row = get_priority(conn, priority_id)
            if row["replaced_at"]:
                return RedirectResponse("/priority", status_code=303)
            if is_htmx(request):
                return render(request, "_priority_edit.html", r=row, editing=edit_form(row),
                              whose_options=priorities.WHOSE)
            return render(request, "priority.html", **priority_context(conn, editing=edit_form(row)))

    @app.post("/priority/{priority_id}/edit", response_class=HTMLResponse)
    def priority_edit_save(request: Request, priority_id: int, url: str = Form(""), words: str = Form(""),
                           section: str = Form(""), page_date: str = Form(""), outlet: str = Form(""),
                           whose_words: str = Form("")):
        require_admin(request)
        same_origin(request)
        form = {"url": url, "words": words, "section": section, "page_date": page_date, "outlet": outlet,
                "whose_words": whose_words}
        try:
            new = priorities.edit(priority_id, form, auth.ACTOR)
        except priorities.PriorityError as exc:
            with db.session() as conn:
                row = get_priority(conn, priority_id)
                if is_htmx(request) and isinstance(exc, priorities.PriorityGone):
                    return render(request, "_priority_row.html", r=priorities.current_version(conn, row))
                if is_htmx(request):  # htmx swaps only a 200: the error is part of the small form
                    return render(request, "_priority_edit.html", r=row, editing=edit_form(row, form, str(exc)),
                                  whose_options=priorities.WHOSE)
                return render(request, "priority.html", status_code=422,
                              **priority_context(conn, editing=edit_form(row, form, str(exc))))
        if is_htmx(request):
            return render(request, "_priority_row.html", r=new, just_edited=True)
        return RedirectResponse("/priority?done=" + urllib.parse.quote("Saved as a new version; the earlier wording is kept."),
                                status_code=303)

    @app.get("/priority/{priority_id}/history", response_class=HTMLResponse)
    def priority_history(request: Request, priority_id: int):
        """The earlier wording of an edited priority, newest first, each with the date it was replaced."""
        require_admin(request)
        with db.session() as conn:
            row = get_priority(conn, priority_id)
            versions = priorities.earlier_versions(conn, row)
        return render(request, "_priority_history.html" if is_htmx(request) else "priority_history.html",
                      r=row, versions=versions)

    return app


app = create_app()
