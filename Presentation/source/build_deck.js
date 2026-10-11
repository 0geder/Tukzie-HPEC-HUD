// SW7 final presentation, 16:9, matching the A1 poster (UCT banner, navy numbered markers, light-blue cards).
// Also writes Presentation/SW7_Talking_Points.md from the speaker notes, so the script always matches the deck.
const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");
const A = (f) => path.join(__dirname, "assets", f);

const C = {
  navy: "14305C", sky: "1565C0", panel: "E8F0FA", accent: "D4700C",
  text: "1B1F24", muted: "4A5566", white: "FFFFFF", line: "C9D6E8",
};
const FONT = "Calibri";
const W = 13.333, H = 7.5, M = 0.6;

// The HUD was replaced by integration with the vehicle's existing dashboard (supervisor agreed 1 Oct 2026;
// title change captured by the course coordinator 2 Oct 2026). Keep TITLE the same in build_poster.js.
const TITLE = "Development of an Embedded HPEC Telemetry Unit\nand Dashboard Integration for the TUKZIE Rev 0 Platform";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "SW7: " + TITLE.replace("\n", " ");
pres.author = "Samson Okuthe";

let slideNo = 0;
const TOTAL_MAIN = 12;
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
    "Good morning. I'm Samson Okuthe, and my project is SW-7, supervised by Associate Professor Simon Winberg with Sampath Jayalath as co-supervisor. " +
    "It is part of TUKZIE, a 72 volt electric cargo trike for last-mile freight. " +
    "I built its on-board electronics: a telemetry unit that measures how the trike rides, and a way of showing the driver only what matters for safety. " +
    "I'll cover why, how I built and tested it, the results, and what is left.");
  txt(s, "EEE4022S Final Year Project 2026, Department of Electrical Engineering, University of Cape Town",
    { x: M, y: 0.35, w: W - 2 * M, h: 0.4, fontSize: 15, color: C.white, align: "center", shadow: shadow() });
  txt(s, TITLE,
    { x: M, y: 0.85, w: W - 2 * M, h: 1.6, fontSize: 34, bold: true, color: C.white, align: "center", valign: "middle", shadow: shadow() });
  txt(s, "Samson Okuthe (OKTSAM001)",
    { x: M, y: 2.5, w: W - 2 * M, h: 0.45, fontSize: 20, bold: true, color: C.white, align: "center", shadow: shadow() });
  txt(s, "Supervisor: A/Prof. Simon Winberg   |   Co-supervisor: Sampath Jayalath   |   Project SW-7",
    { x: M, y: 2.95, w: W - 2 * M, h: 0.4, fontSize: 16, color: C.white, align: "center", shadow: shadow() });
}

