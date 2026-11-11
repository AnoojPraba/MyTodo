# Copyright (c) 2026 Anooj Prabaharan. All rights reserved.
"""Windowless launcher: finding a running copy on the right port, Quit, logging."""
import logging
import socket
import sys
import threading
from pathlib import Path

import pytest
from werkzeug.serving import make_server

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app as app_module  # noqa: E402
from app import create_app  # noqa: E402


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def running(tmp_path):
    """A real MyTodo server on a random port, with its own data folder."""
    folder = tmp_path / "data"
    application = create_app(folder)
    port = free_port()
    server = make_server("127.0.0.1", port, application, threaded=True)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    yield {"folder": folder, "port": port, "db": application.config["DB_PATH"],
           "app": application, "server": server}
    server.shutdown()


def test_is_mytodo_checks_data_folder(running, tmp_path):
    assert app_module.is_mytodo(running["port"], running["db"])
    # same app, different data folder -> not "our" MyTodo
    assert not app_module.is_mytodo(running["port"], str(tmp_path / "other" / "mytodo.db"))
    assert not app_module.is_mytodo(free_port(), running["db"])  # nothing listening


def test_find_running_uses_port_file(running):
    folder, port, dbp = running["folder"], running["port"], running["db"]
    assert app_module.find_running(folder, dbp) is None  # no port file yet
    (folder / app_module.PORT_FILE).write_text(str(port))
    assert app_module.find_running(folder, dbp) == port  # opens the port it is really on
    (folder / app_module.PORT_FILE).write_text("not-a-number")
    assert app_module.find_running(folder, dbp) is None


def test_stale_port_file_is_ignored(tmp_path):
    folder = tmp_path / "data"
    folder.mkdir()
    (folder / app_module.PORT_FILE).write_text(str(free_port()))  # app crashed earlier
    assert app_module.find_running(folder, str(folder / "mytodo.db")) is None


def test_choose_port_skips_other_copy_of_mytodo(running, tmp_path):
    # a MyTodo with a *different* data folder is treated like any other program
    port, already = app_module.choose_port(running["port"], str(tmp_path / "x" / "mytodo.db"))
    assert port != running["port"] and already is False


def test_quit_button_only_when_running_as_app(tmp_path):
    application = create_app(tmp_path / "d")
    client = application.test_client()
    assert "Quit" not in client.get("/").get_data(as_text=True)
    r = client.post("/quit", follow_redirects=True)
    assert "only available" in r.get_data(as_text=True)

    called = []
    application.config["SHUTDOWN"] = lambda: called.append(True)
    assert 'action="/quit"' in client.get("/").get_data(as_text=True)
    r = client.post("/quit")
    assert r.status_code == 200 and "MyTodo has stopped" in r.get_data(as_text=True)
    assert called == [True]


def test_windowless_output_goes_to_log(tmp_path, monkeypatch):
    root = logging.getLogger()
    saved = (list(root.handlers), root.level, sys.stdout, sys.stderr)
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    try:
        app_module.setup_logging(tmp_path)
        print("hello from a windowless exe")
        sys.stderr.write("Traceback: boom\n")
        for h in root.handlers:
            h.flush()
        text = (tmp_path / app_module.LOG_FILE).read_text(encoding="utf-8")
        assert "hello from a windowless exe" in text and "Traceback: boom" in text
    finally:
        for h in root.handlers[:]:
            if h not in saved[0]:
                root.removeHandler(h)
                h.close()
        root.setLevel(saved[1])
