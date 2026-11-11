# Copyright (c) 2026 Anooj Prabaharan. All rights reserved.
"""Build a MyTodo release for the computer this runs on.

Windows:  release/MyTodo-v<version>/  +  release/MyTodo-v<version>-windows.zip
    MyTodo.exe   standalone app (Python + Flask bundled; nothing to install)
Mac:      release/MyTodo-v<version>/  +  release/MyTodo-v<version>-mac.zip
    MyTodo.app   standalone app (Python + Flask bundled; nothing to install)
Both also contain README.txt and source/ (the Python source code).

PyInstaller can only build for the system it runs on, so the Mac app is built on a
Mac. GitHub Actions (.github/workflows/release.yml) builds both when a version tag
is pushed.

Run with the project venv:  .venv\\Scripts\\python build_release.py  (Windows)
                            .venv/bin/python build_release.py      (Mac)
(build_release.bat does this for you on Windows, creating the venv if needed.)
"""
import plistlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
RELEASE_ROOT = ROOT / "release"
SOURCE_ITEMS = ["app.py", "db.py", "backup.py", "review.py", "statuslog.py", "requirements.txt",
                "run.bat", "run.sh", "templates", "static", "tests", "tools", "icon.ico", "icon.icns",
                "requirements-dev.txt", "build_release.py", "build_release.bat"]
IS_MAC = sys.platform == "darwin"


def version():
    m = re.search(r'__version__\s*=\s*"([^"]+)"', (ROOT / "app.py").read_text(encoding="utf-8"))
    return m.group(1)


def run(*cmd):
    print(">", " ".join(str(c) for c in cmd))
    subprocess.run([str(c) for c in cmd], cwd=ROOT, check=True)


def pyinstaller(*extra):
    sep = ";" if sys.platform == "win32" else ":"
    run(sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed",
        "--name", "MyTodo", *extra,
        "--add-data", f"{ROOT / 'templates'}{sep}templates",
        "--add-data", f"{ROOT / 'static'}{sep}static",
        "--distpath", BUILD / "dist", "--workpath", BUILD / "work", "--specpath", BUILD,
        ROOT / "app.py")


def build_windows(out):
    pyinstaller("--onefile", "--icon", ROOT / "icon.ico")
    shutil.copy2(BUILD / "dist" / "MyTodo.exe", out / "MyTodo.exe")
    return out / "MyTodo.exe"


def build_mac(out, ver):
    # A one-file .app is deprecated in PyInstaller, so build the normal app bundle.
    pyinstaller("--onedir", "--icon", ROOT / "icon.icns",
                "--osx-bundle-identifier", "com.anoojpraba.mytodo")
    app = BUILD / "dist" / "MyTodo.app"
    plist_path = app / "Contents" / "Info.plist"
    with open(plist_path, "rb") as f:
        info = plistlib.load(f)
    info.update({
        "LSUIElement": True,  # run in the background: no Dock icon, like the windowless exe
        "CFBundleShortVersionString": ver,
        "CFBundleVersion": ver,
        "NSHumanReadableCopyright": "Copyright (c) 2026 Anooj Prabaharan. All rights reserved.",
    })
    with open(plist_path, "wb") as f:
        plistlib.dump(info, f)
    # editing Info.plist breaks the signature; Apple Silicon needs one (ad hoc is enough)
    run("codesign", "--force", "--deep", "--sign", "-", app)
    # ditto keeps the symlinks and signature inside the bundle
    run("ditto", app, out / "MyTodo.app")
    return out / "MyTodo.app"


def size_mb(path):
    files = [path] if path.is_file() else [f for f in path.rglob("*") if f.is_file()]
    return sum(f.stat().st_size for f in files) / 1_048_576


