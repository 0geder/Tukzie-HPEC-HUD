"""SW-7 IMU pod, revision 3: screwless, thin-walled, after the student's fit test on 13 Oct.

Why: revision 2 was a solid 44 x 30 x 12 block held by M2.5 screws (none on hand), with no room for the GY-521's
right-angle header and the Dupont housings that stick out of its long edge. Revision 3 follows the Pi camera case
(Projects/Pi Camera Mount): 1.6 mm walls, a lid that pushes onto a half-lap rim, and the board clamped between
supports in the base and posts in the lid, with no screws.

Frame (mm): X across the board's long side, Y along the pod (board at -Y, connector bay and wire exit at +Y),
Z up from the bed. Writes base and lid STLs (in print orientation) and preview images next to this script.
Run: python imu_pod_rev3.py
"""
import os
import numpy as np
import trimesh
from manifold3d import Manifold, CrossSection, JoinType

HERE = os.path.dirname(os.path.abspath(__file__))
P = dict(
    BoardL=20.0, BoardW=17.0, BoardT=1.6,   # GY-521, measured 12 Oct (L along X, header on the +Y long edge)
    Clear=0.4,          # board to pocket wall, each side (0.6 in rev 2 was loose: student, 13 Oct)
    Bay=18.0,           # connector bay beyond the header edge: header body plus a 14 mm Dupont housing
    Wall=1.6, Floor=2.0, R=2.0,             # camera case walls are 1.6; the floor is the mounting face
    LedgeH=2.5,         # board raised on ledges so the header's solder tails clear the floor
    LedgeW=1.5,
    PegD=2.0, PegX=7.6, PegY=2.9,           # pegs into the board's 3 mm holes (hole spacing 15.2 not yet measured:
                                            # 1 mm play each way; snip the pegs off if they do not line up)
    WallTop=9.0, Lip=0.8, LipH=1.4,         # half-lap rim as on the camera case (outer half of the wall rises)
    LapGap=0.1,         # radial gap at the lap: the camera case is line to line; 0.1 makes a snug push fit
    LidT=1.2,
    HeaderTop=2.5,      # header body height above the board top (estimate); the lid's front fingers stop here
    NotchW=14.0, NotchZ=5.5,                # wire exit in the +Y end wall, open at the top, closed by the lid
    EarOut=7.0, EarW=10.0, EarT=2.4, SlotL=5.2, SlotW=2.2,   # cable-tie ears, two per side
)
SEG = 48


def rrect(w, h, r):
    return CrossSection.square([w - 2 * r, h - 2 * r], center=True).offset(r, JoinType.Round, circular_segments=SEG)


def prism(cs, z0, z1, dx=0.0, dy=0.0):
    return Manifold.extrude(cs, z1 - z0).translate([dx, dy, z0])


def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def cyl(d, z0, z1, x, y):
    return Manifold.cylinder(z1 - z0, d / 2, d / 2, SEG).translate([x, y, z0])


p = P
IX = p["BoardL"] + 2 * p["Clear"]                       # 20.8
IY = p["BoardW"] + 2 * p["Clear"] + p["Bay"]            # 35.8
OX, OY = IX + 2 * p["Wall"], IY + 2 * p["Wall"]         # 24.0 x 39.0
CY = IY / 2                                             # pod centre in Y (inner -Y wall at Y = 0)
outer = rrect(OX, OY, p["R"])
inner = rrect(IX, IY, max(p["R"] - p["Wall"], 0.3))
lip_in = rrect(OX - 2 * p["Lip"], OY - 2 * p["Lip"], p["R"] - p["Lip"])
TOP = p["WallTop"] + p["LipH"]                          # 10.4: lid underside
F = p["Floor"]
b_bot = F + p["LedgeH"]                                 # board underside 4.5
b_top = b_bot + p["BoardT"]                             # board top 6.1
by0, by1 = p["Clear"], p["Clear"] + p["BoardW"]         # board Y extent 0.4 .. 17.4

# ---------------- base ----------------
base = prism(outer, 0, p["WallTop"], 0, CY) - prism(inner, F, p["WallTop"] + 1, 0, CY)
base = base + (prism(outer, p["WallTop"], TOP, 0, CY) - prism(lip_in, p["WallTop"] - 1, TOP + 1, 0, CY))
lw = p["LedgeW"]
# wire exit notch in the +Y end wall
base = base - box(-p["NotchW"] / 2, p["NotchW"] / 2, IY - 1, IY + p["Wall"] + 1, p["NotchZ"], TOP + 1)
# cable-tie ears
for s in (-1, 1):
    for yc in (6.0, IY - 6.0):
        ex0, ex1 = (OX / 2 - 1, OX / 2 + p["EarOut"]) if s > 0 else (-OX / 2 - p["EarOut"], -OX / 2 + 1)
        ear = prism(rrect(ex1 - ex0, p["EarW"], 1.5), 0, p["EarT"], (ex0 + ex1) / 2, yc)
        sx = s * (OX / 2 + p["EarOut"] / 2)
        ear = ear - box(sx - p["SlotW"] / 2, sx + p["SlotW"] / 2, yc - p["SlotL"] / 2, yc + p["SlotL"] / 2, -1, 5)
        base = base + ear
