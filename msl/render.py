"""Malaysia Student Life Short (1080x1920): title card, numbered point cards, warning card and WhatsApp card over a
Malaysia map, Roman Urdu captions with word highlight, soft music under the Urdu voice.
Usage: python msl/render.py spec.json   (spec["engine"] = folder of the shared engine: src/geo.py and fonts/)"""
import json
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

spec = json.load(open(sys.argv[1]))
ENG = spec["engine"]
sys.path.insert(0, os.path.join(ENG, "src"))
from geo import Topic  # noqa: E402

W, H, FPS = 1080, 1920, 30
FF = spec.get("ffmpeg", "ffmpeg")
WORK = spec["work"]
BOLD = os.path.join(ENG, "fonts", "Poppins-Bold.ttf")
MED = os.path.join(ENG, "fonts", "Poppins-Medium.ttf")
NAVY1, NAVY2 = (8, 24, 52), (10, 58, 88)
YELLOW = (255, 204, 0)
RED = (204, 0, 1)
CREAM = (255, 250, 240)
TEAL = (64, 196, 190)
BRAND = spec.get("brand", "MALAYSIA STUDENT LIFE")


def F(p, s):
    return ImageFont.truetype(p, s)


def wrap(d, text, f, maxw):
    out, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw or not cur:
            cur = t
        else:
            out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    return out


# ---------- background with the Malaysia map ----------
geo = Topic(["Malaysia"], [2010], spec["data_dir"], max_px=2600, log=lambda *a: None)
m = geo.empire(2010)
bx = m.getbbox()
mm = m.crop(bx)
scale = min(900 / mm.width, 460 / mm.height)
mm = mm.resize((int(mm.width * scale), int(mm.height * scale)), Image.LANCZOS)


def background(map_alpha=1.0, map_y=300):
    gy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    bg = np.array(NAVY1, np.float32) * (1 - gy) + np.array(NAVY2, np.float32) * gy
    img = Image.fromarray(np.broadcast_to(bg, (H, W, 3)).astype(np.uint8))
    d = ImageDraw.Draw(img)
    for x in range(0, W, 90):
        d.line((x, 0, x, H), fill=(18, 44, 76))
    for y in range(0, H, 90):
        d.line((0, y, W, y), fill=(18, 44, 76))
    if map_alpha > 0:
        glow = mm.filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.5 * map_alpha))
        x0 = (W - mm.width) // 2
        img.paste(Image.new("RGB", mm.size, TEAL), (x0, map_y), glow)
        img.paste(Image.new("RGB", mm.size, (28, 120, 126)), (x0, map_y), mm.point(lambda v: int(v * 0.9 * map_alpha)))
    # brand
    d.rounded_rectangle((W / 2 - 330, 110, W / 2 + 330, 186), 38, fill=YELLOW)
    d.text((W / 2, 148), BRAND, font=F(BOLD, 34), fill=NAVY1, anchor="mm")
    return img


BG_MAP = background(1.0, 300)
BG_SOFT = background(0.28, 300)


def step_card(sc, k_step, total):
    img = BG_SOFT.copy().convert("RGBA")
    d = ImageDraw.Draw(img)
    # progress dots
    for i in range(total):
        cx = W / 2 + (i - (total - 1) / 2) * 92
        done = i < k_step
        r = 26 if i == k_step - 1 else 18
        d.ellipse((cx - r, 330 - r, cx + r, 330 + r), fill=YELLOW if done else (40, 70, 104))
    # card
    d.rounded_rectangle((70, 470, W - 70, 1210), 48, fill=(250, 248, 242))
    d.ellipse((W / 2 - 95, 400, W / 2 + 95, 590), fill=RED, outline=CREAM, width=8)
    d.text((W / 2, 495), str(sc["n"]), font=F(BOLD, 110), fill=CREAM, anchor="mm")
    y = 680
    for ln in wrap(d, sc["title"], F(BOLD, 74), W - 220)[:2]:
        d.text((W / 2, y), ln, font=F(BOLD, 74), fill=NAVY1, anchor="mm")
        y += 92
    y += 30
    for ln in wrap(d, sc["detail"], F(MED, 52), W - 240)[:4]:
        d.text((W / 2, y), ln, font=F(MED, 52), fill=(60, 72, 92), anchor="mm")
        y += 70
    return img


