"""Mandatory closing summary (tasks.resolution)."""
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
from test_app import DONE, app, client, conn, events, make  # noqa: E402,F401

SUMMARY = "Rolled out the new invoicing flow; errors dropped from 5% to under 1%."


def test_cannot_close_without_summary(conn):
    tid = make(conn)
    for bad in (None, "", "   ", "done"):  # missing / blank / too short
        with pytest.raises(ValueError, match="closing summary"):
            with conn:
                db.change_state(conn, tid, "closed", resolution=bad)
    assert db.get_task(conn, tid)["state"] == "new"


def test_cannot_create_closed_without_summary(conn):
    with pytest.raises(ValueError):
        make(conn, state="closed")
    tid = make(conn, state="closed", resolution=SUMMARY)
    assert db.get_task(conn, tid)["resolution"] == SUMMARY


def test_close_with_summary_is_stored_and_logged(conn):
    tid = make(conn)
    with conn:
        db.change_state(conn, tid, "closed", resolution=SUMMARY)
    t = db.get_task(conn, tid)
    assert t["state"] == "closed" and t["resolution"] == SUMMARY
    ev = [e for e in events(conn, tid) if e["event_type"] == "resolution"]
    assert ev and ev[-1]["new_value"] == SUMMARY


def test_editing_summary_is_logged_and_kept_on_reopen(conn):
    tid = make(conn)
    with conn:
        db.change_state(conn, tid, "closed", resolution=SUMMARY)
        db.update_task(conn, tid, {**dict(db.get_task(conn, tid)), "resolution": SUMMARY + " More."})
    edits = [e for e in events(conn, tid) if e["event_type"] == "edited" and e["detail"] == "resolution"]
    assert edits[-1]["old_value"] == SUMMARY
    with conn:
        db.change_state(conn, tid, "triage")  # reopen: no summary needed
    assert db.get_task(conn, tid)["resolution"] == SUMMARY + " More."  # prefilled for next close


def test_http_close_requires_summary(client, conn):
    tid = make(conn, title="Http task")
    r = client.post(f"/task/{tid}/state", data={"state": "closed"}, follow_redirects=True)
    assert "closing summary is required" in r.get_data(as_text=True)
    assert db.get_task(conn, tid)["state"] == "new"
    client.post(f"/task/{tid}/state", data={"state": "closed", "resolution": SUMMARY})
    assert db.get_task(conn, tid)["state"] == "closed"
    page = client.get(f"/task/{tid}").get_data(as_text=True)
    assert SUMMARY in page and "Closing summary" in page
    assert SUMMARY in client.get("/closed").get_data(as_text=True)


def test_edit_form_requires_summary_when_closing(client, conn):
    tid = make(conn, title="Form task")
    base = {"title": "Form task", "priority": "Medium", "state": "closed"}
    assert client.post(f"/task/{tid}/edit", data=base).status_code == 400
    assert client.post(f"/task/{tid}/edit", data={**base, "resolution": SUMMARY}).status_code == 302


def test_dashboard_has_close_dialog(client, conn):
    make(conn, title="Row")
    page = client.get("/").get_data(as_text=True)
    assert 'id="close-dialog"' in page and 'name="resolution"' in page


def test_review_shows_outcome(client, conn):
    tid = make(conn, title="Reviewed")
    with conn:
        db.change_state(conn, tid, "closed", resolution=SUMMARY)
    today = date.today().isoformat()
    q = {"start": today, "end": today}
    assert SUMMARY in client.get("/review", query_string=q).get_data(as_text=True)
    assert SUMMARY in client.get("/review.html", query_string=q).get_data(as_text=True)
    csv_text = client.get("/review.csv", query_string=q).get_data(as_text=True)
    assert "Closing summary" in csv_text.splitlines()[0] and SUMMARY in csv_text


def test_old_closed_task_without_summary_flagged_in_review(client, conn):
    with conn:
        conn.execute("INSERT INTO tasks (title, state, created_at, updated_at, closed_at)"
                     " VALUES ('Legacy', 'closed', '2025-02-01T09:00:00', '2025-02-01T09:00:00',"
                     " '2025-03-01T09:00:00')")
    page = client.get("/review?start=2025-01-01&end=2025-12-31").get_data(as_text=True)
    assert "Legacy" in page and "No closing summary" in page
    export = client.get("/review.html?start=2025-01-01&end=2025-12-31").get_data(as_text=True)
    assert "Legacy" in export and "No closing summary" not in export  # hint is in-app only


def test_backup_roundtrip_keeps_summary(conn, tmp_path):
    tid = make(conn)
    with conn:
        db.change_state(conn, tid, "closed", resolution=SUMMARY)
    data = json.loads(json.dumps(backup.export_data(conn)))
    other = create_app(tmp_path / "o")
    c2 = db.connect(other.config["DB_PATH"])
    with c2:
        backup.import_data(c2, data, "replace")
    assert c2.execute("SELECT resolution FROM tasks").fetchone()[0] == SUMMARY
    c2.close()


def test_old_backup_closed_task_without_summary_still_imports(conn):
    data = {"version": 1, "comments": [], "log": [], "tasks": [
        {"id": 7, "title": "Old", "state": "closed", "priority": "Low",
         "created_at": "2025-01-01T09:00:00", "closed_at": "2025-02-01T09:00:00"}]}
    with conn:
        assert backup.import_data(conn, data, "merge") == 1


def test_old_database_gets_resolution_column(tmp_path):
    p = tmp_path / "v11.db"
    old = sqlite3.connect(p)
    old.executescript(db.SCHEMA.replace("    resolution  TEXT NOT NULL DEFAULT '',\n", ""))
    old.execute("INSERT INTO tasks (title, state, created_at, updated_at) VALUES ('x','new','a','a')")
    old.commit()
    old.close()
    db.init_db(str(p))
    c = db.connect(str(p))
    assert c.execute("SELECT resolution FROM tasks").fetchone()[0] == ""
    c.close()
    db.init_db(str(p))  # running again is harmless
