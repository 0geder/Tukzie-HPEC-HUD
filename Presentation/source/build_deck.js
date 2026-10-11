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
    "I built its on-board electronics: a telemetry unit that measures how the trike rides and sends the data to a central database, and safety alerts on the dashboard the trike already has.");
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
    "First, electric trikes make economic sense for freight in African cities. On delivery routes studied in Dar es Salaam, an electric cargo tricycle cut the operating cost per kilometre by 45.5 percent against a motorcycle, and by up to 86 percent against a light car. " +
    "Second, anything that takes the driver's eyes off the road is a risk. NHTSA guidance limits a single glance to two seconds. " +
    "So the open problem is to combine edge telemetry with short, safety-only driver information on a low-cost trike, and to measure whether each part works.");
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
    "These are my four research questions, and where each one honestly stands. " +
    "RQ1 asks how accurately and repeatably a low-cost unit can characterise the trike's ride. The instrument is verified on the bench; repeatability on the vehicle is not measured yet. " +
    "RQ2 asks how to show safety alerts on the existing dashboard with the least distraction. It moved from a head-up display to that dashboard with my supervisor's agreement, because a second screen adds distraction. Glance time is not measured yet. " +
    "RQ3 asks about latency, data loss and recovery. Loss and recovery now pass a ten-minute outage test; end-to-end latency still needs GNSS time outdoors. " +
    "RQ4, separating road from powertrain vibration, has passed self-tests only, because it needs road data.");
  // status styles: "bench" filled sky, "part" filled navy, "open" dashed orange outline
  const rows = [
    ["RQ1", "How accurately and repeatably can a low-cost edge unit characterise the trike's ride response?", "Instrument only", "part"],
    ["RQ2", "Which layout and update strategy show safety alerts on the existing dashboard with least distraction?", "Glance untested", "open"],
    ["RQ3", "What latency, data loss and recovery from sensor through local log to the LTE link?", "Loss tested", "bench"],
    ["RQ4", "Which ride features separate road-induced from powertrain vibration?", "Self-test only", "open"],
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

// ---------------- 4 System ----------------
{
  const s = content("The system on the bench",
    "This is the system on the bench. The telemetry unit is an ESP32-S3 with a built-in LTE modem that also gives GNSS. It samples two MPU6050 IMUs at 200 hertz each, reads the battery over Bluetooth, and has a hardware counter for the motor's Hall sensor. " +
    "Every record goes to a local log and over LTE to a central database on the team's Pi 5. " +
    "A Raspberry Pi 4 runs the camera detector and three time-of-flight distance sensors. " +
    "One wire links the boards: the ESP32 pulses it every half second and the Pi logs each edge, so camera and IMU data can be lined up in time.");
  const ih = 5.55, iw = ih * 1845 / 1349;
  s.addImage({ path: A("bench_labelled.png"), x: M, y: 1.35, w: iw, h: ih });
  const x = M + iw + 0.45, w = W - M - x;
  const blocks = [
    ["Telemetry unit", "ESP32-S3, LTE and GNSS: ride features, local log, MQTT to a central database on the Pi 5"],
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
    "Core 1 holds the timing-critical work: one task per IMU at the highest priority, each on a fixed 5 millisecond period. " +
    "They never print or block: each sample is time-stamped and pushed into a bounded queue, and if it is full the sample is dropped and counted. " +
    "Core 0 does the blocking work: the modem, GNSS, MQTT and the flash log, in one task because the modem's serial line has no lock. " +
    "Version 0.7.4, flashed in October, gives every record a sequence number, replays the backlog after an outage, and moves the IMU filter from 260 to 94 hertz, against aliasing at 200 hertz sampling.");
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
}

// ---------------- 6 Approach ----------------
{
  const s = content("Approach: prove each stage before building on it",
    "My method was staged verification. Each interface was brought up alone on the real board, against a pass criterion written before the test. " +
    "Then both IMUs at 200 hertz, calibrated; then the ride features and fusion, each self-tested at boot; then the log, the LTE publish and the replay to the database. " +
    "The last stage, the moving vehicle, is drawn dashed. " +
    "This order is why the faults I'll show next could each be traced to one change.");
  const steps = [
    ["Bring up", "each interface alone on the target board"],
    ["Acquire", "both IMUs at 200 Hz, calibrate to gravity"],
    ["Compute", "ride features and dual-IMU fusion, self-tested"],
    ["Store and send", "log to flash, publish over LTE, replay after an outage"],
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
    "First results. Both IMUs run at 200 hertz with no dropped samples, counted, not assumed. " +
    "Flash writes cause gaps of 33 to 40 milliseconds, now once a minute, and the queue holds the samples through each one. " +
    "Uncalibrated, the two accelerometers read about 8 percent apart in an earlier session. A factor per sensor against gravity brings both to 9.80 or 9.81 at calibration, but it only holds in that orientation, so it will be redone once mounted. " +
    "With equal noise, inverse-variance fusion reduces to the mean. Windows are paired only if they end within half a window, the disagreement is reported, and if one sensor goes silent the other takes over. " +
    "In a 150 second session all 149 windows were fused with under a millisecond of skew.");
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
    "Flash gaps 33 to 40 ms, once a minute",
    "Uncalibrated: 8% apart (earlier run)",
    "Calibration holds in one orientation",
  ], { x: rx + 0.3, y: gy + 0.62, w: rw - 0.6, h: rh - 0.75, fontSize: 13 });
}

