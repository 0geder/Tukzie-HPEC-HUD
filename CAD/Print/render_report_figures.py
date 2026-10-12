"""Render the CAD figures for the report (Report/figures/cad) from the current revision-2 models.

Uses the Sensor_Pod build helpers (snap hides planes and sketches). Each entry: file, picture name, named view, and
whether to show the sensor pod's view cones.
"""
import os
import sys
CAD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(CAD, "Sensor_Pod", "build"))
import swlib                                    # noqa: E402
from swlib import sw, OPENED                    # noqa: E402

OUT = os.path.join(os.path.dirname(CAD), "Report", "figures", "cad")
os.makedirs(OUT, exist_ok=True)
swlib.PREV = OUT
D, P, I = os.path.join(CAD, "Dashboard_Enclosure"), os.path.join(CAD, "Sensor_Pod"), os.path.join(CAD, "IMU_Pod")
JOBS = [
    (os.path.join(D, "SW7_Dash_Assembly.SLDASM"), "dash_assembly_iso.png", "*Isometric", None),
    (os.path.join(D, "SW7_Dash_Assembly.SLDASM"), "dash_assembly_back.png", "*Bottom", None),
    (os.path.join(D, "SW7_Dash_Assembly.SLDASM"), "dash_assembly_side.png", "*Right", None),
    (os.path.join(D, "SW7_Dash_Bracket.SLDPRT"), "dash_bracket.png", "*Isometric", None),
    (os.path.join(D, "SW7_Dash_Clamp_Cap.SLDPRT"), "dash_clamp_cap.png", "*Isometric", None),
    (os.path.join(D, "print_parts", "SW7_Dash_Rail_Plate.SLDPRT"), "dash_rail_plate.png", "*Isometric", None),
    (os.path.join(D, "print_parts", "SW7_Dash_Pi5_Cradle.SLDPRT"), "dash_pi5_cradle.png", "*Bottom", None),
    (os.path.join(D, "print_parts", "SW7_Dash_Shell_Q_Left_Bottom.SLDPRT"), "dash_shell_quarter.png", "*Isometric", None),
    (os.path.join(P, "SW7_Sensor_Pod_Assembly.SLDASM"), "pod_assembly_iso.png", "front_iso", False),
    (os.path.join(P, "SW7_Sensor_Pod_Assembly.SLDASM"), "pod_assembly_side.png", "*Right", False),
    (os.path.join(P, "SW7_Sensor_Pod_Assembly.SLDASM"), "pod_assembly_cones.png", "*Top", True),
    (os.path.join(P, "print_parts", "SW7_Pod_Head_Upper.SLDPRT"), "pod_head_upper.png", "front_iso", None),
    (os.path.join(P, "print_parts", "SW7_Pod_Head_Tray.SLDPRT"), "pod_head_tray.png", "front_iso", None),
    (os.path.join(P, "print_parts", "SW7_Pod_Box_Base.SLDPRT"), "pod_box_base.png", "*Isometric", None),
    (os.path.join(I, "SW7_IMU_Pod_Base.SLDPRT"), "imu_pod_base.png", "*Isometric", None),
    (os.path.join(I, "SW7_IMU_Pod_Lid.SLDPRT"), "imu_pod_lid.png", "*Isometric", None),
]
sw.CloseAllDocuments(True)
for path, png, view, cones in JOBS:
    asm = path.lower().endswith(".sldasm")
    m = sw.OpenDoc(path, 2 if asm else 1)
    if m is None:
        print("could not open", path)
        continue
    OPENED.append(m.GetTitle)
    if asm and cones is not None:
        for c in m.GetComponents(True):
            if c.Name2.startswith("REF_View_Cones"):
                c.Visible = 1 if cones else 0
    swlib.snap(m, png, view, 1600, 1100)
    sw.CloseDoc(m.GetTitle)                   # closed without saving: the cones stay hidden in the saved file
    print("rendered", png)
