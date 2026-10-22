# SW-7 data index

Generated 2026-10-22 by `tools/build_data_index.py` from commit 1d1c2e0 of https://github.com/0geder/Tukzie-HPEC-HUD. Do not edit by hand; run `python tools/build_data_index.py` again after adding data.

Each row is one file. Supports lists where the report cites the file (tex file: figure, table or section label; for the evidence table, the row), and plot inputs of `Report/figures/results/make_results_plots.py`. Test IDs follow `BenchTest/TEST_PROCEDURES.md`. To verify a copy, compare its SHA-256 (`sha256sum <file>` or `Get-FileHash -Algorithm SHA256 <file>`) with the value here. Checksums are of the files on disk when the index was built; a tracked file marked modified differs from the committed copy.

In git: yes = in the GitHub repository; no = on the author's OneDrive copy only (packed in the dated release archive if the report depends on it); outside repo = in the project folder next to the repository. Files marked private (video and pictures showing people) are held by the author and available on request; they are never packed.

## Summary

- Sources indexed: 182 files, 298.3 MB.
- Not in git: 31 files, 226.6 MB; of these the report depends on 25 (134.6 MB), 18 of them private.
- References in the report that resolve to no file: 2 (listed below).
- Files indexed but cited by nothing in the report: 46 (listed below).
- Release archive: `SW7_data_release_2026-10-22.zip` (see SHA256SUMS.txt inside).

## Sources by test

### T1

| Path | Date | Test | Supports | Size | SHA-256 | In git |
|---|---|---|---|---|---|---|
| `BenchTest/logs/2026-09-25_bench_fusion_shake.log` | 2026-09-25 | T1 | appendixc: tab:evidence-index (row: 25 Sep 2026, Recorded bench session, telemetry unit, 150 s from power-up) | 159.3 KB | `b3bdc8a843ab763b23d023787c498a5d2698de63a12849f5bdc8eb281bb79d14` | yes |
| `Report/figures/live_dashboard.png` | 2026-09-25 (mtime) | T1 | appendixb: fig:live-dashboard | 114.0 KB | `5e14551a6aa28575ddbf8b491a20fac98e7a4bea0ba117499f40085f99f4cd48` | yes |
| `Report/figures/recorded_session.png` | 2026-09-25 (mtime) | T1 | Results: fig:recorded-session | 92.8 KB | `92b4e6c9df7b2265437229889c813dd25d7dd0b74afffee84f39d34974e481c3` | yes |

### T2

| Path | Date | Test | Supports | Size | SHA-256 | In git |
|---|---|---|---|---|---|---|
| `BenchTest/logs/2026-09-29_v050_bench_test.log` | 2026-09-29 | T2 | appendixc: tab:evidence-index (row: 29 Sep 2026, Firmware v0.5.0 on the telemetry unit: commands, flash-write); plot input -> figures/results/imu_write_gaps | 412.1 KB | `f8cfc3f950e5d65d94378fcd6e40783fcbf6293ca1b9f492d1f356c4555156a9` | yes |
| `Report/figures/results/imu_write_gaps.pdf` | 2026-10-21 (mtime) | T2, T9 | Results: fig:res-imu-gaps | 45.4 KB | `c3567bb9734d658b23a166e4811fbe4cd751731ec248abd731414f4e8724f5a7` | yes |
| `Report/figures/results/imu_write_gaps.png` | 2026-10-21 (mtime) | T2, T9 | Results: fig:res-imu-gaps (PNG copy) | 127.8 KB | `16067becbcfc9da0c4bd9122f0c907ebb90d4eefdaab67f3757dd9fa8697ddd5` | yes |

### T3

| Path | Date | Test | Supports | Size | SHA-256 | In git |
|---|---|---|---|---|---|---|
| `BenchTest/logs/2026-09-29_gnss_rooftop.log` | 2026-09-29 | T3 | appendixc: tab:evidence-index (row: 29 Sep 2026, GNSS outdoor fix on a rooftop, firmware v0.5.0, raw replies ) | 227.1 KB | `e27175a77c23f007f83cd9f49df89fc2c0b1a149a4b8df29ce2bbf3c877a83e8` | yes |
| `BenchTest/logs/2026-09-29_gnss_rooftop_v051.log` | 2026-09-29 | T3 | not cited | 178.2 KB | `21596fd5ff3f84bd4155b14f5d61826842d70a4dafd6fe5c586550a95b157219` | yes |
| `BenchTest/logs/2026-09-30_gnss_rooftop_v052.log` | 2026-09-30 | T3 | appendixc: tab:evidence-index (row: 30 Sep 2026, GNSS outdoor fix with the corrected parser (v0.5.2), raw rep) | 237.5 KB | `9e5a8a8fb8e6b9600be9a8bd16900519dbbd9ded602673b64f15883ab77f85df` | yes |

### T6

