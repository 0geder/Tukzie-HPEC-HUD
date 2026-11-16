// EEE4022S A1 portrait poster (true A1, 594 x 841 mm).
// v5, 16 Nov 2026 (Planning/poster-v5-prompt.md): laid out after the EcoBot E-poster so that each idea is a picture:
// background as circle photos, scope as labelled arrows, the system as a block diagram in four subsystem colours,
// the plan as a Gantt chart, the requirements as a scorecard, limits paired with next steps, references at the foot.
// Every number is from the final report (Introduction.tex requirement table, Results.tex Table 5.3, Recommendations.tex)
// or run2_summary_numbers.txt; the Gantt dates are the tuksense.site stage dates. v4 is in ../backup_2026-11-16.
const pptxgen = require("pptxgenjs");
const path = require("path");
const A = (f) => path.join(__dirname, "assets", f);
const R = (f) => path.join(__dirname, "..", "..", "Report", "figures", f);

const C = {
  navy: "14305C", panel: "E8F0FA", accent: "B45309", green: "1B7F3B", amber: "B7791F", grey: "6B7280",
  text: "1B1F24", muted: "3F4A5A", white: "FFFFFF", line: "B9C7DA",
};
// the four subsystems: one colour each, used in the diagram, the photo tags, the result tiles and the scorecard
const SYS = {
  sense: { name: "Ride sensing", c: "1565C0", t: "DCE8F8" },
  hazard: { name: "Hazard detection", c: "C2410C", t: "FBE3D6" },
  telem: { name: "Telemetry", c: "0E7490", t: "D3EEF3" },
  display: { name: "Driver display", c: "6D28D9", t: "EAE2FB" },
};
const FONT = "Calibri";
const NB = " ";   // keeps a number and its unit on one line

const W = 594 / 25.4, H = 841 / 25.4;   // A1 portrait, inches (23.39 x 33.11)
const M = 0.7, GAP = 0.45;
const COLW = (W - 2 * M - GAP) / 2;
const XL = M, XR = M + COLW + GAP;
const T = { head: 44, body: 26, small: 24 };   // nothing under 24 pt (2 m rule)

const pres = new pptxgen();
pres.defineLayout({ name: "A1P", width: W, height: H });
pres.layout = "A1P";
pres.title = "Embedded Telemetry with Road-Surface Characterisation and Camera-Based Hazard Detection for the TUKZIE Electric Trike";
pres.author = "Samson Okuthe";
const s = pres.addSlide();
s.background = { color: C.white };
// TUKZIE render as a faint backdrop behind the panels; panels are slightly see-through
const BG_W = W * 1.05, BG_H = BG_W * 1086 / 1448;
const BG_ALPHA = Number(process.env.POSTER_BG_ALPHA || 60);
const PANEL_ALPHA = Number(process.env.POSTER_PANEL_ALPHA || 30);
s.addImage({ path: A("tukzie_three_quarter_front.png"), x: (W - BG_W) / 2, y: 18.5 - BG_H / 2, w: BG_W, h: BG_H,
  transparency: BG_ALPHA, altText: "TUKZIE electric trike (render)" });

// ---------------- header ----------------
const BANNER_H = 4.3;
s.addImage({ path: A("uct_banner.jpg"), x: 0, y: 0, w: W, h: BANNER_H, sizing: { type: "cover", w: W, h: BANNER_H } });
s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: W, h: BANNER_H, fill: { color: "0B1F3F", transparency: 35 }, line: { type: "none" } });
const CREST = 3.1, TX = M + CREST + 0.5;
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: 0.6, w: CREST, h: CREST, rectRadius: 0.25, fill: { color: C.white }, line: { color: C.white } });
s.addImage({ path: A("uct_logo.png"), x: M + 0.15, y: 0.75, w: CREST - 0.3, h: (CREST - 0.3) * 424 / 417, altText: "University of Cape Town crest" });
s.addText("Embedded Telemetry with Road-Surface Characterisation and Camera-Based Hazard Detection for the TUKZIE Electric Trike", {
  x: TX, y: 0.25, w: W - M - TX, h: 3.0, fontFace: FONT, fontSize: 64, bold: true, color: C.white, align: "left", valign: "middle",
  isTextBox: true, margin: 0, lineSpacingMultiple: 0.92, shadow: { type: "outer", color: "000000", blur: 8, offset: 3, angle: 45, opacity: 0.55 },
});
s.addText([
  { text: "Samson Okuthe", options: { bold: true } },
  { text: "   |   Supervisor: A/Prof Simon Winberg   |   Co-supervisor: Sampath Jayalath" },
], { x: TX, y: 3.35, w: W - M - TX, h: 0.65, fontFace: FONT, fontSize: 30, color: C.white, align: "left", valign: "middle", isTextBox: true, margin: 0,
  shadow: { type: "outer", color: "000000", blur: 6, offset: 2, angle: 45, opacity: 0.6 } });

