"""MyTodo - personal task tracker. Run: python app.py  (opens http://127.0.0.1:5000)"""
import csv
import io
import json
import os
import socket
import sys
import threading
import urllib.request
import webbrowser
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import (Flask, Response, abort, flash, g, redirect, render_template, request,
                   url_for)

import backup
import db
import review

__version__ = "1.2.0"

# When packaged as MyTodo.exe (PyInstaller), keep the data folder next to the exe,
# not in the temporary folder the exe unpacks itself into.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent


def create_app(data_dir=None):
    app = Flask(__name__)
    data_dir = Path(data_dir or os.environ.get("MYTODO_DATA") or BASE_DIR / "data")
    data_dir.mkdir(parents=True, exist_ok=True)
    app.config.update(
        SECRET_KEY="mytodo-local-only",
        DB_PATH=str(data_dir / "mytodo.db"),
        BACKUP_DIR=str(data_dir / "backups"),
        MAX_CONTENT_LENGTH=20 * 1024 * 1024,
    )
    db.init_db(app.config["DB_PATH"])

    def get_conn():
        if "conn" not in g:
            g.conn = db.connect(app.config["DB_PATH"])
        return g.conn

    @app.teardown_appcontext
    def close_conn(_exc):
        conn = g.pop("conn", None)
        if conn is not None:
            conn.close()

    @app.context_processor
    def inject():
        return {"STATES": db.STATES, "PRIORITIES": db.PRIORITIES, "MIN_RESOLUTION": db.MIN_RESOLUTION,
                "today": date.today().isoformat()}

    @app.template_filter("dt")
    def fmt_dt(value):
        if not value:
            return ""
        try:
            return datetime.fromisoformat(value).strftime("%d %b %Y, %H:%M")
        except ValueError:
            return value

    @app.template_filter("d")
    def fmt_d(value):
        if not value:
            return ""
        if isinstance(value, date):
            return value.strftime("%d %b %Y")
        try:  # accepts "YYYY-MM-DD" and full ISO timestamps
            return datetime.fromisoformat(value).strftime("%d %b %Y")
        except ValueError:
            return value

    def back(default="dashboard"):
        target = request.form.get("next") or request.args.get("next")
        if target and target.startswith("/") and not target.startswith("//"):
            return redirect(target)
        return redirect(url_for(default))

    # ---------- pages ----------

    @app.get("/")
    def dashboard():
        conn = get_conn()
        f = {k: request.args.get(k, "") for k in ("state", "priority", "q", "sort")}
        tasks = db.list_tasks(conn, state=f["state"] or None, priority=f["priority"] or None,
                              q=f["q"].strip() or None, sort=f["sort"] or "due")
        return render_template("dashboard.html", tasks=tasks, counts=db.counts(conn), f=f)

    @app.get("/closed")
    def closed():
        conn = get_conn()
        q = request.args.get("q", "").strip()
        tasks = db.list_tasks(conn, closed=True, q=q or None)
        return render_template("closed.html", tasks=tasks, q=q)

    @app.route("/task/new", methods=["GET", "POST"])
    def task_new():
        if request.method == "POST":
            conn = get_conn()
            try:
                with conn:
                    task_id = db.create_task(conn, request.form)
            except ValueError as e:
                flash(str(e), "error")
                return render_template("task_form.html", task=request.form, is_new=True), 400
            flash("Task created.", "ok")
            return redirect(url_for("task_detail", task_id=task_id))
        return render_template("task_form.html", task={"priority": "Medium", "state": "new"},
                               is_new=True)

    @app.get("/task/<int:task_id>")
    def task_detail(task_id):
        conn = get_conn()
        task = db.get_task(conn, task_id) or abort(404)
        return render_template("task_detail.html", task=task,
                               timeline=db.timeline(conn, task_id))

    @app.route("/task/<int:task_id>/edit", methods=["GET", "POST"])
    def task_edit(task_id):
        conn = get_conn()
        task = db.get_task(conn, task_id) or abort(404)
        if request.method == "POST":
            try:
                with conn:
                    db.update_task(conn, task_id, request.form)
            except ValueError as e:
                flash(str(e), "error")
                data = dict(request.form, id=task_id)
                return render_template("task_form.html", task=data, is_new=False), 400
            flash("Task updated.", "ok")
            return redirect(url_for("task_detail", task_id=task_id))
        return render_template("task_form.html", task=task, is_new=False)

    @app.post("/task/<int:task_id>/state")
    def task_state(task_id):
        conn = get_conn()
        db.get_task(conn, task_id) or abort(404)
        new_state = request.form.get("state", "")
        depends_on = request.form.get("depends_on")
        resolution = request.form.get("resolution")
        try:
            with conn:
                db.change_state(conn, task_id, new_state, depends_on, resolution)
        except ValueError as e:
            flash(str(e), "error")
        else:
            flash(f"State changed to {new_state}.", "ok")
        return back()

    @app.post("/task/<int:task_id>/comment")
    def task_comment(task_id):
        conn = get_conn()
        db.get_task(conn, task_id) or abort(404)
        try:
            with conn:
                db.add_comment(conn, task_id, request.form.get("body"))
        except ValueError as e:
            flash(str(e), "error")
        return redirect(url_for("task_detail", task_id=task_id))

    @app.get("/__mytodo")
    def identify():
        # lets a second launch recognise an already-running MyTodo on a port
        return Response(f"MyTodo {__version__}", mimetype="text/plain")

    # ---------- report ----------

    @app.get("/report")
    def report():
        rows = db.report_rows(get_conn())
        return render_template("report.html", rows=rows, generated=datetime.now())

    @app.get("/report.csv")
    def report_csv():
        rows = db.report_rows(get_conn())
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["ID", "Task", "State", "Priority", "Due date", "Overdue",
                    "Depends on", "Last comment", "Last comment at"])
        today = date.today().isoformat()
        for r in rows:
            w.writerow([r["id"], r["title"], r["state"], r["priority"], r["due_date"] or "",
                        "Yes" if r["due_date"] and r["due_date"] < today else "",
                        r["depends_on"], r["last_comment"] or "",
                        (r["last_comment_at"] or "").replace("T", " ")])
        name = f"mytodo-open-tasks-{datetime.now():%Y%m%d}.csv"
        # BOM so Excel opens UTF-8 correctly
        return Response("﻿" + buf.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment; filename={name}"})

    # ---------- performance review ----------

    def review_args():
        conn = get_conn()
        src = request.form if request.method == "POST" else request.args
        start, end = review.parse_period(src, conn)
        exclude = review.parse_exclude(src.get("exclude"))
        comments = review.parse_comments(src.get("comments"))
        return start, end, exclude, comments

    def review_qs(start, end, exclude, comments, **extra):
        qs = {"start": start.isoformat(), "end": end.isoformat(), "comments": comments}
        if exclude:
            qs["exclude"] = review.exclude_str(exclude)
        qs.update(extra)
        return qs

    def review_download(fmt, start, end, exclude, comments, notes):
        data = review.review_data(get_conn(), start, end, exclude, comments)
        base = f"mytodo-review-{start.isoformat()}-to-{end.isoformat()}"
        if fmt == "csv":
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(review.CSV_HEADER)
            w.writerows(review.csv_rows(data))
            return Response("﻿" + buf.getvalue(), mimetype="text/csv",
                            headers={"Content-Disposition": f"attachment; filename={base}.csv"})
        css = (Path(app.root_path) / "static" / "review.css").read_text(encoding="utf-8")
        html = render_template("review_export.html", data=data, start=start, end=end,
                               notes=notes, comments=comments, css=css,
                               generated=datetime.now(), version=__version__)
        return Response(html, mimetype="text/html",
                        headers={"Content-Disposition": f"attachment; filename={base}.html"})

    @app.get("/review")
    def review_page():
        conn = get_conn()
        start, end, exclude, comments = review_args()
        data = review.review_data(conn, start, end, exclude, comments)
        return render_template(
            "review.html", data=data, start=start, end=end, exclude=exclude,
            comments=comments, notes=review.get_draft_notes(conn, start, end),
            quick=review.quick_periods(conn), past=review.list_reviews(conn),
            qs=review_qs(start, end, exclude, comments), generated=datetime.now(),
            saved=None)

    @app.post("/review/notes")
    def review_notes():
        conn = get_conn()
        start, end, exclude, comments = review_args()
        with conn:
            review.save_draft_notes(conn, start, end, request.form.get("notes"))
        flash("Summary saved.", "ok")
        return redirect(url_for("review_page", **review_qs(start, end, exclude, comments)))

    @app.post("/review/save")
    def review_save():
        conn = get_conn()
        start, end, exclude, comments = review_args()
        notes = request.form.get("notes")
        if request.form.get("confirm") != "yes":
            flash("Review not saved: confirmation missing.", "error")
            return redirect(url_for("review_page", **review_qs(start, end, exclude, comments)))
        with conn:
            review.save_draft_notes(conn, start, end, notes)
            rid = review.save_review(conn, start, end, notes, exclude, comments)
        flash("Review saved. Your next review will start from "
              f"{(end + timedelta(days=1)).strftime('%d %b %Y')}.", "ok")
        return redirect(url_for("review_saved", review_id=rid))

    @app.get("/review.<fmt>")
    def review_export(fmt):
        if fmt not in ("html", "csv"):
            abort(404)
        conn = get_conn()
        start, end, exclude, comments = review_args()
        return review_download(fmt, start, end, exclude, comments,
                               review.get_draft_notes(conn, start, end))

    @app.get("/review/<int:review_id>")
    def review_saved(review_id):
        conn = get_conn()
        r = review.get_review(conn, review_id) or abort(404)
        fmt = request.args.get("format")
        if fmt in ("html", "csv"):
            return review_download(fmt, r["start_d"], r["end_d"], r["exclude_ids"],
                                   r["comments"], r["notes"])
        data = review.review_data(conn, r["start_d"], r["end_d"], r["exclude_ids"], r["comments"])
        return render_template("review.html", data=data, start=r["start_d"], end=r["end_d"],
                               exclude=r["exclude_ids"], comments=r["comments"],
                               notes=r["notes"], saved=r, generated=datetime.now(),
                               quick=[], past=[], qs={})

    @app.post("/review/<int:review_id>/delete")
    def review_delete(review_id):
        conn = get_conn()
        review.get_review(conn, review_id) or abort(404)
        with conn:
            review.delete_review(conn, review_id)
        flash("Saved review deleted. Your tasks were not changed.", "ok")
        return redirect(url_for("review_page"))

    # ---------- backup ----------

    @app.get("/backup")
    def backup_page():
        folder = Path(app.config["BACKUP_DIR"])
        files = sorted(folder.glob("*.json"), reverse=True) if folder.exists() else []
        return render_template("backup.html", files=files[:15], folder=folder)

    @app.get("/backup/export")
    def backup_export():
        conn = get_conn()
        path = backup.write_backup_file(conn, app.config["BACKUP_DIR"])
        return Response(path.read_text(encoding="utf-8"), mimetype="application/json",
                        headers={"Content-Disposition": f"attachment; filename={path.name}"})

    @app.post("/backup/import")
    def backup_import():
        upload = request.files.get("file")
        mode = request.form.get("mode", "merge")
        if not upload or not upload.filename:
            flash("Choose a backup file to import.", "error")
            return redirect(url_for("backup_page"))
        if mode == "replace" and request.form.get("confirm") != "yes":
            flash("Tick the confirmation box to replace all existing tasks.", "error")
            return redirect(url_for("backup_page"))
        try:
            data = json.loads(upload.read().decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            flash(f"Not a valid JSON file: {e}", "error")
            return redirect(url_for("backup_page"))
        conn = get_conn()
        try:
            backup.validate(data)
            # safety copy of the current data before changing anything
            backup.write_backup_file(conn, app.config["BACKUP_DIR"], prefix="pre-import-")
            with conn:
                n = backup.import_data(conn, data, mode)
        except backup.BackupError as e:
            flash(f"Import rejected: {e}", "error")
            return redirect(url_for("backup_page"))
        flash(f"Imported {n} task(s) ({mode}).", "ok")
        return redirect(url_for("dashboard"))

    return app


def startup_backup(app):
    conn = db.connect(app.config["DB_PATH"])
    try:
        if conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]:
            backup.write_backup_file(conn, app.config["BACKUP_DIR"], keep=10, prefix="auto-")
    finally:
        conn.close()


PORT_TRIES = 20  # 5000, 5001, ... 5019


def port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def is_mytodo(port):
    """True if the program listening on `port` is a running MyTodo."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/__mytodo", timeout=1) as r:
            return r.read(32).decode("utf-8", "ignore").startswith("MyTodo")
    except Exception:
        return False


def choose_port(start):
    """Return (port, already_running). Skips ports taken by other programs."""
    for port in range(start, start + PORT_TRIES):
        if not port_in_use(port):
            return port, False
        if is_mytodo(port):
            return port, True
        print(f"Port {port} is used by another program, trying {port + 1}...")
    raise SystemExit(f"No free port found between {start} and {start + PORT_TRIES - 1}.")


def main():
    open_browser = not os.environ.get("MYTODO_NO_BROWSER")
    port, already_running = choose_port(int(os.environ.get("MYTODO_PORT", "5000")))
    url = f"http://127.0.0.1:{port}"
    if already_running:
        # e.g. exe double-clicked twice: just open the existing one.
        print(f"MyTodo already running at {url}")
        if open_browser:
            webbrowser.open(url)
        return
    application = create_app()
    startup_backup(application)
    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"MyTodo {__version__} running at {url}")
    print(f"Data folder: {BASE_DIR / 'data'}")
    print("Keep this window open while using MyTodo. Close it (or Ctrl+C) to stop.")
    # quiet console: no Flask banner / per-request lines, errors still shown
    import logging
    import flask.cli
    flask.cli.show_server_banner = lambda *a, **k: None
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    application.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    main()
