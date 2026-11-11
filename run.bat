@rem Copyright (c) 2026 Anooj Prabaharan. All rights reserved.
@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo First run: setting up MyTodo. This takes a minute...
    python -m venv .venv || goto :error
    ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt || goto :error
)
rem Start MyTodo in the background (no console window); use "Quit" in the app to stop it.
start "" ".venv\Scripts\pythonw.exe" app.py
goto :eof
:error
echo Setup failed. Make sure Python 3 is installed and on PATH.
pause