| Path | Date | Test | Supports | Size | SHA-256 | In git |
|---|---|---|---|---|---|---|
| `BenchTest/logs/2026-09-30_signal_loss_test.log` | 2026-09-30 | T6 | appendixc: tab:evidence-index (row: 30 Sep 2026, MQTT recovery from a 60 s radio-off period ( AT+CFUN=4 , the) | 82.7 KB | `51a72ab80df4b868f7904fe8652314b61096bd64203d69d4729aff8bd9e57dc7` | yes |
| `BenchTest/logs/2026-09-30_signal_loss_test_v053.log` | 2026-09-30 | T6 | appendixc: tab:evidence-index (row: 30 Sep 2026, MQTT recovery from a 60 s radio-off period ( AT+CFUN=4 , the) | 303.7 KB | `82ae54d26db4debd3b057c68cc7dd311331466227d2eab4563c552981a24d0c0` | yes |

### T7

| Path | Date | Test | Supports | Size | SHA-256 | In git |
|---|---|---|---|---|---|---|
| `BenchTest/logs/2026-09-30_bms_vehicle_v054.log` | 2026-09-30 | T7 | not cited | 113.0 KB | `29a4f8569770b289f1bcfd8db545a76dd9059dd04bec06aa3523925b62e61d6e` | yes |
| `BenchTest/logs/2026-09-30_bms_vehicle_v054_try2.log` | 2026-09-30 | T7 | not cited | 67.7 KB | `042bf9ea1da5b90a4da2ee022ef261bdb702ed39f0324ff539bf74c81863eb25` | yes |

### T9

| Path | Date | Test | Supports | Size | SHA-256 | In git |
|---|---|---|---|---|---|---|
| `BenchTest/logs/2026-10-01_v060_bench_test.log` | 2026-10-01 | T9 | appendixc: tab:evidence-index (row: 1 Oct 2026, Firmware v0.6.0 bench run, 330 s, logging on throughout (buf); plot input -> figures/results/imu_write_gaps | 217.2 KB | `94db1c61d0c6870adc9efa932373a4fbf2484561ff9be6506127ffb8d1fcbfe2` | yes |

### T10

| Path | Date | Test | Supports | Size | SHA-256 | In git |
|---|---|---|---|---|---|---|
| `BenchTest/log_dump.py` | 2026-10-01 (mtime) | T10 | Methodology: sec:bench-tools; Methodology: sec:inv-json; appendixc: tab:evidence-index (row: 1 Oct 2026, Read-back of the stored telemetry log (firmware v0.6.3,) | 4.2 KB | `1035c817019067e8b3360aa2083adbd4ca0142e7fa48fa3a9a584136ad11c5d3` | yes |
| `BenchTest/logs/2026-10-01_telemetry_log_dump.clean.jsonl` | 2026-10-01 | T10 | appendixc: tab:evidence-index (row: 1 Oct 2026, Read-back of the stored telemetry log (firmware v0.6.3, Benc) | 2.1 MB | `7014999080a2307b6e06297a57d982dc54c6d2f1f5dcf6d1768ddc20e588b873` | yes |
| `BenchTest/logs/2026-10-01_telemetry_log_dump.jsonl` | 2026-10-01 | T10 | appendixc: tab:evidence-index (row: 1 Oct 2026, Read-back of the stored telemetry log (firmware v0.6.3, Benc) | 2.1 MB | `cf4f0077fb4162aa842dc3004bf837ce777042a27b025d423b0342764e6c31af` | yes |

### T15

| Path | Date | Test | Supports | Size | SHA-256 | In git |
|---|---|---|---|---|---|---|
| `BenchTest/logs/2026-10-11_sync_outage_test.log` | 2026-10-11 | T15 | appendixc: tab:evidence-index (row: 11 Oct 2026, Store-and-forward outage test T15, firmware v0.7.4, 10 min r); plot input -> figures/results/t15_outage_backlog | 729.0 KB | `40bc0fb9b230fa58980d7660f3415370db97937c7948009eddc983c14a3afc2d` | yes |
| `BenchTest/logs/2026-10-11_t15/2026-10-11_t15_boots.csv` | 2026-10-11 | T15 | appendixc: tab:evidence-index (row: 11 Oct 2026, Store-and-forward outage test T15, firmware v0.7.4, 10 min r) | 193 B | `dff332e87e6f89dfddaa77713f99e24f7741e15a21ba7e7b1155acf1d83f48e6` | yes |
| `BenchTest/logs/2026-10-11_t15/2026-10-11_t15_latency.csv` | 2026-10-11 | T15 | appendixc: tab:evidence-index (row: 11 Oct 2026, Store-and-forward outage test T15, firmware v0.7.4, 10 min r) | 54 B | `f36d139411d1f76a3796f60414e50fe4e495be4f30845845959161711d93e5cf` | yes |
| `BenchTest/logs/2026-10-11_t15/2026-10-11_t15_replay.csv` | 2026-10-11 | T15 | appendixc: tab:evidence-index (row: 11 Oct 2026, Store-and-forward outage test T15, firmware v0.7.4, 10 min r); plot input -> figures/results/t15_outage_backlog | 173 B | `e47d70df3a59244a4ddbbee5e9ccc0a80e7439d277e20a72d604fd7ee39b38d6` | yes |
| `BenchTest/logs/2026-10-11_t15/2026-10-11_t15_summary.csv` | 2026-10-11 | T15 | appendixc: tab:evidence-index (row: 11 Oct 2026, Store-and-forward outage test T15, firmware v0.7.4, 10 min r) | 599 B | `a0afa8e99a63205452b9949f17b9ddd0b4ec63398471dbed378b467233765bf8` | yes |
| `BenchTest/logs/2026-10-11_t15_device_log.clean.jsonl` | 2026-10-11 | T15 | not cited | 697.9 KB | `3fd6912c1b2eb49c1255e589c2c404412ccb5c3488a87be5441d21e2d45689a2` | no |
| `BenchTest/logs/2026-10-11_t15_device_log.jsonl` | 2026-10-11 | T15 | not cited | 697.9 KB | `3fd6912c1b2eb49c1255e589c2c404412ccb5c3488a87be5441d21e2d45689a2` | yes |
| `Report/figures/results/t15_outage_backlog.pdf` | 2026-10-21 (mtime) | T15 | Results: fig:res-t15 | 36.7 KB | `e614b104cedaf46b4c0bf9b500ee1eb803d2adbeff0413753f8aaff7cf34058d` | yes |
| `Report/figures/results/t15_outage_backlog.png` | 2026-10-21 (mtime) | T15 | Results: fig:res-t15 (PNG copy) | 61.6 KB | `a2769bf87acc63f421b1170a2adeef8f697ce6fbd6f907168be9632e2a65091a` | yes |
| `TelemetryUnit/test_host/run.py` | 2026-10-11 (mtime) | T15 | Methodology: sec:maintenance | 666 B | `ec3b1f3a376b803a61d5a8e7931010d154a82ce5c739b5acf5fce3e843d66892` | yes |
| `TelemetryUnit/test_host/test_sync_ledger.cpp` | 2026-10-11 (mtime) | T15 | Methodology: sec:maintenance | 13.2 KB | `25e487505aac2ab070cf4dee6a435de404bf10e2de4ff43684af3fe41b010b4c` | yes |

### C1

| Path | Date | Test | Supports | Size | SHA-256 | In git |
|---|---|---|---|---|---|---|
| `Report/evidence/2026-09-28_camera_run1_label_bug.txt` | 2026-09-28 | C1 | appendixc: tab:evidence-index (row: 28 Sep 2026, Hazard detector, first run on live camera frames) | 1017 B | `51a28d1cbbe718bcd75c1dd929c2b7beb54db023b6afe73ae8f8cb3962095eda` | yes |
| `Report/evidence/2026-09-28_camera_run2_after_fixes.txt` | 2026-09-28 | C1 | appendixc: tab:evidence-index (row: 28 Sep 2026, Hazard detector after the label and colour fixes) | 17.8 KB | `ed79c9a41fbacd83be18946755c8b06003266232ca9060ded402cdf576678fa5` | yes |

### C3

| Path | Date | Test | Supports | Size | SHA-256 | In git |
|---|---|---|---|---|---|---|
| `Report/evidence/c3/card2_all4.jpg` | 2026-10-01 (mtime) | C3 | appendixc: tab:evidence-index (row: 1 Oct 2026, Camera colour check (C3): stills with the standard and the N) | 30.4 KB | `60e810b80d8412315b47cd64a51cb05e6c0fb41443e8efdfa46813631e4c5550` | yes |
| `Report/evidence/c3/card2_blue.jpg` | 2026-10-01 (mtime) | C3 | appendixc: tab:evidence-index (row: 1 Oct 2026, Camera colour check (C3): stills with the standard and the N) | 29.2 KB | `223504e6b1e94ef82cc581a6f672662f511cdb912a168ea7b2aec43a0bfda8b4` | yes |
| `Report/evidence/c3/card2_green.jpg` | 2026-10-01 (mtime) | C3 | appendixc: tab:evidence-index (row: 1 Oct 2026, Camera colour check (C3): stills with the standard and the N) | 29.9 KB | `64b49e03b6fbcc855678e2772efa5f2546e8a88c3dc8a91f1f9a477d39e545d0` | yes |
| `Report/evidence/c3/card2_grey.jpg` | 2026-10-01 (mtime) | C3 | appendixc: tab:evidence-index (row: 1 Oct 2026, Camera colour check (C3): stills with the standard and the N) | 25.9 KB | `c711632d7da76d8a1ef52e2267c83666c879a7b91a91d5566cb0e58d57c2b776` | yes |
| `Report/evidence/c3/card2_white.jpg` | 2026-10-01 (mtime) | C3 | appendixc: tab:evidence-index (row: 1 Oct 2026, Camera colour check (C3): stills with the standard and the N) | 24.4 KB | `e51d666974e711f43ba46cc94ea9d61c92d7f5208b71280379fd05b3a4ce86f2` | yes |
| `Report/evidence/c3/card_blue.jpg` | 2026-10-01 (mtime) | C3 | appendixc: tab:evidence-index (row: 1 Oct 2026, Camera colour check (C3): stills with the standard and the N) | 11.9 KB | `13b171f06bfd5bf9363c6e11d09ac975c38cec35a8f0b4c23e8605c3d7a27bce` | yes |
| `Report/evidence/c3/card_blue_sat18.jpg` | 2026-10-01 (mtime) | C3 | appendixc: tab:evidence-index (row: 1 Oct 2026, Camera colour check (C3): stills with the standard and the N) | 29.8 KB | `782fae4fc5d2427d06b944864cfb1367c5b18797300b476285703f2830ba8386` | yes |
| `Report/evidence/c3/default.jpg` | 2026-10-01 (mtime) | C3 | appendixc: tab:evidence-index (row: 1 Oct 2026, Camera colour check (C3): stills with the standard and the N) | 174.2 KB | `a72bdd985f95e8480e3fbf22eddab68a0b5f03ecea7be36d7c46bed6ca54c248` | yes |
| `Report/evidence/c3/det.txt` | 2026-10-01 (mtime) | C3 | appendixc: tab:evidence-index (row: 1 Oct 2026, Camera colour check (C3): stills with the standard and the N) | 1.7 KB | `04c6fb57ff11aac1b77d3bb24aba8dd3ea65537ce046870fb744d361bf25698a` | yes |
| `Report/evidence/c3/detector_view.jpg` | 2026-10-01 (mtime) | C3 | appendixc: tab:evidence-index (row: 1 Oct 2026, Camera colour check (C3): stills with the standard and the N) | 26.1 KB | `d7ee8b97c700d907b4180b014ca88239bec2a39e9c2727d0bf4ab36b549e6e20` | yes |
| `Report/evidence/c3/detector_view_noir.jpg` | 2026-10-01 (mtime) | C3 | appendixc: tab:evidence-index (row: 1 Oct 2026, Camera colour check (C3): stills with the standard and the N) | 25.6 KB | `aa52157beee64f802da8874536f8cd88708e5c0a607cc6c08ab4863adfe45f6a` | yes |
| `Report/evidence/c3/noir.jpg` | 2026-10-01 (mtime) | C3 | appendixc: tab:evidence-index (row: 1 Oct 2026, Camera colour check (C3): stills with the standard and the N) | 162.7 KB | `994fb9ef37a5be9c21f50a5a80d8eefba967ad153b0e9952970d883df8085634` | yes |

### C4

| Path | Date | Test | Supports | Size | SHA-256 | In git |
|---|---|---|---|---|---|---|
| `BenchTest/logs/2026-09-30_c4_latency/run1_4t.csv` | 2026-09-30 | C4 | appendixc: tab:evidence-index (row: 30 Sep 2026, Camera detector latency on the Pi, three 60 s runs (4 thread); plot input -> figures/results/detector_latency | 55.1 KB | `98a356a696954dd9b97dfbf1f89ac444713b3dde4d8f57c75bd7092fabe8263f` | yes |
| `BenchTest/logs/2026-09-30_c4_latency/run1_4t.txt` | 2026-09-30 | C4 | appendixc: tab:evidence-index (row: 30 Sep 2026, Camera detector latency on the Pi, three 60 s runs (4 thread) | 3.1 KB | `5e332de20765066a32851c87dfc069e14040f50adca353965183bbef30b5141d` | yes |
| `BenchTest/logs/2026-09-30_c4_latency/run2_4t_preview.csv` | 2026-09-30 | C4 | appendixc: tab:evidence-index (row: 30 Sep 2026, Camera detector latency on the Pi, three 60 s runs (4 thread); plot input -> figures/results/detector_latency | 48.9 KB | `84bd211ae271971d7566e28784aa7981863b941849d5c5f2b9fbbf682902d5a8` | yes |
| `BenchTest/logs/2026-09-30_c4_latency/run2_4t_preview.txt` | 2026-09-30 | C4 | appendixc: tab:evidence-index (row: 30 Sep 2026, Camera detector latency on the Pi, three 60 s runs (4 thread) | 3.2 KB | `f374a7e33f4b0f3606fd0255ce7857f1725a970eab3513d197965c3bfc841edf` | yes |
| `BenchTest/logs/2026-09-30_c4_latency/run3_1t.csv` | 2026-09-30 | C4 | appendixc: tab:evidence-index (row: 30 Sep 2026, Camera detector latency on the Pi, three 60 s runs (4 thread); plot input -> figures/results/detector_latency | 20.4 KB | `319ba8993e43526e05bf52f662ff83f639b588104d5a8d9a67a9ff85569e09b7` | yes |
| `BenchTest/logs/2026-09-30_c4_latency/run3_1t.txt` | 2026-09-30 | C4 | appendixc: tab:evidence-index (row: 30 Sep 2026, Camera detector latency on the Pi, three 60 s runs (4 thread) | 3.1 KB | `7c1b63353b31c2641ffe7afedfe37a16416b579eadc51612efa586d41b893b93` | yes |
| `BenchTest/logs/2026-10-15_pi5_detector.log` | 2026-10-15 | C4 | appendixc: tab:evidence-index (row: 15 Oct 2026, Detector on the Raspberry Pi 5 with the dashboard running, s) | 3.7 KB | `370b05eb6a85732d9534dce3cf45efe7bac70739415bb49850793fd56fe4c087` | yes |
| `BenchTest/logs/2026-10-15_pi5_detector_timing.csv` | 2026-10-15 | C4 | plot input -> figures/results/detector_latency | 50.7 KB | `51d0b58d79111f03c14d77d24f9c96dedb09a54bcb497e4179093e5bb2b7741d` | yes |
| `Report/figures/results/detector_latency.pdf` | 2026-10-21 (mtime) | C4 | Results: fig:res-latency | 41.5 KB | `a6a2ca39b12a840af1a9f1b5874f77c8a12c20f394b5c03843dd922d94f71ad1` | yes |
| `Report/figures/results/detector_latency.png` | 2026-10-21 (mtime) | C4 | Results: fig:res-latency (PNG copy) | 67.9 KB | `7ff9a0cba4d7c54e710d622cf2bb4927d401a80a28d0d4fa2bb68cd3aa122e0a` | yes |

### C5

| Path | Date | Test | Supports | Size | SHA-256 | In git |
|---|---|---|---|---|---|---|
| `BenchTest/logs/calibration/20261019_120755_front_trike_10ft.jpg` | 2026-10-19 | C5 | not cited | 26.4 KB | `357d4d951bbe0b07d8609a23028ab35030d49b3e3f9fb1f514299c9e2fd0754a` | yes |
| `BenchTest/logs/calibration/20261019_124143_person_2m.jpg` | 2026-10-19 | C5 | not cited (private: held by the author) | 51.0 KB | `b13bd028d5fca24a17f89d72bd4591fd7673a116eb01ce74e735f3fc8aa33190` | yes |
| `BenchTest/logs/calibration/20261019_124143_person_2m_detections.json` | 2026-10-19 | C5 | not cited | 697 B | `ddb2b187b4f4e9dd5ce260cf66d88fe80e51fd348c0cfdb75b7d17a3bc4c16b6` | yes |
| `BenchTest/logs/calibration/20261019_124331_person_3m.jpg` | 2026-10-19 | C5 | not cited (private: held by the author) | 56.4 KB | `5dfe3524ab8f46d416d2b67a8ca0a464e320febdfadbe3d57dcf9edd7459dbad` | yes |
| `BenchTest/logs/calibration/20261019_124331_person_3m_detections.json` | 2026-10-19 | C5 | not cited | 1.2 KB | `66008059e50bb6571d225cc47e495b24c9529019d1181bebbb120a2e5bac2d48` | yes |
| `BenchTest/logs/calibration/20261019_markers_1m_2m_3m.jpg` | 2026-10-19 | C5 | not cited | 47.6 KB | `34335ff70dbeaa9b27ad5999dc7687fe0750bc16c25a9032b2364ce49593588d` | yes |
| `BenchTest/logs/calibration/rejected/20261019_123951_person_2m.jpg` | 2026-10-19 | C5 | not cited (private: held by the author) | 29.4 KB | `51a9ed11fe9527d237bd4873dbb41d83d287416fdab23c67b7524e1ac8660bdd` | no |
| `BenchTest/logs/calibration/rejected/20261019_123951_person_2m_detections.json` | 2026-10-19 | C5 | not cited | 699 B | `e7503d92a8c75bd568f63d1eda65fd829455d8ad650b8207da3a5a8a106cc309` | no |
| `BenchTest/logs/focal_cal.csv` | 2026-10-19 (mtime) | C5 | not cited | 341 B | `d9aa0c74e64c544d9c876be744ed59fde69bd7a7a74f6683007e142e295908cd` | yes |

### C6

| Path | Date | Test | Supports | Size | SHA-256 | In git |
|---|---|---|---|---|---|---|
| `BenchTest/logs/2026-09-30_sync_edges_run1_noisy.csv` | 2026-09-30 | C6 | appendixc: tab:evidence-index (row: 30 Sep 2026, Sync-pulse edges logged on the Pi (GPIO17, kernel timestamps) | 523 B | `fd2f1cdf4124dcb45795f6deb8797009ae00798cf43d5f6b155acd74bb4098a8` | yes |
| `BenchTest/logs/2026-09-30_sync_edges_run2.csv` | 2026-09-30 | C6 | appendixc: tab:evidence-index (row: 30 Sep 2026, Sync-pulse edges logged on the Pi (GPIO17, kernel timestamps) | 6.0 KB | `004f3be00ee6c67c803117b2c6a513688b2da46cfe2bcb8796ea12bfc7728502` | yes |

### C7

| Path | Date | Test | Supports | Size | SHA-256 | In git |
|---|---|---|---|---|---|---|
| `BenchTest/logs/2026-10-01_tof_cover_test.csv` | 2026-10-01 | C7 | not cited | 22.7 KB | `ce2eb9e908225049e40fdd30457e4a714491ecefebb4c92084309a3765914b0d` | yes |
| `BenchTest/logs/2026-10-01_tof_hand_test.csv` | 2026-10-01 | C7 | not cited | 35.0 KB | `7a2eb1a3ce080943147bf3d142bd7fc8a58c2c1f8f4303597fb50d84022b069f` | yes |
| `BenchTest/logs/2026-10-01_tof_three_sensors.csv` | 2026-10-01 | C7 | appendixc: tab:evidence-index (row: 1 Oct 2026, Stand-in ToF: micromouse sensor board on the Pi (three VL53L) | 7.3 KB | `222cb9acacb83f1952da48a15ce283dbf0a6aea73195ae0c99a82e98331fc2c9` | yes |
| `BenchTest/logs/2026-10-10_tof_hand_test.txt` | 2026-10-10 | C7 | Methodology: sec:inv-tof | 6.5 KB | `571720a840a4da4abda318d2ee262d1e7a7a74666ce87ccf4edea85fc98e2a25` | yes |
| `CameraDetection/tof_probe.py` | 2026-09-30 (mtime) | C7 | appendixc: tab:evidence-index (row: 1 Oct 2026, Stand-in ToF: micromouse sensor board on the Pi (three VL53L) | 2.8 KB | `6b904caa958c48856ac651d39ded77c355ab4232f63d56a6b6f7b7b54008360a` | yes |
| `CameraDetection/tof_reader.py` | 2026-10-10 (mtime) | C7 | appendixc: tab:evidence-index (row: 1 Oct 2026, Stand-in ToF: micromouse sensor board on the Pi (three VL53L); appendixd: app:wiring | 4.7 KB | `b70e95f7d247e41102b39b73cc621cc6332903784fc59e502d14842c52007fd9` | yes |

### C8a

| Path | Date | Test | Supports | Size | SHA-256 | In git |
|---|---|---|---|---|---|---|
| `CameraDetection/ncnn_bench.py` | 2026-10-02 (mtime) | C8a | appendixc: tab:evidence-index (row: 2 Oct 2026, YOLO11n (COCO) via NCNN on the Raspberry Pi 4, 320 input, 4 ); appendixe: sec:diagnoses | 8.4 KB | `f622b9948b04792df837af6a5fc6c04aa535d2df3493db1024335e99aaa9202b` | yes |

### C9

| Path | Date | Test | Supports | Size | SHA-256 | In git |
|---|---|---|---|---|---|---|
| `CameraDetection/fusion_config.json` | 2026-10-15 (mtime) | C9 | not cited | 754 B | `39fe4ec17fc329b80f928f06fc36cf7cea4fa5c4ecaec8e56bcb8e50e0acd46b` | yes |
| `CameraDetection/tests/test_sensor_fusion.py` | 2026-10-15 (mtime) | C9 | appendixc: tab:evidence-index (row: 4 Oct 2026, Camera and time-of-flight fusion, offline tests) | 23.6 KB | `7d3081ea9b9f9c31046a41ffc6a91a6fb5d44873e68976c027b967526601e4e9` | yes |

### B1

| Path | Date | Test | Supports | Size | SHA-256 | In git |
|---|---|---|---|---|---|---|
| `Report/evidence/2026-09-25_bench_console_replay.png` | 2026-09-25 | B1 | appendixc: fig:console-replay; appendixc: tab:evidence-index (row: 25 Sep 2026, The same log replayed through the bench console (Figure fig:) | 379.7 KB | `cd7e2bed13eb8affe0bf5756a17c37c0918cd192749cf99eba1485c3c1db639b` | yes |

### B2

| Path | Date | Test | Supports | Size | SHA-256 | In git |
|---|---|---|---|---|---|---|
| `DashboardIntegration/tests/test_front_camera_page_live.py` | 2026-10-01 (mtime) | B2 | appendixc: tab:evidence-index (row: 1 Oct 2026, Dashboard camera page (laptop, offscreen) against the live d) | 2.0 KB | `f90cd4d16552a3aeb1fa5e1e0ad4aad7d95a4158be8c6cb220edab600e21c43f` | yes |
| `Report/evidence/2026-10-01_dashboard_page_live.png` | 2026-10-01 | B2 | appendixc: tab:evidence-index (row: 1 Oct 2026, Dashboard camera page (laptop, offscreen) against the live d) | 348.7 KB | `80e560b4879a38ae8b49658316c86d2f38a68d8c9ff777035a7e05096ecbcb0c` | yes |
| `Report/evidence/2026-10-01_dashboard_page_person.png` | 2026-10-01 | B2 | appendixc: tab:evidence-index (row: 1 Oct 2026, Dashboard camera page against the live detector with a perso) (private: held by the author) | 320.1 KB | `3e11f088ac3a2a4f212058e25a74e285edc6609e7e4ebcc6af677fa9ad112c66` | yes |

### B3

| Path | Date | Test | Supports | Size | SHA-256 | In git |
|---|---|---|---|---|---|---|
| `DashboardIntegration/tests/test_live_data_provider.py` | 2026-10-15 (mtime) | B3 | appendixc: tab:evidence-index (row: 3 Oct 2026, Dashboard live-only mode and automatic Raspberry Pi 4 findin) | 28.9 KB | `886d56c783b8c5e5cf980611cad2c534f0e6e4ff1079a09b43801388b3a600dd` | yes |

### B4

| Path | Date | Test | Supports | Size | SHA-256 | In git |
|---|---|---|---|---|---|---|
| `DashboardIntegration/tests/tile_map_flat_drive.png` | 2026-10-15 (mtime) | B4 | appendixc: tab:evidence-index (row: 4 Oct 2026, Street-tile map, offscreen, fed the generated UCT replay tra) | 86.6 KB | `0fe1a14cfd66c3dbe836b3a42f967bca02fc939b60dc4c6d814449d46e88f51f` | yes (modified) |
| `DashboardIntegration/tests/tile_map_follow.png` | 2026-10-15 (mtime) | B4 | appendixc: tab:evidence-index (row: 4 Oct 2026, Street-tile map, offscreen, fed the generated UCT replay tra) | 83.6 KB | `a2aa745722b0bf015f68f11a4f9d432d51fcd1fd84701378b9791f1d31b292f6` | yes (modified) |
| `DashboardIntegration/tests/tile_map_navigation_pi5.png` | 2026-10-07 (mtime) | B4 | appendixc: tab:evidence-index (row: 4 Oct 2026, Street-tile map, offscreen, fed the generated UCT replay tra) | 38.1 KB | `d4f9748430e2daa4922dd3d87d1988d64d35cbbaf6e2fb53c6d1f2ca1199be72` | yes |
| `DashboardIntegration/tests/tile_map_network_position.png` | 2026-10-15 (mtime) | B4 | appendixc: tab:evidence-index (row: 4 Oct 2026, Street-tile map, offscreen, fed the generated UCT replay tra) | 55.5 KB | `5a1f15f83517e43ea4fee5a86389a31594d617c82a844ba6d929e06c9557ad7f` | yes (modified) |
| `DashboardIntegration/tests/tile_map_no_fix.png` | 2026-10-15 (mtime) | B4 | appendixc: tab:evidence-index (row: 4 Oct 2026, Street-tile map, offscreen, fed the generated UCT replay tra) | 84.6 KB | `06597e644afeb867fb0da5c7b6f7c663680fc1e1aa890107ef1626f5854ccce5` | yes |
| `DashboardIntegration/tests/tile_map_offline.png` | 2026-10-15 (mtime) | B4 | appendixc: tab:evidence-index (row: 4 Oct 2026, Street-tile map, offscreen, fed the generated UCT replay tra) | 24.4 KB | `19e38fe645d063b6447e39a33c5b8cb4a4a2fe81e8e3b9d3e47cd9d4af20663b` | yes |
| `DashboardIntegration/tests/tile_map_replay.png` | 2026-10-15 (mtime) | B4 | appendixc: tab:evidence-index (row: 4 Oct 2026, Street-tile map, offscreen, fed the generated UCT replay tra) | 84.3 KB | `4e61a5fb23142d7667a55fe2993a2f40b7ca9e8cb7ab4b23018ff6e892d38277` | yes (modified) |
| `DashboardIntegration/tests/tile_map_simulated_drive.png` | 2026-10-15 (mtime) | B4 | appendixc: tab:evidence-index (row: 4 Oct 2026, Street-tile map, offscreen, fed the generated UCT replay tra); appendixc: tab:evidence-index (row: 6 Oct 2026, Simulated drive on the street map, offscreen tests) | 124.2 KB | `55ffb1bb55ccac8a8f8e8d05b8f8108716c4800e9bf8d3812f11d9621d6df489` | yes (modified) |
| `DashboardIntegration/tests/tile_map_tilt_drive.png` | 2026-10-15 (mtime) | B4 | appendixc: tab:evidence-index (row: 4 Oct 2026, Street-tile map, offscreen, fed the generated UCT replay tra) | 105.2 KB | `ad7880304859bbdc5d44cda464d8a6d1dcad6e71330fb21fe37db3150f7ffabd` | yes (modified) |

### B5

| Path | Date | Test | Supports | Size | SHA-256 | In git |
|---|---|---|---|---|---|---|
| `DashboardIntegration/PI5_MAP_CRASH.md` | 2026-10-02 (mtime) | B5 | appendixc: tab:evidence-index (row: 2 Oct 2026, Dashboard map crash on the Raspberry Pi 5, diagnosed over ss) | 3.0 KB | `f12eac5dc2f00a05c3de72468e886d0a405402fbd4417347eafa700044653491` | yes |

### Power

| Path | Date | Test | Supports | Size | SHA-256 | In git |
|---|---|---|---|---|---|---|
| `BenchTest/logs/2026-10-06_pi4_power_watch.log` | 2026-10-06 | Power | Methodology: sec:inv-power; appendixc: tab:evidence-index (row: 6 Oct 2026, Raspberry Pi 4 power and temperature watcher, 20 min) | 7.0 KB | `449cade9c6a789c16fc35c7f9cbcd9676550e2aee08c951b58f3202b58004862` | yes |
| `BenchTest/logs/2026-10-10_bench_observations.md` | 2026-10-10 | Power | Methodology: sec:inv-power; appendixc: tab:evidence-index (row: 10 to 11 Oct 2026, Raspberry Pi 4 reboots, temperature and detector timing with) | 2.8 KB | `10d6337810533950ae58168cf9036b920abae92ef4e67831d3f67aa1227522c6` | yes |

### Pothole model

| Path | Date | Test | Supports | Size | SHA-256 | In git |
|---|---|---|---|---|---|---|
| `CameraDetection/training/runs/colab_session_2026-10-02.ipynb` | 2026-10-02 | Pothole model | not cited | 958.8 KB | `d72fc582a62ba8c23998e2c7b412d510f1a535a012b9a0e06097519dc028c51f` | yes |
| `CameraDetection/training/runs/colab_session_2026-10-06.ipynb` | 2026-10-06 | Pothole model | not cited | 31.7 KB | `6a8ee84301814445499bf182709e9a15b508ac6a5bc24ca0adbc2630e379f89a` | yes |
| `CameraDetection/training/runs/run1_gerapothole_640/BoxPR_curve.png` | 2026-10-02 (mtime) | Pothole model | appendixc: tab:evidence-index (row: 2 Oct 2026, First pothole model: YOLO11n fine-tuned in Colab (T4) on a p) | 91.2 KB | `60f7f9b439e67e213244a8fc7829755abf9a3d28f2db989d87f939302c2124ca` | yes |
| `CameraDetection/training/runs/run1_gerapothole_640/best.pt` | 2026-10-02 (mtime) | Pothole model | appendixc: tab:evidence-index (row: 2 Oct 2026, First pothole model: YOLO11n fine-tuned in Colab (T4) on a p) | 5.2 MB | `a1ce501e143d8127d98ab7a5e781c5172f755e54a25230faf083c65a314218ad` | yes |
| `CameraDetection/training/runs/run1_gerapothole_640/confusion_matrix.png` | 2026-10-02 (mtime) | Pothole model | appendixc: tab:evidence-index (row: 2 Oct 2026, First pothole model: YOLO11n fine-tuned in Colab (T4) on a p) | 101.1 KB | `bdcc46bf2f4b3b1bb984cfb7512686b57af8cbf97b199223f32e2c0f151cf14e` | yes |
| `CameraDetection/training/runs/run1_gerapothole_640/results.csv` | 2026-10-02 (mtime) | Pothole model | appendixc: tab:evidence-index (row: 2 Oct 2026, First pothole model: YOLO11n fine-tuned in Colab (T4) on a p) | 5.4 KB | `29430e41f69c3cbd15710b9d2b86ecbc00637f019b845c395e357623a37298dd` | yes |
| `CameraDetection/training/runs/run1_gerapothole_640/results.png` | 2026-10-02 (mtime) | Pothole model | appendixc: tab:evidence-index (row: 2 Oct 2026, First pothole model: YOLO11n fine-tuned in Colab (T4) on a p) | 295.0 KB | `6c71f7c5a20f0a4e5c43d7bf9e64e5cd6f10a5eabcb84d20257197cec55a7414` | yes |
| `CameraDetection/training/runs/run1_gerapothole_640/training_record.json` | 2026-10-02 (mtime) | Pothole model | appendixc: tab:evidence-index (row: 2 Oct 2026, First pothole model: YOLO11n fine-tuned in Colab (T4) on a p); appendixc: tab:evidence-index (row: 6 Oct 2026, Pothole model run 2, South African road-band tiles (Colab)) | 597 B | `9917ea68b1e268f9107907fa99804f764c27e966e8d7cfc8f2671ea917822d04` | yes |
| `CameraDetection/training/runs/run1_gerapothole_640/yolo11n_pothole_320_ncnn_model/metadata.yaml` | 2026-10-02 (mtime) | Pothole model | appendixc: tab:evidence-index (row: 2 Oct 2026, First pothole model: YOLO11n fine-tuned in Colab (T4) on a p) | 397 B | `1de040620e34f52144b3dd2c92b5e0129aad4fc64ad56bf09cebf4a8f9fa34db` | yes |
| `CameraDetection/training/runs/run1_gerapothole_640/yolo11n_pothole_320_ncnn_model/model.ncnn.bin` | 2026-10-02 (mtime) | Pothole model | appendixc: tab:evidence-index (row: 2 Oct 2026, First pothole model: YOLO11n fine-tuned in Colab (T4) on a p) | 9.9 MB | `000b96c66214f593ab3c7fd3e21ca1ce712455ac420a14acb731529ca79b249e` | yes |
| `CameraDetection/training/runs/run1_gerapothole_640/yolo11n_pothole_320_ncnn_model/model.ncnn.param` | 2026-10-02 (mtime) | Pothole model | appendixc: tab:evidence-index (row: 2 Oct 2026, First pothole model: YOLO11n fine-tuned in Colab (T4) on a p) | 22.2 KB | `8ca9b78856ff0379fafe472513f292479d37f71702e68766098f8d5723251f74` | yes |
| `CameraDetection/training/runs/run1_gerapothole_640/yolo11n_pothole_320_ncnn_model/model_ncnn.py` | 2026-10-02 (mtime) | Pothole model | appendixc: tab:evidence-index (row: 2 Oct 2026, First pothole model: YOLO11n fine-tuned in Colab (T4) on a p) | 797 B | `7b0898c85d5168962a17c88a0c326cf849733702703c8cdb6e7f1fed84e85e3e` | yes |
| `CameraDetection/training/runs/run1_gerapothole_640/yolo11n_pothole_640_ncnn_model/metadata.yaml` | 2026-10-02 (mtime) | Pothole model | appendixc: tab:evidence-index (row: 2 Oct 2026, First pothole model: YOLO11n fine-tuned in Colab (T4) on a p) | 397 B | `82e822b992e5872992c2a00d909d198bb9d17572556cab4db4fff0abbbb79b85` | yes |
| `CameraDetection/training/runs/run1_gerapothole_640/yolo11n_pothole_640_ncnn_model/model.ncnn.bin` | 2026-10-02 (mtime) | Pothole model | appendixc: tab:evidence-index (row: 2 Oct 2026, First pothole model: YOLO11n fine-tuned in Colab (T4) on a p) | 9.9 MB | `9496f151f728b0a67b765d485403f8649c4b75571ce7738fceaadba6b5429feb` | yes |
| `CameraDetection/training/runs/run1_gerapothole_640/yolo11n_pothole_640_ncnn_model/model.ncnn.param` | 2026-10-02 (mtime) | Pothole model | appendixc: tab:evidence-index (row: 2 Oct 2026, First pothole model: YOLO11n fine-tuned in Colab (T4) on a p) | 22.2 KB | `f1dbf5fbfb524490cf3942f6fd527c312fb04b3b71bbe4256d117c4afc11f2d8` | yes |
| `CameraDetection/training/runs/run1_gerapothole_640/yolo11n_pothole_640_ncnn_model/model_ncnn.py` | 2026-10-02 (mtime) | Pothole model | appendixc: tab:evidence-index (row: 2 Oct 2026, First pothole model: YOLO11n fine-tuned in Colab (T4) on a p) | 797 B | `d0566348486cfd559ef558605e5872059a654457d425771ef5dd640eb6f8571b` | yes |
| `CameraDetection/training/runs/run2_sa_band_tiles_640/BoxPR_curve.png` | 2026-10-06 (mtime) | Pothole model | not cited | 87.9 KB | `a52b81e043290d3deb093dccaf8b11f7a7f78f096fbc8fc31ac59a3effed8155` | yes |
| `CameraDetection/training/runs/run2_sa_band_tiles_640/README.md` | 2026-10-11 (mtime) | Pothole model | not cited | 1.8 KB | `24d71cebf230e592d75dc7d37474c0e85b0556f1053ec8184ac77007db382817` | yes |
| `CameraDetection/training/runs/run2_sa_band_tiles_640/best.pt` | 2026-10-06 (mtime) | Pothole model | not cited | 5.2 MB | `0bd12b7eab7828acee7f02463e1b03d40c2f6d17ec1dcb8edd52d210fbd77d2f` | yes |
| `CameraDetection/training/runs/run2_sa_band_tiles_640/confusion_matrix.png` | 2026-10-06 (mtime) | Pothole model | not cited | 104.3 KB | `0150584066e9870321e2d39a00490cffa8284f90e8989c397706ba9cb80c6815` | yes |
| `CameraDetection/training/runs/run2_sa_band_tiles_640/results.csv` | 2026-10-06 (mtime) | Pothole model | not cited | 7.0 KB | `96a24a79536d2a02301daea96f6bba15298e93c61820e6b6dcf4e9bd72d5d231` | yes |
| `CameraDetection/training/runs/run2_sa_band_tiles_640/results.png` | 2026-10-06 (mtime) | Pothole model | not cited | 280.0 KB | `1911d6b64c80d04b06faf32c26bd98c19b31e89a5e786b882d9337a967dd6725` | yes |
| `CameraDetection/training/runs/run2_sa_band_tiles_640/training_record.json` | 2026-10-06 (mtime) | Pothole model | appendixc: tab:evidence-index (row: 6 Oct 2026, Pothole model run 2, South African road-band tiles (Colab)) | 636 B | `dbecb101146b188287b676702646bc2f5ef068a7d586ef9b5f101e7d08b20f0a` | yes |
| `CameraDetection/training/runs/run2_sa_band_tiles_640/yolo11n_sa_band_tiles_320_ncnn_model/metadata.yaml` | 2026-10-06 (mtime) | Pothole model | not cited | 403 B | `d53a9590ea12d07d24ba60fa787664ab4e8ad051db50f4c27936cd4f47b26eab` | yes |
| `CameraDetection/training/runs/run2_sa_band_tiles_640/yolo11n_sa_band_tiles_320_ncnn_model/model.ncnn.bin` | 2026-10-06 (mtime) | Pothole model | not cited | 9.9 MB | `49cfd677a072fd2aa1320a7cceccb057821dd9c8154b5a8be791a3373905d4fa` | yes |
| `CameraDetection/training/runs/run2_sa_band_tiles_640/yolo11n_sa_band_tiles_320_ncnn_model/model.ncnn.param` | 2026-10-06 (mtime) | Pothole model | not cited | 22.2 KB | `8ca9b78856ff0379fafe472513f292479d37f71702e68766098f8d5723251f74` | yes |
| `CameraDetection/training/runs/run2_sa_band_tiles_640/yolo11n_sa_band_tiles_320_ncnn_model/model_ncnn.py` | 2026-10-06 (mtime) | Pothole model | not cited | 809 B | `9fbb310bccd88ce3734e7f5ab17ba9cace7fc21e07ef91bf86e5b62437d44faf` | yes |
| `CameraDetection/training/runs/run2_sa_band_tiles_640/yolo11n_sa_band_tiles_640_ncnn_model/metadata.yaml` | 2026-10-06 (mtime) | Pothole model | not cited | 403 B | `8930d2fb3fe7d6e1b29fda74a53a1b9bd23b7046d87812ef2115291fe1fb4c68` | yes |
| `CameraDetection/training/runs/run2_sa_band_tiles_640/yolo11n_sa_band_tiles_640_ncnn_model/model.ncnn.bin` | 2026-10-06 (mtime) | Pothole model | not cited | 9.9 MB | `debecbb29ec7cb694d12f07412538d9f3b6fff261470e3f9907952ecd8ee97f7` | yes |
| `CameraDetection/training/runs/run2_sa_band_tiles_640/yolo11n_sa_band_tiles_640_ncnn_model/model.ncnn.param` | 2026-10-06 (mtime) | Pothole model | not cited | 22.2 KB | `f1dbf5fbfb524490cf3942f6fd527c312fb04b3b71bbe4256d117c4afc11f2d8` | yes |
| `CameraDetection/training/runs/run2_sa_band_tiles_640/yolo11n_sa_band_tiles_640_ncnn_model/model_ncnn.py` | 2026-10-06 (mtime) | Pothole model | not cited | 809 B | `883ea3af46122ef7af8b1c86d62091483ee4c904ed5a0bfdd319dbcfb22d2c11` | yes |

### Road run 1

| Path | Date | Test | Supports | Size | SHA-256 | In git |
|---|---|---|---|---|---|---|
| `../Roadtest1/WhatsApp Image 2026-10-21 at 21.07.19 (1).jpeg` | 2026-10-21 | Road run 1 | appendixi: app:road1 (private: held by the author) | 129.5 KB | `ae8e13f59cdad57eaf6fc66d12b58556187a8ae2ca839f68367663394b45f104` | outside repo |
| `../Roadtest1/WhatsApp Image 2026-10-21 at 21.07.19 (2).jpeg` | 2026-10-21 | Road run 1 | appendixi: app:road1 (private: held by the author) | 190.3 KB | `96c874f5e4439a963650516a7923452a05575731b23bccb6a5eda62ba9b4c818` | outside repo |
| `../Roadtest1/WhatsApp Image 2026-10-21 at 21.07.19.jpeg` | 2026-10-21 | Road run 1 | appendixi: app:road1 (private: held by the author) | 193.7 KB | `405ec53f619ec40df5d572da7134fb079a2c27530a401e4c6907143b7fb9d970` | outside repo |
| `../Roadtest1/WhatsApp Image 2026-10-21 at 21.07.45.jpeg` | 2026-10-21 | Road run 1 | appendixi: app:road1 (private: held by the author) | 102.9 KB | `cc227da1e8853069af6811dce2cb9184b2a2aa398ef0e12394aa7d8d169793ae` | outside repo |
| `../Roadtest1/WhatsApp Image 2026-10-21 at 21.07.53.jpeg` | 2026-10-21 | Road run 1 | appendixi: app:road1 (private: held by the author) | 124.2 KB | `2dd98a511b230c00493fc899da3e5a906c3b8404167215acd27ecd5972f53575` | outside repo |
| `../Roadtest1/WhatsApp Image 2026-10-21 at 21.08.19 (1).jpeg` | 2026-10-21 | Road run 1 | appendixi: app:road1 (private: held by the author) | 188.5 KB | `ac84906cf5d71e5e82de29b5a975e67474c0295a056d16f98092066adf2b08c5` | outside repo |
| `../Roadtest1/WhatsApp Image 2026-10-21 at 21.08.19 (2).jpeg` | 2026-10-21 | Road run 1 | appendixi: app:road1 (private: held by the author) | 222.4 KB | `cd8885799f7c9a389fc50efe7d2d7f39ff41ab29228a82d6c4850822fc9e452c` | outside repo |
| `../Roadtest1/WhatsApp Image 2026-10-21 at 21.08.19.jpeg` | 2026-10-21 | Road run 1 | appendixi: app:road1 (private: held by the author) | 156.2 KB | `1ea1822a5dad17dcffb7d517f1472052e6f63482f36fc8e98410ef316889d885` | outside repo |
| `../Roadtest1/WhatsApp Image 2026-10-21 at 21.08.20 (1).jpeg` | 2026-10-21 | Road run 1 | appendixi: app:road1 (private: held by the author) | 254.4 KB | `7f31c8b79ecac30ee2a46c22454bd42941c74428e5bb62bd9b9717386b94151e` | outside repo |
| `../Roadtest1/WhatsApp Image 2026-10-21 at 21.08.20 (2).jpeg` | 2026-10-21 | Road run 1 | appendixi: app:road1 (private: held by the author) | 309.7 KB | `2f8818b67ba7f33dadf9272ab4a9d2abd642901f5911e6e04ad1f5d164864d1b` | outside repo |
| `../Roadtest1/WhatsApp Image 2026-10-21 at 21.08.20.jpeg` | 2026-10-21 | Road run 1 | appendixi: app:road1 (private: held by the author) | 175.5 KB | `1ce30ddcb9f5083724a12d8226ab6a39e268b0c31a5c580ac42227f61af57497` | outside repo |
| `../Roadtest1/WhatsApp Image 2026-10-21 at 21.08.21.jpeg` | 2026-10-21 | Road run 1 | appendixi: app:road1 (private: held by the author) | 1.4 MB | `5bea80952709127cbf3f12f99fb2def2c183fc9c68859f0b04b99ab1e927a557` | outside repo |
| `../Roadtest1/WhatsApp Video 2026-10-21 at 21.07.44.mp4` | 2026-10-21 | Road run 1 | appendixi: app:road1; appendixi: tab:road1-videos (private: held by the author) | 9.5 MB | `4e0b7e3f4859145c276c4401a126f7ff6ade5b7f9a8ef878aff2593f58f722ab` | outside repo |
| `../Roadtest1/WhatsApp Video 2026-10-21 at 21.07.53.mp4` | 2026-10-21 | Road run 1 | appendixi: app:road1; appendixi: tab:road1-videos (private: held by the author) | 3.9 MB | `4eefb7848f51adc731307bbce6c35cb659f5efd2f223cae56c5f9f9e020d9c94` | outside repo |
| `../Roadtest1/WhatsApp Video 2026-10-21 at 21.08.18.mp4` | 2026-10-21 | Road run 1 | appendixi: app:road1; appendixi: tab:road1-videos (private: held by the author) | 1.7 MB | `f66d7f2f53c223cb42777219c10b709d332e66703a64b349d3b1ecb5546b2d63` | outside repo |
| `../Roadtest1/WhatsApp Video 2026-10-21 at 21.08.19.mp4` | 2026-10-21 | Road run 1 | appendixi: app:road1; appendixi: tab:road1-videos (private: held by the author) | 3.2 MB | `df4496a0d276c7e941935faeecf4e5691d0d6dabef6530fa40c0320d4c64c46f` | outside repo |
| `../Roadtest1/WhatsApp Video 2026-10-21 at 21.08.20.mp4` | 2026-10-21 | Road run 1 | appendixi: app:road1; appendixi: tab:road1-videos (private: held by the author) | 9.1 MB | `c1e7c021f2adc307a005d8df959ce739acacfe36ca34a7419ebe4f0ea0b458d6` | outside repo |
| `../Roadtest1/edit/TUKZIE_roadtest1_reel.mp4` | 2026-10-21 (mtime) | Road run 1 | appendixi: app:road1 (private: held by the author) | 73.8 MB | `5fce3e8092a114cc61657d2a9256fdfd9811b1b87875f57fefd7659509a82e2c` | outside repo |
| `BenchTest/logs/roadtest_2026-10-19/2026-10-19_171534_roadtest.jsonl` | 2026-10-19 | Road run 1 | Results: fig:res-road; appendixc: tab:evidence-index (row: 19 Oct 2026, First road session, recorder on the Raspberry Pi 5, 17:15 to); plot input -> figures/results/road_session_1019 | 21.5 MB | `9c72060f92588635b024c40fd3cbea93c18cb7e0f467a89c2e7f70843330c62e` | no |
| `BenchTest/logs/roadtest_2026-10-19/2026-10-19_190354_roadtest.jsonl` | 2026-10-19 | Road run 1 | appendixc: tab:evidence-index (row: 19 Oct 2026, First road session, recorder on the Raspberry Pi 5, 17:15 to) | 1.1 MB | `bcb5e39ac837848e69fcbb0c098109d8a1893af0e70eacb1441cd831eb94e347` | no |
| `BenchTest/logs/roadtest_2026-10-19/2026-10-19_190856_roadtest.jsonl` | 2026-10-19 | Road run 1 | appendixc: tab:evidence-index (row: 19 Oct 2026, First road session, recorder on the Raspberry Pi 5, 17:15 to) | 118.3 KB | `2ae21d15bb5e4cca5b11ff20d7525c56426fda1061e46a2c0c4f31e5984a5c3e` | no |
| `BenchTest/logs/roadtest_2026-10-19/pi4_rear_alerts.jsonl` | 2026-10-19 | Road run 1 | appendixc: tab:evidence-index (row: 19 Oct 2026, First road session, recorder on the Raspberry Pi 5, 17:15 to) | 5.9 MB | `849ffd30ea72774baf28559c9c21f340d847309062890cbf4c2208b4b4b624a5` | no |
| `BenchTest/logs/roadtest_2026-10-19/pi5_front_alerts.jsonl` | 2026-10-19 | Road run 1 | appendixc: tab:evidence-index (row: 19 Oct 2026, First road session, recorder on the Raspberry Pi 5, 17:15 to) | 1.0 MB | `3dadc2d579bd9cb614e96c1e8ce68f712f3e36b2b5ea4d7394d85a1e65a5b855` | no |
| `BenchTest/logs/roadtest_2026-10-19/pi5_powerwatch.log` | 2026-10-19 | Road run 1 | appendixc: tab:evidence-index (row: 19 Oct 2026, First road session, recorder on the Raspberry Pi 5, 17:15 to) | 389.6 KB | `53a72472deb7c51d745a26d0cf21e28c32a3f91ba783e3b878e659f4d06e6ad2` | no |
| `BenchTest/logs/roadtest_2026-10-19/roadtest_markers.txt` | 2026-10-19 | Road run 1 | appendixc: tab:evidence-index (row: 19 Oct 2026, First road session, recorder on the Raspberry Pi 5, 17:15 to) | 59 B | `43956401d601da6b82ea36fe82398085ff6c5bee16f116253a9c21c1dc91ac57` | no |
| `Report/figures/results/road_session_1019.pdf` | 2026-10-21 (mtime) | Road run 1 | Results: fig:res-road | 76.5 KB | `09dc3aeaf1945079fef408c1a28cf205100f199fc3861b512d77929f5b9dd700` | yes |
| `Report/figures/results/road_session_1019.png` | 2026-10-21 (mtime) | Road run 1 | Results: fig:res-road (PNG copy) | 91.3 KB | `209c4ab47f6873060cde29be690d4ca1ae8298ca8f7d153c9c481f41fdd9a95c` | yes |
| `Report/figures/road1/chassis_rear.jpg` | 2026-10-21 (mtime) | Road run 1 | appendixi: fig:road1-vehicle | 325.3 KB | `701d2c23d7f588fa36660711bf35dffbdccb389bf236d1612ce1df494f74c848` | yes |
| `Report/figures/road1/chassis_rear_close.jpg` | 2026-10-21 (mtime) | Road run 1 | appendixi: fig:road1-vehicle | 285.0 KB | `a7b175fdeb670c7241ef6a0b311b09df5273dcb35d57d1342b1b92a4a0e0ac0c` | yes |
| `Report/figures/road1/chassis_rear_wide.jpg` | 2026-10-21 (mtime) | Road run 1 | appendixi: fig:road1-vehicle | 179.5 KB | `df80245194379a47f128bc3e2ad2fed0736e49d9dcc5cb3cb57cdbdb8aa98f49` | yes |
| `Report/figures/road1/dash_on_bar.jpg` | 2026-10-21 (mtime) | Road run 1 | appendixi: fig:road1-dash | 253.7 KB | `44136871adb26b5d5ab6b3becbc2647993a4f87d2b553ad807bbaa049f31d6bf` | yes |
| `Report/figures/road1/dash_on_bar_seated.jpg` | 2026-10-21 (mtime) | Road run 1 | appendixi: fig:road1-dash | 220.0 KB | `dc186ab6cd7d8b1c42c31207a5e35ce0fff7df2019765efab283009d17aecd37` | yes |
| `Report/figures/road1/pod_closed_hood.jpg` | 2026-10-21 (mtime) | Road run 1 | appendixi: fig:road1-pod | 143.5 KB | `a08f410a5954f4e9d892a5fd1bfe277b63c344a168a40acbf302c97ffb04e309` | yes |
| `Report/figures/road1/pod_lid_antenna.jpg` | 2026-10-21 (mtime) | Road run 1 | appendixi: fig:road1-pod | 173.5 KB | `3cad6e9e88348994a6107391535af057976df23e3fa3c7914fb165cef942a139` | yes |
| `Report/figures/road1/pod_open_bays.jpg` | 2026-10-21 (mtime) | Road run 1 | appendixi: fig:road1-pod | 208.5 KB | `1837d6a187ddfb5d19e9ba9f889c10a4e3f897416a92c9a7887a335ec4c83233` | yes |
| `Report/figures/road1/pod_open_top.jpg` | 2026-10-21 (mtime) | Road run 1 | appendixi: fig:road1-pod | 210.1 KB | `fd6453cae454d70abad1bf1daa9f7debbc955b03fdb45255202ce6b068b92265` | yes |
| `Report/figures/road1/vid_chassis_side.jpg` | 2026-10-21 (mtime) | Road run 1 | appendixi: fig:road1-vehicle | 126.4 KB | `2f06a902b9a20ae2b05701c4893b2f7ec36b1dfd6d1ed00787733ba29b1db3a7` | yes |
| `Report/figures/road1/vid_dash_drive.jpg` | 2026-10-21 (mtime) | Road run 1 | appendixi: fig:road1-dash | 72.5 KB | `48a00c1b5410008a673e5676a468fd5d52e5685e8e0c730f261dbc575b4117f0` | yes |
| `Report/figures/road1/vid_dash_mount.jpg` | 2026-10-21 (mtime) | Road run 1 | not cited | 83.8 KB | `1f9d12dc15d65f4b51582c580397f607de96c292c00a35d6e712ee6f7e7c4d74` | yes |
| `Report/figures/road1/vid_front_sensor.jpg` | 2026-10-22 (mtime) | Road run 1 | appendixi: fig:road1-front | 124.6 KB | `e7b04b943ccafacb4434f3cb7be0ef2db6d2c6dc5a38a902451d56fdfc6c09e6` | yes |
| `Report/figures/road1/vid_front_sensor_crop.jpg` | 2026-10-22 (mtime) | Road run 1 | appendixi: fig:road1-front | 67.1 KB | `f69cdb0a7a28149f24f0b338c9eb1cf847c6aa33c235ef1c86f419d2f93ec6a6` | yes |

### Lab notebook

| Path | Date | Test | Supports | Size | SHA-256 | In git |
|---|---|---|---|---|---|---|
| `Planning/lab-notebook.md` | 2026-10-22 (mtime) | Lab notebook | Method: sec:data-analysis; Method: sec:data-collection; Method: tab:phases; appendixc: tab:evidence-index (row: 19 Oct 2026, Whole system mounted on the vehicle, lab check); appendixc: tab:evidence-index (row: 21 Oct 2026, Telemetry unit on its own battery, wired UART to the Raspber); appendixe: fig:timeline | 23.3 KB | `47c9769e599087e3709f4cda6c1b9acd76380b328647b24645c37066514787d4` | yes |

### Not assigned to a test

| Path | Date | Test | Supports | Size | SHA-256 | In git |
|---|---|---|---|---|---|---|
| `BenchTest/TEST_PROCEDURES.md` | 2026-10-15 (mtime) | - | Introduction: sec:requirements-mapping; Introduction: tab:terms (row: T, C, B tests, Test identifiers in); Method: sec:experiments; Method: tab:phases; appendixc: tab:evidence-index (row: 11 Oct 2026, Pothole path in the detector (C10)); appendixc: tab:evidence-index (row: 2 Oct 2026, Firmware v0.7.0 DASH line on the bench (40 s) and through th); appendixc: tab:evidence-index (row: 6 Oct 2026, First fused camera and time-of-flight hazard, live, before c); appendixd: app:wiring | 45.3 KB | `6af032a9dcb5fb4ed42192cebf8d4ae157c746628dc11cb584232b17c18f9074` | yes |
| `BenchTest/logs/2026-10-17_183719_roadtest.jsonl` | 2026-10-17 | - | not cited | 91.0 MB | `14b41ba46e27ca41178b95394add9cd11bad5745a9f7d363d89c0bc62b14bdc6` | no |
| `BenchTest/logs/road_logger_console.txt` | 2026-10-18 (mtime) | - | not cited | 347.9 KB | `5ab459ac939ef6a22003e53d3ed7d4babff3030b2b4f56959283c19b46f62989` | no |
| `BenchTest/logs/roadtest_markers.txt` | 2026-10-17 (mtime) | - | not cited | 45 B | `b7dde487a2ad56e0d143af2bdbbeb5e6760fbeaafad2e8f408c00c212fccbdef` | no |
| `CameraDetection/detect.tflite` | 2026-09-16 (mtime) | - | Results: fig:res-latency | 4.0 MB | `e4b118e5e4531945de2e659742c7c590f7536f8d0ed26d135abcfe83b4779d13` | yes |
| `CameraDetection/fusion_config_asbuilt.json` | 2026-10-15 (mtime) | - | not cited | 978 B | `dd568b5c71a42435da15c85e1259b3beb161b52dc2f8816b496f8ea91994f363` | yes |
| `CameraDetection/t.jsonl` | 2026-10-15 (mtime) | - | not cited | 3.4 KB | `343656a9f615913cf3a83d7a8c05414eba03f209b7630258be86ac593db090ff` | yes (modified) |
| `CameraDetection/t3.jsonl` | 2026-10-15 (mtime) | - | not cited | 4.3 KB | `fb743927bd0f4384ed79e78cc0228a2adbe4f7ef79e6f91e8c6d972d40dd1285` | yes (modified) |
| `CameraDetection/test_alerts.jsonl` | 2026-10-15 (mtime) | - | not cited | 4.7 KB | `705b60ceb0baa74b40b1d69a4ea59a6ad1982b57ffb83291429a331f7a3aacfa` | yes (modified) |
| `CameraDetection/tests/data/ATTRIBUTION.txt` | 2026-10-11 (mtime) | - | not cited | 468 B | `ba442559cfc8d98e30fe646911677ce19bc5a3030964217e4067fddac16e4e9d` | yes |
| `CameraDetection/tests/data/pothole_slievebane_road.jpg` | 2026-10-11 (mtime) | - | not cited | 63.1 KB | `e57dc8adf3cd8023e7340b0818b2d07a3ab2d18d40d675a3158c493967640713` | yes |
| `CameraDetection/timing.csv` | 2026-10-15 (mtime) | - | not cited | 10.5 KB | `00a5205b270f1457166ed9f83ba09166b2f208d9bad89cd859de89c41a174a9e` | yes (modified) |
| `DashboardIntegration/tests/hazard_banner.png` | 2026-10-06 (mtime) | - | appendixc: tab:evidence-index (row: 6 Oct 2026, Sensors page and hazard banner, whole dashboard offscreen ag) | 127.0 KB | `ff63690da6240d730140ee00857282fe8cca7850c32cbe52466cdf8f486df759` | yes |
| `DashboardIntegration/tests/sensors_page.png` | 2026-10-06 (mtime) | - | appendixc: tab:evidence-index (row: 6 Oct 2026, Sensors page and hazard banner, whole dashboard offscreen ag) | 80.1 KB | `080aa0e885ab15a7a7f69cb3e5a4126f0424fed65065c936fd79d4ceda633e39` | yes |
| `Report/evidence/README.md` | 2026-09-28 (mtime) | - | not cited | 2.0 KB | `ae5181dfafcc68ade538861eec30268be35a7a240ac4825185dc5de8deaf47ba` | yes |
| `Report/evidence/ethics_approval_EBE-03305-2026.pdf` | 2026-10-21 (mtime) | - | appendixh: app:ethics | 73.7 KB | `38f1809715c73b36d35c5358fb901e24c085967d700ac0be894584c17e7ed3b7` | yes |
| `Report/figures/results/README_snippets.tex` | 2026-10-21 (mtime) | - | not cited | 6.6 KB | `08fc58b902947b8a9308d8872ca4ddd5656353bf66cd5dac3e8ebb3d69eba4d8` | yes |
| `Report/figures/results/make_results_plots.py` | 2026-10-21 (mtime) | - | draws Results: fig:res-imu-gaps; draws Results: fig:res-latency; draws Results: fig:res-road; draws Results: fig:res-t15 | 14.8 KB | `e68ed900fa7f04dff45fcb21a80eb5b3630f1622ff1b4a6951dda2ab778208df` | yes |
| `Research/gap_ledger.json` | 2026-09-19 (mtime) | - | Literature: sec:lit-synthesis | 9.4 KB | `09b94ef033e35667e10ff66a8688ad99ca6c70b4204bb449044907f808b00bb5` | yes |
| `Research/research.db` | 2026-09-19 (mtime) | - | Literature: sec:lit-scope | 1.7 MB | `ebf0d617cf24ebe0611d144cd56e543935c2945f48255042fbe7c956724a9870` | yes |

## References in the report that resolve to no file

Paths that should exist in the repository: none missing.

Bare file names not found in the repository (files on a device, in the toolchain, or kept out of git on purpose; not data, listed for completeness):

- `cmdline.txt` (appendixe.tex, sec:diagnoses)
- `default_16MB.csv` (appendixe.tex, tab:config (row: Partition table, ))

## Data on disk cited by nothing in the report

These files sit in the data folders but no figure, table or section names them (a mention of a whole broad folder such as `BenchTest/logs/` does not count). Either cite them, or note them as supporting material only.

- `BenchTest/logs/2026-09-29_gnss_rooftop_v051.log` (178.2 KB, in git: yes) (folder mentioned only in general)
- `BenchTest/logs/2026-09-30_bms_vehicle_v054.log` (113.0 KB, in git: yes) (folder mentioned only in general)
- `BenchTest/logs/2026-09-30_bms_vehicle_v054_try2.log` (67.7 KB, in git: yes) (folder mentioned only in general)
- `BenchTest/logs/2026-10-01_tof_cover_test.csv` (22.7 KB, in git: yes) (folder mentioned only in general)
- `BenchTest/logs/2026-10-01_tof_hand_test.csv` (35.0 KB, in git: yes) (folder mentioned only in general)
- `BenchTest/logs/2026-10-11_t15_device_log.clean.jsonl` (697.9 KB, in git: no) (folder mentioned only in general)
- `BenchTest/logs/2026-10-11_t15_device_log.jsonl` (697.9 KB, in git: yes) (folder mentioned only in general)
- `BenchTest/logs/2026-10-17_183719_roadtest.jsonl` (91.0 MB, in git: no) (folder mentioned only in general)
- `BenchTest/logs/calibration/20261019_120755_front_trike_10ft.jpg` (26.4 KB, in git: yes) (folder mentioned only in general)
- `BenchTest/logs/calibration/20261019_124143_person_2m.jpg` (51.0 KB, in git: yes) (folder mentioned only in general)
- `BenchTest/logs/calibration/20261019_124143_person_2m_detections.json` (697 B, in git: yes) (folder mentioned only in general)
- `BenchTest/logs/calibration/20261019_124331_person_3m.jpg` (56.4 KB, in git: yes) (folder mentioned only in general)
- `BenchTest/logs/calibration/20261019_124331_person_3m_detections.json` (1.2 KB, in git: yes) (folder mentioned only in general)
- `BenchTest/logs/calibration/20261019_markers_1m_2m_3m.jpg` (47.6 KB, in git: yes) (folder mentioned only in general)
- `BenchTest/logs/calibration/rejected/20261019_123951_person_2m.jpg` (29.4 KB, in git: no) (folder mentioned only in general)
- `BenchTest/logs/calibration/rejected/20261019_123951_person_2m_detections.json` (699 B, in git: no) (folder mentioned only in general)
- `BenchTest/logs/focal_cal.csv` (341 B, in git: yes) (folder mentioned only in general)
- `BenchTest/logs/road_logger_console.txt` (347.9 KB, in git: no) (folder mentioned only in general)
- `BenchTest/logs/roadtest_markers.txt` (45 B, in git: no) (folder mentioned only in general)
- `CameraDetection/fusion_config.json` (754 B, in git: yes)
- `CameraDetection/fusion_config_asbuilt.json` (978 B, in git: yes)
- `CameraDetection/t.jsonl` (3.4 KB, in git: yes (modified))
- `CameraDetection/t3.jsonl` (4.3 KB, in git: yes (modified))
- `CameraDetection/test_alerts.jsonl` (4.7 KB, in git: yes (modified))
- `CameraDetection/tests/data/ATTRIBUTION.txt` (468 B, in git: yes) (folder mentioned only in general)
- `CameraDetection/tests/data/pothole_slievebane_road.jpg` (63.1 KB, in git: yes) (folder mentioned only in general)
- `CameraDetection/timing.csv` (10.5 KB, in git: yes (modified))
- `CameraDetection/training/runs/colab_session_2026-10-02.ipynb` (958.8 KB, in git: yes)
- `CameraDetection/training/runs/colab_session_2026-10-06.ipynb` (31.7 KB, in git: yes)
- `CameraDetection/training/runs/run2_sa_band_tiles_640/BoxPR_curve.png` (87.9 KB, in git: yes) (same dataset folder as cited `training_record.json`)
- `CameraDetection/training/runs/run2_sa_band_tiles_640/README.md` (1.8 KB, in git: yes) (same dataset folder as cited `training_record.json`)
- `CameraDetection/training/runs/run2_sa_band_tiles_640/best.pt` (5.2 MB, in git: yes) (same dataset folder as cited `training_record.json`)
- `CameraDetection/training/runs/run2_sa_band_tiles_640/confusion_matrix.png` (104.3 KB, in git: yes) (same dataset folder as cited `training_record.json`)
- `CameraDetection/training/runs/run2_sa_band_tiles_640/results.csv` (7.0 KB, in git: yes) (same dataset folder as cited `training_record.json`)
- `CameraDetection/training/runs/run2_sa_band_tiles_640/results.png` (280.0 KB, in git: yes) (same dataset folder as cited `training_record.json`)
- `CameraDetection/training/runs/run2_sa_band_tiles_640/yolo11n_sa_band_tiles_320_ncnn_model/metadata.yaml` (403 B, in git: yes)
- `CameraDetection/training/runs/run2_sa_band_tiles_640/yolo11n_sa_band_tiles_320_ncnn_model/model.ncnn.bin` (9.9 MB, in git: yes)
- `CameraDetection/training/runs/run2_sa_band_tiles_640/yolo11n_sa_band_tiles_320_ncnn_model/model.ncnn.param` (22.2 KB, in git: yes)
- `CameraDetection/training/runs/run2_sa_band_tiles_640/yolo11n_sa_band_tiles_320_ncnn_model/model_ncnn.py` (809 B, in git: yes)
- `CameraDetection/training/runs/run2_sa_band_tiles_640/yolo11n_sa_band_tiles_640_ncnn_model/metadata.yaml` (403 B, in git: yes)
- `CameraDetection/training/runs/run2_sa_band_tiles_640/yolo11n_sa_band_tiles_640_ncnn_model/model.ncnn.bin` (9.9 MB, in git: yes)
- `CameraDetection/training/runs/run2_sa_band_tiles_640/yolo11n_sa_band_tiles_640_ncnn_model/model.ncnn.param` (22.2 KB, in git: yes)
- `CameraDetection/training/runs/run2_sa_band_tiles_640/yolo11n_sa_band_tiles_640_ncnn_model/model_ncnn.py` (809 B, in git: yes)
- `Report/evidence/README.md` (2.0 KB, in git: yes) (folder mentioned only in general)
- `Report/figures/results/README_snippets.tex` (6.6 KB, in git: yes) (same dataset folder as cited `detector_latency.pdf`)
- `Report/figures/road1/vid_dash_mount.jpg` (83.8 KB, in git: yes) (same dataset folder as cited `chassis_rear.jpg`)

## Held by the author, available on request

Video and pictures that show people, kept off GitHub and out of the release archive.

- `../Roadtest1/WhatsApp Image 2026-10-21 at 21.07.19 (1).jpeg` (129.5 KB, SHA-256 `ae8e13f59cdad57eaf6fc66d12b58556187a8ae2ca839f68367663394b45f104`)
- `../Roadtest1/WhatsApp Image 2026-10-21 at 21.07.19 (2).jpeg` (190.3 KB, SHA-256 `96c874f5e4439a963650516a7923452a05575731b23bccb6a5eda62ba9b4c818`)
- `../Roadtest1/WhatsApp Image 2026-10-21 at 21.07.19.jpeg` (193.7 KB, SHA-256 `405ec53f619ec40df5d572da7134fb079a2c27530a401e4c6907143b7fb9d970`)
- `../Roadtest1/WhatsApp Image 2026-10-21 at 21.07.45.jpeg` (102.9 KB, SHA-256 `cc227da1e8853069af6811dce2cb9184b2a2aa398ef0e12394aa7d8d169793ae`)
- `../Roadtest1/WhatsApp Image 2026-10-21 at 21.07.53.jpeg` (124.2 KB, SHA-256 `2dd98a511b230c00493fc899da3e5a906c3b8404167215acd27ecd5972f53575`)
- `../Roadtest1/WhatsApp Image 2026-10-21 at 21.08.19 (1).jpeg` (188.5 KB, SHA-256 `ac84906cf5d71e5e82de29b5a975e67474c0295a056d16f98092066adf2b08c5`)
- `../Roadtest1/WhatsApp Image 2026-10-21 at 21.08.19 (2).jpeg` (222.4 KB, SHA-256 `cd8885799f7c9a389fc50efe7d2d7f39ff41ab29228a82d6c4850822fc9e452c`)
- `../Roadtest1/WhatsApp Image 2026-10-21 at 21.08.19.jpeg` (156.2 KB, SHA-256 `1ea1822a5dad17dcffb7d517f1472052e6f63482f36fc8e98410ef316889d885`)
- `../Roadtest1/WhatsApp Image 2026-10-21 at 21.08.20 (1).jpeg` (254.4 KB, SHA-256 `7f31c8b79ecac30ee2a46c22454bd42941c74428e5bb62bd9b9717386b94151e`)
- `../Roadtest1/WhatsApp Image 2026-10-21 at 21.08.20 (2).jpeg` (309.7 KB, SHA-256 `2f8818b67ba7f33dadf9272ab4a9d2abd642901f5911e6e04ad1f5d164864d1b`)
- `../Roadtest1/WhatsApp Image 2026-10-21 at 21.08.20.jpeg` (175.5 KB, SHA-256 `1ce30ddcb9f5083724a12d8226ab6a39e268b0c31a5c580ac42227f61af57497`)
- `../Roadtest1/WhatsApp Image 2026-10-21 at 21.08.21.jpeg` (1.4 MB, SHA-256 `5bea80952709127cbf3f12f99fb2def2c183fc9c68859f0b04b99ab1e927a557`)
- `../Roadtest1/WhatsApp Video 2026-10-21 at 21.07.44.mp4` (9.5 MB, SHA-256 `4e0b7e3f4859145c276c4401a126f7ff6ade5b7f9a8ef878aff2593f58f722ab`)
- `../Roadtest1/WhatsApp Video 2026-10-21 at 21.07.53.mp4` (3.9 MB, SHA-256 `4eefb7848f51adc731307bbce6c35cb659f5efd2f223cae56c5f9f9e020d9c94`)
- `../Roadtest1/WhatsApp Video 2026-10-21 at 21.08.18.mp4` (1.7 MB, SHA-256 `f66d7f2f53c223cb42777219c10b709d332e66703a64b349d3b1ecb5546b2d63`)
- `../Roadtest1/WhatsApp Video 2026-10-21 at 21.08.19.mp4` (3.2 MB, SHA-256 `df4496a0d276c7e941935faeecf4e5691d0d6dabef6530fa40c0320d4c64c46f`)
- `../Roadtest1/WhatsApp Video 2026-10-21 at 21.08.20.mp4` (9.1 MB, SHA-256 `c1e7c021f2adc307a005d8df959ce739acacfe36ca34a7419ebe4f0ea0b458d6`)
- `../Roadtest1/edit/TUKZIE_roadtest1_reel.mp4` (73.8 MB, SHA-256 `5fce3e8092a114cc61657d2a9256fdfd9811b1b87875f57fefd7659509a82e2c`)
- `BenchTest/logs/calibration/rejected/20261019_123951_person_2m.jpg` (29.4 KB, SHA-256 `51a9ed11fe9527d237bd4873dbb41d83d287416fdab23c67b7524e1ac8660bdd`)

Pictures named as showing a person that are already in the public repository (confirm each shows only the author or a team member who agreed, or remove from git):

- `BenchTest/logs/calibration/20261019_124143_person_2m.jpg`
- `BenchTest/logs/calibration/20261019_124331_person_3m.jpg`
- `Report/evidence/2026-10-01_dashboard_page_person.png`

Server database: the central store (`sw7_telemetry.db`, SQLite) lives on the Raspberry Pi 5 (`~/sw7_server/`) and is not copied to the laptop; the T15 results were exported from it as the CSV files in `BenchTest/logs/2026-10-11_t15/` with `Server/sync_report.py`.
