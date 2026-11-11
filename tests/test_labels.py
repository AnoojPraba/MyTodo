# Copyright (c) 2026 Anooj Prabaharan. All rights reserved.
"""Labels: tagging tasks, filtering by label, the Labels page, backups and upgrades."""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import backup  # noqa: E402
import db  # noqa: E402
from app import FEEDBACK_EMAIL, create_app  # noqa: E402
from test_app import DONE, app, client, conn, events, make  # noqa: E402,F401


def names(conn, tid):
    return db.label_names(conn, tid)


def label_id(conn, name):
    return db.get_or_create_label(conn, name)["id"]


def test_parse_label_names():
    assert db.parse_label_names(" Release 2026.1 ,bug, BUG,,  ") == ["Release 2026.1", "bug"]
    assert db.parse_label_names(["A", "a, B", ""]) == ["A", "B"]
    assert db.parse_label_names("x" * 60) == ["x" * db.MAX_LABEL]


def test_create_with_labels_reuses_existing_case_insensitively(conn):
    a = make(conn, labels="Release 2026.1, Bug")
    b = make(conn, labels=["release 2026.1"])
    assert names(conn, a) == ["Bug", "Release 2026.1"]
    assert names(conn, b) == ["Release 2026.1"]  # same label, original spelling kept
    assert conn.execute("SELECT COUNT(*) FROM labels").fetchone()[0] == 2
    assert any(e["event_type"] == "labels" for e in events(conn, a))


def test_label_changes_are_logged_only_when_changed(conn):
    tid = make(conn, labels="A")
    task = dict(db.get_task(conn, tid))
    with conn:
        db.update_task(conn, tid, {**task, "labels": ["a"]})       # same set
        db.update_task(conn, tid, {**task, "labels": ["A", "B"]})  # changed
        db.update_task(conn, tid, {**task})                        # no labels key: untouched
    ev = [e for e in events(conn, tid) if e["event_type"] == "labels"]
    assert [(e["old_value"], e["new_value"]) for e in ev] == [(None, "A"), ("A", "A, B")]
    assert names(conn, tid) == ["A", "B"]
    with conn:
        db.change_state(conn, tid, "closed", resolution=DONE)
    assert names(conn, tid) == ["A", "B"]  # closing keeps labels


def test_form_create_and_edit_labels(client, conn):
    r = client.post("/task/new", data={"title": "Form", "priority": "Medium", "state": "new",
                                       "labels_field": "1", "new_labels": "Release 2026.1, Bug"})
    tid = int(r.headers["Location"].rstrip("/").split("/")[-1])
    assert names(conn, tid) == ["Bug", "Release 2026.1"]
    page = client.get(f"/task/{tid}/edit").get_data(as_text=True)
    assert 'value="Bug" checked' in page
    # untick Bug, keep the release, add Team A
    client.post(f"/task/{tid}/edit", data={"title": "Form", "priority": "Medium", "state": "new",
                                            "labels_field": "1", "labels": ["Release 2026.1"],
                                            "new_labels": "Team A"})
    assert names(conn, tid) == ["Release 2026.1", "Team A"]
    detail = client.get(f"/task/{tid}").get_data(as_text=True)
    assert "Team A" in detail and "Labels:" in detail  # pill + history entry
    # state change from the dashboard does not drop labels
    client.post(f"/task/{tid}/state", data={"state": "triage"})
    assert names(conn, tid) == ["Release 2026.1", "Team A"]


def test_dashboard_filter_and_counts(client, conn):
    r1 = make(conn, title="In release", labels="R1", due_date="2020-01-01")
    make(conn, title="Other release", labels="R2")
    make(conn, title="No label")
    lid = label_id(conn, "R1")
    page = client.get(f"/?label={lid}").get_data(as_text=True)
    assert "In release" in page and "Other release" not in page and "No label" not in page
    assert "Showing open tasks labelled" in page
    c = db.counts(conn, label=lid)
    assert c["new"] == 1 and c["overdue"] == 1
    assert db.counts(conn)["new"] == 3
    with conn:
        db.change_state(conn, r1, "closed", resolution=DONE)
    assert "In release" in client.get(f"/closed?label={lid}").get_data(as_text=True)
    assert "In release" not in client.get(f"/?label={lid}").get_data(as_text=True)


def test_report_and_csv_filtered_by_label(client, conn):
    make(conn, title="Alpha", labels="Release 2026.1, Bug")
    make(conn, title="Beta", labels="Release 2026.2")
    lid = label_id(conn, "Release 2026.1")
    page = client.get(f"/report?label={lid}").get_data(as_text=True)
    assert "Alpha" in page and "Beta" not in page and "Release 2026.1" in page
    r = client.get(f"/report.csv?label={lid}")
    text = r.get_data(as_text=True).lstrip("﻿")
    lines = text.strip().splitlines()
    assert "Labels" in lines[0] and len(lines) == 2
    assert "Bug, Release 2026.1" in lines[1]
    assert "Release-2026.1" in r.headers["Content-Disposition"]


