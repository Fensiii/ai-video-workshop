"""古风竖屏：《大话西游》独白 × 《发如雪》。

水墨远山 + 圆月 + 梅枝 + 孤舟 + 落雪，书法字幕逐字晕开。
用法：
  python3 render.py --still 4 20 41 46     # 出静帧
  python3 render.py --seg 0 400 out0.mp4   # 渲染帧区间（无声）
"""
import json, math, os, sys, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.environ.get("FONT_DIR", os.path.join(HERE, "fonts"))
F_BRUSH = os.path.join(FONT_DIR, "MaShanZheng_400Regular.ttf")
F_TITLE = os.path.join(FONT_DIR, "ZhiMangXing_400Regular.ttf")
F_SERIF = os.path.join(FONT_DIR, "NotoSerifSC_500Medium.ttf")

W, H, FPS, DUR = 1080, 1920, 30, 53.0
M = 80  # 视差余量
SUB_Y = 1330

LINES = json.load(open(os.path.join(HERE, "lines.json"), encoding="utf-8"))["lines"]

INK = np.array([22, 27, 34])
PAPER = np.array([226, 222, 210])
GOLD = (232, 196, 122)
SNOWC = (246, 246, 250)


def smooth(e0, e1, x):
    x = min(max((x - e0) / (e1 - e0), 0.0), 1.0)
    return x * x * (3 - 2 * x)


def noise1d(n, scale, rng, octaves=5):
    out = np.zeros(n)
    amp, s = 1.0, scale
    for _ in range(octaves):
        k = max(int(n / s) + 3, 4)
        pts = rng.uniform(-1, 1, k)
        out += amp * np.interp(np.arange(n) / s, np.arange(k), pts)
        amp *= 0.5
        s /= 2.1
    return out


def blur_noise(h, w, sigma, rng):
    a = Image.fromarray((rng.uniform(0, 255, (h, w))).astype(np.uint8))
    a = a.filter(ImageFilter.GaussianBlur(sigma))
    x = np.asarray(a).astype(np.float32)
    return (x - x.mean()) / (x.std() + 1e-6)


# ---------------------------------------------------------------- 静态图层
def make_sky():
    rng = np.random.default_rng(1)
    y = np.linspace(0, 1, H + 2 * M)[:, None]
    top = np.array([24, 30, 46]); mid = np.array([92, 104, 120]); low = np.array([150, 156, 160])
    c = np.where(y < 0.62, top + (mid - top) * (y / 0.62) ** 1.3,
                 mid + (low - mid) * np.clip((y - 0.62) / 0.2, 0, 1))
    img = np.repeat(c[:, None, :], W + 2 * M, axis=1).reshape(H + 2 * M, W + 2 * M, 3)
    blot = blur_noise(H + 2 * M, W + 2 * M, 60, rng)[..., None]
    grain = rng.normal(0, 1, (H + 2 * M, W + 2 * M, 1))
    img = img * (1 + 0.05 * blot) + 3 * grain
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")


def make_moon():
    S = 900
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32) - S / 2
    r = np.sqrt(xx ** 2 + yy ** 2)
    R = 150
    rng = np.random.default_rng(2)
    tex = blur_noise(S, S, 18, rng)
    disk = np.clip(R - r, 0, 1.5) / 1.5
    glow = np.exp(-((r - R).clip(0)) / 110) * 0.55 + np.exp(-((r - R).clip(0)) / 30) * 0.35
    a = np.clip(disk + glow * (1 - disk), 0, 1)
    col = np.zeros((S, S, 3), np.float32)
    col[:] = (242, 234, 214)
    col = col * (1 - 0.05 * disk[..., None] * (tex[..., None] > 0.4))
    rgba = np.dstack([col, a * 255]).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def make_mountain(seed, base, amp, scale, shade, fall, height_px):
    """水墨山：山脊处墨重，往下渐淡入雾。"""
    rng = np.random.default_rng(seed)
    w = W + 2 * M
    ridge = base - amp * (0.5 + 0.5 * noise1d(w, scale, rng))
    ridge -= amp * 0.6 * np.exp(-((np.arange(w) - rng.uniform(0.2, 0.8) * w) / (w * 0.18)) ** 2)
    yy = np.arange(H + 2 * M)[:, None].astype(np.float32)
    d = yy - ridge[None, :]
    a = np.where(d >= 0, np.exp(-d / fall), 0.0)
    a = a * np.clip(d / 3 + 1, 0, 1)
    tex = blur_noise(H + 2 * M, w, 2.5, rng) * 0.18 + blur_noise(H + 2 * M, w, 14, rng) * 0.22
    a = np.clip(a * (1 + tex) * shade, 0, 1)
    a *= np.clip((height_px - d) / 140, 0, 1)
    col = np.zeros((H + 2 * M, w, 3), np.float32); col[:] = INK
    return Image.fromarray(np.dstack([col, a * 255]).astype(np.uint8), "RGBA")


