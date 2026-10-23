# Run 2, lab part (23 October 2026): data copied from the Pis

Copied on 23 Oct after the session (17:05 to 17:25), checked against the size on the Pi. File names carry the Pi's
clock at opening; files named 2026-10-22_1436xx were opened after a restart before the clock synced (their contents
are timestamped correctly once chrony synced, about 2 min after boot). Raw files and recorder logs are git-ignored
(about 400 MB); they stay here and on the Pis' SD cards. Dashboard screenshots (every 2 s) from 15:48 to 16:29 (1,198 files, both stand runs and the
recalibration) are in pi5_screens/ as nine 5-minute tar files (git-ignored); the rest of the day stays on the Pi 5
(~/roadtest/screens/2026-10-23).

Stand runs: 15:53:11 to 15:55:50 and from 16:08:49 (markers in pi5_roadtest/roadtest_markers.txt). Raw data for them:
rear pi4_rawlog/rear_raw_2026-10-23_151718.txt (15:17 to 16:17), front pi5_raw_front/front_raw_2026-10-22_143608.txt
(15:48 to 16:29); recorder pi5_roadtest/2026-10-22_143608_roadtest.jsonl. Recalibration 16:22: rear in
rear_raw_2026-10-23_161718.txt, front in front_raw_2026-10-22_143608.txt.

Note: pi5_roadtest/2026-10-22_143606_roadtest.jsonl here (copied 17:05) is 50 kB longer than the Pi's copy after the
17:07 power loss, so the laptop copy is the complete one.

| File | Bytes | Modified (laptop) | SHA-256 (first 16) |
|---|---|---|---|
| pi4_rawlog/rear_raw_2026-10-22_143656.txt | 24,030,676 | 17:21 | e88ec5f4b177b3e9 |
| pi4_rawlog/rear_raw_2026-10-23_111845.txt | 2,061,171 | 17:21 | 8aed06c6c1514f11 |
| pi4_rawlog/rear_raw_2026-10-23_112338.txt | 27,328,693 | 17:21 | 52a3bbeda601537b |
| pi4_rawlog/rear_raw_2026-10-23_122338.txt | 27,686,996 | 17:21 | 14ba6cde7a880cf0 |
| pi4_rawlog/rear_raw_2026-10-23_132338.txt | 24,215,552 | 17:21 | 79df731261fe2f9c |
| pi4_rawlog/rear_raw_2026-10-23_151718.txt | 27,638,546 | 17:19 | 41cfd75a48f19358 |
| pi4_rawlog/rear_raw_2026-10-23_161718.txt | 2,334,720 | 17:19 | 08a34ce4f719d793 |
| pi4_rawlog/rear_raw_2026-10-23_162312.txt | 4,900,907 | 17:21 | 09d08e358144aeaf |
| pi4_rawlog/rear_sync_2026-10-22_143648.csv | 39 | 17:19 | 0ee29603a55dfcaa |
| pi5_phone_gps/phone_gps_2026-10-22_143600.txt | 2,155,244 | 17:21 | b55702cb7debd92a |
| pi5_phone_gps/phone_gps_2026-10-23_153619.txt | 0 | 17:09 | e3b0c44298fc1c14 |
| pi5_raw_front/front_raw_2026-10-22_143604.txt | 4,602,649 | 17:20 | d7c8c50a894ce382 |
| pi5_raw_front/front_raw_2026-10-22_143605.txt | 1,056,076 | 17:21 | 01c10048cfb59405 |
| pi5_raw_front/front_raw_2026-10-22_143606_1.txt | 30,669,170 | 17:20 | 54b2d5d2a5abd6dd |
| pi5_raw_front/front_raw_2026-10-22_143606_2.txt | 2,611,215 | 17:20 | 0d7dae693a06ab71 |
| pi5_raw_front/front_raw_2026-10-22_143608.txt | 20,889,600 | 17:09 | 20609b395a1a16d8 |
| pi5_raw_front/front_raw_2026-10-23_113701.txt | 30,760,049 | 17:20 | 9fbcab2866e8fb24 |
| pi5_raw_front/front_raw_2026-10-23_123701.txt | 30,813,558 | 17:08 | a6d33d9cd91a490c |
| pi5_raw_front/front_raw_2026-10-23_133701.txt | 30,887,060 | 17:08 | 6b1f461061b639f0 |
| pi5_raw_front/front_raw_2026-10-23_143701.txt | 30,887,143 | 17:19 | ce242a870321ba82 |
| pi5_raw_front/front_raw_2026-10-23_153701.txt | 3,727,248 | 17:08 | 6053e925d1c7dafc |
| pi5_roadtest/2026-10-22_143604_roadtest.jsonl | 2,676,954 | 17:21 | 4d310b7849297811 |
| pi5_roadtest/2026-10-22_143605_roadtest.jsonl | 589,824 | 17:21 | 254a307ce1560005 |
| pi5_roadtest/2026-10-22_143606_roadtest.jsonl | 79,028,942 | 17:05 | 0678f41e86eebc73 |
| pi5_roadtest/2026-10-22_143608_roadtest.jsonl | 14,519,661 | 17:05 | cbea63d141b0ba57 |
| pi5_roadtest/roadtest_markers.txt | 467 | 17:05 | 240388598e79a4e6 |