# board supports: a ledge along the -Y wall, ledges along both sides stopping 3 mm short of the header edge
# (its solder tails), peg bosses, and pegs into the board's holes
base = base + box(-IX / 2, IX / 2, 0, by0 + lw, F, b_bot)
for s in (-1, 1):
    x0, x1 = (IX / 2 - lw, IX / 2) if s > 0 else (-IX / 2, -IX / 2 + lw)
    base = base + box(x0, x1, 0, by1 - 3.0, F, b_bot)
    base = base + cyl(p["PegD"] + 2.0, F, b_bot, s * p["PegX"], by0 + p["PegY"])
    base = base + cyl(p["PegD"], b_bot - 0.5, b_top + 0.5, s * p["PegX"], by0 + p["PegY"])

# ---------------- lid (modelled in place, assembled frame) ----------------
lid = prism(outer, TOP, TOP + p["LidT"], 0, CY)
g = p["LapGap"]
ring_o = rrect(OX - 2 * (p["Lip"] + g), OY - 2 * (p["Lip"] + g), p["R"] - p["Lip"] - g)
ring_i = rrect(OX - 2 * p["Wall"], OY - 2 * p["Wall"], max(p["R"] - p["Wall"], 0.3))
lid = lid + (prism(ring_o, p["WallTop"] + 0.2, TOP + 0.01, 0, CY) - prism(ring_i, p["WallTop"], TOP + 1, 0, CY))
for s in (-1, 1):
    # tubes over the pegs press the board's -Y corners onto the peg bosses
    x, y = s * p["PegX"], by0 + p["PegY"]
    lid = lid + (cyl(p["PegD"] + 2.4, b_top, TOP + 0.01, x, y) - cyl(p["PegD"] + 0.5, b_top - 1, TOP - 0.6, x, y))
    # fingers on the header body at the +Y corners stop the board's front edge lifting
    lid = lid + cyl(2.4, b_top + p["HeaderTop"], TOP + 0.01, s * (p["BoardL"] / 2 - 1.2), by1 - 1.2)
# forward arrow engraved 0.6 mm into the top, pointing -Y (away from the wire exit)
arrow = CrossSection([np.array([(-1.5, -2), (-4, -2), (0, -8), (4, -2), (1.5, -2), (1.5, 6), (-1.5, 6)], dtype=float)])
lid = lid - prism(arrow, TOP + p["LidT"] - 0.6, TOP + p["LidT"] + 1, 0, CY)


def to_tm(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=True)


base_tm, lid_tm = to_tm(base), to_tm(lid)
asm = trimesh.util.concatenate([base_tm, lid_tm])
# interference check, assembled: base and lid volumes must add up to their union
union_gap = base.volume() + lid.volume() - (base + lid).volume()
print("base %.1f x %.1f x %.1f mm, %.0f mm3, watertight %s" % (*base_tm.extents, base.volume(), base_tm.is_watertight))
print("lid  %.1f x %.1f x %.1f mm, %.0f mm3, watertight %s" % (*lid_tm.extents, lid.volume(), lid_tm.is_watertight))
print("base/lid overlap volume: %.3f mm3 (must be 0)" % union_gap)
print("internal height above board top: %.1f mm; board pocket %.1f x %.1f; bay %.1f" % (TOP - b_top, IX, p["BoardW"] + 2 * p["Clear"], p["Bay"]))

# print orientation: base as is (floor on the bed); lid flipped, top face on the bed
lid_print = lid_tm.copy()
lid_print.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
lid_print.apply_translation(-lid_print.bounds[0] * [0, 0, 1])
base_tm.export(os.path.join(HERE, "SW7_IMU_Pod_Base_rev3.stl"))
lid_print.export(os.path.join(HERE, "SW7_IMU_Pod_Lid_rev3.stl"))
asm.export(os.path.join(HERE, "SW7_IMU_Pod_rev3_assembled.stl"))

# previews: sections through the board and through the bay, and a top view of the base
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig, axs = plt.subplots(1, 3, figsize=(16, 5.5))
for ax, (nrm, org, ttl, ij) in zip(axs, [([1, 0, 0], [p["PegX"], 0, 0], "Section at the peg (X = 7.6), assembled", (1, 2)),
                                          ([0, 1, 0], [0, by0 + p["PegY"], 0], "Section across the pegs (Y = 3.3)", (0, 2)),
                                          ([0, 0, 1], [0, 0, b_bot - 0.2], "Base at Z = 4.3 (ledges, pegs, bay)", (0, 1))]):
    for mesh, col in ((base_tm, "k"), (lid_tm, "tab:orange")):
        sec = mesh.section(plane_origin=org, plane_normal=nrm)
        if sec is None:
            continue
        for e in sec.discrete:
            ax.plot(e[:, ij[0]], e[:, ij[1]], col + "-" if col == "k" else "-", color=col, lw=1)
    if nrm != [0, 0, 1]:
        bx = [by0, by1] if ij[0] == 1 else [-p["BoardL"] / 2, p["BoardL"] / 2]
        ax.fill_between(bx, b_bot, b_top, color="tab:blue", alpha=.5, label="board")
        ax.legend(loc="upper right")
    ax.set_title(ttl)
    ax.set_aspect("equal")
    ax.grid(alpha=.3)
plt.tight_layout()
plt.savefig(os.path.join(HERE, "rev3_sections.png"), dpi=80)
print("written to", HERE)
