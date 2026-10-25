# Source checks

Every external source used to check a value in the report is downloaded, filed under References/Papers and listed
here with where it came from, its SHA-256 (first 16 hex digits), what was taken from it and the result. Newest last.

## 2026-10-24: ISO 2631-1 Wk weighting filter (BenchTest/analysis/dsp.py)

Claim checked: the filter's band-limiting, transition and step parameters, and its gain at the one-third-octave
frequencies. The standard itself (ISO 2631-1:1997) is paywalled and was not consulted; the check is against
published derivations of it. Files in References/Papers/IMU-Based Ride Smoothness and Road Roughness, downloaded
24 Oct 2026.

| File | Source URL | Bytes | SHA-256 | Used for |
|---|---|---|---|---|
| Rimell_Mansfield_2007_Digital_filters_frequency_weightings_vibration_IndHealth45-512.pdf | https://www.jstage.jst.go.jp/article/indhealth/45/4/45_4_512/_pdf | 93,464 | 7b28f425bffaec32 | Table 3, Wk row: f1 0.4 Hz, Q1 1/sqrt2, f2 100 Hz, Q2 1/sqrt2, f3 = f4 12.5 Hz, Q4 0.63, f5 2.37 Hz, Q5 0.91, f6 3.3 Hz, Q6 0.91 |
| Rimell_Mansfield_2010_Erratum_IndHealth48-129.pdf | https://www.jniosh.johas.go.jp/en/indu_hel/doc/IH_48_1_129.pdf | 20,582 | 115e9dbca6dd3a11 | Corrects Equation 4 (the Wk step term) of the 2007 paper |
| Rimell_Mansfield_2010_Corrigendum_IndHealth48-743.pdf | https://www.jniosh.johas.go.jp/en/indu_hel/doc/IH_48_5_743.pdf | 429,339 | fedf27bac7aab6ae | Corrects Equation 4 again and Tables 5 and 8 (BS 6841 Wb gain, Wh equations); Wk parameters unaffected |
| Virtins_2024_Frequency_weightings_for_sound_and_vibration.pdf | https://virtins.com/doc/Frequency-Weightings-for-Sound-and-Vibration-Perceived-by-Humans-using-Multi-Instrument.pdf | 1,634,259 | 7c912b58b881c255 | Wk parameter table with f6 3.35 Hz, Q6 0.91, and Wk at one-third-octave frequencies 0.1 to 400 Hz |

Result: the code's parameters equal Rimell and Mansfield's Table 3 except f6 (code 3.35 Hz, paper 3.3 Hz); with 3.35 Hz
the gain matches the Virtins table within 0.005 dB at all 37 frequencies (up to 0.27 dB off with 3.3 Hz), so 3.3 is
read as rounded. The code's Equation 4 form matches the corrected form in the erratum and corrigendum. Tests:
BenchTest/analysis/tests/test_dsp.py (37 Virtins values within 0.006 dB; parameters against the paper; the f6 check).
Report: citations rimell2007, rimell2010corr and virtins2024 (Method 3.6, Appendix J).

## 2026-10-24: Design chapter theory (MPU6050 filter, road spectrum for the speed index)

Claims checked: the MPU6050 digital low-pass setting used by the firmware (DLPF_CFG 2, `MPU_VAL_CONFIG 0x02` in
TelemetryUnit/src/main.cpp) and the accelerometer output rate, for the anti-aliasing analysis; and the ISO 8608 form
of the road displacement spectrum, for the derivation of the 1/v scaling of I_v. ISO 8608 itself is paywalled and was
not consulted; the form is taken from an open-access paper that states it. Downloaded 24 Oct 2026.

| File | Source URL | Bytes | SHA-256 | Used for |
|---|---|---|---|---|
| Component Selection Justification/InvenSense_RM-MPU-6000A-00_rev4.0_MPU-6000_MPU-6050_Register_Map.pdf | https://cdn.sparkfun.com/datasheets/Sensors/Accelerometers/RM-MPU-6000A.pdf | 665,861 | ccaa6312b9d86a9d | Register 26 (CONFIG) table: DLPF_CFG 2 gives accelerometer bandwidth 94 Hz, delay 3.0 ms (gyroscope 98 Hz, 2.8 ms, Fs 1 kHz); register 25 note: accelerometer output rate 1 kHz. No filter order or roll-off is given. |
| IMU-Based Ride Smoothness and Road Roughness/Agostinacchio_Ciampa_Olita_2014_Vibrations_road_irregularities_ETRR6-267.pdf | https://etrr.springeropen.com/counter/pdf/10.1007/s12544-013-0127-8.pdf | 581,590 | 106fc4d0469275b2 | Section 2, Equation 3 and Table 1: ISO 8608 displacement PSD Gd(n) = Gd(n0)(n/n0)^-2 with n0 = 0.1 cycles/m, and the class values of Gd(n0) |

