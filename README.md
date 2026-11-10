<p align="center">
  <img src="static/icon.png" alt="MyTodo logo" width="96">
</p>

<h1 align="center">MyTodo</h1>

<p align="center">
  A personal task tracker that runs on your own computer.<br>
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
- **Report:** lists all open tasks with their due date and latest comment. You can print it, save it as a PDF, or download it for Excel.
- **Performance review:**
  - Pick a period, such as this year.
  - MyTodo lists what you **completed**, each with its closing summary, and what was **still in progress** at the end.
  - It adds summary numbers and your own written highlights.
  - Share it as a **PDF**, as an **HTML file** you can email, or as a **CSV** for Excel.
  - Save each review, so that next year's review starts where this one ended.
- **Backup and restore:** save everything to one file and load it back whenever you need to.
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
- A **Windows 10 or Windows 11** computer.
- A modern **web browser**, such as Microsoft Edge, Google Chrome or Firefox. MyTodo appears inside your browser, but it runs only on your own computer.

### Option A: nothing else
The app file already contains everything it needs.

### Options B and C: Python 3.10 or newer
*Python* is the programming language MyTodo is written in. To install it:

1. Go to <https://www.python.org/downloads/> and click the yellow **Download Python** button.
2. Run the installer. On the first screen, **tick the box "Add python.exe to PATH"**. This step is important: it lets Windows find Python.
3. Click **Install Now** and wait for it to finish.
4. Check that it worked. Open the **Command Prompt**: press the Windows key, type `cmd`, and press Enter. Then type:
   ```
   python --version
   ```
   You should see something like `Python 3.13.1`. If you see an error instead, read [Troubleshooting](#9-troubleshooting).

You also need an **internet connection the first time** you run MyTodo from the code. It downloads one small library called *Flask*. After that it works offline.

### Getting the code (Options B and C)
- **Without Git (easiest):** on the GitHub page for this project, click the green **Code** button, then **Download ZIP**, and unzip the file.
- **With Git:** if you already use Git, run:
  ```
  git clone <this repository's URL>
  ```

---

## 4. Option A: use the ready-made app (easiest)

1. On the GitHub page for this project, open **Releases** (in the right-hand column). Download the latest `MyTodo-vX.Y.Z.zip`.
2. Unzip it to a permanent place, for example `Documents\MyTodo`. Don't run it from inside the zip file.
3. Double-click **`MyTodo.exe`**.
4. **The first time,** Windows may show a blue box saying **"Windows protected your PC"**. This happens because the app is not signed with a paid Microsoft certificate, not because anything is wrong. Click **More info**, then **Run anyway**.
5. A black window opens, and then MyTodo opens in your browser.

> **Keep the black window open while you use MyTodo.** Closing the window stops the app.
> To open MyTodo again later, double-click `MyTodo.exe` again.

---

## 5. Option B: run it from the code

1. Install Python and get the code, as described in [section 3](#3-what-you-need-requirements).
2. Open the MyTodo folder and double-click **`run.bat`**.
   - The **first run takes a minute or two** while it sets things up. This is normal.
   - Later runs start in a few seconds.
3. MyTodo opens in your browser. As with Option A, keep the black window open while you use it.

<details>
<summary><b>Prefer typing commands?</b> (click to expand)</summary>

Open Command Prompt in the MyTodo folder, then run:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

The first command creates a *virtual environment*: a private folder (`.venv`) that holds MyTodo's libraries, so they don't mix with anything else on your computer.
</details>

---

## 6. A quick tour

The top bar has six pages and a button for adding tasks:

| Page | What you do there |
|---|---|
| **Dashboard** | See all open tasks. Click a count card to filter. Change a task's state from its dropdown. Choosing **Closed** asks for the closing summary. |
| **+ New task** | Add a task: title, description, priority, due date and state. |
| *(task page)* | Click any task title. Here you can add comments, change the state, edit the task, and see its full history. |
| **Closed** | Finished tasks, each with its closing summary. **Reopen** a task if it needs more work. |
| **Report** | All open tasks with due dates and latest comments. Click **Print / Save as PDF** or **Download CSV**. |
| **Review** | Your performance review. See the steps below. |
| **Backup** | Download a backup, or restore from one. |

### Your yearly review in 5 steps
1. Open **Review**. The period is filled in for you: from the day after your last saved review (or 1 January) up to today.
2. Read through **Completed** and **In progress**. Untick **Include** on anything you don't want to share.
3. Write your highlights in **My summary**, then click **Save summary**.
4. Share the review with **Print / Save as PDF**, **Download for email (.html)** or **Download CSV**.
5. After your discussion, click **Save this review**. It is kept under *Past reviews*, and next year's review starts the day after this one ended.

> **Tip:** write good closing summaries as you close tasks. They become the "Outcome" lines in your review, so you won't have to remember a whole year's work at once.

---

## 7. Your data and backups

**Where your data is stored:** in a folder called **`data`**, next to `MyTodo.exe` (or next to `app.py` if you run from the code).

| File | Contents |
|---|---|
| `data\mytodo.db` | All your tasks, comments, history and reviews |
| `data\backups\` | Backup files. `auto-…` files are made each time MyTodo starts, and the newest 10 are kept. `pre-import-…` files are safety copies made just before you restore a backup. |

**To make a backup:** go to **Backup**, then click **Download backup**. Keep the file somewhere safe, such as OneDrive or a USB stick.

**To restore a backup:** go to **Backup**, choose the file, and pick one of these:
- **Merge:** adds the backup's tasks to the ones you already have.
- **Replace all:** clears what you have and loads the backup instead.

The file is checked before anything changes, and a safety copy of your current data is saved first.

**Moving to another computer:** copy `MyTodo.exe` **and** the `data` folder together. You can also make a backup on the old computer and restore it on the new one.

> ⚠️ **Never upload the `data` folder (or backup files) to GitHub or anywhere public.** They contain your work tasks and review notes. This project's `.gitignore` file already stops Git from including them.

---

## 8. Upgrading to a new version

1. Optional but recommended: make a backup first (**Backup → Download backup**).
2. Close MyTodo's black window.
3. Replace the old `MyTodo.exe` with the new one. **Leave the `data` folder where it is.**
4. Start MyTodo. Your existing data is upgraded automatically, and backups from older versions still restore.

---

## 9. Troubleshooting

**The browser didn't open.**
Look in the black window for a line such as `MyTodo 1.2.0 running at http://127.0.0.1:5000`. Copy that address into your browser.

**It says "Port 5000 is used by another program, trying 5001…"**
Nothing is wrong. Another program on your computer is using that *port* (a numbered connection point), so MyTodo picks the next free one. The black window shows which address it is using.

**Double-clicking MyTodo again only opens a browser tab.**
That's expected. MyTodo is already running, so it just opens the existing one for you.

**"Windows protected your PC" appears.**
Click **More info**, then **Run anyway**. See [Option A, step 4](#4-option-a-use-the-ready-made-app-easiest).

**A Windows Firewall message appears.**
You can click **Cancel**. MyTodo only talks to your own computer (`127.0.0.1`) and needs no network access.

**I closed the black window and MyTodo stopped working.**
That's how it works: the window *is* the app. Double-click `MyTodo.exe` (or `run.bat`) to start it again. Nothing is lost.

**"A closing summary is required to close a task".**
Write at least a sentence (10 characters or more) describing the outcome. It is used in your performance review.

**`'python' is not recognized as an internal or external command`** (Options B and C).
Python is either not installed or not on the *PATH*, the list of places Windows looks for programs. Run the Python installer again, choose **Modify**, and make sure **"Add Python to environment variables"** is ticked. Then close and reopen Command Prompt.

**`run.bat` says "Setup failed".**
Check that Python is installed (see above) and that you are connected to the internet the first time.

---

## 10. For developers (Option C: build the app yourself)

### Tech stack
Python 3.10+, Flask, SQLite (built into Python), and plain HTML, CSS and JavaScript with no build step. The single-file Windows `.exe` is made with PyInstaller.

### Project layout

| Path | What it is |
|---|---|
| `app.py` | Flask app: all pages and routes, startup, port selection, `__version__` |
| `db.py` | Database tables, upgrades for older databases, and task create/update. Every change writes to the history log. |
| `backup.py` | JSON backup export and import (merge or replace), with validation |
| `review.py` | Performance review: period logic, sections, stats, saved reviews, CSV |
| `templates/` | HTML pages (Jinja2 templates) |
| `static/` | CSS, JavaScript and logo files |
| `tests/` | Automated tests (pytest) |
| `tools/make_icon.py` | Regenerates all logo files from one design |
| `icon.ico` | Windows icon built into the `.exe` |
| `run.bat` | Sets up and runs from the code (Option B) |
| `build_release.bat` / `build_release.py` | Runs the tests, builds `MyTodo.exe`, and packages a release zip |
| `requirements.txt` | Libraries needed to run the app (Flask) |
| `requirements-dev.txt` | Extra tools for testing and building (pytest, PyInstaller, Pillow) |

### Run the tests
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest
```

### Build a release
1. Update `__version__` in `app.py`, for example `"1.3.0"`.
2. Double-click **`build_release.bat`**. It installs the build tools, runs all the tests, and builds the app.
3. The result appears in `release\MyTodo-v<version>\`, along with a matching `.zip`:
   - `MyTodo.exe`: the app
   - `README.txt`: short instructions for users
   - `source\`: a copy of the code
4. Publish the `.zip` on GitHub under **Releases**. Don't commit it to the repository.

### Change the logo
Edit the colours or shape in `tools/make_icon.py`, then run:
```
python tools\make_icon.py
```
This rewrites `static/icon.svg`, `static/icon.png`, `static/favicon.ico` and `icon.ico`.

### Settings (environment variables)
| Variable | Default | Purpose |
|---|---|---|
| `MYTODO_PORT` | `5000` | First port to try. MyTodo tries up to 20 ports from here. |
| `MYTODO_DATA` | `data` next to the app | Where the database and backups are stored |
| `MYTODO_NO_BROWSER` | *(not set)* | Set it to `1` to stop MyTodo opening the browser at startup |

### What not to commit
`data/`, `.venv/`, `build/` and `release/` are listed in `.gitignore`. Keep it that way: `data/` holds personal work information, and the other three are recreated by the scripts.

---

## 11. Privacy

MyTodo has **no accounts, no cloud, no tracking and no internet connection**. It runs a small web server that only your own computer can reach (`127.0.0.1`), and stores everything in the `data` folder next to the app. Your tasks leave your computer only if you share a backup or report yourself.