// ---------------- 8 Found and fixed ----------------
{
  const s = content("Seven fault investigations: symptom, test, cause, fix",
    "The report works through seven faults that needed a real diagnosis: symptom, candidate causes, deciding test, and fix. Here is one in full. " +
    "The Raspberry Pi 4 kept throttling and rebooting. It could have been its own supply, the distance-sensor board, the telemetry unit on its USB port, or heat. " +
    "A logger recorded the power flags every two seconds. With nothing attached, the flags were clear. Fourteen seconds after the telemetry unit was plugged in, when its modem came up, under-voltage began. " +
    "With the unit on the Pi, there were three restarts in twenty minutes; moved off the Pi, none in four hours. " +
    "The others follow the same pattern, from a GNSS reply in an unexpected layout to a battery checksum off by exactly three. " +
    "The outage test found an eighth: a broker setting that silently stopped delivery to the database.");
  const items = [
    ["Boot loop, full flash", "Seen: reset once a second at one address. Tests: PSRAM setting, all overrides off, ROM banner. Cause: quad mode asked, chip runs dual (DIO). Fix: size, mode and table set together."],
    ["GNSS reply layout", "Seen: first fix near 0, 0. Test: raw replies logged: 17 fields in decimal degrees, not 13 as assumed. Fix: parser anchors on the hemisphere letter; median 2.7 m."],
    ["Battery checksum", "Seen: every frame rejected. Test: the firmware's own query frame shows the rule. Cause: register byte summed too, so each reply failed by 3. Fix: 14 valid records, 74.78 V."],
    ["Invalid JSON in the log", "Seen: 5,545 of 6,020 records failed to parse. Test: indexed, length-checked read-back: all intact, so not transfer. Cause: nan for missing values. Fix: null; all parse."],
    ["Camera colour cast", "Seen: pink image. Tests: stills with the standard and the NoIR tuning. Cause: no infrared-cut filter, not channel order. Fix: NoIR tuning plus saturation 1.8."],
    ["Distance-sensor hang", "Seen: nulls, then a frozen reader. Test: bus scan; driver timeout found to be zero, wait for ever. Fix: 0.5 s timeout, wiring re-seated; all three read again."],
    ["Pi 4 under-voltage, reboots", "Candidates: supply, sensor board, telemetry unit on USB, heat. Test: power flags every 2 s: under-voltage 14 s after the modem came up. Unit moved off: 3 restarts in 20 min, then none in 4 h."],
    ["Found in the outage test", "Seen: records at the broker, none in the database. Cause: the ingest's persistent broker session stopped delivering while connected. Fix: made opt-in; missed records backfilled from the unit's log."],
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

// ---------------- 9 Timing, position, cellular ----------------
{
  const s = content("Result: timing, position, and no data lost in an outage",
    "Timing first: over 121 sync edges the median interval was 500.06 milliseconds with a spread under 0.7, so camera and IMU clocks line up precisely. " +
    "Position: on a rooftop, 104 fixes were a median of 2.7 metres from a phone, and indoors the modem gives a network position stated to 550 metres. " +
    "The main new result is the outage test. With version 0.7.4 I switched the radio off for ten minutes. The unit built up 60 records, reconnected 5.2 seconds after the radio came back, and cleared the backlog in about 40 seconds. " +
    "The database on the Pi 5 holds 112 of 112 records, and 111 of 111 against the unit's own log, so nothing was lost. " +
    "Two limits: the public test broker does not queue, so reading the log back is the safety net, and latency needs GNSS time outdoors.");
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
     "Assisted GNSS loads; effect on fix time not yet measured",
     "Indoors: network position in 0.7 s, 550 m stated"]);
  col(M + 2 * (cw + g), "10-minute LTE outage (T15)", "112 / 112", "records stored in the Pi 5 database, none missing or doubled",
    ["60 records built up; reconnected 5.2 s after radio on",
     "Backlog cleared in 37 to 43 s; 111 of 111 against the unit's log",
     "Public broker does not queue: log read-back is the safety net",
     "Latency not yet measured (no GNSS time indoors)"]);
}

