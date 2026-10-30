// Final presentation (oral exam, 16 or 17 Nov 2026: 10-minute talk, 5 minutes of questions), 16:9,
// matching the A1 poster (UCT banner, navy numbered markers, light-blue cards).
// Also writes Presentation/SW7_Talking_Points.md from the speaker notes, so the script always matches the deck.
// Rewritten 30 Oct 2026 after the report was submitted: 13 slides, road-test results of 27 Oct, no project code on
// the slides. Every number is taken from the submitted report (Results Table 5.3, Discussion, Conclusions,
// Recommendations) or BenchTest/logs/run2_road_2026-10-27/analysis/run2_summary_numbers.txt.
const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");
const A = (f) => path.join(__dirname, "assets", f);
const R = (f) => path.join(__dirname, "..", "..", "Report", "figures", f);   // report figures, used as they are

const C = {
  navy: "14305C", sky: "1565C0", panel: "E8F0FA", accent: "B85C00",
  text: "1B1F24", muted: "4A5566", white: "FFFFFF", line: "C9D6E8",
};
const FONT = "Calibri";
const W = 13.333, H = 7.5, M = 0.6;
const BOTTOM = 6.75;   // lowest edge of slide content; the footer sits below it

// Exact title of the submitted report. Keep TITLE the same in build_poster.js.
const TITLE = "Embedded Telemetry with Road-Surface Characterisation\nand Camera-Based Hazard Detection\nfor the TUKZIE Electric Trike";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = TITLE.replace(/\n/g, " ");
pres.author = "Samson Okuthe";

let slideNo = 0;
const script = [];   // [slide number, title, notes] for the talking points

function txt(s, t, o) { s.addText(t, Object.assign({ fontFace: FONT, color: C.text, isTextBox: true, margin: 0 }, o)); }
function card(s, x, y, w, h, fill = C.panel, line) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: fill }, line: line || { color: fill } });
}
function dashedCard(s, x, y, w, h) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: C.white }, line: { color: C.accent, width: 2, dashType: "dash" } });
}
function bullets(s, items, o) {
  s.addText(items.map((t, i) => ({ text: t, options: { bullet: { indent: 18 }, breakLine: i < items.length - 1, paraSpaceAfter: 6 } })),
    Object.assign({ fontFace: FONT, fontSize: 16, color: C.text, valign: "top", isTextBox: true, margin: 0 }, o));
}
function caption(s, t, x, y, w, h = 0.3) { txt(s, t, { x, y, w, h, fontSize: 12, italic: true, color: C.muted, valign: "top" }); }
// picture scaled to fit inside the box (x, y, w, h), centred; ar = width / height of the file
function fit(s, file, ar, x, y, w, h, o = {}) {
  let iw = w, ih = w / ar; if (ih > h) { ih = h; iw = h * ar; }
  s.addImage(Object.assign({ path: file, x: x + (w - iw) / 2, y: y + (h - ih) / 2, w: iw, h: ih }, o));
  return { x: x + (w - iw) / 2, y: y + (h - ih) / 2, w: iw, h: ih };
}
// rounded status label
function pill(s, x, y, w, h, label, style) {
  const open = style === "open", col = style === "met" ? C.sky : open ? C.accent : C.navy;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: h / 2,
    fill: { color: open ? C.white : col }, line: { color: col, width: 1.5, dashType: open ? "dash" : "solid" } });
  txt(s, label, { x, y, w, h, fontSize: 14, bold: true, color: open ? C.accent : C.white, align: "center", valign: "middle" });
}
// big number with a short label underneath, on a card
function stat(s, x, y, w, h, big, small, o = {}) {
  if (o.dashed) dashedCard(s, x, y, w, h); else card(s, x, y, w, h, o.fill || C.panel);
  const bh = o.bigH || 0.62;
  txt(s, big, { x: x + 0.22, y: y + 0.12, w: w - 0.44, h: bh, fontSize: o.bigSize || 30, bold: true, color: o.dashed ? C.accent : (o.bigColor || C.navy), valign: "middle" });
  txt(s, small, { x: x + 0.22, y: y + 0.16 + bh, w: w - 0.44, h: h - bh - 0.24, fontSize: o.size || 14, valign: "top" });
}
// card with a bold heading and a body text
function infoCard(s, x, y, w, h, head, body, o = {}) {
  if (o.dashed) dashedCard(s, x, y, w, h); else card(s, x, y, w, h);
  txt(s, head, { x: x + 0.22, y: y + 0.12, w: w - 0.44, h: 0.36, fontSize: 16, bold: true, color: o.dashed ? C.accent : C.navy });
  txt(s, body, { x: x + 0.22, y: y + 0.52, w: w - 0.44, h: h - 0.6, fontSize: o.size || 14, valign: "top" });
}

// content slide: navy numbered marker + title, footer with crest and slide number
function content(title, notes) {
  const s = pres.addSlide();
  slideNo++;
  s.background = { color: C.white };
  s.addShape(pres.shapes.OVAL, { x: M, y: 0.42, w: 0.62, h: 0.62, fill: { color: C.navy }, line: { color: C.navy } });
  txt(s, String(slideNo - 1), { x: M, y: 0.42, w: 0.62, h: 0.62, fontSize: 20, bold: true, color: C.white, align: "center", valign: "middle" });
  txt(s, title, { x: M + 0.85, y: 0.34, w: W - 2 * M - 0.85, h: 0.8, fontSize: 30, bold: true, color: C.navy, valign: "middle" });
  s.addImage({ path: A("uct_logo.png"), x: W - M - 0.42, y: H - 0.58, w: 0.42, h: 0.427 });
  txt(s, "Samson Okuthe   |   EEE4022S 2026   |   UCT", { x: M, y: H - 0.52, w: 6, h: 0.32, fontSize: 11, color: C.muted, valign: "middle" });
  txt(s, String(slideNo), { x: W - M - 1.6, y: H - 0.52, w: 1.0, h: 0.32, fontSize: 11, color: C.muted, align: "right", valign: "middle" });
  s.addNotes(notes);
  script.push([slideNo, title, notes]);
  return s;
}

