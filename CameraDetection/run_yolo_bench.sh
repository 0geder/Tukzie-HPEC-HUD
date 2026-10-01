#!/usr/bin/env bash
# YOLO11n vs YOLO11n-seg on the Pi 4, at 320 and 640 input, 60 s each.
# Separate venv (~/yolo_bench/venv) so the working detector's venv is untouched.
# System site packages are included so picamera2 (installed with apt) is visible.
# Stop the detector first: the camera can only be opened by one process.
set -euo pipefail
cd ~/yolo_bench
if [ ! -d venv ]; then
  python3 -m venv --system-site-packages venv
  venv/bin/pip install --upgrade pip
  venv/bin/pip install ultralytics ncnn
fi
for m in yolo11n yolo11n-seg; do
  for s in 320 640; do
    [ -d "${m}_${s}_ncnn_model" ] && continue
    venv/bin/yolo export model="$m.pt" format=ncnn imgsz="$s"
    mv "${m}_ncnn_model" "${m}_${s}_ncnn_model"
  done
done
mkdir -p results
for m in yolo11n yolo11n-seg; do
  for s in 320 640; do
    venv/bin/python yolo_bench.py --model "${m}_${s}_ncnn_model" --imgsz "$s" --duration 60 \
      --tuning ov5647_noir.json --saturation 1.8 --out "results/${m}_${s}.csv" | tee "results/${m}_${s}.txt"
    sleep 20   # let the CPU cool between runs
  done
done
