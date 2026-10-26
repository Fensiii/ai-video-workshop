"""《成功》抖音 16:9 节拍字效视频。音源：用户上传的 FUNK MANDALA 片段（32.3s）。
用法: python3 render.py <audio.wav> <out.mp4>
"""
import sys, math, subprocess, functools
import numpy as np
from multiprocessing import Pool
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1920, 1080, 30
DUR = 32.33
T0, BEAT = 5.098, 0.5674          # 第一个重拍 & 拍长（由音频起音拟合）
BAR = BEAT * 4
CN = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
EN = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
GOLD = (255, 200, 70)
RED = (255, 60, 60)
WHITE = (245, 245, 245)

def bar(i):  return T0 + i * BAR
def beat(i): return T0 + i * BEAT

# ---------------- 基础工具 ----------------
def ease_out(x): x = min(max(x, 0), 1); return 1 - (1 - x) ** 3
def ease_back(x):
    x = min(max(x, 0), 1); c = 1.9
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2
def decay(t, t0, tau):
    return math.exp(-(t - t0) / tau) if t >= t0 else 0.0

@functools.lru_cache(maxsize=256)
def font(path, size): return ImageFont.truetype(path, size)

@functools.lru_cache(maxsize=256)
def sprite(text, size, color, en=False, glow=True, gold=False):
    """渲染带发光的文字贴图（RGBA）。文泉驿没有粗体，用同色描边加粗。"""
    f = font(EN if en else CN, size)
    sw = max(2, size // 28)
    l, t, r, b = f.getbbox(text, stroke_width=sw)
    pad = size // 2
    w, h = r - l + pad * 2, b - t + pad * 2
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).text((pad - l, pad - t), text, font=f, fill=255,
                              stroke_width=sw, stroke_fill=255)
    m = np.asarray(mask, np.float32) / 255
    if gold:   # 竖向金色渐变
        g = np.linspace(0, 1, h)[:, None]
        rgb = np.stack([255 - 10 * g, 236 - 90 * g, 150 - 120 * g], -1) * np.ones((1, w, 1))
    else:
        rgb = np.ones((h, w, 3)) * np.array(color, np.float32)
    out = np.zeros((h, w, 4), np.float32)
    if glow:
        gm = np.asarray(mask.filter(ImageFilter.GaussianBlur(size / 7)), np.float32) / 255
        gc = np.array(GOLD if gold else color, np.float32)
        a_g = np.clip(gm * 0.9, 0, 1)
        out[..., :3] = gc * a_g[..., None]
        out[..., 3] = a_g
    a = m
    out[..., :3] = rgb * a[..., None] + out[..., :3] * (1 - a[..., None])
    out[..., 3] = a + out[..., 3] * (1 - a)
    # 转成非预乘
    al = np.maximum(out[..., 3:4], 1e-6)
    out[..., :3] = out[..., :3] / al
    return Image.fromarray(np.clip(np.concatenate([out[..., :3], out[..., 3:] * 255], -1), 0, 255).astype(np.uint8), "RGBA")

def put(canvas, spr, cx, cy, scale=1.0, alpha=1.0):
    if alpha <= 0.01 or scale <= 0.01: return
    s = spr
    if abs(scale - 1) > 1e-3:
        s = s.resize((max(1, int(s.width * scale)), max(1, int(s.height * scale))), Image.BILINEAR)
    if alpha < 0.999:
        s = s.copy(); s.putalpha(s.getchannel("A").point(lambda v: int(v * alpha)))
    canvas.alpha_composite(s, (int(cx - s.width / 2), int(cy - s.height / 2))) if \
        0 <= int(cx - s.width / 2) and 0 <= int(cy - s.height / 2) and \
        int(cx - s.width / 2) + s.width <= W and int(cy - s.height / 2) + s.height <= H else \
        _put_clip(canvas, s, int(cx - s.width / 2), int(cy - s.height / 2))

def _put_clip(canvas, s, x, y):
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    layer.paste(s, (x, y))
    canvas.alpha_composite(layer)

def slam(t, t0, dur=0.22):
    """重拍砸入：从 1.8 倍缩回 1，带一点回弹。返回 (scale, alpha)。"""
    if t < t0: return 0, 0
    x = (t - t0) / dur
    return 1 + 0.8 * (1 - ease_back(x)) if x < 1 else 1.0, min(1, x * 3)

