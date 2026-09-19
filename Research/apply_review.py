"""One-off: record the human/assistant review of auto-flagged gap evidence.

Reviews were made from the abstracts stored in research.db, not full texts.
That is adequate to judge whether a paper addresses the same *combination* a
gap claim asserts is unaddressed, but not to settle fine methodological
points - noted per entry where it matters.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
LEDGER = HERE / "gap_ledger.json"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")

# (claim_id, source_id) -> (stance, note)
REVIEWS = {
    ("G1", 243): ("challenges",
        "Open-architecture motorcycle telemetry unit (STM32H745) combining a 9-DoF IMU with "
        "on-chip fusion, RTK-GNSS, CAN-FD powertrain acquisition and a SIM7600E-H 4G/LTE "
        "uplink, with deterministic dual-core task partitioning and a 3D-printed vibration-"
        "resistant enclosure. This is architecturally very close to SW-7 and defeats any broad "
        "claim that an open embedded IMU+GNSS+cellular telemetry unit is itself novel. It does "
        "NOT disprove G1 as worded: it is a two-wheeled racing platform, uses a single fused "
        "IMU rather than spatially-separated dual IMUs, and targets performance optimisation "
        "rather than ride-quality characterisation. G1 must narrow to those distinctions. "
        "ACTION: read the full text before finalising the narrowed wording."),
    ("G1", 167): ("neutral",
        "IoT public-safety alerting (gas/flame/vibration/biometric sensors, MQTT over TLS). "
        "Different domain and purpose; no vehicle-dynamics characterisation. Does not bear on G1."),
    ("G1", 94): ("neutral",
        "AgroGuardian ATV crash detection: IMU attitude estimation + GPS + satellite modem. "
        "Event-triggered crash detection on a single IMU, not continuous ride characterisation, "
        "and not a three-wheeled passenger/cargo platform. Does not bear on G1 directly, but is "
        "relevant prior art for G3 (see separate entry)."),
    ("G1", 245): ("neutral",
        "Structural health monitoring of buildings with synchronised low-cost MEMS "
        "accelerometers and on-board filtering. Different domain, but a useful methodological "
        "precedent for synchronising multiple cheap MEMS accelerometers - worth citing in the "
        "methodology rather than as a challenge to the gap."),

    ("G2", 356): ("neutral",
        "EKF fusion of monocular vision and IMU for indoor mobile-robot pose estimation. The "
        "sensors overlap with SW-7 but the purpose does not: localisation, not hazard awareness, "
        "and no telemetry or road vehicle. Useful background on camera/IMU fusion; does not "
        "challenge G2."),
    ("G2", 167): ("neutral",
        "No camera-based hazard detection and no vehicle-dynamics telemetry. Does not bear on G2."),

    ("G3", 243): ("challenges",
        "Partially challenges G3: the design does pair microSD logging with the 4G uplink, which "
        "is the mechanism G3 says is missing. However the paper explicitly states that 4G-uplink "
        "reliability is characterised from manufacturer specifications rather than experimentally, "
        "so intermittent-uplink behaviour is still not empirically established. G3 should narrow "
        "from 'does not address' to 'does not experimentally characterise'."),
    ("G3", 167): ("challenges",
        "Implements LoRa fallback explicitly for rural/low-connectivity environments, i.e. "
        "degraded-connectivity handling is addressed in adjacent IoT literature. Different "
        "mechanism from store-and-forward buffering, but enough that G3 cannot claim the problem "
        "is unrecognised - only that vehicle-telemetry store-and-forward recovery is "
        "uncharacterised."),
    ("G3", 168): ("neutral",
        "Generic IoT/IIoT/Industry 4.0 review with no abstract stored and no specific bearing on "
        "vehicle telemetry under intermittent connectivity."),
}

# Claim wording changes justified by the review above. Original wording is
# preserved so the narrowing itself is auditable.
NARROWED = {
    "G1": "No published system combines spatially-separated dual-IMU ride characterisation "
          "(ride quality, ISO 2631 sense) with cellular telemetry on a three-wheeled "
          "cargo/passenger electric vehicle. Narrowed 2026-09-19: open-architecture embedded "
          "IMU+GNSS+cellular telemetry units are established prior art on two-wheeled racing "
          "platforms (Electronics 2026, doi 10.3390/electronics15122604); the remaining "
          "distinctions are the dual spatially-separated IMUs, the ride-quality rather than "
          "performance framing, and the vehicle class.",
    "G3": "Existing low-cost vehicle telematics work does not experimentally characterise local "
          "buffering and recovery of telemetry when the cellular uplink is intermittent. "
          "Narrowed 2026-09-19: the mechanism (local logging alongside a cellular uplink, or "
          "alternative-radio fallback) does appear in prior work, but uplink reliability is "
          "typically taken from manufacturer specifications rather than measured.",
}

led = json.loads(LEDGER.read_text(encoding="utf-8"))

applied = 0
for e in led.get("evidence", []):
    key = (e["claim_id"], e["source_id"])
    if key in REVIEWS:
        stance, note = REVIEWS[key]
        e["stance"] = stance
        e["note"] = note
        e["reviewed_at"] = NOW
        e["reviewed_from"] = "abstract"
        applied += 1

for claim in led["claims"]:
    if claim["id"] in NARROWED:
        claim.setdefault("original_claim", claim["claim"])
        claim["claim"] = NARROWED[claim["id"]]
        claim["narrowed_at"] = NOW

LEDGER.write_text(json.dumps(led, indent=2), encoding="utf-8")

from collections import Counter
print(f"reviews applied: {applied}")
print("stances:", dict(Counter(e["stance"] for e in led["evidence"])))
print("claims narrowed:", [c["id"] for c in led["claims"] if "narrowed_at" in c])
