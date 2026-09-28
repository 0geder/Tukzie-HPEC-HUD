// SW7 final presentation, 16:9, matching the A1 poster (UCT banner, navy numbered markers, light-blue cards).
const pptxgen = require("pptxgenjs");
const path = require("path");
const A = (f) => path.join(__dirname, "assets", f);

const C = {
  navy: "14305C", sky: "1565C0", panel: "E8F0FA", accent: "D4700C",
  text: "1B1F24", muted: "4A5566", white: "FFFFFF", line: "C9D6E8",
};
const FONT = "Calibri";
const W = 13.333, H = 7.5, M = 0.6;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "SW7: Embedded telemetry unit and windshield HUD for the TUKZIE Rev 0";
pres.author = "Samson Okuthe";

let slideNo = 0;
const TOTAL_MAIN = 12;

function txt(s, t, o) { s.addText(t, Object.assign({ fontFace: FONT, color: C.text, isTextBox: true, margin: 0 }, o)); }
function card(s, x, y, w, h, fill = C.panel, line) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: fill }, line: line || { color: fill } });
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
  if (notes) s.addNotes(notes);
  return s;
}

function bannerSlide(notes) {
  const s = pres.addSlide();
  slideNo++;
  s.background = { color: C.navy };
  s.addImage({ path: A("uct_banner.jpg"), x: 0, y: 0, w: W, h: H, sizing: { type: "cover", w: W, h: H } });
  if (notes) s.addNotes(notes);
  return s;
}
const shadow = () => ({ type: "outer", color: "000000", blur: 6, offset: 2, angle: 45, opacity: 0.6 });

// ---------------- 1 Title ----------------
{
  const s = bannerSlide(
    "Good morning. I'm Samson Okuthe, and my project is SW-7, supervised by Associate Professor Simon Winberg with Sampath Jayalath as co-supervisor. " +
    "It is part of the TUKZIE programme, which is building a 72 volt electric cargo trike for last-mile freight. " +
    "My part is the on-board electronics: a telemetry unit that measures how the trike rides, and a windshield head-up display that shows the driver only what matters for safety. " +
    "In the next ten minutes I'll cover why this is needed, how I built and tested it, what the bench results show, and what is left.");
  txt(s, "EEE4022S Final Year Project 2026, Department of Electrical Engineering, University of Cape Town",
    { x: M, y: 0.35, w: W - 2 * M, h: 0.4, fontSize: 15, color: C.white, align: "center", shadow: shadow() });
  txt(s, "An Embedded Telemetry Unit and Windshield HUD\nfor the TUKZIE Rev 0 Electric Cargo Trike",
    { x: M, y: 0.85, w: W - 2 * M, h: 1.6, fontSize: 38, bold: true, color: C.white, align: "center", valign: "middle", shadow: shadow() });
  txt(s, "Samson Okuthe (OKTSAM001)",
    { x: M, y: 2.5, w: W - 2 * M, h: 0.45, fontSize: 20, bold: true, color: C.white, align: "center", shadow: shadow() });
  txt(s, "Supervisor: A/Prof. Simon Winberg   |   Co-supervisor: Sampath Jayalath   |   Project SW-7",
    { x: M, y: 2.95, w: W - 2 * M, h: 0.4, fontSize: 16, color: C.white, align: "center", shadow: shadow() });
}

