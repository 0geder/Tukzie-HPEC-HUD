"""Rear unit v0.7.6 soak of 22 Oct 2026 (13:48, about 62 min) against the
bench pass criteria of TelemetryUnit/CHANGELOG.md (v0.7.6 bench test, step 3).

Input: soak_v076b_20261022_134823.jsonl in this folder, a copy of
/home/ogeder/soak/soak_v076b_20261022_134823.jsonl on the Raspberry Pi 4: one
line about every 5 s with the bridge's latest DASH record ("esp32") and its
line counters. Output: soak_v076b_summary.txt in this folder.
Run: python Report/figures/results/soak_v076b_eval.py
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
rows = [json.loads(l) for l in (HERE / "soak_v076b_20261022_134823.jsonl").read_text().splitlines() if l.strip()]
e = [r["esp32"] for r in rows]
L = timezone(timedelta(hours=2))
out = []
say = lambda s: (print(s), out.append(s))
t0, t1 = rows[0]["t"], rows[-1]["t"]
say(f"rows {len(rows)}, {datetime.fromtimestamp(t0, L):%H:%M:%S} to {datetime.fromtimestamp(t1, L):%H:%M:%S}, "
    f"{(t1 - t0) / 60:.1f} min; fw {sorted({x['fw'] for x in e})}; node {sorted({x.get('node') for x in e})}")
up = [x["up_ms"] for x in e]
say(f"restarts (uptime falling) {sum(b < a for a, b in zip(up, up[1:]))}; uptime {up[0]/1000:.0f} to {up[-1]/1000:.0f} s")
hz = [x["imu_hz"][0] for x in e]
off = [(i, x["imu_hz"][0], x["up_ms"]) for i, x in enumerate(e) if not 199.5 <= x["imu_hz"][0] <= 200.5]
say(f"IMU1 rate {min(hz)} to {max(hz)} Hz; outside 199.5..200.5 in {len(off)} of {len(e)} rows: {off[:10]}")
say(f"drops always [0,0]: {all(x['drops'] == [0, 0] for x in e)}")
say(f"vib present in every row: {all(x['vib'] is not None for x in e)}; vib min {min(x['vib'] for x in e)}, "
    f"median {sorted(x['vib'] for x in e)[len(e)//2]}, max {max(x['vib'] for x in e)}")
for k in ("rdfail", "stuck", "rawdrop", "late", "qmax"):
    say(f"{k}: start {e[0][k]}, end {e[-1][k]}, max IMU1 {max(x[k][0] for x in e)}")
st = [(datetime.fromtimestamp(r['t'], L).strftime('%H:%M:%S'), r['esp32']['stuck'][0]) for r in rows]
ch = [(a, b) for (a, b), (_, c) in zip(st[1:], st[:-1]) if b != c]
say(f"stuck changes (time, new IMU1 count): {ch}")
ca = [max(v for v in x["cons_age_ms"] if v >= 0) for x in e]
say(f"consumer age max over the run {max(ca)} ms (per row max: median {sorted(ca)[len(ca)//2]})")
say(f"idle min core0 {min(x['idle'][0] for x in e)}, core1 {min(x['idle'][1] for x in e)}")
say(f"csq values {sorted({str(x['csq']) for x in e})}; soc {sorted({x['soc'] for x in e})}; v {min(x['v'] for x in e)} to {max(x['v'] for x in e)}")
age = [x["age_ms"] for x in e]
say(f"record age at the bridge max {max(age)} ms")
b0, b1 = rows[0]["bridge"], rows[-1]["bridge"]
say(f"bridge lines {b0['lines']} to {b1['lines']}, bad {b0['bad_lines']} to {b1['bad_lines']}")
seq = [x["seq"] for x in e]
say(f"DASH seq {seq[0]} to {seq[-1]} ({seq[-1] - seq[0] + 1} records over the run)")
(HERE / "soak_v076b_summary.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
