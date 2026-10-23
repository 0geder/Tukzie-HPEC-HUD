// SW7 final presentation, 16:9, matching the A1 poster (UCT banner, navy numbered markers, light-blue cards).
// Also writes Presentation/SW7_Talking_Points.md from the speaker notes, so the script always matches the deck.
// Updated 20 Oct 2026: two-sided layout, Pi 5 detector, approaching-object warning, enclosures and power,
// first road session (19 Oct). Every number is taken from the report (Methodology, Results, Discussion).
const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");
const A = (f) => path.join(__dirname, "assets", f);
const R = (f) => path.join(__dirname, "..", "..", "Report", "figures", f);   // report figures, used as they are

const C = {
  navy: "14305C", sky: "1565C0", panel: "E8F0FA", accent: "D4700C",
  text: "1B1F24", muted: "4A5566", white: "FFFFFF", line: "C9D6E8",
};
const FONT = "Calibri";
const W = 13.333, H = 7.5, M = 0.6;

// The HUD was replaced by integration with the vehicle's existing dashboard (supervisor agreed 1 Oct 2026;
// title change captured by the course coordinator 2 Oct 2026; changed again 23 Oct 2026 with the supervisor's and
// convenor's agreement). Keep TITLE the same in build_poster.js.
const TITLE = "Embedded Telemetry, Road-Surface Characterisation\nand Camera-Based Hazard Detection\nfor the TUKZIE Electric Tricycle";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "SW7: " + TITLE.replace(/\n/g, " ");
pres.author = "Samson Okuthe";

let slideNo = 0;
const TOTAL_MAIN = 14;
const script = [];   // [slide number, title, notes] for the talking points

function txt(s, t, o) { s.addText(t, Object.assign({ fontFace: FONT, color: C.text, isTextBox: true, margin: 0 }, o)); }
function card(s, x, y, w, h, fill = C.panel, line) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: fill }, line: line || { color: fill } });
}
function dashedCard(s, x, y, w, h) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: C.white }, line: { color: C.accent, width: 2, dashType: "dash" } });
}
function bullets(s, items, o) {
  s.addText(items.map((t, i) => ({ text: t, options: { bullet: { indent: 18 }, breakLine: i < items.length - 1, paraSpaceAfter: 8 } })),
    Object.assign({ fontFace: FONT, fontSize: 18, color: C.text, valign: "top", isTextBox: true, margin: 0 }, o));
}
// card with a bold heading and a body text, used on several slides
function infoCard(s, x, y, w, h, head, body, o = {}) {
  if (o.dashed) dashedCard(s, x, y, w, h); else card(s, x, y, w, h);
  txt(s, head, { x: x + 0.25, y: y + 0.1, w: w - 0.5, h: 0.36, fontSize: o.headSize || 16, bold: true, color: o.dashed ? C.accent : C.navy });
  txt(s, body, { x: x + 0.25, y: y + 0.48, w: w - 0.5, h: h - 0.55, fontSize: o.size || 13, valign: "top" });
}
function caption(s, t, x, y, w, h = 0.3) { txt(s, t, { x, y, w, h, fontSize: 12, italic: true, color: C.muted, valign: "top" }); }

// content slide: navy numbered marker + title, footer with crest and slide number
function content(title, notes) {
  const s = pres.addSlide();
  slideNo++;
  s.background = { color: C.white };
  s.addShape(pres.shapes.OVAL, { x: M, y: 0.42, w: 0.62, h: 0.62, fill: { color: C.navy }, line: { color: C.navy } });
  txt(s, String(slideNo - 1), { x: M, y: 0.42, w: 0.62, h: 0.62, fontSize: 20, bold: true, color: C.white, align: "center", valign: "middle" });
  txt(s, title, { x: M + 0.85, y: 0.34, w: W - 2 * M - 0.85, h: 0.8, fontSize: 32, bold: true, color: C.navy, valign: "middle" });
  s.addImage({ path: A("uct_logo.png"), x: W - M - 0.42, y: H - 0.58, w: 0.42, h: 0.427 });
  txt(s, "SW-7   |   Samson Okuthe   |   EEE4022S 2026", { x: M, y: H - 0.52, w: 6, h: 0.32, fontSize: 11, color: C.muted, valign: "middle" });
  txt(s, `${slideNo} / ${TOTAL_MAIN}`, { x: W - M - 1.6, y: H - 0.52, w: 1.0, h: 0.32, fontSize: 11, color: C.muted, align: "right", valign: "middle" });
  s.addNotes(notes);
  script.push([slideNo, title, notes]);
  return s;
}

function bannerSlide(title, notes) {
  const s = pres.addSlide();
  slideNo++;
  s.background = { color: C.navy };
  s.addImage({ path: A("uct_banner.jpg"), x: 0, y: 0, w: W, h: H, sizing: { type: "cover", w: W, h: H } });
  s.addNotes(notes);
  script.push([slideNo, title, notes]);
  return s;
}
const shadow = () => ({ type: "outer", color: "000000", blur: 6, offset: 2, angle: 45, opacity: 0.6 });

// ---------------- 1 Title ----------------
{
  const s = bannerSlide("Title",
    "Good morning. I'm Samson Okuthe, and my project is SW-7, supervised by Associate Professor Simon Winberg with Sampath Jayalath. " +
    "It is part of TUKZIE, a 72 volt electric cargo trike for last-mile freight. " +
    "I built its on-board electronics: a telemetry unit that measures how the trike rides, and safety alerts on the dashboard it already has.");
  txt(s, "EEE4022S Final Year Project 2026, Department of Electrical Engineering, University of Cape Town",
    { x: M, y: 0.35, w: W - 2 * M, h: 0.4, fontSize: 15, color: C.white, align: "center", shadow: shadow() });
  txt(s, TITLE,
    { x: M, y: 0.85, w: W - 2 * M, h: 1.6, fontSize: 31, bold: true, color: C.white, align: "center", valign: "middle", shadow: shadow() });
  txt(s, "Samson Okuthe (OKTSAM001)",
    { x: M, y: 2.5, w: W - 2 * M, h: 0.45, fontSize: 20, bold: true, color: C.white, align: "center", shadow: shadow() });
  txt(s, "Supervisor: A/Prof. Simon Winberg   |   Co-supervisor: Sampath Jayalath   |   Project SW-7",
    { x: M, y: 2.95, w: W - 2 * M, h: 0.4, fontSize: 16, color: C.white, align: "center", shadow: shadow() });
}