def title_card(sc):
    img = BG_MAP.copy().convert("RGBA")
    d = ImageDraw.Draw(img)
    y = 940
    for ln in wrap(d, sc["title"], F(BOLD, 96), W - 140)[:3]:
        d.text((W / 2, y), ln, font=F(BOLD, 96), fill=CREAM, anchor="mm", stroke_width=6, stroke_fill=NAVY1)
        y += 112
    d.rounded_rectangle((W / 2 - 300, y + 20, W / 2 + 300, y + 110), 45, fill=RED)
    d.text((W / 2, y + 65), sc["badge"], font=F(BOLD, 48), fill=CREAM, anchor="mm")
    return img


def warn_card(sc):
    img = BG_SOFT.copy().convert("RGBA")
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((70, 520, W - 70, 1180), 48, fill=(255, 238, 236), outline=RED, width=10)
    d.regular_polygon((W / 2, 640, 90), 3, fill=RED)
    d.text((W / 2, 660), "!", font=F(BOLD, 100), fill=CREAM, anchor="mm")
    y = 820
    for ln in wrap(d, sc["title"], F(BOLD, 70), W - 220)[:2]:
        d.text((W / 2, y), ln, font=F(BOLD, 70), fill=RED, anchor="mm")
        y += 88
    y += 20
    for ln in wrap(d, sc["detail"], F(MED, 46), W - 240)[:3]:
        d.text((W / 2, y), ln, font=F(MED, 46), fill=(90, 30, 30), anchor="mm")
        y += 62
    return img


def cta_card(sc):
    img = BG_MAP.copy().convert("RGBA")
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((90, 880, W - 90, 1240), 48, fill=(37, 211, 102))
    d.text((W / 2, 960), sc["title"], font=F(BOLD, 64), fill=(255, 255, 255), anchor="mm")
    d.text((W / 2, 1060), sc["contact"], font=F(BOLD, 50), fill=(10, 50, 30), anchor="mm")
    d.text((W / 2, 1160), sc["detail"], font=F(MED, 40), fill=(255, 255, 255), anchor="mm")
    return img


# ---------- frames ----------
segs = spec["segments"]
scenes = spec["scenes"]
total_steps = sum(1 for s in scenes if s["kind"] == "step")
cards = []
ks = 0
for sc in scenes:
    if sc["kind"] == "step":
        ks += 1
        cards.append(step_card(sc, ks, total_steps))
    elif sc["kind"] == "title":
        cards.append(title_card(sc))
    elif sc["kind"] == "warn":
        cards.append(warn_card(sc))
    else:
        cards.append(cta_card(sc))

T = float(spec["total"])
LEAD = float(spec.get("lead", 0.6))
starts = [LEAD + s["start"] for s in segs]
starts[0] = 0.0
ends = [LEAD + s["end"] for s in segs]
cap_f = F(BOLD, 58)


def caption_layer(t):
    """Roman Urdu caption of the line being spoken, words light up in yellow as they come."""
    for i, s in enumerate(segs):
        a, b = LEAD + s["start"], LEAD + s["end"]
        if a - 0.05 <= t <= b + 0.25:
            words = scenes[i]["caption"].split()
            lens = [len(w) + 1 for w in words]
            tot = sum(lens)
            u = min(1, max(0, (t - a) / max(0.3, b - a)))
            lit = 0
            acc = 0
            for w in lens:
                acc += w
                if acc / tot <= u + 0.02:
                    lit += 1
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(ov)
            lines = wrap(d, scenes[i]["caption"], cap_f, W - 140)
            # keep at most 2 lines: show the half being spoken
            if len(lines) > 2:
                half = (len(words) + 1) // 2
                first = " ".join(words[:half])
                if lit > half:
                    words, lit = words[half:], lit - half
                else:
                    words = words[:half]
                lines = wrap(d, " ".join(words), cap_f, W - 140)
            y = 1380 - (len(lines) - 1) * 40
            wi = 0
            for ln in lines[:2]:
                ws = ln.split()
                total_w = d.textlength(ln, font=cap_f)
                x = W / 2 - total_w / 2
                for w in ws:
                    col = YELLOW if wi < lit else CREAM
                    d.text((x, y), w, font=cap_f, fill=col, anchor="lm", stroke_width=7, stroke_fill=(0, 0, 0))
                    x += d.textlength(w + " ", font=cap_f)
                    wi += 1
                y += 80
            return ov
    return None