// ---------------- 2 Why ----------------
{
  const s = content("Why this matters",
    "Two facts frame the project. First, electric trikes can make economic sense for freight in African cities: on the routes a 2025 study examined in Dar es Salaam, an electric cargo tricycle cut operating cost per kilometre by 45.5 percent against a motorcycle and up to 86 percent against a light car. " +
    "Second, any display that pulls the driver's eyes down is a risk. NHTSA guidance says a single glance away from the road should not exceed two seconds. " +
    "So the question is whether we can put edge telemetry and a head-up display together on a low-cost trike, which the literature treats as an open problem. I'll keep the background short and move to what I built.");
  const cw = (W - 2 * M - 0.5) / 2, cy = 1.45, ch = 3.3;
  [["45.5 to 86%", "lower operating cost per km for an electric cargo tricycle than a motorcycle, petrol tuk-tuk or light car on delivery routes in Dar es Salaam", "Sebwa et al., 2025"],
   ["2 s", "longest single glance away from the road that NHTSA guidance allows, which a head-down display works against", "NHTSA, 2013"]]
    .forEach(([big, small, src], i) => {
      const x = M + i * (cw + 0.5);
      card(s, x, cy, cw, ch);
      txt(s, big, { x: x + 0.4, y: cy + 0.35, w: cw - 0.8, h: 1.2, fontSize: 60, bold: true, color: C.navy });
      txt(s, small, { x: x + 0.4, y: cy + 1.6, w: cw - 0.8, h: 1.1, fontSize: 18, color: C.text, valign: "top" });
      txt(s, src, { x: x + 0.4, y: cy + ch - 0.55, w: cw - 0.8, h: 0.35, fontSize: 13, italic: true, color: C.muted });
    });
  txt(s, [{ text: "The open problem: ", options: { bold: true, color: C.navy } },
          { text: "bringing on-board edge telemetry and a sparse head-up display together on a low-cost electric trike, and measuring whether each part works." }],
    { x: M, y: 5.2, w: W - 2 * M, h: 1.0, fontSize: 20, valign: "middle" });
}

// ---------------- 3 Research questions ----------------
{
  const s = content("Aim and research questions",
    "The aim is a low-cost unit that characterises the trike's ride at the edge and shows only safety-relevant data head-up. " +
    "I split that into four research questions, and I've marked honestly where each one stands. " +
    "RQ1, dual-IMU acquisition at 200 hertz with the sensors agreeing within noise, is verified on the bench. " +
    "RQ3, the data path from sensor to cloud, is verified on the bench for acquisition and the MQTT publish, but not yet on the vehicle. " +
    "RQ4, the ride features, passes its self-test but needs real road data. RQ2, the HUD, depends on the field test and is still outstanding.");
  const rows = [
    ["RQ1", "Acquire two IMUs at 200 Hz (at least 160 Hz for ISO 2631-1) with the sensors agreeing within noise", "Bench-verified", C.sky],
    ["RQ2", "Show safety-critical data head-up without exceeding the 2 s glance guidance", "Outstanding", C.accent],
    ["RQ3", "Bounded latency, measured data loss and recovery from sensor through to the cellular link", "Partly verified", C.navy],
    ["RQ4", "Ride features that separate road-induced from powertrain vibration", "Self-test only", C.navy],
  ];
  const y0 = 1.45, rh = 1.08, gap = 0.18;
  rows.forEach(([id, req, status, col], i) => {
    const y = y0 + i * (rh + gap);
    card(s, M, y, W - 2 * M, rh);
    txt(s, id, { x: M + 0.3, y, w: 1.0, h: rh, fontSize: 24, bold: true, color: C.navy, valign: "middle" });
    txt(s, req, { x: M + 1.35, y, w: 8.4, h: rh, fontSize: 18, valign: "middle" });
    const bx = W - M - 2.55;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: bx, y: y + 0.29, w: 2.25, h: 0.5, rectRadius: 0.25,
      fill: { color: status === "Outstanding" ? C.white : col }, line: { color: col, width: 1.5, dashType: status === "Outstanding" ? "dash" : "solid" } });
    txt(s, status, { x: bx, y: y + 0.29, w: 2.25, h: 0.5, fontSize: 15, bold: true, color: status === "Outstanding" ? C.accent : C.white, align: "center", valign: "middle" });
  });
}

