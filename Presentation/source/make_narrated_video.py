"""Assemble the narrated presentation video: slide image + narration per slide; on slide 8 the road timelapse
plays over the dashboard image. Usage: narr_video.py deck.pdf audio_dir timelapse.mp4 out.mp4"""
import os, subprocess, sys, re
import pymupdf
import imageio_ffmpeg

PDF, AUD, TL, OUT = sys.argv[1:5]
FF = imageio_ffmpeg.get_ffmpeg_exe()
WORK = os.path.join(os.path.dirname(OUT) or ".", "narr_work")
os.makedirs(WORK, exist_ok=True)
PAD_IN, PAD_OUT = 0.6, 0.9          # silence before and after each slide's narration
PX = 1920 / 13.333                  # pixels per inch at 1920 wide
# Slide 8 image box from build_deck.js: x = M = 0.6, y = 1.4, w = 6.3, h = 6.3 * 800 / 1280
BOX = [round(v * PX) for v in (0.6, 1.4, 6.3, 6.3 * 800 / 1280)]
CLIP = (4.0, 19.0)                  # timelapse span: rear camera tracking a person, then front camera clear


def dur(path):
    r = subprocess.run([FF, "-i", path], capture_output=True, text=True)
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


doc = pymupdf.open(PDF)
segs = []
for i, page in enumerate(doc, start=1):
    png = os.path.join(WORK, f"s{i:02d}.png")
    z = 1920 / page.rect.width
    page.get_pixmap(matrix=pymupdf.Matrix(z, z)).save(png)
    aud = os.path.join(AUD, f"a{i:02d}.mp3")
    d = dur(aud) + PAD_IN + PAD_OUT
    seg = os.path.join(WORK, f"seg{i:02d}.mp4")
    audio_f = f"[1:a]adelay={int(PAD_IN*1000)}:all=1,apad,atrim=0:{d:.3f},aresample=48000[a]"
    if i == 8:
        x, y, w, h = BOX
        span = CLIP[1] - CLIP[0]
        slow = d / span                      # stretch the clip to fill the slide's time
        vf = (f"[2:v]trim={CLIP[0]}:{CLIP[1]},setpts=(PTS-STARTPTS)*{slow:.4f},scale={w}:{h},fps=30[c];"
              f"[0:v][c]overlay={x}:{y}:shortest=0:eof_action=repeat,format=yuv420p[v]")
        cmd = [FF, "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-t", f"{d:.3f}", "-i", png,
               "-i", aud, "-i", TL, "-filter_complex", vf + ";" + audio_f]
    else:
        cmd = [FF, "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-t", f"{d:.3f}", "-i", png,
               "-i", aud, "-filter_complex", "[0:v]format=yuv420p[v];" + audio_f]
    cmd += ["-map", "[v]", "-map", "[a]", "-t", f"{d:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-tune", "stillimage" if i != 8 else "film", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-r", "30", seg]
    subprocess.run(cmd, check=True)
    segs.append(seg)
    print(i, round(d, 1), "s")

lst = os.path.join(WORK, "list.txt")
with open(lst, "w") as f:
    f.writelines(f"file '{s}'\n" for s in segs)
subprocess.run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                "-movflags", "+faststart", OUT], check=True)
print("wrote", OUT, round(dur(OUT), 1), "s")
