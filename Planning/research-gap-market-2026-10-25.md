# Research gap: market and literature scan, 25 Oct 2026

Web searches run on 25 Oct 2026 to test the gap claim of Section 2.12 against products on the market, not only the academic search of 19 Sept. These entries come from search results. Before any of them is cited in the report, it must be downloaded, filed in References/Papers, checked and recorded in Planning/source-checks.md.

## What exists, by slice of the problem

| Slice | Closest existing work | Where it stops |
|---|---|---|
| Battery and position telemetry for electric three-wheelers | Commercial platforms for Indian e-rickshaws and cargo three-wheelers: Navionyx (AIS 140, claims 5,000+ vehicles; notes most L3 e-rickshaws have no standard diagnostic port), Pictor Telematics (cloud BMS: cell voltage, SoC, SoH, thermal alerts), battery makers with IoT packs (Livguard, Ecoblaze, Amara Raja) | GPS, battery and fleet data only: no ride or road response, no hazard sensing, no driver display. Closed systems, with performance figures that are vendor claims (no published loss, latency or recovery) |
| Collision warning on 2- and 3-wheelers | Ride Vision: front and rear cameras with forward-collision and blind-spot alerts, marketed for "any 2 or 3-wheeler", sold in Israel, Australia and parts of Europe. Bosch rider assistance (radar based). Academic monocular TTC with an IMU on motorcycles (J. Intell. Connected Vehicles, 2021) | Warning only: no telemetry, ride or battery data, nothing on the vehicle's existing dashboard. Closed, accuracy on 3-wheelers not published, not offered in South Africa |
| Road sensing with low-cost inertial sensors | Nericell (Microsoft Research India, 2008: phones on 2- and 4-wheelers, potholes and bumps by thresholds); Raspberry Pi and IMU systems validated against a profiler; IMU plus pulsed radar for IRI, about US$214 (2025); ESP32 and MPU-9250 road-surface classification (2026); Alatoom and Smadi (2025, already cited) | Cars or phones, not three-wheelers. Acquisition integrity (jitter, loss) not reported. No separation of the vehicle's own powertrain vibration |
| Vibration on auto-rickshaws | Singh (2019, India): 120 drivers, four auto-rickshaw models, a laboratory-grade vibration meter (SVAN 106), whole-body vibration against road condition and passengers | Occupational health with an expensive instrument, not an on-vehicle edge system; no road and powertrain separation |
| Road against powertrain vibration in electric vehicles | NVH work: order analysis of EV drivetrains (World Electric Vehicle Journal 2026); rejecting road disturbances to judge powertrain vibration at the steering wheel (INCE 2024); hub-motor and road coupling models | High-end test instrumentation or simulation, cars; nothing low-cost on a hub-motor cargo trike |
| Store-and-forward telemetry | MQTT persistent sessions and local buffering (vendor guidance, MDPI V2X 2025, IIoT practice) | No vehicle study found that measures delivery and recovery after a real cellular outage |
| Electric cargo tricycles in operation | Toronto parking and stop study (GPS with shipments, 2026); Padua and Florence cargo bikes (GPS, energy, data loggers); Faenza cargo-bike air quality (2025); in Africa, Mobility for Africa's Hamba e-trikes (Zimbabwe, 190 to 400 vehicles) and MellowVans e-trikes in Cape Town deliveries (2022) | They measure operations (stops, energy, exposure), not the vehicle's response, surroundings or data integrity. No published telemetry from the African fleets |

## The gap, as defended

Every slice of the problem has existing work, but each sits in a different place:
- commercial telematics gives battery and position;
- commercial rider assistance gives camera warnings;
- research gives road sensing on cars and phones, and powertrain separation in NVH laboratories.

Nothing found combines them on a low-cost electric cargo three-wheeler, with the system's own data integrity measured and published openly.

**Gap statement for the report.** No published or commercial system was found that, on a low-cost electric cargo three-wheeler:
1. acquires the vehicle's motion at a fixed rate, with its timing and losses measured;
2. separates road-induced from powertrain vibration, using nodes at both ends and stationary baselines;
3. warns of nearby and approaching hazards by fusing a camera with range sensors;
4. keeps every record through cellular outages and measures its recovery;
5. presents only live, valid data on the vehicle's existing dashboard.

Existing products each cover one of these as a closed system with unpublished performance. Existing research covers parts of them on cars, phones or laboratory rigs.

**What the project answers.** It shows that this integration can be built from parts costing a few hundred rand to a few thousand, and it measures how far each part can be trusted:
- acquisition: 200 Hz, zero counted drops;
- recovery: 112 of 112 records after a 10-minute outage;
- detection: 51 to 54 ms on the Pi 5;
- battery link: held to 46.9 A on the road;
- the powertrain's lines located on the stands;
- the honest limits: legibility, the stall on the road, the unvalidated speed.

Road repeatability (RQ1) and the road share of the powertrain (RQ4) complete the answer with run 2.

**How to state the contribution.** The contribution is the integration, measured, on a vehicle class that the products and the research both leave out: African electric cargo trikes. It is not any single component. Commercial products also strengthen the motivation: operators in India already pay for battery telematics, and camera warnings for 3-wheelers are on sale, so the parts are wanted. What is missing is one open, measured system that does both, plus ride sensing, on a cheap trike.

## Candidates for Chapter 2 (after source checks)

- Add a "commercial" row group to Table 2.1: e-three-wheeler telematics (Navionyx or Pictor) and Ride Vision. Shows markers that the market was searched.
- Cite Singh (2019) in Section 2.3 or 2.4: three-wheeler vibration has been measured, but for health and with a laboratory meter.
- Cite Nericell in Section 2.3: phone road sensing on 2-wheelers in India since 2008, with thresholds and no integrity measures.
- Cite one low-cost IMU roughness system validated against a profiler, to sharpen what this project does not claim (an IRI).
- Words: about +150, offset by cuts elsewhere (body at 14,946 of a 15,000 guide).