// ---------------- 4 System ----------------
{
  const s = content("The system on the bench",
    "This is the whole system on the bench, with each part labelled. " +
    "On the right is the telemetry unit: an ESP32-S3 on a Makerfabs board with a built-in A7670X LTE modem, which also gives us GNSS. Two MPU6050 IMUs are sampled at 200 hertz each, and the battery management system is read over Bluetooth Low Energy. " +
    "On the left is a Raspberry Pi 4 with the camera. The two boards share one wire: the ESP32 toggles a sync pulse that the Pi logs, so camera frames and IMU data can be lined up in time. " +
    "The Pi 4 is used rather than the team's Pi 5 so the existing vehicle dashboard on the Pi 5 is not disturbed.");
  const ih = 5.55, iw = ih * 1845 / 1349;
  s.addImage({ path: A("bench_labelled.png"), x: M, y: 1.35, w: iw, h: ih });
  const x = M + iw + 0.45, w = W - M - x;
  const blocks = [
    ["Telemetry unit", "ESP32-S3 with A7670X LTE and GNSS: acquisition, ride features, local log, MQTT"],
    ["Two IMUs", "MPU6050s at 200 Hz each, fused into one ride estimate"],
    ["Battery link", "BMS read over Bluetooth Low Energy"],
    ["Camera", "Raspberry Pi 4 and OV5647, time-aligned by a sync-pulse wire"],
  ];
  const bh = 1.22, bg = 0.2;
  blocks.forEach(([h, b], i) => {
    const y = 1.35 + i * (bh + bg);
    card(s, x, y, w, bh);
    txt(s, h, { x: x + 0.25, y: y + 0.12, w: w - 0.5, h: 0.38, fontSize: 17, bold: true, color: C.navy });
    txt(s, b, { x: x + 0.25, y: y + 0.5, w: w - 0.5, h: 0.66, fontSize: 14, color: C.text, valign: "top" });
  });
}

// ---------------- 5 Firmware ----------------
{
  const s = content("Firmware: deterministic acquisition first",
    "The firmware runs on FreeRTOS and is split across the two cores. " +
    "Core 1 holds everything timing-critical: one task per IMU at the highest priority, each holding a 5 millisecond period with vTaskDelayUntil so the rate cannot drift. " +
    "The acquisition tasks never print or block. They time-stamp each sample with a microsecond clock and push it into a bounded queue; if a queue is full the sample is dropped and counted, so a slow consumer can never stall acquisition. " +
    "Separate tasks compute the ride features over one-second windows and fuse the two sensors. Core 0 handles the slow, blocking work: the modem, GNSS, MQTT, the flash log and the battery link.");
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
  bx(colA, py + 3.4, bw, 1.0, "SyncTask", "GPIO pulse to the Pi");
  txt(s, "Each sample carries a sensor ID, a sequence number and a microsecond timestamp from esp_timer.",
    { x: colB, y: py + 3.45, w: 4.85, h: 0.9, fontSize: 14, italic: true, color: C.muted, valign: "middle" });
  // core 0 panel
  const qx = px + pw + 0.35, qw = W - M - qx;
  card(s, qx, py, qw, ph);
  txt(s, "Core 0: blocking I/O", { x: qx + 0.25, y: py + 0.12, w: qw - 0.5, h: 0.4, fontSize: 16, bold: true, color: C.sky });
  bx(qx + 0.3, py + 0.7, qw - 0.6, 1.4, "ModemTask", "AT commands, GNSS polling, MQTT publish, flash log");
  bx(qx + 0.3, py + 2.35, qw - 0.6, 1.0, "BmsTask", "battery over BLE");
  txt(s, "The modem UART has no lock, so everything that talks to the modem stays in one task.",
    { x: qx + 0.3, y: py + 3.5, w: qw - 0.6, h: 1.2, fontSize: 14, italic: true, color: C.muted, valign: "top" });
}

