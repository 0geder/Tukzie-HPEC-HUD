"""Export every front pod print part to STL (SolidWorks defaults: binary, mm, translated to positive space, as the
13 Oct prints) into the print folder, then report triangles, size and volume read back from each file.
Usage: python export_stl.py [out folder]   (default: Desktop/Fourth Year/EEE4022S/3D Prints/front_pod/stl)
"""
import os
import struct
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from swlib import sw, OPENED, PRINT

DST = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\0geda\Desktop\Fourth Year\EEE4022S\3D Prints\front_pod\stl"
os.makedirs(DST, exist_ok=True)


def stl_info(p):
    with open(p, "rb") as f:
        f.read(80)
        n = struct.unpack("<I", f.read(4))[0]
        tris = [struct.unpack("<12f", f.read(50)[:48]) for _ in range(n)]
    vol = 0.0
    for t in tris:
        a, b, c = t[3:6], t[6:9], t[9:12]
        vol += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
                + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6
    hi = [max(t[3 + 3 * i + k] for t in tris for i in range(3)) for k in range(3)]
    lo = [min(t[3 + 3 * i + k] for t in tris for i in range(3)) for k in range(3)]
    return n, [round(h - l, 2) for h, l in zip(hi, lo)], round(vol, 1)


if __name__ == "__main__":
    for f in sorted(os.listdir(PRINT)):
        if not f.endswith(".SLDPRT") or f.startswith("~$"):
            continue
        m = sw.OpenDoc(os.path.join(PRINT, f), 1)
        OPENED.append(m.GetTitle)
        out = os.path.join(DST, f[:-7] + ".STL")
        if os.path.exists(out):
            os.remove(out)          # only files this script wrote: the folder is new and holds front pod parts only
        err = m.SaveAs3(out, 0, 1 | 2)          # silent, copy
        sw.CloseDoc(m.GetTitle)
        print(f"{f[:-7]:28s} err {err}  triangles, size, volume: {stl_info(out)}")