// ---------------- helpers ----------------
const PH = 1.35;   // panel heading band
function panel(n, title, x, y, w, h) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: C.panel, transparency: PANEL_ALPHA }, line: { color: C.line, width: 1 }, rectRadius: 0.3 });
  s.addShape(pres.shapes.OVAL, { x: x + 0.4, y: y + 0.3, w: 0.85, h: 0.85, fill: { color: C.navy }, line: { color: C.navy } });
  s.addText(String(n), { x: x + 0.4, y: y + 0.3, w: 0.85, h: 0.85, fontFace: FONT, fontSize: 34, bold: true, color: C.white,
    align: "center", valign: "middle", isTextBox: true, margin: 0 });
  s.addText(title, { x: x + 1.45, y: y + 0.25, w: w - 1.8, h: 0.95, fontFace: FONT, fontSize: T.head, bold: true, color: C.navy,
    valign: "middle", isTextBox: true, margin: 0 });
  return { x: x + 0.5, y: y + PH, w: w - 1.0 };
}
function rich(text, opts = {}) {   // "a_w" -> a with subscript w
  const parts = text.split("a_w"), runs = [];
  parts.forEach((p, i) => {
    if (p) runs.push({ text: p, options: { ...opts } });
    if (i < parts.length - 1) { runs.push({ text: "a", options: { ...opts } }); runs.push({ text: "w", options: { ...opts, subscript: true } }); }
  });
  return runs;
}
function txt(t, x, y, w, h, o = {}) {
  s.addText(typeof t === "string" ? rich(t) : t, { x, y, w, h, fontFace: FONT, fontSize: T.small, color: C.text, valign: "top",
    isTextBox: true, margin: 0, ...o });
}
function photo(file, x, y, w, h, alt, round = false) {
  s.addImage({ path: file, x, y, w, h, sizing: { type: "cover", w, h }, rounding: round, altText: alt });
  if (round) s.addShape(pres.shapes.OVAL, { x, y, w, h, fill: { type: "none" }, line: { color: C.navy, width: 4 } });
  else s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { type: "none" }, line: { color: C.white, width: 3 } });
}
function box(x, y, w, h, fill, line) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.1, fill: { color: fill }, line: { color: line || fill, width: 1.5 } });
}

const TOP = BANNER_H + 0.45;
const REF_H = 0.85, BOTTOM = H - M - REF_H - GAP;

// ================= left column =================
// 1 Background: three circle photos with a short line each
let y = TOP;
const h1 = 4.45;
let b = panel(1, "Background", XL, y, COLW, h1);
{
  const items = [
    [A("road_test_1027.jpg"), "The TUKZIE: an electric cargo trike for last-mile freight", "The TUKZIE trike on the road test"],
    [A("existing_dashboard.jpg"), "As built, nothing measured its ride or warned its driver", "The trike's own dashboard screen before this project"],
    [A("project_brief.jpg"), "The brief's windshield HUD became alerts on its dashboard", "The project brief page with the windshield HUD concept"],
  ];
  const cw = b.w / 3, d = 1.65;
  items.forEach(([f, t, alt], i) => {
    const cx = b.x + i * cw;
    photo(f, cx + (cw - d) / 2, b.y, d, d, alt, true);
    txt(t, cx + 0.1, b.y + d + 0.12, cw - 0.2, 1.25, { align: "center" });
    if (i < 2) s.addShape(pres.shapes.LINE, { x: cx + (cw + d) / 2 + 0.12, y: b.y + d / 2, w: cw - d - 0.24, h: 0,
      line: { color: C.navy, width: 3, endArrowType: "triangle" } });
  });
}

