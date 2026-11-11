# Changelog

All notable changes to MyTodo. The newest version is first.

## v1.3.3 (2026-11-11)

- The page footer is now one compact line in a smaller font, with the version, copyright, Status & log and feedback email.
- README screenshots updated to match.

## v1.3.2 (2026-11-11)

### Now available for Mac
- A ready-made **`MyTodo.app`** for Macs with Apple Silicon (M1 or newer), running macOS 12 or later. It works like the Windows version: it runs in the background with no window or Dock icon, opens in your default browser, and has a Quit button.
- On a Mac, your data is stored in `~/Library/Application Support/MyTodo`. **Open data folder** on the Status & log page shows it in Finder.
- If something stops MyTodo from starting, the Mac app shows an alert, just like the error box on Windows.
- `run.sh` runs MyTodo from the code on a Mac (or Linux), like `run.bat` on Windows.
- Moving between Windows and Mac: make a backup on one and restore it on the other.

### Releases
- GitHub now builds both the Windows and Mac apps automatically, and runs all tests on both systems, whenever a version tag is pushed. The zips are named `MyTodo-vX.Y.Z-windows.zip` and `MyTodo-vX.Y.Z-mac.zip`.
- The README and the in-app wording now cover both Windows and Mac.

## v1.3.1 (2026-11-11)

### Labels
- Tag tasks with **coloured labels**, such as a release, a team or a type. A task can have several.
- On the task form, tick existing labels or type new ones, separated by commas. Capitals don't matter, so `bug` and `Bug` are the same label.
- **Filter by label** on the Dashboard (the count cards follow the filter), the Closed list and the Report. The report CSV is filtered too and gets a Labels column, which makes a per-release status report.
- New **Labels** page: open and closed counts for each label, plus create, rename, recolour and delete. Deleting a label keeps its tasks.
- Label changes, including renames and deletes, appear in each task's history.
- Labels appear on performance review cards and in the review CSV.
- Backups include labels. A merge matches labels by name, so it never creates duplicates, and older backups still import.

### Other
- A footer link on every page invites ideas and improvements by email.
- A copyright notice is in every source file and in the app footer.

## v1.3.0 (2026-11-11)

### Runs in the background
- **No more black window.** `MyTodo.exe` now runs quietly in the background and opens in your **Windows default browser**. If you change or uninstall a browser, MyTodo simply follows the new default.
- **Quit button** at the top right stops MyTodo cleanly. It asks for confirmation first and then shows a "MyTodo has stopped" page.
- **Always opens the right address.** MyTodo remembers the port it is using (in `data\mytodo.port`). Double-clicking `MyTodo.exe` again reopens the copy that is already running, even if it is not on port 5000. It also never mistakes another copy of MyTodo, using a different `data` folder, for yours.
- `run.bat` also starts MyTodo in the background once setup is done.

### Troubleshooting
- New **Status & log** page, linked at the bottom of every page:
  - version, address, data folder, database size and last backup
  - the log, newest first, with a **Warnings & errors only** filter and expandable technical details
  - **Open data folder** and **Download log** buttons
- A red **⚠** badge next to the link shows warnings or errors since MyTodo started.
- A friendly **"Something went wrong"** page replaces bare server errors and links straight to the log.
- Everything is logged to `data\mytodo.log`: starts, stops, port changes, backup imports and errors. Older entries are kept in rotated files.
- If MyTodo cannot start at all, an error box says why.

## v1.2.0 (2026-11-09)
- **A closing summary is required** whenever a task is closed: from the dashboard dropdown (a box asks for it), the task page or the edit form. It appears as **Outcome** in the performance review and its CSV, on the task page, in the history log and on the Closed list.
- New **logo**, shown in the app, the browser tab and on `MyTodo.exe`.
- Existing databases and backups are upgraded automatically.

## v1.1.0 (2026-11-09)
- **Performance review** page:
  - pick a period, with quick buttons
  - **Completed** and **In progress** sections, summary numbers, and your own summary
  - leave out individual tasks
  - comment detail settings
  - share as **PDF**, an emailable **HTML** file, or **CSV**
- **Save this review**: keeps a copy under *Past reviews*, and the next review starts the day after it ended.
- Backups now include saved reviews and summaries. Older backups still import.

## v1.0.0 (2026-11-08)
- First release: tasks with priority and due date, and the states New / Triage / Depended / Closed.
- Dashboard of open tasks with counts, overdue tasks, filters, search, sorting and quick state changes.
- History log of every change, and comments.
- Closed tasks page, with reopening.
- Open-tasks report: print, PDF and CSV.
- JSON backup and restore (merge or replace), plus automatic backups at startup.
- Standalone Windows `MyTodo.exe`: nothing to install. If port 5000 is busy, it picks the next free port.

---

<sub>Copyright © 2026 Anooj Prabaharan. All rights reserved.</sub>