// ---------------- 2 Why ----------------
{
  const s = content("Why this matters",
    "Electric trikes make economic sense for freight in African cities: on delivery routes in Dar es Salaam, an electric cargo tricycle cut the operating cost per kilometre by 45.5 percent against a motorcycle. " +
    "But anything that takes the driver's eyes off the road is a risk; NHTSA guidance limits a single glance to two seconds. " +
    "So the problem is to combine edge telemetry with short, safety-only alerts on a low-cost trike, and to measure whether each part works.");
  const cw = (W - 2 * M - 0.5) / 2, cy = 1.45, ch = 3.3;
  [["45.5 to 86%", "lower operating cost per km for an electric cargo tricycle than a motorcycle, petrol tuk-tuk or light car on delivery routes in Dar es Salaam", "Sebwa et al., 2025"],
   ["2 s", "longest single glance away from the road that NHTSA guidance allows, so driver information must be short and safety-only", "NHTSA, 2013"]]
    .forEach(([big, small, src], i) => {
      const x = M + i * (cw + 0.5);
      card(s, x, cy, cw, ch);
      txt(s, big, { x: x + 0.4, y: cy + 0.35, w: cw - 0.8, h: 1.2, fontSize: 60, bold: true, color: C.navy });
      txt(s, small, { x: x + 0.4, y: cy + 1.6, w: cw - 0.8, h: 1.1, fontSize: 18, color: C.text, valign: "top" });
      txt(s, src, { x: x + 0.4, y: cy + ch - 0.55, w: cw - 0.8, h: 0.35, fontSize: 13, italic: true, color: C.muted });
    });
  txt(s, [{ text: "The open problem: ", options: { bold: true, color: C.navy } },
          { text: "bringing on-board edge telemetry and sparse, safety-only driver alerts together on a low-cost electric trike, and measuring whether each part works." }],
    { x: M, y: 5.2, w: W - 2 * M, h: 1.0, fontSize: 20, valign: "middle" });
}

// ---------------- 3 Research questions ----------------
{
  const s = content("Aim and research questions",
    "Four research questions, and where each honestly stands. " +
    "RQ1, how accurately and repeatably a low-cost unit characterises the ride: the instrument is verified, and on the first road session it held its rate, but repeatability is not measured yet. " +
    "RQ2, alerts on the existing dashboard with the least distraction: this replaced the head-up display with my supervisor's agreement. It is built; glance time is not measured. " +
    "RQ3, latency, loss and recovery: loss and recovery pass a ten-minute outage test; latency needs GNSS time. " +
    "RQ4, road against powertrain vibration, needs the second road session.");
  // status styles: "bench" filled sky, "part" filled navy, "open" dashed orange outline
  const rows = [
    ["RQ1", "How accurately and repeatably can a low-cost edge unit characterise the trike's ride response?", "Rate held on road", "part"],
    ["RQ2", "Which layout and update strategy show safety alerts on the existing dashboard with least distraction?", "Glance untested", "open"],
    ["RQ3", "What latency, data loss and recovery from sensor through local log to the LTE link?", "Loss tested", "bench"],
    ["RQ4", "Which ride features separate road-induced from powertrain vibration?", "Needs session 2", "open"],
  ];
  const y0 = 1.45, rh = 1.08, gap = 0.18;
  rows.forEach(([id, req, status, style], i) => {
    const y = y0 + i * (rh + gap);
    card(s, M, y, W - 2 * M, rh);
    txt(s, id, { x: M + 0.3, y, w: 1.0, h: rh, fontSize: 24, bold: true, color: C.navy, valign: "middle" });
    const bx = W - M - 2.75, open = style === "open";
    txt(s, req, { x: M + 1.35, y, w: bx - M - 1.6, h: rh, fontSize: 18, valign: "middle" });
    const col = style === "bench" ? C.sky : open ? C.accent : C.navy;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: bx, y: y + 0.29, w: 2.45, h: 0.5, rectRadius: 0.25,
      fill: { color: open ? C.white : col }, line: { color: col, width: 1.5, dashType: open ? "dash" : "solid" } });
    txt(s, status, { x: bx, y: y + 0.29, w: 2.45, h: 0.5, fontSize: 15, bold: true, color: open ? C.accent : C.white, align: "center", valign: "middle" });
  });
}

