"""The pairing site: FastAPI with Jinja templates and HTMX.

Public:  /               approved pairings as cards, filterable by official or donor (a little JavaScript)
         /pairings/<slug>  one card at its own URL
         /status          the worker's summary as JSON
Sign-in: /login           the ADMIN_TOKEN sets a signed session cookie
Admin:   /review          the queue: approve (needs the recording check ticked) or reject, inline through HTMX
         /review/dropped  pairs the AI filter dropped, with reasons
         /priority        add a donor's priority (own site or news report): the page is fetched and the pasted words must be on it
         /priority/<key>/edit  correct one: prefilled and checked against the page again; the old row goes to the log

Every approval, rejection, sign-in and priority added or edited is written to the audit log with its time and action.
"""

import contextlib
import datetime
import html
import json
import os
import time
import urllib.parse

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from . import auth, config, db, logs, priorities, sources, spotcheck, status  # noqa: F401  (sources: discovery libraries on the path)

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
    templates.env.globals.update(NEWS_KIND=priorities.NEWS, WHOSE_WORDS=priorities.WHOSE_WORDS)

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
                failed = spotcheck.problems(conn, row)
                if failed:
                    reason = "Not approved: the card's quote does not match the stored transcript (%s)." % "; ".join(failed)
                    db.audit(conn, auth.ACTOR, "approval blocked by the spot check", pairing_id, "; ".join(failed))
                    return row, reason
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
        edits = {r["k"]: r["n"] for r in conn.execute(
            "SELECT json_extract(detail, '$.key') AS k, count(*) AS n FROM audit_log "
            "WHERE action = 'priority edited' GROUP BY k")}
        return {"families": fams["payload"]["families"] if fams else [], "recent": rows, "edits": edits,
                "whose_words": priorities.WHOSE_WORDS, "editing": None, "earlier": []}

    def form_of(row):
        news = row["kind"] == priorities.NEWS
        return {"family": row["family"], "url": row["url"], "words": row["text"], "section": row["section"],
                "page_date": row["page_date"], "source_type": priorities.NEWS if news else priorities.OWN_SITE,
                "outlet": row["outlet"], "whose_words": row["whose_words"]}

    def earlier_versions(conn, key):
        """The superseded versions of one priority, newest first: each edit wrote the row as it was before."""
        out = []
        for r in conn.execute("SELECT at, detail FROM audit_log WHERE action = 'priority edited' "
                              "AND json_extract(detail, '$.key') = ? ORDER BY id DESC", (key,)):
            out.append(dict(json.loads(r["detail"])["before"], replaced_at=r["at"]))
        return out

    @app.get("/priority", response_class=HTMLResponse)
    def priority_page(request: Request, edited: str = ""):
        require_admin(request)
        with db.session() as conn:
            return render(request, "priority.html", form={"source_type": priorities.OWN_SITE}, error="",
                          saved=None, edited=edited, **priority_context(conn))

    def get_priority(conn, key):
        row = conn.execute("SELECT * FROM donor_priorities WHERE key = ?", (key,)).fetchone()
        if not row:
            raise HTTPException(404, "No such priority")
        return row

    def priority_submit(request, form, key=None):
        """Checks the form and saves it: a new row, or (key given) an update of that row after writing the old row in
        full to the audit log. The page is fetched before the write lock is taken. Returns the page to show."""
        with db.session() as conn:
            ctx = priority_context(conn)
            if key:
                ctx["editing"] = get_priority(conn, key)
                ctx["earlier"] = earlier_versions(conn, key)
        fam = next((f for f in ctx["families"] if f["key"] == form["family"]), None)
        error, saved = "", None
        try:
            if not fam:
                raise priorities.PriorityError("Choose the donor this priority belongs to.")
            src = priorities.check_source(form["source_type"], form["outlet"], form["whose_words"], form["page_date"])
            found = priorities.verify(form["url"], form["words"])
            section = form["section"].strip()[:200]
            if key:
                with db.session(write=True) as conn:
                    old = get_priority(conn, key)
                    kind = old["kind"] if src["kind"] == priorities.OWN_KIND and old["kind"] != priorities.NEWS else src["kind"]
                    db.audit(conn, auth.ACTOR, "priority edited", None,
                             json.dumps({"key": key, "before": old}, default=str, ensure_ascii=False))
                    conn.execute(
                        "UPDATE donor_priorities SET family = ?, donor = ?, url = ?, section = ?, text = ?, page_date = ?, "
                        "retrieved = ?, kind = ?, outlet = ?, whose_words = ? WHERE key = ?",
                        (form["family"], fam["name"], found["url"], section, found["text"], src["page_date"],
                         found["retrieved"], kind, src["outlet"], src["whose_words"], key))
                return RedirectResponse("/priority?edited=" + urllib.parse.quote(key), status_code=303)
            new_key = "form-%s-%s" % (form["family"], time.time_ns())
            with db.session(write=True) as conn:
                conn.execute(
                    "INSERT INTO donor_priorities (key, family, donor, url, section, text, page_date, retrieved, kind, "
                    "outlet, whose_words, added_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (new_key, form["family"], fam["name"], found["url"], section, found["text"], src["page_date"],
                     found["retrieved"], src["kind"], src["outlet"], src["whose_words"], auth.ACTOR))
                db.audit(conn, auth.ACTOR, "priority added", None,
                         "%s%s: %s (words found verbatim on the page; retrieved %s)" % (
                             fam["name"], " [news report: %s]" % src["outlet"] if src["outlet"] else "",
                             found["url"], found["retrieved"]))
                ctx = priority_context(conn)
            saved, form = found, {"source_type": form["source_type"]}
        except priorities.PriorityError as exc:
            error = str(exc)
        return render(request, "priority.html", status_code=422 if error else 200, form=form, error=error,
                      saved=saved, edited="", **ctx)

    def priority_form(family, url, words, section, page_date, source_type, outlet, whose_words):
        return {"family": family, "url": url, "words": words, "section": section, "page_date": page_date,
                "source_type": source_type, "outlet": outlet, "whose_words": whose_words}

    @app.post("/priority", response_class=HTMLResponse)
    def priority_save(request: Request, family: str = Form(""), url: str = Form(""), words: str = Form(""),
                      section: str = Form(""), page_date: str = Form(""), source_type: str = Form(priorities.OWN_SITE),
                      outlet: str = Form(""), whose_words: str = Form("")):
        require_admin(request)
        same_origin(request)
        return priority_submit(request, priority_form(family, url, words, section, page_date, source_type, outlet,
                                                      whose_words))

    @app.get("/priority/{key}/edit", response_class=HTMLResponse)
    def priority_edit_page(request: Request, key: str):
        require_admin(request)
        with db.session() as conn:
            ctx = priority_context(conn)
            ctx["editing"] = row = get_priority(conn, key)
            ctx["earlier"] = earlier_versions(conn, key)
        return render(request, "priority.html", form=form_of(row), error="", saved=None, edited="", **ctx)

    @app.post("/priority/{key}/edit", response_class=HTMLResponse)
    def priority_edit_save(request: Request, key: str, family: str = Form(""), url: str = Form(""),
                           words: str = Form(""), section: str = Form(""), page_date: str = Form(""),
                           source_type: str = Form(priorities.OWN_SITE), outlet: str = Form(""),
                           whose_words: str = Form("")):
        require_admin(request)
        same_origin(request)
        return priority_submit(request, priority_form(family, url, words, section, page_date, source_type, outlet,
                                                      whose_words), key)

    return app


app = create_app()