// 2 Scope: labelled arrows (aim, requirements, constraints)
y += h1 + GAP;
const h2 = 5.2;
b = panel(2, "Scope", XL, y, COLW, h2);
{
  const rows = [
    ["Aim", "IMUs measure vibration front and rear; cameras warn the driver on the trike's own dashboard; no record is lost when the network drops.", 1.62],
    ["Requirements", "13, each with a pass mark set before its test; bench first, then the trike.", 0.92],
    ["Constraints", "Removable, no drilling; no test participants (ethics); low-speed tests in a car park.", 0.92],
  ];
  const lw = 2.85;
  let ry = b.y;
  rows.forEach(([lab, t, rh]) => {
    s.addShape(pres.shapes.PENTAGON, { x: b.x, y: ry, w: lw, h: rh, fill: { color: C.navy }, line: { color: C.navy } });
    txt(lab, b.x + 0.15, ry, lw - 0.4, rh, { color: C.white, bold: true, valign: "middle" });
    box(b.x + lw + 0.1, ry, b.w - lw - 0.1, rh, C.white, C.line);
    txt(t, b.x + lw + 0.3, ry + 0.06, b.w - lw - 0.45, rh - 0.1, { valign: "middle" });
    ry += rh + 0.15;
  });
}

// 3 System: block diagram, front and rear computers, blocks coloured by subsystem, photos tagged the same way
y += h2 + GAP;
const H5 = 13.15, H6 = 5.9;   // right-column heights, so panel 4 starts level with panel 7
const h3 = H5 + H6 - h1 - h2 - GAP;
b = panel(3, "System on the trike", XL, y, COLW, h3);
{
  // legend
  const leg = [["sense", 2.15], ["hazard", 2.75], ["telem", 1.95], ["display", 2.47]];
  let lx = b.x;
  leg.forEach(([k, w]) => {
    box(lx, b.y, w, 0.5, SYS[k].c);
    txt(SYS[k].name, lx, b.y, w, 0.5, { color: C.white, bold: true, align: "center", valign: "middle" });
    lx += w + 0.1;
  });
  // two computers
  const zy = b.y + 0.75, zw = 4.15, zh = 3.5, bh = 0.6, bg = 0.1;
  const zone = (x, head, blocks) => {
    box(x, zy, zw, zh, C.white, C.navy);
    txt(head, x + 0.15, zy + 0.08, zw - 0.3, 0.5, { bold: true, color: C.navy, fontSize: 26 });
    blocks.forEach(([k, t], i) => {
      const by = zy + 0.7 + i * (bh + bg);
      box(x + 0.15, by, zw - 0.3, bh, SYS[k].t, SYS[k].c);
      txt(t, x + 0.3, by, zw - 0.5, bh, { valign: "middle", color: C.text });
    });
  };
  zone(b.x, "Front: Raspberry Pi 5", [
    ["sense", "IMU node, 200" + NB + "Hz"],
    ["hazard", "Front camera, detector"],
    ["display", "Dashboard, 10.1" + NB + "in screen"],
    ["telem", "Phone GNSS for speed"],
  ]);
  const zr = b.x + b.w - zw;
  zone(zr, "Rear: Raspberry Pi 4", [
    ["sense", "IMU node, 200" + NB + "Hz"],
    ["hazard", "Rear camera, detector, ToF"],
    ["telem", "Battery (BMS) and GNSS"],
    ["telem", "Store and forward over LTE"],
  ]);
  const ax = b.x + zw + 0.08, aw = zr - ax - 0.08, ay = zy + zh / 2;
  s.addShape(pres.shapes.LINE, { x: ax, y: ay, w: aw, h: 0, line: { color: C.navy, width: 5, beginArrowType: "triangle", endArrowType: "triangle" } });
  txt("Ethernet", ax - 0.3, ay - 0.6, aw + 0.6, 0.45, { bold: true, color: C.navy, align: "center" });
  txt("time sync", ax - 0.3, ay + 0.15, aw + 0.6, 0.45, { color: C.navy, align: "center" });
  // photos, one per subsystem
  const py = zy + zh + 0.3, pg = 0.2, pw = (b.w - 2 * pg) / 3, ph = h3 - PH - (py - b.y) - 0.75;
  const pics = [
    [R("road1/front_camera_1022.jpg"), "Front camera", "hazard", "Front camera in its printed housing on the frame"],
    [R("road1/rear_system_1022.jpg"), "Rear unit", "telem", "Rear unit in its printed enclosure on the cargo bed"],
    [A("road_battery_page_1027.jpg"), "Battery page", "display", "Dashboard battery page on the road at 11:37 on 27 October, live from the BMS: 55 percent, 74.0 V"],
  ];
  pics.forEach(([f, cap, k, alt], i) => {
    const px = b.x + i * (pw + pg);
    photo(f, px, py, pw, ph, alt);
    txt(cap, px, py + ph + 0.06, pw, 0.45, { align: "center", bold: true, color: SYS[k].c });
  });
}

