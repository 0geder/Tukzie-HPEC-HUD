// SW7 A1 portrait poster, in the style of the UCT poster template
// (campus banner header, light-blue content panels, UCT crest).
// Updated 20 Oct 2026 with the two-sided layout, the Pi 5 detector, the approaching-object warning,
// the power budget and the first road session; numbers from the report.
// Updated 24 Oct 2026: one IMU per node, phone GNSS, legibility, stand runs of 23 Oct, R1 status on the vehicle.
const pptxgen = require("pptxgenjs");
const path = require("path");
const A = (f) => path.join(__dirname, "assets", f);
const R = (f) => path.join(__dirname, "..", "..", "Report", "figures", f);

const C = {
  navy: "14305C", sky: "1565C0", panel: "E8F0FA", accent: "D4700C",
  text: "1B1F24", muted: "4A5566", white: "FFFFFF",
};
const FONT = "Calibri";
const NB = " ";   // keeps a number and its unit on one line

const W = 33.11, H = 46.81;            // A1 portrait, inches
const M = 1.2, GAP = 0.9;              // outer margin, gap between columns/panels
const COLW = (W - 2 * M - GAP) / 2;
const XL = M, XR = M + COLW + GAP;

const pres = new pptxgen();
pres.defineLayout({ name: "A1P", width: W, height: H });
pres.layout = "A1P";
pres.title = "SW7 poster: Embedded telemetry, road-surface characterisation and camera-based hazard detection for the TUKZIE electric tricycle";
const s = pres.addSlide();
s.background = { color: C.white };

// ---- header: campus banner with the title on the sky ----
const BANNER_H = 10.6;
s.addImage({ path: A("uct_banner.jpg"), x: 0, y: 0, w: W, h: BANNER_H, sizing: { type: "cover", w: W, h: BANNER_H } });
s.addText("EEE4022S Final Year Project 2026, Department of Electrical Engineering, University of Cape Town", {
  x: M, y: 0.45, w: W - 2 * M, h: 0.8, fontFace: FONT, fontSize: 30, color: C.white, align: "center", isTextBox: true, margin: 0,
});
s.addText("Embedded Telemetry, Road-Surface Characterisation\nand Camera-Based Hazard Detection for the TUKZIE Electric Tricycle", {
  x: M, y: 1.35, w: W - 2 * M, h: 3.3, fontFace: FONT, fontSize: 78, bold: true, color: C.white, align: "center", valign: "middle",
  isTextBox: true, margin: 0, shadow: { type: "outer", color: "000000", blur: 8, offset: 3, angle: 45, opacity: 0.55 },
});
s.addText("Samson Okuthe (OKTSAM001)   |   Supervisor: A/Prof. Simon Winberg   |   Co-supervisor: Sampath Jayalath", {
  x: M, y: 4.85, w: W - 2 * M, h: 0.9, fontFace: FONT, fontSize: 34, bold: true, color: C.white, align: "center", isTextBox: true, margin: 0,
  shadow: { type: "outer", color: "000000", blur: 6, offset: 2, angle: 45, opacity: 0.6 },
});

// ---- panel helper: rounded light-blue card with a numbered heading ----
function panel(n, title, x, y, h) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: COLW, h, fill: { color: C.panel }, line: { color: C.panel }, rectRadius: 0.35 });
  s.addShape(pres.shapes.OVAL, { x: x + 0.55, y: y + 0.5, w: 1.25, h: 1.25, fill: { color: C.navy }, line: { color: C.navy } });
  s.addText(String(n), { x: x + 0.55, y: y + 0.5, w: 1.25, h: 1.25, fontFace: FONT, fontSize: 44, bold: true, color: C.white,
    align: "center", valign: "middle", isTextBox: true, margin: 0 });
  s.addText(title, { x: x + 2.15, y: y + 0.45, w: COLW - 2.6, h: 1.35, fontFace: FONT, fontSize: 56, bold: true, color: C.navy,
    valign: "middle", isTextBox: true, margin: 0 });
  return { x: x + 0.7, y: y + 2.2, w: COLW - 1.4 };   // content box
}
function bullets(items, box, h, size = 32, color = C.text) {
  s.addText(items.map((t, i) => ({ text: t, options: { bullet: { indent: 32 }, breakLine: i < items.length - 1, paraSpaceAfter: 14 } })), {
    x: box.x, y: box.y, w: box.w, h, fontFace: FONT, fontSize: size, color, valign: "top", isTextBox: true, margin: 0,
  });
}
function caption(t, x, y, w, h = 1.0) {
  s.addText(t, { x, y, w, h, fontFace: FONT, fontSize: 24, italic: true, color: C.muted, valign: "top", isTextBox: true, margin: 0 });
}

const TOP = BANNER_H + 0.9, BOTTOM = H - 3.1;