// ---------------- 6 Approach ----------------
{
  const s = content("Approach: prove each stage before building on it",
    "My method was staged verification. Each interface was brought up on its own on the real board, with a defined pass criterion, before anything was built on top of it. " +
    "Then both IMUs were acquired at 200 hertz and calibrated against gravity. Then the ride features and the fusion, each with a self-test at boot. Then the local log and the LTE publish. " +
    "The last stage, validation on the moving vehicle, is still to come, and it's drawn dashed for that reason. " +
    "This order paid off: several of the faults I'll show later would have been invisible if I'd integrated everything first.");
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
    "Two nominally identical accelerometers disagreed by 5 to 8 percent at rest; per-sensor calibration against true gravity brought that down to measurement noise, which meets RQ1. " +
    "The two are then fused into one ride estimate. With equal noise on both sensors, inverse-variance weighting reduces to a plain mean. Windows are only paired if they ended within half a window of each other, a disagreement figure is reported rather than hidden, and if one sensor goes silent for three seconds the output falls back to the other. " +
    "The chart is a recorded 150 second session: still, then disturbed by hand from about 75 seconds. All 149 windows were fused from both sensors with skew under a millisecond, and all five boot self-tests passed. " +
    "One honest finding: the stored calibration on the board was not the one first measured, and the resting readings were 1.3 and 2.9 percent above gravity, so the sensors will be recalibrated before the field test.");
  const stats = [
    ["200 Hz", "on both IMUs, zero dropped samples"],
    ["5 to 8%", "IMU gap at rest, calibrated down to noise"],
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

// ---------------- 8 Sync and connectivity ----------------
{
  const s = content("Result: camera alignment and the cellular path",
    "Two more bench results. On the camera side, a 15 second combined test produced 439 frames, consistent with about 29 frames a second, and 33 sync edges, consistent with the 2 hertz pulse. A dedicated calibration then bounded the offset between the camera clock and the IMU clock to under about one second, which is enough for labelling ride events after the fact. " +
    "On the network side, the full chain worked end to end on real hardware: SIM, registration, data context, MQTT connect, and an acknowledged publish, tested against a public broker. " +
    "Registration was intermittent, so this proves the mechanism, not reliability under vehicle conditions. Telemetry is also logged to the board's own flash so nothing depends on coverage.");
  const cw = (W - 2 * M - 0.4) / 2, cy = 1.4, ch = 5.35;
  const col = (x, title, big, bigSub, items) => {
    card(s, x, cy, cw, ch);
    txt(s, title, { x: x + 0.35, y: cy + 0.2, w: cw - 0.7, h: 0.45, fontSize: 20, bold: true, color: C.navy });
    txt(s, big, { x: x + 0.35, y: cy + 0.75, w: cw - 0.7, h: 1.0, fontSize: big.length > 6 ? 40 : 48, bold: true, color: C.sky, valign: "middle" });
    txt(s, bigSub, { x: x + 0.35, y: cy + 1.8, w: cw - 0.7, h: 0.5, fontSize: 16, color: C.muted });
    bullets(s, items, { x: x + 0.35, y: cy + 2.45, w: cw - 0.7, h: ch - 2.6, fontSize: 16 });
  };
  col(M, "Camera to IMU alignment", "< 1 s", "offset between camera frames and IMU data",
    ["15 s combined test: 439 frames (about 29 fps) and 33 sync edges (2 Hz pulse)",
     "Adequate for labelling ride events after the fact",
     "A tighter bound would need an optical check driven from the sync pin"]);
  col(M + cw + 0.4, "Cellular publish path", "Acknowledged", "SIM, registration, data context, MQTT connect, publish",
    ["Tested end to end on real hardware against a public test broker",
     "Registration was intermittent: the mechanism works, reliability on the vehicle is untested",
     "Local log on the 16 MB internal flash keeps a full record without coverage"]);
}

// ---------------- 9 Found and fixed ----------------
{
  const s = content("What testing found, and how it was fixed",
    "Testing each stage on real hardware found faults that would have been hard to trace later. " +
    "The GNSS reply was assumed to have 13 fields; the real modem gave 9, and the manual documents 16 with speed in knots. The parser checks the count, so this showed up in the log instead of producing wrong positions. " +
    "The BLE service lookup assumed the wrong parent service; it now searches all services, and my frame decoding matched an independent parser byte for byte. " +
    "The microSD chip-select resistor isn't fitted, so logging moved to internal flash. A boot loop came from a flash-size mismatch. " +
    "And one open finding: the flash writes line up with 25 to 30 millisecond stalls on both IMUs every 12 seconds. No samples were lost, and disabling the log for one session will confirm the cause.");
  const items = [
    ["GNSS reply format", "Assumed 13 fields, measured 9; the manual documents 16, with speed in knots. The field-count check caught it."],
    ["Battery (BLE) lookup", "Wrong parent-service assumption; now searches all services. Decoding matched an independent parser byte for byte."],
    ["microSD not wired", "Chip-select resistor R23 is not fitted, so logging moved to LittleFS on internal flash."],
    ["Boot loop", "Flash size did not match the 16 MB partition table; set to 16 MB, DIO mode."],
  ];
  const cw = (W - 2 * M - 0.3) / 2, ch = 1.62;
  items.forEach(([h, b], i) => {
    const x = M + (i % 2) * (cw + 0.3), y = 1.4 + Math.floor(i / 2) * (ch + 0.25);
    card(s, x, y, cw, ch);
    txt(s, h, { x: x + 0.3, y: y + 0.15, w: cw - 0.6, h: 0.42, fontSize: 18, bold: true, color: C.navy });
    txt(s, b, { x: x + 0.3, y: y + 0.6, w: cw - 0.6, h: ch - 0.7, fontSize: 15, valign: "top" });
  });
  const oy = 1.4 + 2 * (ch + 0.25);
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: oy, w: W - 2 * M, h: 1.35, rectRadius: 0.12, fill: { color: C.white }, line: { color: C.accent, width: 2, dashType: "dash" } });
  txt(s, "Open finding", { x: M + 0.3, y: oy + 0.15, w: 3, h: 0.42, fontSize: 18, bold: true, color: C.accent });
  txt(s, "Flash writes line up with 25 to 30 ms gaps on both IMUs every 12 s (nominal 5 ms). No samples lost. To confirm: one session with logging disabled.",
    { x: M + 0.3, y: oy + 0.58, w: W - 2 * M - 0.6, h: 0.7, fontSize: 15, valign: "top" });
}

