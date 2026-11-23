"""LinkedIn explainer video (1920x1080, 30 fps, silent, burned-in captions) that follows how the system works:
sense, detect, warn, store and send, road test, then the step towards autonomy.

Clips come from Presentation/site/videos, media/ and media/reels; figures from source/assets and the deck PDF.
Numbers are the report's (deck slides 3, 6, 9 and the LinkedIn post). No music: add it in the app if wanted.
Run from Presentation/source:  python make_linkedin_video.py <work dir>
Output: Presentation/linkedin_media/A_video/tukzie_how_it_works.mp4
"""
import os, subprocess, sys
import imageio_ffmpeg, fitz
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
PRES = os.path.dirname(HERE)
A = lambda *p: os.path.join(HERE, "assets", *p)
V = lambda *p: os.path.join(PRES, *p)
WORK = sys.argv[1] if len(sys.argv) > 1 else os.path.join(PRES, "linkedin_media", "_work")
os.makedirs(WORK, exist_ok=True)
OUT = os.path.join(PRES, "linkedin_media", "A_video", "tukzie_how_it_works.mp4")
FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS = 1920, 1080, 30

NAVY, PANEL, ACCENT, TEXT, MUTED, WHITE, SKY = "#14305C", "#E8F0FA", "#B85C00", "#1B1F24", "#4A5566", "#FFFFFF", "#1565C0"
BG_DARK = "#0E2240"
BOLD, REG = "C:/Windows/Fonts/calibrib.ttf", "C:/Windows/Fonts/calibri.ttf"
F = lambda size, bold=True: ImageFont.truetype(BOLD if bold else REG, size)


def run(args):
    r = subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y"] + args, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stderr)


def wrap(d, text, font, width):
    lines = []
    for para in text.split("\n"):
        cur = ""
        for w in para.split(" "):
            t = (cur + " " + w).strip()
            if d.textlength(t, font=font) <= width or not cur:
                cur = t
            else:
                lines.append(cur); cur = w
        lines.append(cur)
    return lines


def text_block(d, x, y, text, font, fill, width, gap=1.18):
    lh = int(font.size * gap)
    for ln in wrap(d, text, font, width):
        d.text((x, y), ln, font=font, fill=fill); y += lh
    return y


def paste_fit(base, im, box, radius=0):
    x0, y0, x1, y1 = box
    k = min((x1 - x0) / im.width, (y1 - y0) / im.height)
    im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
    px, py = x0 + (x1 - x0 - im.width) // 2, y0 + (y1 - y0 - im.height) // 2
    if radius:
        m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, im.width, im.height), radius, fill=255)
        base.paste(im.convert("RGB"), (px, py), m)
    elif im.mode == "RGBA":
        base.paste(im, (px, py), im)
    else:
        base.paste(im, (px, py))
    return (px, py, px + im.width, py + im.height)


def step_tag(d, x, y, label, dark=False):
    f = F(30)
    tw = d.textlength(label, font=f)
    d.rounded_rectangle((x, y, x + tw + 40, y + 50), 25, fill=ACCENT)
    d.text((x + 20, y + 8), label, font=f, fill=WHITE)
    return y + 74


# ---------------------------------------------------------------- cards (static PNGs)
def card_title():
    im = Image.new("RGB", (W, H), PANEL); d = ImageDraw.Draw(im)
    paste_fit(im, Image.open(A("tukzie_three_quarter_front.png")), (1020, 120, 1880, 900))
    y = 250
    y = text_block(d, 120, y, "One step closer to a trike that drives itself", F(88), NAVY, 900, 1.08) + 30
    y = text_block(d, 120, y, "Giving the TUKZIE electric cargo trike its senses: motion, cameras, live data", F(40, False), TEXT, 860) + 50
    d.text((120, y), "Samson Okuthe  |  EEE4022S final-year project  |  UCT 2026", font=F(32, False), fill=MUTED)
    return im


