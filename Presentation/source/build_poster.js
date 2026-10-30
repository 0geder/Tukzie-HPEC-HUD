// EEE4022S A1 portrait poster (true A1, 594 x 841 mm), in the style of the UCT poster template
// (campus banner header, light-blue numbered panels, UCT crest).
// Rebuilt 30 Oct 2026 for the poster session: true A1 page, report title, road results of 27 October,
// system as driven on 27 October, QR code to the video site. Every number is from the final report
// (Results.tex, Table 5.3, Conclusions.tex) or run2_summary_numbers.txt.
// Earlier version (A0-sized canvas, "pending" road items) backed up in ../backup_2026-10-30.
const pptxgen = require("pptxgenjs");
const path = require("path");
const A = (f) => path.join(__dirname, "assets", f);
const R = (f) => path.join(__dirname, "..", "..", "Report", "figures", f);

const C = {
  navy: "14305C", sky: "1565C0", panel: "E8F0FA", accent: "B45309", green: "1B7F3B",
  text: "1B1F24", muted: "3F4A5A", white: "FFFFFF", line: "B9C7DA",
};
const FONT = "Calibri";
const NB = " ";   // keeps a number and its unit on one line

const W = 594 / 25.4, H = 841 / 25.4;   // A1 portrait, inches (23.39 x 33.11)
const M = 0.8, GAP = 0.55;              // outer margin, gap between columns/panels
const COLW = (W - 2 * M - GAP) / 2;
const XL = M, XR = M + COLW + GAP;

// type scale at A1 (Lecture 2: title 70, headings 56, body 32; floor 24)
const T = { title: 82, head: 48, body: 28, small: 25, cap: 24, big: 50 };

const pres = new pptxgen();
pres.defineLayout({ name: "A1P", width: W, height: H });
pres.layout = "A1P";
pres.title = "Embedded Telemetry with Road-Surface Characterisation and Camera-Based Hazard Detection for the TUKZIE Electric Trike";
pres.author = "Samson Okuthe";
const s = pres.addSlide();
s.background = { color: C.white };

// ---------------- header: campus banner, darkened, with crest, title and names ----------------
const BANNER_H = 7.55;
s.addImage({ path: A("uct_banner.jpg"), x: 0, y: 0, w: W, h: BANNER_H, sizing: { type: "cover", w: W, h: BANNER_H } });
s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: W, h: BANNER_H, fill: { color: "0B1F3F", transparency: 35 }, line: { type: "none" } });
// crest on a white card
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: 0.35, w: 2.45, h: 2.45, rectRadius: 0.2, fill: { color: C.white }, line: { color: C.white } });
s.addImage({ path: A("uct_logo.png"), x: M + 0.12, y: 0.47, w: 2.21, h: 2.21 * 424 / 417, altText: "University of Cape Town crest" });
s.addText([
  { text: "Department of Electrical Engineering, University of Cape Town", options: { bold: true, breakLine: true } },
  { text: "EEE4022S Final Year Project 2026" },
], { x: M + 2.85, y: 0.65, w: W - 2 * M - 2.85, h: 1.85, fontFace: FONT, fontSize: 30, color: C.white, valign: "middle", isTextBox: true, margin: 0 });
s.addText("Embedded Telemetry with Road-Surface Characterisation and Camera-Based Hazard Detection for the TUKZIE Electric Trike", {
  x: M - 0.2, y: 2.95, w: W - 2 * M + 0.4, h: 3.55, fontFace: FONT, fontSize: T.title, bold: true, color: C.white, align: "center", valign: "middle",
  isTextBox: true, margin: 0, lineSpacingMultiple: 0.92, shadow: { type: "outer", color: "000000", blur: 8, offset: 3, angle: 45, opacity: 0.55 },
});
s.addText([
  { text: "Samson Okuthe", options: { bold: true } },
  { text: "   |   Supervisor: A/Prof Simon Winberg   |   Co-supervisor: Sampath Jayalath" },
], { x: M, y: 6.6, w: W - 2 * M, h: 0.7, fontFace: FONT, fontSize: 32, color: C.white, align: "center", valign: "middle", isTextBox: true, margin: 0,
  shadow: { type: "outer", color: "000000", blur: 6, offset: 2, angle: 45, opacity: 0.6 } });