// ================= left column =================
// 1 Background
let yL = TOP, h1 = 6.6;
let b = panel(1, "Background", XL, yL, h1);
bullets([
  "Electric cargo trikes are a low-cost route to last-mile freight in African cities, but their ride and road conditions go unmeasured.",
  "Head-down displays draw the driver's eyes off the road; single glances should stay under 2" + NB + "s.",
  "Aim: a low-cost unit that characterises the ride at the edge and gives the driver only safety-relevant alerts, each stage tested before the next.",
], b, h1 - 2.4, 30);

// 2 System: two sides joined by Ethernet
yL += h1 + GAP;
const h2 = 10.0;
b = panel(2, "System: front and rear", XL, yL, h2);
{
  const cw = (b.w - 3.0) / 2, ch = 6.3, cy = b.y;
  const side = (x, head, items) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: cy, w: cw, h: ch, rectRadius: 0.2, fill: { color: C.white }, line: { color: C.sky, width: 3 } });
    s.addText(head, { x: x + 0.35, y: cy + 0.25, w: cw - 0.7, h: 1.3, fontFace: FONT, fontSize: 30, bold: true, color: C.navy, valign: "top", isTextBox: true, margin: 0 });
    bullets(items, { x: x + 0.35, y: cy + 1.65, w: cw - 0.7 }, ch - 1.8, 24);
  };
  side(b.x, "Front: Raspberry Pi 5,\nbehind the dashboard", [
    "Front camera, detector and time-of-flight board",
    "Front node: ESP32-S3 with one IMU at 200" + NB + "Hz",
    "Dashboard on the 10.1" + NB + "in touchscreen",
    "Phone GNSS for speed; road recorder",
  ]);
  const xr = b.x + b.w - cw;
  side(xr, "Rear: Raspberry Pi 4,\nbeside the battery", [
    "Rear camera, detector and time-of-flight board",
    "Rear node: ESP32-S3 with one IMU at 200" + NB + "Hz",
    "LTE, GNSS, battery over Bluetooth",
    "Local log and LTE uplink to a database",
  ]);
  const lx = b.x + cw + 0.2, lw = xr - lx - 0.2, ly = cy + ch / 2;
  s.addShape(pres.shapes.LINE, { x: lx, y: ly, w: lw, h: 0, line: { color: C.navy, width: 5, beginArrowType: "triangle", endArrowType: "triangle" } });
  s.addText("Ethernet", { x: lx, y: ly - 0.95, w: lw, h: 0.7, fontFace: FONT, fontSize: 28, bold: true, color: C.navy, align: "center", isTextBox: true, margin: 0 });
  s.addText("1000" + NB + "Mb/s\n0.22 to 0.25" + NB + "ms", { x: lx, y: ly + 0.25, w: lw, h: 1.2, fontFace: FONT, fontSize: 22, color: C.muted, align: "center", valign: "top", isTextBox: true, margin: 0 });
  caption("Two sides since 15 October: the battery's Bluetooth did not reach the front, and the Pi 5 runs the detector more than twice as fast.",
    b.x, cy + ch + 0.25, b.w, 1.1);
}

// 3 Hazard warnings on the dashboard
yL += h2 + GAP;
const h3 = BOTTOM - yL;
b = panel(3, "Hazard warnings on the dashboard", XL, yL, h3);
{
  const iw = (b.w - 0.5) / 2, ih = iw * 800 / 1280;
  s.addImage({ path: R("ui/ui_dualcam_front.png"), x: b.x, y: b.y, w: iw, h: ih });
  s.addImage({ path: R("ui/ui_dualcam_rear_approaching.png"), x: b.x + iw + 0.5, y: b.y, w: iw, h: ih });
  caption("Front | Rear switch on the existing dashboard (test images).", b.x, b.y + ih + 0.15, iw, 0.9);
  caption("Rear view mirrored; a car approaching at 1.6" + NB + "s.", b.x + iw + 0.5, b.y + ih + 0.15, iw, 0.9);
  const by = b.y + ih + 1.25;
  bullets([
    "Detection on the Pi 5 beside the display: 51 to 54" + NB + "ms median from sensor readout at 19.2" + NB + "fps, against 118 to 122" + NB + "ms on the Pi 4 with the whole system.",
    "Approaching objects: time to contact from the growth of the box, τ = w / (dw/dt), with no focal length or object size (Lee 1976). Warning under 4" + NB + "s, immediate under 2" + NB + "s.",
    "Synthetic tests within 2" + NB + "%; not yet tested on a real approach. Live data only; frames never stored.",
    "Legibility at 0.70" + NB + "m (ISO 15008: 16 arc minutes acceptable, 20 recommended): speed digits 84, alert banner 9, labels a median of 9. The speed is legible at a glance; the warnings are not. Glance time needs a participant.",
  ], { x: b.x, y: by, w: b.w }, yL + h3 - by - 0.4, 28);
}

