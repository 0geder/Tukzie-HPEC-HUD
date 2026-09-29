// SW7 A1 portrait poster, in the style of the UCT poster template
// (campus banner header, light-blue content panels, UCT crest).
const pptxgen = require("pptxgenjs");
const path = require("path");
const A = (f) => path.join(__dirname, "assets", f);

const C = {
  navy: "14305C", sky: "1565C0", panel: "E8F0FA", accent: "D4700C",
  text: "1B1F24", muted: "4A5566", white: "FFFFFF",
};
const FONT = "Calibri";

const W = 33.11, H = 46.81;            // A1 portrait, inches
const M = 1.2, GAP = 0.9;              // outer margin, gap between columns/panels
const COLW = (W - 2 * M - GAP) / 2;
const XL = M, XR = M + COLW + GAP;

const pres = new pptxgen();
pres.defineLayout({ name: "A1P", width: W, height: H });
pres.layout = "A1P";
pres.title = "SW7 poster: Embedded telemetry unit and windshield HUD for the TUKZIE Rev 0";
const s = pres.addSlide();
s.background = { color: C.white };

// ---- header: campus banner with the title on the sky ----
const BANNER_H = 10.6;
s.addImage({ path: A("uct_banner.jpg"), x: 0, y: 0, w: W, h: BANNER_H, sizing: { type: "cover", w: W, h: BANNER_H } });
s.addText("EEE4022S Final Year Project 2026, Department of Electrical Engineering, University of Cape Town", {
  x: M, y: 0.45, w: W - 2 * M, h: 0.8, fontFace: FONT, fontSize: 30, color: C.white, align: "center", isTextBox: true, margin: 0,
});
s.addText("An Embedded Telemetry Unit and Windshield HUD\nfor the TUKZIE Rev 0 Electric Cargo Trike", {
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
function bullets(items, box, h, size = 32) {
  s.addText(items.map((t, i) => ({ text: t, options: { bullet: { indent: 32 }, breakLine: i < items.length - 1, paraSpaceAfter: 14 } })), {
    x: box.x, y: box.y, w: box.w, h, fontFace: FONT, fontSize: size, color: C.text, valign: "top", isTextBox: true, margin: 0,
  });
}

const TOP = BANNER_H + 0.9;

// ================= left column =================
// 1 Background
let yL = TOP, h1 = 7.0;
let b = panel(1, "Background", XL, yL, h1);
bullets([
  "Electric cargo trikes are a low-cost route to last-mile freight in African cities, but their ride and road conditions go unmeasured.",
  "Head-down displays draw the driver's eyes off the road; single glances should stay under 2 s.",
  "Aim: a low-cost unit that characterises the trike's ride at the edge and shows only safety-relevant data head-up.",
], b, h1 - 2.5);

// 2 System
yL += h1 + GAP;
const imgW = COLW - 1.4, imgH = imgW * 1349 / 1845;
let h2 = 2.2 + imgH + 1.3;
b = panel(2, "System", XL, yL, h2);
s.addImage({ path: A("bench_labelled.png"), x: b.x, y: b.y, w: imgW, h: imgH });
s.addText("Bench setup: ESP32-S3 telemetry unit with LTE modem, two IMUs, GNSS and BLE battery link; Raspberry Pi 4 camera, time-aligned by a sync-pulse wire.", {
  x: b.x, y: b.y + imgH + 0.15, w: b.w, h: 1.0, fontFace: FONT, fontSize: 24, italic: true, color: C.muted, isTextBox: true, margin: 0,
});

// 3 Approach: staged verification flow
yL += h2 + GAP;
let h3 = H - 3.1 - yL;
b = panel(3, "Approach", XL, yL, h3);
const steps = [
  "Bring up each interface on the target board",
  "Acquire both IMUs at 200 Hz and calibrate them",
  "Compute ride features and fuse the two IMUs",
  "Log locally and publish over LTE",
  "Validate on the moving vehicle",
];
const stepH = 1.05, stepGap = 0.3;
steps.forEach((t, i) => {
  const y = b.y + i * (stepH + stepGap);
  const last = i === steps.length - 1;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: b.x, y, w: b.w, h: stepH, rectRadius: 0.2,
    fill: { color: last ? C.white : C.white }, line: { color: last ? C.accent : C.sky, width: 3, dashType: last ? "dash" : "solid" } });
  s.addText([{ text: `${i + 1}  `, options: { bold: true, color: last ? C.accent : C.sky } }, { text: t, options: { color: C.text } }], {
    x: b.x + 0.4, y, w: b.w - 0.8, h: stepH, fontFace: FONT, fontSize: 30, valign: "middle", isTextBox: true, margin: 0 });
});
s.addText("Each stage is tested before the next is built on it. Stage 5 is still to come.", {
  x: b.x, y: b.y + steps.length * (stepH + stepGap) + 0.05, w: b.w, h: 0.9, fontFace: FONT, fontSize: 24, italic: true, color: C.muted, isTextBox: true, margin: 0,
});

