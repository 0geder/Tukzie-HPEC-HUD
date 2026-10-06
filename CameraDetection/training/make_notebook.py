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
# 2b. South African pothole dataset straight from Kaggle (Nienaber, Kroon and Booysen, Stellenbosch University,
#     SATC 2015; CC0 1.0). Needs a Colab secret: KAGGLE_API_TOKEN (kaggle.com > Settings > API Tokens >
#     Generate New Token), or the legacy pair KAGGLE_USERNAME and KAGGLE_KEY from kaggle.json.
#     This cell only downloads and shows the layout, so the label format can be checked before it is
#     converted or uploaded to Roboflow.
!pip -q install -U "kagglehub>=0.4.1"
import os, glob
from google.colab import userdata
def secret(name):
    try: return userdata.get(name)
    except Exception: return None
if secret('KAGGLE_API_TOKEN'):
    os.environ['KAGGLE_API_TOKEN'] = secret('KAGGLE_API_TOKEN')
elif secret('KAGGLE_USERNAME') and secret('KAGGLE_KEY'):
    os.environ['KAGGLE_USERNAME'] = secret('KAGGLE_USERNAME'); os.environ['KAGGLE_KEY'] = secret('KAGGLE_KEY')
else:
    print('No Kaggle secret found; trying without (works for some public datasets).')
import kagglehub
SA_DIR = kagglehub.dataset_download('sovitrath/road-pothole-images-for-pothole-detection')
print('downloaded to', SA_DIR)
for root, dirs, files in os.walk(SA_DIR):
    depth = root[len(SA_DIR):].count(os.sep)
    if depth > 3: continue
    exts = sorted({os.path.splitext(f)[1].lower() for f in files})
    print('  ' * depth + os.path.basename(root) + '/', len(files), 'files', exts)
labels = [f for f in glob.glob(SA_DIR + '/**/*', recursive=True) if f.lower().endswith(('.txt', '.xml', '.json', '.csv'))]
print(len(labels), 'label-like files; first one:', labels[:1])
if labels: print(open(labels[0]).read()[:600])
"""),
code(r"""
# 2c. Inspect the South African dataset fully
import os, glob, csv
from PIL import Image
for root, dirs, files in os.walk(SA_DIR):
    d = root[len(SA_DIR):].count(os.sep)
    exts = sorted({os.path.splitext(f)[1].lower() for f in files})
    print('  ' * d + os.path.basename(root) + '/', len(files), 'files', exts)
for f in glob.glob(SA_DIR + '/**/*.csv', recursive=True) + glob.glob(SA_DIR + '/**/*.txt', recursive=True):
    rows = open(f).read().splitlines()
    print('\n==', f.replace(SA_DIR, ''), len(rows), 'lines'); print('\n'.join(rows[:4]))
"""),
code(r"""
# 2d. Convert the South African labels to YOLO format (full frames) and measure pothole sizes.
#     Annotation lines: '<path with spaces>.bmp <n> x y w h ...' in pixels (top-left x, y).
#     Result on 2 Oct 2026: 3680x2760 images; median pothole 100x26 px, i.e. 17x4.5 px at 640 input;
#     pothole centres between 0.48 and 0.62 of the image height.
import os, glob, random, re, statistics as st, yaml
from PIL import Image
OUT = '/content/sa_yolo'
root = glob.glob(SA_DIR + '/**/Dataset 1 (Simplex)/Dataset 1 (Simplex)', recursive=True)[0]
imgs = {os.path.splitext(os.path.basename(p))[0]: p for p in glob.glob(root + '/**/*.[jJ][pP][gG]', recursive=True)}
names = ['Potholes']                    # class list of the dataset the model is trained on
if os.path.exists('/content/dataset/data.yaml'):
    names = yaml.safe_load(open('/content/dataset/data.yaml'))['names']
names = list(names.values()) if isinstance(names, dict) else list(names)
POT = next(i for i, n in enumerate(names) if 'pothole' in n.lower())
ann = {}
for txt in glob.glob(root + '/*.txt'):
    for line in open(txt).read().splitlines():
        m = re.match(r'^(.*?\.(?:bmp|jpg|jpeg|png))\s+(.*)$', line.strip().replace('\\', '/'), re.I)
        if not m: continue
        nums = m.group(2).split()
        stem, n = os.path.splitext(os.path.basename(m.group(1)))[0], int(nums[0])
        v = list(map(int, nums[1:1 + 4 * n]))
        ann[stem] = [tuple(v[i:i + 4]) for i in range(0, len(v), 4)]
