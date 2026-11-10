"""JSON export / import for MyTodo."""
import json
from datetime import datetime
from pathlib import Path

from db import STATES, PRIORITIES, _log, now

BACKUP_VERSION = 1
TASK_COLS = ["id", "title", "description", "priority", "due_date", "state", "depends_on",
             "resolution", "created_at", "updated_at", "closed_at"]
COMMENT_COLS = ["id", "task_id", "body", "created_at"]
LOG_COLS = ["id", "task_id", "event_type", "old_value", "new_value", "detail", "created_at"]
REVIEW_COLS = ["id", "start", "end", "notes", "exclude", "comments", "saved_at"]
NOTE_COLS = ["period", "body", "updated_at"]


class BackupError(ValueError):
    pass


def export_data(conn):
    def rows(table, cols, order="id"):
        return [dict(r) for r in
                conn.execute(f"SELECT {', '.join(cols)} FROM {table} ORDER BY {order}")]
    return {
        "app": "MyTodo",
        "version": BACKUP_VERSION,
        "exported_at": now(),
        "tasks": rows("tasks", TASK_COLS),
        "comments": rows("comments", COMMENT_COLS),
        "log": rows("log", LOG_COLS),
        "reviews": rows("reviews", REVIEW_COLS),
        "review_notes": rows("review_notes", NOTE_COLS, order="period"),
    }


def backup_filename():
    return f"mytodo-backup-{datetime.now():%Y%m%d-%H%M%S}.json"


def write_backup_file(conn, folder, keep=None, prefix=""):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (prefix + backup_filename())
    path.write_text(json.dumps(export_data(conn), indent=2), encoding="utf-8")
    if keep:
        old = sorted(folder.glob(prefix + "mytodo-backup-*.json"))
        for stale in old[:-keep]:
            stale.unlink(missing_ok=True)
    return path


def validate(data):
    """Check structure before anything is written. Raises BackupError."""
    if not isinstance(data, dict):
        raise BackupError("Backup file is not a JSON object.")
    if data.get("version") != BACKUP_VERSION:
        raise BackupError(f"Unsupported backup version: {data.get('version')!r}")
    for key in ("tasks", "comments", "log"):
        if not isinstance(data.get(key), list):
            raise BackupError(f"Backup is missing the '{key}' list.")
    ids = set()
    for t in data["tasks"]:
        if not isinstance(t, dict) or not isinstance(t.get("id"), int):
            raise BackupError("Every task needs an integer 'id'.")
        if not str(t.get("title") or "").strip():
            raise BackupError(f"Task {t['id']} has no title.")
        if t.get("state") not in STATES:
            raise BackupError(f"Task {t['id']} has invalid state {t.get('state')!r}.")
        if t.get("priority") not in PRIORITIES:
            raise BackupError(f"Task {t['id']} has invalid priority {t.get('priority')!r}.")
        if t["id"] in ids:
            raise BackupError(f"Duplicate task id {t['id']}.")
        ids.add(t["id"])
    for key, required in (("comments", ("task_id", "body", "created_at")),
                          ("log", ("task_id", "event_type", "created_at"))):
        for row in data[key]:
            if not isinstance(row, dict) or any(row.get(k) in (None, "") for k in required):
                raise BackupError(f"A '{key}' entry is missing required fields.")
            if row["task_id"] not in ids:
                raise BackupError(f"A '{key}' entry refers to unknown task {row['task_id']}.")
    # optional sections (added in v1.1.0; older backups simply don't have them)
    for key, required in (("reviews", ("start", "end", "saved_at")),
                          ("review_notes", ("period", "updated_at"))):
        rows = data.get(key, [])
        if not isinstance(rows, list):
            raise BackupError(f"'{key}' must be a list.")
        for row in rows:
            if not isinstance(row, dict) or any(row.get(k) in (None, "") for k in required):
                raise BackupError(f"A '{key}' entry is missing required fields.")


def import_data(conn, data, mode="merge"):
    """Import a validated backup. mode = 'replace' or 'merge'. Returns #tasks imported.

    The caller's connection context manager commits on success / rolls back on error,
    so a failure part-way leaves the database untouched.
    """
    validate(data)
    if mode not in ("replace", "merge"):
        raise BackupError(f"Unknown import mode {mode!r}.")
    if mode == "replace":
        conn.execute("DELETE FROM log")
        conn.execute("DELETE FROM comments")
        conn.execute("DELETE FROM tasks")
        conn.execute("DELETE FROM reviews")
        conn.execute("DELETE FROM review_notes")

    ts = now()
    id_map = {}
    for t in data["tasks"]:
        cur = conn.execute(
            "INSERT INTO tasks (title, description, priority, due_date, state, depends_on,"
            " resolution, created_at, updated_at, closed_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (t["title"], t.get("description") or "", t["priority"], t.get("due_date"),
             t["state"], t.get("depends_on") or "", t.get("resolution") or "",
             t.get("created_at") or ts,
             t.get("updated_at") or ts, t.get("closed_at")),
        )
        id_map[t["id"]] = cur.lastrowid
    for c in data["comments"]:
        conn.execute("INSERT INTO comments (task_id, body, created_at) VALUES (?, ?, ?)",
                     (id_map[c["task_id"]], c["body"], c["created_at"]))
    for entry in data["log"]:
        conn.execute(
            "INSERT INTO log (task_id, event_type, old_value, new_value, detail, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (id_map[entry["task_id"]], entry["event_type"], entry.get("old_value"),
             entry.get("new_value"), entry.get("detail"), entry["created_at"]),
        )
    for r in data.get("reviews", []):
        # excluded task ids refer to the backup's ids: translate to the new ones
        old_ids = [int(x) for x in str(r.get("exclude") or "").split(",") if x.strip().isdigit()]
        new_ids = sorted(id_map[i] for i in old_ids if i in id_map)
        conn.execute(
            "INSERT INTO reviews (start, end, notes, exclude, comments, saved_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (r["start"], r["end"], r.get("notes") or "", ",".join(map(str, new_ids)),
             r.get("comments") or "latest", r["saved_at"]),
        )
    for n in data.get("review_notes", []):
        conn.execute(
            "INSERT INTO review_notes (period, body, updated_at) VALUES (?, ?, ?)"
            " ON CONFLICT(period) DO UPDATE SET body = excluded.body,"
            " updated_at = excluded.updated_at",
            (n["period"], n.get("body") or "", n["updated_at"]),
        )
    for new_id in id_map.values():
        _log(conn, new_id, "imported", new=mode, detail=f"Imported from backup ({mode})", at=ts)
    return len(id_map)