Result: the firmware's filter setting matches the register map (94 Hz, 3.0 ms). The attenuations quoted at the image
frequencies (157.25, 151.0, 136.0 Hz) are computed for an assumed first-order and an assumed second-order Butterworth
response, because the map gives no order; they are labelled as such in the report. The time-domain form and the
sigma^2 proportional to v result are derived in the report from Equation 3, not taken from the paper. Not obtained:
Li et al. 2018 (li2018, Shock and Vibration, doi 10.1155/2018/5131434); the Hindawi and Wiley PDF links returned HTML,
so the derivation is not attributed to it. Report: citations invensense2012rm and agostinacchio2014 (Design chapter,
Sections Sampling and anti-aliasing and Speed-normalised index); bibitems in Report/new_refs_design.tex.

## 2026-10-24: Literature Review sources (calibration, timing, GNSS, MQTT, store-and-forward, fusion, TTC validation)

Claim checked: each statement attributed to these sources in Report/Literature.tex (new Section 2.5 "Calibration, timing
and position" and additions to 2.4, 2.8, 2.9, 2.10). Metadata of every item checked against Crossref (or the standards
body / NHTSA page); entries in Report/new_refs_lit.tex. Downloaded 24 Oct 2026 unless marked "already filed".

| File | Source URL | Bytes | SHA-256 | Used for |
|---|---|---|---|---|
| IMU-Based Ride Smoothness and Road Roughness/Ru_etal_2022_MEMS_Inertial_Sensor_Calibration_Review_Micromachines13-879.pdf | https://mdpi-res.com/d_attachment/micromachines/micromachines-13-00879/article_deploy/micromachines-13-00879.pdf | 923,457 | b05f6302eb74b7f6 | Sec. 2.1-2.2: dominant errors bias, scale factor, non-orthogonality, misalignment; thermal drift of offset; Sec. 3.2.1: static six-position method, Eqs. (8)-(9), dependence on alignment, turntable or cube; Sec. 3.2.2: autonomous calibration from constant gravity magnitude (Eq. 10) |
| IMU-Based Ride Smoothness and Road Roughness/Webering_etal_2022_Improved_IMU_Calibration_without_Precision_Equipment_arXiv2207.04801.pdf | https://arxiv.org/pdf/2207.04801 | 2,856,949 | eb381acdba6d186b | Abstract: N = 12 orientations sufficient vs 37 to 50 recommended by Tedaldi; calibration time ca. 5 min to under 2 min. arXiv preprint (comment "Submitted to BioCAS 2022"); no published version found on Crossref |
| (not filed) Tedaldi, Pretto, Menegatti, ICRA 2014, doi 10.1109/ICRA.2014.6907297 | https://doi.org/10.1109/ICRA.2014.6907297 (author copy http://www.dis.uniroma1.it/~pretto/papers/tpm_icra2014.pdf did not respond) | - | - | METADATA AND ABSTRACT ONLY (Crossref; abstract from OpenAlex): multi-position scheme, sensor moved by hand to static positions, scale, misalignment and bias without external equipment. No number taken from this paper |
| Component Selection Justification/Reliability_Testing_Procedure_for_MEMS_IMUs_Applied_to_Vibrating_Environments_2010.pdf (already filed) | https://doi.org/10.3390/s100100456 | 1,041,629 | 4219fd9b6de397bf | Conclusions: six-position calibration and Allan variance before/after accelerated vibration; variation of bias, scale factors and non-orthogonality between axes as indicator of damage |
| IMU-Based Ride Smoothness and Road Roughness/Alessandroni_etal_2017_Speed_Influence_Road_Roughness_SmartRoadSense_Sensors17-305.pdf | https://mdpi-res.com/d_attachment/sensors/sensors-17-00305/article_deploy/sensors-17-00305.pdf | 6,130,562 | 0cac882934d5c978 | Abstract: roughness index vs speed locally approximated by a gamma (power) law |
| HPEC and Embedded Computing/Mills_etal_2010_RFC5905_NTPv4.txt | https://www.rfc-editor.org/rfc/rfc5905.txt | 241,096 | 8b7abd903c60202e | Sec. 1: "Typical secondary servers and clients on fast LANs are within a few hundred microseconds" |
| HPEC and Embedded Computing/Elson_Girod_Estrin_2002_Reference_Broadcast_Synchronization_OSDI.pdf | https://www.usenix.org/legacy/events/osdi02/tech/full_papers/elson/elson.pdf | 215,332 | dd396c4bb7209d23 | Abstract: receivers timestamp a reference broadcast; removing sender non-determinism; 1.85 +/- 1.28 us over 802.11. Crossref record is the ACM SIGOPS OSR version (doi 10.1145/844128.844143, pp. 147-163) |
| HPEC and Embedded Computing/Olson_2010_Passive_Sensor_Synchronization_IROS.pdf | https://april.eecs.umich.edu/pdfs/olson2010.pdf | 207,605 | 1d66ff31d9aa6c10 | Abstract and Sec. I: sensors without sync support; non-real-time OS jitter "can amount to hundreds of milliseconds on a loaded system"; passive method using low-latency messages reduces error vs timestamping on arrival |
| General Automotive Sensors/Merry_Bettinger_2019_Smartphone_GPS_Accuracy_Urban_PLoSONE.pdf | https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0219890&type=printable | 3,217,723 | b54ee0c48e228917 | Abstract: iPhone 6 average horizontal accuracy 7 to 13 m in an urban environment, consistent with recreation-grade receivers in high-multipath settings |
| Automotive Communication Systems/OASIS_2014_MQTT_Version_3.1.1_Standard.pdf | https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.pdf | 2,269,570 | c45a1f4f3d0d9a66 | Sec. 1.1/4.3: QoS 0 at most once, QoS 1 at least once (duplicates can occur), QoS 2 exactly once (four-packet flow); Sec. 3.1.2.4 client session state; Sec. 4.1 non-normative: stored state may be discarded or lost through hardware or software failure |
| Automotive Communication Systems/Fall_2003_Delay-Tolerant_Network_Architecture_SIGCOMM.pdf | https://www2.cs.arizona.edu/classes/cs525/papers/DTN.pdf | 100,020 | 2897a52884ba31ff | Abstract, Secs. 2.3 and 4.5: in-network persistent storage and retransmission, custody transfer, end nodes not having to wait for end-to-end acknowledgement |
| Component Selection Justification/Chapungo_Postolache_2025_LoRaWAN_Reliability_Rural_Mozambique.pdf (already filed) | https://doi.org/10.3390/s25196027 | 4,914,624 | 8c730595edbe0e02 | Highlights: rural Mozambican site with no electricity or mobile network |
| Component Selection Justification/Ugwuanyi_Paul_Irvine_2021_Survey_IoT_Developing_Countries_LoRaWAN_vs_NB-IoT.pdf (already filed) | https://doi.org/10.3390/electronics10182224 | 1,801,134 | 5f674f982d7e43a3 | Introduction: power and network coverage limit IoT deployment in developing countries |
| Camera and Object Detection/Manglik_etal_2019_Forecasting_Time-to-Collision_from_Monocular_Video.pdf (already filed; arXiv v3) | https://doi.org/10.1109/IROS40897.2019.8967730 | 3,368,260 | 163b79f79a18336d | LiDAR ground truth "accurate to within a few centimeters", camera-LiDAR extrinsic calibration; average error 0.75 s; platform speed 0.2-1.5 m/s; caution on generalising to other camera heights, speeds, scenes |
| Camera and Object Detection/Lenkeit_DRI_2012_NHTSA_NCAP_FCW_Confirmation_Test_2013_Ford_Explorer.pdf | https://nrd-static.nhtsa.dot.gov/reports/vehdb/v00000/v08900/v08966R001.pdf | 5,436,541 | 0f164a4f54f4b217 | Report OCAS-DRI-FCW-13-009: Test 1 stopped POV, alert at TTC >= 2.1 s; Test 2 decelerating POV, >= 2.4 s; Test 3 slower POV, >= 2.0 s; SV 45 mph (72.4 km/h); pass in at least 5 of 7 trials; POV a mid-size sedan |
| Camera and Object Detection/Yeong_etal_2021_Sensor_and_Sensor_Fusion_in_Autonomous_Vehicles_Review_Sensors21-2140.pdf | https://mdpi-res.com/d_attachment/sensors/sensors-21-02140/article_deploy/sensors-21-02140.pdf | 2,740,260 | 1d66b3c22ac98302 | Sec. 4 and Table 8: high-level vs low-level (and mid-level) fusion; HLF lower complexity, discards lower-confidence classifications with overlapping obstacles; LLF needs precise extrinsic and temporal calibration |
| Camera and Object Detection/2021_Near-field_Perception_for_Low-Speed_Vehicle_Automation_Surround-view_Fisheye_Cameras.pdf (already filed; arXiv v4) | https://doi.org/10.1109/TITS.2021.3127646 | 10,331,141 | 2bdfe3ce943354b4 | Redundancy section: ultrasonic arrays a mature low-cost near-field safety sensor; redundancy between sensor types |

