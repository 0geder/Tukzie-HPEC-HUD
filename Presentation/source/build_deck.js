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
    "It is part of the TUKZIE programme, which is building a 72 volt electric cargo trike for last-mile freight. " +
    "My part is the on-board electronics: a telemetry unit that measures how the trike rides, and a way of showing the driver only what matters for safety. " +
    "In the next ten minutes I'll cover why this is needed, how I built and tested it, what the results show, and what is left.");
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
    "Two facts frame the project. First, electric trikes can make economic sense for freight in African cities: on the routes a 2025 study examined in Dar es Salaam, an electric cargo tricycle cut operating cost per kilometre by 45.5 percent against a motorcycle and up to 86 percent against a light car. " +
    "Second, anything that pulls the driver's eyes off the road is a risk. NHTSA guidance says a single glance away should not exceed two seconds, so the driver should see only short, safety-relevant alerts. " +
    "The open problem is bringing edge telemetry and that kind of sparse driver information together on a low-cost trike, and measuring whether each part works.");
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
    "The aim is a low-cost unit that characterises the trike's ride at the edge and gives the driver only safety-relevant information. I split that into four research questions, and I've marked honestly where each one stands. " +
    "RQ1, two IMUs at 200 hertz agreeing within noise, is verified on the bench. " +
    "RQ3, bounded latency, measured data loss and recovery, is also verified on the bench: no dropped samples, a measured camera latency, and automatic recovery after the signal is cut. It still needs the moving vehicle. " +
    "RQ4, separating road from powertrain vibration, passes its self-tests but needs road data. " +
    "RQ2 changed during the project, with my supervisor's agreement. The trike already has a dashboard that shows what a HUD would show, and a second display adds distraction, so the camera's alerts now go on that dashboard instead.");
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
    "This is the whole system on the bench. The telemetry unit is an ESP32-S3 on a Makerfabs board with a built-in A7670X LTE modem, which also gives GNSS. Two MPU6050 IMUs are sampled at 200 hertz each, the battery management system is read over Bluetooth Low Energy, and a hardware counter is ready for the motor's Hall sensor. " +
    "On the camera side, a Raspberry Pi 4 runs the object detector, and three time-of-flight distance sensors facing left, ahead and right. " +
    "The two boards share one wire: the ESP32 sends a pulse every half second that the Pi logs, so camera and IMU data can be lined up in time. " +
    "I use the Pi 4 rather than the team's Pi 5, so the dashboard running on the Pi 5 is not disturbed.");
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
    "The firmware runs on FreeRTOS and is split across the two cores. " +
    "Core 1 holds everything timing-critical: one task per IMU at the highest priority, each holding a 5 millisecond period with vTaskDelayUntil so the rate cannot drift. " +
    "The acquisition tasks never print or block. They time-stamp each sample with a microsecond clock and push it into a bounded queue; if a queue is full the sample is dropped and counted, so a slow consumer can never stall acquisition. " +
    "Core 0 handles the slow, blocking work: the modem, GNSS, MQTT and the flash log in one task, because the modem's serial line has no lock, plus the battery link and the Hall counter, which counts pulses in hardware.");
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
  bx(qx + 0.3, py + 0.65, qw - 0.6, 1.3, "ModemTask", "AT commands, GNSS, MQTT, signal quality, flash log written once a minute");
  bx(qx + 0.3, py + 2.1, qw - 0.6, 0.8, "BmsTask", "battery over BLE");
  bx(qx + 0.3, py + 3.05, qw - 0.6, 0.8, "HallTask", "hardware pulse counter");
  txt(s, "The modem UART has no lock, so all modem traffic stays in one task.",
    { x: qx + 0.3, y: py + 3.95, w: qw - 0.6, h: 0.7, fontSize: 12, italic: true, color: C.muted, valign: "top" });
}