// ---------------- 1 Title ----------------
{
  const s = pres.addSlide();
  slideNo++;
  const notes = "Good morning. I'm Samson Okuthe. My project gives the TUKZIE electric cargo trike embedded telemetry: " +
    "it measures how the trike rides, warns the driver of hazards on the dashboard it already has, and keeps its data when coverage drops. " +
    "I was supervised by Associate Professor Simon Winberg, with Sampath Jayalath as co-supervisor.";
  s.background = { color: C.navy };
  s.addImage({ path: A("uct_banner.jpg"), x: 0, y: 0, w: W, h: H, sizing: { type: "cover", w: W, h: H } });
  const px = M, py = 0.35, pw = W - 2 * M, ph = 3.7;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: px, y: py, w: pw, h: ph, rectRadius: 0.15, fill: { color: C.navy, transparency: 18 }, line: { color: C.navy, transparency: 18 } });
  // crest on a white tile so it reads on the navy panel
  card(s, px + 0.35, py + 0.35, 1.1, 1.1, C.white);
  s.addImage({ path: A("uct_logo.png"), x: px + 0.45, y: py + 0.44, w: 0.9, h: 0.9 * 424 / 417 });
  const tx = px + 1.55, tw = pw - 3.1;
  // same words as TITLE, broken so that no line overflows at this size
  txt(s, "Embedded Telemetry with Road-Surface\nCharacterisation and Camera-Based Hazard Detection\nfor the TUKZIE Electric Trike", { x: tx, y: py + 0.2, w: tw, h: 1.75, fontSize: 27, bold: true, color: C.white, align: "center", valign: "middle" });
  txt(s, "Samson Okuthe", { x: tx, y: py + 2.05, w: tw, h: 0.45, fontSize: 22, bold: true, color: C.white, align: "center" });
  txt(s, "Supervisor: A/Prof Simon Winberg   |   Co-supervisor: Sampath Jayalath",
    { x: tx, y: py + 2.55, w: tw, h: 0.38, fontSize: 16, color: C.white, align: "center" });
  txt(s, "Department of Electrical Engineering, University of Cape Town   |   EEE4022S Final Year Project, 2026",
    { x: px + 0.4, y: py + 3.0, w: pw - 0.8, h: 0.38, fontSize: 15, color: C.white, align: "center" });
  s.addNotes(notes);
  script.push([slideNo, "Title", notes]);
}

// ---------------- 2 Why ----------------
{
  const s = content("Why this matters",
    "Electric cargo trikes make sense for freight in African cities: in Dar es Salaam an electric cargo tricycle cost 45.5 percent less per kilometre to run than a motorcycle, and 86 percent less than a light car. " +
    "But anything that takes the driver's eyes off the road is a risk; NHTSA guidance wants glances away from the road to mostly last two seconds or less. " +
    "So the problem is to put edge telemetry and short, safety-only alerts on a low-cost trike, and to measure whether each part works. ");
  const ph = 4.85, pw = ph * 1080 / 930;
  s.addImage({ path: A("road_test_1027.jpg"), x: M, y: 1.4, w: pw, h: ph });
  caption(s, "The TUKZIE Rev 0 on the road test, 27 October 2026", M, 1.4 + ph + 0.08, pw);
  const rx = M + pw + 0.45, rw = W - M - rx;
  stat(s, rx, 1.4, rw, 1.75, "45.5 to 86 %", "lower running cost per km for an electric cargo tricycle than a motorcycle or a light car, Dar es Salaam (Sebwa et al., 2025)", { bigSize: 36, size: 15 });
  stat(s, rx, 3.45, rw, 1.75, "2 s", "glances away from the road should mostly last 2 s or less (NHTSA, 2013), so alerts must be short and safety-only", { bigSize: 36, size: 15 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: rx, y: 5.5, w: rw, h: BOTTOM - 5.5, rectRadius: 0.12, fill: { color: C.white }, line: { color: C.sky, width: 1.5 } });
  txt(s, [{ text: "The problem: ", options: { bold: true, color: C.navy } },
          { text: "edge telemetry and sparse, safety-only alerts together on a low-cost electric trike, with each part measured." }],
    { x: rx + 0.25, y: 5.5, w: rw - 0.5, h: BOTTOM - 5.5, fontSize: 16, valign: "middle" });
}