def ease(x):
    return 1 - (1 - x) ** 3


silent = os.path.join(WORK, "_v.mp4")
enc = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", silent], stdin=subprocess.PIPE)
N = int(T * FPS)
cur = 0
prev_img = None
for f in range(N):
    t = f / FPS
    while cur + 1 < len(cards) and t >= starts[cur + 1]:
        prev_img = cards[cur]
        cur += 1
    since = t - starts[cur]
    card = cards[cur]
    u = ease(min(1, since / 0.35))
    sc = 0.92 + 0.08 * u
    fr = card.resize((int(W * sc), int(H * sc)), Image.BILINEAR) if sc < 0.999 else card
    base = (prev_img or card).copy()
    base.paste(fr, ((W - fr.width) // 2, (H - fr.height) // 2))
    if u < 1 and prev_img is not None:
        base = Image.blend(prev_img, base, u)
    cl = caption_layer(t)
    if cl is not None:
        base = Image.alpha_composite(base, cl)
    enc.stdin.write(base.convert("RGB").tobytes())
enc.stdin.close()
enc.wait()

# ---------- music: soft, warm, hopeful ----------
SR = 24000
n = int(T * SR) + SR
tt = np.arange(n, dtype=np.float32) / SR
mus = np.zeros(n, np.float32)
chords = [(261.63, 329.63, 392.0), (220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (196.0, 246.94, 293.66)]
bar = 2.4
for i in range(int(T / bar) + 2):
    a, b = int(i * bar * SR), min(n, int((i + 1) * bar * SR))
    if a >= n:
        break
    x = tt[a:b] - tt[a]
    env = np.minimum(1, x / 0.3) * np.exp(-x / 2.2)
    for f0 in chords[i % 4]:
        mus[a:b] += 0.05 * env * np.sin(2 * np.pi * f0 * x)
    # light pluck on the beat
    for q in range(4):
        p = int((i * bar + q * bar / 4) * SR)
        if p + 4000 < n:
            k = np.arange(4000) / SR
            mus[p:p + 4000] += 0.03 * np.exp(-k * 18) * np.sin(2 * np.pi * chords[i % 4][q % 3] * 2 * k)
fade = np.minimum(1, tt / 1.0) * np.minimum(1, np.maximum(0, T - tt) / 1.5)
mus = (mus * fade / max(1e-6, np.abs(mus).max()) * 0.9 * 32767).astype(np.int16)
mw = os.path.join(WORK, "_m.wav")
with wave.open(mw, "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(mus.tobytes())
ms = int(LEAD * 1000)
flt = (f"[1:a]adelay={ms}|{ms},apad[v];[2:a]volume=0.16[m];[v]asplit[vo][sc];[m][sc]sidechaincompress=threshold=0.03:ratio=5[md];"
       f"[vo][md]amix=inputs=2:normalize=0,alimiter=limit=0.95[a]")
r = subprocess.run([FF, "-y", "-loglevel", "error", "-i", silent, "-i", spec["voice"], "-i", mw, "-filter_complex", flt, "-map", "0:v", "-map", "[a]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-t", f"{T:.2f}", "-movflags", "+faststart", spec["out"]], capture_output=True, text=True)
if r.returncode:
    raise SystemExit(r.stderr[-800:])
os.remove(silent)
print("short done", flush=True)