def card_before():
    im = Image.new("RGB", (W, H), PANEL); d = ImageDraw.Draw(im)
    paste_fit(im, Image.open(A("existing_dashboard.jpg")), (1180, 90, 1800, 990), radius=24)
    y = step_tag(d, 120, 300, "Where it started")
    y = text_block(d, 120, y, "The dashboard showed simulated numbers.", F(64), NAVY, 960) + 20
    text_block(d, 120, y, "Nothing on the trike measured how it rode, saw what was around it, or warned the driver.", F(44, False), TEXT, 940)
    return im


def card_system(stage):
    """System diagram, revealed in stages 1..4."""
    im = Image.new("RGB", (W, H), WHITE); d = ImageDraw.Draw(im)
    d.text((120, 70), "How it fits together", font=F(64), fill=NAVY)
    trike = Image.open(A("tukzie_side.png")).convert("RGBA")
    paste_fit(im, trike, (700, 300, 1220, 700))

    def box(x0, y0, x1, y1, title, lines, on, col=NAVY):
        fill = PANEL if on else "#F4F6F9"; tc = col if on else "#B8C2D0"; lc = TEXT if on else "#C8CFD9"
        d.rounded_rectangle((x0, y0, x1, y1), 28, fill=fill, outline=col if on else "#DDE3EA", width=4)
        d.text((x0 + 34, y0 + 26), title, font=F(40), fill=tc)
        y = y0 + 86
        for ln in lines:
            y = text_block(d, x0 + 34, y, ln, F(31, False), lc, x1 - x0 - 68) + 6

    box(110, 200, 680, 620, "Front: Raspberry Pi 5",
        ["Dashboard on the 10.1 in touchscreen", "Front camera and detector", "Front motion sensor, 200 per second"], stage >= 1)
    box(1240, 200, 1810, 620, "Rear: Raspberry Pi 4",
        ["Rear camera and detector", "Rear motion sensor, 200 per second", "Telemetry unit: battery, GPS, 4G, log"], stage >= 2)
    if stage >= 3:
        d.line((690, 410, 1230, 410), fill=SKY, width=8)
        for x, s in ((690, 1), (1230, -1)):
            d.polygon([(x, 410), (x + 26 * s, 394), (x + 26 * s, 426)], fill=SKY)
        f = F(34); t = "Ethernet: one shared clock"
        tw = d.textlength(t, font=f)
        d.rounded_rectangle((960 - tw / 2 - 20, 340, 960 + tw / 2 + 20, 392), 14, fill=WHITE)
        d.text((960 - tw / 2, 346), t, font=f, fill=SKY)
    if stage >= 4:
        d.rounded_rectangle((560, 760, 1360, 900), 28, fill=NAVY)
        d.text((600, 782), "4G to the cloud database", font=F(44), fill=WHITE)
        d.text((600, 840), "Logged on the trike first, so nothing is lost", font=F(30, False), fill="#CFDDF0")
        d.line((1525, 625, 1525, 830, 1365, 830), fill=NAVY, width=8, joint="curve")
        d.polygon([(1365, 830), (1392, 814), (1392, 846)], fill=NAVY)
    d.text((120, 980), "Three ESP32-S3 boards do the fixed-rate sensing; the two Raspberry Pis run the cameras and the dashboard.",
           font=F(30, False), fill=MUTED)
    return im


def card_ride():
    im = Image.new("RGB", (W, H), PANEL); d = ImageDraw.Draw(im)
    y = step_tag(d, 120, 70, "1  Sense the ride")
    text_block(d, 120, y, "Same trike, same speed: the sensors tell a smooth road from a rough one", F(54), NAVY, 1680)
    paste_fit(im, Image.open(A("imu_smooth_rough.png")), (120, 300, 1800, 1040), radius=18)
    return im


def card_data(slide_png):
    im = Image.new("RGB", (W, H), PANEL); d = ImageDraw.Draw(im)
    y = step_tag(d, 120, 70, "4  Store and send")
    text_block(d, 120, y, "I cut the 4G radio for 10 minutes. The trike kept logging, then sent the backlog when the signal came back.",
               F(48), NAVY, 1680)
    sl = Image.open(slide_png).convert("RGB")
    sx = sl.width / 1920
    chart = sl.crop((int(122 * sx), int(288 * sx), int(1052 * sx), int(638 * sx)))
    paste_fit(im, chart, (120, 300, 1260, 1030), radius=14)
    x, y = 1320, 380
    for big, small in (("112 / 112", "records reached the database, none missing or doubled"),
                       ("38 s", "to clear the backlog after reconnecting"),
                       ("99.9 %", "of road-test records over the wired link")):
        d.text((x, y), big, font=F(76), fill=NAVY)
        y = text_block(d, x, y + 86, small, F(32, False), TEXT, 480) + 34
    return im


