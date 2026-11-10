import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import backup  # noqa: E402
import db  # noqa: E402
import review  # noqa: E402
from app import create_app  # noqa: E402
from test_app import app, client, conn, make  # noqa: E402,F401  (fixtures)


def put(conn, title, created, closed=None, due=None, state=None, priority="Medium"):
    """Insert a task with explicit timestamps (bypassing now())."""
    st = state or ("closed" if closed else "new")
    cur = conn.execute(
        "INSERT INTO tasks (title, priority, due_date, state, created_at, updated_at, closed_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)", (title, priority, due, st, created, created, closed))
    return cur.lastrowid


def comment(conn, tid, body, at):
    conn.execute("INSERT INTO comments (task_id, body, created_at) VALUES (?, ?, ?)",
                 (tid, body, at))


Y_START, Y_END = date(2025, 1, 1), date(2025, 12, 31)
Q = {"start": "2025-01-01", "end": "2025-12-31"}


@pytest.fixture
def year(conn):
    """Tasks around a 2025 review period."""
    with conn:
        ids = {
            "old": put(conn, "Closed in 2024", "2024-03-01T09:00:00", "2024-12-20T10:00:00"),
            "done": put(conn, "Shipped billing", "2025-01-10T09:00:00", "2025-03-01T17:00:00",
                        due="2025-03-05", priority="High"),
            "late": put(conn, "Late migration", "2025-02-01T09:00:00", "2025-06-10T12:00:00",
                        due="2025-05-31"),
            "edge": put(conn, "Closed on last day", "2025-11-01T09:00:00", "2025-12-31T23:59:00"),
            "after": put(conn, "Closed in Jan 2026", "2025-09-01T09:00:00", "2026-01-15T09:00:00"),
            "open": put(conn, "Still running", "2024-11-01T09:00:00", state="depended"),
            "future": put(conn, "Created in 2026", "2026-02-01T09:00:00"),
        }
        comment(conn, ids["done"], "kickoff", "2025-01-11T09:00:00")
        comment(conn, ids["done"], "went live", "2025-03-01T16:00:00")
        comment(conn, ids["open"], "from last year", "2024-12-01T09:00:00")
        comment(conn, ids["open"], "this year update", "2025-07-01T09:00:00")
    return ids


def titles(tasks):
    return [t["title"] for t in tasks]


def test_sections(conn, year):
    d = review.review_data(conn, Y_START, Y_END)
    assert titles(d["completed"]) == ["Shipped billing", "Late migration", "Closed on last day"]
    assert set(titles(d["in_progress"])) == {"Closed in Jan 2026", "Still running"}
    after = next(t for t in d["in_progress"] if t["title"] == "Closed in Jan 2026")
    assert after["closed_later"].startswith("2026-01-15")


def test_stats(conn, year):
    s = review.review_data(conn, Y_START, Y_END)["stats"]
    assert s["completed"] == 3 and s["in_progress"] == 2
    assert s["new"] == 4  # done, late, edge, after were created in 2025
    assert s["high_completed"] == 1
    assert (s["on_time"], s["with_due"], s["on_time_pct"]) == (1, 2, 50)


def test_comment_modes(conn, year):
    def comments_of(mode, key):
        d = review.review_data(conn, Y_START, Y_END, comments=mode)
        t = next(t for t in d["completed"] + d["in_progress"] if t["id"] == year[key])
        return [c["body"] for c in t["comments"]]
    assert comments_of("all", "done") == ["kickoff", "went live"]
    assert comments_of("latest", "done") == ["went live"]
    assert comments_of("none", "done") == []
    assert comments_of("all", "open") == ["this year update"]  # 2024 comment is outside period


def test_exclude_everywhere(client, conn, year):
    q = {**Q, "exclude": str(year["late"])}
    d = review.review_data(conn, Y_START, Y_END, frozenset({year["late"]}))
    assert "Late migration" not in titles(d["completed"]) and d["stats"]["completed"] == 2
    assert d["stats"]["on_time_pct"] == 100
    html = client.get("/review.html", query_string=q).get_data(as_text=True)
    assert "Shipped billing" in html and "Late migration" not in html
    csv_text = client.get("/review.csv", query_string=q).get_data(as_text=True)
    assert "Shipped billing" in csv_text and "Late migration" not in csv_text
    page = client.get("/review", query_string=q).get_data(as_text=True)
    assert "Late migration" in page and "rv-card excluded" in page  # greyed, can re-include