# ---------------- 背景 ----------------
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
R = np.sqrt(((XX - W / 2) / W) ** 2 + ((YY - H / 2) / H) ** 2)
BASE = np.stack([10 + 22 * np.exp(-R * 4), 8 + 14 * np.exp(-R * 4), 14 + 8 * np.exp(-R * 4)], -1)
VIGN = np.clip(1.25 - R * 1.3, 0.25, 1)[..., None]
rng = np.random.default_rng(7)
PART = rng.random((140, 4))   # x, 速度, 大小, 相位

# 贯穿全片的“成长曲线”：有起有落，总体向上
CURVE_N = 400
_cx = np.linspace(0, 1, CURVE_N)
_noise = np.cumsum(rng.normal(0, 1, CURVE_N)); _noise -= np.linspace(_noise[0], _noise[-1], CURVE_N)
CURVE_Y = _cx ** 1.6 + 0.045 * _noise / (np.abs(_noise).max() + 1e-6) + 0.06 * np.sin(_cx * 23) * (1 - _cx)

def energy(t):
    if t < 0.5: return 0.1
    if t < 2.5: return 0.5
    if t < T0: return 0.3
    if t < bar(2): return 0.75
    if t < bar(11): return 1.0
    return max(0.2, 1 - (t - bar(11)) / 2)