// ---------------- 4 Two-sided system ----------------
{
  const s = content("The system: front and rear, joined by one cable",
    "Since the fifteenth of October the system has two sides, joined by one Ethernet cable. " +
    "At the front, a Raspberry Pi 5 behind the dashboard runs its own camera, the detector, a time-of-flight board and the fusion, so a front alert never crosses the network. " +
    "At the rear, beside the battery, the Pi 4 runs the rear camera and sensors and carries the telemetry unit: an ESP32-S3 with LTE and GNSS, two IMUs at 200 hertz and the battery link. " +
    "Two findings drove this: the battery's Bluetooth did not reach the front, and the Pi 5 runs the detector more than twice as fast.");
  const cw = 5.0, cy = 1.45, ch = 3.45, xr = W - M - cw;
  const side = (x, head, items) => {
    card(s, x, cy, cw, ch);
    txt(s, head, { x: x + 0.3, y: cy + 0.18, w: cw - 0.6, h: 0.75, fontSize: 19, bold: true, color: C.navy, valign: "top" });
    bullets(s, items, { x: x + 0.3, y: cy + 1.0, w: cw - 0.6, h: ch - 1.1, fontSize: 16 });
  };
  side(M, "Front: Raspberry Pi 5,\nbehind the dashboard", [
    "Front camera and object detector",
    "Time-of-flight board (left, ahead, right) and camera fusion",
    "Dashboard on the 10.1 in touchscreen",
    "Road recorder: all four sources at 2 Hz",
  ]);
  side(xr, "Rear: Raspberry Pi 4,\nbeside the battery", [
    "Rear camera, detector, time-of-flight board",
    "Telemetry unit on USB: ESP32-S3 with LTE, GNSS, local log",
    "Two IMUs at 200 Hz; battery over Bluetooth; Hall counter",
    "LTE uplink to the central database",
  ]);
  // the link between them
  const lx = M + cw + 0.12, lw = xr - lx - 0.12, ly = cy + ch / 2;
  s.addShape(pres.shapes.LINE, { x: lx, y: ly, w: lw, h: 0, line: { color: C.navy, width: 3, beginArrowType: "triangle", endArrowType: "triangle" } });
  txt(s, "Ethernet", { x: lx, y: ly - 0.55, w: lw, h: 0.4, fontSize: 16, bold: true, color: C.navy, align: "center" });
  txt(s, "1000 Mb/s\n0.22 to 0.25 ms", { x: lx, y: ly + 0.15, w: lw, h: 0.7, fontSize: 13, color: C.muted, align: "center", valign: "top" });
  // why
  const wy = cy + ch + 0.3, wh = 6.75 - wy;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: wy, w: W - 2 * M, h: wh, rectRadius: 0.12, fill: { color: C.white }, line: { color: C.sky, width: 1.5 } });
  txt(s, [{ text: "Why two sides (15 Oct): ", options: { bold: true, color: C.navy } },
          { text: "the battery's Bluetooth link did not reach the telemetry unit at the front, and the Pi 5 runs the detector more than twice as fast as the Pi 4. A front alert no longer crosses the network to reach the screen." }],
    { x: M + 0.3, y: wy, w: W - 2 * M - 0.6, h: wh, fontSize: 16, valign: "middle" });
}

// ---------------- 5 Firmware ----------------
{
  const s = content("Firmware: deterministic acquisition first",
    "The firmware runs on FreeRTOS across two cores. " +
    "Core 1 holds one task per IMU at the highest priority, on a fixed 5 millisecond period. " +
    "They never block: each sample is time-stamped into a bounded queue, and if it is full the sample is dropped and counted. " +
    "Core 0 does the modem, GNSS, MQTT and the flash log, in one task because the modem's serial line has no lock. " +
    "Version 0.7.4 adds sequence numbers, backlog replay and a 94 hertz filter against aliasing.");
  const bx = (x, y, w, h, title, sub, fill = C.white, border = C.sky) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.1, fill: { color: fill }, line: { color: border, width: 1.5 } });
    txt(s, title, { x: x + 0.12, y: y + 0.06, w: w - 0.24, h: 0.36, fontSize: 15, bold: true, color: C.navy, align: "center" });
    if (sub) txt(s, sub, { x: x + 0.12, y: y + 0.42, w: w - 0.24, h: h - 0.48, fontSize: 12, color: C.muted, align: "center", valign: "top" });
  };
  // negative sizes corrupt the file, so an upward arrow is drawn flipped
  const arrow = (x1, y1, x2, y2) => s.addShape(pres.shapes.LINE, {
    x: x1, y: Math.min(y1, y2), w: x2 - x1, h: Math.abs(y2 - y1), flipV: y2 < y1,
    line: { color: C.navy, width: 1.5, endArrowType: "triangle" } });
  // core 1 panel
  const px = M, py = 1.45, pw = 8.1, ph = 4.75;
  card(s, px, py, pw, ph);
  txt(s, "Core 1: timing-critical", { x: px + 0.25, y: py + 0.12, w: 4, h: 0.4, fontSize: 16, bold: true, color: C.sky });
  const colA = px + 0.3, colB = px + 2.95, colC = px + 5.6, bw = 2.2;
  bx(colA, py + 0.7, bw, 1.0, "Imu1Task", "200 Hz, priority 3, 94 Hz filter");
  bx(colA, py + 2.05, bw, 1.0, "Imu2Task", "200 Hz, priority 3, 94 Hz filter");
  bx(colB, py + 0.7, bw, 1.0, "Queues", "bounded; drop and count, never block");
  bx(colB, py + 2.05, bw, 1.0, "StatsTask", "rate, jitter, drops every 2 s");
  bx(colC, py + 0.7, bw, 1.0, "RideChar x2", "1 s windows: RMS, std, peak-to-peak, jerk");
  bx(colC, py + 2.05, bw, 1.0, "Fusion", "pairs windows, reports disagreement", C.white, C.accent);
  arrow(colA + bw, py + 1.2, colB, py + 1.2);
  arrow(colA + bw, py + 2.55, colB, py + 1.45);
  arrow(colB + bw, py + 1.2, colC, py + 1.2);
  arrow(colB + bw / 2, py + 1.7, colB + bw / 2, py + 2.05);
  arrow(colC + bw / 2, py + 1.7, colC + bw / 2, py + 2.05);
  bx(colA, py + 3.4, bw, 1.0, "SyncTask", "pulse to the Pi every 500 ms");
  txt(s, "Each sample carries a sensor ID, a sequence number and a microsecond timestamp from esp_timer.",
    { x: colB, y: py + 3.45, w: 4.85, h: 0.9, fontSize: 14, italic: true, color: C.muted, valign: "middle" });
  // core 0 panel
  const qx = px + pw + 0.35, qw = W - M - qx;
  card(s, qx, py, qw, ph);
  txt(s, "Core 0: blocking I/O", { x: qx + 0.25, y: py + 0.12, w: qw - 0.5, h: 0.4, fontSize: 16, bold: true, color: C.sky });
  bx(qx + 0.3, py + 0.65, qw - 0.6, 1.3, "ModemTask", "GNSS, MQTT with sequence numbers and backlog replay (v0.7.4), flash log once a minute");
  bx(qx + 0.3, py + 2.1, qw - 0.6, 0.8, "BmsTask", "battery over BLE");
  bx(qx + 0.3, py + 3.05, qw - 0.6, 0.8, "HallTask", "hardware pulse counter");
  txt(s, "The modem UART has no lock, so all modem traffic stays in one task.",
    { x: qx + 0.3, y: py + 3.95, w: qw - 0.6, h: 0.7, fontSize: 12, italic: true, color: C.muted, valign: "top" });
  txt(s, "Method: each stage (bring-up, acquisition, features and fusion, log and uplink, vehicle) was tested against a pass criterion before the next was built on it.",
    { x: M, y: py + ph + 0.15, w: W - 2 * M, h: 0.45, fontSize: 14, italic: true, color: C.muted, valign: "top" });
}

