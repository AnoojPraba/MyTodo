"""In-app "Status & log" page, log parsing, footer badge and friendly error page."""
import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app as app_module  # noqa: E402
import statuslog  # noqa: E402
from app import create_app  # noqa: E402

SAMPLE = """\
2026-11-11 09:00:00,100 INFO mytodo: MyTodo 1.3.0 running at http://127.0.0.1:5000 (data: X)
2026-11-11 09:05:00,200 WARNING mytodo: Backup import rejected: Unsupported backup version: 9
2026-11-11 09:10:00,300 ERROR app: Exception on /review [GET]
Traceback (most recent call last):
  File "app.py", line 1, in review_page
ZeroDivisionError: division by zero
2026-11-11 09:15:00,400 INFO mytodo: MyTodo stopped.
"""


@pytest.fixture
def setup(tmp_path):
    folder = tmp_path / "data"
    application = create_app(folder)
    return application, application.test_client(), folder


def test_parse_newest_first_with_tracebacks(tmp_path):
    (tmp_path / "mytodo.log").write_text(SAMPLE, encoding="utf-8")
    entries = statuslog.read_log(tmp_path)
    assert [e["level"] for e in entries] == ["INFO", "ERROR", "WARNING", "INFO"]
    err = entries[1]
    assert err["message"] == "Exception on /review [GET]"
    assert "ZeroDivisionError" in err["details"] and "Traceback" in err["details"]
    problems = statuslog.read_log(tmp_path, problems_only=True)
    assert [e["level"] for e in problems] == ["ERROR", "WARNING"]


def test_rotated_logs_are_included_in_order(tmp_path):
    (tmp_path / "mytodo.log.1").write_text(
        "2026-11-10 08:00:00,000 INFO mytodo: older entry\n", encoding="utf-8")
    (tmp_path / "mytodo.log").write_text(
        "2026-11-11 08:00:00,000 INFO mytodo: newer entry\n", encoding="utf-8")
    msgs = [e["message"] for e in statuslog.read_log(tmp_path)]
    assert msgs == ["newer entry", "older entry"]
    text = statuslog.full_log_text(tmp_path)
    assert text.index("older entry") < text.index("newer entry")


def test_status_page_without_log(setup):
    _, client, folder = setup
    page = client.get("/status").get_data(as_text=True)
    assert "Status &amp; log" in page and str(folder) in page and "The log is empty" in page
    assert "None yet" in page  # no backup made yet


def test_status_page_shows_entries_and_filter(setup):
    _, client, folder = setup
    (folder / "mytodo.log").write_text(SAMPLE, encoding="utf-8")
    page = client.get("/status").get_data(as_text=True)
    assert "MyTodo stopped." in page and "ZeroDivisionError" in page
    assert "2 warnings or errors in the log" in page
    filtered = client.get("/status?show=problems").get_data(as_text=True)
    assert "Backup import rejected" in filtered and "MyTodo stopped." not in filtered


def test_log_download(setup):
    _, client, folder = setup
    (folder / "mytodo.log").write_text(SAMPLE, encoding="utf-8")
    r = client.get("/status/log.txt")
    assert "attachment" in r.headers["Content-Disposition"]
    body = r.get_data(as_text=True)
    assert body.startswith("MyTodo ") and "ZeroDivisionError" in body


def test_open_folder_outside_app_just_shows_path(setup):
    _, client, folder = setup
    r = client.post("/status/open-folder", follow_redirects=True)
    assert str(folder) in r.get_data(as_text=True)


def test_footer_link_and_problem_badge(setup, monkeypatch):
    _, client, _ = setup
    monkeypatch.setattr(app_module.PROBLEMS, "count", 0)  # other tests may have logged errors
    page = client.get("/").get_data(as_text=True)
    assert 'href="/status"' in page and app_module.__version__ in page
    assert "foot-alert" not in page
    monkeypatch.setattr(app_module.PROBLEMS, "count", 3)
    assert "⚠ 3" in client.get("/").get_data(as_text=True)


def test_problem_counter_counts_warnings_only():
    counter = app_module._ProblemCounter()
    lg = logging.getLogger("mytodo.test-counter")
    lg.addHandler(counter)
    lg.propagate = False
    try:
        lg.info("fine")
        lg.warning("hmm")
        lg.error("bad")
    finally:
        lg.removeHandler(counter)
    assert counter.count == 2


def test_friendly_error_page(setup):
    application, client, _ = setup

    @application.get("/boom")
    def boom():
        raise ZeroDivisionError("division by zero")

    r = client.get("/boom")
    body = r.get_data(as_text=True)
    assert r.status_code == 500
    assert "Something went wrong" in body and "/status?show=problems" in body
    assert "ZeroDivisionError" not in body  # technical details stay in the log
