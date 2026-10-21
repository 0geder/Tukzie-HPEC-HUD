# Prompt: road-test photographs and videos as a report appendix

Written 21 Oct 2026 for the first road session. Reuse it for later sessions by changing the folder and the date.

## Input

- Folder with the team's photos and videos: `Projects/Roadtest1/` (12 JPEG photos, 5 MP4 videos, shared on WhatsApp on 21 Oct 2026; taken around the session of 19 Oct).
- The report: `Tukzie-HPEC-HUD/Report/`, ethics section `sec:ethics` in `Method.tex`, vehicle tests `sec:field-test-design`.

## Rules

1. Privacy first (ethics approval EBE/03305/2026; the report says images kept show only the author). Look at every photo and at frames from every video before using them. Crop away or blur every face of anyone else and the vehicle's number plate. Do not put a video in the report if it shows faces; describe it in a table instead.
2. Describe only what is visible. If a unit in a photo cannot be identified for certain, describe it plainly (for example "a clear box with further electronics") instead of guessing.
3. Do not claim a photo was taken at a particular moment unless that is known. The files carry the date they were shared, not the date they were taken.
4. Keep the originals out of git (size and privacy); only the processed, privacy-checked copies go in `Report/figures/road1/`, at most 1400 px on the long side, JPEG quality about 85.
5. Plain captions: what the picture shows and why it matters for the report. No em dashes, no unnecessary bold.

## Steps

1. Make a contact sheet of the photos and of four frames from each video; note what each shows and where people or the plate appear.
2. Choose photos in three groups: the rear sensor pod (open and closed), the system on the vehicle, and the dashboard on the handlebar. Add video stills where they show something the photos do not.
3. Blur or crop, resize, save to `Report/figures/road1/`, and check the processed images again.
4. Write `Report/appendixi.tex`: a short introduction (source, date, where the originals are kept, the privacy treatment), one figure per group with subfigures and captions, and a table of the videos (file, length, what it shows). Include it after Appendix H in the main file and reference it from the vehicle tests section.
5. Build the report, render the appendix pages, and check them by eye.