Result: all statements in the chapter match the passages listed; no number was taken from Tedaldi et al. (abstract only).
Report: citations ru2022, tedaldi2014, webering2022, depasquale2010, alessandroni2017, rfc5905, elson2002, olson2010,
merry2019, mqtt311, fall2003, chapungo2025, ugwuanyi2021, manglik2019, lenkeit2012fcw, yeong2021, eising2022
(Report/new_refs_lit.tex, to be merged into References.tex).

## tukzie.com (25 Oct 2026)

Source: University of Cape Town, "Tukzie", programme website, https://tukzie.com/, accessed 25 Oct 2026. Copy: References/Papers/Urban Electric Cargo Trike/TUKZIE_website_tukzie.com_2026-10-25.html.
Checked against the report: "Developed at UCT, it is built for Africa's conditions and opportunities" and "An electric mobility platform combining adaptable vehicle architecture, energy systems, control and connected technologies" support Section 1.1's "TUKZIE Flagship Programme of the University of Cape Town". The site gives no specifications (battery, motor, range), so no number in the report is taken from it.
Report: citation tukzie2026web (Introduction, first sentence).

## ISO 15008:2003 (25 Oct 2026)

Source: ISO 15008:2003, first edition, read in the publisher's preview (standards.iteh.ai), 12 pages: Foreword, Introduction, Sections 1 to 4.2 and the start of 4.3. Copy: References/Papers/HMI/ISO_15008_2003_preview_iTeh.pdf (git-ignored: copyrighted).
Checked: 4.3.1 minimum contrast ratio between symbol and background 5:1 night, 3:1 day, 2:1 sunlight. Cited (iso15008) in Section 6.5 for the contrast criterion.
Not in the preview: 4.5 Alphanumerical character dimensions and Annex C, so the 20 and 16 arc-minute character heights are still cited through reimer2014typeface and you2021charsize, which are still to be downloaded and checked. The full standard (or ISO 15008:2017, or SANS 15008) is to be sought through UCT Libraries.

## ISO 15008:2017 (25 Oct 2026)

Source: DIN EN ISO 15008:2017-07, English translation (DIN, Beuth Verlag), the full 32-page document, which supersedes DIN EN ISO 15008:2011-06. Copy: References/Papers/HMI/DIN_EN_ISO_15008_2017_en.pdf (git-ignored: copyrighted).
Checked: 4.5.2 Table 1, capital height as the angle subtended at the rearmost point of the cyclopean eyellipse: 20 arcmin recommended, 16 acceptable, 12 minimum (only where accuracy and speed of reading are modest). 4.3.2.1 minimum contrast ratio between symbol and background: 5:1 night, 3:1 twilight, 3:1 day, 2:1 direct sunlight.
Report: the citation iso15008 now refers to the 2017 edition (Section 2.7 for character height, Section 6.5 for contrast). The 2003 preview gives the same contrast minimums for night, day and sunlight. Section 2.7 no longer cites you2021charsize (entry removed); reimer2014typeface stays for the typeface finding.
