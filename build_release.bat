@rem Copyright (c) 2026 Anooj Prabaharan. All rights reserved.
@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv || goto :error
)
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt -r requirements-dev.txt || goto :error
".venv\Scripts\python.exe" build_release.py || goto :error
pause
goto :eof
:error
echo Build failed.
pause