// ---------------- 6 IMU acquisition and fusion ----------------
{
  const s = content("Result: 200 Hz acquisition and dual-IMU fusion",
    "Both IMUs run at 200 hertz with no dropped samples, counted, not assumed. " +
    "Flash writes cause one gap of under 45 milliseconds a minute, and the queue holds the samples through it. " +
    "A gravity factor per sensor brings both to 9.80 or 9.81, but only in that orientation, so it is redone once mounted. " +
    "Fusion is an equal-weight mean; windows pair only if they end within half a window, and the disagreement is reported. " +
    "In a 150 second session all 149 windows fused with under a millisecond of skew.");
  const stats = [
    ["200 Hz", "on both IMUs, no samples dropped"],
    ["9.8 m/s²", "both IMUs at rest just after calibration (9.80, 9.81)"],
    ["149 / 149", "windows fused from both IMUs"],
    ["< 1 ms", "skew between paired windows"],
  ];
  const cw = (W - 2 * M - 3 * 0.3) / 4, cy = 1.4, ch = 1.6;
  stats.forEach(([big, small], i) => {
    const x = M + i * (cw + 0.3);
    card(s, x, cy, cw, ch);
    txt(s, big, { x: x + 0.25, y: cy + 0.12, w: cw - 0.5, h: 0.75, fontSize: 34, bold: true, color: C.navy, valign: "middle" });
    txt(s, small, { x: x + 0.25, y: cy + 0.9, w: cw - 0.5, h: 0.62, fontSize: 14, valign: "top" });
  });
  const gy = cy + ch + 0.3, chW = 7.6, chH = chW * 888 / 2604;
  s.addImage({ path: A("vibration_chart.png"), x: M, y: gy, w: chW, h: chH });
  txt(s, "Recorded 150 s session: still, then disturbed by hand from about 75 s. Fused (green) sits between IMU1 and IMU2.",
    { x: M, y: gy + chH + 0.05, w: chW, h: 0.5, fontSize: 13, italic: true, color: C.muted });
  const rx = M + chW + 0.35, rw = W - M - rx, rh = 6.75 - gy;
  card(s, rx, gy, rw, rh);
  txt(s, "Fusion rules and limits", { x: rx + 0.3, y: gy + 0.15, w: rw - 0.6, h: 0.4, fontSize: 18, bold: true, color: C.navy });
  bullets(s, [
    "Equal-weight mean (equal noise)",
    "Paired if windows end within 500 ms",
    "Disagreement reported; 3 s fallback",
    "Flash gaps 33 to 44 ms, once a minute",
    "Uncalibrated: 8% apart (earlier run)",
    "Calibration holds in one orientation",
  ], { x: rx + 0.3, y: gy + 0.62, w: rw - 0.6, h: rh - 0.75, fontSize: 13 });
}

// ---------------- 7 Found and fixed ----------------
{
  const s = content("Seven fault investigations: symptom, test, cause, fix",
    "Because each stage was tested before the next, every fault could be traced to one change. Seven needed a real diagnosis; here is the one that mattered most. " +
    "The Pi 4 kept throttling and rebooting. A logger recorded its power flags every two seconds: clear with nothing attached, then under-voltage fourteen seconds after the telemetry unit's modem came up on its USB port. Moved off, no restarts in four hours. " +
    "It came back in the closed box: 76.9 degrees and a brown-out restart. So the unit needs its own supply, and the lids gained vents. " +
    "The Pi 5's restarts while mounting were different: abrupt power loss, not a brown-out.");
  const items = [
    ["Boot loop, full flash", "Seen: reset once a second at one address. Tests: PSRAM setting, all overrides off, ROM banner. Cause: quad mode asked, chip runs dual (DIO). Fix: size, mode and table set together."],
    ["GNSS reply layout", "Seen: first fix near 0, 0. Test: raw replies logged: 17 fields in decimal degrees, not 13 as assumed. Fix: parser anchors on the hemisphere letter; median 2.7 m."],
    ["Battery checksum", "Seen: every frame rejected. Test: the firmware's own query frame shows the rule. Cause: register byte summed too, so each reply failed by 3. Fix: 14 valid records, 74.78 V."],
    ["Invalid JSON in the log", "Seen: 5,545 of 6,020 records failed to parse. Test: indexed, length-checked read-back: all intact, so not transfer. Cause: nan for missing values. Fix: null; all parse."],
    ["Camera colour cast", "Seen: pink image. Tests: stills with the standard and the NoIR tuning. Cause: no infrared-cut filter, not channel order. Fix: NoIR tuning plus saturation 1.8."],
    ["Distance-sensor hang", "Seen: nulls, then a frozen reader. Test: bus scan; driver timeout found to be zero, wait for ever. Fix: 0.5 s timeout, wiring re-seated; all three read again."],
    ["Pi 4 under-voltage, reboots", "Candidates: supply, sensor board, telemetry unit on USB, heat. Test: power flags every 2 s: under-voltage 14 s after the modem came up. Unit moved off: 3 restarts in 20 min, then none in 4 h."],
    ["It came back (16 to 19 Oct)", "Closed rear box, unit still on the Pi's USB: 76.9 °C and a brown-out restart. Fix: own supply for the unit; vented lids. Pi 5 restarts: last readings normal, so abrupt power loss, not a brown-out."],
  ];
  const n = 4, g = 0.22, cw = (W - 2 * M - (n - 1) * g) / n, ch = 2.4, gy = 0.18;
  items.forEach(([h, b], i) => {
    const x = M + (i % n) * (cw + g), y = 1.35 + Math.floor(i / n) * (ch + gy), last = i === items.length - 1;
    if (last) dashedCard(s, x, y, cw, ch); else card(s, x, y, cw, ch);
    txt(s, h, { x: x + 0.2, y: y + 0.12, w: cw - 0.4, h: 0.38, fontSize: 15, bold: true, color: last ? C.accent : C.navy });
    txt(s, b, { x: x + 0.2, y: y + 0.52, w: cw - 0.4, h: ch - 0.6, fontSize: 12, valign: "top" });
  });
  txt(s, "Each is told in the report as symptom, candidate causes, deciding test, cause and fix, consequence; each test was run again after the fix.",
    { x: M, y: 6.5, w: W - 2 * M, h: 0.35, fontSize: 14, italic: true, color: C.muted, align: "center" });
}

