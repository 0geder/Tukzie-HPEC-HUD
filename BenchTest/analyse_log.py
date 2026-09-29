import re, statistics as st, sys

path = sys.argv[1]
rows = []
for l in open(path, encoding="utf-8"):
    m = re.match(r"^\[\s*([\d.]+)s\]\s?(.*)$", l.rstrip("\n"))
    if m:
        rows.append((float(m.group(1)), m.group(2)))

print("lines:", len(rows), "| span: %.1f s" % rows[-1][0])
for t, s in rows:
    if re.search(r"Overall:|\[CAL\]|\[LOG\]|found and configured|Firmware v|Flash:", s):
        print("  %6.2fs  %s" % (t, s.strip()))

fused = []
for t, s in rows:
    m = re.search(r"\[FUSED\] src=(\S+).*?skew=(-?\d+)ms rms=([\d.]+) std=([\d.]+) p2p=([\d.]+) jerk=([\d.]+) dis=(\S+)", s)
    if m:
        fused.append((t, m.group(1), int(m.group(2)), float(m.group(3)), float(m.group(4)), float(m.group(5)), float(m.group(6)), float(m.group(7)) if m.group(7) != "nan" else float("nan")))
print("\nfused windows:", len(fused), "| sources:", sorted(set(f[1] for f in fused)), "| max skew ms:", max(f[2] for f in fused))

def summary(label, sel):
    if not sel:
        print(label, "none"); return
    stds = [f[4] for f in sel]; p2p = [f[5] for f in sel]; dis = [f[7] for f in sel if f[7] == f[7]]
    print("%-22s n=%3d  std median %.3f max %.3f | p2p median %.3f max %.3f | dis median %.2f" %
          (label, len(sel), st.median(stds), max(stds), st.median(p2p), max(p2p), st.median(dis) if dis else float("nan")))

summary("still (before 50 s)", [f for f in fused if f[0] < 48])
summary("shake (50 to 70 s)", [f for f in fused if 50 <= f[0] <= 72])
summary("still (after 75 s)", [f for f in fused if f[0] > 75])

big = max(fused, key=lambda f: f[4])
print("largest fused window: t=%.1fs std=%.3f p2p=%.3f jerk=%.2f dis=%.2f" % (big[0], big[4], big[5], big[6], big[7]))

rates, gaps, drops = [], [], []
for t, s in rows:
    m = re.search(r"^IMU(\d): (\d+) samples \(([\d.]+) Hz\)\s+dt_us\[min=(\d+) avg=(\d+) max=(\d+)\]\s+dropped=(\d+)", s)
    if m:
        rates.append(float(m.group(3))); gaps.append((t, int(m.group(1)), int(m.group(6)))); drops.append(int(m.group(7)))
print("\nacquisition windows:", len(rates), "| rate min/max %.1f/%.1f Hz | total dropped %d" % (min(rates), max(rates), sum(drops)))
print("max inter-sample gap overall: %d us" % max(g[2] for g in gaps))
print("windows with a gap > 10 ms:", [("%.0fs" % t, "IMU%d" % i, g) for t, i, g in gaps if g > 10000])
g = [s for t, s in rows if s.startswith("GNSS:")]
print("GNSS lines: first", g[0] if g else None, "| last", g[-1] if g else None)