// ---------------- 3 Aim and research questions ----------------
{
  const s = content("Aim, research questions and approach",
    "The aim is on the slide. Four research questions follow from it: how accurately and repeatably the ride can be measured; how alerts should appear with the least distraction; what latency, loss and recovery the data chain achieves; and which features separate road from powertrain vibration. " +
    "The approach was a V-model: thirteen requirements with criteria fixed before each test, every part tested on the bench, then on the vehicle on 19 and 27 October.");
  card(s, M, 1.4, W - 2 * M, 0.9);
  txt(s, [{ text: "Aim: ", options: { bold: true, color: C.navy } },
          { text: "measure the trike's response to the road and its powertrain, warn of hazards on the existing dashboard, and keep the data through gaps in coverage." }],
    { x: M + 0.3, y: 1.4, w: W - 2 * M - 0.6, h: 0.9, fontSize: 17, valign: "middle" });
  const rows = [
    ["RQ1", "How accurately and repeatably can a low-cost edge unit characterise the trike's ride?"],
    ["RQ2", "How should safety alerts appear on the existing dashboard with the least distraction?"],
    ["RQ3", "What latency, data loss and recovery from sensor to the LTE database?"],
    ["RQ4", "Which features separate road vibration from powertrain vibration?"],
  ];
  const y0 = 2.6, rh = 0.92, gap = 0.16, lw = 8.0;
  rows.forEach(([id, q], i) => {
    const y = y0 + i * (rh + gap);
    card(s, M, y, lw, rh);
    txt(s, id, { x: M + 0.25, y, w: 0.9, h: rh, fontSize: 22, bold: true, color: C.navy, valign: "middle" });
    txt(s, q, { x: M + 1.2, y, w: lw - 1.45, h: rh, fontSize: 17, valign: "middle" });
  });
  const ax = M + lw + 0.4, aw = W - M - ax;
  txt(s, "Approach", { x: ax, y: y0, w: aw, h: 0.4, fontSize: 18, bold: true, color: C.navy });
  const steps = [["13 requirements", "criterion fixed before each test"], ["Bench", "each part tested before the next"], ["Vehicle", "road sessions, 19 and 27 Oct"]];
  const sh = 0.95, sg = 0.33;
  steps.forEach(([h, b], i) => {
    const y = y0 + 0.5 + i * (sh + sg);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: ax, y, w: aw, h: sh, rectRadius: 0.1, fill: { color: i === 2 ? C.navy : C.white }, line: { color: C.navy, width: 1.5 } });
    txt(s, h, { x: ax + 0.2, y: y + 0.08, w: aw - 0.4, h: 0.4, fontSize: 17, bold: true, color: i === 2 ? C.white : C.navy, align: "center" });
    txt(s, b, { x: ax + 0.2, y: y + 0.47, w: aw - 0.4, h: 0.4, fontSize: 14, color: i === 2 ? C.white : C.text, align: "center" });
    if (i < 2) s.addShape(pres.shapes.LINE, { x: ax + aw / 2, y: y + sh, w: 0, h: sg, line: { color: C.navy, width: 2, endArrowType: "triangle" } });
  });
}

// ---------------- 4 System as driven ----------------
{
  const s = content("The system as driven on 27 October",
    "This is the system as driven on 27 October. It has two sides joined by one Ethernet cable, which also shares the clock. " +
    "At the front, a Raspberry Pi 5 behind the display runs the dashboard, the front camera and detector, three time-of-flight sensors and the front IMU node; a phone streams its GNSS for speed. " +
    "At the rear, a Raspberry Pi 4 beside the battery runs the rear camera and reads two boards: the rear IMU node, and the telemetry unit, which reads the battery, GNSS and LTE and logs to flash. " +
    "So there are three ESP32-S3 boards. Run from a portable power station, the whole system drew 27 watts at its output.");
  const pw = 2.7, ph = 3.6, py = 1.4;
  s.addImage({ path: R("road1/front_camera_1022.jpg"), x: M, y: py, w: pw, h: ph });
  caption(s, "Front camera in its printed case on the frame (22 Oct)", M, py + ph + 0.08, pw, 0.55);
  const rpx = W - M - pw;
  s.addImage({ path: R("road1/rear_system_1022.jpg"), x: rpx, y: py, w: pw, h: ph });
  caption(s, "Rear enclosure on the deck: Pi 4, antennas, camera (22 Oct)", rpx, py + ph + 0.08, pw, 0.55);
  const cx = M + pw + 0.35, cw = rpx - 0.35 - cx;
  const box = (y, h, head, items) => {
    card(s, cx, y, cw, h);
    txt(s, head, { x: cx + 0.25, y: y + 0.12, w: cw - 0.5, h: 0.38, fontSize: 17, bold: true, color: C.navy });
    bullets(s, items, { x: cx + 0.25, y: y + 0.55, w: cw - 0.5, h: h - 0.62, fontSize: 15, paraSpaceAfter: 2 });
  };
  box(1.4, 1.95, "Front: Raspberry Pi 5, behind the display", [
    "Dashboard on the 10.1 in touchscreen",
    "Front camera, detector, 3 time-of-flight sensors",
    "Front IMU node (ESP32-S3, 200 Hz)",
    "Phone GNSS over its hotspot, for speed",
  ]);
  const ly = 3.35, lh = 0.62;
  s.addShape(pres.shapes.LINE, { x: cx + 1.0, y: ly + 0.04, w: 0, h: lh - 0.08, line: { color: C.navy, width: 3, beginArrowType: "triangle", endArrowType: "triangle" } });
  txt(s, "Ethernet, 1000 Mb/s, one shared clock", { x: cx + 1.3, y: ly, w: cw - 1.3, h: lh, fontSize: 15, bold: true, color: C.navy, valign: "middle" });
  box(ly + lh, 2.05, "Rear: Raspberry Pi 4, beside the battery", [
    "Rear camera, detector, 3 time-of-flight sensors",
    "Rear IMU node (ESP32-S3, 200 Hz)",
    "Telemetry unit (ESP32-S3): battery, GNSS, LTE, log",
  ]);
  const by = 6.15;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: by, w: W - 2 * M, h: BOTTOM - by, rectRadius: 0.1, fill: { color: C.white }, line: { color: C.sky, width: 1.5 } });
  txt(s, [{ text: "Three ESP32-S3 boards", options: { bold: true, color: C.navy } }, { text: " hold the fixed-rate sensing; the Pis run the cameras.   " },
          { text: "27 W", options: { bold: true, color: C.navy } }, { text: " whole system, measured at the EcoFlow output." }],
    { x: M + 0.3, y: by, w: W - 2 * M - 0.6, h: BOTTOM - by, fontSize: 15, valign: "middle" });
}