// 4 Plan and method: Gantt from the site's stage dates, then how the road test was run
y += h3 + GAP;
const h4 = BOTTOM - y;
b = panel(4, "Plan and method", XL, y, COLW, h4);
{
  const day0 = Date.UTC(2026, 6, 20), span = 103;   // 20 Jul to 31 Oct 2026
  const d = (m, dd) => (Date.UTC(2026, m - 1, dd) - day0) / 86400000;
  const lw = 2.95, gx = b.x + lw, gw = b.w - lw, rh = 0.4;
  const X = (v) => gx + gw * v / span;
  const months = [["Aug", d(8, 1)], ["Sep", d(9, 1)], ["Oct", d(10, 1)]];
  const gy = b.y + 0.45;
  const rows = [
    ["Brief, planning", d(7, 22), d(8, 31)],
    ["Meeting the trike", d(9, 2), d(9, 16)],
    ["First prototype", d(9, 18), d(9, 28)],
    ["Sensors, training", d(9, 30), d(10, 2)],
    ["Bench tests", d(10, 3), d(10, 14)],
    ["Enclosures", d(10, 11), d(10, 16)],
    ["Fixes for run 2", d(10, 21), d(10, 26)],
    ["Road tests", null, null],
  ];
  const gh = rows.length * rh;
  txt("Jul", gx, b.y, 0.8, 0.4, { color: C.muted });
  months.forEach(([m, v]) => {
    s.addShape(pres.shapes.LINE, { x: X(v), y: gy, w: 0, h: gh, line: { color: C.line, width: 1.5 } });
    txt(m, X(v) + 0.05, b.y, 0.8, 0.4, { color: C.muted });
  });
  rows.forEach(([lab, a, e], i) => {
    const ry = gy + i * rh;
    txt(lab, b.x, ry, lw - 0.1, rh, { valign: "middle" });
    if (a !== null) s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: X(a), y: ry + 0.07, w: Math.max(X(e + 1) - X(a), 0.12), h: rh - 0.14,
      rectRadius: 0.05, fill: { color: C.navy }, line: { color: C.navy } });
  });
  // road tests as diamonds, 19 and 27 October
  const ry = gy + (rows.length - 1) * rh;
  [d(10, 19), d(10, 27)].forEach((v) => {
    s.addShape(pres.shapes.DIAMOND, { x: X(v) - 0.17, y: ry + 0.03, w: 0.34, h: 0.34, fill: { color: C.accent }, line: { color: C.accent } });
  });
  txt("19 and 27 Oct", X(d(10, 19)) - 2.45, ry, 2.2, rh, { color: C.accent, bold: true, align: "right", valign: "middle" });
  const my = gy + gh + 0.25;
  s.addText([
    ...rich("Requirements first: ", { bold: true, color: C.navy }),
    ...rich("each pass mark set before its test. "),
    ...rich("Road test: ", { bold: true, color: C.navy }),
    ...rich("smooth loop (5 passes) and rough strip (4 passes) at 10" + NB + "km/h; one vibration score per pass, a_w (ISO" + NB + "2631-1)."),
  ], { x: b.x, y: my, w: b.w, h: h4 - PH - (my - b.y) - 0.25, fontFace: FONT, fontSize: T.small, color: C.text, valign: "top", isTextBox: true, margin: 0 });
}

