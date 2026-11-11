# Copyright (c) 2026 Anooj Prabaharan. All rights reserved.
"""SQLite storage for MyTodo.

All mutating helpers write a matching row to the `log` table inside the same
transaction, so the audit trail can never be skipped.
"""
import sqlite3
import zlib
from datetime import datetime

STATES = ["new", "triage", "depended", "closed"]
PRIORITIES = ["Low", "Medium", "High"]
PRIORITY_RANK = {"High": 3, "Medium": 2, "Low": 1}
MIN_RESOLUTION = 10  # characters required in a closing summary
MAX_LABEL = 40       # characters in a label name
# label colours: (name shown in the picker, hex)
LABEL_COLORS = [("Blue", "#3b82f6"), ("Green", "#059669"), ("Orange", "#d97706"),
                ("Purple", "#8b5cf6"), ("Red", "#dc2626"), ("Teal", "#0891b2"),
                ("Pink", "#db2777"), ("Grey", "#64748b")]
LABEL_HEXES = [h for _, h in LABEL_COLORS]

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
CREATE TABLE IF NOT EXISTS labels (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL UNIQUE COLLATE NOCASE,
    color TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS task_labels (
    task_id  INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    label_id INTEGER NOT NULL REFERENCES labels(id) ON DELETE CASCADE,
    PRIMARY KEY (task_id, label_id)
);
CREATE INDEX IF NOT EXISTS idx_task_labels_label ON task_labels(label_id);
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


LABEL_FILTER = " AND {col} IN (SELECT task_id FROM task_labels WHERE label_id = ?)"


def list_tasks(conn, closed=False, state=None, priority=None, q=None, sort="due", label=None):
    sql = "SELECT * FROM tasks WHERE " + ("state = 'closed'" if closed else "state != 'closed'")
    args = []
    if label:
        sql += LABEL_FILTER.format(col="id")
        args.append(label)
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


def report_rows(conn, label=None):
    """Open tasks with their most recent comment, ordered by due date (undated last)."""
    where, args = "", ()
    if label:
        where, args = LABEL_FILTER.format(col="t.id"), (label,)
    return conn.execute(
        """
        SELECT t.*, c.body AS last_comment, c.created_at AS last_comment_at
          FROM tasks t
          LEFT JOIN comments c ON c.id = (
                SELECT id FROM comments WHERE task_id = t.id
                 ORDER BY created_at DESC, id DESC LIMIT 1)
         WHERE t.state != 'closed' {where}
         ORDER BY t.due_date IS NULL, t.due_date,
                  CASE t.priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END, t.id
        """.format(where=where), args
    ).fetchall()


def counts(conn, label=None):
    where, args = "", []
    if label:
        where, args = LABEL_FILTER.format(col="id"), [label]
    rows = conn.execute(
        f"SELECT state, COUNT(*) AS n FROM tasks WHERE 1=1 {where} GROUP BY state", args).fetchall()
    result = {s: 0 for s in STATES}
    result.update({r["state"]: r["n"] for r in rows})
    today = datetime.now().date().isoformat()
    result["overdue"] = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE state != 'closed' AND due_date IS NOT NULL"
        f" AND due_date < ? {where}", [today, *args],
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
    if fields.get("labels"):
        set_task_labels(conn, task_id, fields["labels"], at=ts)
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
    if fields.get("labels") is not None:  # only forms that edit labels send this
        set_task_labels(conn, task_id, fields["labels"], at=ts)


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


# ---------- labels ----------

def parse_label_names(value):
    """Clean label names from a comma-separated string and/or a list of strings."""
    items = [value] if isinstance(value, str) else list(value or [])
    names, seen = [], set()
    for item in items:
        for part in str(item).split(","):
            name = " ".join(part.split())[:MAX_LABEL]
            if name and name.casefold() not in seen:
                seen.add(name.casefold())
                names.append(name)
    return names


def _label_color(name):
    return LABEL_HEXES[zlib.crc32(name.casefold().encode("utf-8")) % len(LABEL_HEXES)]


def get_label(conn, label_id):
    return conn.execute("SELECT * FROM labels WHERE id = ?", (label_id,)).fetchone()


def get_or_create_label(conn, name):
    row = conn.execute("SELECT * FROM labels WHERE name = ?", (name,)).fetchone()  # NOCASE
    if row:
        return row
    cur = conn.execute("INSERT INTO labels (name, color) VALUES (?, ?)", (name, _label_color(name)))
    return get_label(conn, cur.lastrowid)


def task_labels(conn, task_ids):
    """{task_id: [label rows]} for many tasks in one query."""
    ids = list(task_ids)
    result = {i: [] for i in ids}
    if not ids:
        return result
    marks = ",".join("?" * len(ids))
    for r in conn.execute(
            f"SELECT tl.task_id, l.* FROM task_labels tl JOIN labels l ON l.id = tl.label_id"
            f" WHERE tl.task_id IN ({marks}) ORDER BY l.name COLLATE NOCASE", ids):
        result[r["task_id"]].append(r)
    return result


def label_names(conn, task_id):
    return [r["name"] for r in task_labels(conn, [task_id])[task_id]]


def _names_str(names):
    return ", ".join(names) or None


def set_task_labels(conn, task_id, names, at=None):
    """Replace a task's labels; logs a 'labels' event if they changed."""
    wanted = [get_or_create_label(conn, n) for n in parse_label_names(names)]
    current = task_labels(conn, [task_id])[task_id]
    if {r["id"] for r in wanted} == {r["id"] for r in current}:
        return False
    conn.execute("DELETE FROM task_labels WHERE task_id = ?", (task_id,))
    conn.executemany("INSERT INTO task_labels (task_id, label_id) VALUES (?, ?)",
                     [(task_id, r["id"]) for r in wanted])
    after = label_names(conn, task_id)
    _log(conn, task_id, "labels", old=_names_str([r["name"] for r in current]),
         new=_names_str(after), at=at)
    return True


def list_labels(conn):
    return conn.execute(
        """
        SELECT l.*, COALESCE(SUM(t.state != 'closed'), 0) AS n_open,
               COALESCE(SUM(t.state = 'closed'), 0) AS n_closed
          FROM labels l
          LEFT JOIN task_labels tl ON tl.label_id = l.id
          LEFT JOIN tasks t ON t.id = tl.task_id
         GROUP BY l.id ORDER BY l.name COLLATE NOCASE
        """).fetchall()


def create_label(conn, name, color=None):
    names = parse_label_names(name)
    if not names:
        raise ValueError("Give the label a name.")
    existing = conn.execute("SELECT * FROM labels WHERE name = ?", (names[0],)).fetchone()
    if existing:
        raise ValueError(f"A label called “{existing['name']}” already exists.")
    row = get_or_create_label(conn, names[0])
    if color:
        recolor_label(conn, row["id"], color)
    return row["id"]


def _tasks_with_label(conn, label_id):
    return [r[0] for r in conn.execute(
        "SELECT task_id FROM task_labels WHERE label_id = ?", (label_id,))]


def _log_label_changes(conn, before):
    ts = now()
    for task_id, old in before.items():
        new = label_names(conn, task_id)
        if old != new:
            _log(conn, task_id, "labels", old=_names_str(old), new=_names_str(new), at=ts)


def rename_label(conn, label_id, new_name):
    label = get_label(conn, label_id)
    if label is None:
        raise KeyError(label_id)
    names = parse_label_names(new_name)
    if not names:
        raise ValueError("A label name cannot be empty.")
    clash = conn.execute("SELECT name FROM labels WHERE name = ? AND id != ?",
                         (names[0], label_id)).fetchone()
    if clash:
        raise ValueError(f"A label called “{clash['name']}” already exists.")
    if names[0] == label["name"]:
        return
    before = {t: label_names(conn, t) for t in _tasks_with_label(conn, label_id)}
    conn.execute("UPDATE labels SET name = ? WHERE id = ?", (names[0], label_id))
    _log_label_changes(conn, before)


def recolor_label(conn, label_id, color):
    if color not in LABEL_HEXES:
        raise ValueError("Pick one of the listed colours.")
    conn.execute("UPDATE labels SET color = ? WHERE id = ?", (color, label_id))


def delete_label(conn, label_id):
    if get_label(conn, label_id) is None:
        raise KeyError(label_id)
    before = {t: label_names(conn, t) for t in _tasks_with_label(conn, label_id)}
    conn.execute("DELETE FROM labels WHERE id = ?", (label_id,))
    _log_label_changes(conn, before)
