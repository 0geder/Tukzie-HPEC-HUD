"""Build and run the host-side ledger test with g++ (no ESP32 needed).

Usage, from anywhere: python TelemetryUnit/test_host/run.py
Needs g++ on PATH (on this laptop: MSYS2 UCRT64, C:/msys64/ucrt64/bin)."""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
UNIT = os.path.dirname(HERE)
exe = os.path.join(tempfile.gettempdir(), "sw7_test_sync_ledger" + (".exe" if os.name == "nt" else ""))
subprocess.check_call(["g++", "-std=c++11", "-O1", "-Wall", "-Wextra", "-I", os.path.join(UNIT, "include"),
                       os.path.join(HERE, "test_sync_ledger.cpp"), "-o", exe])
sys.exit(subprocess.call([exe]))