// ---------------- 5 Deterministic acquisition ----------------
{
  const s = content("Deterministic acquisition: a 33 to 44 ms gap found and removed",
    "Ride measurement needs a fixed sample rate. Under FreeRTOS the IMU task runs at top priority on a 5 millisecond period and never blocks: if its queue is full, the sample is dropped and counted. " +
    "Counting exposed the one timing fault. Every flash write paused reading for 33 to 44 milliseconds, the spikes in this plot. Buffering made the pauses rarer, not shorter. " +
    "The fix was to take logging off the IMU nodes: on the vehicle they held 200 hertz with no interval over 5.2 milliseconds. " +
    "On the road the front node lost nothing in 1.8 million samples; the rear lost 0.08 percent in transport, none at the node.");
  const fw = 6.55, fh = fw * 761 / 1234;
  s.addImage({ path: R("results/imu_write_gaps.png"), x: M, y: 1.4, w: fw, h: fh });
  caption(s, "Bench: longest interval between IMU samples in each 2 s window. (a) writing to flash every 10 s; (b) buffered writes. Nominal interval 5 ms.",
    M, 1.4 + fh + 0.08, fw, 0.6);
  const rx = M + fw + 0.4, rw = W - M - rx;
  infoCard(s, rx, 1.4, rw, 1.5, "Design: timing where it is predictable",
    "FreeRTOS on an ESP32-S3: IMU task at top priority, 5 ms period. Bounded queue: drop and count, never block.");
  infoCard(s, rx, 3.15, rw, 1.5, "Fix: no flash log on the IMU nodes",
    "On the vehicle both held 200.00 Hz with no interval over 5.2 ms (about 35,000 samples at rest).");
  const tw = (rw - 0.3) / 2, ty = 4.9, th = BOTTOM - ty;
  stat(s, rx, ty, tw, th, "0 gaps", "front node on the road: 1,791,190 samples", { bigSize: 28 });
  stat(s, rx + tw + 0.3, ty, tw, th, "0.08 %", "rear lost in transport on the road; the node dropped none", { bigSize: 28 });
}

// ---------------- 6 Fault investigations ----------------
{
  const s = content("Fault investigations: symptom, test, cause, fix",
    "Because each stage was tested before the next, each fault could be traced to one change. The one that mattered most is power. " +
    "The Pi 4 kept throttling and restarting. Logging its power flags every two seconds showed under-voltage starting fourteen seconds after the telemetry unit's modem came up on its USB port. Moved off, it went from three restarts in twenty minutes to none in four hours. " +
    "The others: a task stall hidden behind a healthy-looking rate, a dead sensor connection that led to the third board, a flash-mode boot loop, a battery checksum off by three, and invalid JSON found only by reading the log back.");
  const items = [
    ["Pi 4 under-voltage, restarts", "Power flags every 2 s: under-voltage began 14 s after the modem on its USB port came up. Moved off: 3 restarts in 20 min, then none in 4 h. It needs a regulated supply.", true],
    ["IMU stall (21 to 22 Oct)", "Drop counts rose while the rate still read 200 Hz. Cause: statistics and ride tasks starved on the IMU core. Moved in v0.7.6; a 62-minute soak had no drops."],
    ["Rear IMU lost (26 Oct)", "No device at 0x68 on the telemetry unit: wiring or module supply open. The sensor worked on a second ESP32-S3, which became the rear IMU node."],
    ["Boot loop at full flash", "Reset at a fixed address after enabling 16 MB flash. Cause: quad mode asked for, the chip runs dual (DIO). Fix: size, mode and partition table set together."],
    ["Battery checksum", "Every frame rejected. The firmware's own query frame showed the rule: the register byte was left out, so replies failed by 3. Fixed: 74.78 V read."],
    ["Invalid JSON in the log", "5,545 of 6,020 records failed to parse. A length-checked read-back showed the transfer intact; cause: nan for missing values. Fix: null; all parse."],
  ];
  const n = 3, g = 0.3, cw = (W - 2 * M - (n - 1) * g) / n, ch = 2.5, gy = 0.3;
  items.forEach(([h, b, key], i) => {
    const x = M + (i % n) * (cw + g), y = 1.4 + Math.floor(i / n) * (ch + gy);
    infoCard(s, x, y, cw, ch, h, b, { dashed: !!key, size: 16 });
  });
}