def main():
    ver = version()
    name = f"MyTodo-v{ver}"
    out = RELEASE_ROOT / name
    print(f"=== Building {name} for {'Mac' if IS_MAC else 'Windows'} ===")

    run(sys.executable, "-m", "pytest", "-q", "tests")

    shutil.rmtree(BUILD, ignore_errors=True)
    shutil.rmtree(out, ignore_errors=True)
    (out / "source").mkdir(parents=True)
    app_path = build_mac(out, ver) if IS_MAC else build_windows(out)

    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")
    for item in SOURCE_ITEMS:
        src = ROOT / item
        if src.is_dir():
            shutil.copytree(src, out / "source" / item, ignore=ignore)
        else:
            shutil.copy2(src, out / "source" / item)
    readme = (README_MAC if IS_MAC else README_WINDOWS).format(ver=ver)
    (out / "README.txt").write_text(readme, encoding="utf-8")

    zip_path = RELEASE_ROOT / f"{name}-{'mac' if IS_MAC else 'windows'}.zip"
    zip_path.unlink(missing_ok=True)
    if IS_MAC:
        run("ditto", "-c", "-k", "--keepParent", out, zip_path)
    else:
        shutil.make_archive(str(zip_path.with_suffix("")), "zip", RELEASE_ROOT, name)
    print(f"\nDone.\n  Folder: {out}\n  Zip:    {zip_path}\n"
          f"  {app_path.name}: {size_mb(app_path):.1f} MB")


README_WINDOWS = """\
MyTodo v{ver} for Windows
=========================

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
  Click Quit in MyTodo, replace MyTodo.exe with the new one and keep the data
  folder where it is. (Taking a backup first from the Backup page is a good idea.)

FIRST START WARNINGS
  Windows SmartScreen may say "Windows protected your PC" because the exe is not
  code-signed: click "More info" -> "Run anyway".
  If Windows Firewall asks, you can click Cancel: MyTodo only listens on this
  computer (127.0.0.1) and needs no network access.

MOVING TO A MAC
  Use Backup -> Download backup here, then Backup -> Import on the Mac.

COPYRIGHT
  Copyright (c) 2026 Anooj Prabaharan. All rights reserved.

SOURCE CODE
  source\\ contains the Python code. To run from source instead of the exe
  (needs Python 3.10+ installed): double-click source\\run.bat
"""

README_MAC = """\
MyTodo v{ver} for Mac
=====================

INSTALL
  Drag MyTodo.app into your Applications folder.
  Nothing else needs to be installed: Python and all libraries are inside the app.

FIRST START
  The app is not signed with a paid Apple certificate, so the first time macOS
  says it "cannot be opened" or is from an "unidentified developer":
    - Right-click (or Control-click) MyTodo.app, choose Open, then click Open.
    - If there is no Open button: open System Settings -> Privacy & Security,
      scroll down and click "Open Anyway" next to MyTodo, then open it again.
  You only need to do this once.

RUN
  Open MyTodo.app. It opens in your default browser and runs quietly in the
  background (no Dock icon, no window).
  To stop MyTodo, click "Quit" at the top right of the app.
  Closed the tab? While MyTodo is running, macOS does not start it a second time,
  so opening the app again won't reopen the tab. Bookmark the address instead
  (usually http://127.0.0.1:5001), or click Quit and open MyTodo.app again.
  Problems? Click "Status & log" at the bottom of any page: it shows the
  address, data folder and a log of any errors (with a Download log button).
  macOS uses port 5000 for AirPlay, so MyTodo normally picks 5001 (or the next
  free port) and always opens the right one.

YOUR DATA
  Stored in your user Library, not inside the app:
    ~/Library/Application Support/MyTodo/mytodo.db     all tasks, comments, history
    ~/Library/Application Support/MyTodo/backups/      JSON backups (newest 10 auto- kept)
    ~/Library/Application Support/MyTodo/mytodo.log    starts, stops and errors
  "Open data folder" on the Status & log page shows it in Finder.

UPGRADING TO A NEW VERSION
  Click Quit in MyTodo, then replace MyTodo.app in Applications with the new one.
  Your data stays where it is. (Taking a backup first from the Backup page is a
  good idea.)

MOVING FROM WINDOWS
  On Windows, use Backup -> Download backup. On the Mac, use Backup -> Import
  and choose that file.

COPYRIGHT
  Copyright (c) 2026 Anooj Prabaharan. All rights reserved.

SOURCE CODE
  source/ contains the Python code. To run from source instead of the app
  (needs Python 3.10+ from python.org): in Terminal, cd into source and run
  ./run.sh
"""

if __name__ == "__main__":
    main()
