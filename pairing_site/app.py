"""The Flask site: a public list of three-zone pairing cards, each on its own URL, and a password-protected
queue where a maintainer approves candidates and enters priorities.

Cards render per request from the database. Nothing is published until a candidate is approved. The admin pages
sit behind HTTP basic auth with ADMIN_PASSWORD (any user name).
"""

import functools
import hmac
import os
import threading
import time
import traceback
import uuid
from urllib.parse import urlparse

from flask import Flask, Response, abort, g, redirect, render_template, request, url_for
from werkzeug.exceptions import HTTPException

from . import candidates, config, db, fetcher, logs, money, pairing_cards, review, scheduler
from . import fmap_lib as fl

QUEUE_PAGE = 40
CONTEXT_ROWS = 4
DETAIL_CONTEXT_ROWS = 10


def create_app(settings=None, start_scheduler=True):
    settings = settings or config.load()
    os.environ["FETCH_CONTACT_EMAIL"] = settings["fetch_contact_email"]
    app = Flask(__name__)
    app.config["SETTINGS"] = settings
    logs.setup()
    db.init(settings["database_path"]).close()

    def get_db():
        if "db" not in g:
            g.db = db.connect(settings["database_path"])
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        conn = g.pop("db", None)
        if conn is not None:
            conn.close()

    app.jinja_env.filters["mark"] = pairing_cards.marked
    app.jinja_env.filters["sentence"] = lambda s: s[:1].upper() + s[1:]

    # ----------------------------------------------------------------------- request log and errors

    @app.before_request
    def begin():
        g.request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex
        g.started = time.perf_counter()

    @app.after_request
    def finish(resp):
        status = resp.status_code
        logs.emit("error" if status >= 500 else "info", "%s %s %d" % (request.method, request.path, status),
                  request_id=g.get("request_id", ""), method=request.method, path=request.path, status=status,
                  duration_ms=round((time.perf_counter() - g.get("started", time.perf_counter())) * 1000, 2))
        resp.headers["X-Request-Id"] = g.get("request_id", "")
        return resp

    @app.errorhandler(Exception)
    def unhandled(exc):
        if isinstance(exc, HTTPException):
            return exc
        logs.emit("error", "unhandled error on %s %s" % (request.method, request.path), request_id=g.get("request_id", ""),
                  method=request.method, path=request.path, error=str(exc),
                  stack="".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
        return Response("Something went wrong. The error was logged with request id %s.\n" % g.get("request_id", ""),
                        status=500, mimetype="text/plain")

    # ----------------------------------------------------------------------- admin access

    def admin_required(view):
        @functools.wraps(view)
        def wrapped(*args, **kwargs):
            auth = request.authorization
            ok = bool(auth and auth.password is not None
                      and hmac.compare_digest(auth.password.encode("utf-8"), settings["admin_password"].encode("utf-8")))
            if not ok:
                return Response("The review queue needs the maintainer's password.\n", status=401,
                                headers={"WWW-Authenticate": 'Basic realm="Pairing site admin"'}, mimetype="text/plain")
            if request.method == "POST":
                origin = request.headers.get("Origin")
                if origin and urlparse(origin).netloc != request.host:
                    abort(403)
            return view(*args, **kwargs)
        return wrapped

    # ----------------------------------------------------------------------- public pages

    @app.get("/")
    def index():
        return render_template("index.html", cards=pairing_cards.approved_cards(get_db()))

    @app.get("/pairings/<slug>")
    def pairing(slug):
        card = pairing_cards.card_by_slug(get_db(), slug)
        if card is None:
            abort(404)
        return render_template("pairing.html", card=card)

    # ----------------------------------------------------------------------- admin: status

    @app.get("/admin")
    @admin_required
    def admin_status():
        conn = get_db()
        count = lambda sql: conn.execute(sql).fetchone()["n"]  # noqa: E731
        stats = {
            "donors": count("SELECT COUNT(*) AS n FROM donors"), "priorities": count("SELECT COUNT(*) AS n FROM priorities"),
            "meetings": count("SELECT COUNT(*) AS n FROM meetings"), "lines": count("SELECT COUNT(*) AS n FROM lines"),
            "filings": count("SELECT COUNT(*) AS n FROM contributions"),
            "pending": count("SELECT COUNT(*) AS n FROM candidates WHERE status='pending'"),
            "approved": count("SELECT COUNT(*) AS n FROM candidates WHERE status='approved'"),
            "rejected": count("SELECT COUNT(*) AS n FROM candidates WHERE status='rejected'"),
        }
        runs = conn.execute("SELECT * FROM fetch_runs ORDER BY id DESC LIMIT 10").fetchall()
        return render_template(
            "admin_status.html", stats=stats, runs=runs, running=fetcher.RUN_LOCK.locked(),
            next_run=scheduler.next_run_at(conn, settings["fetch_interval_hours"]),
            money_retrieved=db.get_meta(conn, "money_retrieved"), loaded_through=db.get_meta(conn, "money_loaded_through"),
            contact=settings["fetch_contact_email"], interval=settings["fetch_interval_hours"])

    @app.post("/admin/fetch")
    @admin_required
    def admin_fetch():
        def work():
            conn = db.connect(settings["database_path"])
            try:
                fetcher.run(conn, settings, "manual")
            except Exception as exc:  # the run is recorded as failed; the thread has nowhere to raise to
                logs.emit("error", "manual fetch failed", error=str(exc), stack=traceback.format_exc())
            finally:
                conn.close()
        threading.Thread(target=work, name="manual-fetch", daemon=True).start()
        return redirect(url_for("admin_status"), code=303)

    # ----------------------------------------------------------------------- admin: queue

    def lines_around(conn, cand, rows):
        lo, hi = cand["first_idx"] - rows, cand["last_idx"] + rows
        found = conn.execute("SELECT idx, stamp, text FROM lines WHERE meeting_id=? AND idx BETWEEN ? AND ? ORDER BY idx",
                             (cand["meeting_id"], lo, hi)).fetchall()
        return [{"stamp": r["stamp"], "text": r["text"], "flagged": cand["first_idx"] <= r["idx"] <= cand["last_idx"]}
                for r in found]

    def candidate_view(conn, row, context):
        c = dict(row)
        c["official"] = conn.execute("SELECT name, office, district FROM officials WHERE id=?", (row["official_id"],)).fetchone()
        c["donor"] = conn.execute("SELECT name FROM donors WHERE id=?", (row["donor_id"],)).fetchone()
        c["meeting"] = conn.execute("SELECT * FROM meetings WHERE id=?", (row["meeting_id"],)).fetchone()
        c["hit_list"] = db.jl(row["hits"])
        c["why"] = db.jl(row["doubt_why"])
        c["cue"] = db.jl(row["cue_lines"])
        c["lines"] = lines_around(conn, row, context)
        named = db.jl(row["priority_ids"])
        c["priorities"] = [dict(p, named=p["id"] in named) for p in conn.execute(
            "SELECT * FROM priorities WHERE donor_id=? ORDER BY id", (row["donor_id"],))]
        return c

    @app.get("/admin/queue")
    @admin_required
    def admin_queue():
        conn = get_db()
        page = max(int(request.args.get("page", "1") or 1), 1)
        total = conn.execute("SELECT COUNT(*) AS n FROM candidates WHERE status='pending'").fetchone()["n"]
        rows = conn.execute(
            "SELECT c.* FROM candidates c JOIN meetings m ON m.id = c.meeting_id WHERE c.status='pending' "
            "ORDER BY m.date DESC, c.first_stamp, c.id LIMIT ? OFFSET ?", (QUEUE_PAGE, (page - 1) * QUEUE_PAGE)).fetchall()
        items = [candidate_view(conn, r, CONTEXT_ROWS) for r in rows]
        return render_template("admin_queue.html", items=items, total=total, page=page, pages=max(-(-total // QUEUE_PAGE), 1))

    def render_candidate(cid, errors=None, form=None):
        conn = get_db()
        row = conn.execute("SELECT * FROM candidates WHERE id=?", (cid,)).fetchone()
        if row is None:
            abort(404)
        return render_template("admin_candidate.html", c=candidate_view(conn, row, DETAIL_CONTEXT_ROWS), errors=errors or [],
                               form=form or {}, doubts=review.DOUBT_LEVELS)

    @app.get("/admin/candidates/<int:cid>")
    @admin_required
    def admin_candidate(cid):
        return render_candidate(cid)

    def review_action(cid, action):
        try:
            action(get_db())
        except review.FormError as exc:
            return render_candidate(cid, errors=exc.errors, form=request.form), 400
        except LookupError:
            abort(404)
        return redirect(url_for("admin_candidate", cid=cid), code=303)

    @app.post("/admin/candidates/<int:cid>/approve")
    @admin_required
    def admin_approve(cid):
        form = {k: request.form.get(k, "") for k in ("begin_at", "end_at", "doubt", "doubt_note", "in_common", "differs")}
        form["statements"] = request.form.getlist("statements")
        return review_action(cid, lambda conn: review.approve(conn, cid, form))

    @app.post("/admin/candidates/<int:cid>/reject")
    @admin_required
    def admin_reject(cid):
        return review_action(cid, lambda conn: review.reject(conn, cid, request.form.get("reject_note", "")))

    @app.post("/admin/candidates/<int:cid>/doubt")
    @admin_required
    def admin_doubt(cid):
        return review_action(cid, lambda conn: review.set_doubt(conn, cid, request.form.get("doubt", ""),
                                                                request.form.get("doubt_note", "")))

    # ----------------------------------------------------------------------- admin: donors and priorities

    @app.get("/admin/priorities")
    @admin_required
    def admin_priorities():
        conn = get_db()
        donors = []
        for d in conn.execute("SELECT * FROM donors ORDER BY name"):
            pris = conn.execute("SELECT * FROM priorities WHERE donor_id=? ORDER BY id", (d["id"],)).fetchall()
            donors.append({"row": d, "priorities": [dict(p, measure_list=db.jl(p["measures"]), phrase_list=db.jl(p["phrases"]))
                                                    for p in pris],
                           "funded": len(money.funded_official_ids(conn, d["id"])),
                           "rows": conn.execute("SELECT COUNT(*) AS n FROM contributions WHERE donor_id=?", (d["id"],)).fetchone()["n"]})
        return render_template("admin_priorities.html", donors=donors)

    @app.route("/admin/priorities/new", methods=["GET", "POST"])
    @admin_required
    def admin_priority_new():
        conn = get_db()
        donors = conn.execute("SELECT id, name FROM donors ORDER BY name").fetchall()
        form, errors = request.form if request.method == "POST" else {"donor_id": request.args.get("donor", ""),
                                                                     "retrieved": fl.today()}, []
        if request.method == "POST":
            try:
                review.save_priority(conn, request.form)
                return redirect(url_for("admin_priorities"), code=303)
            except review.FormError as exc:
                errors = exc.errors
        return render_template("admin_priority_form.html", donors=donors, form=form, errors=errors,
                               suggestions=review.SOURCE_TYPE_SUGGESTIONS), (400 if errors else 200)

    @app.route("/admin/donors/new", methods=["GET", "POST"])
    @admin_required
    def admin_donor_new():
        conn = get_db()
        form, errors = request.form if request.method == "POST" else {}, []
        if request.method == "POST":
            try:
                review.save_donor(conn, request.form)
                return redirect(url_for("admin_priorities"), code=303)
            except review.FormError as exc:
                errors = exc.errors
        return render_template("admin_donor_form.html", form=form, errors=errors), (400 if errors else 200)

    if start_scheduler:
        app.config["SCHEDULER"] = scheduler.Scheduler(settings)
        app.config["SCHEDULER"].start()
    return app
