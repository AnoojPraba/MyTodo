#!/bin/sh
# Copyright (c) 2026 Anooj Prabaharan. All rights reserved.
# Run MyTodo from source on a Mac (or Linux). Needs Python 3.10+ (python.org).
# Usage: open Terminal, cd into this folder, then:  ./run.sh   (or: sh run.sh)
cd "$(dirname "$0")" || exit 1
if [ ! -x ".venv/bin/python" ]; then
    echo "First run: setting up MyTodo. This takes a minute..."
    python3 -m venv .venv && .venv/bin/python -m pip install -q -r requirements.txt || {
        echo "Setup failed. Make sure Python 3 is installed (https://www.python.org)."
        exit 1
    }
fi
# Start MyTodo in the background; use "Quit" in the app to stop it.
nohup .venv/bin/python app.py >/dev/null 2>&1 &
echo "MyTodo is starting and will open in your browser. Use Quit in the app to stop it."