// ---------------- 8 Timing, position, cellular ----------------
{
  const s = content("Result: timing, position, and no data lost in an outage",
    "The sync wire gives a median interval of 500.06 milliseconds over 121 edges, with under 0.7 of spread, so camera and IMU clocks line up. " +
    "On a rooftop, GNSS was a median 2.7 metres from a phone. " +
    "The outage test: I switched the radio off for ten minutes. The unit reconnected 5.2 seconds after it came back and cleared 60 records in about 40 seconds; the database holds 112 of 112. " +
    "The public test broker does not queue, so the log read-back is the safety net, and latency needs GNSS time.");
  const n = 3, g = 0.35, cw = (W - 2 * M - (n - 1) * g) / n, cy = 1.4, ch = 5.35;
  const col = (x, title, big, bigSub, items) => {
    card(s, x, cy, cw, ch);
    txt(s, title, { x: x + 0.3, y: cy + 0.2, w: cw - 0.6, h: 0.45, fontSize: 19, bold: true, color: C.navy });
    txt(s, big, { x: x + 0.3, y: cy + 0.7, w: cw - 0.6, h: 0.9, fontSize: 40, bold: true, color: C.sky, valign: "middle" });
    txt(s, bigSub, { x: x + 0.3, y: cy + 1.6, w: cw - 0.6, h: 0.6, fontSize: 14, color: C.muted, valign: "top" });
    bullets(s, items, { x: x + 0.3, y: cy + 2.35, w: cw - 0.6, h: ch - 2.5, fontSize: 14 });
  };
  col(M, "Camera to IMU timing", "500.06 ms", "median sync interval over 121 edges, kernel timestamps",
    ["Spread under 0.7 ms",
     "Video frames placed on the IMU clock within 1 s",
     "A loose jumper twice gave false edges: a latched connector is needed"]);
  col(M + cw + g, "GNSS outdoors (bench)", "2.7 m", "median from a phone's position over 104 fixes",
    ["95% within 11 m; fix 105 s after a cold start",
     "Indoors: network position in 0.7 s, 550 m stated",
     "No fix at all on the first road session"]);
  col(M + 2 * (cw + g), "10-minute LTE outage (T15)", "112 / 112", "records stored in the Pi 5 database, none missing or doubled",
    ["60 records built up; reconnected 5.2 s after radio on",
     "Backlog cleared in 37 to 43 s; 111 of 111 against the unit's log",
     "An ingest fault found in the test was fixed; 24 records backfilled from the log",
     "Latency not yet measured (needs GNSS time)"]);
}

// ---------------- 9 Detection, front and rear ----------------
{
  const s = content("Hazard detection: twice as fast at the front",
    "The detector is a pretrained 8-bit SSD-MobileNet. " +
    "On the Pi 4 with the whole system running it takes 118 to 122 milliseconds from sensor readout to result, at 14.6 frames per second. " +
    "On the Pi 5 beside the dashboard it is 51 to 54 milliseconds at 19.2 frames per second, with no throttling. " +
    "At 30 kilometres an hour that is about 0.6 metres less travel before an alert. " +
    "An alert needs three frames to raise and five to clear, and no frame is ever stored. " +
    "My pothole model works on a test image but is off by default.");
  const lw = 6.55, ly = 1.4, lh = 4.55;
  card(s, M, ly, lw, lh);
  s.addChart(pres.charts.BAR, [{ name: "Median readout to result (ms)",
      labels: ["Pi 4, whole system: 118 to 122 ms", "Pi 4, detector alone: 102 ms", "Pi 5, with the dashboard: 51 to 54 ms"],
      values: [120, 102, 52.5] }], {
    x: M + 0.2, y: ly + 0.15, w: lw - 0.4, h: lh - 0.3, barDir: "bar",
    chartColors: [C.sky], showTitle: true, title: "Median, sensor readout to detection (ms)", titleFontSize: 15, titleColor: C.navy, titleFontFace: FONT,
    catAxisLabelFontSize: 13, catAxisLabelColor: C.text, catAxisLabelFontFace: FONT, catAxisOrientation: "maxMin",
    valAxisMinVal: 0, valAxisMaxVal: 140, valAxisMajorUnit: 20, valAxisLabelFontSize: 11, valAxisLabelColor: C.muted, valAxisLabelFontFace: FONT,
    valGridLine: { color: "C9D6E8", size: 0.75 }, catGridLine: { style: "none" }, showLegend: false, showValue: false, barGapWidthPct: 60,
  });
  caption(s, "Bench runs: Pi 4 whole system 11 Oct; Pi 5 with the dashboard 15 Oct, 60 s. At 30 km/h the Pi 5 saves about 0.6 m of travel before an alert.",
    M, ly + lh + 0.1, lw, 0.6);
  const rx = M + lw + 0.35, rw = W - M - rx, g = 0.15, bh = (5.35 - 3 * g) / 4;
  [["Front, Raspberry Pi 5 (bench)", "19.2 fps; 51 to 54 ms median, 61 to 63 ms 95th percentile; CPU 64 to 73 %, 53 to 54 °C, no throttling."],
   ["Mounted on the vehicle (19 Oct)", "Front 17.5 to 22.0 fps, 53 to 102 ms. Rear 14.4 to 14.5 fps, 126 to 151 ms, slower while the Pi 4 was throttled."],
   ["Alert logic and privacy", "Raised after 3 frames, cleared after 5 empty frames. Frames are never stored; five fields per alert."],
   ["Pothole model (off by default)", "mAP@50 0.714 on validation tiles; found at 0.63 in a test image; too slow beside the detector on the Pi 4."],
  ].forEach(([h, b], i) => infoCard(s, rx, 1.4 + i * (bh + g), rw, bh, h, b));
}