// ---------------- 2 Why ----------------
{
  const s = content("Why this matters",
    "Two facts frame the project. First, electric trikes make economic sense for freight in African cities: on routes studied in Dar es Salaam in 2025, an electric cargo tricycle cut operating cost per kilometre by 45.5 percent against a motorcycle and up to 86 percent against a light car. " +
    "Second, anything that takes the driver's eyes off the road is a risk: NHTSA guidance limits a single glance to two seconds. " +
    "The open problem is combining edge telemetry with that kind of sparse, safety-only driver information on a low-cost trike, and measuring whether each part works.");
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
    "The aim is a low-cost unit that characterises the ride at the edge and shows the driver only safety-relevant information. There are four research questions, marked honestly. " +
    "RQ1, two IMUs at 200 hertz agreeing within noise, is verified on the bench. " +
    "RQ3, bounded latency, measured loss and recovery, is verified on the bench but still needs the moving vehicle. " +
    "RQ4, separating road from powertrain vibration, passes its self-tests but needs road data. " +
    "RQ2 changed with my supervisor's agreement: the trike already has a dashboard showing what a HUD would show, and a second display adds distraction, so the alerts now go on that dashboard.");
  const rows = [
    ["RQ1", "Acquire two IMUs at 200 Hz (at least 160 Hz for ISO 2631-1) with the sensors agreeing within noise", "Bench-verified", "solid"],
    ["RQ2", "Show safety-critical alerts on the existing dashboard without exceeding the 2 s glance guidance", "Page tested", "dash"],
    ["RQ3", "Bounded latency, measured data loss and recovery from sensor through to the cellular link", "Bench-verified", "solid"],
    ["RQ4", "Ride features that separate road-induced from powertrain vibration", "Self-test only", "solid"],
  ];
  const y0 = 1.45, rh = 1.08, gap = 0.18;
  rows.forEach(([id, req, status, style], i) => {
    const y = y0 + i * (rh + gap);
    card(s, M, y, W - 2 * M, rh);
    txt(s, id, { x: M + 0.3, y, w: 1.0, h: rh, fontSize: 24, bold: true, color: C.navy, valign: "middle" });
    const bx = W - M - 2.75, open = style === "dash";
    txt(s, req, { x: M + 1.35, y, w: bx - M - 1.6, h: rh, fontSize: 18, valign: "middle" });
    const col = status === "Bench-verified" ? C.sky : open ? C.accent : C.navy;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: bx, y: y + 0.29, w: 2.45, h: 0.5, rectRadius: 0.25,
      fill: { color: open ? C.white : col }, line: { color: col, width: 1.5, dashType: style } });
    txt(s, status, { x: bx, y: y + 0.29, w: 2.45, h: 0.5, fontSize: 15, bold: true, color: open ? C.accent : C.white, align: "center", valign: "middle" });
  });
}

// ---------------- 4 System ----------------
{
  const s = content("The system on the bench",
    "This is the whole system on the bench. The telemetry unit is an ESP32-S3 with a built-in LTE modem that also gives GNSS. It samples two MPU6050 IMUs at 200 hertz each, reads the battery management system over Bluetooth, and has a hardware counter ready for the motor's Hall sensor. " +
    "A Raspberry Pi 4 runs the camera detector and three time-of-flight distance sensors facing left, ahead and right, apart from the team's Pi 5 so their dashboard is not disturbed. " +
    "One wire links the boards: the ESP32 pulses it every half second and the Pi logs each edge, so camera and IMU data can be lined up in time.");
  const ih = 5.55, iw = ih * 1845 / 1349;
  s.addImage({ path: A("bench_labelled.png"), x: M, y: 1.35, w: iw, h: ih });
  const x = M + iw + 0.45, w = W - M - x;
  const blocks = [
    ["Telemetry unit", "ESP32-S3 with LTE and GNSS: acquisition, ride features, local log, MQTT"],
    ["Two IMUs", "MPU6050s at 200 Hz each, fused into one ride estimate"],
    ["Battery and motor", "BMS over Bluetooth Low Energy; Hall pulse counter"],
    ["Camera", "Pi 4 and OV5647: object detector, time-aligned by a sync wire"],
    ["Distance sensors", "Three time-of-flight sensors on the Pi: left, ahead, right"],
  ];
  const bh = 0.95, bg = 0.2;
  blocks.forEach(([h, b], i) => {
    const y = 1.35 + i * (bh + bg);
    card(s, x, y, w, bh);
    txt(s, h, { x: x + 0.25, y: y + 0.08, w: w - 0.5, h: 0.34, fontSize: 16, bold: true, color: C.navy });
    txt(s, b, { x: x + 0.25, y: y + 0.42, w: w - 0.5, h: 0.5, fontSize: 13, color: C.text, valign: "top" });
  });
}