// ================= right column =================
// 5 Results: trace, then six tiles tinted by subsystem
y = TOP;
const h5 = H5;
b = panel(5, "What the road test showed", XR, y, COLW, h5);
{
  const tile = (k, big, small, x, ty, tw, th, bigSize = 34) => {
    box(x, ty, tw, th, SYS[k].t, SYS[k].t);
    txt(big, x + 0.18, ty + 0.06, tw - 0.3, 0.62, { fontSize: bigSize, bold: true, color: SYS[k].c, valign: "middle" });
    txt(small, x + 0.18, ty + 0.72, tw - 0.3, th - 0.76);
  };
  // ride: rear IMU trace, then three tiles
  const fw = b.w * 0.8, fH = fw * 5 / 10;
  s.addImage({ path: A("imu_smooth_rough.png"), x: b.x + (b.w - fw) / 2, y: b.y - 0.1, w: fw, h: fH,
    altText: "Rear IMU vertical vibration over 40 s of a smooth-loop pass and a rough-strip pass at 10 km/h; the rough trace is about twice as large" });
  txt("Rear IMU, one pass of each (all passes: 1.78 against 3.61" + NB + "m/s²)",
    b.x, b.y - 0.08 + fH, b.w, 0.45, { italic: true, color: C.muted, align: "center" });
  const tg = 0.15, t3 = (b.w - 2 * tg) / 3, ry1 = b.y + fH + 0.45, th1 = 1.95;
  tile("sense", "about 2" + NB + "×", "more vibration on the rough strip, both ends", b.x, ry1, t3, th1);
  tile("sense", "5.0 / 5.3" + NB + "%", "pass-to-pass spread; target 10" + NB + "%: met", b.x + t3 + tg, ry1, t3, th1);
  tile("sense", "ICC 0.16", "spot-by-spot repeat; target 0.75: not met", b.x + 2 * (t3 + tg), ry1, t3, th1);
  // cameras: the dashboard on the road with a truck and people detected
  const cy = ry1 + th1 + 0.25, cw = 6.25, ch = cw * 590 / 1280;
  photo(A("road_truck_detect_1027.jpg"), b.x, cy, cw, ch,
    "Dashboard on the road at 12:32 on 27 October: the front camera boxes a truck 7.3 m to the right as a warning and lists three people ahead; the banner shows a person alert from the rear");
  const sx = b.x + cw + 0.18, sw = b.w - cw - 0.18;
  tile("hazard", "23.3 / 12.1", "frames/s on the road, front / rear", sx, cy, sw, 1.5, 32);
  txt("Truck 7.3" + NB + "m right: a warning; people ahead; rear alert in the banner",
    sx, cy + 1.6, sw, ch - 1.6, { color: C.text });
  txt("Front camera on the dashboard, 12:32 on 27 Oct (screen capture)", b.x, cy + ch + 0.05, b.w, 0.45, { italic: true, color: C.muted });
  // links
  const ry3 = cy + ch + 0.6, t2 = (b.w - tg) / 2, th3 = 1.55;
  tile("telem", "112 / 112", "records kept through a 10-minute LTE outage (bench)", b.x, ry3, t2, th3);
  tile("display", "99.9" + NB + "%", "of records reached the recorder over the wired link", b.x + t2 + tg, ry3, t2, th3);
}