def test_export_is_standalone(client, conn, year):
    r = client.get("/review.html", query_string=Q)
    body = r.get_data(as_text=True)
    assert "attachment" in r.headers["Content-Disposition"]
    assert "<style>" in body and "/static/" not in body and "<nav" not in body
    assert "01 Jan 2025" in body and "31 Dec 2025" in body
    assert "rv-toggle" not in body  # no in-app controls


def test_page_renders(client, conn, year):
    page = client.get("/review", query_string={**Q, "comments": "all"}).get_data(as_text=True)
    assert "Shipped billing" in page and "Closed in 2024" not in page
    assert "Created in 2026" not in page and "went live" in page
    assert client.get("/review?start=bad&end=2025-13-45").status_code == 200


def test_draft_notes_save_view_delete(client, conn, year):
    q = {**Q, "comments": "all"}
    client.post("/review/notes", data={**q, "notes": "Great year"})
    assert "Great year" in client.get("/review", query_string=q).get_data(as_text=True)

    client.post("/review/save", data={**q, "notes": "Great year"})  # no confirmation
    assert review.list_reviews(conn) == []

    r = client.post("/review/save", data={**q, "notes": "Great year", "confirm": "yes",
                                           "exclude": str(year["late"])})
    rid = int(r.headers["Location"].rstrip("/").split("/")[-1])
    saved = review.get_review(conn, rid)
    assert saved["notes"] == "Great year" and saved["exclude_ids"] == {year["late"]}
    assert review.default_period(conn, today=date(2026, 11, 9)) == (date(2026, 1, 1),
                                                                   date(2026, 11, 9))

    page = client.get(f"/review/{rid}").get_data(as_text=True)
    assert "Great year" in page and "Shipped billing" in page and "Late migration" not in page
    dl = client.get(f"/review/{rid}?format=html").get_data(as_text=True)
    assert "Great year" in dl and "Late migration" not in dl
    assert "Shipped billing" in client.get(f"/review/{rid}?format=csv").get_data(as_text=True)
    assert "Past reviews" in client.get("/review").get_data(as_text=True)

    n = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    client.post(f"/review/{rid}/delete")
    assert review.get_review(conn, rid) is None
    assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == n


def test_default_period_follows_last_saved_review(conn):
    today = date(2026, 11, 9)
    assert review.default_period(conn, today=today) == (date(2026, 1, 1), today)
    with conn:
        review.save_review(conn, date(2025, 4, 1), date(2026, 3, 31), "", frozenset(), "latest")
    assert review.default_period(conn, today=today) == (date(2026, 4, 1), today)
    assert review.quick_periods(conn, today=today)[0][0] == "Since last review"


def test_backup_keeps_reviews_and_remaps_exclude(conn, year, tmp_path):
    with conn:
        review.save_draft_notes(conn, Y_START, Y_END, "draft")
        review.save_review(conn, Y_START, Y_END, "final", frozenset({year["late"]}), "all")
    data = json.loads(json.dumps(backup.export_data(conn)))

    other = create_app(tmp_path / "o")
    c2 = db.connect(other.config["DB_PATH"])
    with c2:
        make(c2, title="pre-existing")  # shifts ids, so merge must remap
        backup.import_data(c2, data, "merge")
    r = review.list_reviews(c2)[0]
    late_new = c2.execute("SELECT id FROM tasks WHERE title='Late migration'").fetchone()[0]
    assert late_new != year["late"]
    assert r["notes"] == "final" and r["exclude_ids"] == {late_new}
    assert review.get_draft_notes(c2, Y_START, Y_END) == "draft"
    c2.close()


def test_old_backup_without_review_sections_imports(conn):
    make(conn, title="x")
    data = backup.export_data(conn)
    del data["reviews"], data["review_notes"]
    with conn:
        assert backup.import_data(conn, data, "merge") == 1


def test_old_database_gets_new_tables(tmp_path):
    p = tmp_path / "old.db"
    old = sqlite3.connect(p)
    old.executescript(db.SCHEMA.split("CREATE TABLE IF NOT EXISTS review_notes")[0])
    old.close()
    db.init_db(str(p))
    c = db.connect(str(p))
    names = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    c.close()
    assert {"reviews", "review_notes", "tasks"} <= names
