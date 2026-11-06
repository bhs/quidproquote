"""The pairing site: FastAPI with Jinja templates and HTMX.

Public:  /               approved pairings as cards, filterable by official or donor (a little JavaScript)
         /pairings/<slug>  one card at its own URL
         /status          the worker's summary as JSON
Sign-in: /login           the ADMIN_TOKEN sets a signed session cookie
Admin:   /review          the queue: approve (needs the recording check ticked) or reject, inline through HTMX
         /review/dropped  pairs the AI filter dropped, with reasons
         /priority        add a donor's priority from a link: the page is fetched for its outlet and date, then the
                          pasted words must be on it. /priority/<id>/edit re-checks an edit the same way, and
                          /priority/<id>/history shows the current wording beside the earlier ones

Every approval, rejection, sign-in, priority added and priority edited is written to the audit log with its time and
action; an edit keeps the old row whole in its entry. A card's quote is compared with the stored transcript each time
it is drawn, and again at approval.
"""

import contextlib
import datetime
import html
import os
import secrets
import time
import urllib.parse

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from . import auth, config, db, logs, pipeline, priorities, sources, status  # noqa: F401  (sources: discovery libraries on the path)

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


def check_cards(conn, rows):
    """Compares each pairing's card quote with the transcript stored in `meetings` and notes the result on the row:
    quote_status ('matches', 'mismatch' or 'unavailable') and quote_shown, the words the card shows. On a mismatch
    that is the stored text, never the card's own copy; every result but a match is logged."""
    rows = [r for r in rows if "quote_status" not in r]
    ids = sorted({r["meeting_id"] for r in rows})
    transcripts = {}
    if ids:
        for m in conn.execute("SELECT id, captions FROM meetings WHERE id IN (%s)" % ",".join("?" * len(ids)), ids):
            transcripts[m["id"]] = pipeline.parse_captions(m["captions"])
    for r in rows:
        q = r["card"]["quote"]
        first = q.get("first_stamp") or r["first_stamp"]
        status_, stored = pipeline.check_quote(transcripts.get(r["meeting_id"]), q["text"], first, q.get("last_stamp") or first)
        r["quote_status"] = status_
        r["quote_shown"] = stored if status_ == "mismatch" else q["text"]
        if status_ != "matches":
            logs.emit("warn", "card quote does not match the stored transcript" if status_ == "mismatch"
                      else "card quote cannot be compared: transcript or stamps not stored",
                      slug=r["slug"], meeting_id=r["meeting_id"], first_stamp=first, status=status_)
    return rows


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
    templates.env.globals["shared_terms"] = pipeline.shared_terms

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
                                "recording_checked_at, meeting_id, first_stamp FROM pairings WHERE status = 'approved' "
                                "ORDER BY published_at DESC, id").fetchall()
            check_cards(conn, rows)
        return render(request, "index.html", rows=rows,
                      officials=sorted({r["official"] for r in rows}), donors=sorted({r["donor_name"] for r in rows}))

    @app.get("/pairings/{slug}", response_class=HTMLResponse)
    def pairing(request: Request, slug: str):
        with db.session() as conn:
            row = conn.execute("SELECT * FROM pairings WHERE slug = ?", (slug,)).fetchone()
            if not row or (row["status"] != "approved" and not admin(request)):
                raise HTTPException(404, "No such pairing")
            check_cards(conn, [row])
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
        check_cards(conn, pending)
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
                check_cards(conn, [row])
                if row["quote_status"] != "matches":  # nothing is published on words the stored transcript does not hold
                    db.audit(conn, auth.ACTOR, "approval refused", pairing_id,
                             "the card's quote does not match the stored transcript (%s)" % row["quote_status"])
                    return row, ("The card's quote does not match the stored transcript (%s), so nothing was published. "
                                 "The stored text is shown above." % row["quote_status"])
                stamp = db.now()
                conn.execute("UPDATE pairings SET status = 'approved', recording_checked = 1, "
                             "recording_checked_at = ?, published_at = ?, decided_at = ?, "
                             "decision_note = ? WHERE id = ?", (stamp, db.today(), stamp, note, pairing_id))
                db.audit(conn, auth.ACTOR, "approved", pairing_id,
                         "recording checked at transcript time %s; quote matches the stored transcript" % row["first_stamp"]
                         + ("; " + note if note else ""))
            else:
                conn.execute("UPDATE pairings SET status = 'rejected', decided_at = ?, decision_note = ? WHERE id = ?",
                             (db.now(), note, pairing_id))
                db.audit(conn, auth.ACTOR, "rejected", pairing_id, note)
            return conn.execute("SELECT * FROM pairings WHERE id = ?", (pairing_id,)).fetchone(), ""

    def decision_response(request, row, error):
        if is_htmx(request):
            with db.session() as conn:
                check_cards(conn, [row])
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
        rows = conn.execute("SELECT * FROM donor_priorities ORDER BY COALESCE(updated_at, added_at) DESC, id DESC "
                            "LIMIT 30").fetchall()
        return {"families": fams["payload"]["families"] if fams else [], "recent": rows,
                "edits": priorities.edit_counts(conn)}

    def form_of(priority_id, version, family, url, words, outlet, page_date, kind):
        return {"priority_id": priority_id.strip(), "version": version.strip(), "family": family, "url": url,
                "words": words, "outlet": outlet, "page_date": page_date, "kind": kind}

    def priority_row(conn, priority_id):
        """The priority being edited (None for a new one); 404 when the id is not one."""
        if not priority_id.strip():
            return None
        row = conn.execute("SELECT * FROM donor_priorities WHERE id = ?",
                           (int(priority_id) if priority_id.strip().isdigit() else -1,)).fetchone()
        if not row:
            raise HTTPException(404, "No such priority")
        return row

    def priority_render(request, form, error="", saved=None, notice="", editing=None):
        with db.session() as conn:
            ctx = priority_context(conn)
        return render(request, "priority.html", status_code=422 if error else 200, form=form, error=error,
                      saved=saved, notice=notice, editing=editing, **ctx)

    @app.get("/priority", response_class=HTMLResponse)
    def priority_page(request: Request):
        require_admin(request)
        return priority_render(request, {"kind": "news"})

    @app.get("/priority/{priority_id}/edit", response_class=HTMLResponse)
    def priority_edit(request: Request, priority_id: str):
        require_admin(request)
        with db.session() as conn:
            row = priority_row(conn, priority_id)
        form = form_of(str(row["id"]), str(row["version"]), row["family"], row["url"], row["text"], row["outlet"],
                       row["page_date"], priorities.kind_key(row["kind"]))
        return priority_render(request, form, editing=row)

    @app.get("/priority/{priority_id}/history", response_class=HTMLResponse)
    def priority_history(request: Request, priority_id: str):
        require_admin(request)
        with db.session() as conn:
            current, earlier = priorities.history(conn, int(priority_id) if priority_id.isdigit() else -1)
        if not current:
            raise HTTPException(404, "No such priority")
        return render(request, "priority_history.html", current=current, earlier=earlier,
                      news_kind=priorities.KIND_NEWS)

    @app.post("/priority/lookup", response_class=HTMLResponse)
    def priority_lookup(request: Request, priority_id: str = Form(""), version: str = Form(""), family: str = Form(""),
                        url: str = Form(""), words: str = Form(""), outlet: str = Form(""), page_date: str = Form(""),
                        kind: str = Form("news")):
        """Fetches the pasted link and fills in the outlet and the date the page shows, for the maintainer to confirm."""
        require_admin(request)
        same_origin(request)
        form = form_of(priority_id, version, family, url, words, outlet, page_date, kind)
        with db.session() as conn:
            editing = priority_row(conn, priority_id)
        error, notice = "", ""
        try:
            found = priorities.lookup(url)
            form["url"] = found["url"]
            form["outlet"] = found["outlet"]
            if found["page_date"]:
                form["page_date"] = found["page_date"]
                notice = "Read from the page: outlet %s, dated %s. Confirm them or correct them." % (found["outlet"], found["page_date"])
            else:
                notice = ("Read from the page: outlet %s. The page gives no date: enter the date the article shows." %
                          found["outlet"])
        except priorities.PriorityError as exc:
            error = str(exc)
        return priority_render(request, form, error=error, notice=notice, editing=editing)

    @app.post("/priority", response_class=HTMLResponse)
    def priority_save(request: Request, priority_id: str = Form(""), version: str = Form(""), family: str = Form(""),
                      url: str = Form(""), words: str = Form(""), outlet: str = Form(""), page_date: str = Form(""),
                      kind: str = Form("news")):
        require_admin(request)
        same_origin(request)
        form = form_of(priority_id, version, family, url, words, outlet, page_date, kind)
        with db.session() as conn:
            editing = priority_row(conn, priority_id)
            fams = priority_context(conn)["families"]
        fam = next((f for f in fams if f["key"] == (editing["family"] if editing else family)), None)
        error, saved = "", None
        if not fam:
            error = "Choose the donor this priority belongs to."
        else:
            try:
                source = priorities.clean_source(outlet, page_date, kind)
                if editing:
                    source = priorities.keep_own_kind(editing, source)
                    if priorities.unchanged(editing, url, words, source):
                        raise priorities.PriorityError("Nothing was changed, so nothing was saved.")
                found = priorities.verify(url, words)  # fetches the page: done before the write lock is taken
                with db.session(write=True) as conn:
                    if editing:
                        priorities.update(conn, editing["id"], found, source, auth.ACTOR,
                                          expected_version=int(version) if version.strip().isdigit() else None)
                        pid = editing["id"]
                    else:
                        pid = priorities.add(conn, fam, "form-%s-%s-%s" % (fam["key"], int(time.time()), secrets.token_hex(3)),
                                             found, source, auth.ACTOR)
                    new_version = conn.execute("SELECT version FROM donor_priorities WHERE id = ?", (pid,)).fetchone()["version"]
                saved = dict(found, id=pid, edited=bool(editing), version=new_version, outlet=source["outlet"],
                             kind=source["kind"])
                form, editing = {"kind": "news"}, None
            except priorities.PriorityError as exc:
                error = str(exc)
        return priority_render(request, form, error=error, saved=saved, editing=editing)

    return app


app = create_app()
