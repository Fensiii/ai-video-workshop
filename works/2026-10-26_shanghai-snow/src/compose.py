"""在 three.js 渲染出的帧上叠字幕、定位/歌名标签、暗角和首尾淡入淡出，再和音频一起编码。

用法：
  python3 compose.py <帧目录> <audio.m4a> <输出.mp4>
  python3 compose.py <帧目录> --still 4 15 22          # 只出几张合成静帧 → stills/
"""
import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.environ.get("FONT_DIR", os.path.join(HERE, "fonts"))
F_SUB = os.path.join(FONT_DIR, "NotoSerifSC_600SemiBold.ttf")
F_UI = os.path.join(FONT_DIR, "NotoSansSC_500Medium.ttf")
W, H, FPS, DUR = 1080, 1920, 30, 24.5
NFRAMES = int(round(DUR * FPS))
SUB_Y = 1340
LINES = json.load(open(os.path.join(HERE, "lines.json"), encoding="utf-8"))["lines"]


def smooth(e0, e1, x):
    x = min(max((x - e0) / (e1 - e0), 0.0), 1.0)
    return x * x * (3 - 2 * x)


_fonts = {}


def font(path, size):
    if (path, size) not in _fonts:
        _fonts[(path, size)] = ImageFont.truetype(path, size)
    return _fonts[(path, size)]


# ---------------------------------------------------------------- 字幕：逐字从上方轻轻落下、由虚到实
BLUR = [0, 1.0, 2.0, 3.5, 5.5]
TRACK = 8
_glyph = {}


def glyph(ch, size, color, bl):
    key = (ch, size, color, bl)
    if key in _glyph:
        return _glyph[key]
    f = font(F_SUB, size)
    pad = 36
    w, h = int(f.getlength(ch)) + 2 * pad, int(size * 1.5) + 2 * pad
    fg = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(fg).text((pad, pad), ch, font=f, fill=color + (255,))
    a = fg.getchannel("A")
    zero = Image.new("L", (w, h), 0)
    sh = a.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.8))
    out = Image.merge("RGBA", [zero, zero, zero, sh])
    gl = a.filter(ImageFilter.GaussianBlur(5)).point(lambda v: int(v * 0.4))
    out.alpha_composite(Image.merge("RGBA", [Image.new("L", (w, h), c) for c in (200, 220, 255)] + [gl]))
    out.alpha_composite(fg)
    if bl:
        out = out.filter(ImageFilter.GaussianBlur(BLUR[bl]))
    _glyph[key] = (out, pad)
    return _glyph[key]


def layout(text, size):
    items, warm = [], False
    for ch in text:
        if ch == "【": warm = True; continue
        if ch == "】": warm = False; continue
        items.append((ch, (255, 214, 150) if warm else (250, 250, 255)))
    f = font(F_SUB, size)
    tw = sum(f.getlength(c) for c, _ in items) + TRACK * (len(items) - 1)
    if tw > 960:
        return layout(text, int(size * 960 / tw))
    x = W / 2 - tw / 2
    out = []
    for ch, c in items:
        out.append((ch, x, SUB_Y - size * 0.7, c, size))
        x += f.getlength(ch) + TRACK
    return out


def draw_line(fr, t, t0, t1, text, size):
    if t < t0 - 0.05 or t > t1 + 0.05:
        return
    items = layout(text, size)
    st = min(0.06, 0.55 / max(len(items), 1))
    q = smooth(t1 - 0.4, t1, t)
    for i, (ch, x, y, c, sz) in enumerate(items):
        p = smooth(t0 + i * st, t0 + i * st + 0.45, t)
        a = p * (1 - q)
        if a <= 0.01:
            continue
        bl = min(4, int(round(4 * max(1 - p, q))))
        g, pad = glyph(ch, sz, c, bl)
        if a < 0.995:
            g = g.copy()
            g.putalpha(g.getchannel("A").point(lambda v: int(v * a)))
        dy = -16 * (1 - p) + 10 * q
        fr.alpha_composite(g, (int(round(x - pad)), int(round(y - pad + dy))))


def make_tags():
    """右上角：定位“上海 · 外滩”+ 歌名。"""
    im = Image.new("RGBA", (W, 200), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f1, f2 = font(F_UI, 38), font(F_UI, 27)
    t1, t2 = "上海 · 外滩", "♪ 薛之谦《认真的雪》"
    xr = W - 44
    x1 = xr - f1.getlength(t1)
    d.text((x1, 40), t1, font=f1, fill=(255, 255, 255, 240))
    cx, cy = x1 - 26, 62
    d.ellipse([cx - 12, cy - 16, cx + 12, cy + 8], fill=(255, 255, 255, 240))
    d.polygon([(cx - 10, cy), (cx + 10, cy), (cx, cy + 20)], fill=(255, 255, 255, 240))
    d.ellipse([cx - 5, cy - 9, cx + 5, cy + 1], fill=(0, 0, 0, 0))
    d.text((xr - f2.getlength(t2), 100), t2, font=f2, fill=(235, 238, 250, 215))
    a = im.getchannel("A").filter(ImageFilter.GaussianBlur(6)).point(lambda v: int(v * 0.7))
    z = Image.new("L", im.size, 0)
    out = Image.merge("RGBA", [z, z, z, a])
    out.alpha_composite(im)
    return out


def make_vignette():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.5) / (H * 0.62)) ** 2)
    a = np.clip((r - 0.62) / 0.6, 0, 1) ** 1.5 * 0.6
    col = np.zeros((H, W, 3)); col[:] = (4, 5, 10)
    return Image.fromarray(np.dstack([col, a * 255]).astype(np.uint8), "RGBA")


class Composer:
    def __init__(self):
        self.tags = make_tags()
        self.vig = make_vignette()

    def frame(self, img, t):
        if t < 1.6:   # 开场：失焦 → 清晰
            img = img.filter(ImageFilter.GaussianBlur(9 * (1 - smooth(0, 1.6, t))))
        fr = img.convert("RGBA")
        fr.alpha_composite(self.vig)
        ta = smooth(0.8, 1.8, t)
        if ta > 0.01:
            tg = self.tags.copy()
            tg.putalpha(tg.getchannel("A").point(lambda v: int(v * ta)))
            fr.alpha_composite(tg, (0, 150))
        for t0, t1, text in LINES:
            draw_line(fr, t, t0, t1, text, 78 if text == "突然飘雪" else 64)
        black = max(1 - smooth(0, 0.9, t), smooth(23.9, 24.5, t))
        if black > 0:
            fr.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * black))))
        return fr.convert("RGB")


def main():
    src = sys.argv[1]
    cp = Composer()
    if sys.argv[2] == "--still":
        os.makedirs("stills", exist_ok=True)
        for s in sys.argv[3:]:
            i = int(round(float(s) * FPS))
            cp.frame(Image.open(f"{src}/f{i:04d}.jpg"), i / FPS).save(f"stills/c{float(s):05.1f}.jpg", quality=92)
        return
    audio, out = sys.argv[2], sys.argv[3]
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
                          "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for i in range(NFRAMES):
        p.stdin.write(cp.frame(Image.open(f"{src}/f{i:04d}.jpg").convert("RGB"), i / FPS).tobytes())
    p.stdin.close(); p.wait()


if __name__ == "__main__":
    main()