// ---------------- 7 Telemetry and store-and-forward ----------------
{
  const s = content("Telemetry: log first, then store and forward",
    "Every record is written to flash whatever the coverage, then sent over LTE and replayed when the link returns. " +
    "On the bench I switched the radio off for ten minutes. The unit reconnected 5.2 seconds after it came back, cleared its 60-record backlog in about 38 seconds, and the database held 112 of 112 records, none missing or doubled. " +
    "On the road the wired link to the Pi carried 4,196 of 4,201 records, 99.9 percent, against 62 percent over USB on the first session. " +
    "Over LTE 153 records arrived, 116 of them replays, with a median delay of 0.44 seconds; but only nine records carry that figure, and from 11:51 the link did not reconnect.");
  const lw = 6.95, top = 1.4, hgt = BOTTOM - top;
  card(s, M, top, lw, hgt);
  txt(s, "Bench: 10-minute LTE outage", { x: M + 0.25, y: top + 0.12, w: lw - 0.5, h: 0.38, fontSize: 17, bold: true, color: C.navy });
  const fw = lw - 0.5, fh = fw * 458 / 1217;
  s.addImage({ path: R("results/t15_outage_backlog.png"), x: M + 0.25, y: top + 0.6, w: fw, h: fh });
  const sy = top + 0.6 + fh + 0.25, sw = (fw - 0.4) / 3, shh = BOTTOM - 0.2 - sy;
  [["5.2 s", "to reconnect after the radio returned"], ["38 s", "to clear the 60-record backlog"], ["112 / 112", "records stored, none missing or doubled"]]
    .forEach(([b, t], i) => stat(s, M + 0.25 + i * (sw + 0.2), sy, sw, shh, b, t, { fill: C.white, bigSize: 26, bigH: 0.5 }));
  const rx = M + lw + 0.35, rw = W - M - rx;
  card(s, rx, top, rw, hgt);
  txt(s, "Road, 27 October", { x: rx + 0.25, y: top + 0.12, w: rw - 0.5, h: 0.38, fontSize: 17, bold: true, color: C.navy });
  const rows = [["99.9 %", "4,196 of 4,201 records over the wired link (62 % over USB, 19 Oct)"],
                ["153", "records over LTE, 116 of them replayed from the backlog"],
                ["0.44 s", "median delay from stamp to database (n = 9)"]];
  const r0 = top + 0.6, rrh = 1.2;
  rows.forEach(([b, t], i) => {
    const y = r0 + i * (rrh + 0.1);
    txt(s, b, { x: rx + 0.25, y, w: 1.75, h: 0.55, fontSize: 28, bold: true, color: C.navy, valign: "middle" });
    txt(s, t, { x: rx + 2.05, y, w: rw - 2.3, h: rrh, fontSize: 14, valign: "top" });
  });
  const ny = r0 + 3 * (rrh + 0.1) + 0.05;
  dashedCard(s, rx + 0.25, ny, rw - 0.5, BOTTOM - 0.2 - ny);
  txt(s, "From 11:51 the LTE link did not reconnect; the rest stayed in the unit's log.",
    { x: rx + 0.45, y: ny, w: rw - 0.9, h: BOTTOM - 0.2 - ny, fontSize: 14, bold: true, color: C.accent, valign: "middle" });
}

// ---------------- 8 Hazard detection ----------------
{
  const s = content("Hazard detection on the road: front and rear",
    "Each camera runs a pretrained 8-bit SSD-MobileNet detector. On the road the front, on the Pi 5, took a median of 68 milliseconds from readout to result at 23.3 frames per second; the rear, on the Pi 4, 103 milliseconds at 12.1. " +
    "An alert is raised after three frames and cleared after five, and no frame is ever stored. " +
    "Distance bands do not say whether something is closing, so the system also estimates time to contact from how fast a box grows; it is within 2 percent in 40 synthetic tests but has not met a real approach. " +
    "No forward video was kept, so how many road alerts were correct is still unknown.");
  const iw = 6.3, ih = iw * 800 / 1280;
  s.addImage({ path: R("ui/ui_dualcam_rear_approaching.png"), x: M, y: 1.4, w: iw, h: ih });
  caption(s, "Dashboard, rear view mirrored, with an approaching-object warning (test image)", M, 1.4 + ih + 0.08, iw);
  const ty = 1.4 + ih + 0.5;
  card(s, M, ty, iw, BOTTOM - ty);
  txt(s, [{ text: "Time to contact ", options: { bold: true, color: C.navy } },
          { text: "from box growth, τ = w / (dw/dt): within 2 % in 40 synthetic tests; no real approach yet." }],
    { x: M + 0.25, y: ty, w: iw - 0.5, h: BOTTOM - ty, fontSize: 15, valign: "middle" });
  const rx = M + iw + 0.4, rw = W - M - rx, tw = (rw - 0.3) / 2;
  stat(s, rx, 1.4, tw, 2.05, "68 ms", "front, Pi 5: median on the road, 23.3 fps (bench 51 to 54 ms)", { bigSize: 34, bigH: 0.7 });
  stat(s, rx + tw + 0.3, 1.4, tw, 2.05, "103 ms", "rear, Pi 4: median on the road, 12.1 fps (bench 118 to 122 ms)", { bigSize: 34, bigH: 0.7 });
  infoCard(s, rx, 3.75, rw, 1.25, "Alert logic and privacy", "Raised after 3 frames, cleared after 5. No frame is ever stored.");
  infoCard(s, rx, 5.3, rw, BOTTOM - 5.3, "Not yet checked",
    "No forward video kept, so road precision is unknown. Fused range 0.47 m at about 0.5 m on a person (n = 43); a flat-target check is needed.", { dashed: true });
}

