# Builds train_pothole_yolo11n.ipynb (run: python make_notebook.py). Edit the cells here, not the .ipynb.
import json

def md(t): return {"cell_type": "markdown", "metadata": {}, "source": t.strip("\n").splitlines(True)}
def code(t): return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": t.strip("\n").splitlines(True)}

cells = [
md("""
# SW-7: train a YOLO11n pothole detector for the Raspberry Pi

Trains YOLO11n on a public pothole dataset from Roboflow Universe, records the accuracy and settings for the report, and converts the result to NCNN for `CameraDetection/yolo_bench.py` on the Pi.

Before running:
1. Runtime > Change runtime type > **T4 GPU**.
2. Secrets (key icon on the left): add `ROBOFLOW_API_KEY` with your Roboflow key, and allow this notebook to use it. Do not type the key into a cell.
3. On the dataset's Universe page: Download Dataset > format **YOLOv11** > "show download code". Copy the workspace, project and version into cell 3.

No camera frames from the vehicle are used: only the public dataset.
"""),
code("""
# 1. GPU check
!nvidia-smi --query-gpu=name,memory.total --format=csv
"""),
code("""
# 2. Packages, and Google Drive so training survives a disconnect
!pip -q install ultralytics roboflow
from google.colab import drive
drive.mount('/content/drive')
import os
RUN_DIR = '/content/drive/MyDrive/SW7_training'
os.makedirs(RUN_DIR, exist_ok=True)
"""),
code("""
# 3. Dataset from Roboflow Universe (fill in from the dataset's download code)
WORKSPACE = 'gerapothole'            # example: https://universe.roboflow.com/gerapothole/pothole-detection-yolov8
PROJECT   = 'pothole-detection-yolov8'
VERSION   = 1
DATASET_URL = f'https://universe.roboflow.com/{WORKSPACE}/{PROJECT}'

from google.colab import userdata
from roboflow import Roboflow
rf = Roboflow(api_key=userdata.get('ROBOFLOW_API_KEY'))
ds = rf.workspace(WORKSPACE).project(PROJECT).version(VERSION).download('yolov11', location='/content/dataset')
DATA_YAML = '/content/dataset/data.yaml'
print(open(DATA_YAML).read())
for split in ('train', 'valid', 'test'):
    d = f'/content/dataset/{split}/images'
    print(split, len(os.listdir(d)) if os.path.isdir(d) else 0, 'images')
print('Record the licence shown on', DATASET_URL, 'for the report.')
"""),
code("""
# 4. Train. Settings are recorded in cell 6. Re-running resumes from the last checkpoint on Drive.
from ultralytics import YOLO
EPOCHS, IMGSZ, BATCH, PATIENCE = 60, 640, 32, 15
NAME = f'yolo11n_pothole_{IMGSZ}'
last = f'{RUN_DIR}/{NAME}/weights/last.pt'
if os.path.exists(last):
    model = YOLO(last); model.train(resume=True)
else:
    model = YOLO('yolo11n.pt')      # COCO-pretrained start (transfer learning)
    model.train(data=DATA_YAML, epochs=EPOCHS, imgsz=IMGSZ, batch=BATCH, patience=PATIENCE,
                project=RUN_DIR, name=NAME, exist_ok=True, seed=0)
"""),
code("""
# 5. Accuracy on the held-out test split, at the training size and at 320 (the faster Pi setting)
best = f'{RUN_DIR}/{NAME}/weights/best.pt'
model = YOLO(best)
split = 'test' if os.path.isdir('/content/dataset/test/images') else 'val'
results = {}
for sz in (IMGSZ, 320):
    m = model.val(data=DATA_YAML, split=split, imgsz=sz, batch=16, plots=(sz == IMGSZ),
                  project=RUN_DIR, name=f'{NAME}_val{sz}', exist_ok=True)
    results[sz] = {'mAP50': round(float(m.box.map50), 3), 'mAP50_95': round(float(m.box.map), 3),
                   'precision': round(float(m.box.mp), 3), 'recall': round(float(m.box.mr), 3)}
    print(sz, results[sz])
"""),
code("""
# 6. Record settings and results for the report
import json, ultralytics, torch, datetime
record = {'date': datetime.date.today().isoformat(), 'dataset': DATASET_URL, 'version': VERSION,
          'model': 'yolo11n.pt (COCO-pretrained)', 'epochs_max': EPOCHS, 'imgsz': IMGSZ, 'batch': BATCH,
          'patience': PATIENCE, 'seed': 0, 'eval_split': split, 'results': results,
          'ultralytics': ultralytics.__version__, 'torch': torch.__version__,
          'gpu': torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu'}
json.dump(record, open(f'{RUN_DIR}/{NAME}/training_record.json', 'w'), indent=2)
print(json.dumps(record, indent=2))
"""),
code("""
# 7. Convert to NCNN for the Pi (same format as the benchmark) and download one zip
import shutil
out = f'/content/{NAME}_pi'
os.makedirs(out, exist_ok=True)
for sz in (320, IMGSZ):
    p = YOLO(best).export(format='ncnn', imgsz=sz)
    shutil.move(p, f'{out}/yolo11n_pothole_{sz}_ncnn_model')
for f in ('training_record.json', 'results.csv', 'results.png', 'weights/best.pt'):
    src = f'{RUN_DIR}/{NAME}/{f}'
    if os.path.exists(src): shutil.copy(src, out)
for f in ('confusion_matrix.png', 'PR_curve.png', 'BoxPR_curve.png'):
    src = f'{RUN_DIR}/{NAME}_val{IMGSZ}/{f}'
    if os.path.exists(src): shutil.copy(src, out)
shutil.make_archive(out, 'zip', out)
from google.colab import files
files.download(out + '.zip')
"""),
md("""
After downloading: unzip into `CameraDetection/training/`, then copy the `*_ncnn_model` folders to `~/yolo_bench` on the Pi and run
`venv/bin/python yolo_bench.py --model yolo11n_pothole_320_ncnn_model --imgsz 320 --duration 60 --tuning ov5647_noir.json --saturation 1.8`.
"""),
]
nb = {"cells": cells, "metadata": {"accelerator": "GPU", "colab": {"provenance": []},
      "kernelspec": {"name": "python3", "display_name": "Python 3"}}, "nbformat": 4, "nbformat_minor": 0}
json.dump(nb, open("train_pothole_yolo11n.ipynb", "w"), indent=1)
print("wrote train_pothole_yolo11n.ipynb")