// ================= right column =================
// 4 Bench results
let yR = TOP;
const chartW = COLW - 1.4, chartH = chartW * 888 / 2604;
const statH = 3.05;
let h4 = 2.2 + 2 * statH + 0.4 + 0.6 + chartH + 1.3;
b = panel(4, "Bench results", XR, yR, h4);
const stats = [
  ["200 Hz", "both IMUs, zero dropped samples"],
  ["8%", "gap between the two IMUs, calibrated down to noise"],
  ["< 1 s", "camera aligned to the IMU data"],
  ["149 / 149", "windows fused from both IMUs"],
];
const statW = (b.w - 0.5) / 2;
stats.forEach(([big, small], i) => {
  const x = b.x + (i % 2) * (statW + 0.5), y = b.y + Math.floor(i / 2) * (statH + 0.4);
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: statW, h: statH, rectRadius: 0.2, fill: { color: C.white }, line: { color: C.white } });
  s.addText(big, { x: x + 0.3, y: y + 0.2, w: statW - 0.6, h: 1.55, fontFace: FONT, fontSize: 66, bold: true, color: C.navy, isTextBox: true, margin: 0 });
  s.addText(small, { x: x + 0.3, y: y + 1.75, w: statW - 0.6, h: 1.15, fontFace: FONT, fontSize: 26, color: C.muted, valign: "top", isTextBox: true, margin: 0 });
});
const cy = b.y + 2 * statH + 0.4 + 0.6;
s.addImage({ path: A("vibration_chart.png"), x: b.x, y: cy, w: chartW, h: chartH });
s.addText("Recorded 150 s bench session: board still, then disturbed by hand from about 75 s. The fused estimate (green) sits between the two sensors.", {
  x: b.x, y: cy + chartH + 0.15, w: b.w, h: 1.0, fontFace: FONT, fontSize: 24, italic: true, color: C.muted, isTextBox: true, margin: 0,
});

// 5 Faults found and fixed
yR += h4 + GAP;
let h5 = 7.9;
b = panel(5, "Found and fixed", XR, yR, h5);
bullets([
  "GNSS reply: assumed 13 fields, measured 9; the manual documents 16, with speed in knots.",
  "Battery (BLE) service lookup was wrong; fixed, and the frame decoding matched an independent parser byte for byte.",
  "The microSD chip-select is not fitted, so logging moved to the processor's own flash.",
  "A boot loop traced to a flash-size mismatch with the 16 MB partition table.",
], b, h5 - 2.5, 30);

// 6 Conclusions
yR += h5 + GAP;
let h6 = H - 3.1 - yR;
b = panel(6, "Conclusions and next steps", XR, yR, h6);
bullets([
  "Every subsystem runs together on the target board, with dual-IMU fusion verified live.",
  "Next: recalibrate the IMUs and run the on-vehicle field test, then integrate the time-of-flight and air-quality sensors and build the HUD.",
], b, h6 - 2.5, 30);

// ---- footer ----
s.addImage({ path: A("uct_logo.png"), x: M, y: H - 2.75, w: 2.3, h: 2.34 });
s.addText("Department of Electrical Engineering, University of Cape Town   |   EEE4022S 2026   |   Project SW-7", {
  x: M + 2.9, y: H - 2.1, w: W - 2 * M - 2.9, h: 1.0, fontFace: FONT, fontSize: 28, color: C.navy, valign: "middle", isTextBox: true, margin: 0,
});

const out = process.argv[2] || path.join(__dirname, "SW7_Poster_A1.pptx");
pres.writeFile({ fileName: out }).then((f) => console.log("wrote", f));