def background(t):
    img = Image.fromarray(BASE.astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(img, "RGBA")
    e = energy(t)
    # 透视地面网格
    hy = H * 0.62
    for i in range(-14, 15):
        d.line([(W / 2 + i * 18, hy), (W / 2 + i * 260, H)], fill=(255, 190, 80, int(40 * e)), width=2)
    sp = (t * 0.9) % 1
    for k in range(10):
        z = (k + sp) / 10
        y = hy + (H - hy) * z ** 2.2
        d.line([(0, y), (W, y)], fill=(255, 190, 80, int(55 * e * z)), width=2)
    # 上升的金色粒子
    for x, v, s, ph in PART:
        y = (ph - t * (0.05 + 0.12 * v) * (0.6 + e)) % 1.0
        px, py = x * W + 20 * math.sin(t * 1.3 + ph * 9), H - y * H * 1.1
        r = 1 + s * 3
        d.ellipse([px - r, py - r, px + r, py + r], fill=(255, 210, 120, int(120 * e * (0.4 + s))))
    return img

def draw_curve(img, t):
    """底部成长曲线 + 进度百分比，从 drop 开始画到结尾。"""
    p = min(max((t - T0) / (bar(11) - T0), 0), 1)
    if p <= 0: return
    n = max(2, int(CURVE_N * p))
    x0, x1, yb, yt = 120, W - 120, H - 70, H - 330
    pts = [(x0 + (x1 - x0) * _cx[i], yb - (yb - yt) * CURVE_Y[i]) for i in range(n)]
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.line(pts, fill=(255, 190, 70, 255), width=10, joint="curve")
    glow = lay.filter(ImageFilter.GaussianBlur(14))
    d.line(pts, fill=(255, 240, 200, 255), width=4, joint="curve")
    hx, hy = pts[-1]
    d.ellipse([hx - 11, hy - 11, hx + 11, hy + 11], fill=(255, 255, 255, 255))
    a = 0.55 if t < bar(10) else 0.95
    for L in (glow, glow, lay):
        if a < 1:
            L = L.copy(); L.putalpha(L.getchannel("A").point(lambda v: int(v * a)))
        img.alpha_composite(L)
    pct = int(round(p * 100))
    put(img, sprite(f"{pct}%", 40, GOLD, en=True, glow=False), hx + 10 if hx < W - 200 else hx - 80, hy - 46, 1, a)

# ---------------- 各段内容 ----------------
def scene(img, t):
    cx, cy = W / 2, H / 2 - 60
    # 前奏：0.5–2.5 响，2.5–5.1 收着
    if t < 2.55:
        if t >= 0.5:
            w = ease_out((t - 0.5) / 0.6) * 900
            ImageDraw.Draw(img).rectangle([cx - w / 2, cy + 120, cx + w / 2, cy + 126], fill=(*GOLD, 255))
        if t >= 0.55:
            s, a = slam(t, 0.55); put(img, sprite("什么是", 110, WHITE), cx, cy - 40, s, a * (1 - ease_out((t - 2.3) / 0.25)))
        if t >= 1.15:
            s, a = slam(t, 1.15); put(img, sprite("成功？", 200, GOLD, gold=True), cx, cy + 230, s, a * (1 - ease_out((t - 2.3) / 0.25)))
        return
    if t < T0:
        k = int((t - T0 + 4 * BEAT) // BEAT) if t >= T0 - 4 * BEAT else -1
        if k <= 0:
            a = ease_out((t - 2.55) / 0.3)
            put(img, sprite("答案不在别处", 90, WHITE, glow=False), cx, cy, 1, a)
        else:
            n = ["", "3", "2", "1"][k]
            s, a = slam(t, beat(-4 + k), 0.18)
            put(img, sprite(n, 300, GOLD, en=True, gold=True), cx, cy, s, a)
        return
    b = int((t - T0) // BAR)
    tb = bar(b)
    def bt(i): return tb + i * BEAT
    if b == 0:
        s, a = slam(t, tb, 0.28)
        put(img, sprite("成功", 360, GOLD, gold=True), cx, cy - 20, s, a)
        if t > bt(2):
            put(img, sprite("S U C C E S S", 56, WHITE, en=True, glow=False), cx, cy + 210, 1, ease_out((t - bt(2)) / 0.3))
    elif b == 1:
        for j, (word, y) in enumerate([("不是运气", cy - 120), ("不是天赋", cy + 120)]):
            if t >= bt(2 * j):
                s, a = slam(t, bt(2 * j)); put(img, sprite(word, 170, WHITE), cx, y, s, a)
            if t >= bt(2 * j + 1):
                p = ease_out((t - bt(2 * j + 1)) / 0.15)
                sw = sprite(word, 170, WHITE)
                ww = (sw.width - 170) * p
                ImageDraw.Draw(img).rectangle([cx - (sw.width - 170) / 2, y - 8, cx - (sw.width - 170) / 2 + ww, y + 8], fill=(*RED, 255))
    elif b == 2:
        words = ["是", "跌倒", "爬起", "再来"]
        k = min(3, int((t - tb) // BEAT))
        s, a = slam(t, bt(k), 0.16)
        put(img, sprite(words[k], 300 if k else 240, GOLD if k == 3 else WHITE, gold=(k == 3)), cx, cy, s, a)
    elif b == 3:
        p = (t - tb) / BAR
        n = max(1, min(99, int(1 + 98 * p ** 1.3)))
        put(img, sprite("失败", 150, RED), cx - 330, cy, 1, 1)
        put(img, sprite(f"{n}", 260, RED, en=True), cx + 120, cy, 1.0 + 0.08 * decay(t, bt(int(p * 4)), 0.1), 1)
        put(img, sprite("次", 150, RED), cx + 430, cy, 1, 1)
    elif b == 4:
        s, a = slam(t, tb, 0.25)
        put(img, sprite("第 100 次", 230, GOLD, gold=True), cx, cy - 60, s, a)
        if t >= bt(2):
            s, a = slam(t, bt(2)); put(img, sprite("依然出发", 110, WHITE), cx, cy + 170, s, a)
    elif b == 5:
        steps = ["早起", "读书", "训练", "复盘"]
        k = min(3, int((t - tb) // BEAT))
        d = ImageDraw.Draw(img, "RGBA")
        for i in range(4):
            x, y = 330 + i * 330, cy + 260 - i * 140
            lit = i <= k
            d.rectangle([x, y, x + 330, y + 22], fill=(*(GOLD if lit else (90, 80, 70)), 255))
            if lit:
                s, a = slam(t, bt(i), 0.15)
                put(img, sprite(steps[i], 90, GOLD if i == k else WHITE, glow=(i == k)), x + 165, y - 70, s, a)
        px = 330 + k * 330 + 165 + 0; py = cy + 260 - k * 140 - 150
        put(img, sprite("▲", 60, GOLD, en=True), px, py - 60 - 10 * math.sin((t - bt(k)) * 10), 1, 1)
    elif b in (6, 7):
        word = "熬过的夜" if b == 6 else "流过的汗"
        k = min(3, int((t - tb) // BEAT))
        for i in range(k + 1):
            s, a = slam(t, bt(i), 0.15)
            put(img, sprite(word[i], 260, GOLD if i == 3 else WHITE, gold=(i == 3)), cx - 450 + i * 300, cy, s, a)
    elif b == 8:
        s, a = slam(t, tb); put(img, sprite("没人看见的", 130, WHITE), cx, cy - 120, s, a)
        if t >= bt(2):
            s, a = slam(t, bt(2), 0.25); put(img, sprite("努力", 280, GOLD, gold=True), cx, cy + 110, s, a)
    elif b == 9:
        s, a = slam(t, tb); put(img, sprite("终将", 150, WHITE), cx, cy - 140, s, a)
        if t >= bt(2):
            s, a = slam(t, bt(2), 0.25); put(img, sprite("被看见", 260, GOLD, gold=True), cx, cy + 100, s, a)
    elif b == 10:
        s, a = slam(t, tb, 0.3)
        sc = s * (1 + 0.025 * (t - tb))
        put(img, sprite("成功", 400, GOLD, gold=True), cx, cy - 70, sc, a)
        if t >= bt(1):
            put(img, sprite("是熬出来的", 90, WHITE), cx, cy + 290, 1, ease_out((t - bt(1)) / 0.3))
    else:  # 尾声
        a = ease_out((t - tb) / 0.5) * (1 - ease_out((t - 31.6) / 0.6))
        put(img, sprite("致 每一个还在坚持的你", 96, WHITE), cx, cy - 20, 1, a)
        put(img, sprite("—— 成功 ——", 60, GOLD, glow=False), cx, cy + 110, 1, a)

# ---------------- 节拍后期 ----------------
def downbeats(t):
    return [bar(i) for i in range(12)] + [0.55, 1.15] + [beat(-3), beat(-2), beat(-1)]

def post(img, t):
    e = energy(t)
    # 节拍推镜
    z = 1.0
    if T0 - 0.05 <= t < bar(11):
        lb = beat(math.floor((t - T0) / BEAT))
        z += 0.025 * decay(t, lb, 0.12)
    hit = max([decay(t, d, 0.12) for d in downbeats(t)] + [0])
    z += 0.05 * hit
    # 抖动
    sx = sy = 0
    if hit > 0.05:
        r = np.random.default_rng(int(t * 1000))
        sx, sy = r.normal(0, 14 * hit, 2)
    z = max(z, 1 + 2 * (abs(sx) + abs(sy) + 2) / W * 1.8)  # 留出抖动余量
    if z > 1.001 or sx or sy:
        cw, ch = W / z, H / z
        x0 = min(max((W - cw) / 2 + sx, 0), W - cw); y0 = min(max((H - ch) / 2 + sy, 0), H - ch)
        img = img.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))
    a = np.asarray(img.convert("RGB"), np.float32)
    # RGB 分离
    k = int(18 * hit)
    if k:
        a[..., 0] = np.roll(a[..., 0], k, 1); a[..., 2] = np.roll(a[..., 2], -k, 1)
    a = a * VIGN
    # 闪白
    fl = max([decay(t, d, 0.07) for d in downbeats(t)] + [0]) * 0.55
    if fl > 0.01: a = a + (255 - a) * fl
    # 颗粒
    a += np.random.default_rng(int(t * 997)).normal(0, 5, (H, W, 1)).astype(np.float32)
    # 首尾淡入淡出
    if t < 0.4: a *= t / 0.4
    if t > DUR - 0.5: a *= max(0, (DUR - t) / 0.5)
    return np.clip(a, 0, 255).astype(np.uint8)

def frame(i):
    t = i / FPS
    img = background(t)
    draw_curve(img, t)
    scene(img, t)
    return post(img, t).tobytes()

def main(audio, out, start=0, end=None):
    n = int(DUR * FPS)
    rng_ = range(start, end or n)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool() as pool:
        for j, buf in enumerate(pool.imap(frame, rng_, chunksize=4)):
            p.stdin.write(buf)
            if j % 100 == 0: print(j, flush=True)
    p.stdin.close(); p.wait()

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
