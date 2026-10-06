# Run 2: YOLO11n on South African road-band tiles (6 Oct 2026)

Notebook: `../../train_pothole_yolo11n.ipynb`, cells 2g (band tiles) and 4b (training), Colab T4, 60 epochs.
Data: Nienaber, Kroon and Booysen, Stellenbosch University (Kaggle `sovitrath/road-pothole-images-for-pothole-detection`),
each frame cropped to 42 to 68 % of its height and cut into three 1280-pixel tiles (cell 2g).

| Input | mAP@50 | mAP@50-95 | Precision | Recall |
|---|---|---|---|---|
| 640 | 0.714 | 0.349 | 0.811 | 0.623 |
| 320 | 0.566 | 0.246 | 0.688 | 0.510 |

Read with care:
- Scored on the **validation** tiles (`eval_split: val` in `training_record.json`), which training used to pick the
  best epoch (54 of 60), so the figures are optimistic. Cell 5 looked for a Roboflow-style test folder and fell back
  to validation. Fixed on 6 Oct; cell 5b scores this run on the held-out test tiles.
- Per tile, not per full frame.
- `training_record.json` says "yolo11n.pt (COCO-pretrained)" because cell 6 used to write that text whatever the
  start; cell 4b starts from run 1's weights when they are on Drive. Cell 5b prints the real start from `args.yaml`.
- Not yet run on the Raspberry Pi or on the vehicle's camera.

Files: `best.pt`, NCNN models for the Pi at 320 and 640, `results.csv` and `results.png` (training curves),
`confusion_matrix.png`, `BoxPR_curve.png`, `training_record.json`.
