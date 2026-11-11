"""Read MyTodo's log file for the in-app "Status & log" page."""
import re
from pathlib import Path

LOG_FILE = "mytodo.log"
# "2026-11-11 12:58:17,928 INFO mytodo: message"
_LINE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ (\w+) ([^:]+): ?(.*)$")
LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}


def log_files(folder):
    """Current log first, then rotated ones (mytodo.log.1, .2) - newest to oldest."""
    folder = Path(folder)
    files = [folder / LOG_FILE] + sorted(folder.glob(LOG_FILE + ".*"))
    return [f for f in files if f.is_file()]


def _parse(text):
    entries = []
    for raw in text.splitlines():
        m = _LINE.match(raw)
        if m:
            when, level, source, msg = m.groups()
            entries.append({"when": when, "level": level.upper(), "source": source.strip(),
                            "message": msg, "details": []})
        elif entries and raw.strip():
            entries[-1]["details"].append(raw)  # traceback / continuation line
        elif raw.strip():
            entries.append({"when": "", "level": "INFO", "source": "", "message": raw,
                            "details": []})
    return entries


def read_log(folder, problems_only=False, limit=500):
    """Newest-first log entries. problems_only keeps warnings and errors."""
    entries = []
    for f in reversed(log_files(folder)):  # oldest file first so order is chronological
        try:
            entries += _parse(f.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    if problems_only:
        entries = [e for e in entries if LEVELS.get(e["level"], 20) >= 30]
    entries.reverse()
    for e in entries:
        e["details"] = "\n".join(e["details"])
    return entries[:limit]


def full_log_text(folder):
    parts = []
    for f in reversed(log_files(folder)):
        try:
            parts.append(f.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            pass
    return "".join(parts)


def folder_size(path):
    try:
        return Path(path).stat().st_size
    except OSError:
        return 0


def human_size(n):
    for unit in ("bytes", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "bytes" else f"{n:.1f} {unit}"
        n /= 1024