def make_mist(seed):
    rng = np.random.default_rng(seed)
    w = W + 2 * M + 600
    n = blur_noise(H + 2 * M, w, 50, rng)
    yy = np.arange(H + 2 * M)[:, None]
    band = np.exp(-((yy - 1180) / 140.0) ** 2) * 0.55 + np.exp(-((yy - 1480) / 90.0) ** 2) * 0.6
    a = np.clip(band * (0.6 + 0.4 * n), 0, 1)
    col = np.zeros((H + 2 * M, w, 3)); col[:] = (200, 204, 208)
    return Image.fromarray(np.dstack([col, a * 255]).astype(np.uint8), "RGBA")


def make_water():
    rng = np.random.default_rng(5)
    w = W + 2 * M
    img = Image.new("RGBA", (w, H + 2 * M), (0, 0, 0, 0))
    yy = np.arange(H + 2 * M)[:, None].astype(np.float32)
    a = np.clip((yy - 1560) / 260, 0, 1) * 0.85
    a = np.repeat(a, w, axis=1)
    col = np.zeros((H + 2 * M, w, 3)); col[:] = (18, 24, 32)
    arr = np.dstack([col, a * 255]).astype(np.uint8)
    img = Image.fromarray(arr, "RGBA")
    d = ImageDraw.Draw(img)
    for _ in range(140):  # 水纹
        y = rng.uniform(1580, H + M)
        x = rng.uniform(0, w); L = rng.uniform(40, 220)
        d.line([(x, y), (x + L, y)], fill=(170, 180, 190, int(rng.uniform(15, 45))), width=1)
    return img


