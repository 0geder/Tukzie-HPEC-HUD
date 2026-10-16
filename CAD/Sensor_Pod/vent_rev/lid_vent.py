"""Rear pod (Pi 4 + ESP32) lid with an exhaust grille over the Pi 4, and a push-on rain hood (16 Oct 2026).

Why: the box had intake and exhaust slots only in the floor and low in the +X wall, nothing in the lid, and the
Pi 4 reached 73.5 C under the detector. Hot air now leaves through a grille in the lid over the Pi bay, under a
hood that is open towards the rear (pod -Y) so rain from above and the head wind stay out.

Works on the exported lid STL (no SolidWorks needed). Pod frame: X across, Y forward (box from Y -154.4 to -11.9),
Z up; the STL frame is X + 74.3, Y = Z_pod, Z = -Y_pod (SolidWorks model frame). Writes the new lid, the hood (both
in print orientation) and a section preview next to this script.
"""
import os
import numpy as np
import trimesh
from manifold3d import Manifold

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = r"C:\Users\0geda\Desktop\Fourth Year\EEE4022S\3D Prints\stl\SW7_Pod_Box_Lid.STL"
XOFF = 74.3
LID_TOP = 12.4          # pod Z of the lid's outer face (BOX_TOP_Z 10 + LID_T 2.4)
LID_T = 2.4
# Grille over the Pi 4 bay (Pi at X -40..45, Y -82..-26; fan at X 16, Y -58). Slots along X, 4 mm wide, 2.5 mm ribs.
G_X0, G_X1, G_Y0, G_Y1 = -30.0, 38.0, -74.0, -34.0
SLOT_W, RIB_W = 4.0, 2.5
# Hood: roof 10 mm over the lid on walls at the front (+Y) and both sides, open at the rear (-Y).
HOOD_GAP, HOOD_T, WALL_T, OVER = 10.0, 2.0, 2.0, 8.0
HX0, HX1, HY0, HY1 = G_X0 - OVER, G_X1 + OVER, G_Y0 - OVER, G_Y1 + OVER
REAR_LIP = 3.0          # drip lip down from the roof's open rear edge
PIN_D, HOLE_D, PIN_L = 3.0, 3.2, LID_T + 0.4     # push fit; a drop of glue if loose
PINS = [(HX0 + WALL_T / 2, HY1 - WALL_T / 2), (HX1 - WALL_T / 2, HY1 - WALL_T / 2),
        (HX0 + WALL_T / 2, HY0 + 6.0), (HX1 - WALL_T / 2, HY0 + 6.0)]


def to_pod(m):
    v = m.vertices
    return trimesh.Trimesh(np.c_[v[:, 0] - XOFF, -v[:, 2], v[:, 1]], m.faces, process=True)


def from_pod(m):
    v = m.vertices
    return trimesh.Trimesh(np.c_[v[:, 0] + XOFF, v[:, 2], -v[:, 1]], m.faces, process=True)


def man(t):
    return Manifold(mesh=__import__("manifold3d").Mesh(vert_properties=np.asarray(t.vertices, np.float32),
                                                       tri_verts=np.asarray(t.faces, np.uint32)))


def tm(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=True)


def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def cyl(d, z0, z1, x, y):
    return Manifold.cylinder(z1 - z0, d / 2, d / 2, 40).translate([x, y, z0])


lid_pod = to_pod(trimesh.load(SRC))
assert lid_pod.is_watertight, "source lid not watertight"
lid = man(lid_pod)
v0 = lid.volume()
cut = Manifold()
y = G_Y0
while y + SLOT_W <= G_Y1 + 1e-6:
    cut = cut + box(G_X0, G_X1, y, y + SLOT_W, LID_TOP - LID_T - 1, LID_TOP + 1)
    y += SLOT_W + RIB_W
for (x, yy) in PINS:
    cut = cut + cyl(HOLE_D, LID_TOP - LID_T - 1, LID_TOP + 1, x, yy)
lid = lid - cut

top = LID_TOP + HOOD_GAP
hood = box(HX0, HX1, HY0, HY1, top, top + HOOD_T)                                   # roof
hood = hood + box(HX0, HX1, HY1 - WALL_T, HY1, LID_TOP, top)                       # front wall
hood = hood + box(HX0, HX0 + WALL_T, HY0 + 4.0, HY1, LID_TOP, top)                 # side walls (stop short of rear)
hood = hood + box(HX1 - WALL_T, HX1, HY0 + 4.0, HY1, LID_TOP, top)
hood = hood + box(HX0, HX1, HY0, HY0 + 1.6, top - REAR_LIP, top)                   # rear drip lip
for (x, yy) in PINS:
    hood = hood + cyl(PIN_D, LID_TOP - PIN_L, LID_TOP + 0.01, x, yy)
    if yy < HY0 + 10:                                                              # rear pins get a post
        hood = hood + cyl(PIN_D + 3.0, LID_TOP, top, x, yy)

# checks
slots = int(round((G_Y1 - G_Y0 + RIB_W) / (SLOT_W + RIB_W)))
open_area = slots * SLOT_W * (G_X1 - G_X0)
outlet = (HX1 - HX0) * (HOOD_GAP - REAR_LIP) + 2 * 4.0 * HOOD_GAP
inter = (lid ^ hood).volume()
print("lid volume %.0f -> %.0f mm3; grille %d slots, %.0f mm2 open; hood outlet about %.0f mm2" %
      (v0, lid.volume(), slots, open_area, outlet))
print("hood %.0f x %.0f x %.1f mm, %.0f mm3; lid-hood overlap %.3f mm3 (pins in holes must be 0)" %
      (HX1 - HX0, HY1 - HY0, HOOD_GAP + HOOD_T, hood.volume(), inter))

lid_t = from_pod(tm(lid))
lid_t.export(os.path.join(HERE, "SW7_Pod_Box_Lid_vented.stl"))                    # same frame as the original STL
h = tm(hood)
h.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))       # roof on the bed
h.apply_translation(-h.bounds[0])
h.export(os.path.join(HERE, "SW7_Pod_Lid_Vent_Hood.stl"))
asm = trimesh.util.concatenate([tm(lid), tm(hood)])
asm.export(os.path.join(HERE, "lid_vent_assembled_podframe.stl"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig, axs = plt.subplots(1, 2, figsize=(15, 5))
A = tm(lid); B = tm(hood)
for ax, (org, nrm, ij, ttl) in zip(axs, [([0, -54, 0], [0, 1, 0], (0, 2), "Section Y = -54 (across)"),
                                         ([5, 0, 0], [1, 0, 0], (1, 2), "Section X = 5 (along; front is +Y)")]):
    for mesh, col in ((A, "k"), (B, "tab:orange")):
        s = mesh.section(plane_origin=org, plane_normal=nrm)
        if s is not None:
            for e in s.discrete:
                ax.plot(e[:, ij[0]], e[:, ij[1]], color=col, lw=1)
    ax.set_aspect("equal"); ax.grid(alpha=.3); ax.set_title(ttl)
    ax.set_xlim((-80, 80) if ij[0] == 0 else (-100, -10)); ax.set_ylim(4, 26)
plt.tight_layout(); plt.savefig(os.path.join(HERE, "lid_vent_sections.png"), dpi=80)
print("written to", HERE)
