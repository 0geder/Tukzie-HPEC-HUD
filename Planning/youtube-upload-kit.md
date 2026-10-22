# YouTube upload kit: video evidence for the report (22 Oct 2026)

Prof. Winberg agreed that video evidence should be included. The report carries it as a table with a link and a QR code per video (Appendix I, section "Video evidence"), which appears automatically once `Report/video_links.tex` exists. Nothing appears until then, so the report never shows a placeholder.

## Before uploading

1. Consent: the clips show team members (Yusuf driving, helpers) and their faces. Ask each person shown, or blur them. YouTube Studio's editor has a face-blur tool (Content > video > Editor > Blur > Face blur) and a custom blur for the number plate.
2. Visibility: Unlisted (not Public, not Private). Unlisted videos open for anyone with the link and are not searchable. Private would block the examiners.
3. Audience: "No, it's not made for kids".
4. Music: none in the files. If added, use YouTube's Audio Library only, so there is no copyright claim.

## Playlist

Title: `SW-7 TUKZIE telemetry: video evidence (UCT EEE4022S 2026)`, unlisted, videos in the order below.

## Videos

| # | File | Title | Description | Report section |
|---|---|---|---|---|
| 1 | `Roadtest1/edit/TUKZIE_roadtest1_reel.mp4` (91 s) | `TUKZIE road test day 1: from the lab to the test` | First vehicle session, 19 Oct 2026: the TUKZIE Rev 0 is taken out of the building and into the test venue, the system on board (rear sensor pod, IMU pods, wiring, live dashboard, front sensors), and the trike ridden in the venue. Project SW-7, UCT EEE4022S, supervisor A/Prof. S. Winberg. Chapters (YouTube needs each at least 10 s): 0:00 out of the building, 0:33 into Lecture Theatre 13, 0:45 the system on board, 1:07 the RC car and the TUKZIE's run. | Appendix I; vehicle tests |
| 2 | `WhatsApp Video 2026-10-21 at 21.08.20.mp4` (43 s) | `TUKZIE system walk-round: wiring, dashboard, front sensors` | Uncut walk-round of the mounted system on 19 Oct 2026: power at the bed, the dashboard's DRIVE page on the handlebar display, the front sensor board on its mount. | Appendix I, Figures I.3 and I.4 |
| 3 | `WhatsApp Video 2026-10-21 at 21.08.18.mp4` (8 s) | `TUKZIE rear frame with the units mounted` | The rear sensor pod and other units on the board over the rear frame. | Appendix I, Figure I.2 |
| 4 | `WhatsApp Video 2026-10-21 at 21.08.19.mp4` (16 s) | `TUKZIE ridden in the test venue` | The vehicle ridden slowly in the lecture venue, 19 Oct 2026. | Vehicle tests |

Run 2 videos are added the same way after the session (the phone video used as ground truth for alerts and potholes, and the reel).

## After uploading

Send the links in this form and they go straight into the report:

```
1 https://youtu.be/...
2 https://youtu.be/...
```

Each becomes a line of `Report/video_links.tex`:

```
\videoentry{Road test day 1 (reel)}{From the lab to the test, the system on board and the run}{Appendix~\ref{app:road1}}{https://youtu.be/...}
```