// ---------------- 10 Camera, casing, hazard awareness ----------------
{
  const s = content("Camera casing and hazard awareness",
    "On supervisor direction, the camera's role grew from a visual record to a hazard-awareness function. " +
    "I designed a three-part casing and 3D printed it: a bottom shell and top cover that protect the camera and its ribbon cable, and a 30 degree corner mount to fix it to the trike. A second casing houses a second camera. The casings are printed but not yet fixed to the vehicle. " +
    "The detector is a pretrained, 8-bit SSD-MobileNet chosen to fit the Pi 4, with no training of my own. It reports only a few object types in three coarse distance bands. It has now run on live bench footage at about 7 frames a second and detects a person reliably; the other object types and the distance calibration are still to be tested. " +
    "For a live near-object alert I chose a VL53L5CX time-of-flight sensor with an 8 by 8 zone grid, so it can tell left, centre and right apart. It has been sourced and is awaiting delivery.");
  const ih = 5.35, iw = ih * 1827 / 1306;
  s.addImage({ path: A("casing_labelled.png"), x: M, y: 1.4, w: iw, h: ih });
  const x = M + iw + 0.4, w = W - M - x;
  const blocks = [
    ["3D-printed casing", "Designed and printed in this project: shell, cover and 30-degree corner mount. A second casing holds a second camera. Not yet fixed to the vehicle."],
    ["Object detector", "Pretrained 8-bit SSD-MobileNet sized for the Pi 4: a few object types in three distance bands. Running live at about 7 fps; person confirmed, other classes untested."],
    ["Time-of-flight sensor", "VL53L5CX, 8x8 zones over 63 degrees, up to 4 m, for left, centre and right alerts. Sourced, awaiting delivery."],
  ];
  const bh = 1.65, bg = 0.2;
  blocks.forEach(([h, b], i) => {
    const y = 1.4 + i * (bh + bg);
    card(s, x, y, w, bh);
    txt(s, h, { x: x + 0.25, y: y + 0.12, w: w - 0.5, h: 0.4, fontSize: 17, bold: true, color: C.navy });
    txt(s, b, { x: x + 0.25, y: y + 0.52, w: w - 0.5, h: bh - 0.6, fontSize: 14, valign: "top" });
  });
}