W, H = Image.open(next(iter(imgs.values()))).size
boxes = [b for bs in ann.values() for b in bs]
print('images:', len(imgs), '| annotated:', len(ann), '| boxes:', len(boxes), '| size:', (W, H))
q = lambda v: [round(x) for x in st.quantiles(v, n=10)[::4]]
print('width px p10/p50/p90', q([b[2] for b in boxes]), '-> at 640:', [round(x * 640 / W, 1) for x in q([b[2] for b in boxes])])
print('height px p10/p50/p90', q([b[3] for b in boxes]), '-> at 640:', [round(x * 640 / W, 1) for x in q([b[3] for b in boxes])])
print('centre y / H p10/p50/p90', [round(x, 2) for x in st.quantiles([(b[1] + b[3] / 2) / H for b in boxes], n=10)[::4]])
split_of = lambda p: 'test' if '/Test data/' in p.replace('\\', '/') else 'train'
random.seed(0)
pos = [s for s, p in imgs.items() if split_of(p) == 'train' and ann.get(s)]
neg = [s for s, p in imgs.items() if split_of(p) == 'train' and not ann.get(s)]
neg = random.sample(neg, min(len(neg), len(pos)))
train = pos + neg; random.shuffle(train); nval = len(train) * 15 // 100
plan = {'val': train[:nval], 'train': train[nval:], 'test': [s for s, p in imgs.items() if split_of(p) == 'test']}
for sp, stems in plan.items():
    os.makedirs(f'{OUT}/{sp}/images', exist_ok=True); os.makedirs(f'{OUT}/{sp}/labels', exist_ok=True)
    for s in stems:
        dst = f'{OUT}/{sp}/images/{s}.jpg'
        if not os.path.exists(dst): os.symlink(imgs[s], dst)
        with open(f'{OUT}/{sp}/labels/{s}.txt', 'w') as f:
            for x, y, w, h in ann.get(s, []):
                f.write(f'{POT} {(x + w / 2) / W:.6f} {(y + h / 2) / H:.6f} {w / W:.6f} {h / H:.6f}\n')
    print(sp, len(stems), 'images,', sum(len(ann.get(s, [])) for s in stems), 'potholes')
SA_YAML = f'{OUT}/data.yaml'
yaml.safe_dump({'path': OUT, 'train': 'train/images', 'val': 'val/images', 'test': 'test/images', 'names': names}, open(SA_YAML, 'w'))
"""),
code(r"""
# 2e. An existing pothole model on the South African test images at three input sizes (no training):
#     shows the gap between the training photos and South African roads, and the effect of resolution.
from ultralytics import YOLO
MODEL_TO_TEST = f'{RUN_DIR}/yolo11n_pothole_640/weights/best.pt'    # run 1
m = YOLO(MODEL_TO_TEST)
for sz in (640, 1280, 1920):
    r = m.val(data=SA_YAML, split='test', imgsz=sz, batch=8, plots=False, verbose=False,
              project=RUN_DIR, name=f'SA_test_{sz}', exist_ok=True)
    print(f'imgsz {sz}: mAP50 {r.box.map50:.3f}  mAP50-95 {r.box.map:.3f}  P {r.box.mp:.3f}  R {r.box.mr:.3f}')