// ================= right column =================
// 4 Bench results: six tiles
let yR = TOP;
const statH = 2.85, statG = 0.35;
const h4 = 2.2 + 3 * statH + 2 * statG + 0.5;
b = panel(4, "Bench results", XR, yR, h4);
{
  const stats = [
    ["200" + NB + "Hz", "both IMUs, no samples dropped; 149 of 149 windows fused"],
    ["51 to 54" + NB + "ms", "median detection on the Pi 5 at 19.2 fps (Pi 4: about 120" + NB + "ms)"],
    ["2.7" + NB + "m", "median GNSS error against a phone, 104 fixes"],
    ["112 / 112", "records stored in the database across a 10-minute LTE outage"],
    ["within 2" + NB + "%", "time to contact in 40 synthetic tests; 0.27" + NB + "ms per frame"],
    ["about 20" + NB + "W", "power budget, 0.27" + NB + "A from the 72" + NB + "V pack; only the Pi 5 measured"],
  ];
  const statW = (b.w - 0.5) / 2;
  stats.forEach(([big, small], i) => {
    const x = b.x + (i % 2) * (statW + 0.5), y = b.y + Math.floor(i / 2) * (statH + statG);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: statW, h: statH, rectRadius: 0.2, fill: { color: C.white }, line: { color: C.white } });
    s.addText(big, { x: x + 0.3, y: y + 0.15, w: statW - 0.6, h: 1.35, fontFace: FONT, fontSize: 60, bold: true, color: C.navy, isTextBox: true, margin: 0, valign: "middle" });
    s.addText(small, { x: x + 0.3, y: y + 1.55, w: statW - 0.6, h: 1.2, fontFace: FONT, fontSize: 24, color: C.muted, valign: "top", isTextBox: true, margin: 0 });
  });
}

// 5 Faults found and fixed
yR += h4 + GAP;
const h5 = 6.6;
b = panel(5, "Fault investigations", XR, yR, h5);
bullets([
  "Seven faults diagnosed as symptom, candidate causes, deciding test, cause and fix, from a flash-mode boot loop to a battery checksum off by 3.",
  "The one that mattered most: Pi 4 reboots. Power flags logged every 2" + NB + "s showed under-voltage 14" + NB + "s after the modem came up on its USB port; it returned in the closed box (76.9" + NB + "°C), so the unit needs its own supply.",
], b, h5 - 2.4, 28);

// 6 Road session and conclusions
yR += h5 + GAP;
const h6 = BOTTOM - yR;
b = panel(6, "On the vehicle: road and stands", XR, yR, h6);
bullets([
  "Road session, 19 Oct: 108.6" + NB + "min recorded, about 16" + NB + "min driving. 200" + NB + "Hz with no counted drops, but one 2" + NB + "s stall: R1 not met on the vehicle. Battery link held at up to 46.9" + NB + "A. No GNSS fix (no antenna).",
], b, 2.0, 28);
{
  const fw = 11.6, fh = fw * 396 / 1100, fy = b.y + 2.1;
  s.addImage({ path: R("results/stand_spectra_1023.png"), x: b.x + (b.w - fw) / 2, y: fy, w: fw, h: fh });
  caption("Stand runs, 23 Oct, drive wheel raised: rear vibration 5 to 7 times rest, energy 40 to 70" + NB + "Hz; the same lines at the front (42.75, 49.0, 64.0" + NB + "Hz). Throttle settings not recorded.",
    b.x, fy + fh + 0.1, b.w, 0.9);
  const oy = fy + fh + 1.1;
  s.addText([
    ["Pending, road run 26 Oct: ", "repeatability over passes (RQ1) and the stand lines' share of the road spectrum (RQ4)."],
    ["Next: ", "enlarge the warnings, then glance time; the real approach test; a regulated supply for the telemetry unit."],
  ].flatMap(([k, t], i, a) => [
    { text: k, options: { bold: true, color: C.accent, bullet: { indent: 32 } } },
    { text: t, options: { breakLine: i < a.length - 1, paraSpaceAfter: 10 } },
  ]), { x: b.x, y: oy, w: b.w, h: yR + h6 - oy - 0.3, fontFace: FONT, fontSize: 26, color: C.text, valign: "top", isTextBox: true, margin: 0 });
}

// ---- footer ----
s.addImage({ path: A("uct_logo.png"), x: M, y: H - 2.75, w: 2.3, h: 2.34 });
s.addText("Department of Electrical Engineering, University of Cape Town   |   EEE4022S 2026   |   Project SW-7", {
  x: M + 2.9, y: H - 2.1, w: W - 2 * M - 2.9, h: 1.0, fontFace: FONT, fontSize: 28, color: C.navy, valign: "middle", isTextBox: true, margin: 0,
});

const out = process.argv[2] || path.join(__dirname, "..", "SW7_Poster_A1.pptx");
pres.writeFile({ fileName: out }).then((f) => console.log("wrote", f));