// ---------------- 10 Approaching objects ----------------
{
  const s = content("Approaching objects: time to contact from box growth",
    "Distance bands say how near an object is, not whether it is coming closer. " +
    "For an object closing at constant speed, the inverse of its box width falls in a straight line to zero at contact. " +
    "So time to contact is the width over its rate of growth, after Lee in 1976, and it needs no focal length or object size. " +
    "I fit that line robustly over the last 0.6 seconds, and warn below 4 seconds, immediate below 2. " +
    "In 40 synthetic tests it is within 2 percent, at 0.27 milliseconds a frame. It has not been tested on a real approach.");
  const lw = 6.3, ly = 1.4, lh = 5.35;
  card(s, M, ly, lw, lh);
  // three boxes growing as an object closes
  const base = ly + 2.15;
  [[0.55, 0.42, "t − 0.6 s"], [0.95, 0.72, "t − 0.3 s"], [1.55, 1.18, "now"]].forEach(([bw, bh], i) => {
    const cx = M + 0.95 + i * 2.05;
    s.addShape(pres.shapes.RECTANGLE, { x: cx - bw / 2, y: base - bh, w: bw, h: bh, fill: { color: C.white }, line: { color: i === 2 ? C.accent : C.sky, width: 2 } });
  });
  [["t − 0.6 s", 0], ["t − 0.3 s", 1], ["now", 2]].forEach(([l, i]) =>
    txt(s, l, { x: M + 0.95 + i * 2.05 - 0.8, y: base + 0.08, w: 1.6, h: 0.3, fontSize: 13, color: C.muted, align: "center" }));
  txt(s, "The box width w of a tracked object grows as it closes", { x: M + 0.3, y: ly + 0.18, w: lw - 0.6, h: 0.4, fontSize: 16, bold: true, color: C.navy });
  txt(s, "τ = w / (dw/dt)", { x: M + 0.3, y: base + 0.5, w: lw - 0.6, h: 0.75, fontSize: 34, bold: true, color: C.navy, valign: "middle" });
  bullets(s, [
    "1/w falls in a straight line to zero at contact; a Theil-Sen line is fitted over the last 0.6 s",
    "No focal length or object size needed (Lee 1976; Dagan et al. 2004)",
    "Used only with 5 frames over 0.25 s, 75 % of slopes agreeing, 5 % growth, box clear of the image edge",
  ], { x: M + 0.3, y: base + 1.35, w: lw - 0.6, h: ly + lh - base - 1.45, fontSize: 14 });
  const rx = M + lw + 0.35, rw = W - M - rx, g = 0.18, bh = (lh - 2 * g) / 3;
  infoCard(s, rx, ly, rw, bh, "Warning rule",
    "Approaching when τ is under 4 s (warning) or 2 s (immediate), after the 3-frame onset; released above 5 s. Inside the time-of-flight range the sensor's own closing rate gives τ.");
  infoCard(s, rx, ly + bh + g, rw, bh, "Tested (synthetic, 15 Oct)",
    "40 tests pass: τ within 2 % at constant speed; no alerts in 5,000 frames of receding, still or jittering boxes. 0.27 ms per frame on a laptop.");
  infoCard(s, rx, ly + 2 * (bh + g), rw, bh, "Untested",
    "No real approach yet (test C11). On the road the front camera marked 261 car alerts as approaching, not yet checked against video. A still object ahead counts while driving: intended.",
    { dashed: true });
}

