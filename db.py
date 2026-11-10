"""SQLite storage for MyTodo.

All mutating helpers write a matching row to the `log` table inside the same
transaction, so the audit trail can never be skipped.
"""
import sqlite3
from datetime import datetime

STATES = ["new", "triage", "depended", "closed"]
PRIORITIES = ["Low", "Medium", "High"]
PRIORITY_RANK = {"High": 3, "Medium": 2, "Low": 1}
MIN_RESOLUTION = 10  # characters required in a closing summary

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    priority    TEXT NOT NULL DEFAULT 'Medium',
    due_date    TEXT,
    state       TEXT NOT NULL DEFAULT 'new',
    depends_on  TEXT NOT NULL DEFAULT '',
    resolution  TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    closed_at   TEXT
);
CREATE TABLE IF NOT EXISTS comments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id    INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    body       TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id    INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    old_value  TEXT,
    new_value  TEXT,
    detail     TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS review_notes (
    period     TEXT PRIMARY KEY,
    body       TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reviews (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    start    TEXT NOT NULL,
    end      TEXT NOT NULL,
    notes    TEXT NOT NULL DEFAULT '',
    exclude  TEXT NOT NULL DEFAULT '',
    comments TEXT NOT NULL DEFAULT 'latest',
    saved_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_comments_task ON comments(task_id);
CREATE INDEX IF NOT EXISTS idx_log_task ON log(task_id);
"""


def now():
    return datetime.now().isoformat(timespec="seconds")


def connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(path):
    with connect(path) as conn:
        conn.executescript(SCHEMA)
        # upgrade databases created by v1.0 / v1.1
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(tasks)")}
        if "resolution" not in cols:
            conn.execute("ALTER TABLE tasks ADD COLUMN resolution TEXT NOT NULL DEFAULT ''")


def _log(conn, task_id, event_type, old=None, new=None, detail=None, at=None):
    conn.execute(
        "INSERT INTO log (task_id, event_type, old_value, new_value, detail, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (task_id, event_type, old, new, detail, at or now()),
    )


def _clean(fields):
    title = (fields.get("title") or "").strip()
    if not title:
        raise ValueError("Title is required.")
    priority = fields.get("priority") or "Medium"
    if priority not in PRIORITIES:
        raise ValueError(f"Invalid priority: {priority}")
    state = fields.get("state") or "new"
    if state not in STATES:
        raise ValueError(f"Invalid state: {state}")
    due = (fields.get("due_date") or "").strip() or None
    if due:
        datetime.strptime(due, "%Y-%m-%d")  # raises ValueError if malformed
    depends_on = (fields.get("depends_on") or "").strip() if state == "depended" else ""
    resolution = (fields.get("resolution") or "").strip()
    if state == "closed" and len(resolution) < MIN_RESOLUTION:
        raise ValueError(
            "A closing summary is required to close a task (at least "
            f"{MIN_RESOLUTION} characters): describe the outcome, what was delivered "
            "and its impact. It is used in your performance review.")
    return {
        "title": title,
        "description": (fields.get("description") or "").strip(),
        "priority": priority,
        "due_date": due,
        "state": state,
        "depends_on": depends_on,
        "resolution": resolution,
    }


# ---------- reads ----------

def get_task(conn, task_id):
    return conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()


def list_tasks(conn, closed=False, state=None, priority=None, q=None, sort="due"):
    sql = "SELECT * FROM tasks WHERE " + ("state = 'closed'" if closed else "state != 'closed'")
    args = []
    if state and not closed:
        sql += " AND state = ?"
        args.append(state)
    if priority:
        sql += " AND priority = ?"
        args.append(priority)
    if q:
        sql += " AND (title LIKE ? OR description LIKE ?)"
        args += [f"%{q}%", f"%{q}%"]
    if closed:
        sql += " ORDER BY closed_at DESC"
    elif sort == "priority":
        sql += (" ORDER BY CASE priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END,"
                " due_date IS NULL, due_date")
    elif sort == "updated":
        sql += " ORDER BY updated_at DESC"
    else:  # due date, empty dates last
        sql += " ORDER BY due_date IS NULL, due_date, id"
    return conn.execute(sql, args).fetchall()


def report_rows(conn):
    """Open tasks with their most recent comment, ordered by due date (undated last)."""
    return conn.execute(
        """
        SELECT t.*, c.body AS last_comment, c.created_at AS last_comment_at
          FROM tasks t
          LEFT JOIN comments c ON c.id = (
                SELECT id FROM comments WHERE task_id = t.id
                 ORDER BY created_at DESC, id DESC LIMIT 1)
         WHERE t.state != 'closed'
         ORDER BY t.due_date IS NULL, t.due_date,
                  CASE t.priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END, t.id
        """
    ).fetchall()


def counts(conn):
    rows = conn.execute("SELECT state, COUNT(*) AS n FROM tasks GROUP BY state").fetchall()
    result = {s: 0 for s in STATES}
    result.update({r["state"]: r["n"] for r in rows})
    today = datetime.now().date().isoformat()
    result["overdue"] = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE state != 'closed' AND due_date IS NOT NULL AND due_date < ?",
        (today,),
    ).fetchone()[0]
    return result


def timeline(conn, task_id):
    """Full history for a task, newest first.

    Comments are logged as `comment` events (body in `detail`), so the log alone
    is the complete merged timeline of comments, state changes and edits.
    """
    return conn.execute(
        "SELECT id, event_type, old_value, new_value, detail, created_at FROM log"
        " WHERE task_id = ? ORDER BY created_at DESC, id DESC",
        (task_id,),
    ).fetchall()


# ---------- writes (each logs) ----------

def create_task(conn, fields):
    f = _clean(fields)
    ts = now()
    cur = conn.execute(
        "INSERT INTO tasks (title, description, priority, due_date, state, depends_on,"
        " resolution, created_at, updated_at, closed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (f["title"], f["description"], f["priority"], f["due_date"], f["state"],
         f["depends_on"], f["resolution"], ts, ts, ts if f["state"] == "closed" else None),
    )
    task_id = cur.lastrowid
    _log(conn, task_id, "created", new=f["state"], detail=f["title"], at=ts)
    if f["state"] == "closed":
        _log(conn, task_id, "resolution", new=f["resolution"], at=ts)
    if f["state"] == "depended" and f["depends_on"]:
        _log(conn, task_id, "dependency", new=f["depends_on"], at=ts)
    return task_id


def update_task(conn, task_id, fields):
    old = get_task(conn, task_id)
    if old is None:
        raise KeyError(task_id)
    f = _clean(fields)
    ts = now()
    for key in ("title", "description", "priority", "due_date"):
        if (old[key] or None) != (f[key] or None):
            _log(conn, task_id, "edited", old=old[key], new=f[key], detail=key, at=ts)
    if old["state"] != f["state"]:
        _log(conn, task_id, "state_change", old=old["state"], new=f["state"], at=ts)
    if (old["depends_on"] or "") != f["depends_on"] and f["state"] == "depended":
        _log(conn, task_id, "dependency", old=old["depends_on"] or None, new=f["depends_on"], at=ts)
    if f["state"] == "closed" and old["state"] != "closed":
        _log(conn, task_id, "resolution", new=f["resolution"], at=ts)
    elif f["state"] == "closed" and (old["resolution"] or "") != f["resolution"]:
        _log(conn, task_id, "edited", old=old["resolution"] or None, new=f["resolution"],
             detail="resolution", at=ts)
    closed_at = old["closed_at"]
    if f["state"] == "closed" and old["state"] != "closed":
        closed_at = ts
    elif f["state"] != "closed":
        closed_at = None
    conn.execute(
        "UPDATE tasks SET title=?, description=?, priority=?, due_date=?, state=?, depends_on=?,"
        " resolution=?, updated_at=?, closed_at=? WHERE id=?",
        (f["title"], f["description"], f["priority"], f["due_date"], f["state"],
         f["depends_on"], f["resolution"], ts, closed_at, task_id),
    )


def change_state(conn, task_id, new_state, depends_on=None, resolution=None):
    old = get_task(conn, task_id)
    if old is None:
        raise KeyError(task_id)
    fields = dict(old)
    fields["state"] = new_state
    if depends_on is not None:
        fields["depends_on"] = depends_on
    if resolution is not None:
        fields["resolution"] = resolution
    update_task(conn, task_id, fields)


def add_comment(conn, task_id, body):
    body = (body or "").strip()
    if not body:
        raise ValueError("Comment cannot be empty.")
    if get_task(conn, task_id) is None:
        raise KeyError(task_id)
    ts = now()
    conn.execute("INSERT INTO comments (task_id, body, created_at) VALUES (?, ?, ?)",
                 (task_id, body, ts))
    _log(conn, task_id, "comment", detail=body, at=ts)
    conn.execute("UPDATE tasks SET updated_at = ? WHERE id = ?", (ts, task_id))
