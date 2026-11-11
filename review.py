# Copyright (c) 2026 Anooj Prabaharan. All rights reserved.
"""Performance review: what was completed and what was in progress during a period.

Tasks are selected purely by their dates (created_at / closed_at), so earlier
years never leak into a review. Saved reviews only record the period, summary
and choices made, and are rebuilt from the same data when viewed again.
"""
from datetime import date, datetime, timedelta

from db import now, task_labels

COMMENT_MODES = ("latest", "all", "none")


# ---------- periods ----------

def _parse_date(value):
    try:
        return datetime.strptime((value or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def last_review_end(conn):
    row = conn.execute("SELECT MAX(end) FROM reviews").fetchone()
    return _parse_date(row[0]) if row and row[0] else None


def default_period(conn, today=None):
    today = today or date.today()
    last = last_review_end(conn)
    start = last + timedelta(days=1) if last and last < today else date(today.year, 1, 1)
    return start, today


def quick_periods(conn, today=None):
    today = today or date.today()
    periods = []
    last = last_review_end(conn)
    if last and last < today:
        periods.append(("Since last review", last + timedelta(days=1), today))
    periods += [
        ("This year", date(today.year, 1, 1), today),
        ("Last year", date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)),
        ("Last 12 months", today - timedelta(days=364), today),
    ]
    return periods


def parse_period(args, conn):
    d_start, d_end = default_period(conn)
    start = _parse_date(args.get("start")) or d_start
    end = _parse_date(args.get("end")) or d_end
    if start > end:
        start, end = end, start
    return start, end


def parse_exclude(value):
    ids = set()
    for part in (value or "").split(","):
        part = part.strip()
        if part.isdigit():
            ids.add(int(part))
    return frozenset(ids)


def exclude_str(ids):
    return ",".join(str(i) for i in sorted(ids))


def parse_comments(value):
    return value if value in COMMENT_MODES else "latest"


# ---------- data ----------

def _bounds(start, end):
    return start.isoformat(), (end + timedelta(days=1)).isoformat()  # [lo, hi)


def _days_between(a, b):
    try:
        return (datetime.fromisoformat(b).date() - datetime.fromisoformat(a).date()).days
    except (TypeError, ValueError):
        return None


def _attach_comments(conn, tasks, lo, hi, mode):
    if mode == "none" or not tasks:
        for t in tasks:
            t["comments"] = []
        return
    ids = [t["id"] for t in tasks]
    marks = ",".join("?" * len(ids))
    rows = conn.execute(
        f"SELECT task_id, body, created_at FROM comments WHERE task_id IN ({marks})"
        " AND created_at >= ? AND created_at < ? ORDER BY created_at, id",
        (*ids, lo, hi),
    ).fetchall()
    by_task = {}
    for r in rows:
        by_task.setdefault(r["task_id"], []).append(dict(r))
    for t in tasks:
        cs = by_task.get(t["id"], [])
        t["comments"] = cs[-1:] if mode == "latest" else cs


def review_data(conn, start, end, exclude=frozenset(), comments="latest"):
    lo, hi = _bounds(start, end)
    completed_all = [dict(r) for r in conn.execute(
        "SELECT * FROM tasks WHERE state = 'closed' AND closed_at >= ? AND closed_at < ?"
        " ORDER BY closed_at, id", (lo, hi))]
    progress_all = [dict(r) for r in conn.execute(
        "SELECT * FROM tasks WHERE created_at < ? AND (closed_at IS NULL OR closed_at >= ?)"
        " ORDER BY due_date IS NULL, due_date,"
        " CASE priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END, id", (hi, hi))]

    for t in completed_all:
        t["days_taken"] = _days_between(t["created_at"], t["closed_at"])
        if t["due_date"]:
            t["on_time"] = t["closed_at"][:10] <= t["due_date"]
        else:
            t["on_time"] = None
    end_iso = end.isoformat()
    for t in progress_all:
        t["closed_later"] = t["closed_at"] if t["state"] == "closed" else None
        t["overdue_at_end"] = bool(t["due_date"] and t["due_date"] < end_iso)

    for group in (completed_all, progress_all):
        for t in group:
            t["included"] = t["id"] not in exclude
    _attach_comments(conn, completed_all + progress_all, lo, hi, comments)
    labels = task_labels(conn, [t["id"] for t in completed_all + progress_all])
    for t in completed_all + progress_all:
        t["labels"] = labels[t["id"]]

    completed = [t for t in completed_all if t["included"]]
    in_progress = [t for t in progress_all if t["included"]]
    with_due = [t for t in completed if t["on_time"] is not None]
    new_taken = conn.execute(
        "SELECT id FROM tasks WHERE created_at >= ? AND created_at < ?", (lo, hi)).fetchall()
    stats = {
        "completed": len(completed),
        "in_progress": len(in_progress),
        "new": sum(1 for r in new_taken if r["id"] not in exclude),
        "high_completed": sum(1 for t in completed if t["priority"] == "High"),
        "with_due": len(with_due),
        "on_time": sum(1 for t in with_due if t["on_time"]),
        "on_time_pct": round(100 * sum(1 for t in with_due if t["on_time"]) / len(with_due))
        if with_due else None,
    }
    return {"completed_all": completed_all, "progress_all": progress_all,
            "completed": completed, "in_progress": in_progress, "stats": stats}


# ---------- draft summary ----------

def _period_key(start, end):
    return f"{start.isoformat()}_{end.isoformat()}"


def get_draft_notes(conn, start, end):
    row = conn.execute("SELECT body FROM review_notes WHERE period = ?",
                       (_period_key(start, end),)).fetchone()
    return row["body"] if row else ""


def save_draft_notes(conn, start, end, body):
    conn.execute(
        "INSERT INTO review_notes (period, body, updated_at) VALUES (?, ?, ?)"
        " ON CONFLICT(period) DO UPDATE SET body = excluded.body, updated_at = excluded.updated_at",
        (_period_key(start, end), (body or "").strip(), now()),
    )


# ---------- saved reviews ----------

def save_review(conn, start, end, notes, exclude, comments):
    cur = conn.execute(
        "INSERT INTO reviews (start, end, notes, exclude, comments, saved_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (start.isoformat(), end.isoformat(), (notes or "").strip(), exclude_str(exclude),
         parse_comments(comments), now()),
    )
    return cur.lastrowid