// ---------------- 5 Firmware ----------------
{
  const s = content("Firmware: deterministic acquisition first",
    "The firmware runs on FreeRTOS across the two cores. " +
    "Core 1 holds the timing-critical work: one task per IMU at the highest priority, each on a fixed 5 millisecond period, so the rate cannot drift. " +
    "These tasks never print or block. Each sample is time-stamped in microseconds and pushed into a bounded queue; if it is full the sample is dropped and counted, so a slow consumer can never stall acquisition. " +
    "Core 0 does the blocking work: the modem, GNSS, MQTT and the flash log in one task, because the modem's serial line has no lock, plus the battery link and the Hall counter.");
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
  bx(colA, py + 0.7, bw, 1.0, "Imu1Task", "200 Hz, priority 3");
  bx(colA, py + 2.05, bw, 1.0, "Imu2Task", "200 Hz, priority 3");
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
  bx(qx + 0.3, py + 0.65, qw - 0.6, 1.3, "ModemTask", "AT commands, GNSS with assisted GNSS, MQTT, signal quality, flash log once a minute");
  bx(qx + 0.3, py + 2.1, qw - 0.6, 0.8, "BmsTask", "battery over BLE");
  bx(qx + 0.3, py + 3.05, qw - 0.6, 0.8, "HallTask", "hardware pulse counter");
  txt(s, "The modem UART has no lock, so all modem traffic stays in one task.",
    { x: qx + 0.3, y: py + 3.95, w: qw - 0.6, h: 0.7, fontSize: 12, italic: true, color: C.muted, valign: "top" });
}

// ---------------- 6 Approach ----------------
{
  const s = content("Approach: prove each stage before building on it",
    "My method was staged verification. Each interface was brought up alone on the real board, against a pass criterion written before the test. " +
    "Then both IMUs at 200 hertz, calibrated; then the ride features and fusion, each self-tested at boot; then the log and the LTE publish. " +
    "The last stage, the moving vehicle, is drawn dashed: the first road test is planned for 14 October. " +
    "This order is why the faults I'll show could be traced.");
  const steps = [
    ["Bring up", "each interface alone on the target board"],
    ["Acquire", "both IMUs at 200 Hz, calibrate to gravity"],
    ["Compute", "ride features and dual-IMU fusion, self-tested"],
    ["Store and send", "log to flash, publish over LTE"],
    ["Validate", "on the moving vehicle"],
  ];
  const n = steps.length, gap = 0.28, sw = (W - 2 * M - (n - 1) * gap) / n, sy = 2.0, sh = 2.9;
  steps.forEach(([h, b], i) => {
    const x = M + i * (sw + gap), last = i === n - 1;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: sy, w: sw, h: sh, rectRadius: 0.12,
      fill: { color: last ? C.white : C.panel }, line: { color: last ? C.accent : C.panel, width: 2, dashType: last ? "dash" : "solid" } });
    s.addShape(pres.shapes.OVAL, { x: x + sw / 2 - 0.36, y: sy + 0.3, w: 0.72, h: 0.72, fill: { color: last ? C.accent : C.navy }, line: { color: last ? C.accent : C.navy } });
    txt(s, String(i + 1), { x: x + sw / 2 - 0.36, y: sy + 0.3, w: 0.72, h: 0.72, fontSize: 22, bold: true, color: C.white, align: "center", valign: "middle" });
    txt(s, h, { x: x + 0.15, y: sy + 1.2, w: sw - 0.3, h: 0.5, fontSize: 20, bold: true, color: last ? C.accent : C.navy, align: "center" });
    txt(s, b, { x: x + 0.2, y: sy + 1.75, w: sw - 0.4, h: 1.0, fontSize: 15, align: "center", valign: "top" });
    if (!last) s.addShape(pres.shapes.LINE, { x: x + sw + 0.03, y: sy + sh / 2, w: gap - 0.06, h: 0, line: { color: C.navy, width: 2, endArrowType: "triangle" } });
  });
  txt(s, "Stages 1 to 4 are complete on the bench. Stage 5: the first road test is planned for 14 October.",
    { x: M, y: 5.4, w: W - 2 * M, h: 0.6, fontSize: 18, italic: true, color: C.muted, align: "center" });
}