def card_autonomy():
    im = Image.new("RGB", (W, H), WHITE); d = ImageDraw.Draw(im)
    y = step_tag(d, 120, 80, "Why it matters")
    y = text_block(d, 120, y, "A vehicle can only drive itself once it can:", F(56), NAVY, 1700) + 24
    items = ["see what is around it", "know how it is moving and what the road is like",
             "keep every sensor on the same clock", "never lose its data"]
    for it in items:
        d.ellipse((128, y + 18, 150, y + 40), fill=ACCENT)
        d.text((180, y), it, font=F(44, False), fill=TEXT); y += 70
    y += 30
    d.rounded_rectangle((120, y, 1800, y + 230), 26, fill=PANEL)
    text_block(d, 160, y + 30, "Today: it warns a human driver, the driver-assistance stage before self-driving.", F(40), NAVY, 1600)
    text_block(d, 160, y + 120, "Next: accurate positioning, an AI accelerator for the cameras, drive-by-wire control.", F(40, False), TEXT, 1600)
    return im


def card_end():
    im = Image.new("RGB", (W, H), NAVY); d = ImageDraw.Draw(im)
    paste_fit(im, Image.open(A("tukzie_three_quarter_front.png")), (1120, 160, 1840, 760))
    d.text((120, 230), "One step closer.", font=F(100), fill=WHITE)
    d.text((120, 380), "TUKZIE is an ongoing UCT programme; this is one piece of it.", font=F(40, False), fill="#CFDDF0")
    d.text((120, 520), "The whole journey:", font=F(36, False), fill="#CFDDF0")
    d.text((120, 565), "tuksense.site", font=F(76), fill=WHITE)
    d.text((120, 690), "The programme:", font=F(36, False), fill="#CFDDF0")
    d.text((120, 735), "tukzie.com", font=F(76), fill=WHITE)
    d.text((120, 940), "Supervisors: A/Prof Simon Winberg and Sampath Jayalath  |  Samson Okuthe, UCT EEE4022S 2026",
           font=F(30, False), fill="#A9BCD8")
    return im