def get_review(conn, review_id):
    row = conn.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
    if row is None:
        return None
    r = dict(row)
    r["start_d"], r["end_d"] = _parse_date(r["start"]), _parse_date(r["end"])
    r["exclude_ids"] = parse_exclude(r["exclude"])
    return r


def list_reviews(conn):
    out = []
    for row in conn.execute("SELECT id FROM reviews ORDER BY end DESC, id DESC"):
        r = get_review(conn, row["id"])
        stats = review_data(conn, r["start_d"], r["end_d"], r["exclude_ids"], "none")["stats"]
        r["n_completed"], r["n_in_progress"] = stats["completed"], stats["in_progress"]
        out.append(r)
    return out


def delete_review(conn, review_id):
    conn.execute("DELETE FROM reviews WHERE id = ?", (review_id,))


# ---------- CSV ----------

CSV_HEADER = ["Section", "ID", "Task", "Priority", "Labels", "State", "Started", "Completed",
              "Days taken", "Due date", "On time", "Closing summary", "Depends on", "Description",
              "Comments"]


def csv_rows(data):
    def comments_text(t):
        return "\n".join(f"[{c['created_at'][:10]}] {c['body']}" for c in t["comments"])
    def labels_text(t):
        return ", ".join(x["name"] for x in t.get("labels", []))
    for t in data["completed"]:
        yield ["Completed", t["id"], t["title"], t["priority"], labels_text(t), t["state"],
               t["created_at"][:10],
               t["closed_at"][:10], t["days_taken"] if t["days_taken"] is not None else "",
               t["due_date"] or "", {True: "Yes", False: "No", None: ""}[t["on_time"]],
               t["resolution"], "", t["description"], comments_text(t)]
    for t in data["in_progress"]:
        yield ["In progress", t["id"], t["title"], t["priority"], labels_text(t), t["state"],
               t["created_at"][:10],
               (t["closed_later"] or "")[:10], "", t["due_date"] or "", "",
               t["resolution"] if t["closed_later"] else "", t["depends_on"], t["description"],
               comments_text(t)]