def make_plum():
    """右上角梅枝，墨枝 + 朱红梅花。"""
    rng = np.random.default_rng(7)
    S = 4
    img = Image.new("RGBA", (760 * S // 2, 900 * S // 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    sc = S / 2
    flowers = []

    def branch(x, y, ang, length, thick, depth):
        segs = int(length / 14)
        for i in range(segs):
            ang += rng.normal(0, 0.12)
            nx, ny = x + math.cos(ang) * 14, y + math.sin(ang) * 14
            t = thick * (1 - 0.6 * i / segs)
            d.line([(x * sc, y * sc), (nx * sc, ny * sc)], fill=(20, 22, 26, 245), width=max(1, int(t * sc)))
            d.ellipse([(nx - t / 2) * sc, (ny - t / 2) * sc, (nx + t / 2) * sc, (ny + t / 2) * sc], fill=(20, 22, 26, 245))
            x, y = nx, ny
            if depth > 0 and rng.random() < 0.13:
                branch(x, y, ang + rng.choice([-1, 1]) * rng.uniform(0.5, 1.0), length * rng.uniform(0.35, 0.6), t * 0.6, depth - 1)
            if rng.random() < 0.22 and t < 9:
                flowers.append((x + rng.normal(0, 6), y + rng.normal(0, 6), rng.uniform(7, 13)))
        flowers.append((x, y, rng.uniform(5, 8)))

    branch(780, 120, math.pi * 0.92, 520, 22, 3)
    branch(780, 330, math.pi * 1.04, 360, 15, 2)
    for x, y, r in flowers:
        if rng.random() < 0.25:  # 花苞
            d.ellipse([(x - r * .45) * sc, (y - r * .45) * sc, (x + r * .45) * sc, (y + r * .45) * sc], fill=(150, 28, 38, 240))
            continue
        rot = rng.uniform(0, 2 * math.pi)
        for k in range(5):
            a = rot + k * 2 * math.pi / 5
            px, py = x + math.cos(a) * r * 0.55, y + math.sin(a) * r * 0.55
            pr = r * 0.52
            d.ellipse([(px - pr) * sc, (py - pr) * sc, (px + pr) * sc, (py + pr) * sc], fill=(178, 34, 46, 235))
        d.ellipse([(x - r * .25) * sc, (y - r * .25) * sc, (x + r * .25) * sc, (y + r * .25) * sc], fill=(240, 200, 120, 255))
        # 积雪
        d.ellipse([(x - r * .5) * sc, (y - r * .9) * sc, (x + r * .3) * sc, (y - r * .45) * sc], fill=(245, 245, 248, 170))
    return img.resize((760, 900), Image.LANCZOS)


def make_boat():
    S = 3
    img = Image.new("RGBA", (260 * S, 200 * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = (16, 20, 26, 250)
    p = lambda pts: [(x * S, y * S) for x, y in pts]
    d.polygon(p([(10, 150), (40, 168), (200, 168), (245, 140), (190, 156), (60, 156)]), fill=c)  # 船身
    d.polygon(p([(70, 156), (80, 120), (150, 116), (165, 156)]), fill=c)  # 篷
    d.arc([70 * S, 96 * S, 165 * S, 150 * S], 180, 360, fill=c, width=10 * S)
    d.polygon(p([(185, 156), (183, 112), (195, 112), (196, 156)]), fill=c)  # 人身
    d.polygon(p([(170, 114), (189, 92), (210, 114)]), fill=c)  # 斗笠
    d.line(p([(205, 60), (150, 180)]), fill=c, width=3 * S)  # 竹篙
    return img.resize((260, 200), Image.LANCZOS)


def make_snow_sprites():
    out = {}
    for r in range(1, 14):
        s = r * 6 + 4
        yy, xx = np.mgrid[0:s, 0:s] - (s - 1) / 2
        a = np.exp(-(xx ** 2 + yy ** 2) / (2 * (r * 0.75) ** 2))
        col = np.zeros((s, s, 3)); col[:] = SNOWC
        out[r] = Image.fromarray(np.dstack([col, a * 255]).astype(np.uint8), "RGBA")
    return out


def make_vignette():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.47) / (H * 0.58)) ** 2)
    a = np.clip((r - 0.55) / 0.7, 0, 1) ** 1.6 * 0.75
    rng = np.random.default_rng(9)
    tex = blur_noise(H, W, 1.2, rng)
    a = np.clip(a + 0.025 * tex.clip(0), 0, 1)
    col = np.zeros((H, W, 3)); col[:] = (6, 8, 12)
    return Image.fromarray(np.dstack([col, a * 255]).astype(np.uint8), "RGBA")


def make_title():
    """左上竖排“发如雪” + 朱印“大话西游”。"""
    img = Image.new("RGBA", (260, 700), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(F_TITLE, 120)
    for i, ch in enumerate("发如雪"):
        d.text((70, 20 + i * 135), ch, font=f, fill=(238, 236, 228, 240))
    sh = img.filter(ImageFilter.GaussianBlur(8))
    sh_a = np.asarray(sh)[..., 3].astype(np.float32) * 0.6
    shadow = Image.fromarray(np.dstack([np.zeros((700, 260, 3)), sh_a]).astype(np.uint8), "RGBA")
    out = Image.alpha_composite(shadow, img)
    # 朱印
    seal = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
    sd = ImageDraw.Draw(seal)
    sd.rounded_rectangle([2, 2, 94, 94], 8, fill=(168, 30, 36, 235))
    sf = ImageFont.truetype(F_SERIF, 34)
    for i, ch in enumerate("大话西游"):
        cx, cy = (52 if i < 2 else 10), (8 if i % 2 == 0 else 50)
        sd.text((cx, cy), ch, font=sf, fill=(250, 236, 220, 255))
    out.alpha_composite(seal, (82, 450))
    return out


# ---------------------------------------------------------------- 字幕
_glyph = {}


def glyph(ch, size, color):
    key = (ch, size, color)
    if key in _glyph:
        return _glyph[key]
    f = ImageFont.truetype(F_BRUSH, size)
    pad = 30
    w = int(f.getlength(ch)) + 2 * pad
    h = size + 2 * pad
    fg = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(fg).text((pad, pad), ch, font=f, fill=color + (255,))
    a = np.asarray(fg)[..., 3]
    sh = Image.fromarray(a).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(9))
    sa = np.asarray(sh).astype(np.float32) * 0.85
    shadow = Image.fromarray(np.dstack([np.full((h, w, 3), 8), sa]).astype(np.uint8), "RGBA")
    g = Image.alpha_composite(shadow, fg)
    _glyph[key] = (g, pad)
    return _glyph[key]


def layout(text, size):
    """返回 [(ch, x, y, color)]，【】内为金色。"""
    rows, gold = [], False
    for raw in text.split("\n"):
        row = []
        for ch in raw:
            if ch == "【": gold = True; continue
            if ch == "】": gold = False; continue
            row.append((ch, GOLD if gold else (247, 243, 232)))
        rows.append(row)
    f = ImageFont.truetype(F_BRUSH, size)
    maxw = max(sum(f.getlength(c) for c, _ in r) for r in rows)
    if maxw > 950:
        return layout(text, int(size * 950 / maxw))
    out = []
    lh = size * 1.35
    y0 = SUB_Y - (len(rows) - 1) * lh / 2 - size / 2
    for ri, row in enumerate(rows):
        rw = sum(f.getlength(c) for c, _ in row)
        x = W / 2 - rw / 2
        for ch, col in row:
            out.append((ch, x, y0 + ri * lh, col, size))
            x += f.getlength(ch)
    return out


def draw_line(frame, t, t0, t1, text, size):
    if t < t0 - 0.05 or t > t1 + 0.05:
        return
    items = layout(text, size)
    n = len(items)
    stagger = min(0.07, 0.6 / max(n, 1))
    out_a = 1 - smooth(t1 - 0.35, t1, t)
    for i, (ch, x, y, col, sz) in enumerate(items):
        a = smooth(t0 + i * stagger, t0 + i * stagger + 0.35, t) * out_a
        if a <= 0.01:
            continue
        g, pad = glyph(ch, sz, col)
        if a < 0.999:
            g = g.copy()
            g.putalpha(g.getchannel("A").point(lambda v: int(v * a)))
        dy = (1 - a) * 14 if out_a > 0.99 else -(1 - out_a) * 10
        frame.alpha_composite(g, (int(round(x - pad)), int(round(y - pad + dy))))


def draw_text_center(frame, text, font, size, y, color, alpha, spacing=0):
    if alpha <= 0.01:
        return
    f = ImageFont.truetype(font, size)
    tw = sum(f.getlength(c) for c in text) + spacing * (len(text) - 1)
    layer = Image.new("RGBA", (W, size + 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x = W / 2 - tw / 2
    for c in text:
        d.text((x, 30), c, font=f, fill=color + (int(255 * alpha),))
        x += f.getlength(c) + spacing
    sa = np.asarray(layer.getchannel("A").filter(ImageFilter.GaussianBlur(7))).astype(np.float32) * 0.8
    sh = Image.fromarray(np.dstack([np.full((size + 60, W, 3), 8), sa]).astype(np.uint8), "RGBA")
    frame.alpha_composite(Image.alpha_composite(sh, layer), (0, int(y - 30)))


# ---------------------------------------------------------------- 合成
class Scene:
    def __init__(self):
        self.sky = make_sky()
        self.moon = make_moon()
        self.mts = [
            (make_mountain(11, 1080, 260, 420, 0.38, 260, 520), 0.15),
            (make_mountain(12, 1260, 300, 330, 0.62, 200, 420), 0.35),
            (make_mountain(13, 1460, 260, 260, 0.9, 160, 360), 0.65),
        ]
        self.mist = make_mist(21)
        self.water = make_water()
        self.plum = make_plum()
        self.boat = make_boat()
        self.snow = make_snow_sprites()
        self.vig = make_vignette()
        self.title = make_title()
        rng = np.random.default_rng(33)
        # 雪：(x0, y0, 速度, 半径, 摆幅, 相位, 透明度, 出现阈值)
        self.flakes = []
        for layer, (n, rr, vv, aa) in enumerate([(260, (1, 2), (40, 70), .55), (150, (2, 4), (80, 130), .75), (40, (6, 12), (170, 260), .55)]):
            for _ in range(n):
                self.flakes.append((rng.uniform(-100, W + 100), rng.uniform(0, H + 200), rng.uniform(*vv),
                                    int(rng.integers(rr[0], rr[1] + 1)), rng.uniform(8, 40), rng.uniform(0, 6.28),
                                    aa * rng.uniform(.6, 1), rng.random()))

    def layer_at(self, img, par, cam_x, cam_y, zoom, extra_x=0):
        """按视差把一层（含余量 M）变换到画面。"""
        z = 1 + (zoom - 1) * (0.4 + par)
        ox = M + extra_x + cam_x * par
        oy = M + cam_y * par
        # 画面坐标 (u,v) -> 图层坐标 ((u-W/2)/z + W/2 + ox, ...)
        a, e = 1 / z, 1 / z
        c = W / 2 + ox - W / 2 / z
        f = H / 2 + oy - H / 2 / z
        return img.transform((W, H), Image.AFFINE, (a, 0, c, 0, e, f), resample=Image.BILINEAR)

    def frame(self, t):
        zoom = 1 + 0.07 * (t / DUR)
        cam_x = 30 * math.sin(t / DUR * math.pi) - 15
        cam_y = -20 * (t / DUR)
        fr = self.layer_at(self.sky, 0.0, cam_x, cam_y, zoom)
        moon = Image.new("RGBA", (W + 2 * M, H + 2 * M), (0, 0, 0, 0))
        moon.alpha_composite(self.moon, (M + 330, M + 80 - int(0)))
        fr.alpha_composite(self.layer_at(moon, 0.05, cam_x, cam_y, zoom, extra_x=-t * 0.4))
        for i, (mt, par) in enumerate(self.mts):
            fr.alpha_composite(self.layer_at(mt, par, cam_x, cam_y, zoom))
            if i == 1:
                mist = self.mist.crop((int(t * 9) % 600, 0, int(t * 9) % 600 + W + 2 * M, H + 2 * M))
                fr.alpha_composite(self.layer_at(mist, 0.45, cam_x, cam_y, zoom))
        fr.alpha_composite(self.layer_at(self.water, 0.8, cam_x, cam_y, zoom))
        self.moon_reflection(fr, t)
        bob = 3 * math.sin(t * 1.3)
        fr.alpha_composite(self.boat, (int(150 + t * 2.2), int(1585 + bob)))
        fr.alpha_composite(self.plum, (W - 760 + int(6 * math.sin(t * 0.7)), -40 + int(4 * math.sin(t * 0.9))))
        self.draw_snow(fr, t)
        fr.alpha_composite(self.vig)
        # 标题
        ta = smooth(0.4, 2.2, t) * (1 - 0.35 * smooth(3, 5, t)) * (1 - smooth(51.5, 52.6, t))
        if ta > 0.01:
            ti = self.title.copy(); ti.putalpha(ti.getchannel("A").point(lambda v: int(v * ta)))
            fr.alpha_composite(ti, (30, 150))
        for t0, t1, text in LINES:
            big = "一万年" in text
            draw_line(fr, t, t0, t1, text, 96 if big else 80)
        # 片尾
        ea = smooth(43.8, 45.0, t) * (1 - smooth(51.0, 52.3, t))
        draw_text_center(fr, "—— 《大话西游》 ——", F_SERIF, 46, 1290, (240, 234, 220), ea, spacing=4)
        draw_text_center(fr, "BGM  周杰伦《发如雪》", F_SERIF, 34, 1380, (210, 205, 196), ea * 0.9, spacing=3)
        # 黑场
        black = max(1 - smooth(0, 1.2, t), smooth(51.8, 53.0, t))
        if black > 0:
            fr.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * black))))
        return fr.convert("RGB")

    def moon_reflection(self, fr, t):
        d = ImageDraw.Draw(fr, "RGBA")
        rng = np.random.default_rng(int(t * 6))
        cx = 780
        for k in range(26):
            y = 1590 + k * 11 + rng.uniform(-2, 2)
            w = (1 - k / 30) * rng.uniform(40, 130)
            x = cx + 12 * math.sin(t * 2 + k) - w / 2
            d.line([(x, y), (x + w, y)], fill=(240, 230, 200, int(90 * (1 - k / 28))), width=2)

    def draw_snow(self, fr, t):
        dens = 0.55 + 0.45 * smooth(18.5, 20.5, t)
        for x0, y0, v, r, amp, ph, a, th in self.flakes:
            if th > dens:
                continue
            y = (y0 + v * t) % (H + 200) - 100
            x = x0 + 25 * t * (v / 150) + amp * math.sin(t * (0.6 + v / 300) + ph)
            x = (x + 100) % (W + 200) - 100
            sp = self.snow[r]
            s = sp if a > 0.98 else sp.copy()
            if s is not sp:
                s.putalpha(sp.getchannel("A").point(lambda q: int(q * a)))
            fr.alpha_composite(s, (int(x - sp.width / 2), int(y - sp.height / 2))) if 0 <= x - sp.width / 2 and x + sp.width / 2 < W and 0 <= y - sp.height / 2 and y + sp.height / 2 < H else None


def main():
    sc = Scene()
    if sys.argv[1] == "--still":
        os.makedirs("stills", exist_ok=True)
        for s in sys.argv[2:]:
            sc.frame(float(s)).save(f"stills/{float(s):05.1f}.jpg", quality=90)
        return
    _, a, b, out = sys.argv[1:5]
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                          "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in range(int(a), int(b)):
        p.stdin.write(sc.frame(i / FPS).tobytes())
    p.stdin.close(); p.wait()


if __name__ == "__main__":
    main()