def test_labels_page_counts_rename_recolor_delete(client, conn):
    a = make(conn, title="A", labels="Rel")
    b = make(conn, title="B", labels="Rel")
    with conn:
        db.change_state(conn, b, "closed", resolution=DONE)
    lid = label_id(conn, "Rel")
    row = next(r for r in db.list_labels(conn) if r["id"] == lid)
    assert (row["n_open"], row["n_closed"]) == (1, 1)
    assert "1 open" in client.get("/labels").get_data(as_text=True)

    client.post(f"/labels/{lid}/edit", data={"name": "Release 1", "color": db.LABEL_HEXES[3]})
    assert names(conn, a) == ["Release 1"]
    assert db.get_label(conn, lid)["color"] == db.LABEL_HEXES[3]
    assert any(e["event_type"] == "labels" and e["new_value"] == "Release 1" for e in events(conn, a))

    make(conn, title="C", labels="Other")
    r = client.post(f"/labels/{lid}/edit", data={"name": "other"}, follow_redirects=True)
    assert "already exists" in r.get_data(as_text=True)

    client.post(f"/labels/{lid}/delete")
    assert db.get_label(conn, lid) is None
    assert db.get_task(conn, a) is not None and names(conn, a) == []


def test_create_label_on_labels_page(client, conn):
    client.post("/labels", data={"name": "Release 2027.1", "color": ""})
    assert [r["name"] for r in db.list_labels(conn)] == ["Release 2027.1"]
    r = client.post("/labels", data={"name": "release 2027.1"}, follow_redirects=True)
    assert "already exists" in r.get_data(as_text=True)


def test_new_task_link_presets_label(client, conn):
    make(conn, labels="R9")
    lid = label_id(conn, "R9")
    page = client.get(f"/task/new?label={lid}").get_data(as_text=True)
    assert 'value="R9" checked' in page


def test_review_shows_labels(client, conn):
    tid = make(conn, title="Labelled work", labels="Release 2026.1")
    with conn:
        db.change_state(conn, tid, "closed", resolution=DONE)
    from datetime import date
    q = {"start": date.today().isoformat(), "end": date.today().isoformat()}
    assert "Release 2026.1" in client.get("/review", query_string=q).get_data(as_text=True)
    csv_text = client.get("/review.csv", query_string=q).get_data(as_text=True)
    assert "Labels" in csv_text.splitlines()[0] and "Release 2026.1" in csv_text


def test_backup_roundtrip_and_merge_by_name(conn, tmp_path):
    make(conn, title="T1", labels="Release 2026.1, Bug")
    data = json.loads(json.dumps(backup.export_data(conn)))
    other = create_app(tmp_path / "o")
    c2 = db.connect(other.config["DB_PATH"])
    with c2:
        make(c2, title="Existing", labels="bug")  # same label, different capitals
        backup.import_data(c2, data, "merge")
    assert c2.execute("SELECT COUNT(*) FROM labels").fetchone()[0] == 2  # no duplicate Bug
    t1 = c2.execute("SELECT id FROM tasks WHERE title='T1'").fetchone()[0]
    assert db.label_names(c2, t1) == ["bug", "Release 2026.1"]
    with c2:
        backup.import_data(c2, data, "replace")
    t1 = c2.execute("SELECT id FROM tasks WHERE title='T1'").fetchone()[0]
    assert db.label_names(c2, t1) == ["Bug", "Release 2026.1"]
    c2.close()


def test_old_backup_without_labels_imports(conn):
    make(conn, title="x")
    data = backup.export_data(conn)
    del data["labels"], data["task_labels"]
    with conn:
        assert backup.import_data(conn, data, "merge") == 1


def test_old_database_gets_label_tables(tmp_path):
    p = tmp_path / "old.db"
    old = sqlite3.connect(p)
    old.executescript(db.SCHEMA.split("CREATE TABLE IF NOT EXISTS labels")[0])
    old.close()
    db.init_db(str(p))
    c = db.connect(str(p))
    tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    c.close()
    assert {"labels", "task_labels"} <= tables


def test_footer_feedback_email(client):
    page = client.get("/").get_data(as_text=True)
    assert f"mailto:{FEEDBACK_EMAIL}?subject=" in page and FEEDBACK_EMAIL == "anooj.prabaharan@outlook.com"