// ---------------- 10 Camera, alerts, distance ----------------
{
  const s = content("Camera hazard detection and distance sensing",
    "The camera's role grew, on supervisor direction, from a visual record to hazard awareness. I designed and 3D printed this casing. " +
    "The live detector is a pretrained 8-bit SSD-MobileNet. On its own it ran at 19.5 frames per second, 102 milliseconds from sensor to result. With everything else running on a healthy Pi 4 it is 14.6 frames per second and about 120 milliseconds, and that is the figure for the system. " +
    "An alert needs three frames to raise and five empty frames to clear, and no frame is stored. " +
    "COCO has no potholes, so I trained my own model: 0.71 mAP at 50 on validation tiles. On the Pi it finds the pothole in a test image at confidence 0.63, but only one run every four seconds fits beside the main detector, so it is off by default.");
  const ih = 5.35, iw = ih * 1827 / 1306;
  s.addImage({ path: A("casing_labelled.png"), x: M, y: 1.4, w: iw, h: ih });
  const x = M + iw + 0.4, w = W - M - x;
  const blocks = [
    ["Object detection (tested)", "SSD-MobileNet, 8-bit. Full system, healthy Pi 4: 14.6 fps, about 120 ms median. Detector alone (benchmark): 19.5 fps, 102 ms."],
    ["Pothole path (built, off by default)", "Own model: mAP@50 0.714 (validation; held-out pending). On the Pi: found at 0.63 in a test image; only 0.25 Hz fits beside the detector."],
    ["Alert logic", "Raised after 3 frames, cleared after 5 empty frames. Five fields logged per alert; frames are never stored."],
    ["Distance sensors", "Three VL53L0X (left, ahead, right) stand in for the VL53L5CX. 0.5 s timeout; hand test 80 to 264 mm ahead."],
  ];
  const bg = 0.15, bh = (5.35 - 3 * bg) / 4;
  blocks.forEach(([h, b], i) => {
    const y = 1.4 + i * (bh + bg);
    card(s, x, y, w, bh);
    txt(s, h, { x: x + 0.25, y: y + 0.1, w: w - 0.5, h: 0.36, fontSize: 16, bold: true, color: C.navy });
    txt(s, b, { x: x + 0.25, y: y + 0.46, w: w - 0.5, h: bh - 0.5, fontSize: 13, valign: "top" });
  });
}

