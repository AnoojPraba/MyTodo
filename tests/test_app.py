# Copyright (c) 2026 Anooj Prabaharan. All rights reserved.
import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import backup  # noqa: E402
import db  # noqa: E402
from app import create_app  # noqa: E402


@pytest.fixture
def app(tmp_path):
    return create_app(tmp_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def conn(app):
    c = db.connect(app.config["DB_PATH"])
    yield c
    c.close()


DONE = "Delivered and signed off by the team."


def make(conn, **kw):
    fields = {"title": "Task", "priority": "Medium", "state": "new", **kw}
    with conn:
        return db.create_task(conn, fields)


def events(conn, task_id):
    return [dict(r) for r in conn.execute(
        "SELECT * FROM log WHERE task_id = ? ORDER BY id", (task_id,))]


def test_create_logs(conn):
    tid = make(conn, title="Write report")
    ev = events(conn, tid)
    assert ev[0]["event_type"] == "created" and ev[0]["new_value"] == "new"


def test_state_change_logs_old_and_new(conn):
    tid = make(conn)
    with conn:
        db.change_state(conn, tid, "depended", "Waiting on Bob")
    ev = [e for e in events(conn, tid) if e["event_type"] == "state_change"]
    assert (ev[0]["old_value"], ev[0]["new_value"]) == ("new", "depended")
    assert db.get_task(conn, tid)["depends_on"] == "Waiting on Bob"
    assert any(e["event_type"] == "dependency" for e in events(conn, tid))


def test_due_date_change_logged(client, conn):
    tid = make(conn, title="Dated", due_date="2026-11-01")
    task = dict(db.get_task(conn, tid))
    with conn:
        db.update_task(conn, tid, {**task, "due_date": "2026-11-15"})
        db.update_task(conn, tid, {**task, "due_date": ""})
    ev = [e for e in events(conn, tid) if e["event_type"] == "edited" and e["detail"] == "due_date"]
    assert [(e["old_value"], e["new_value"]) for e in ev] == [
        ("2026-11-01", "2026-11-15"), ("2026-11-15", None)]
    page = client.get(f"/task/{tid}").get_data(as_text=True)
    assert "01 Nov 2026" in page and "15 Nov 2026" in page


def test_close_sets_closed_at_and_reopen_clears(conn):
    tid = make(conn)
    with conn:
        db.change_state(conn, tid, "closed", resolution=DONE)
    assert db.get_task(conn, tid)["closed_at"]
    with conn:
        db.change_state(conn, tid, "triage")
    assert db.get_task(conn, tid)["closed_at"] is None


def test_comment_logs(conn):
    tid = make(conn)
    with conn:
        db.add_comment(conn, tid, "Called the vendor")
    ev = events(conn, tid)[-1]
    assert ev["event_type"] == "comment" and ev["detail"] == "Called the vendor"


def test_invalid_input_rejected(conn):
    with pytest.raises(ValueError):
        make(conn, title="  ")
    with pytest.raises(ValueError):
        make(conn, state="done")


def test_dashboard_hides_closed(client, conn):
    make(conn, title="Open one")
    tid = make(conn, title="Finished one")
    with conn:
        db.change_state(conn, tid, "closed", resolution=DONE)
    page = client.get("/").get_data(as_text=True)
    assert "Open one" in page and "Finished one" not in page
    assert "Finished one" in client.get("/closed").get_data(as_text=True)


def test_http_flow(client, conn):
    r = client.post("/task/new", data={"title": "Via form", "priority": "High",
                                       "state": "new", "due_date": "2026-01-01"})
    assert r.status_code == 302
    tid = conn.execute("SELECT id FROM tasks WHERE title='Via form'").fetchone()[0]
    client.post(f"/task/{tid}/state", data={"state": "triage"})
    client.post(f"/task/{tid}/comment", data={"body": "hello"})
    page = client.get(f"/task/{tid}").get_data(as_text=True)
    assert "hello" in page and "triage" in page
    assert client.post("/task/new", data={"title": ""}).status_code == 400


def test_export_import_roundtrip(app, conn, tmp_path):
    a = make(conn, title="A", due_date="2026-12-01", priority="High")
    b = make(conn, title="B")
    with conn:
        db.add_comment(conn, a, "note")
        db.change_state(conn, b, "closed", resolution=DONE)
    data = backup.export_data(conn)

    other = create_app(tmp_path / "other")
    c2 = db.connect(other.config["DB_PATH"])
    with c2:
        assert backup.import_data(c2, json.loads(json.dumps(data)), "replace") == 2
    titles = {r["title"]: dict(r) for r in c2.execute("SELECT * FROM tasks")}
    assert titles["A"]["due_date"] == "2026-12-01" and titles["B"]["state"] == "closed"
    assert c2.execute("SELECT COUNT(*) FROM comments").fetchone()[0] == 1
    # original log rows + one 'imported' row per task
    assert c2.execute("SELECT COUNT(*) FROM log").fetchone()[0] == len(data["log"]) + 2
    c2.close()


def test_merge_remaps_ids(conn):
    existing = make(conn, title="Existing")
    src = make(conn, title="Source")
    with conn:
        db.add_comment(conn, src, "c1")
    data = backup.export_data(conn)
    data["tasks"] = [t for t in data["tasks"] if t["id"] == src]
    data["comments"] = [c for c in data["comments"] if c["task_id"] == src]
    data["log"] = [e for e in data["log"] if e["task_id"] == src]
    with conn:
        backup.import_data(conn, data, "merge")
    new_id = conn.execute("SELECT MAX(id) FROM tasks").fetchone()[0]
    assert new_id not in (existing, src)
    assert conn.execute("SELECT body FROM comments WHERE task_id=?", (new_id,)).fetchone()[0] == "c1"
    assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 3


def test_malformed_backup_rejected_without_writes(client, conn):
    make(conn, title="Keep me")
    bad = {"version": 1, "tasks": [{"id": 1, "title": "x", "state": "bogus", "priority": "Low"}],
           "comments": [], "log": []}
    r = client.post("/backup/import", data={
        "mode": "replace", "confirm": "yes",
        "file": (io.BytesIO(json.dumps(bad).encode()), "bad.json")},
        content_type="multipart/form-data", follow_redirects=True)
    assert "Import rejected" in r.get_data(as_text=True)
    assert [r["title"] for r in conn.execute("SELECT title FROM tasks")] == ["Keep me"]


def test_replace_requires_confirmation(client, conn):
    make(conn, title="Keep me")
    data = json.dumps(backup.export_data(conn)).encode()
    r = client.post("/backup/import", data={"mode": "replace",
                                            "file": (io.BytesIO(data), "b.json")},
                    content_type="multipart/form-data", follow_redirects=True)
    assert "confirmation" in r.get_data(as_text=True)
    assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 1


def test_export_endpoint(client, conn, app):
    make(conn, title="Exported")
    r = client.get("/backup/export")
    assert r.status_code == 200 and "attachment" in r.headers["Content-Disposition"]
    assert json.loads(r.data)["tasks"][0]["title"] == "Exported"
    assert list(Path(app.config["BACKUP_DIR"]).glob("mytodo-backup-*.json"))


def test_report_shows_open_tasks_with_last_comment(client, conn):
    a = make(conn, title="Alpha", due_date="2026-01-05")
    b = make(conn, title="Beta")
    c = make(conn, title="Gamma")
    with conn:
        db.add_comment(conn, a, "first note")
        db.add_comment(conn, a, "latest note")
        db.change_state(conn, c, "closed", resolution=DONE)
    page = client.get("/report").get_data(as_text=True)
    assert "Alpha" in page and "Beta" in page and "Gamma" not in page
    assert "latest note" in page and "first note" not in page
    assert "05 Jan 2026" in page and "No comments" in page

    csv_text = client.get("/report.csv").get_data(as_text=True)
    lines = csv_text.lstrip("﻿").strip().splitlines()
    assert len(lines) == 3  # header + 2 open tasks
    assert "latest note" in lines[1] and "Gamma" not in csv_text


def test_choose_port_skips_foreign_and_detects_mytodo(monkeypatch):
    import app as app_module
    busy = {5000: "other", 5001: "mytodo"}
    monkeypatch.setattr(app_module, "port_in_use", lambda p: p in busy)
    monkeypatch.setattr(app_module, "is_mytodo", lambda p, db_path: busy.get(p) == "mytodo")
    assert app_module.choose_port(5000, "x.db") == (5001, True)   # skips 5000, finds MyTodo
    busy[5001] = "other"
    assert app_module.choose_port(5000, "x.db") == (5002, False)  # both taken -> 5002


def test_identify_endpoint(client):
    assert client.get("/__mytodo").get_data(as_text=True).startswith("MyTodo")