// ---------------- 9 Dashboard ----------------
{
  const s = content("The existing dashboard: live alerts, honest legibility",
    "RQ2 lands on the dashboard the team already runs, here on the vehicle. It shows only live data, never a simulated value, and an immediate hazard appears as a banner over every page. " +
    "Glance time needs a participant and an ethics amendment, so it was not tested; but legibility needs neither, so I measured it at the driver's eye distance of 0.62 metres. " +
    "The speed digits subtend 94 arc minutes, far above the 20 that ISO 15008 recommends. The alert banner subtends 10, below even its minimum of 12. So the hierarchy is inverted: the warnings must be enlarged before any glance study. " +
    "Spoken commands work offline, 15 to 18 of 18 on the bench, but no driver was tested.");
  const ph = 4.55, pw = ph * 478 / 850;
  s.addImage({ path: R("road1/vid_dash_drive.jpg"), x: M, y: 1.4, w: pw, h: ph });
  caption(s, "On the vehicle: the driving page", M, 1.4 + ph + 0.08, pw, 0.55);
  const mx = M + pw + 0.35, mw = 5.3, mh = mw * 800 / 1280;
  s.addImage({ path: R("ui/ui_pi5_live_drive.png"), x: mx, y: 1.4, w: mw, h: mh });
  caption(s, "Live on the Pi 5: an obstacle banner over the driving page; absent data shown as absent", mx, 1.4 + mh + 0.08, mw, 0.55);
  const vy = 1.4 + mh + 0.75;
  infoCard(s, mx, vy, mw, BOTTOM - vy, "Voice commands, offline",
    "15 to 18 of 18 synthetic-voice commands on the bench, in 1.8 to 2.4 s; alerts and battery read out on request. No driver tested.");
  const rx = mx + mw + 0.35, rw = W - M - rx;
  card(s, rx, 1.4, rw, BOTTOM - 1.4);
  txt(s, "Legibility at 0.62 m (ISO 15008)", { x: rx + 0.22, y: 1.52, w: rw - 0.44, h: 0.62, fontSize: 16, bold: true, color: C.navy, valign: "top" });
  txt(s, "94 arc min", { x: rx + 0.22, y: 2.2, w: rw - 0.44, h: 0.55, fontSize: 28, bold: true, color: C.sky, valign: "middle" });
  txt(s, "speed digits; 20 recommended", { x: rx + 0.22, y: 2.75, w: rw - 0.44, h: 0.35, fontSize: 14 });
  txt(s, "10 arc min", { x: rx + 0.22, y: 3.3, w: rw - 0.44, h: 0.55, fontSize: 28, bold: true, color: C.accent, valign: "middle" });
  txt(s, "alert banner; below the minimum of 12. Only 4 of 110 labels reach the acceptable 16.", { x: rx + 0.22, y: 3.85, w: rw - 0.44, h: 0.95, fontSize: 14, valign: "top" });
  txt(s, "The speed is legible at a glance; the warnings are not. Enlarge them first, then a glance study (R12, not tested: needs a participant).",
    { x: rx + 0.22, y: 5.0, w: rw - 0.44, h: BOTTOM - 5.1, fontSize: 14, bold: true, color: C.navy, valign: "top" });
}