// ---------------- helpers ----------------
function panel(n, title, x, y, w, h) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: C.panel }, line: { color: C.panel }, rectRadius: 0.3 });
  s.addShape(pres.shapes.OVAL, { x: x + 0.4, y: y + 0.35, w: 1.0, h: 1.0, fill: { color: C.navy }, line: { color: C.navy } });
  s.addText(String(n), { x: x + 0.4, y: y + 0.35, w: 1.0, h: 1.0, fontFace: FONT, fontSize: 40, bold: true, color: C.white,
    align: "center", valign: "middle", isTextBox: true, margin: 0 });
  s.addText(title, { x: x + 1.65, y: y + 0.3, w: w - 2.0, h: 1.1, fontFace: FONT, fontSize: T.head, bold: true, color: C.navy,
    valign: "middle", isTextBox: true, margin: 0 });
  return { x: x + 0.5, y: y + 1.65, w: w - 1.0 };   // content box
}
// split "a_w" into a + subscript w, carrying the run options
function rich(text, opts = {}) {
  const parts = text.split("a_w"), runs = [];
  parts.forEach((p, i) => {
    if (p) runs.push({ text: p, options: { ...opts } });
    if (i < parts.length - 1) { runs.push({ text: "a", options: { ...opts } }); runs.push({ text: "w", options: { ...opts, subscript: true } }); }
  });
  return runs;
}
// mark the first run as a bullet and the last as the end of the paragraph
function para(runs, last, extra = {}) {
  runs[0].options = { ...runs[0].options, bullet: { indent: 28 } };
  runs[runs.length - 1].options = { ...runs[runs.length - 1].options, breakLine: !last, paraSpaceAfter: 10, ...extra };
  return runs;
}
function bullets(items, box, h, size = T.body, color = C.text) {
  // items: string, or [boldLead, rest]
  const runs = [];
  items.forEach((it, i) => {
    const last = i === items.length - 1;
    const r = Array.isArray(it) ? [...rich(it[0], { bold: true, color: C.navy }), ...rich(it[1])] : rich(it);
    runs.push(...para(r, last));
  });
  s.addText(runs, { x: box.x, y: box.y, w: box.w, h, fontFace: FONT, fontSize: size, color, valign: "top", isTextBox: true, margin: 0 });
}
function caption(t, x, y, w, h = 0.5, align = "left") {
  s.addText(t, { x, y, w, h, fontFace: FONT, fontSize: T.cap, italic: true, color: C.muted, valign: "top", align, isTextBox: true, margin: 0 });
}
function photo(file, x, y, w, h, alt) {
  s.addImage({ path: file, x, y, w, h, sizing: { type: "cover", w, h }, altText: alt });
  s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { type: "none" }, line: { color: C.white, width: 3 } });
}

const TOP = BANNER_H + 0.55, BOTTOM = H - M;

// ================= left column =================
// 1 Problem and aim
let yL = TOP;
const h1 = 6.6;
let b = panel(1, "Problem and aim", XL, yL, COLW, h1);
{
  const pw = 3.55, ph = pw * 890 / 1070;
  bullets([
    "Electric cargo trikes such as the TUKZIE carry last-mile freight cheaply, but their ride and the roads they use go unmeasured.",
    ["Aim: ", "a low-cost unit that measures the ride at both ends, warns the driver of hazards and keeps its data through coverage gaps."],
  ], { x: b.x, y: b.y, w: b.w - pw - 0.35 }, h1 - 1.9);
  photo(A("road_test_1027.jpg"), b.x + b.w - pw, b.y + 0.05, pw, ph, "The trike on the road test of 27 October 2026, side view");
  caption("Road test, 27 Oct", b.x + b.w - pw, b.y + ph + 0.1, pw, 0.5, "center");
}

