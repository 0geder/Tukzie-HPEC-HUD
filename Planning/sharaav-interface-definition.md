# SW-6 (Sharaav) <-> SW-7 UART interface definition

Status: preliminary, agreed informally 2026-09-21, to be finalised at an
in-person discussion Wednesday. This is the interface-definition deliverable
the VIT plan's D5 joint session specifies - no record could be found of that
session producing one, so this captures the real agreement as it happens
rather than let it live only in a WhatsApp thread.

**Update, 2026-09-24**: Sharaav indicated today that he may no longer need
this link, since most of the speed/battery data SW-7's HUD (then planned) would consume
from it may already be available via the existing vac-work dashboard
instead. Not yet confirmed as final on either side. This changes nothing
below until it is confirmed one way or the other - if the link is dropped,
SW-7's HUD would need to source speed/SoC from the dashboard's own data
layer instead (consistent with the tether-to-dashboard direction already
being explored for the HUD generally), and this document's "still open"
and "not yet built" sections below become moot.

**Update, 2026-10-03**: the windshield HUD was replaced by integration
with the vehicle's existing dashboard on the Pi 5 (supervisor agreed
1 Oct 2026, title change captured 2 Oct 2026). The dashboard now gets SoC
from SW-7's own BMS link through the Pi 4 telemetry bridge
(DashboardIntegration/TELEMETRY_LINK.md); speed is not yet mapped because
the GNSS speed units are unconfirmed. This UART link is therefore optional:
if SW-6 still sends speed, it would feed the dashboard through the same
bridge. Below, "the HUD" read as "the driver display" (now the dashboard).

## Physical layer

- Dedicated USB-C port on the SW-7 Makerfabs board, wired via CH340K to
  ESP32-S3 GPIO43 (TX) / GPIO44 (RX) - confirmed free, unused by any other
  firmware function (checked against the schematic and grepped the codebase
  before agreeing to this).
- 115200 baud, 8N1 framing. Confirmed by both sides.

## Data layer

- Format: CSV, sent as a plain string line.
- Direction: SW-6 -> SW-7 (one-way, at least at this stage - Sharaav has his
  own IMU, so no ride-characterisation data flows the other way).
- Content: vehicle speed (km/h) and battery percentage.

## Why this matters beyond the wire

SW-7's driver-display design (then the HUD) settled on exactly two persistent, always-shown values:
speed and battery state of charge (everything else - hazards, faults,
notifications - is pop-up/event-driven, not constant). This link is the
direct data source for both of those values. SW-7 does not need to
independently solve reliable speed/SoC reporting; it consumes SW-6's feed
for the driver display, while continuing to own ride-characterisation (IMU), camera
hazard awareness, and cellular telemetry publishing.

## Still open - bring to Wednesday's discussion

- Exact field order in the CSV (e.g. `speed,battery\n` vs `battery,speed\n`)
  and numeric precision (integer vs one/two decimal places).
- Update rate - how often SW-6 sends a line.
- Line terminator / framing - plain `\n`, `\r\n`, or any start/end marker
  beyond newline-delimiting.
- Behaviour on an invalid or out-of-range line: discard and hold last-known
  value, or something else. SW-7's own GNSS/BMS handling elsewhere in this
  project already uses a "hold last valid, flag as stale" pattern
  (`GnssFix.valid`, similar for BMS) - worth proposing the same convention
  here for consistency rather than inventing a new one.

## SW-7-side implementation, not yet built

A dedicated `HardwareSerial` instance on GPIO43/44, with its own FreeRTOS
task owning it exclusively (same discipline as `ModemTask` owning `Serial1`
- no locking exists on ESP32 UART access, so shared access from multiple
tasks would corrupt the stream). Parses the agreed CSV format once finalised
Wednesday, updates `latestSpeedKmph`/`latestBatteryPct`-style globals
(volatile, field-by-field assignment per the established pattern used for
`latestGnssFix`/`latestBmsSample`), passed to the dashboard through the DASH
line and the Pi 4 bridge if the link is built.