# ---------------------------------------------------------------- overlays for video shots
def overlay_portrait(tag, head, sub):
    """Transparent overlay: caption panel on the right; the portrait clip sits at the left."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((900, 250, 1830, 830), 30, fill=(14, 34, 64, 225))
    y = step_tag(d, 950, 300, tag) if tag else 300
    y = text_block(d, 950, y + 6, head, F(56), WHITE, 830) + 18
    if sub:
        text_block(d, 950, y, sub, F(36, False), "#D5E1F2", 830)
    return im


def overlay_screen(tag, head, sub, hl=None):
    """Navy background with the screen recording area at the top and the caption band below."""
    im = Image.new("RGBA", (W, H), BG_DARK); d = ImageDraw.Draw(im)
    x = 120
    if tag:
        step_tag(d, 120, 886, tag)
        x = int(120 + d.textlength(tag, font=F(30)) + 40 + 30)
    text_block(d, x, 878, head, F(50), WHITE, 1800 - x)
    if sub:
        text_block(d, x, 942, sub, F(34, False), "#D5E1F2", 1800 - x)
    return im


SX, SY, SW, SH = 192, 20, 1536, 840   # where a 1152x720 / 1280x800 screen recording goes (keeps 8:5 within 1536x960 crop)


def seg_screen(name, src, t0, t1, speed, ov, freeze=None, hl=None, zoom=False):
    """Screen recording (8:5) scaled into the top area of a navy frame, caption band below."""
    png = os.path.join(WORK, name + "_ov.png"); ov.save(png)
    out = os.path.join(WORK, name + ".mp4")
    sw = int(SH * 8 / 5); sx = (W - sw) // 2
    if freeze is not None:
        frame = os.path.join(WORK, name + "_frame.png")
        run(["-ss", str(freeze), "-i", src, "-frames:v", "1", frame])
        base = Image.open(png).convert("RGB")
        raw = Image.open(frame).convert("RGB")
        k = sw / raw.width
        base.paste(raw.resize((sw, SH), Image.LANCZOS), (sx, SY))
        d = ImageDraw.Draw(base)
        if hl:
            x0, y0, x1, y1 = (int(v * k) for v in hl)
            d.rounded_rectangle((sx + x0, SY + y0, sx + x1, SY + y1), 16, outline="#E03A1E", width=7)
        still = os.path.join(WORK, name + "_still.png"); base.save(still)
        dur = t1 - t0
        zf = "zoompan=z='min(1+0.0009*on,1.12)':x='iw/2-(iw/zoom/2)-on*0.6':y='0':d=1:s=1920x1080:fps=30," if zoom else ""
        run(["-loop", "1", "-t", f"{dur}", "-i", still, "-vf", f"{zf}format=yuv420p,fade=t=in:st=0:d=0.3,fade=t=out:st={dur - 0.3}:d=0.3",
             "-r", str(FPS), "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-t", f"{dur}", out])
        return out
    dur = (t1 - t0) / speed
    fc = (f"[0:v]setpts=(PTS-STARTPTS)/{speed},fps={FPS},scale={sw}:{SH}:flags=lanczos[v];"
          f"[1:v][v]overlay={sx}:{SY}:shortest=1,format=yuv420p,"
          f"fade=t=in:st=0:d=0.3,fade=t=out:st={dur - 0.3:.2f}:d=0.3[o]")
    run(["-ss", str(t0), "-to", str(t1), "-i", src, "-loop", "1", "-i", png, "-filter_complex", fc,
         "-map", "[o]", "-an", "-r", str(FPS), "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-t", f"{dur:.2f}", out])
    return out


def seg_portrait(name, src, t0, t1, speed, ov, keep=1.0, src_h=None):
    """Portrait phone clip on the left over a blurred copy of itself; caption panel on the right.
    keep: fraction of the frame height kept from the top (cuts burned-in phone captions at the bottom)."""
    png = os.path.join(WORK, name + "_ov.png"); ov.save(png)
    out = os.path.join(WORK, name + ".mp4")
    dur = (t1 - t0) / speed
    crop = f"crop=iw:ih*{keep}:0:0," if keep < 1 else ""
    fc = (f"[0:v]setpts=(PTS-STARTPTS)/{speed},fps={FPS},{crop}split[a][b];"
          f"[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=40:2,eq=brightness=-0.18:saturation=0.8[bg];"
          f"[b]scale=-2:{H - 80}:flags=lanczos[fg];"
          f"[bg][fg]overlay=140:40[m];[m][1:v]overlay=0:0:shortest=1,format=yuv420p,"
          f"fade=t=in:st=0:d=0.3,fade=t=out:st={dur - 0.3:.2f}:d=0.3[o]")
    run(["-ss", str(t0), "-to", str(t1), "-i", src, "-loop", "1", "-i", png, "-filter_complex", fc,
         "-map", "[o]", "-an", "-r", str(FPS), "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-t", f"{dur:.2f}", out])
    return out


def seg_card(name, im, dur, fade_in=True, fade_out=True):
    png = os.path.join(WORK, name + ".png"); im.convert("RGB").save(png)
    out = os.path.join(WORK, name + ".mp4")
    fades = []
    if fade_in: fades.append("fade=t=in:st=0:d=0.3")
    if fade_out: fades.append(f"fade=t=out:st={dur - 0.3}:d=0.3")
    vf = ",".join(["format=yuv420p"] + fades)
    run(["-loop", "1", "-t", f"{dur}", "-i", png, "-vf", vf, "-r", str(FPS), "-c:v", "libx264", "-crf", "18",
         "-preset", "medium", "-tune", "stillimage", "-t", f"{dur}", out])
    return out


# ---------------------------------------------------------------- the edit
deck_png = os.path.join(WORK, "deck_s07.png")
fitz.open(V("SW7_Final_Presentation.pdf"))[6].get_pixmap(dpi=300).save(deck_png)

TL = V("site", "videos", "dashboard-timelapse.mp4")     # dashboard screen recording, 27 Oct road test, 10 fps
RUN2 = V("media", "run2_the_run_12-23_to_12-38.mp4")    # Surroundings page, 12:23 to 12:38
segs = [
    seg_card("s01_title", card_title(), 4.0),
    seg_card("s02_before", card_before(), 4.5),
    seg_card("s03a_sys", card_system(1), 1.6, fade_out=False),
    seg_card("s03b_sys", card_system(2), 1.6, fade_in=False, fade_out=False),
    seg_card("s03c_sys", card_system(3), 1.8, fade_in=False, fade_out=False),
    seg_card("s03d_sys", card_system(4), 3.2, fade_in=False),
    seg_portrait("s04_build", V("media", "reels", "reel3_whats_inside.mp4"), 0.0, 9.0, 1.2,
                 overlay_portrait("Built from scratch", "Three ESP32-S3 boards and two Raspberry Pis",
                                  "In enclosures I designed and 3D printed")),
    seg_portrait("s05_fit", V("site", "videos", "pods-wiring-deck.mp4"), 0.0, 7.8, 1.3,
                 overlay_portrait("1  Sense the ride", "Motion sensors front and rear",
                                  "Each reads the ride 200 times a second")),
    seg_card("s06_ride", card_ride(), 5.5),
    seg_screen("s07_rear", TL, 5.0, 16.0, 1.6,
               overlay_screen("2  Detect", "Rear camera: a person behind the trike", "Distance shown live on the driver's screen")),
    seg_screen("s08_bus", TL, 120.0, 127.0, 1.4,
               overlay_screen("2  Detect", "Front camera: a bus 4.3 m ahead", "People and vehicles, at both ends of the trike")),
    seg_screen("s09_truck", RUN2, 13.0, 17.9, 1.0,
               overlay_screen("2  Detect", "On the road test: a truck and people picked out", None)),
    seg_screen("s10_alert", TL, 0, 4.5, 1.0,
               overlay_screen("3  Warn", "Too close: the alert reaches the driver's screen in about 68 ms", None),
               freeze=95.0, hl=(38, 58, 575, 108)),
    seg_screen("s11_battery", TL, 21.0, 27.0, 1.2,
               overlay_screen("Live data", "Battery, range and charging on the dashboard", "Real readings, not simulated numbers")),
    seg_portrait("s12_voice", V("site", "videos", "map-page-on-trike.mp4"), 44.0, 59.5, 2.0,
                 overlay_portrait("Hands on the bars", "Offline voice commands",
                                  "The driver can switch screens, from the map to charging, without touching the screen"),
                 keep=0.78),
    seg_card("s13_data", card_data(deck_png), 6.5),
    seg_portrait("s14_road", V("site", "videos", "road-test-car-park.mp4"), 0.0, 10.0, 1.25,
                 overlay_portrait("Road test", "The same reading lap after lap, within about 5 %",
                                  "And on this trike, the road shakes it far more than its own motor does"),
                 keep=0.78),
    seg_card("s15_why", card_autonomy(), 7.0),
    seg_card("s16_end", card_end(), 5.0),
]

lst = os.path.join(WORK, "list.txt")
with open(lst, "w") as f:
    for s in segs:
        f.write(f"file '{s}'\n")
joined = os.path.join(WORK, "joined.mp4")
run(["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined])
os.makedirs(os.path.dirname(OUT), exist_ok=True)
run(["-i", joined, "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest",
     "-c:v", "libx264", "-preset", "slow", "-crf", "21", "-maxrate", "8M", "-bufsize", "16M", "-pix_fmt", "yuv420p",
     "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", OUT])
probe = subprocess.run([FF, "-hide_banner", "-i", OUT], capture_output=True, text=True).stderr
print("done", OUT, probe.split("Duration: ")[1].split(",")[0], f"{os.path.getsize(OUT) / 1e6:.1f} MB")