// ---------------- 11 Field test slot ----------------
{
  const s = content("Field test on the TUKZIE Rev 0",
    "PLACEHOLDER: replace this slide once the on-vehicle test has been done. " +
    "Planned content: the ride features against known road and powertrain events for RQ4; end-to-end latency, data loss and recovery over LTE on the moving vehicle for RQ3; the HUD and glance observation for RQ2; and the first outdoor GNSS fix, which confirms the field order and speed units and lets the speed-normalised index be computed.");
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: 1.4, w: W - 2 * M, h: 5.35, rectRadius: 0.12, fill: { color: C.white }, line: { color: C.accent, width: 2.5, dashType: "dash" } });
  txt(s, "To be completed after the on-vehicle test", { x: M + 0.4, y: 1.6, w: W - 2 * M - 0.8, h: 0.55, fontSize: 24, bold: true, color: C.accent });
  const planned = [
    ["RQ4", "Ride features against known road and powertrain events"],
    ["RQ3", "Latency, data loss and recovery over LTE while moving"],
    ["RQ2", "HUD layout and glance observation"],
    ["GNSS", "First outdoor fix: confirms field order and speed units, enables the speed-normalised index"],
  ];
  const cw = (W - 2 * M - 0.8 - 0.3) / 2, ch = 1.85;
  planned.forEach(([id, t], i) => {
    const x = M + 0.4 + (i % 2) * (cw + 0.3), y = 2.4 + Math.floor(i / 2) * (ch + 0.25);
    card(s, x, y, cw, ch);
    txt(s, id, { x: x + 0.3, y: y + 0.2, w: cw - 0.6, h: 0.5, fontSize: 22, bold: true, color: C.navy });
    txt(s, t, { x: x + 0.3, y: y + 0.75, w: cw - 0.6, h: ch - 0.9, fontSize: 17, valign: "top" });
  });
}

// ---------------- 12 Conclusions ----------------
{
  const s = content("Conclusions and next steps",
    "To conclude. Every subsystem runs together on the target board: two IMUs at 200 hertz with no loss, calibrated and fused live, battery and GNSS interfaces, a local log, an acknowledged cellular publish, and a camera aligned to the IMU data within a second. " +
    "Testing each stage on real hardware found and fixed several faults that assumptions had hidden. " +
    "What's left is the part that answers the ride and HUD questions: recalibrate the IMUs, run the field test on the trike, confirm the flash-write stall, integrate the time-of-flight and air-quality sensors, and build the HUD. Thank you, I'm happy to take questions.");
  const cw = (W - 2 * M - 0.4) / 2, cy = 1.4, ch = 4.45;
  card(s, M, cy, cw, ch);
  txt(s, "Done on the bench", { x: M + 0.35, y: cy + 0.2, w: cw - 0.7, h: 0.45, fontSize: 20, bold: true, color: C.navy });
  bullets(s, [
    "All subsystems running together on the target board",
    "200 Hz dual-IMU acquisition, calibrated and fused live",
    "Acknowledged MQTT publish over LTE, plus a local flash log",
    "Camera aligned to IMU data within 1 s",
    "Faults found early by testing each stage on real hardware",
  ], { x: M + 0.35, y: cy + 0.85, w: cw - 0.7, h: ch - 1.0, fontSize: 16 });
  const x2 = M + cw + 0.4;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x2, y: cy, w: cw, h: ch, rectRadius: 0.12, fill: { color: C.white }, line: { color: C.accent, width: 2, dashType: "dash" } });
  txt(s, "Next", { x: x2 + 0.35, y: cy + 0.2, w: cw - 0.7, h: 0.45, fontSize: 20, bold: true, color: C.accent });
  bullets(s, [
    "Recalibrate both IMUs while stationary",
    "On-vehicle field test with the TUKZIE team",
    "Confirm the flash-write stall with logging disabled",
    "Integrate the VL53L5CX and SEN55 sensors",
    "Build and evaluate the HUD",
  ], { x: x2 + 0.35, y: cy + 0.85, w: cw - 0.7, h: ch - 1.0, fontSize: 16 });
  txt(s, "Thank you. Questions?", { x: M, y: 6.05, w: W - 2 * M, h: 0.6, fontSize: 26, bold: true, color: C.navy, align: "center", valign: "middle" });
}

const out = process.argv[2] || path.join(__dirname, "SW7_Final_Presentation.pptx");
pres.writeFile({ fileName: out }).then((f) => console.log("wrote", f));