"""),
code(r"""
# 2g. Run 2 data: crop the road band and cut it into tiles, so the South African potholes are big enough to see.
#     Their centres lie at 48 to 62 % of the frame height (Report, Methodology). The band 42 to 68 % is cut into
#     three overlapping 1280-pixel-wide tiles; at the 640 training size a median pothole becomes about 50 x 13 px
#     instead of 17 x 4.5 px for the whole frame. A box is kept in a tile when at least half of it lies inside.
#     Needs cells 2, 2b and 2d first (cell 3, 2c and 2e can be skipped). Takes about 10 minutes.
from PIL import Image
TILE_OUT = '/content/sa_band_tiles'
BAND = (0.42, 0.68); TILE_W = 1280
y0, y1 = int(BAND[0] * H), int(BAND[1] * H)
xs = [0, (W - TILE_W) // 2, W - TILE_W]
def tile_boxes(bs, tx):
    out = []
    for x, y, w, h in bs:
        ix0, iy0 = max(x, tx), max(y, y0); ix1, iy1 = min(x + w, tx + TILE_W), min(y + h, y1)
        if ix1 <= ix0 or iy1 <= iy0 or (ix1 - ix0) * (iy1 - iy0) < 0.5 * w * h: continue
        out.append((ix0 - tx, iy0 - y0, ix1 - ix0, iy1 - iy0))
    return out
th = y1 - y0; counts = {}
for sp, stems in plan.items():
    os.makedirs(f'{TILE_OUT}/{sp}/images', exist_ok=True); os.makedirs(f'{TILE_OUT}/{sp}/labels', exist_ok=True)
    n_img = n_box = 0
    for s in stems:
        im = None
        for k, tx in enumerate(xs):
            dst = f'{TILE_OUT}/{sp}/images/{s}_t{k}.jpg'
            bs = tile_boxes(ann.get(s, []), tx)
            if not os.path.exists(dst):
                im = im or Image.open(imgs[s]).convert('RGB')
                im.crop((tx, y0, tx + TILE_W, y1)).save(dst, quality=92)
            with open(f'{TILE_OUT}/{sp}/labels/{s}_t{k}.txt', 'w') as f:
                for x, y, w, h in bs:
                    f.write(f'{POT} {(x + w / 2) / TILE_W:.6f} {(y + h / 2) / th:.6f} {w / TILE_W:.6f} {h / th:.6f}\n')
            n_img += 1; n_box += len(bs)
    counts[sp] = (n_img, n_box); print(sp, n_img, 'tiles,', n_box, 'potholes')
SA_TILE_YAML = f'{TILE_OUT}/data.yaml'
yaml.safe_dump({'path': TILE_OUT, 'train': 'train/images', 'val': 'val/images', 'test': 'test/images', 'names': names},
               open(SA_TILE_YAML, 'w'))
print('band rows', y0, 'to', y1, '| tile size', TILE_W, 'x', th, '| data:', SA_TILE_YAML)
"""),
code("""
# 3. Dataset from Roboflow Universe (fill in from the dataset's download code)
# Run 1 dataset: 8,016 images, 5 classes (Pothole, Manhole, Open Manhole, Speed Bump, Unmarked Bump), CC BY 4.0;
# v23 is the unaugmented version (v25 is the same images tripled by augmentation). Uploader's model: mAP50 37.8%.
WORKSPACE = 'pothole-detection-1nczj'
PROJECT   = 'real-time-road-anomalies-detection-in-different-weather-conditions-and-lightning'
VERSION   = 23
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
NAME = f'yolo11n_{PROJECT[:24]}_v{VERSION}_{IMGSZ}'   # one folder per dataset and version, so a new dataset never resumes an old run
last = f'{RUN_DIR}/{NAME}/weights/last.pt'
if os.path.exists(last):
    model = YOLO(last); model.train(resume=True)
else:
    model = YOLO('yolo11n.pt')      # COCO-pretrained start (transfer learning)
    model.train(data=DATA_YAML, epochs=EPOCHS, imgsz=IMGSZ, batch=BATCH, patience=PATIENCE,
                project=RUN_DIR, name=NAME, exist_ok=True, seed=0)
"""),
code(r"""
# 4b. Run 2: train on the South African band tiles (instead of cell 4). Starts from the run 1 weights if they are
#     on Drive (fine-tuning), otherwise from COCO. Cells 5, 6 and 7 then work unchanged on this run.
#     About an hour on a T4. Re-running resumes from the last checkpoint on Drive.
from ultralytics import YOLO
DATA_YAML = SA_TILE_YAML
DATASET_URL = 'https://www.kaggle.com/datasets/sovitrath/road-pothole-images-for-pothole-detection (band tiles, cell 2g)'
PROJECT, VERSION = 'sa_band_tiles', 1
EPOCHS, IMGSZ, BATCH, PATIENCE = 60, 640, 32, 15
NAME = 'yolo11n_sa_band_tiles_640'
run1 = f'{RUN_DIR}/yolo11n_pothole_640/weights/best.pt'
last = f'{RUN_DIR}/{NAME}/weights/last.pt'
if os.path.exists(last):
    model = YOLO(last); model.train(resume=True)
else:
    start = run1 if os.path.exists(run1) else 'yolo11n.pt'
    print('starting from', start)
    model = YOLO(start)
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
    shutil.move(p, f"{out}/{NAME.rsplit('_', 1)[0]}_{sz}_ncnn_model")
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