// ---------------- 10 Road test ----------------
{
  const s = content("Road test, 27 October: repeatable per pass, not per place",
    "This is the main road result. On a smooth loop at 10 kilometres an hour, five passes gave a weighted acceleration, a w, that varied by 5.0 percent at the rear and 5.3 at the front, inside the 10 percent criterion. " +
    "On a rougher strip it read about twice as high at the same speed, so the measurement responds to the road. " +
    "But aligned by position in 8 metre cells, the passes did not agree place by place: an ICC of 0.16, at most 0.32 in the sensitivity checks, against 0.75. With one-second phone positions I cannot separate this from the line each lap took. " +
    "The speed index also rose with speed, so it is not speed-invariant here.");
  const cw = 3.95, g = 0.3, top = 1.4, chH = 3.75;
  const chartBase = {
    catAxisLabelFontSize: 14, catAxisLabelColor: C.text, catAxisLabelFontFace: FONT,
    valAxisLabelFontSize: 12, valAxisLabelColor: C.muted, valAxisLabelFontFace: FONT,
    valGridLine: { color: "C9D6E8", size: 0.75 }, catGridLine: { style: "none" },
    showTitle: true, titleFontSize: 14, titleColor: C.navy, titleFontFace: FONT,
    dataLabelFontSize: 13, dataLabelColor: C.text, dataLabelFontFace: FONT,
  };
  // chart 1: CV of a_w on the smooth loop, with the 10 % criterion
  card(s, M, top, cw, chH, C.white, { color: C.line, width: 1 });
  s.addChart([
    { type: pres.charts.BAR, data: [{ name: "CV of a_w (%)", labels: ["Rear", "Front"], values: [5.0, 5.3] }],
      options: { chartColors: [C.sky], barGapWidthPct: 70, showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.0" } },
    { type: pres.charts.LINE, data: [{ name: "Criterion 10 %", labels: ["Rear", "Front"], values: [10, 10] }],
      options: { chartColors: [C.accent], lineSize: 2, lineDash: "dash", lineDataSymbol: "none", showValue: false } },
  ], Object.assign({}, chartBase, {
    x: M + 0.1, y: top + 0.1, w: cw - 0.2, h: chH - 0.2, barDir: "col",
    title: "CV of a_w, smooth loop (%)",
    valAxisMinVal: 0, valAxisMaxVal: 12, valAxisMajorUnit: 2,
    showLegend: true, legendPos: "b", legendFontSize: 12, legendFontFace: FONT, legendColor: C.text,
  }));
  pill(s, M + 0.2, top + chH + 0.18, cw - 0.4, 0.5, "Met at both ends", "met");
  // chart 2: a_w smooth against rough
  const x2 = M + cw + g;
  card(s, x2, top, cw, chH, C.white, { color: C.line, width: 1 });
  s.addChart(pres.charts.BAR, [
    { name: "Smooth loop", labels: ["Rear", "Front"], values: [1.78, 1.16] },
    { name: "Rough strip", labels: ["Rear", "Front"], values: [3.61, 2.26] },
  ], Object.assign({}, chartBase, {
    x: x2 + 0.1, y: top + 0.1, w: cw - 0.2, h: chH - 0.2, barDir: "col", barGrouping: "clustered",
    title: "a_w at 10 km/h (m/s²)", chartColors: [C.sky, C.navy], barGapWidthPct: 60,
    valAxisMinVal: 0, valAxisMaxVal: 4, valAxisMajorUnit: 1,
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.00",
    showLegend: true, legendPos: "b", legendFontSize: 12, legendFontFace: FONT, legendColor: C.text,
  }));
  pill(s, x2 + 0.2, top + chH + 0.18, cw - 0.4, 0.5, "About twice: separates surfaces", "part");
  // ICC verdict and speed index
  const x3 = x2 + cw + g, w3 = W - M - x3;
  dashedCard(s, x3, top, w3, 2.75);
  txt(s, "Place by place: not met", { x: x3 + 0.22, y: top + 0.12, w: w3 - 0.44, h: 0.38, fontSize: 16, bold: true, color: C.accent });
  txt(s, "ICC 0.16", { x: x3 + 0.22, y: top + 0.55, w: w3 - 0.44, h: 0.7, fontSize: 36, bold: true, color: C.accent, valign: "middle" });
  txt(s, "at most 0.32 in sensitivity checks, against 0.75. Whole passes repeat; place by place they do not.",
    { x: x3 + 0.22, y: top + 1.3, w: w3 - 0.44, h: 1.35, fontSize: 14, valign: "top" });
  const iy = top + 2.75 + 0.3;
  infoCard(s, x3, iy, w3, top + chH + 0.68 - iy, "Speed index I_v rose with speed",
    "Rear 1.14, 1.59, 2.44 at about 10, 13, 18 km/h: not speed-invariant.");
  txt(s, "Laps 11:30 to 12:40; speed from the phone's GNSS; passes found from speed and current, no section markers or video. Only 2 passes at 15 km/h and 1 at 20 km/h. Battery peaked at 82.9 A.",
    { x: M, y: 6.0, w: W - 2 * M, h: BOTTOM - 6.0, fontSize: 13, italic: true, color: C.muted, valign: "middle" });
}

// ---------------- 11 Powertrain against road ----------------
{
  const s = content("Powertrain against road: the road dominates",
    "RQ4 asks what is road and what is powertrain. With the drive wheel raised on stands, the motor shook the body between about 40 and 70 hertz, with the same lines at the front as at the rear, so the front sensor does not escape it. " +
    "On the road, those lines held only 0.9 to 3.1 percent of the energy in powered passes, while 65 to 84 percent lay between 4 and 8 hertz, the body's response to the road. " +
    "A coasting pass gave the same reading as a powered one, 1.80 against 1.78. " +
    "So at these low speeds the road dominates; at higher power the motor's share would grow.");
  const fw = 7.45, fh = fw * 396 / 1100;
  s.addImage({ path: R("results/stand_spectra_1023.png"), x: M, y: 1.4, w: fw, h: fh });
  caption(s, "Stands, 23 Oct, drive wheel raised: rear vibration 5 to 7 times rest, energy 40 to 70 Hz; the same lines at the front (42.75, 49.0, 64.0 Hz).",
    M, 1.4 + fh + 0.08, fw, 0.6);
  const vy = 1.4 + fh + 0.85;
  card(s, M, vy, fw, BOTTOM - vy, C.navy);
  txt(s, "At these speeds the road dominates the measured vibration; at higher power the 40 to 70 Hz energy of the stand runs would weigh more.",
    { x: M + 0.3, y: vy, w: fw - 0.6, h: BOTTOM - vy, fontSize: 18, bold: true, color: C.white, valign: "middle" });
  const rx = M + fw + 0.35, rw = W - M - rx, g = 0.3, ch = (BOTTOM - 1.4 - 2 * g) / 3;
  stat(s, rx, 1.4, rw, ch, "0.9 to 3.1 %", "of the 0.5 to 80 Hz road energy in the powertrain lines, powered passes (0.4 % coasting)", { bigSize: 30 });
  stat(s, rx, 1.4 + ch + g, rw, ch, "65 to 84 %", "between 4 and 8 Hz: the body's response to the road", { bigSize: 30 });
  stat(s, rx, 1.4 + 2 * (ch + g), rw, ch, "1.80 vs 1.78", "rear a_w (m/s²), coasting against powered, smooth loop at 10 km/h", { bigSize: 30 });
}

// ---------------- 12 Conclusions per RQ ----------------
{
  const s = content("Conclusions: each question answered in part",
    "So, honestly, each question is answered in part. RQ1: the instrument is verified on the bench, and on the road it repeats over whole passes but not yet place by place. " +
    "RQ2: the alerts are built and live-only, but the warning text is too small and glance time was not measured. " +
    "RQ3: on the bench every record survived a ten-minute outage; on the road the wired link carried 99.9 percent, but LTE latency rests on nine records. " +
    "RQ4: at these speeds the road dominates. " +
    "Of thirteen requirements, five are met on the bench, seven partly and one, glance time, was not tested. On the vehicle R1 was met at the front, R2 was not.");
  const rows = [
    ["RQ1", "Bench: rate, calibration and features verified. Road: repeats over whole passes (CV 5 %), not place by place (ICC 0.16).", "Partly"],
    ["RQ2", "Sparse, live-only alerts on the existing dashboard; warning text below ISO 15008; glance time not measured.", "Partly"],
    ["RQ3", "Bench: every record replayed after a 10-minute outage. Road: 99.9 % over the wired link; LTE latency rests on 9 records.", "Partly"],
    ["RQ4", "Powertrain lines at 40 to 70 Hz on the stands; 0.9 to 3.1 % of the road energy; one coasting pass did not lower a_w.", "Road dominates"],
  ];
  const lw = 8.2, rh = 1.12, gap = 0.2;
  rows.forEach(([id, t, st], i) => {
    const y = 1.4 + i * (rh + gap);
    card(s, M, y, lw, rh);
    txt(s, id, { x: M + 0.22, y, w: 0.85, h: rh, fontSize: 20, bold: true, color: C.navy, valign: "middle" });
    txt(s, t, { x: M + 1.1, y, w: lw - 3.35, h: rh, fontSize: 15, valign: "middle" });
    pill(s, M + lw - 2.1, y + (rh - 0.5) / 2, 1.9, 0.5, st, st === "Partly" ? "part" : "met");
  });
  const rx = M + lw + 0.35, rw = W - M - rx;
  card(s, rx, 1.4, rw, BOTTOM - 1.4);
  txt(s, "13 requirements (bench)", { x: rx + 0.25, y: 1.52, w: rw - 0.5, h: 0.4, fontSize: 17, bold: true, color: C.navy });
  [["5", "met", C.sky], ["7", "partly met", C.navy], ["1", "not tested (R12, glance time)", C.accent]].forEach(([n, l, col], i) => {
    const y = 2.05 + i * 0.85;
    txt(s, n, { x: rx + 0.25, y, w: 0.8, h: 0.75, fontSize: 40, bold: true, color: col, valign: "middle" });
    txt(s, l, { x: rx + 1.1, y, w: rw - 1.35, h: 0.75, fontSize: 15, valign: "middle" });
  });
  txt(s, "On the vehicle, 27 Oct", { x: rx + 0.25, y: 4.75, w: rw - 0.5, h: 0.38, fontSize: 16, bold: true, color: C.navy });
  bullets(s, ["R1 met at the front", "R4, R9, R10 partly met", "R2 not met"],
    { x: rx + 0.25, y: 5.2, w: rw - 0.5, h: BOTTOM - 5.3, fontSize: 15, paraSpaceAfter: 3 });
}

// ---------------- 13 Contribution and next steps ----------------
{
  const s = content("Contribution and next steps",
    "The contribution is an integrated low-cost architecture, a measured account of its timing and loss, and road evidence that the ride measurement repeats over whole passes. " +
    "Four steps would make it dependable. First, a regulated supply for the telemetry unit, never a Pi's USB port. Second, fix the LTE reconnection and measure latency on the road. " +
    "Third, marked sections with side video and three passes per speed, for a place-by-place ICC. Fourth, validate the fusion and time to contact against a flat target, a real approaching car and labelled video. " +
    "Videos of the road test are at tuksense.site. Thank you; I'm happy to take questions.");
  const top = 1.4, chh = 1.3;
  card(s, M, top, W - 2 * M, chh);
  txt(s, "Contribution", { x: M + 0.25, y: top + 0.1, w: 3, h: 0.36, fontSize: 16, bold: true, color: C.navy });
  const cw3 = (W - 2 * M - 0.5 - 0.6) / 3;
  ["An integrated, low-cost architecture for a three-wheeled EV, run on the vehicle",
   "A measured account of timing and loss: flash gap, detector latency, outage replay",
   "Road evidence: repeats over whole passes, separates surfaces; not yet place by place"]
    .forEach((t, i) => txt(s, t, { x: M + 0.25 + i * (cw3 + 0.3), y: top + 0.5, w: cw3, h: chh - 0.6, fontSize: 15, valign: "top" }));
  const recs = [
    ["Regulated supply", "Power the telemetry unit from a vehicle converter, never a Pi's USB port; measure each unit inline."],
    ["LTE reconnection", "Fix the reconnection lost from 11:51, then measure latency on the road."],
    ["Marked sections, video", "Straight sections with side video, three passes per speed, for a place-by-place ICC."],
    ["Fusion and time to contact", "Flat-target ranging, a car approaching the parked trike, at least 200 road alerts labelled on video."],
  ];
  const ry = top + chh + 0.3, g = 0.3, rw = (W - 2 * M - 3 * g) / 4, rh = 2.3;
  recs.forEach(([h, b], i) => {
    const x = M + i * (rw + g);
    card(s, x, ry, rw, rh, C.white, { color: C.sky, width: 1.5 });
    s.addShape(pres.shapes.OVAL, { x: x + 0.2, y: ry + 0.17, w: 0.42, h: 0.42, fill: { color: C.navy }, line: { color: C.navy } });
    txt(s, String(i + 1), { x: x + 0.2, y: ry + 0.17, w: 0.42, h: 0.42, fontSize: 15, bold: true, color: C.white, align: "center", valign: "middle" });
    txt(s, h, { x: x + 0.75, y: ry + 0.12, w: rw - 0.9, h: 0.52, fontSize: 15, bold: true, color: C.navy, valign: "middle" });
    txt(s, b, { x: x + 0.2, y: ry + 0.75, w: rw - 0.4, h: rh - 0.85, fontSize: 14, valign: "top" });
  });
  const cy = ry + rh + 0.25;
  txt(s, "Thank you. Questions?", { x: M, y: cy, w: W - 2 * M, h: 0.55, fontSize: 28, bold: true, color: C.navy, align: "center", valign: "middle" });
  txt(s, [{ text: "Videos of the system on the road: " },
          { text: "https://tuksense.site", options: { hyperlink: { url: "https://tuksense.site" }, color: C.sky, bold: true } }],
    { x: M, y: cy + 0.55, w: W - 2 * M, h: 0.4, fontSize: 16, color: C.text, align: "center", valign: "middle" });
}

// ---------------- talking points ----------------
function writeScript(file) {
  const words = (t) => t.split(/\s+/).filter(Boolean).length;
  const total = script.reduce((n, [, , t]) => n + words(t), 0);
  let md = "# Final presentation: talking points\n\n" +
    `Generated from the speaker notes by Presentation/source/build_deck.js; edit the notes there, not here.\n\n` +
    `${slideNo} slides, 10 minutes plus 5 minutes of questions. ${total} words in total, about ${Math.round(total / 140 * 10) / 10} minutes at 140 words a minute.\n`;
  for (const [n, title, notes] of script)
    md += `\n## Slide ${n}: ${title} (${words(notes)} words, about ${Math.round(words(notes) / 140 * 60)} s)\n\n${notes}\n`;
  fs.writeFileSync(file, md);
  console.log("wrote", file, `(${total} words)`);
}

const out = process.argv[2] || path.join(__dirname, "..", "SW7_Final_Presentation.pptx");
pres.writeFile({ fileName: out }).then((f) => {
  console.log("wrote", f);
  writeScript(path.join(path.dirname(out), "SW7_Talking_Points.md"));
});