// ---------------- 7 IMU acquisition and fusion ----------------
{
  const s = content("Result: 200 Hz acquisition and dual-IMU fusion",
    "First results. Both IMUs run at 200 hertz with zero dropped samples, which the drop counters prove rather than assume. " +
    "Two identical accelerometers disagreed by about 8 percent at rest; a per-sensor calibration against gravity brought that down to noise. " +
    "With equal noise, inverse-variance fusion reduces to the mean. Windows are paired only if they end within half a window, the disagreement is reported, and if one sensor is silent for three seconds the other takes over. " +
    "In this 150 second session all 149 windows were fused with under a millisecond of skew. " +
    "A review also caught that my speed-normalised index used the mean square, which gravity dominates; version 0.7.2 uses the variance. " +
    "The calibration only holds in the orientation it was taken in, so it will be redone once mounted.");
  const stats = [
    ["200 Hz", "on both IMUs, zero dropped samples"],
    ["8%", "IMU gap at rest, calibrated down to noise"],
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
  txt(s, "Fusion rules", { x: rx + 0.3, y: gy + 0.15, w: rw - 0.6, h: 0.4, fontSize: 18, bold: true, color: C.navy });
  bullets(s, [
    "Equal-weight mean (inverse-variance, equal noise)",
    "Paired only if windows end within 500 ms",
    "Disagreement figure reported, not hidden",
    "One-sensor fallback after 3 s of silence",
    "5 / 5 boot self-tests passed",
    "Speed index: variance, not mean square (v0.7.2)",
  ], { x: rx + 0.3, y: gy + 0.62, w: rw - 0.6, h: rh - 0.75, fontSize: 14 });
}

// ---------------- 8 Found and fixed ----------------
{
  const s = content("What testing found, and how it was fixed",
    "Testing each stage against a stated pass criterion found faults that assumptions had hidden. " +
    "The GNSS reply had a different layout from the one assumed, so the first fix put the trike in the sea; the parser now anchors on the hemisphere letter. " +
    "The battery checksum included one byte too many, so every real frame failed by exactly three. " +
    "Flash writes stalled both IMUs; switching the log off proved it, and the log is now written six times less often. " +
    "The pink image came from a camera with no infrared filter. " +
    "Two are new. The Pi 4 kept browning out and rebooting because the ESP32's LTE modem drew its transmit current through the Pi's USB port; the ESP32 now needs its own powered hub, and a fan brought the Pi down from 81 degrees. " +
    "And the distance-sensor reader froze when one sensor stopped answering; a half-second timeout now skips it, and all three read.");
  const items = [
    ["GNSS reply layout", "Assumed degrees and minutes in fixed places; the real reply is decimal degrees with a varying layout, so satellite counts were read as the position. Parser now anchors on the hemisphere letter: median 2.7 m from the reference."],
    ["Battery checksum", "Summed the register byte as well, so every real frame failed by exactly 3. The protocol's own query frame showed the rule. After the fix: valid readings, 74.78 V and 60%."],
    ["IMU stalls from flash writes", "33 to 40 ms gaps every 10 s on both IMUs. Logging off: worst gap 5.9 ms, so the flash is the cause. The log is now buffered and written once a minute."],
    ["Pink camera image", "The module has no infrared filter: the same scene was pink with the standard tuning and neutral with the NoIR one. With saturation 1.8 the colour cards read correctly."],
    ["Pi 4 brown-outs and reboots", "Under-voltage began 14 s after the ESP32 was plugged into the Pi's USB, when its LTE modem came up: throttled to 600 MHz. Fix: a powered hub for the ESP32 (to fit). A fan took the Pi from 81 C to 48 to 57 C."],
    ["Distance-sensor reader hang", "One stuck sensor froze the whole reader. A 0.5 s I/O timeout now skips and logs it. All three read again: hand test 80 to 264 mm ahead, 157 to 199 mm right."],
  ];
  const cw = (W - 2 * M - 0.3) / 2, ch = 1.55, gy = 0.15;
  items.forEach(([h, b], i) => {
    const x = M + (i % 2) * (cw + 0.3), y = 1.35 + Math.floor(i / 2) * (ch + gy);
    card(s, x, y, cw, ch);
    txt(s, h, { x: x + 0.3, y: y + 0.1, w: cw - 0.6, h: 0.4, fontSize: 17, bold: true, color: C.navy });
    txt(s, b, { x: x + 0.3, y: y + 0.5, w: cw - 0.6, h: ch - 0.56, fontSize: 13, valign: "top" });
  });
  txt(s, "Each fault was found by a test, fixed, and the same test run again.",
    { x: M, y: 6.5, w: W - 2 * M, h: 0.35, fontSize: 15, italic: true, color: C.muted, align: "center" });
}

// ---------------- 9 Timing, position, cellular ----------------
{
  const s = content("Result: timing, position and the cellular link",
    "Three more bench results. Timing: the Pi takes each sync edge's time from the kernel, and over 121 edges the median interval was 500.06 milliseconds with a spread under 0.7, so the camera and IMU clocks can be related precisely. " +
    "Position: on a rooftop, 104 fixes were a median of 2.7 metres from a phone's position. Version 0.7.3 does what a phone does: assisted GNSS loads satellite data over LTE, and indoors the modem gives a network position in 0.7 seconds, stated to 550 metres, and here about 30 metres from the outdoor fix. " +
    "Cellular: 47 of 47 publishes were acknowledged, and after a 60 second radio cut the link recovered by itself about 5 seconds after the signal returned.");
  const n = 3, g = 0.35, cw = (W - 2 * M - (n - 1) * g) / n, cy = 1.4, ch = 5.35;
  const col = (x, title, big, bigSub, items) => {
    card(s, x, cy, cw, ch);
    txt(s, title, { x: x + 0.3, y: cy + 0.2, w: cw - 0.6, h: 0.45, fontSize: 19, bold: true, color: C.navy });
    txt(s, big, { x: x + 0.3, y: cy + 0.7, w: cw - 0.6, h: 0.9, fontSize: 40, bold: true, color: C.sky, valign: "middle" });
    txt(s, bigSub, { x: x + 0.3, y: cy + 1.6, w: cw - 0.6, h: 0.6, fontSize: 14, color: C.muted, valign: "top" });
    bullets(s, items, { x: x + 0.3, y: cy + 2.35, w: cw - 0.6, h: ch - 2.5, fontSize: 15 });
  };
  col(M, "Camera to IMU timing", "500.06 ms", "median sync interval over 121 edges, kernel timestamps",
    ["Spread under 0.7 ms",
     "Video frames placed on the IMU clock within 1 s",
     "A loose jumper twice gave false edges: a latched connector is needed"]);
  col(M + cw + g, "GNSS outdoors", "2.7 m", "median from a phone's position over 104 fixes",
    ["95% within 11 m; fix 105 s after a cold start",
     "Assisted GNSS loads (+AGPS: success); effect on fix time not yet measured",
     "Indoors: network position in 0.7 s, 550 m stated, about 30 m from the outdoor fix"]);
  col(M + 2 * (cw + g), "Cellular link", "47 / 47", "MQTT publishes acknowledged",
    ["Radio cut for 60 s: loss seen in 0.8 s, reconnected about 5 s after it returned",
     "Every record also logged to flash: 6,020 read back",
     "In progress: sequence numbers, backlog replay, central database (v0.7.4)"]);
}

// ---------------- 10 Camera, alerts, distance ----------------
{
  const s = content("Camera hazard detection and distance sensing",
    "The camera's role grew, on supervisor direction, from a visual record to hazard awareness. I designed and 3D printed this casing. " +
    "The live detector is a pretrained 8-bit SSD-MobileNet sized for the Pi 4: 19.5 frames per second and 102 milliseconds median from sensor to result in the benchmark, and 14.6 frames per second, about 120 milliseconds, in the latest check on a healthy Pi 4. " +
    "An alert needs three frames to raise and five empty frames to clear, which stopped one person causing 16 alerts in 47 seconds; no frame is stored. " +
    "COCO has no potholes, so I trained my own model: zero on South African dashcam footage at first, 0.71 mAP at 50 on validation tiles after training on the road band. Running it on the Pi is in progress. " +
    "Three time-of-flight sensors cover close range until the 8 by 8 zone sensor arrives.");
  const ih = 5.35, iw = ih * 1827 / 1306;
  s.addImage({ path: A("casing_labelled.png"), x: M, y: 1.4, w: iw, h: ih });
  const x = M + iw + 0.4, w = W - M - x;
  const blocks = [
    ["Object detection", "Live: pretrained SSD-MobileNet, 19.5 fps and 102 ms median (benchmark); 14.6 fps and about 120 ms on a healthy Pi 4 (Oct). Own pothole model: mAP@50 0.000 before, 0.714 after road-band tiles (validation); on the Pi: in progress."],
    ["Alert logic", "Raised after 3 frames, cleared after 5 empty frames. Five fields logged per alert; frames are never stored."],
    ["Distance sensors", "Three VL53L0X stand in for the VL53L5CX: left, ahead, right. Reader hang fixed (0.5 s timeout); all three reading: 80 to 264 mm ahead, 157 to 199 mm right in a hand test."],
  ];
  const bh = 1.65, bg = 0.2;
  blocks.forEach(([h, b], i) => {
    const y = 1.4 + i * (bh + bg);
    card(s, x, y, w, bh);
    txt(s, h, { x: x + 0.25, y: y + 0.12, w: w - 0.5, h: 0.4, fontSize: 17, bold: true, color: C.navy });
    txt(s, b, { x: x + 0.25, y: y + 0.52, w: w - 0.5, h: bh - 0.6, fontSize: 13, valign: "top" });
  });
}

// ---------------- 11 Dashboard ----------------
{
  const s = content("Hazard alerts and navigation on the existing dashboard",
    "This is where RQ2 lands: my pages on the dashboard the team already runs, now the default at boot on their Pi 5, with their own build untouched. " +
    "The Pi 4 sends ESP32, distance and camera data twice a second, and the dashboard shows only real values, with dashes where data is missing. " +
    "On the left, the Sensors page shows the distance gauges and fused hazards, and a red banner covers any page for an immediate hazard. " +
    "On the right is navigation: a Google-style turn banner with spoken directions. For indoor demonstrations a simulated drive moves every page in step under a yellow SIMULATED strip, and a status chip always reads LIVE, REPLAY, NO DATA or SIMULATED, so simulated numbers are never taken for real ones. " +
    "Pages change with a two-finger swipe, three on the map. " +
    "Still open: glance time on the vehicle, against the NHTSA two-second rule.");
  const iw = 7.4, imW = (iw - 0.2) / 2, ih = imW * 800 / 1280;
  s.addImage({ path: A("sensors_page.png"), x: M, y: 1.4, w: imW, h: ih });
  s.addImage({ path: A("nav_simulated.png"), x: M + imW + 0.2, y: 1.4, w: imW, h: ih });
  txt(s, "Sensors page, live data on the Pi 5",
    { x: M, y: 1.4 + ih + 0.06, w: imW, h: 0.3, fontSize: 12, italic: true, color: C.muted });
  txt(s, "Navigation during a simulated drive (labelled)",
    { x: M + imW + 0.2, y: 1.4 + ih + 0.06, w: imW, h: 0.3, fontSize: 12, italic: true, color: C.muted });
  const wy = 1.4 + ih + 0.5, wh = 6.75 - wy;
  card(s, M, wy, iw, wh);
  txt(s, "Added 7 to 11 Oct (tested offscreen, not yet on the vehicle)", { x: M + 0.3, y: wy + 0.12, w: iw - 0.6, h: 0.38, fontSize: 16, bold: true, color: C.navy });
  bullets(s, [
    "Turn banner and spoken turn-by-turn directions",
    "Simulated drive in step on every page, clearly marked",
    "Network-position circle on the map when there is no fix",
    "Finger scrolling; two-finger page swipe (three on the map)",
  ], { x: M + 0.3, y: wy + 0.55, w: iw - 0.6, h: wh - 0.6, fontSize: 14 });
  const rx = M + iw + 0.35, rw = W - M - rx;
  card(s, rx, 1.4, rw, 5.35);
  txt(s, "Running on the dashboard's Pi 5", { x: rx + 0.3, y: 1.55, w: rw - 0.6, h: 0.45, fontSize: 18, bold: true, color: C.navy });
  bullets(s, [
    "Default dashboard at boot; team's copy untouched",
    "Live sensor data every 0.5 s",
    "LIVE / REPLAY / NO DATA / SIMULATED chip",
    "Camera + distance fusion shown live",
    "Red banner over any page for immediate hazards",
    "In progress: Uber-style destination search",
  ], { x: rx + 0.3, y: 2.1, w: rw - 0.6, h: 3.4, fontSize: 15 });
  txt(s, [{ text: "Still open: ", options: { bold: true, color: C.accent } }, { text: "glance time on the vehicle, and a design review against NHTSA and ISO 15008." }],
    { x: rx + 0.3, y: 5.65, w: rw - 0.6, h: 0.95, fontSize: 15, valign: "top" });
}

// ---------------- 12 Conclusions ----------------
{
  const s = content("Conclusions and next steps",
    "To conclude. Every subsystem runs together on the target hardware: two IMUs at 200 hertz with no loss, calibrated and fused; GNSS within about 3 metres, with a network position indoors; the battery over Bluetooth; a cellular link that recovers by itself; a full local log; camera alerts in about a tenth of a second; and hazards, navigation and spoken directions on the existing dashboard. " +
    "Each fault was found by a test, fixed and tested again. " +
    "In progress: a central database with backlog replay, and the pothole model on the Pi. " +
    "Next is the vehicle: the road test on 14 October, then the fusion calibration. Thank you, I'm happy to take questions.");
  const cw = (W - 2 * M - 0.4) / 2, cy = 1.4, ch = 4.45;
  card(s, M, cy, cw, ch);
  txt(s, "Done on the bench", { x: M + 0.35, y: cy + 0.2, w: cw - 0.7, h: 0.45, fontSize: 20, bold: true, color: C.navy });
  bullets(s, [
    "Two IMUs at 200 Hz, no loss, calibrated and fused",
    "GNSS 2.7 m median; network position indoors; battery over BLE",
    "Cellular publish with automatic recovery; full local log",
    "Hazards, navigation and voice on the Pi 5 dashboard",
    "Each fault found by a test, fixed and re-tested",
  ], { x: M + 0.35, y: cy + 0.85, w: cw - 0.7, h: ch - 1.0, fontSize: 16 });
  const x2 = M + cw + 0.4;
  dashedCard(s, x2, cy, cw, ch);
  txt(s, "In progress and next", { x: x2 + 0.35, y: cy + 0.2, w: cw - 0.7, h: 0.45, fontSize: 20, bold: true, color: C.accent });
  bullets(s, [
    "In progress: central database, backlog replay (v0.7.4)",
    "In progress: pothole model on the Pi 4; destination search",
    "Road test (planned 14 Oct): mount, recalibrate, RQ3 and RQ4 on the move",
    "Calibrate and validate the fusion (test C9)",
    "Fit the VL53L5CX and SEN55 when they arrive",
  ], { x: x2 + 0.35, y: cy + 0.85, w: cw - 0.7, h: ch - 1.0, fontSize: 16 });
  txt(s, "Thank you. Questions?", { x: M, y: 6.05, w: W - 2 * M, h: 0.6, fontSize: 26, bold: true, color: C.navy, align: "center", valign: "middle" });
}

// ---------------- talking points ----------------
function writeScript(file) {
  const words = (t) => t.split(/\s+/).filter(Boolean).length;
  const total = script.reduce((n, [, , t]) => n + words(t), 0);
  let md = "# SW7 final presentation: talking points\n\n" +
    `Generated from the speaker notes by Presentation/source/build_deck.js; edit the notes there, not here.\n\n` +
    `${TOTAL_MAIN} slides, 10 minutes plus questions. ${total} words in total, about ${Math.round(total / 150 * 10) / 10} minutes at 150 words a minute.\n`;
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
