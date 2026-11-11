# Copyright (c) 2026 Anooj Prabaharan. All rights reserved.
"""Build a MyTodo release:  release/MyTodo-v<version>/  +  release/MyTodo-v<version>.zip

    MyTodo.exe   standalone app (Python + Flask bundled; nothing to install)
    README.txt   how to run / back up / upgrade
    source/      the Python source code

Run with the project venv:  .venv\\Scripts\\python build_release.py
(build_release.bat does this for you, creating the venv if needed.)
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
RELEASE_ROOT = ROOT / "release"
SOURCE_ITEMS = ["app.py", "db.py", "backup.py", "review.py", "statuslog.py", "requirements.txt", "run.bat",
                "templates", "static", "tests", "tools", "icon.ico",
                "requirements-dev.txt", "build_release.py", "build_release.bat"]


def version():
    m = re.search(r'__version__\s*=\s*"([^"]+)"', (ROOT / "app.py").read_text(encoding="utf-8"))
    return m.group(1)


def run(*cmd):
    print(">", " ".join(str(c) for c in cmd))
    subprocess.run([str(c) for c in cmd], cwd=ROOT, check=True)


def main():
    ver = version()
    name = f"MyTodo-v{ver}"
    out = RELEASE_ROOT / name
    print(f"=== Building {name} ===")

    run(sys.executable, "-m", "pytest", "-q", "tests")

    shutil.rmtree(BUILD, ignore_errors=True)
    sep = ";" if sys.platform == "win32" else ":"
    run(sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed",
        "--name", "MyTodo", "--icon", ROOT / "icon.ico",
        "--add-data", f"{ROOT / 'templates'}{sep}templates",
        "--add-data", f"{ROOT / 'static'}{sep}static",
        "--distpath", BUILD / "dist", "--workpath", BUILD / "work", "--specpath", BUILD,
        ROOT / "app.py")

    shutil.rmtree(out, ignore_errors=True)
    (out / "source").mkdir(parents=True)
    shutil.copy2(BUILD / "dist" / "MyTodo.exe", out / "MyTodo.exe")
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")
    for item in SOURCE_ITEMS:
        src = ROOT / item
        if src.is_dir():
            shutil.copytree(src, out / "source" / item, ignore=ignore)
        else:
            shutil.copy2(src, out / "source" / item)
    (out / "README.txt").write_text(README.format(ver=ver), encoding="utf-8")

    zip_path = shutil.make_archive(str(out), "zip", RELEASE_ROOT, name)
    exe_mb = (out / "MyTodo.exe").stat().st_size / 1_048_576
    print(f"\nDone.\n  Folder: {out}\n  Zip:    {zip_path}\n  MyTodo.exe: {exe_mb:.1f} MB")


README = """\
MyTodo v{ver}
=============

RUN
  Double-click MyTodo.exe. It opens in your default browser (the one Windows
  is set to use) and runs quietly in the background - no extra window.
  Nothing needs to be installed: Python and all libraries are inside the exe.
  Closed the tab? Double-click MyTodo.exe again: it reopens at the right address.
  To stop MyTodo, click "Quit" at the top right of the app.
  Problems? Click "Status & log" at the bottom of any page: it shows the
  address, data folder and a log of any errors (with a Download log button).
  It normally uses http://127.0.0.1:5000; if another program has that port it
  picks the next free one (5001, 5002, ...) and always opens the right one.

YOUR DATA
  Stored in the "data" folder created next to MyTodo.exe:
    data\\mytodo.db        all tasks, comments and history
    data\\backups\\        JSON backups (auto- = made at each start, newest 10 kept)
    data\\mytodo.log       starts, stops and errors (useful for troubleshooting)
    data\\mytodo.port      port in use (only while MyTodo is running)
  Move MyTodo.exe together with its data folder if you relocate it.

UPGRADING TO A NEW VERSION
  Replace MyTodo.exe with the new one and keep the data folder where it is.
  (Taking a backup first from the Backup page is a good idea.)

FIRST START WARNINGS
  Windows SmartScreen may say "Windows protected your PC" because the exe is not
  code-signed: click "More info" -> "Run anyway".
  If Windows Firewall asks, you can click Cancel: MyTodo only listens on this
  computer (127.0.0.1) and needs no network access.

COPYRIGHT
  Copyright (c) 2026 Anooj Prabaharan. All rights reserved.

SOURCE CODE
  source\\ contains the Python code. To run from source instead of the exe
  (needs Python 3.10+ installed): double-click source\\run.bat
"""

if __name__ == "__main__":
    main()
