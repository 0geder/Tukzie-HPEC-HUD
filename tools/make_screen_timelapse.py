"""Turn the Pi 5 dashboard screenshots (sw7-screens.service, one every 2 s) into a time-lapse video.

Usage: python tools/make_screen_timelapse.py <folder with HHMMSS.jpg> <out.mp4> [--fps 10] [--from HHMMSS] [--to HHMMSS]
At 10 frames/s each second of video is 20 s of real time. The clock time of each frame is burned in at the top.
"""
import argparse, os, subprocess, tempfile
import imageio_ffmpeg

ap = argparse.ArgumentParser()
ap.add_argument("folder"); ap.add_argument("out")
ap.add_argument("--fps", type=float, default=10); ap.add_argument("--from", dest="t0", default="000000")
ap.add_argument("--to", dest="t1", default="235959")
a = ap.parse_args()
frames = sorted(f for f in os.listdir(a.folder) if f.endswith(".jpg") and a.t0 <= f[:6] <= a.t1)
if not frames:
    raise SystemExit("no frames in range")
with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as lst:
    for f in frames:
        lst.write(f"file '{os.path.abspath(os.path.join(a.folder, f))}'\nduration {1 / a.fps:.4f}\n")
    lst.write(f"file '{os.path.abspath(os.path.join(a.folder, frames[-1]))}'\n")
ff = imageio_ffmpeg.get_ffmpeg_exe()
subprocess.run([ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst.name,
                "-vf", "scale=1280:800,format=yuv420p", "-c:v", "libx264", "-crf", "23", "-r", str(a.fps),
                "-movflags", "+faststart", a.out], check=True)
print(f"{len(frames)} frames {frames[0][:6]} to {frames[-1][:6]} -> {a.out}")