// 6 Requirements scorecard: R1 to R13 by subsystem, coloured by verdict
y += h5 + GAP;
const h6 = H6;
b = panel(6, "Requirements scorecard", XR, y, COLW, h6);
{
  const V = { m: C.green, p: C.amber, n: C.grey };
  const legend = [["m", "Met (5)"], ["p", "Partly met (7)"], ["n", "Not tested (1)"]];
  let lx = b.x;
  legend.forEach(([k, t]) => {
    box(lx, b.y + 0.05, 0.4, 0.4, V[k]);
    txt(t, lx + 0.5, b.y, 2.6, 0.5, { valign: "middle" });
    lx += 3.1;
  });
  const rows = [
    ["sense", [["R1 IMU rate", "m"], ["R2 Calibration", "m"], ["R3 Features", "m"]]],
    ["hazard", [["R6 Sync pulse", "p"], ["R7 Detection", "p"], ["R8 Range", "p"]]],
    ["telem", [["R4 Position", "p"], ["R5 Battery", "p"], ["R9 Store, send", "m"]]],
    ["display", [["R10 Wired link", "m"], ["R11 Live data", "p"], ["R12 Glance time", "n"]]],
    [null, [["R13 Removable", "p"]]],
  ];
  const lab = 2.55, cw = (b.w - lab - 0.2) / 3, rh = 0.56;
  rows.forEach(([k, chips], i) => {
    const ry = b.y + 0.7 + i * (rh + 0.1);
    txt(k ? SYS[k].name : "Installation", b.x, ry, lab - 0.1, rh, { bold: true, color: k ? SYS[k].c : C.navy, valign: "middle" });
    chips.forEach(([t, v], j) => {
      const cx = b.x + lab + j * (cw + 0.1);
      box(cx, ry, cw, rh, V[v]);
      txt(t, cx, ry, cw, rh, { color: C.white, bold: true, align: "center", valign: "middle" });
    });
  });
  txt("On the trike, R2 was not met and R9 and R10 were partly met.",
    b.x, b.y + 0.7 + 5 * (rh + 0.1) + 0.05, b.w, 0.8, { italic: true, color: C.muted });
}

// 7 Conclusion, limits paired with next steps, QR code
y += h6 + GAP;
const h7 = BOTTOM - y;
b = panel(7, "Conclusion", XR, y, COLW, h7);
{
  const qr = 2.1;
  txt("The unit works on the trike: its vibration score tells smooth road from rough and repeats over whole passes, not yet place by place.",
    b.x, b.y, b.w - qr - 0.35, 1.7, { fontSize: T.body });
  const qx = b.x + b.w - qr, qy = b.y - 0.95;
  s.addShape(pres.shapes.RECTANGLE, { x: qx, y: qy, w: qr, h: qr, fill: { color: C.white }, line: { color: C.white } });
  s.addImage({ path: A("qr_tuksense.png"), x: qx + 0.08, y: qy + 0.08, w: qr - 0.16, h: qr - 0.16, altText: "QR code to https://tuksense.site" });
  txt([{ text: "Videos: ", options: { bold: true } }, { text: "tuksense.site" }], qx - 1.5, qy + qr + 0.05, qr + 1.5, 0.45,
    { color: C.navy, align: "right" });
  const pairs = [
    ["One trike, short low-speed runs, no reference sensor", "Tie the score to a surveyed road section"],
    ["Pi" + NB + "4 restarted once on low voltage", "Regulated supply from the vehicle"],
    ["Warnings below ISO" + NB + "15008 size", "Enlarge them, then a glance study (R12)"],
  ];
  const py0 = b.y + 1.6, hw = (b.w - 0.6) / 2, rh = 0.8;
  txt("Limited by", b.x, py0, hw, 0.42, { bold: true, color: C.accent });
  txt("Next", b.x + hw + 0.6, py0, hw, 0.42, { bold: true, color: C.green });
  pairs.forEach(([l, n], i) => {
    const py = py0 + 0.45 + i * (rh + 0.1);
    box(b.x, py, hw, rh, C.white, C.accent);
    txt(l, b.x + 0.15, py, hw - 0.25, rh, { valign: "middle" });
    s.addShape(pres.shapes.LINE, { x: b.x + hw + 0.08, y: py + rh / 2, w: 0.44, h: 0, line: { color: C.navy, width: 3, endArrowType: "triangle" } });
    box(b.x + hw + 0.6, py, hw, rh, C.white, C.green);
    txt(n, b.x + hw + 0.75, py, hw - 0.25, rh, { valign: "middle" });
  });
}

// ---------------- references ----------------
const ry = H - M - REF_H;
box(M, ry, W - 2 * M, REF_H, C.white, C.line);
txt([
  { text: "References: ", options: { bold: true, color: C.navy } },
  { text: "ISO 2631-1:1997, whole-body vibration;  ISO 15008:2017, in-vehicle visual presentation;  NHTSA (2013), visual-manual driver distraction guidelines.  Full list in the report." },
], M + 0.25, ry, W - 2 * M - 0.5, REF_H, { valign: "middle" });

const out = process.argv[2] || path.join(__dirname, "..", "SW7_Poster_A1.pptx");
pres.writeFile({ fileName: out }).then((f) => console.log("wrote", f));