// ---------------- 11 Dashboard ----------------
{
  const s = content("Both cameras on the existing dashboard",
    "This is where RQ2 lands, on the dashboard the team already runs. " +
    "The Surroundings page now has a Front and Rear switch, which moves the picture, alerts, distances and hazards together, each from that side's own unit. " +
    "The rear view is mirrored like a reversing camera. " +
    "The banner shows warnings from both sides, names the side, and puts an approaching object first. " +
    "It shows only live data, never a simulated value. " +
    "It is tested offscreen and live on the Pi 5; glance time on the vehicle is still open.");
  const iw = 7.4, imW = (iw - 0.2) / 2, ih = imW * 800 / 1280;
  s.addImage({ path: R("ui/ui_dualcam_front.png"), x: M, y: 1.4, w: imW, h: ih });
  s.addImage({ path: R("ui/ui_dualcam_rear_approaching.png"), x: M + imW + 0.2, y: 1.4, w: imW, h: ih });
  caption(s, "Front: Pi 5 camera and ToF (test image)", M, 1.4 + ih + 0.06, imW);
  caption(s, "Rear, mirrored: car approaching at 1.6 s (test)", M + imW + 0.2, 1.4 + ih + 0.06, imW);
  const wy = 1.4 + ih + 0.5, wh = 6.75 - wy;
  card(s, M, wy, iw, wh);
  txt(s, "Two cameras, one page (15 Oct)", { x: M + 0.3, y: wy + 0.12, w: iw - 0.6, h: 0.38, fontSize: 16, bold: true, color: C.navy });
  bullets(s, [
    "Front | Rear switch moves picture, alerts, distances and hazards together",
    "Rear view mirrored like a car's reversing camera",
    "Banner names the side; an approaching object comes first",
    "Live data only: a lost side shows offline, never zero or the other side",
  ], { x: M + 0.3, y: wy + 0.55, w: iw - 0.6, h: wh - 0.6, fontSize: 14 });
  const rx = M + iw + 0.35, rw = W - M - rx;
  card(s, rx, 1.4, rw, 5.35);
  txt(s, "Live on the Pi 5", { x: rx + 0.3, y: 1.52, w: rw - 0.6, h: 0.42, fontSize: 18, bold: true, color: C.navy });
  const sw = rw - 0.6, sh = sw * 800 / 1280;
  s.addImage({ path: R("ui/ui_pi5_live_dualcam.png"), x: rx + 0.3, y: 2.0, w: sw, h: sh });
  caption(s, "15 Oct: live front camera at 23.6 fps, a rear warning in the banner", rx + 0.3, 2.0 + sh + 0.06, sw, 0.5);
  bullets(s, [
    "Tested offscreen with four fake servers",
    "Paper theme, one tap colour, status in words",
  ], { x: rx + 0.3, y: 2.0 + sh + 0.6, w: sw, h: 0.8, fontSize: 13 });
  txt(s, [{ text: "Still open: ", options: { bold: true, color: C.accent } }, { text: "glance time on the vehicle, against NHTSA and ISO 15008." }],
    { x: rx + 0.3, y: 6.05, w: rw - 0.6, h: 0.6, fontSize: 14, valign: "top" });
}

// ---------------- 12 Enclosures, heat and power ----------------
{
  const s = content("On the vehicle: enclosures, heat and power",
    "The enclosures were modelled from scripts in SOLIDWORKS, each checked for interference, fasteners and thin walls: a display mount, a front pod for the Pi 5 and its AI HAT, and a screwless IMU pod. " +
    "After the Pi 4 reached 76.9 degrees in its closed box, both lids gained an exhaust grille under a rain hood. " +
    "The power budget is about 20 watts, 0.27 amps from the 72 volt pack, under one percent of the motor's rated input. " +
    "Only the Pi 5 is measured; the rest are estimates.");
  const lw = 7.4, top = 1.4;
  const cellW = (lw - 0.2) / 2;
  // row 1: front pod, display mount
  const img = (p, x, y, w, h, cap) => {
    card(s, x, y, w, h, C.white, { color: C.line, width: 1 });
    const ar = p.ar, maxW = w - 0.2, maxH = h - 0.55;
    let iw2 = maxW, ih2 = iw2 / ar; if (ih2 > maxH) { ih2 = maxH; iw2 = ih2 * ar; }
    s.addImage({ path: p.f, x: x + (w - iw2) / 2, y: y + 0.1, w: iw2, h: ih2 });
    caption(s, cap, x + 0.15, y + h - 0.42, w - 0.3, 0.36);
  };
  const r1h = 2.75;
  img({ f: A("cad_front_pod.png"), ar: 885 / 595 }, M, top, cellW, r1h, "Front pod: Pi 5 with AI HAT+, camera, ToF");
  img({ f: A("cad_display_mount.png"), ar: 1030 / 720 }, M + cellW + 0.2, top, cellW, r1h, "Display mount: bar clamp, dovetail rail");
  const r2y = top + r1h + 0.2, r2h = 1.75;
  img({ f: A("cad_vented_lid.png"), ar: 460 / 270 }, M, r2y, cellW, r2h, "Vented lid: grille under a rain hood");
  img({ f: A("cad_front_pod_inside.png"), ar: 1105 / 425 }, M + cellW + 0.2, r2y, cellW, r2h, "Front pod inside: Pi 5, cooler, AI HAT+");
  caption(s, "Also an IMU pod (rev 3, push-fit, no screws). Printed so far: the rear box and a first IMU pod; the rest are checked in CAD only, fit tests outstanding.",
    M, r2y + r2h + 0.1, lw, 0.6);
  // power
  const rx = M + lw + 0.35, rw = W - M - rx;
  card(s, rx, top, rw, 5.35);
  txt(s, "Power budget", { x: rx + 0.3, y: top + 0.15, w: rw - 0.6, h: 0.4, fontSize: 18, bold: true, color: C.navy });
  txt(s, "about 20 W", { x: rx + 0.3, y: top + 0.6, w: rw - 0.6, h: 0.8, fontSize: 40, bold: true, color: C.sky, valign: "middle" });
  txt(s, "0.27 A from the 72 V pack while driving; 35 W short peaks", { x: rx + 0.3, y: top + 1.42, w: rw - 0.6, h: 0.6, fontSize: 14, color: C.muted, valign: "top" });
  bullets(s, [
    "About 0.8 % of the motor's 2.5 kW rated input",
    "Pack from the BMS: 24 cells, 150 A, about 60 to 88 V",
    "Converter: rated to 100 V, 40 W at 5 V, fused, off with the vehicle",
    "Measured: only the Pi 5 (2.2 to 3.0 W on its rails); the rest are estimates",
  ], { x: rx + 0.3, y: top + 2.15, w: rw - 0.6, h: 3.1, fontSize: 14 });
}

