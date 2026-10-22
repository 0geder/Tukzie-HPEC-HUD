"""Judge the v0.7.6 soak log against the bench-gate pass criteria (TelemetryUnit/CHANGELOG.md)."""
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
e = [r["esp32"] for r in rows if r.get("esp32")]
n = len(rows); m = len(e)
dur = (rows[-1]["t"] - rows[0]["t"]) / 60 if n > 1 else 0
boots = sorted({x.get("up_ms", 0) // 1000 for x in e})
restarts = sum(1 for a, b in zip(e, e[1:]) if b.get("up_ms", 0) < a.get("up_ms", 0))
def worst(key, idx=None, fn=max):
    v = [x.get(key) for x in e if x.get(key) is not None]
    if idx is not None:
        v = [x[idx] for x in v if isinstance(x, list) and len(x) > idx]
    return fn(v) if v else None
drops_end = e[-1].get("drops") if e else None
checks = {
    "duration >= 60 min": dur >= 60,
    "no restart": restarts == 0,
    "drops stay [0,0]": all(x.get("drops") in ([0, 0], [0]) for x in e),
    "vib present in every record": all(x.get("vib") is not None for x in e),
    "imu1 199.5..200.5 Hz": all(199.5 <= (x.get("imu_hz") or [0])[0] <= 200.5 for x in e),
    "cons_age_ms < 200": all(max(x.get("cons_age_ms") or [0]) < 200 for x in e),
    "late stays 0": all(sum(x.get("late") or [0]) == 0 for x in e),
    "qmax < 50": all(max(x.get("qmax") or [0]) < 50 for x in e),
    "idle > 0 on both cores": all(min(x.get("idle") or [0]) > 0 for x in e),
    "rawdrop stays 0": all(sum(x.get("rawdrop") or [0]) == 0 for x in e),
    "rdfail imu1 stays 0": all((x.get("rdfail") or [0])[0] == 0 for x in e),
}
print(f"records {n} ({m} with esp32), {dur:.1f} min, restarts {restarts}")
print(f"end: drops {drops_end}, rdfail {e[-1].get('rdfail')}, late {e[-1].get('late')}, qmax {e[-1].get('qmax')}, "
      f"max cons_age {worst('cons_age_ms', None, lambda v: max(max(a) for a in v))}, "
      f"min idle {worst('idle', None, lambda v: min(min(a) for a in v))}, csq {e[-1].get('csq')}, soc {e[-1].get('soc')}")
print(f"bridge lines {rows[-1]['bridge']}")
for k, ok in checks.items():
    print(("PASS " if ok else "FAIL ") + k)
print("OVERALL", "PASS" if all(checks.values()) else "FAIL")
