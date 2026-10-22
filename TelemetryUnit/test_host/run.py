"""Build and run the host-side firmware tests with g++ (no ESP32 needed):
test_sync_ledger.cpp (store-and-forward ledger) and test_raw_stream.cpp
(raw IMU stream encoder, decoder, drop and read-health counters, MQTT
position scrub; v0.7.5) and test_imu_pacing.cpp (IMU task pacing and
consumer-health helpers; v0.7.6). The raw stream test writes a simulated capture,
which the Python reference decoder tools/raw_stream_decode.py must then
decode to the same samples.

Usage, from anywhere: python TelemetryUnit/test_host/run.py
Needs g++ on PATH (on this laptop: MSYS2 UCRT64, C:/msys64/ucrt64/bin, added
automatically when g++ is not found)."""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
UNIT = os.path.dirname(HERE)
TESTS = ("test_sync_ledger", "test_raw_stream", "test_imu_pacing")

env = dict(os.environ)
if shutil.which("g++") is None and os.path.isdir("C:/msys64/ucrt64/bin"):
    env["PATH"] = "C:/msys64/ucrt64/bin" + os.pathsep + env.get("PATH", "")

tmp = tempfile.gettempdir()
capture = os.path.join(tmp, "sw7_raw_capture.txt")
expected = os.path.join(tmp, "sw7_raw_expected.csv")

worst = 0
for name in TESTS:
    exe = os.path.join(tmp, "sw7_" + name + (".exe" if os.name == "nt" else ""))
    subprocess.check_call(["g++", "-std=c++11", "-O1", "-Wall", "-Wextra", "-I", os.path.join(UNIT, "include"),
                           os.path.join(HERE, name + ".cpp"), "-o", exe], env=env)
    print("== %s" % name, flush=True)
    args = [exe] + ([capture, expected] if name == "test_raw_stream" else [])
    rc = subprocess.call(args, env=env)
    print("== %s: %s" % (name, "PASS" if rc == 0 else "FAIL (exit %d)" % rc), flush=True)
    worst = worst or rc

print("== raw_stream_decode.py selftest", flush=True)
rc = subprocess.call([sys.executable, os.path.join(UNIT, "tools", "raw_stream_decode.py"), "--selftest",
                      capture, expected])
print("== raw_stream_decode.py: %s" % ("PASS" if rc == 0 else "FAIL (exit %d)" % rc), flush=True)
worst = worst or rc
sys.exit(worst)