// ---------------- 6 Approach ----------------
{
  const s = content("Approach: prove each stage before building on it",
    "My method was staged verification. Each interface was brought up on its own on the real board, with a pass criterion written down before the test, before anything was built on top of it. " +
    "Then both IMUs at 200 hertz, calibrated against gravity. Then the ride features and the fusion, each with a self-test at boot. Then the local log and the LTE publish. " +
    "The last stage, validation on the moving vehicle, is still to come, and it's drawn dashed for that reason. " +
    "This order paid off: most of the faults I'll show shortly would have been very hard to trace if I'd integrated everything first.");
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
  txt(s, "Stages 1 to 4 are complete on the bench. Stage 5 depends on vehicle access and is the main outstanding work.",
    { x: M, y: 5.4, w: W - 2 * M, h: 0.6, fontSize: 18, italic: true, color: C.muted, align: "center" });
}

// ---------------- 7 IMU acquisition and fusion ----------------
{
  const s = content("Result: 200 Hz acquisition and dual-IMU fusion",
    "First results. Both IMUs run at 200 hertz with zero dropped samples, and the drop counters prove that rather than assuming it. " +
    "Two identical accelerometers disagreed by about 8 percent at rest; a per-sensor calibration against gravity brought that down to noise. " +
    "The two are then fused. With equal noise on both, inverse-variance weighting reduces to the mean. Windows are paired only if they end within half a window of each other, a disagreement figure is reported rather than hidden, and if one sensor goes silent for three seconds the output falls back to the other. " +
    "In this recorded 150 second session all 149 windows were fused from both sensors with under a millisecond of skew. " +
    "One honest finding: the calibration only holds in the orientation it was taken in, so it will be redone once the sensors are mounted on the trike.");
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
    "Equal-weight mean (inverse-variance weighting with equal noise)",
    "Paired only if windows end within 500 ms",
    "Disagreement figure reported, not hidden",
    "One-sensor fallback after 3 s of silence",
    "5 / 5 boot self-tests passed",
  ], { x: rx + 0.3, y: gy + 0.62, w: rw - 0.6, h: rh - 0.75, fontSize: 15 });
}

// ---------------- 8 Found and fixed ----------------
{
  const s = content("What testing found, and how it was fixed",
    "Testing each stage on real hardware against a stated pass criterion found six faults that assumptions had hidden. " +
    "The GNSS reply had a different layout from the one assumed, so the first outdoor fix put the trike in the sea; the parser now anchors on the hemisphere letter. " +
    "The modem was switching itself off after every reprogramming, because its power key toggles. " +
    "The battery checksum included one byte too many, so every real frame failed by exactly three. " +
    "Flash writes stalled both IMUs; I proved it by switching the log off, and the log is now buffered and written six times less often. " +
    "Reading the log back showed most records were invalid JSON. " +
    "And the pink camera image came from a module with no infrared filter, which I showed by comparing tuning files on the same scene.");
  const items = [
    ["GNSS reply layout", "Assumed degrees and minutes in fixed places; the real reply is decimal degrees with a varying layout, so satellite counts were read as the position. Parser now anchors on the hemisphere letter: median 2.7 m from the reference."],
    ["Modem switched itself off", "Its power key toggles, so pulsing it at every boot turned a running modem off after each reprogramming. Now pulsed only if the modem does not answer."],
    ["Battery checksum", "Summed the register byte as well, so every real frame failed by exactly 3. The protocol's own query frame showed the rule. After the fix: valid readings, 74.78 V and 60%."],
    ["IMU stalls from flash writes", "33 to 40 ms gaps every 10 s on both IMUs. Logging off: worst gap 5.9 ms, so the flash is the cause. The log is now buffered and written once a minute."],
    ["Stored log not valid JSON", "Reading 6,020 records back found 5,545 holding nan, which JSON does not allow, and the same text went over MQTT. Now written as null; all records parse."],
    ["Pink camera image", "The module has no infrared filter: the same scene was pink with the standard tuning and neutral with the NoIR one. With saturation 1.8 the colour cards read correctly."],
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
    "Three more bench results. Timing: the Pi now takes each sync edge's time from the kernel, and over 121 edges the median interval was 500.06 milliseconds with a spread under 0.7 milliseconds, so the camera and IMU clocks can be related precisely. A loose jumper twice produced false edges, so the vehicle needs a latched connector. " +
    "Position: on a rooftop, 104 fixes were a median of 2.7 metres from a phone's position, and 95 percent within 11 metres. " +
    "Cellular: 47 of 47 publishes were acknowledged. When I cut the radio for 60 seconds, the firmware detected the loss in under a second and reconnected about 5 seconds after the signal came back. Every record is also logged to flash, and all 6,020 stored records were read back.");
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
    ["95% within 11 m",
     "3D fix 105 s after a cold start, 23 to 25 satellites",
     "Speed units still to confirm on the vehicle"]);
  col(M + 2 * (cw + g), "Cellular link", "47 / 47", "MQTT publishes acknowledged",
    ["Radio cut for 60 s: loss seen in 0.8 s, reconnected about 5 s after it returned",
     "Every record also logged to flash: 6,020 read back",
     "Signal strength sent with each record"]);
}

