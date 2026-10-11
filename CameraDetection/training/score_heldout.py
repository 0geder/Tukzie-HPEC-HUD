"""Score a trained YOLO pothole model on a held-out split, for the report.

Run 2 (training/runs/run2_sa_band_tiles_640) was only scored on its validation tiles, which
training used to pick the best epoch, so its 0.714 mAP@50 is optimistic. This scores best.pt
on the South African test tiles (cell 2g: the dataset's own "Test data" frames, 605 frames,
none used in training or validation) and writes the numbers to a JSON file next to the run.

It also checks that no test image name appears in the train or val lists, and prints which
weights training started from (args.yaml), since the run's record did not state it.

In Colab (T4 or CPU; scoring takes a few minutes):
  1. Run notebook cells 1 (GPU), 2 (packages, Drive), 2b (Kaggle download), 2d (convert labels)
     and 2g (band tiles). Do not run 4b (training). This rebuilds /content/sa_band_tiles with
     the same seed, so train/val/test are the same split as training used.
  2. Copy this file to Colab (Files pane, or from Drive) and run:
       !python score_heldout.py \
           --weights /content/drive/MyDrive/SW7_training/yolo11n_sa_band_tiles_640/weights/best.pt \
           --data /content/sa_band_tiles/data.yaml --split test \
           --out /content/drive/MyDrive/SW7_training/run2_test_scores.json
  3. Copy run2_test_scores.json into training/runs/run2_sa_band_tiles_640/ and update its README
     and the report with the test figures (per tile, at 640 and 320).

Any folder of images with YOLO labels can be scored the same way without a data.yaml:
  python score_heldout.py --weights best.pt --images /path/to/test/images --names Potholes

Needs ultralytics (pip install ultralytics). Nothing is invented here: if the split is missing
the script stops rather than falling back to validation.
"""
import argparse
import datetime
import glob
import json
import os
import sys
import tempfile


def image_stems(folder):
    exts = (".jpg", ".jpeg", ".png", ".bmp")
    return {os.path.splitext(os.path.basename(f))[0] for f in glob.glob(os.path.join(folder, "*"))
            if f.lower().endswith(exts)}


def split_dir(data, split):
    import yaml
    d = yaml.safe_load(open(data))
    rel = d.get(split)
    if not rel:
        return None
    base = d.get("path") or os.path.dirname(os.path.abspath(data))
    return rel if os.path.isabs(rel) else os.path.join(base, rel)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--weights", required=True, help="best.pt of the run")
    ap.add_argument("--data", help="data.yaml with a held-out split (e.g. /content/sa_band_tiles/data.yaml)")
    ap.add_argument("--split", default="test", help="split to score (default test; never val for a held-out score)")
    ap.add_argument("--images", help="instead of --data: a folder of held-out images, labels in ../labels")
    ap.add_argument("--names", default="Potholes", help="class names for --images, comma separated")
    ap.add_argument("--imgsz", default="640,320", help="input sizes to score (default 640,320)")
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--out", default=None, help="JSON file for the results")
    a = ap.parse_args()

    if a.split == "val":
        print("Refusing to report the validation split as held out; use --split test.")
        sys.exit(2)
    import yaml
    from ultralytics import YOLO

    if a.images:
        tmp = tempfile.mkdtemp()
        data = os.path.join(tmp, "data.yaml")
        names = a.names.split(",")
        yaml.safe_dump({"path": os.path.dirname(os.path.abspath(a.images)), "train": os.path.abspath(a.images),
                        "val": os.path.abspath(a.images), "test": os.path.abspath(a.images), "names": names},
                       open(data, "w"))
        split = "test"
    else:
        if not a.data:
            ap.error("give --data or --images")
        data, split = a.data, a.split

    test_dir = split_dir(data, split)
    if not test_dir or not os.path.isdir(test_dir):
        print(f"No '{split}' images at {test_dir}; nothing scored.")
        sys.exit(1)
    test = image_stems(test_dir)
    overlap = {}
    if not a.images:
        for other in ("train", "val"):
            d = split_dir(data, other)
            if d and os.path.isdir(d) and os.path.abspath(d) != os.path.abspath(test_dir):
                overlap[other] = len(test & image_stems(d))
    print(f"held-out images: {len(test)} in {test_dir}; names shared with train/val: {overlap or 'not checked'}")
    if any(overlap.values()):
        print("WARNING: test images also appear in train or val; the score would not be held out.")

    args_yaml = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(a.weights))), "args.yaml")
    started_from = None
    if os.path.exists(args_yaml):
        started_from = yaml.safe_load(open(args_yaml)).get("model")
        print("training started from:", started_from)

    model = YOLO(a.weights)
    results = {}
    for sz in (int(s) for s in a.imgsz.split(",")):
        r = model.val(data=data, split=split, imgsz=sz, batch=a.batch, plots=False, verbose=False)
        results[str(sz)] = {"mAP50": round(float(r.box.map50), 3), "mAP50_95": round(float(r.box.map), 3),
                            "precision": round(float(r.box.mp), 3), "recall": round(float(r.box.mr), 3)}
        print(f"{split.upper()} {sz}: {results[str(sz)]}")

    record = {"date": datetime.date.today().isoformat(), "weights": a.weights, "data": data, "split": split,
              "held_out_images": len(test), "shared_with_train_val": overlap, "started_from": started_from,
              "results": results, "note": "per tile (band tiles, cell 2g), not per full frame"}
    if a.out:
        json.dump(record, open(a.out, "w"), indent=2)
        print("written", a.out)


if __name__ == "__main__":
    main()
