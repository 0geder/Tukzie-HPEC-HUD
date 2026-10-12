"""Cut the TUKZIE concept renders out of their white backgrounds for the dashboard's middle plane.

  python tools/cut_tukzie_renders.py [renders folder]   (default: the Projects folder above this repository)

For each render (new_tukzie_three_quarter_front.png, new_tukzie_front.png, new_tukzie_side.png):
  1. the background is the smooth, near-neutral region connected to the image border: pixels with low chroma and a
     small local gradient, grown from the border (scipy.ndimage.label). The vehicle's crisp silhouette edge stops it.
  2. the render's own soft ground shadow (inside that region, darker than the white) becomes a translucent shadow:
     alpha from its darkness, colour a warm near-black, so it reads on the paper and on the night ground.
  3. the vehicle's edge is pulled in by one pixel (no white fringe) and feathered (Gaussian, sigma 0.8 px).
  4. cropped to the visible pixels plus a margin and scaled to at most MAX_W px wide.
Output: DashboardIntegration/assets/tukzie_<view>.png (RGBA). Needs Pillow, numpy and scipy (development only; the
dashboard just loads the PNGs).
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
INTEG = os.path.dirname(HERE)
OUT = os.path.join(INTEG, "assets")
VIEWS = {"three_quarter": "new_tukzie_three_quarter_front.png", "front": "new_tukzie_front.png",
         "side": "new_tukzie_side.png"}
FLOOR_Y = {"three_quarter": 770, "front": 855, "side": 790}   # source px: below the sills and the body's underside
MAX_W = 900
SHADOW_RGB = (40, 32, 26)


def cut(path, floor_y=None):
    rgb = np.asarray(Image.open(path).convert("RGB")).astype(np.float32)
    L = rgb.mean(axis=2)
    chroma = rgb.max(axis=2) - rgb.min(axis=2)
    grad = np.hypot(ndimage.sobel(L, axis=0), ndimage.sobel(L, axis=1)) / 8.0
    smooth = (chroma < 10) & (grad < 3.0) & (L > 150)
    smooth = ndimage.binary_opening(smooth, iterations=1)
    labels, _n = ndimage.label(smooth)
    border = set(np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))) - {0}
    bg = np.isin(labels, list(border))
    bg = ndimage.binary_closing(bg, iterations=2) | bg
    # fill tiny holes the gradient test left inside the background (noise), not inside the vehicle
    holes = ndimage.binary_fill_holes(~bg) & bg
    vehicle = ~bg
    lab_v, n_v = ndimage.label(vehicle)
    if n_v > 1:                                             # keep the vehicle, drop specks
        sizes = ndimage.sum(vehicle, lab_v, range(1, n_v + 1))
        keep = np.isin(lab_v, [i + 1 for i, s in enumerate(sizes) if s > 400])
        vehicle = keep
    _ = holes
    # peel near-white pixels off the vehicle's boundary (the anti-aliased white fringe and the lightest shadow)
    whiteish = (L > 226) & (chroma < 12)
    for _i in range(10):
        edge = vehicle & ~ndimage.binary_erosion(vehicle)
        peel = edge & whiteish
        if not peel.any():
            break
        vehicle = vehicle & ~peel
    vehicle = ndimage.binary_opening(vehicle, iterations=2)
    lab_v, n_v = ndimage.label(vehicle)
    if n_v > 1:
        sizes = ndimage.sum(vehicle, lab_v, range(1, n_v + 1))
        vehicle = lab_v == (int(np.argmax(sizes)) + 1)
    # the floor between the wheels: light, neutral patches in the bottom quarter are ground (shadow), not vehicle
    ys = np.where(vehicle.any(axis=1))[0]
    low = np.zeros_like(vehicle)
    low[int(ys.min() + 0.72 * (ys.max() - ys.min())):, :] = True
    ground = vehicle & low & (L > 150) & (chroma < 14) & (grad < 6)
    lab_g, n_g = ndimage.label(ground)
    if n_g:
        sizes = ndimage.sum(ground, lab_g, range(1, n_g + 1))
        near_bg = ndimage.binary_dilation(~vehicle, iterations=3)       # touching the background (door panels do not)
        touch = set(np.unique(lab_g[near_bg & ground])) - {0}
        vehicle = vehicle & ~np.isin(lab_g, [i + 1 for i, s in enumerate(sizes) if s > 150 and (i + 1) in touch])
    # what is left of the floor under the body (the render's grey ground, below the sills): every neutral patch
    # under the view's floor line that reaches the outside is ground, not vehicle, so the cut-out sits cleanly on the
    # night charcoal. Tyres, trim and wheel rims are dark (or enclosed by the tyre) and stay; door panels sit above
    # the line. Repeated, since removing one patch can open the next to the outside.
    if floor_y:
        zone = np.zeros_like(vehicle)
        zone[int(floor_y):, :] = True
        band = np.zeros_like(vehicle)
        band[int(floor_y) - 70:, :] = True
        for _i in range(4):
            floor = vehicle & ((zone & (L > 50)) | (band & (L > 190))) & (chroma < 16)
            lab_f, n_f = ndimage.label(floor)
            if not n_f:
                break
            out_edge = ndimage.binary_dilation(~vehicle, iterations=2)
            touch = set(np.unique(lab_f[out_edge & floor])) - {0}
            if not touch:
                break
            vehicle = vehicle & ~np.isin(lab_f, list(touch))
        # any grey left under the floor line is the render's own ground shadow: it becomes the soft shadow layer
        vehicle = vehicle & ~(((zone & (L > 85)) | (band & (L > 243))) & (chroma < 16))
    vehicle = ndimage.binary_opening(vehicle, iterations=2)
    lab_v, n_v = ndimage.label(vehicle)
    if n_v > 1:
        sizes = ndimage.sum(vehicle, lab_v, range(1, n_v + 1))
        vehicle = lab_v == (int(np.argmax(sizes)) + 1)
    core = ndimage.binary_erosion(vehicle, iterations=1)
    v_alpha = ndimage.gaussian_filter(core.astype(np.float32), 0.8)
    v_alpha = np.clip(v_alpha * 1.15, 0, 1)
    # the render's own ground shadow, as a translucent shadow
    dark = np.clip((251.0 - L) / 130.0, 0, 1) ** 0.85
    s_alpha = np.where(vehicle, 0, dark * 0.62)
    s_alpha = ndimage.gaussian_filter(s_alpha, 3.0)                # a soft contact shadow, no hard patch edges
    alpha = np.maximum(v_alpha, s_alpha * (1 - v_alpha))
    out = np.zeros(rgb.shape[:2] + (4,), np.float32)
    w_v = np.where(alpha > 0, v_alpha / np.maximum(alpha, 1e-6), 0)[..., None]
    out[..., :3] = rgb * w_v + np.array(SHADOW_RGB, np.float32) * (1 - w_v)
    out[..., 3] = alpha * 255
    ys, xs = np.where(alpha > 0.02)
    m = 6
    y0, y1 = max(0, ys.min() - m), min(alpha.shape[0], ys.max() + m)
    x0, x1 = max(0, xs.min() - m), min(alpha.shape[1], xs.max() + m)
    img = Image.fromarray(np.clip(out[y0:y1, x0:x1], 0, 255).astype(np.uint8))
    if img.width > MAX_W:
        img = img.resize((MAX_W, round(img.height * MAX_W / img.width)), Image.LANCZOS)
    return img


def main(argv):
    src = argv[1] if len(argv) > 1 else os.path.join(INTEG, "..", "..")
    os.makedirs(OUT, exist_ok=True)
    for view, name in VIEWS.items():
        img = cut(os.path.join(src, name), FLOOR_Y.get(view))
        dst = os.path.join(OUT, f"tukzie_{view}.png")
        img.save(dst, optimize=True)
        print(f"{dst}: {img.width} x {img.height}")


if __name__ == "__main__":
    main(sys.argv)
