"""Instagram reel (1080x1920, about 1:30) of the first road-test day from the phone clips in Projects/Roadtest1.

Follows Planning/roadtest-reel-prompt.md. Originals are not changed; output and working files go to Roadtest1/edit/.
Run: python make_roadtest_reel.py "<path to Roadtest1>"
"""
import os, subprocess, sys
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

SRC = sys.argv[1]
OUT = os.path.join(SRC, "edit")
os.makedirs(OUT, exist_ok=True)
FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H = 1080, 1920
BOLD = "C:/Windows/Fonts/segoeuib.ttf"

def clip(t):
    return os.path.join(SRC, f"WhatsApp Video 2026-10-21 at {t}.mp4")

V0, V1, V2, V3, V4 = (clip(t) for t in ("21.07.44", "21.07.53", "21.08.18", "21.08.19", "21.08.20"))

# (clip, in s, out s, speed, caption, title)
SHOTS = [
    (V0, 0.0, 14.0, 3.0, "Step 1: get it out of the building", "TUKZIE road test day"),
    (V0, 14.0, 42.0, 1.0, "Step 1: get it out of the building", None),
    (V1, 6.0, 18.5, 1.0, "Step 2: into Lecture Theatre 13", None),
    (V2, 0.0, 8.1, 1.0, "Step 3: sensors on board", None),
    (V4, 0.0, 6.0, 1.5, "Power and wiring", None),
    (V4, 14.0, 20.0, 1.0, "Live dashboard", None),
    (V4, 28.0, 34.0, 1.5, "Front sensors", None),
    (V1, 0.0, 5.3, 1.0, "The challenger: an RC car", None),
    (V3, 0.0, 15.5, 1.0, "TUKZIE's turn", None),
]

def run(args):
    r = subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y"] + args, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stderr)

def box_text(d, y, text, size, pad=28):
    f = ImageFont.truetype(BOLD, size)
    l, t, r, b = d.textbbox((0, 0), text, font=f)
    tw, th = r - l, b - t
    x = (W - tw) // 2
    d.rounded_rectangle((x - pad, y - pad // 2, x + tw + pad, y + th + pad), radius=26, fill=(15, 15, 15, 175))
    d.text((x - l, y - t + pad // 4), text, font=f, fill=(255, 255, 255, 255))
    return y + th + pad + 18

def caption_png(path, caption, title):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    y = 300
    if title:
        y = box_text(d, y, title, 84)
    box_text(d, y, caption, 58)
    im.save(path)

def atempo(s):
    if s == 1.0:
        return "anull"
    parts, r = [], s
    while r > 2.0:
        parts.append("atempo=2.0"); r /= 2.0
    parts.append(f"atempo={r:.4f}")
    return ",".join(parts)

segs = []
for i, (src, a, b, s, cap, title) in enumerate(SHOTS):
    png = os.path.join(OUT, f"cap{i}.png"); caption_png(png, cap, title)
    seg = os.path.join(OUT, f"seg{i}.mp4")
    fc = (f"[0:v]setpts=(PTS-STARTPTS)/{s},fps=30,scale={W}:{H}:flags=lanczos,unsharp=5:5:0.5,format=yuv420p[v];"
          f"[v][1:v]overlay=0:0:shortest=1,format=yuv420p[o];"
          f"[0:a]asetpts=PTS-STARTPTS,{atempo(s)},aresample=48000,aformat=channel_layouts=stereo[a]")
    run(["-ss", str(a), "-to", str(b), "-i", src, "-loop", "1", "-i", png, "-filter_complex", fc,
         "-map", "[o]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", "30",
         "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-shortest", seg])
    segs.append(seg); print("shot", i, cap, f"{(b - a) / s:.1f} s")

# end card from the last frame
last = os.path.join(OUT, "last.png")
src, a, b, s, _, _ = SHOTS[-1]  # raw frame, so the last shot's caption is not baked into the card
run(["-ss", f"{b - 0.3:.2f}", "-i", src, "-frames:v", "1", "-vf", f"scale={W}:{H}:flags=lanczos", last])
card = ImageEnhance.Brightness(Image.open(last).convert("RGB")).enhance(0.35).convert("RGBA")
d = ImageDraw.Draw(card)
y = box_text(d, 760, "SW-7 | TUKZIE telemetry", 70)
y = box_text(d, y, "UCT EEE4022S 2026", 52)
card.convert("RGB").save(os.path.join(OUT, "card.png"))
end = os.path.join(OUT, "seg_end.mp4")
run(["-loop", "1", "-t", "3", "-i", os.path.join(OUT, "card.png"), "-f", "lavfi", "-t", "3", "-i", "anullsrc=r=48000:cl=stereo",
     "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "160k", "-shortest", end])
segs.append(end)

lst = os.path.join(OUT, "list.txt")
with open(lst, "w") as f:
    for s in segs:
        f.write(f"file '{s}'\n")
joined = os.path.join(OUT, "joined.mp4")
run(["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined])
probe = subprocess.run([FF, "-hide_banner", "-i", joined], capture_output=True, text=True).stderr
dur_s = probe.split("Duration: ")[1].split(",")[0]
h, m, s = dur_s.split(":"); T = int(h) * 3600 + int(m) * 60 + float(s)
final = os.path.join(OUT, "TUKZIE_roadtest1_reel.mp4")
run(["-i", joined, "-vf", f"fade=t=in:st=0:d=0.4,fade=t=out:st={T - 0.8:.2f}:d=0.8",
     "-af", f"loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:st=0:d=0.3,afade=t=out:st={T - 1.0:.2f}:d=1.0",
     "-c:v", "libx264", "-preset", "slow", "-crf", "23", "-maxrate", "7M", "-bufsize", "14M",
     "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", final])
print("done", final, f"{T:.1f} s", f"{os.path.getsize(final) / 1e6:.1f} MB")
