# Data availability: draft statement and how the index works

Written 22 Oct 2026 (workstream B of `Planning/run2-readiness-prompt.md`). Draft for the student to check; nothing here is in the report yet.

## What exists now

- `DATA_INDEX.md` (repository root): one row per data file behind the report, grouped by test (T1 to T15, C1 to C11, B1 to B5, power, pothole model, road run 1, lab notebook). Each row gives the path, date, test ID, where the report cites it (figure, table or section label, and for Appendix C the evidence-table row), size, SHA-256 and whether git tracks it. It also lists report references that resolve to no file, data cited by nothing, and the files held back for privacy.
- `tools/build_data_index.py`: rebuilds the index (`python tools/build_data_index.py`, about 5 s, standard library only). With `--pack` it also writes `../SW7_data_release/SW7_data_release_<date>.zip` (outside the repository) holding every file the report depends on that git does not track, plus `DATA_INDEX.md`, `SHA256SUMS.txt`, `WITHHELD.txt` and `README.txt`, and a `.zip.sha256` beside it. `--include-uncited` adds untracked data the report does not cite (at present the 17 Oct trial recording, 91 MB).
- First archive, built 22 Oct 2026: `SW7_data_release_2026-10-22.zip`, 7 files (the 19 Oct road session: three recorder files, front and rear alert logs, Pi 5 power watch, markers), 29.9 MB uncompressed, 1.3 MB zipped. Checksums verified inside the zip.

Rebuild the index and the archive after run 2 and before submission, then commit `DATA_INDEX.md`, so the hashes in the report's repository match the archive.

## Where to store the archive (student to choose)

| Option | For | Against |
|---|---|---|
| Zenodo (zenodo.org), upload the dated zip, licence CC BY 4.0, can be linked to the GitHub repository | Permanent DOI that can be cited in the reference list; free; survives the end of the UCT account | Public once published (a restricted or embargoed record is possible); the run-2 GNSS track would be public, so trim the start and end near home or campus parking first |
| UCT OneDrive, folder shared with "people with the link" (or UCT only) | Already where the data lives; quick; access can be limited to examiners | Link breaks when the student account closes after graduation; no DOI |

A workable path: OneDrive link now for the examiners, Zenodo DOI before the final submission. The LaTeX below has a slot for either.

## What is withheld

Video and pictures that show people: the five road-test videos, the twelve road-test photos and the reel (`../Roadtest1/`, 105 MB) and the rejected calibration still with a person. They are listed with their SHA-256 in `DATA_INDEX.md` and `WITHHELD.txt` as held by the author and available on request. The published versions are the blurred stills in Appendix I and, once uploaded, the unlisted YouTube videos in the video-evidence section of Appendix I.

Already public in the GitHub repository and showing a person (check each shows only the author or a team member who agreed, or remove them from git): `BenchTest/logs/calibration/20261019_124143_person_2m.jpg`, `BenchTest/logs/calibration/20261019_124331_person_3m.jpg`, `Report/evidence/2026-10-01_dashboard_page_person.png`.

## LaTeX to paste

Where: a new last section of Appendix C (`Report/appendixc.tex`), after the evidence table and the two verbatim blocks, so the statement sits next to the evidence index. Then one sentence at the end of the first paragraph of the Data collection section in `Report/Method.tex` pointing to it (given below). If the department prefers a statement in the main body, the same text works as an unnumbered section after the Conclusions (`\section*{Data availability}` plus `\addcontentsline{toc}{section}{Data availability}`).

Pick one of the two archive sentences and delete the other. Fill the DOI or link only once it exists; do not leave the brackets in.

