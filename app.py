# Copyright (c) 2026 Anooj Prabaharan. All rights reserved.
"""MyTodo - personal task tracker.

Run: python app.py  (opens http://127.0.0.1:5000, or the next free port).
The packaged MyTodo.exe runs with no console window; use "Quit" in the app to stop it.
"""
import csv
import io
import json
import logging
import os
import re
import socket
import sys
import threading
import urllib.request
import webbrowser
from datetime import date, datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import (Flask, Response, abort, flash, g, redirect, render_template, request,
                   url_for)
from werkzeug.serving import make_server

import backup
import db
import review
import statuslog

__version__ = "1.3.0"
FEEDBACK_EMAIL = "anooj.prabaharan@outlook.com"

# When packaged as MyTodo.exe (PyInstaller), keep the data folder next to the exe,
# not in the temporary folder the exe unpacks itself into.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

log = logging.getLogger("mytodo")


class _ProblemCounter(logging.Handler):
    """Counts warnings/errors logged since this start (shown as a badge in the footer)."""
    def __init__(self):
        super().__init__(level=logging.WARNING)
        self.count = 0

    def emit(self, record):
        self.count += 1


PROBLEMS = _ProblemCounter()


def create_app(data_dir=None):
    app = Flask(__name__)
    data_dir = Path(data_dir or os.environ.get("MYTODO_DATA") or BASE_DIR / "data")
    data_dir.mkdir(parents=True, exist_ok=True)
    app.config.update(
        SECRET_KEY="mytodo-local-only",
        DATA_DIR=str(data_dir),
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
                "today": date.today().isoformat(), "can_quit": bool(app.config.get("SHUTDOWN")),
                "app_version": __version__, "log_problems": PROBLEMS.count,
                "all_labels": lambda: db.list_labels(get_conn()),
                "LABEL_COLORS": db.LABEL_COLORS,
                "FEEDBACK_EMAIL": FEEDBACK_EMAIL}

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

    def current_label():
        """The ?label=<id> filter, as a label row (or None)."""
        label_id = request.args.get("label", type=int)
        return db.get_label(get_conn(), label_id) if label_id else None

    def task_fields():
        """Form data for create/update. Labels are only included when the form edits them."""
        fields = request.form.to_dict()
        if "labels_field" in request.form:
            fields["labels"] = request.form.getlist("labels") + [request.form.get("new_labels", "")]
        return fields

    def form_label_names():
        return db.parse_label_names(request.form.getlist("labels")
                                    + [request.form.get("new_labels", "")])

    def back(default="dashboard"):
        target = request.form.get("next") or request.args.get("next")
        if target and target.startswith("/") and not target.startswith("//"):
            return redirect(target)
        return redirect(url_for(default))

    # ---------- pages ----------

    @app.get("/")
    def dashboard():
        conn = get_conn()
        f = {k: request.args.get(k, "") for k in ("state", "priority", "q", "sort", "label")}
        label = current_label()
        lid = label["id"] if label else None
        tasks = db.list_tasks(conn, state=f["state"] or None, priority=f["priority"] or None,
                              q=f["q"].strip() or None, sort=f["sort"] or "due", label=lid)
        return render_template("dashboard.html", tasks=tasks, counts=db.counts(conn, label=lid),
                               f=f, label=label, tl=db.task_labels(conn, [t["id"] for t in tasks]))

    @app.get("/closed")
    def closed():
        conn = get_conn()
        q = request.args.get("q", "").strip()
        label = current_label()
        tasks = db.list_tasks(conn, closed=True, q=q or None, label=label["id"] if label else None)
        return render_template("closed.html", tasks=tasks, q=q, label=label,
                               tl=db.task_labels(conn, [t["id"] for t in tasks]))

    @app.route("/task/new", methods=["GET", "POST"])
    def task_new():
        if request.method == "POST":
            conn = get_conn()
            try:
                with conn:
                    task_id = db.create_task(conn, task_fields())
            except ValueError as e:
                flash(str(e), "error")
                return render_template("task_form.html", task=request.form, is_new=True,
                                       task_label_names=form_label_names()), 400
            flash("Task created.", "ok")
            return redirect(url_for("task_detail", task_id=task_id))
        preset = [lbl["name"]] if (lbl := current_label()) else []
        return render_template("task_form.html", task={"priority": "Medium", "state": "new"},
                               is_new=True, task_label_names=preset)

    @app.get("/task/<int:task_id>")
    def task_detail(task_id):
        conn = get_conn()
        task = db.get_task(conn, task_id) or abort(404)
        return render_template("task_detail.html", task=task,
                               timeline=db.timeline(conn, task_id),
                               labels=db.task_labels(conn, [task_id])[task_id])

    @app.route("/task/<int:task_id>/edit", methods=["GET", "POST"])
    def task_edit(task_id):
        conn = get_conn()
        task = db.get_task(conn, task_id) or abort(404)
        if request.method == "POST":
            try:
                with conn:
                    db.update_task(conn, task_id, task_fields())
            except ValueError as e:
                flash(str(e), "error")
                data = dict(request.form, id=task_id)
                return render_template("task_form.html", task=data, is_new=False,
                                       task_label_names=form_label_names()), 400
            flash("Task updated.", "ok")
            return redirect(url_for("task_detail", task_id=task_id))
        return render_template("task_form.html", task=task, is_new=False,
                               task_label_names=db.label_names(conn, task_id))

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
        # lets a second launch recognise an already-running MyTodo on a port,
        # and check it is using the same data folder (not another copy of the app)
        return Response(f"MyTodo {__version__}\n{app.config['DB_PATH']}", mimetype="text/plain")

    @app.post("/quit")
    def quit_app():
        shutdown = app.config.get("SHUTDOWN")
        if not shutdown:
            flash("Quit is only available when MyTodo is started as an app.", "error")
            return redirect(url_for("dashboard"))
        shutdown()
        return render_template("quit.html", version=__version__)

    # ---------- report ----------

    @app.get("/report")
    def report():
        conn = get_conn()
        label = current_label()
        rows = db.report_rows(conn, label=label["id"] if label else None)
        return render_template("report.html", rows=rows, generated=datetime.now(), label=label,
                               tl=db.task_labels(conn, [r["id"] for r in rows]))

    @app.get("/report.csv")
    def report_csv():
        conn = get_conn()
        label = current_label()
        rows = db.report_rows(conn, label=label["id"] if label else None)
        tl = db.task_labels(conn, [r["id"] for r in rows])
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["ID", "Task", "State", "Priority", "Labels", "Due date", "Overdue",
                    "Depends on", "Last comment", "Last comment at"])
        today = date.today().isoformat()
        for r in rows:
            w.writerow([r["id"], r["title"], r["state"], r["priority"],
                        ", ".join(x["name"] for x in tl[r["id"]]), r["due_date"] or "",
                        "Yes" if r["due_date"] and r["due_date"] < today else "",
                        r["depends_on"], r["last_comment"] or "",
                        (r["last_comment_at"] or "").replace("T", " ")])
        suffix = f"-{re.sub(r'[^A-Za-z0-9._-]+', '-', label['name']).strip('-')}" if label else ""
        name = f"mytodo-open-tasks{suffix}-{datetime.now():%Y%m%d}.csv"
        # BOM so Excel opens UTF-8 correctly
        return Response("﻿" + buf.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment; filename={name}"})

    # ---------- labels ----------

    @app.get("/labels")
    def labels_page():
        return render_template("labels.html", labels=db.list_labels(get_conn()))

    @app.post("/labels")
    def labels_create():
        conn = get_conn()
        try:
            with conn:
                db.create_label(conn, request.form.get("name"), request.form.get("color") or None)
        except ValueError as e:
            flash(str(e), "error")
        else:
            flash("Label created.", "ok")
        return redirect(url_for("labels_page"))

    @app.post("/labels/<int:label_id>/edit")
    def labels_edit(label_id):
        conn = get_conn()
        db.get_label(conn, label_id) or abort(404)
        try:
            with conn:
                db.rename_label(conn, label_id, request.form.get("name"))
                if request.form.get("color"):
                    db.recolor_label(conn, label_id, request.form.get("color"))
        except ValueError as e:
            flash(str(e), "error")
        else:
            flash("Label saved.", "ok")
        return redirect(url_for("labels_page"))

    @app.post("/labels/<int:label_id>/delete")
    def labels_delete(label_id):
        conn = get_conn()
        label = db.get_label(conn, label_id) or abort(404)
        with conn:
            db.delete_label(conn, label_id)
        flash(f"Label “{label['name']}” deleted. Its tasks were kept.", "ok")
        return redirect(url_for("labels_page"))

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

    # ---------- status & log ----------

    @app.get("/status")
    def status():
        conn = get_conn()
        folder = Path(app.config["DATA_DIR"])
        problems = request.args.get("show") == "problems"
        backups = sorted(Path(app.config["BACKUP_DIR"]).glob("*.json"),
                         key=lambda p: p.stat().st_mtime, reverse=True) \
            if Path(app.config["BACKUP_DIR"]).exists() else []
        info = {
            "version": __version__,
            "url": request.host_url.rstrip("/"),
            "data_dir": str(folder),
            "db_size": statuslog.human_size(statuslog.folder_size(app.config["DB_PATH"])),
            "tasks_open": conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE state != 'closed'").fetchone()[0],
            "tasks_closed": conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE state = 'closed'").fetchone()[0],
            "last_backup": datetime.fromtimestamp(backups[0].stat().st_mtime) if backups else None,
            "log_path": str(folder / statuslog.LOG_FILE),
            "python": sys.version.split()[0],
            "packaged": bool(getattr(sys, "frozen", False)),
        }
        entries = statuslog.read_log(folder, problems_only=problems)
        n_problems = len(statuslog.read_log(folder, problems_only=True))
        return render_template("status.html", info=info, entries=entries, problems=problems,
                               n_problems=n_problems)

    @app.get("/status/log.txt")
    def status_log_download():
        folder = Path(app.config["DATA_DIR"])
        header = (f"MyTodo {__version__} log, downloaded {datetime.now():%Y-%m-%d %H:%M}\n"
                  f"Python {sys.version.split()[0]}, data folder {folder}\n\n")
        text = statuslog.full_log_text(folder) or "(the log is empty)\n"
        return Response(header + text, mimetype="text/plain",
                        headers={"Content-Disposition":
                                 f"attachment; filename=mytodo-log-{datetime.now():%Y%m%d-%H%M}.txt"})

    @app.post("/status/open-folder")
    def status_open_folder():
        # only meaningful when running as the desktop app on this PC
        if app.config.get("SHUTDOWN") and sys.platform == "win32":
            os.startfile(app.config["DATA_DIR"])  # noqa: S606 - local folder, local user
        else:
            flash(f"Data folder: {app.config['DATA_DIR']}", "ok")
        return redirect(url_for("status"))

    @app.errorhandler(500)
    def server_error(err):
        # Flask has already logged the full traceback to the log file
        return render_template("error.html", path=request.path,
                               when=datetime.now()), 500

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
            log.warning("Backup import rejected: %s", e)
            flash(f"Import rejected: {e}", "error")
            return redirect(url_for("backup_page"))
        log.info("Imported %s task(s) from %s (%s)", n, upload.filename, mode)
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
PORT_FILE = "mytodo.port"  # written next to the database while MyTodo is running
LOG_FILE = statuslog.LOG_FILE



def data_dir():
    return Path(os.environ.get("MYTODO_DATA") or BASE_DIR / "data")


def _same_path(a, b):
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def is_mytodo(port, db_path):
    """True if `port` is a running MyTodo that uses the same database as us."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/__mytodo", timeout=1) as r:
            text = r.read(4096).decode("utf-8", "ignore")
    except Exception:
        return False
    lines = text.splitlines()
    return bool(lines) and lines[0].startswith("MyTodo") and len(lines) > 1 \
        and _same_path(lines[1], db_path)


def read_port_file(folder):
    try:
        return int((Path(folder) / PORT_FILE).read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def find_running(folder, db_path):
    """Port of an already-running MyTodo for this data folder, else None."""
    port = read_port_file(folder)
    if port and is_mytodo(port, db_path):
        return port
    return None


def choose_port(start, db_path):
    """Return (port, already_running). Skips ports taken by other programs."""
    for port in range(start, start + PORT_TRIES):
        if not port_in_use(port):
            return port, False
        if is_mytodo(port, db_path):
            return port, True
        log.info("Port %s is used by another program, trying %s...", port, port + 1)
    raise RuntimeError(f"No free port found between {start} and {start + PORT_TRIES - 1}.")


class _LogWriter:
    """Stand-in for stdout/stderr when there is no console window."""
    def __init__(self, level):
        self.level = level

    def write(self, text):
        text = text.rstrip()
        if text:
            log.log(self.level, text)

    def flush(self):
        pass


def setup_logging(folder):
    folder.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    fh = RotatingFileHandler(folder / LOG_FILE, maxBytes=1_000_000, backupCount=2,
                             encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.addHandler(fh)
    root.addHandler(PROBLEMS)
    has_console = sys.stdout is not None and sys.stderr is not None
    if has_console:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(logging.Formatter("%(message)s"))
        root.addHandler(sh)
    else:
        # windowless exe: anything printed (incl. tracebacks) goes to the log file
        sys.stdout = _LogWriter(logging.INFO)
        sys.stderr = _LogWriter(logging.ERROR)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)  # no per-request lines


def show_error(message):
    """Tell the user something went wrong, even without a console window."""
    log.error(message)
    if sys.platform == "win32" and (sys.stdout is None or isinstance(sys.stdout, _LogWriter)):
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, message, "MyTodo", 0x10)
        except Exception:
            pass


def open_in_browser(url):
    if not os.environ.get("MYTODO_NO_BROWSER"):
        webbrowser.open(url)


def main():
    folder = data_dir()
    setup_logging(folder)
    db_path = str(folder / "mytodo.db")

    # 1. Already running? Open the browser on the port it is actually using.
    port = find_running(folder, db_path)
    if port:
        log.info("MyTodo already running at http://127.0.0.1:%s", port)
        open_in_browser(f"http://127.0.0.1:{port}")
        return

    application = create_app(folder)
    startup_backup(application)

    # 2. Pick a free port (skipping other programs) and bind to it.
    start = int(os.environ.get("MYTODO_PORT", "5000"))
    server = None
    while server is None:
        port, already_running = choose_port(start, db_path)
        if already_running:
            log.info("MyTodo already running at http://127.0.0.1:%s", port)
            open_in_browser(f"http://127.0.0.1:{port}")
            return
        try:
            server = make_server("127.0.0.1", port, application, threaded=True)
        except OSError:  # taken in the meantime: try the next one
            start = port + 1

    def shutdown():
        # give the "MyTodo has stopped" page time to reach the browser first
        threading.Timer(0.7, server.shutdown).start()
    application.config["SHUTDOWN"] = shutdown

    port_file = folder / PORT_FILE
    port_file.write_text(str(port), encoding="utf-8")
    url = f"http://127.0.0.1:{port}"
    log.info("MyTodo %s running at %s (data: %s)", __version__, url, folder)
    open_in_browser(url)  # the socket is already listening, so the page loads
    try:
        server.serve_forever()
    finally:
        if read_port_file(folder) == port:
            port_file.unlink(missing_ok=True)
        log.info("MyTodo stopped.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as exc:  # noqa: BLE001
        logging.getLogger("mytodo").exception("MyTodo failed to start")
        show_error(f"MyTodo could not start:\n\n{exc}\n\nDetails are in "
                   f"{data_dir() / LOG_FILE}")
        sys.exit(1)
