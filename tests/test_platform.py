# Copyright (c) 2026 Anooj Prabaharan. All rights reserved.
"""Windows / Mac differences: data folder location and opening a folder."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app as app_module  # noqa: E402


def test_data_dir_from_source_is_next_to_program(monkeypatch):
    monkeypatch.delenv("MYTODO_DATA", raising=False)
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert app_module.default_data_dir() == app_module.BASE_DIR / "data"


def test_data_dir_windows_exe_is_next_to_exe(monkeypatch):
    monkeypatch.delenv("MYTODO_DATA", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    assert app_module.default_data_dir() == app_module.BASE_DIR / "data"


def test_data_dir_mac_app_is_application_support(monkeypatch):
    monkeypatch.delenv("MYTODO_DATA", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "darwin")
    expected = Path.home() / "Library" / "Application Support" / "MyTodo"
    assert app_module.default_data_dir() == expected
    assert app_module.data_dir() == expected


def test_data_dir_env_override_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("MYTODO_DATA", str(tmp_path))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "darwin")
    assert app_module.default_data_dir() == tmp_path


def test_open_folder_uses_the_platform_tool(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(app_module.subprocess, "Popen", lambda cmd: calls.append(cmd))
    monkeypatch.setattr(app_module.os, "startfile", lambda p: calls.append(["startfile", p]),
                        raising=False)
    for platform in ("win32", "darwin", "linux"):
        monkeypatch.setattr(sys, "platform", platform)
        app_module.open_folder(tmp_path)
    assert [c[0] for c in calls] == ["startfile", "open", "xdg-open"]
    assert all(c[1] == str(tmp_path) for c in calls)


def test_status_open_folder_falls_back_to_showing_path(monkeypatch, tmp_path):
    application = app_module.create_app(tmp_path)
    application.config["SHUTDOWN"] = lambda: None  # pretend to be the desktop app

    def fail(path):
        raise OSError("no file manager")
    monkeypatch.setattr(app_module, "open_folder", fail)
    r = application.test_client().post("/status/open-folder", follow_redirects=True)
    assert str(tmp_path) in r.get_data(as_text=True)
