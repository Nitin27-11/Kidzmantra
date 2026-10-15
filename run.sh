#!/bin/sh
# Start the Kidzmantra site and AI backend.
cd "$(dirname "$0")"
[ -d .venv ] || { python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt; }
exec .venv/bin/python server.py
