<p align="center">
  <img src="static/icon.png" alt="MyTodo logo" width="96">
</p>

<h1 align="center">MyTodo</h1>

<p align="center">
  A personal task tracker that runs on your own computer, <b>Windows or Mac</b>.<br>
  It keeps track of the work you are given and records a history of every change.<br>
  It also creates a <b>performance review report</b> you can share with your manager.
</p>

---

## Contents

1. [What MyTodo does](#1-what-mytodo-does)
2. [Choose how to use it](#2-choose-how-to-use-it)
3. [What you need (requirements)](#3-what-you-need-requirements)
4. [Option A: use the ready-made app (easiest)](#4-option-a-use-the-ready-made-app-easiest)
5. [Option B: run it from the code](#5-option-b-run-it-from-the-code)
6. [A quick tour](#6-a-quick-tour)
7. [Your data and backups](#7-your-data-and-backups)
8. [Upgrading to a new version](#8-upgrading-to-a-new-version)
9. [Troubleshooting](#9-troubleshooting)
10. [For developers (Option C: build the app yourself)](#10-for-developers-option-c-build-the-app-yourself)
11. [Privacy](#11-privacy)

---

## 1. What MyTodo does

- **Add tasks:** each task has a title, description, priority (Low / Medium / High) and due date.
- **Track progress through four states:**

  | State | Meaning |
  |---|---|
  | **New** | Just arrived, not looked at yet |
  | **Triage** | Being looked at or worked on |
  | **Depended** | Waiting on someone or something. You note what it is waiting for. |
  | **Closed** | Finished. A **closing summary is required**: a few lines on what was delivered and its impact. |

- **Dashboard:** shows only open work. You see counts per state and how many tasks are overdue. You can filter, search and sort, and change a task's state straight from the list.
- **History log:** every state change, edit and comment is recorded with a date and time. Entries cannot be edited or deleted.
- **Comments:** add notes to any task as the work goes on.
- **Labels:** tag tasks with coloured labels, such as a release (*Release 2026.1*), a team or a type (*Bug*). A task can have several. Filter the Dashboard, Closed list and Report by a label to see, for example, every open task in a release.
- **Report:** lists all open tasks with their due date and latest comment. You can print it, save it as a PDF, or download it for Excel.
- **Performance review:**
  - Pick a period, such as this year.
  - MyTodo lists what you **completed**, each with its closing summary, and what was **still in progress** at the end.
  - It adds summary numbers and your own written highlights.
  - Share it as a **PDF**, as an **HTML file** you can email, or as a **CSV** for Excel.
  - Save each review, so that next year's review starts where this one ended.
- **Backup and restore:** save everything to one file and load it back whenever you need to.
- **Runs quietly in the background:** no extra windows. It opens in your default browser and has a **Quit** button to stop it.
- **Status & log:** one page shows the version, address and data folder, plus a log of anything that went wrong, to make troubleshooting easy.
- **Private:** everything stays on your computer. There is no account, no cloud and no internet connection.

---

## 2. Choose how to use it

| Option | Who it is for | What you need to install |
|---|---|---|
| **A: Ready-made app** | Most people | **Nothing.** Download it and double-click. |
| **B: Run from the code** | People comfortable installing Python | Python |
| **C: Build the app yourself** | Developers | Python. The build tools install themselves. |

If you are not sure, choose **Option A**.

---

## 3. What you need (requirements)

### For every option
- A **Windows 10 or Windows 11** PC, **or** a **Mac** with macOS 12 (Monterey) or newer. The ready-made Mac app is built for Apple Silicon (M1 or newer); older Intel Macs can use Option B.
- A modern **web browser**, such as Microsoft Edge, Google Chrome, Safari or Firefox. MyTodo appears inside your browser, but it runs only on your own computer.

### Option A: nothing else
The app file already contains everything it needs.

### Options B and C: Python 3.10 or newer
*Python* is the programming language MyTodo is written in. To install it on **Windows**:

1. Go to <https://www.python.org/downloads/> and click the yellow **Download Python** button.
2. Run the installer. On the first screen, **tick the box "Add python.exe to PATH"**. This step is important: it lets Windows find Python.
3. Click **Install Now** and wait for it to finish.
4. Check that it worked. Open the **Command Prompt**: press the Windows key, type `cmd`, and press Enter. Then type:
   ```
   python --version
   ```
   You should see something like `Python 3.13.1`. If you see an error instead, read [Troubleshooting](#9-troubleshooting).

On a **Mac**: download the macOS installer from the same page and run it. Then open **Terminal** (press Command-Space, type `Terminal`, and press Enter) and type `python3 --version` to check it worked.

You also need an **internet connection the first time** you run MyTodo from the code. It downloads one small library called *Flask*. After that it works offline.

### Getting the code (Options B and C)
- **Without Git (easiest):** on the GitHub page for this project, click the green **Code** button, then **Download ZIP**, and unzip the file.
- **With Git:** if you already use Git, run:
  ```
  git clone <this repository's URL>
  ```

---

## 4. Option A: use the ready-made app (easiest)

On the GitHub page for this project, open **Releases** (in the right-hand column). Download the zip for your computer:
- **Windows:** `MyTodo-vX.Y.Z-windows.zip`
- **Mac:** `MyTodo-vX.Y.Z-mac.zip`

### On Windows
1. Unzip it to a permanent place, for example `Documents\MyTodo`. Don't run it from inside the zip file.
2. Double-click **`MyTodo.exe`**.
3. **The first time,** Windows may show a blue box saying **"Windows protected your PC"**. This happens because the app is not signed with a paid Microsoft certificate, not because anything is wrong. Click **More info**, then **Run anyway**.
4. MyTodo opens in your **default browser**. No other window appears; MyTodo runs quietly in the background.

> **Closed the browser tab?** MyTodo is still running. Double-click `MyTodo.exe` again and it reopens at the right address.
> **To stop MyTodo,** click **Quit** at the top right of the app. Your work is always saved.

### On a Mac
1. Double-click the zip to unzip it, then drag **`MyTodo.app`** into your **Applications** folder.
2. **The first time,** macOS may say MyTodo "cannot be opened" or is from an "unidentified developer". This happens because the app is not signed with a paid Apple certificate, not because anything is wrong.
   - **Right-click** (or Control-click) `MyTodo.app`, choose **Open**, then click **Open** again.
   - If there's no **Open** button: open **System Settings → Privacy & Security**, scroll down, click **Open Anyway** next to MyTodo, and open it again.
   - You only need to do this once.
3. MyTodo opens in your **default browser**. It runs quietly in the background, with no window and no Dock icon.

> **Closed the browser tab?** On a Mac, opening an app that's already running doesn't start it again, so opening MyTodo again won't reopen the tab. **Bookmark the address** (usually `http://127.0.0.1:5001`), or click **Quit** and open MyTodo again.
> **To stop MyTodo,** click **Quit** at the top right of the app. Your work is always saved.

---

## 5. Option B: run it from the code

1. Install Python and get the code, as described in [section 3](#3-what-you-need-requirements).
2. Start it:
   - **Windows:** open the MyTodo folder and double-click **`run.bat`**.
   - **Mac:** open **Terminal**, type `cd ` (with a space), drag the MyTodo folder into the Terminal window, press Enter, then type `sh run.sh` and press Enter.
   - The **first run takes a minute or two** while it sets things up. This is normal. Later runs start in a few seconds.
3. MyTodo opens in your browser and runs in the background, just like Option A. Use **Quit** in the app to stop it.

<details>
<summary><b>Prefer typing commands?</b> (click to expand)</summary>

Open Command Prompt (Windows) or Terminal (Mac) in the MyTodo folder, then run:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

On a Mac, use `python3 -m venv .venv` and `source .venv/bin/activate` for the first two lines.

The first command creates a *virtual environment*: a private folder (`.venv`) that holds MyTodo's libraries, so they don't mix with anything else on your computer.

Started this way, MyTodo runs **inside that Command Prompt window** and prints its messages there, which is handy while developing. Stop it with **Quit** in the app, or by pressing **Ctrl+C** in the window. Next time you only need the last command (after `.venv\Scripts\activate`).
</details>

---

## 6. A quick tour

The top bar has six pages plus **+ New task** and **Quit**. The **Status & log** link is at the bottom of every page.

| Page | What you do there |
|---|---|
| **Dashboard** | See all open tasks. Click a count card to filter. Change a task's state from its dropdown. Choosing **Closed** asks for the closing summary. |
| **+ New task** | Add a task: title, description, priority, due date, state and labels. |
| *(task page)* | Click any task title. Here you can add comments, change the state, edit the task, and see its full history. |
| **Closed** | Finished tasks, each with its closing summary. **Reopen** a task if it needs more work. |
| **Labels** | All your labels, with how many open and closed tasks each has. Click a count to see those tasks. Create, rename, recolour or delete labels. Deleting a label keeps its tasks. |
| **Report** | All open tasks with due dates and latest comments. Pick a label to get a status report for one release. Click **Print / Save as PDF** or **Download CSV**. |
| **Review** | Your performance review. See the steps below. |
| **Backup** | Download a backup, or restore from one. |
| **Quit** | Stops MyTodo. Your work is already saved. Open MyTodo again (`MyTodo.exe` or `MyTodo.app`) to start it again. |
| **Status & log** *(link at the bottom of every page)* | Version, address, data folder, last backup, and the log of what MyTodo has been doing, including any errors. Has **Open data folder** and **Download log** buttons. |

### See the open tasks in a release
1. When you add or edit a task, tick a label in **Labels**, or type a new one such as `Release 2026.1`.
2. Open **Labels** and click the release's **open** count. The Dashboard now shows only that release's open tasks, and its count cards count only those tasks.
3. For a shareable status report, click **report** next to the count, or choose the label on the **Report** page. Then print it, save it as a PDF, or download a CSV.

### Your yearly review in 5 steps
1. Open **Review**. The period is filled in for you: from the day after your last saved review (or 1 January) up to today.
2. Read through **Completed** and **In progress**. Untick **Include** on anything you don't want to share.
3. Write your highlights in **My summary**, then click **Save summary**.
4. Share the review with **Print / Save as PDF**, **Download for email (.html)** or **Download CSV**.
5. After your discussion, click **Save this review**. It is kept under *Past reviews*, and next year's review starts the day after this one ended.

> **Tip:** write good closing summaries as you close tasks. They become the "Outcome" lines in your review, so you won't have to remember a whole year's work at once.

---

## 7. Your data and backups

**Where your data is stored:**
- **Windows:** in a folder called **`data`**, next to `MyTodo.exe`.
- **Mac app:** in **`~/Library/Application Support/MyTodo`**, inside your user folder, not inside the app. To go there, click **Open data folder** on the Status & log page, or press Shift-Command-G in Finder and paste the path.
- **Running from the code (both):** in the `data` folder next to `app.py`.

| File | Contents |
|---|---|
| `mytodo.db` | All your tasks, comments, history and reviews |
| `mytodo.log` | A log of starts, stops and any errors. Useful when asking for help. |
| `mytodo.port` | Only exists while MyTodo is running: the port number it's using |
| `backups\` | Backup files. `auto-…` files are made each time MyTodo starts, and the newest 10 are kept. `pre-import-…` files are safety copies made just before you restore a backup. |

**To make a backup:** go to **Backup**, then click **Download backup**. Keep the file somewhere safe, such as OneDrive or a USB stick.

**To restore a backup:** go to **Backup**, choose the file, and pick one of these:
- **Merge:** adds the backup's tasks to the ones you already have.
- **Replace all:** clears what you have and loads the backup instead.

The file is checked before anything changes, and a safety copy of your current data is saved first.

**Moving to another computer:** make a backup on the old computer and restore it on the new one. This works between Windows and Mac in either direction. Between two Windows PCs, you can also copy `MyTodo.exe` **and** the `data` folder together.

> ⚠️ **Never upload the `data` folder (or backup files) to GitHub or anywhere public.** They contain your work tasks and review notes. This project's `.gitignore` file already stops Git from including them.

---

## 8. Upgrading to a new version

1. Optional but recommended: make a backup first (**Backup → Download backup**).
2. Stop MyTodo: click **Quit** at the top right of the app.
3. Replace the old app with the new one.
   - **Windows:** replace `MyTodo.exe`, and **leave the `data` folder where it is.**
   - **Mac:** replace `MyTodo.app` in Applications. Your data is kept separately, so nothing else needs to be done.
4. Start MyTodo. Your existing data is upgraded automatically, and backups from older versions still restore.

---

## 9. Troubleshooting

> **First stop for any problem: the Status & log page.** Click **Status & log** at the bottom of any page. It shows the address MyTodo is using and where your data is, and lists what happened, including errors. Choose **Warnings & errors only** to see just the problems. If you need help from someone, click **Download log** and send them the file. When something goes wrong, a red **⚠** number also appears next to that link.

**The browser didn't open.**
Open your data folder (see [section 7](#7-your-data-and-backups)). The file **`mytodo.port`** contains the number MyTodo is using, for example `5000`. Type `http://127.0.0.1:5000` into your browser, replacing `5000` with that number. The log file **`mytodo.log`** in the same folder also records the address and any problems.

**Which browser does MyTodo use?**
Your default browser. To change it, on **Windows** open **Settings → Apps → Default apps**; on a **Mac** open **System Settings → Desktop & Dock → Default web browser**. MyTodo follows your choice automatically, and nothing breaks if you uninstall a browser.

**MyTodo isn't on port 5000.**
Nothing is wrong. Another program on your computer was using that *port* (a numbered connection point), so MyTodo picked the next free one. On a Mac this is usual: macOS uses port 5000 for AirPlay, so MyTodo uses 5001. It always opens your browser on the port it is really using.

**Double-clicking MyTodo again only opens a browser tab.**
That's expected on Windows. MyTodo is already running, so it just opens the existing one for you.

**How do I know if MyTodo is running?**
On Windows, double-click `MyTodo.exe`: if it's running, your browser opens it; if not, it starts. You can also look for **MyTodo** in Task Manager. On a Mac, look for **MyTodo** in **Activity Monitor**, or try your bookmarked address.

**On a Mac, opening MyTodo again does nothing.**
MyTodo is already running, and macOS doesn't start an app twice. Open your bookmark (usually `http://127.0.0.1:5001`). If you don't have one, the port number is in `mytodo.port` in your data folder. Or quit MyTodo from **Activity Monitor** and open it again.

**macOS says MyTodo "cannot be opened" or is from an "unidentified developer".**
Right-click `MyTodo.app`, choose **Open**, then click **Open**. See [Option A, On a Mac](#on-a-mac).

**"Windows protected your PC" appears.**
Click **More info**, then **Run anyway**. See [Option A, On Windows](#on-windows).

**A Windows Firewall message appears.**
You can click **Cancel**. MyTodo only talks to your own computer (`127.0.0.1`) and needs no network access.

**I clicked Quit by mistake.**
Open MyTodo again (`MyTodo.exe`, `MyTodo.app`, `run.bat` or `run.sh`). Nothing is lost, because every change is saved immediately.

**MyTodo shows an error box and won't start.**
The message says what went wrong. Because the app isn't running, the Status & log page isn't available, so open `mytodo.log` in your data folder with Notepad (Windows) or TextEdit (Mac) for the details.

**A page says "Something went wrong".**
Your saved data is not affected. Click **Open Status & log** on that page to see the error details, or download the log to share it.

**"A closing summary is required to close a task".**
Write at least a sentence (10 characters or more) describing the outcome. It is used in your performance review.

**`'python' is not recognized as an internal or external command`** (Options B and C).
Python is either not installed or not on the *PATH*, the list of places Windows looks for programs. Run the Python installer again, choose **Modify**, and make sure **"Add Python to environment variables"** is ticked. Then close and reopen Command Prompt.

**`python3: command not found`** (Mac, Options B and C).
Python isn't installed. Install it from <https://www.python.org/downloads/>, then close and reopen Terminal.

**`run.bat` or `run.sh` says "Setup failed".**
Check that Python is installed (see above) and that you are connected to the internet the first time.

---

## 10. For developers (Option C: build the app yourself)

### Tech stack
Python 3.10+, Flask, SQLite (built into Python), and plain HTML, CSS and JavaScript with no build step. The Windows `MyTodo.exe` and the Mac `MyTodo.app` are made with PyInstaller, built automatically by GitHub Actions.

### Project layout

| Path | What it is |
|---|---|
| `app.py` | Flask app: all pages and routes, startup, port selection, `__version__` |
| `db.py` | Database tables (tasks, comments, log, reviews, labels), upgrades for older databases, task create/update and labels. Every change writes to the history log. |
| `backup.py` | JSON backup export and import (merge or replace), with validation |
| `review.py` | Performance review: period logic, sections, stats, saved reviews, CSV |
| `statuslog.py` | Reads the log file for the Status & log page |
| `templates/` | HTML pages (Jinja2 templates) |
| `static/` | CSS, JavaScript and logo files |
| `tests/` | Automated tests (pytest) |
| `tools/make_icon.py` | Regenerates all logo files from one design |
| `icon.ico` / `icon.icns` | App icons for Windows (`.exe`) and Mac (`.app`) |
| `run.bat` / `run.sh` | Sets up and runs from the code on Windows / Mac (Option B) |
| `build_release.py` | Runs the tests, builds `MyTodo.exe` (on Windows) or `MyTodo.app` (on a Mac), and packages a release zip |
| `build_release.bat` | Windows shortcut: sets up the build tools and runs `build_release.py` |
| `.github/workflows/release.yml` | GitHub Actions: builds and tests on Windows and Mac, and creates a draft release when a version tag is pushed |
| `requirements.txt` | Libraries needed to run the app (Flask) |
| `requirements-dev.txt` | Extra tools for testing and building (pytest, PyInstaller, Pillow) |

### Run the tests
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest
```

### Build a release (automatic, Windows and Mac)
PyInstaller can only build an app for the system it runs on, so GitHub builds both on its own Windows and Mac machines.
1. Update `__version__` in `app.py` (for example `"1.3.2"`) and `CHANGELOG.md`, then commit and push.
2. Create and push a tag with the same version:
   ```
   git tag v1.3.2
   git push origin v1.3.2
   ```
3. GitHub runs all the tests on both systems and builds `MyTodo-v1.3.2-windows.zip` and `MyTodo-v1.3.2-mac.zip`. Progress is shown on the **Actions** tab, and it takes about 5–10 minutes.
4. When it finishes, open **Releases**. A **draft** release has both zips attached. Write the description, then click **Publish release**.

To try a build without making a release, go to **Actions → Build release → Run workflow**. The zips appear under *Artifacts* on the run's page.

### Build on your own computer
Double-click **`build_release.bat`** (Windows), or run `python3 build_release.py` on a Mac after installing `requirements.txt` and `requirements-dev.txt`. It runs all the tests and builds the app for that computer. The result appears in `release/MyTodo-v<version>/`, along with a matching `.zip`:
- `MyTodo.exe` or `MyTodo.app`: the app
- `README.txt`: short instructions for users
- `source/`: a copy of the code

Don't commit the zips to the repository; they belong under **Releases**.

### Change the logo
Edit the colours or shape in `tools/make_icon.py`, then run:
```
python tools\make_icon.py
```
This rewrites `static/icon.svg`, `static/icon.png`, `static/favicon.ico`, `icon.ico` and `icon.icns`.

### Settings (environment variables)
| Variable | Default | Purpose |
|---|---|---|
| `MYTODO_PORT` | `5000` | First port to try. MyTodo tries up to 20 ports from here. |
| `MYTODO_DATA` | `data` next to the app (Mac app: `~/Library/Application Support/MyTodo`) | Where the database and backups are stored |
| `MYTODO_NO_BROWSER` | *(not set)* | Set it to `1` to stop MyTodo opening the browser at startup |

### Version history
See [CHANGELOG.md](CHANGELOG.md) for what changed in each version.

### What not to commit
`data/`, `.venv/`, `build/` and `release/` are listed in `.gitignore`. Keep it that way: `data/` holds personal work information, and the other three are recreated by the scripts.

---

## 11. Privacy

MyTodo has **no accounts, no cloud, no tracking and no internet connection**. It runs a small web server that only your own computer can reach (`127.0.0.1`), and stores everything in your data folder (see [section 7](#7-your-data-and-backups)). Your tasks leave your computer only if you share a backup or report yourself.

---

<sub>Copyright © 2026 Anooj Prabaharan. All rights reserved.</sub>