// ---------------- 11 Dashboard ----------------
{
  const s = content("Hazard alerts and navigation on the existing dashboard",
    "This is where RQ2 lands: my pages on the dashboard the team already runs, the default at boot on their Pi 5. " +
    "It shows only real values, with a chip that always reads LIVE, REPLAY, NO DATA or SIMULATED. " +
    "On the left, the Sensors page shows the distance gauges and fused hazards. An immediate hazard now shows as a red pill in the status bar, so it no longer covers the page. " +
    "In the middle is navigation with spoken directions, in a simulated drive that is clearly marked. " +
    "On the right is the new destination search: offline matches in under 20 milliseconds, and online suggestions in just over a second on the Pi. Pages change with a two-finger swipe. " +
    "These are tested offscreen; glance time on the vehicle is still open.");
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
    "Immediate hazard as a red pill in the status bar (no longer covers the page)",
    "Carousel page swipe: two fingers, three on the map; decided on release",
    "Turn banner, spoken directions; simulated drive clearly marked",
    "Network-position circle on the map when there is no fix",
  ], { x: M + 0.3, y: wy + 0.55, w: iw - 0.6, h: wh - 0.6, fontSize: 14 });
  const rx = M + iw + 0.35, rw = W - M - rx;
  card(s, rx, 1.4, rw, 5.35);
  txt(s, "Destination search (new)", { x: rx + 0.3, y: 1.52, w: rw - 0.6, h: 0.42, fontSize: 18, bold: true, color: C.navy });
  const sw = rw - 0.6, sh = sw * 800 / 1280;
  s.addImage({ path: A("search_results.png"), x: rx + 0.3, y: 2.0, w: sw, h: sh });
  bullets(s, [
    "Type-ahead from Photon, biased to the trike's position",
    "Offline matches in under 20 ms; Photon 1.1 to 1.4 s on the Pi 5",
    "Deployed on the Pi 5; not yet tried by hand",
  ], { x: rx + 0.3, y: 2.0 + sh + 0.15, w: rw - 0.6, h: 1.25, fontSize: 13 });
  txt(s, [{ text: "Still open: ", options: { bold: true, color: C.accent } }, { text: "glance time on the vehicle, against NHTSA and ISO 15008." }],
    { x: rx + 0.3, y: 6.05, w: rw - 0.6, h: 0.6, fontSize: 14, valign: "top" });
}

// ---------------- 12 Conclusions ----------------
{
  const s = content("Conclusions and next steps",
    "To conclude. Every subsystem runs together on the target hardware: two IMUs at 200 hertz, calibrated and fused; GNSS within about 3 metres; the battery over Bluetooth; a full local log; and now a central database that lost nothing across a ten-minute outage. " +
    "Camera detection takes about 120 milliseconds in the full system, and hazards, navigation and search run on the existing dashboard. " +
        "What remains is the vehicle: end-to-end latency with GNSS time, repeatability for RQ1, road data for RQ4, and glance time for RQ2. " +
    "Thank you, I'm happy to take questions.");
  const cw = (W - 2 * M - 0.4) / 2, cy = 1.4, ch = 4.45;
  card(s, M, cy, cw, ch);
  txt(s, "Done on the bench", { x: M + 0.35, y: cy + 0.2, w: cw - 0.7, h: 0.45, fontSize: 20, bold: true, color: C.navy });
  bullets(s, [
    "Two IMUs at 200 Hz, no loss, calibrated and fused",
    "GNSS 2.7 m median; battery over BLE; full local log",
    "112 of 112 records stored across an LTE outage",
    "Camera: about 120 ms, 14.6 fps in the full system",
    "Hazards, navigation and search on the Pi 5 dashboard",
    "Seven faults diagnosed, fixed and re-tested",
  ], { x: M + 0.35, y: cy + 0.85, w: cw - 0.7, h: ch - 1.0, fontSize: 16 });
  const x2 = M + cw + 0.4;
  dashedCard(s, x2, cy, cw, ch);
  txt(s, "Open, and next", { x: x2 + 0.35, y: cy + 0.2, w: cw - 0.7, h: 0.45, fontSize: 20, bold: true, color: C.accent });
  bullets(s, [
    "Road test (planned 14 Oct): mount, recalibrate, RQ1, RQ3 and RQ4 on the move",
    "End-to-end latency with GNSS time; a team broker with credentials",
    "Glance time on the vehicle (RQ2)",
    "Pothole: held-out score; a faster model to fit beside the detector",
    "Calibrate and validate the camera and distance fusion (C9)",
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
