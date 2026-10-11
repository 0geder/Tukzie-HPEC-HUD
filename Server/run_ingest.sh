#!/bin/sh
# Start the SW-7 ingest from its own folder with its own venv (no sudo, nothing
# installed system-wide). First time: python3 -m venv venv && venv/bin/pip install -r requirements.txt
# Broker settings: sw7_ingest.env in this folder (see sw7_ingest.env.example).
cd "$(dirname "$0")" || exit 1
exec ./venv/bin/python -u sw7_ingest.py --quiet "$@"