// 2 System as driven on 27 October
yL += h1 + GAP;
const h2 = 10.4;
b = panel(2, "System on the trike, 27 Oct", XL, yL, COLW, h2);
{
  const cw = 4.05, ch = 4.15, cy = b.y;
  const side = (x, head, items) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: cy, w: cw, h: ch, rectRadius: 0.15, fill: { color: C.white }, line: { color: C.sky, width: 3 } });
    s.addText(head, { x: x + 0.25, y: cy + 0.15, w: cw - 0.5, h: 0.6, fontFace: FONT, fontSize: 28, bold: true, color: C.navy, valign: "top", isTextBox: true, margin: 0 });
    s.addText(items.map((t, i) => ({ text: t, options: { bullet: { indent: 22 }, breakLine: i < items.length - 1, paraSpaceAfter: 6 } })), {
      x: x + 0.25, y: cy + 0.85, w: cw - 0.4, h: ch - 0.95, fontFace: FONT, fontSize: T.cap, color: C.text, valign: "top", isTextBox: true, margin: 0 });
  };
  side(b.x, "Front: Raspberry Pi 5", [
    "Front camera, detector",
    "Dashboard, 10.1" + NB + "in screen",
    "Front node: ESP32-S3, IMU at 200" + NB + "Hz",
    "Recorder; phone GNSS",
  ]);
  const xr = b.x + b.w - cw;
  side(xr, "Rear: Raspberry Pi 4", [
    "Rear camera, detector",
    "Rear node: ESP32-S3, IMU at 200" + NB + "Hz",
    "Telemetry unit: ESP32-S3 with battery, GNSS and LTE",
  ]);
  const lx = b.x + cw + 0.1, lw = xr - lx - 0.1, ly = cy + ch / 2;
  s.addShape(pres.shapes.LINE, { x: lx, y: ly, w: lw, h: 0, line: { color: C.navy, width: 5, beginArrowType: "triangle", endArrowType: "triangle" } });
  s.addText("Ethernet", { x: lx - 0.2, y: ly - 0.65, w: lw + 0.4, h: 0.5, fontFace: FONT, fontSize: T.cap, bold: true, color: C.navy, align: "center", isTextBox: true, margin: 0 });
  // photos
  const py = cy + ch + 0.35, pg = 0.25, pw = (b.w - 2 * pg) / 3, ph = 3.65;
  photo(R("road1/front_install_1023.jpg"), b.x, py, pw, ph, "Front: Raspberry Pi 5 and front node under the dashboard");
  photo(R("road1/front_camera_1022.jpg"), b.x + pw + pg, py, pw, ph, "Front camera in its printed housing on the frame");
  photo(R("road1/rear_system_1022.jpg"), b.x + 2 * (pw + pg), py, pw, ph, "Rear unit in its printed enclosure on the cargo bed");
  caption("Front computer", b.x, py + ph + 0.08, pw, 0.45, "center");
  caption("Front camera", b.x + pw + pg, py + ph + 0.08, pw, 0.45, "center");
  caption("Rear unit", b.x + 2 * (pw + pg), py + ph + 0.08, pw, 0.45, "center");
}

// 3 Method
yL += h2 + GAP;
const h3 = BOTTOM - yL;
b = panel(3, "Method", XL, yL, COLW, h3);
bullets([
  ["Requirements first: ", "thirteen requirements, each with a criterion fixed before its test; bench tests, then the vehicle."],
  ["Road, 27 Oct: ", "five passes of a smooth loop and four of a rough strip at 10" + NB + "km/h; phone GNSS as the speed reference."],
  ["Analysis: ", "ISO" + NB + "2631-1 weighted vibration a_w per pass; CV over passes (criterion 10" + NB + "%); ICC in 8" + NB + "m cells (0.75); share of the stand-run motor lines in the road spectrum."],
], b, h3 - 1.9);