// ---------------- 10 Camera, alerts, distance ----------------
{
  const s = content("Camera hazard detection and distance sensing",
    "The camera's role grew, on supervisor direction, from a visual record to hazard awareness. I designed and 3D printed the three-part casing on the left, with a 30 degree corner mount. " +
    "The detector is a pretrained 8-bit SSD-MobileNet sized for the Pi 4, with no training of my own. Using all four cores it runs at 19.5 frames per second, with a median of 102 milliseconds from the sensor to a result. With the three-frame debounce an alert comes about 0.2 seconds after an object appears, about 1.7 metres at 30 kilometres per hour. " +
    "An alert clears only after five empty frames, which stopped one person producing 16 alerts in 47 seconds. Only five fields are logged and no frame is stored. " +
    "For close range, three time-of-flight sensors stand in until the 8 by 8 zone sensor arrives.");
  const ih = 5.35, iw = ih * 1827 / 1306;
  s.addImage({ path: A("casing_labelled.png"), x: M, y: 1.4, w: iw, h: ih });
  const x = M + iw + 0.4, w = W - M - x;
  const blocks = [
    ["Object detector", "Pretrained 8-bit SSD-MobileNet on the Pi 4. 19.5 fps, median 102 ms from sensor to result; an alert about 0.2 s after an object appears."],
    ["Alert logic", "Raised after 3 frames, cleared after 5 empty frames. Five fields logged per alert; frames are never stored."],
    ["Distance sensors", "Three VL53L0X stand in for the VL53L5CX: left, ahead and right at 31 readings/s each; labels confirmed by covering each."],
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
  const s = content("Hazard alerts on the existing dashboard",
    "This is where RQ2 now lands. Instead of a separate windshield display, I wrote a camera page for the dashboard the TUKZIE team already runs. " +
    "Three reasons: that dashboard already carries what a HUD would show, two displays compete for the driver's attention, and the programme's move towards autonomy makes the camera's alerts more useful than a second screen. " +
    "It now runs as the default dashboard on the team's Pi 5, in a separate copy so their own build is untouched. The Pi 4 sends the ESP32, distance-sensor and camera data over Wi-Fi twice a second, and the dashboard shows only real values, with dashes where data is missing. " +
    "This Sensors page shows the three distance sensors and the fused hazards: here the camera recognises an object and the distance sensor gives its range. If anything is in the immediate band, a red banner appears over whichever page the driver is on. " +
    "What's still open is the glance-time check on the vehicle, and a design review against the NHTSA two-second rule and the ISO legibility standard.");
  const iw = 7.4, imW = 5.2, ih = imW * 800 / 1280;
  s.addImage({ path: A("sensors_page.png"), x: M, y: 1.4, w: imW, h: ih });
  txt(s, "Sensors page on the Pi 5, live data: distance gauges and hazards, nearest first.",
    { x: M, y: 1.4 + ih + 0.08, w: iw, h: 0.35, fontSize: 13, italic: true, color: C.muted });
  const wy = 1.4 + ih + 0.55, wh = 6.75 - wy;
  card(s, M, wy, iw, wh);
  txt(s, "Why not a windshield HUD", { x: M + 0.3, y: wy + 0.12, w: iw - 0.6, h: 0.38, fontSize: 16, bold: true, color: C.navy });
  bullets(s, [
    "The dashboard already shows what a HUD would",
    "Two displays compete for the driver's attention",
    "A move towards autonomy makes the camera more useful",
  ], { x: M + 0.3, y: wy + 0.55, w: iw - 0.6, h: wh - 0.6, fontSize: 14 });
  const rx = M + iw + 0.35, rw = W - M - rx;
  card(s, rx, 1.4, rw, 5.35);
  txt(s, "Running on the dashboard's Pi 5", { x: rx + 0.3, y: 1.55, w: rw - 0.6, h: 0.45, fontSize: 18, bold: true, color: C.navy });
  bullets(s, [
    "Default dashboard at boot; team's copy untouched",
    "Live sensor data every 0.5 s",
    "Camera + distance fusion shown live",
    "Red banner over any page for immediate hazards",
    "Street map with routing; campus tiles cached",
  ], { x: rx + 0.3, y: 2.1, w: rw - 0.6, h: 3.3, fontSize: 15 });
  txt(s, [{ text: "Still open: ", options: { bold: true, color: C.accent } }, { text: "glance time on the vehicle, and a design review against NHTSA and ISO 15008." }],
    { x: rx + 0.3, y: 5.55, w: rw - 0.6, h: 1.0, fontSize: 15, valign: "top" });
}

// ---------------- 12 Conclusions ----------------
{
  const s = content("Conclusions and next steps",
    "To conclude. Every subsystem runs together on the target board: two IMUs at 200 hertz with no loss, calibrated and fused; GNSS within about 3 metres; the battery read over Bluetooth; a cellular link that recovers by itself; a full local log; camera alerts in about a tenth of a second; and the camera and distance sensors fused and shown live on the existing dashboard. " +
    "Each fault was found by a test with a stated pass criterion, then fixed and tested again. " +
    "What's left is the vehicle: mount and recalibrate the unit in place, then the field test that answers the ride and latency questions on the move, calibrate and validate the fusion, and fit the zoned distance and air-quality sensors when they arrive. Thank you, I'm happy to take questions.");
  const cw = (W - 2 * M - 0.4) / 2, cy = 1.4, ch = 4.45;
  card(s, M, cy, cw, ch);
  txt(s, "Done on the bench", { x: M + 0.35, y: cy + 0.2, w: cw - 0.7, h: 0.45, fontSize: 20, bold: true, color: C.navy });
  bullets(s, [
    "Two IMUs at 200 Hz, no loss, calibrated and fused",
    "GNSS within 2.7 m median; battery read over BLE",
    "Cellular publish with automatic recovery; full local log",
    "Camera + distance fusion live on the Pi 5 dashboard",
    "Each fault found by a test, fixed and re-tested",
  ], { x: M + 0.35, y: cy + 0.85, w: cw - 0.7, h: ch - 1.0, fontSize: 16 });
  const x2 = M + cw + 0.4;
  dashedCard(s, x2, cy, cw, ch);
  txt(s, "Next", { x: x2 + 0.35, y: cy + 0.2, w: cw - 0.7, h: 0.45, fontSize: 20, bold: true, color: C.accent });
  bullets(s, [
    "Mount on the trike and recalibrate in place",
    "Field test: ride features (RQ4), latency and loss on the move (RQ3)",
    "Calibrate and validate the fusion (test C9)",
    "Check the battery against its app; wire the Hall tap",
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
