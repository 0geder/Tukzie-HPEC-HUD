import subprocess, os
PS = r"C:\Users\0geda\Downloads\PrusaSlicer-2.9.4\PrusaSlicer-2.9.4\prusa-slicer-console.exe"
A = os.path.join(os.environ["APPDATA"], "PrusaSlicer")
src = os.path.join(A, "print", "0.20mm QUALITY @MINI - Copy.ini")
lines = [l for l in open(src, encoding="utf-8").read().splitlines() if " = " in l and not l.startswith("#")]
stl = os.path.abspath("oriented/SW7_IMU_Pod_Base.stl")
def ok(sub):
    p = os.path.abspath("config/_probe.ini")
    open(p, "w", encoding="utf-8").write("\n".join(sub) + "\n")
    r = subprocess.run([PS, "--export-gcode", "--load", os.path.join(A, "printer", "Original Prusa MINI & MINI+ - Copy.ini"),
                        "--load", p, "-o", os.path.abspath("gcode/_probe.gcode"), stl], capture_output=True, text=True)
    return r.returncode == 0
bad = []
for i in range(0, len(lines), 12):
    chunk = lines[i:i + 12]
    if not ok(chunk):
        bad += [l for l in chunk if not ok([l])]
print("bad lines:", bad)
good = [l for l in lines if l not in bad]
print("cleaned file works:", ok(good))
open(os.path.abspath("config/0.20mm QUALITY @MINI (cli).ini"), "w", encoding="utf-8").write("\n".join(good) + "\n")
os.remove(os.path.abspath("config/_probe.ini"))