// ================= right column =================
// 4 Key results
let yR = TOP;
const h4 = 14.4;
b = panel(4, "Key results on the road", XR, yR, COLW, h4);
{
  // chart: a_w smooth vs rough, rear and front
  const chH = 3.75;
  s.addChart(pres.charts.BAR, [
    { name: "Rear", labels: ["Smooth loop (5 passes)", "Rough strip (4 passes)"], values: [1.78, 3.61] },
    { name: "Front", labels: ["Smooth loop (5 passes)", "Rough strip (4 passes)"], values: [1.16, 2.26] },
  ], {
    x: b.x, y: b.y - 0.1, w: b.w, h: chH, barDir: "col", barGapWidthPct: 60,
    chartColors: [C.navy, "5B9BD5"], showLegend: true, legendPos: "r", legendFontSize: 24, legendFontFace: FONT, legendColor: C.text,
    showTitle: true, title: "Mean weighted vibration per pass, 10 km/h (m/s²)", titleFontSize: 26, titleFontFace: FONT, titleColor: C.navy,
    showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 24, dataLabelFontFace: FONT, dataLabelColor: C.text, dataLabelFormatCode: "0.00",
    catAxisLabelFontSize: 24, catAxisLabelFontFace: FONT, catAxisLabelColor: C.text,
    valAxisHidden: true, valAxisMinVal: 0, valAxisMaxVal: 4.4, valGridLine: { style: "none" }, catGridLine: { style: "none" },
    plotArea: { fill: { color: C.panel } }, chartArea: { fill: { color: C.panel } },
  });
  // tiles
  const tiles = [
    ["5.0" + NB + "% / 5.3" + NB + "%", "CV of a_w over 5 passes, rear / front; criterion 10" + NB + "%: met", C.green],
    ["about 2" + NB + "×", "rough strip against the smooth loop, at both ends", C.navy],
    ["ICC 0.16 vs 0.75", "not met: repeats over whole passes, not place by place", C.accent],
    ["0.9 to 3.1" + NB + "%", "of road vibration energy in the motor lines, powered passes", C.navy],
    ["0 gaps", "front IMU at 200" + NB + "Hz; rear 0.08" + NB + "% of samples lost", C.green],
    ["99.9" + NB + "%", "of records over the wired link to the Raspberry Pi 4", C.green],
    ["153 records", "over LTE, 116 replayed after the drop; median 0.44" + NB + "s (n" + NB + "=" + NB + "9)", C.navy],
    ["23.3 / 12.1 fps", "detection, front / rear; median 68" + NB + "/" + NB + "103" + NB + "ms", C.navy],
  ];
  const ty0 = b.y + chH + 0.15, tg = 0.22, tw = (b.w - tg) / 2, th = 1.95;
  tiles.forEach(([big, small, col], i) => {
    const x = b.x + (i % 2) * (tw + tg), y = ty0 + Math.floor(i / 2) * (th + tg);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: tw, h: th, rectRadius: 0.12, fill: { color: C.white }, line: { color: C.white } });
    s.addText(big, { x: x + 0.2, y: y + 0.1, w: tw - 0.4, h: 0.8, fontFace: FONT, fontSize: 42, bold: true, color: col, isTextBox: true, margin: 0, valign: "middle" });
    s.addText(rich(small), { x: x + 0.2, y: y + 0.92, w: tw - 0.35, h: th - 0.97, fontFace: FONT, fontSize: T.cap, color: C.text, valign: "top", isTextBox: true, margin: 0 });
  });
}

// 5 Limitations
yR += h4 + GAP;
const h5 = 4.5;
b = panel(5, "Limitations", XR, yR, COLW, h5);
bullets([
  "One vehicle, two short low-speed sessions; no reference accelerometer, so repeatability, not accuracy.",
  "LTE did not reconnect after 11:51; the vehicle's GNSS lay 8 to 25" + NB + "m from the phone's.",
  "Warnings below ISO" + NB + "15008 legibility; the driver's glance time was not measured.",
], b, h5 - 1.75, T.small);

// 6 Conclusion and QR code
yR += h5 + GAP;
const h6 = BOTTOM - yR;
b = panel(6, "Conclusion", XR, yR, COLW, h6);
{
  const qr = 2.55;
  bullets([
    "The unit ran on the trike; its ride reading repeats over whole passes, separates two surfaces and is dominated by the road.",
    "Next: own supply, larger warnings, glance time.",
  ], { x: b.x, y: b.y, w: b.w - qr - 0.95 }, h6 - 1.8, T.small);
  const qx = b.x + b.w - qr, qy = yR + 0.35;
  s.addShape(pres.shapes.RECTANGLE, { x: qx, y: qy, w: qr, h: qr, fill: { color: C.white }, line: { color: C.white } });
  s.addImage({ path: A("qr_tuksense.png"), x: qx + 0.1, y: qy + 0.1, w: qr - 0.2, h: qr - 0.2, altText: "QR code to https://tuksense.site" });
  s.addText([
    { text: "Videos of the system on the road", options: { bold: true, breakLine: true } },
    { text: "tuksense.site" },
  ], { x: qx - 0.9, y: qy + qr + 0.08, w: qr + 1.0, h: 0.85, fontFace: FONT, fontSize: T.cap, color: C.navy, align: "center", valign: "top", isTextBox: true, margin: 0 });
}

const out = process.argv[2] || path.join(__dirname, "..", "SW7_Poster_A1.pptx");
pres.writeFile({ fileName: out }).then((f) => console.log("wrote", f));