// ---------------- 13 First road session ----------------
{
  const s = content("First road session, 19 October",
    "On the nineteenth of October the whole system was mounted and the first road session run. " +
    "A recorder on the Pi 5 ran for 108.6 minutes, about 16 of them driving, with no laptop on board. " +
    "Both IMUs held 200 hertz with no drops and one short stall, but a third of the per-second records were lost on the USB link, now replaced by wires, so R1 is only partly met on the vehicle. " +
    "The battery link held under load: up to 46.9 amps, the pack falling from 74.6 to 72.8 volts. " +
    "The cameras raised 1,342 front and 741 rear alerts, not yet checked against video. " +
    "But GNSS had no fix, as no antenna was fitted, and there were no raw samples or run markers, so RQ1 and RQ4 are not answered yet. A second, shorter session is planned.");
  const lw = 7.4, top = 1.4, g = 0.25, tw = (lw - g) / 2, th = 2.2;
  const tiles = [
    ["108.6 min", "recorded on the vehicle by the Pi 5, about 16 min of it driving"],
    ["200 Hz", "both IMUs, no drops, one 2 s stall; 38 % of records lost on USB: R1 partly met"],
    ["46.9 A", "peak battery current; 74.6 to 72.8 V, 60 to 58 %: R5 partly met (no meter check)"],
    ["1,342 / 741", "front and rear camera alerts, not yet checked against video"],
  ];
  tiles.forEach(([big, small], i) => {
    const x = M + (i % 2) * (tw + g), y = top + Math.floor(i / 2) * (th + g);
    card(s, x, y, tw, th);
    txt(s, big, { x: x + 0.3, y: y + 0.15, w: tw - 0.6, h: 0.85, fontSize: 36, bold: true, color: C.navy, valign: "middle" });
    txt(s, small, { x: x + 0.3, y: y + 1.05, w: tw - 0.6, h: th - 1.15, fontSize: 14, valign: "top" });
  });
  caption(s, "Parked and driving separate clearly: one-second vibration median 0.03 parked; while driving median 1.39, 95th percentile 3.2, maximum 5.09.",
    M, top + 2 * th + g + 0.1, lw, 0.6);
  const rx = M + lw + 0.35, rw = W - M - rx;
  dashedCard(s, rx, top, rw, 5.35);
  txt(s, "Not captured, so still open", { x: rx + 0.3, y: top + 0.15, w: rw - 0.6, h: 0.4, fontSize: 18, bold: true, color: C.accent });
  bullets(s, [
    "No GNSS fix in any record (no antenna fitted): R4 untested on the vehicle, and no speed",
    "No raw 200 Hz samples (v0.7.4) and no run markers: RQ1 and RQ4 not answered yet",
    "LTE upload down: no latency",
    "Driving found afterwards from battery current and vibration; no gear or speed signal",
    "Next: a second, shorter session with the raw stream (v0.7.5), a working GNSS antenna, timed runs and the powertrain baseline on stands",
  ], { x: rx + 0.3, y: top + 0.7, w: rw - 0.6, h: 4.5, fontSize: 15 });
}

// ---------------- 14 Conclusions ----------------
{
  const s = content("Conclusions and next steps",
    "To conclude. Every subsystem runs together, now on the vehicle: two IMUs at 200 hertz, fused; a database that lost nothing across an outage; detection in about 50 milliseconds at the front; an approaching-object warning; and both cameras on the existing dashboard. " +
    "What remains is the second road session with raw data and GNSS for RQ1 and RQ4, the real approach test, glance time for RQ2, and a separate supply for the telemetry unit. " +
    "Thank you, I'm happy to take questions.");
  const cw = (W - 2 * M - 0.4) / 2, cy = 1.4, ch = 4.45;
  card(s, M, cy, cw, ch);
  txt(s, "Done and measured", { x: M + 0.35, y: cy + 0.2, w: cw - 0.7, h: 0.45, fontSize: 20, bold: true, color: C.navy });
  bullets(s, [
    "Two IMUs at 200 Hz, fused; held on the vehicle (R1)",
    "112 of 112 records stored across an LTE outage",
    "Front detection 51 to 54 ms on the Pi 5 (Pi 4: about 120 ms)",
    "Approaching-object warning: synthetic tests within 2 %",
    "Both cameras on the existing dashboard, live data only",
    "Battery under load on the vehicle (R5); seven faults fixed",
  ], { x: M + 0.35, y: cy + 0.85, w: cw - 0.7, h: ch - 1.0, fontSize: 16 });
  const x2 = M + cw + 0.4;
  dashedCard(s, x2, cy, cw, ch);
  txt(s, "Open, and next", { x: x2 + 0.35, y: cy + 0.2, w: cw - 0.7, h: 0.45, fontSize: 20, bold: true, color: C.accent });
  bullets(s, [
    "Second road session: raw samples, GNSS, timed runs (RQ1, RQ4)",
    "Real approach test (C11), fusion and focal calibration (C9)",
    "Glance time on the vehicle (RQ2); latency with GNSS time",
    "Own supply for the telemetry unit; measure each unit's power",
    "Fit-test the printed enclosures on the vehicle",
  ], { x: x2 + 0.35, y: cy + 0.85, w: cw - 0.7, h: ch - 1.0, fontSize: 16 });
  txt(s, "Thank you. Questions?", { x: M, y: 6.05, w: W - 2 * M, h: 0.6, fontSize: 26, bold: true, color: C.navy, align: "center", valign: "middle" });
}

// ---------------- talking points ----------------
function writeScript(file) {
  const words = (t) => t.split(/\s+/).filter(Boolean).length;
  const total = script.reduce((n, [, , t]) => n + words(t), 0);
  let md = "# SW7 final presentation: talking points\n\n" +
    `Generated from the speaker notes by Presentation/source/build_deck.js; edit the notes there, not here. The timed version with cuts is SW7_Speaker_Script.md.\n\n` +
    `${TOTAL_MAIN} slides, 10 minutes plus questions. ${total} words in total, about ${Math.round(total / 140 * 10) / 10} minutes at 140 words a minute.\n`;
  for (const [n, title, notes] of script)
    md += `\n## Slide ${n}: ${title} (${words(notes)} words)\n\n${notes}\n`;
  fs.writeFileSync(file, md);
  console.log("wrote", file, `(${total} words)`);
}

const out = process.argv[2] || path.join(__dirname, "..", "SW7_Final_Presentation.pptx");
pres.writeFile({ fileName: out }).then((f) => {
  console.log("wrote", f);
  writeScript(path.join(path.dirname(out), "SW7_Talking_Points.md"));
});