```latex
\section{Data availability}
\label{sec:data-availability}

The source code, firmware, test scripts, bench logs and the figures' data are in the project repository at \url{https://github.com/0geder/Tukzie-HPEC-HUD}. The file \texttt{DATA\_INDEX.md} at the top of the repository lists every data file behind a number, figure or table in this report, with its date, test identifier, the part of the report it supports, its size and its SHA-256 checksum, and states whether the file is in the repository. The index is rebuilt by \texttt{tools/build\_data\_index.py}.

The road-session recordings and alert logs are too large for the repository and are kept in a dated archive, \texttt{SW7\_data\_release\_2026-10-22.zip}, which holds the files at their repository paths together with the index and a list of checksums. % choose one:
The archive is published on Zenodo at \url{https://doi.org/10.5281/zenodo.XXXXXXX}.
% The archive is available from the author's UCT OneDrive at \url{LINK}.
A copy can be checked against the index by computing the SHA-256 of each file (\texttt{sha256sum -c SHA256SUMS.txt} inside the archive).

Photographs and video that show people other than the author are not published, in line with Section~\ref{sec:ethics}. The originals are held by the author and are available on request; the index lists them with their checksums. The report uses only stills in which faces and the number plate are cropped or blurred (Appendix~\ref{app:road1}), and the videos are linked in Section~\ref{sec:video-evidence} with the same treatment.
```

Sentence for `Report/Method.tex`, end of the first paragraph of the Data collection section:

```latex
Where each record is kept, and how to check a copy of it, is given in Appendix~\ref{app:evidence}, Section~\ref{sec:data-availability}.
```

Notes before pasting:
- `\ref{sec:video-evidence}` exists only when `Report/video_links.tex` exists (workstream E). Until the links are in, drop the last clause ("and the videos are linked ...").
- `\url` needs `hyperref`, which the template already loads.
- If the archive is rebuilt after run 2, change the file name in the second paragraph to the new date.

## Findings from the first index run (22 Oct 2026)

- 182 files indexed, 298.3 MB; 31 not in git (226.6 MB), of which the report depends on 25 (134.6 MB): the 7 road-session files (packed) and 18 private media files (withheld).
- Every path in the Appendix C evidence table resolves to a file on disk; the only unresolved references in the whole report are `cmdline.txt` and `default_16MB.csv` in Appendix E, which are device or toolchain files, not data.
- Evidence-table rows with no raw file behind them:
  - 2 Oct, first pothole model on the South African split: the file column says "Colab session notebook (to be saved)", but the notebook is saved as `CameraDetection/training/runs/colab_session_2026-10-02.ipynb` (in git). Replace the cell with that path.
  - 2 Oct DASH line (T11, T12), 6 Oct first fused hazard (C9), 11 Oct pothole path (C10): cite only `TEST_PROCEDURES.md` notes; no console log was kept.
  - 19 Oct lab check and 21 Oct battery and UART run: cite only `Planning/lab-notebook.md`; the 21 Oct console (2,489 lines) was not saved. Save the console of every run-2 bench check under `BenchTest/logs/`.
- Untracked data cited by nothing: `BenchTest/logs/2026-10-17_183719_roadtest.jsonl` (91 MB, recorder trial of 17 Oct), `road_logger_console.txt`, `roadtest_markers.txt` (17 Oct), `2026-10-11_t15_device_log.clean.jsonl`, and the rejected calibration still. Either cite the 17 Oct trial in Method (recorder shakedown) or leave it as supporting material.
- Tracked data cited by nothing in the report: the T15 device log (named only in `TEST_PROCEDURES.md`), the GNSS v0.5.1 and BMS v0.5.4 logs (T3, T7), the ToF hand and cover tests (C7), the calibration folder and `focal_cal.csv` (C5), the run-2 pothole model files beside the cited `training_record.json`, and four scratch files in `CameraDetection/` (`t.jsonl`, `t3.jsonl`, `test_alerts.jsonl`, `timing.csv`, all modified and uncommitted). The scratch files should be deleted or moved under `BenchTest/logs/` with a dated name.
- The central database (`sw7_telemetry.db`) lives only on the Raspberry Pi 5. The T15 numbers come from CSV exports in `BenchTest/logs/2026-10-11_t15/`, which are indexed. For run 2, export the database (`sqlite3 sw7_telemetry.db .dump` or `sync_report.py --csv`) into the dated log folder so the release archive holds it.
