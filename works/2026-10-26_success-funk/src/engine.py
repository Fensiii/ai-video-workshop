"""《成功》v2 渲染引擎。

线性光 HDR 合成：颜色按 sRGB 书写，进管线前转线性，最后 ACES 色调映射回 sRGB。
- 文字：skia 抗锯齿字形蒙版 → 倒角金属材质（可挤出厚度）→ 预乘 RGBA 精灵
- 精灵：仿射/透视变换只算包围盒；运动模糊 = 快门内多时刻采样取平均
- 后期：体积光、冲击波折射、辉光金字塔、横向光条、镜头光晕、色散、故障、颗粒
"""
import math
import functools

import numpy as np
import cv2
import skia

cv2.setNumThreads(1)          # 并行交给多进程

W, H = 1920, 1080
FPS = 60
U = H / 1080.0                # 以 1080p 为基准的尺寸单位
CX, CY = W / 2.0, H / 2.0
SHUTTER = 0.5 / FPS           # 180° 快门
MARGIN = int(0.08 * W)        # 背景层四周留边，镜头晃动/旋转不露边
BW, BH = W + 2 * MARGIN, H + 2 * MARGIN

_F = "/usr/share/fonts/"
FONTS = {
    "serif": (_F + "opentype/noto/NotoSerifCJK-Black.ttc", 2),     # 思源宋体 Heavy
    "serif_b": (_F + "opentype/noto/NotoSerifCJK-Bold.ttc", 2),
    "serif_m": (_F + "opentype/noto/NotoSerifCJK-Medium.ttc", 2),
    "sans": (_F + "opentype/noto/NotoSansCJK-Black.ttc", 2),       # 思源黑体 Heavy
    "sans_b": (_F + "opentype/noto/NotoSansCJK-Bold.ttc", 2),
    "sans_m": (_F + "opentype/noto/NotoSansCJK-Medium.ttc", 2),
    "sans_l": (_F + "opentype/noto/NotoSansCJK-Light.ttc", 2),
    "smiley": (_F + "truetype/smiley-sans/SmileySans-Oblique.ttf", 0),  # 得意黑
    "kai": (_F + "truetype/lxgw-wenkai/LXGWWenKai-Bold.ttf", 0),       # 霞鹜文楷
    "inter": (_F + "opentype/inter/InterDisplay-Black.otf", 0),
    "inter_b": (_F + "opentype/inter/InterDisplay-Bold.otf", 0),
    "inter_l": (_F + "opentype/inter/InterDisplay-Light.otf", 0),
    "mono": (_F + "truetype/jetbrains-mono/JetBrainsMono-ExtraBold.ttf", 0),
    "mono_m": (_F + "truetype/jetbrains-mono/JetBrainsMono-Medium.ttf", 0),
}


# ---------------------------------------------------------------- 数学/颜色
def clamp01(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def smooth(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def ease_out(x, p=3.0):
    return 1 - (1 - clamp01(x)) ** p


def ease_in(x, p=3.0):
    return clamp01(x) ** p


def ease_io(x):
    x = clamp01(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def back_out(x, c=1.7):
    x = clamp01(x)
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def spring(x, freq=2.2, damp=6.0):
    """从 1 衰减振荡到 0（x 为秒）。"""
    return math.exp(-damp * x) * math.cos(2 * math.pi * freq * x) if x > 0 else 1.0


def pulse(t, t0, attack=0.012, decay=0.12):
    """冲击包络：快速起、指数落。"""
    if t < t0:
        return 0.0
    x = t - t0
    return x / attack if x < attack else math.exp(-(x - attack) / decay)


def window(t, a, b, fi=0.08, fo=0.08):
    """[a,b] 区间内为 1，两端平滑淡入淡出。"""
    if t < a or t > b:
        return 0.0
    return min(smooth((t - a) / fi) if fi > 0 else 1.0, smooth((b - t) / fo) if fo > 0 else 1.0)


def hash01(*k):
    """确定性伪随机（多进程一致）。"""
    x = 0
    for v in k:
        x = (x * 1000003) ^ int(v * 1000 + 7919)
    x = (x ^ (x >> 13)) * 0x5BD1E995 & 0xFFFFFFFF
    return ((x ^ (x >> 15)) & 0xFFFFFF) / float(0xFFFFFF)


def lin(c):
    """sRGB → 线性。整数元组按 0..255，浮点按 0..1。"""
    a = np.asarray(c)
    a = a / 255.0 if (a.dtype.kind in "iu" or a.max() > 1.0) else a
    return np.power(a.astype(np.float32), 2.2).astype(np.float32)


def ramp(v, stops):
    pos = [p for p, _ in stops]
    cols = np.array([lin(c) for _, c in stops], np.float32)
    v = np.asarray(v, np.float32)
    return np.stack([np.interp(v, pos, cols[:, i]) for i in range(3)], -1).astype(np.float32)


# ---------------------------------------------------------------- 文字
@functools.lru_cache(maxsize=None)
def typeface(key):
    path, idx = FONTS[key]
    tf = skia.Typeface.MakeFromFile(path, idx)
    assert tf is not None, path
    return tf


@functools.lru_cache(maxsize=None)
def _font(key, size):
    f = skia.Font(typeface(key), size)
    f.setSubpixel(True)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    f.setHinting(skia.FontHinting.kNone)
    return f


def _runs(text, font):
    if isinstance(text, str):
        return [(text, font, 1.0)]
    return [(r[0], r[1], r[2] if len(r) > 2 else 1.0) for r in text]


def layout(text, size, font="sans", tracking=0.0):
    """逐字排版。text 可以是字符串，或 ((文字, 字体, 字号倍数), ...) 混排。
    返回 [(字, Font, 左x, 字宽)] 与总宽；tracking 以字号为单位。"""
    out, x = [], 0.0
    for s, fk, mul in _runs(text, font):
        f = _font(fk, size * mul)
        for ch in s:
            adv = f.measureText(ch)
            out.append((ch, f, x, adv))
            x += adv + tracking * size
    total = x - tracking * size if out else 0.0
    return out, total


def text_mask(text, size, font="sans", tracking=0.0, margin=0.22):
    """返回 (蒙版 float32, 锚点)。锚点在整行字宽中点、字面框竖直中心，逐字精灵用同一约定可严丝合缝拼回整行。"""
    glyphs, total = layout(text, size, font, tracking)
    pad = int(size * 0.9) + 8
    w, h = int(math.ceil(total)) + 2 * pad, int(size * 1.7) + 2 * pad
    base = pad + size * 1.15
    buf = np.zeros((h, w, 4), np.uint8)
    surf = skia.Surface(buf, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType)
    cv = surf.getCanvas()
    paint = skia.Paint(AntiAlias=True, Color=skia.ColorWHITE)
    for ch, f, x, _ in glyphs:
        cv.drawString(ch, pad + x, base, f, paint)
    del cv, surf
    a = buf[..., 3].astype(np.float32) / 255.0
    ys, xs = np.nonzero(a > 0.003)
    m = int(size * margin) + 6
    y0, y1 = max(0, ys.min() - m), min(h, ys.max() + m + 1)
    x0, x1 = max(0, xs.min() - m), min(w, xs.max() + m + 1)
    return np.ascontiguousarray(a[y0:y1, x0:x1]), (pad + total / 2 - x0, base - 0.38 * size - y0)


# ---------------------------------------------------------------- 材质
_L = np.array([-0.42, -0.78, 0.46], np.float32)
_L /= np.linalg.norm(_L)
_HV = _L + np.array([0, 0, 1], np.float32)
_HV /= np.linalg.norm(_HV)

GOLD_ENV = [(0.00, (255, 248, 222)), (0.20, (255, 218, 128)), (0.44, (222, 156, 52)),
            (0.50, (118, 66, 16)), (0.56, (250, 200, 104)), (0.78, (232, 168, 66)), (1.00, (156, 96, 28))]
WHITE_ENV = [(0.0, (255, 255, 255)), (0.55, (246, 246, 250)), (1.0, (204, 210, 224))]
RED_ENV = [(0.0, (255, 140, 120)), (0.45, (240, 46, 42)), (1.0, (150, 8, 18))]
ICE_ENV = [(0.0, (250, 252, 255)), (0.5, (214, 230, 255)), (1.0, (140, 172, 232))]


def _normals(mask, size, bevel):
    sig = max(0.8, size * 0.028 * bevel)
    hb = cv2.GaussianBlur(mask, (0, 0), sig)
    gx = cv2.Sobel(hb, cv2.CV_32F, 1, 0, ksize=3) / 8.0
    gy = cv2.Sobel(hb, cv2.CV_32F, 0, 1, ksize=3) / 8.0
    k = 3.4 * sig
    nx, ny = -gx * k, -gy * k
    nz = 1.0 / np.sqrt(nx * nx + ny * ny + 1.0)
    return nx * nz, ny * nz, nz


def material(mask, size, kind="gold", bevel=1.0, emissive=1.0, color=None):
    """蒙版 → 预乘线性 RGBA。gold/white/red/ice 为倒角金属感；flat 为纯色。"""
    h, w = mask.shape
    if kind == "flat":
        col = np.broadcast_to(lin(color), (h, w, 3)) * emissive
        return np.dstack([col * mask[..., None], mask]).astype(np.float32)
    nx, ny, nz = _normals(mask, size, bevel)
    diff = np.clip(nx * _L[0] + ny * _L[1] + nz * _L[2], 0, 1)
    spec = np.clip(nx * _HV[0] + ny * _HV[1] + nz * _HV[2], 0, 1)
    rows = np.nonzero(mask.max(1) > 0.05)[0]
    yy = (np.arange(h, dtype=np.float32)[:, None] - rows.min()) / max(1, rows.max() - rows.min())
    yy = np.broadcast_to(yy, (h, w))
    if kind == "gold":
        base = ramp(np.clip(yy + ny * 0.32, 0, 1), GOLD_ENV)
        col = base * (0.5 + 0.8 * diff[..., None]) + (spec ** 36)[..., None] * lin((255, 238, 196)) * 2.6
    elif kind == "white":
        base = ramp(yy, WHITE_ENV)
        col = base * (0.72 + 0.38 * diff[..., None]) + (spec ** 30)[..., None] * 1.1
    elif kind == "red":
        base = ramp(np.clip(yy + ny * 0.2, 0, 1), RED_ENV)
        col = base * (0.55 + 0.7 * diff[..., None]) + (spec ** 30)[..., None] * lin((255, 200, 190)) * 1.6
    elif kind == "ice":
        base = ramp(np.clip(yy + ny * 0.25, 0, 1), ICE_ENV)
        col = base * (0.62 + 0.5 * diff[..., None]) + (spec ** 34)[..., None] * lin((220, 236, 255)) * 1.8
    else:
        raise ValueError(kind)
    col = col * emissive
    return np.dstack([col * mask[..., None], mask]).astype(np.float32)


def extrude_rgba(face, mask, depth, front=(140, 84, 22), back=(36, 18, 4), dx=0.0, dy=1.0):
    """把正面 face 沿 (dx,dy) 方向挤出 depth 像素的厚度（亚像素平移，侧面由亮到暗）。"""
    h, w = mask.shape
    n = max(1, int(depth))
    P = n + 3
    out = np.zeros((h + 2 * P, w + 2 * P, 4), np.float32)
    cf, cb = lin(front), lin(back)
    for i in range(n, 0, -1):
        f = i / n
        M = np.float32([[1, 0, P + dx * i], [0, 1, P + dy * i]])
        a = cv2.warpAffine(mask, M, (w + 2 * P, h + 2 * P), flags=cv2.INTER_LINEAR)
        c = cf * (1 - f) ** 1.4 + cb * (1 - (1 - f) ** 1.4)
        out[..., :3] = c * a[..., None] + out[..., :3] * (1 - a[..., None])
        out[..., 3] = a + out[..., 3] * (1 - a)
    fa = face[..., 3:4]
    reg = out[P:P + h, P:P + w]
    reg[..., :3] = face[..., :3] + reg[..., :3] * (1 - fa)
    reg[..., 3:4] = fa + reg[..., 3:4] * (1 - fa)
    return out, P


class Sprite:
    """预乘线性 RGBA 精灵，(ax, ay) 为锚点（像素坐标）。"""

    def __init__(self, img, ax, ay):
        self.img = np.ascontiguousarray(img, np.float32)
        self.ax, self.ay = float(ax), float(ay)
        self._mips = {}
        self._derived = {}

    @property
    def h(self):
        return self.img.shape[0]

    @property
    def w(self):
        return self.img.shape[1]

    def mip(self, level):
        if level == 0:
            return self.img
        if level not in self._mips:
            s = self.mip(level - 1)
            self._mips[level] = cv2.resize(s, (max(1, s.shape[1] // 2), max(1, s.shape[0] // 2)),
                                           interpolation=cv2.INTER_AREA)
        return self._mips[level]

    def derived(self, key, fn):
        if key not in self._derived:
            self._derived[key] = fn(self)
        return self._derived[key]


@functools.lru_cache(maxsize=None)
def text_sprite(text, size, font="sans", kind="gold", tracking=0.0, bevel=1.0, extrude=0,
                emissive=1.0, color=None, ex_front=(140, 84, 22), ex_back=(36, 18, 4)):
    mask, (ax, ay) = text_mask(text, size, font, tracking)
    rgba = material(mask, size, kind, bevel, emissive, color)
    if extrude:
        rgba, P = extrude_rgba(rgba, mask, extrude * U, ex_front, ex_back)
        ax, ay = ax + P, ay + P
    return Sprite(rgba, ax, ay)


def glow_sprite(spr, sigma, color, gain=1.0):
    """由精灵 alpha 生成纯加色光晕精灵（alpha=0，只加亮）。"""
    def make(s):
        p = int(sigma * 3)
        a = np.pad(s.img[..., 3], p)
        g = cv2.GaussianBlur(a, (0, 0), sigma)
        img = np.zeros(g.shape + (4,), np.float32)
        img[..., :3] = g[..., None] * lin(color) * gain
        return Sprite(img, s.ax + p, s.ay + p)
    return spr.derived(("glow", sigma, tuple(color), gain), make)


def shadow_sprite(spr, sigma=10.0, opacity=0.55):
    """柔和投影（黑色、只压暗不加亮），垫在亮背景上的字下面提高可读性。"""
    def make(s):
        p = int(sigma * 3)
        a = cv2.GaussianBlur(np.pad(s.img[..., 3], p), (0, 0), sigma) * opacity
        img = np.zeros(a.shape + (4,), np.float32)
        img[..., 3] = a
        return Sprite(img, s.ax + p, s.ay + p)
    return spr.derived(("shadow", sigma, opacity), make)


def reflect_sprite(spr, strength=0.32, fade=0.55, blur=2.5):
    """地面倒影：上下翻转、按距离渐隐并略微模糊。锚点放在原字底边（翻转轴）。"""
    def make(s):
        rows = np.nonzero(s.img[..., 3].max(1) > 0.02)[0]
        bottom = rows.max() + 1
        img = s.img[:bottom][::-1].copy()
        h = img.shape[0]
        g = np.clip(1 - np.arange(h, dtype=np.float32) / (h * fade), 0, 1) ** 1.6 * strength
        img *= g[:, None, None]
        img = cv2.GaussianBlur(img, (0, 0), blur * U)
        return Sprite(img, s.ax, 0.0)
    return spr.derived(("refl", strength, fade, blur), make)


def shatter(spr, n=36, seed=1):
    """Voronoi 碎裂：返回 [(碎片精灵, 碎片中心相对锚点的偏移)]。"""
    def make(s):
        rng = np.random.default_rng(seed)
        a = s.img[..., 3]
        ys, xs = np.nonzero(a > 0.1)
        pts = np.stack([rng.uniform(xs.min(), xs.max(), n), rng.uniform(ys.min(), ys.max(), n)], 1)
        yy, xx = np.mgrid[0:s.h, 0:s.w].astype(np.float32)
        d = (xx[..., None] - pts[:, 0]) ** 2 + (yy[..., None] - pts[:, 1]) ** 2
        lab = d.argmin(-1)
        pieces = []
        for i in range(n):
            m = (lab == i) & (a > 0.003)
            if m.sum() < 30:
                continue
            py, px = np.nonzero(m)
            y0, y1, x0, x1 = py.min(), py.max() + 1, px.min(), px.max() + 1
            img = s.img[y0:y1, x0:x1] * m[y0:y1, x0:x1, None]
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            pieces.append((Sprite(img, cx - x0, cy - y0), (cx - s.ax, cy - s.ay)))
        return pieces
    return spr.derived(("shatter", n, seed), make)


def shine_img(spr, pos, width=0.08, strength=1.6, angle=0.35, color=(255, 246, 220)):
    """沿斜向扫过的高光带。pos 0→1 从左到右。"""
    img = spr.img
    h, w = img.shape[:2]
    if pos < -0.3 or pos > 1.3:
        return img
    xx = np.arange(w, dtype=np.float32)[None, :] / w
    yy = np.arange(h, dtype=np.float32)[:, None] / w
    d = (xx + yy * angle) - pos * (1 + angle * h / w)
    band = np.exp(-(d / width) ** 2) * strength
    out = img.copy()
    out[..., :3] += band[..., None] * img[..., 3:4] * lin(color)
    return out


# ---------------------------------------------------------------- 变换 / 合成
def mat_translate(x, y):
    return np.array([[1, 0, x], [0, 1, y], [0, 0, 1]], np.float64)


def sprite_matrix(spr, x, y, s=1.0, rot=0.0, sx=1.0, sy=1.0, rx=0.0, ry=0.0, focal=None):
    """精灵像素 → 世界坐标的 3x3 矩阵。rx/ry 为绕水平/竖直轴的 3D 倾斜（度），透视投影。"""
    M = mat_translate(-spr.ax, -spr.ay)
    M = np.diag([s * sx, s * sy, 1.0]) @ M
    if rx or ry:
        f = focal or 1.8 * W
        a, b = math.radians(rx), math.radians(ry)
        Rx = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
        Ry = np.array([[math.cos(b), 0, math.sin(b)], [0, 1, 0], [-math.sin(b), 0, math.cos(b)]])
        R = Ry @ Rx
        Hp = np.array([[f * R[0, 0], f * R[0, 1], 0], [f * R[1, 0], f * R[1, 1], 0], [R[2, 0], R[2, 1], f]])
        M = Hp @ M
        M = M / M[2, 2] if abs(M[2, 2]) > 1e-9 else M
    if rot:
        r = math.radians(rot)
        M = np.array([[math.cos(r), -math.sin(r), 0], [math.sin(r), math.cos(r), 0], [0, 0, 1]]) @ M
    return mat_translate(x, y) @ M


def cam_matrix(cam, par=1.0):
    """世界 → 屏幕：绕画面中心缩放/旋转 + 平移。par 为视差系数（远景 < 1）。"""
    z = 1 + (cam["z"] - 1) * par
    r = math.radians(cam["rot"] * par)
    c, s = math.cos(r) * z, math.sin(r) * z
    tx, ty = cam["x"] * par, cam["y"] * par
    return np.array([[c, -s, CX - c * CX + s * CY - c * tx + s * ty],
                     [s, c, CY - s * CX - c * CY - s * tx - c * ty],
                     [0, 0, 1]], np.float64)


def _corners(M, w, h):
    P = M @ np.array([[0, w, w, 0], [0, 0, h, h], [1, 1, 1, 1]], np.float64)
    if (P[2] <= 1e-6).any():
        return None
    return P[0] / P[2], P[1] / P[2]


def item_bbox(it, cam):
    spr = it["spr"]
    M = cam_matrix(cam, it.get("par", 1.0)) @ it["M"]
    c = _corners(M, spr.w, spr.h)
    if c is None:
        return None
    return c[0].min(), c[1].min(), c[0].max(), c[1].max()


def draw_item(buf, off, it, cam):
    """把一个精灵画进 buf（覆盖屏幕区域 off=(x0,y0) 起的 RGBA 缓冲）。"""
    spr = it["spr"]
    a = it.get("a", 1.0)
    if a <= 0.003:
        return
    M = cam_matrix(cam, it.get("par", 1.0)) @ it["M"]
    sc = math.sqrt(abs(np.linalg.det(M[:2, :2]))) if abs(M[2, 0]) + abs(M[2, 1]) < 1e-12 else \
        math.sqrt(abs(np.linalg.det(M[:2, :2] / M[2, 2])))
    level = 0
    while sc < 0.6 and level < 4 and min(spr.w, spr.h) >> (level + 1) > 4:
        sc *= 2
        level += 1
    img = it.get("img")
    if img is None or level:
        img = spr.mip(level) if img is None else cv2.resize(img, (max(1, img.shape[1] >> level), max(1, img.shape[0] >> level)), interpolation=cv2.INTER_AREA)
    if level:
        M = M @ np.diag([float(1 << level), float(1 << level), 1.0])
    h, w = img.shape[:2]
    c = _corners(M, w, h)
    if c is None:
        return
    bh, bw = buf.shape[:2]
    x0 = max(int(math.floor(c[0].min())) - 1, off[0])
    y0 = max(int(math.floor(c[1].min())) - 1, off[1])
    x1 = min(int(math.ceil(c[0].max())) + 2, off[0] + bw)
    y1 = min(int(math.ceil(c[1].max())) + 2, off[1] + bh)
    if x1 <= x0 or y1 <= y0:
        return
    Mr = mat_translate(-x0, -y0) @ M
    if abs(Mr[2, 0]) + abs(Mr[2, 1]) < 1e-12:
        out = cv2.warpAffine(img, (Mr[:2] / Mr[2, 2]).astype(np.float32), (x1 - x0, y1 - y0),
                             flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    else:
        out = cv2.warpPerspective(img, Mr.astype(np.float32), (x1 - x0, y1 - y0),
                                  flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    if a < 0.999:
        out *= a * a      # 透明度按感知曲线：线性光里很小的 alpha 在暗背景上仍很显眼
    reg = buf[y0 - off[1]:y1 - off[1], x0 - off[0]:x1 - off[0]]
    mode = it.get("blend", "over")
    if mode == "add":
        reg[..., :3] += out[..., :3]
    else:
        oa = out[..., 3:4]
        reg[..., :3] = out[..., :3] + reg[..., :3] * (1 - oa)
        reg[..., 3:4] = oa + reg[..., 3:4] * (1 - oa)


def item(spr, x, y, s=1.0, a=1.0, rot=0.0, sx=1.0, sy=1.0, rx=0.0, ry=0.0, blend="over", par=1.0,
         shine=None, img=None):
    """场景用：生成一个绘制条目。shine=(pos, width, strength) 扫光。"""
    it = {"spr": spr, "M": sprite_matrix(spr, x, y, s, rot, sx, sy, rx, ry), "a": a, "blend": blend, "par": par}
    if shine is not None:
        it["img"] = shine_img(spr, *shine)
    elif img is not None:
        it["img"] = img
    return it


# ---------------------------------------------------------------- 背景工具
_YY, _XX = np.mgrid[0:H, 0:W].astype(np.float32)
_BYY, _BXX = np.mgrid[0:BH // 4, 0:BW // 4].astype(np.float32) * 4


def fbm(size, octaves=6, seed=0, base=4):
    rng = np.random.default_rng(seed)
    out = np.zeros((size, size), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        n = base * 2 ** o
        g = rng.random((n + 3, n + 3)).astype(np.float32)
        up = cv2.resize(g, (size + size * 3 // n, size + size * 3 // n), interpolation=cv2.INTER_CUBIC)
        out += up[:size, :size] * amp
        tot += amp
        amp *= 0.55
    out /= tot
    out = (out - out.min()) / (out.max() - out.min())
    return out


NOISE = [fbm(1024, 7, s) for s in (11, 23, 37)]


def noise_field(t, scale=1.0, speed=(0.0, 0.0), idx=0, w=BW // 4, h=BH // 4):
    """在大噪声图上平移采样，得到低分辨率的流动噪声（0..1）。"""
    n = NOISE[idx]
    sx = 1024 / (w * 1.6) / scale
    ox = (speed[0] * t * 60) % 300 + 100
    oy = (speed[1] * t * 60) % 300 + 100
    M = np.float32([[sx, 0, ox], [0, sx, oy]])
    return cv2.warpAffine(n, M, (w, h), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)


def up_bg(small):
    """低分辨率背景层放大到带边距的背景尺寸。"""
    return cv2.resize(small, (BW, BH), interpolation=cv2.INTER_CUBIC)


def bg_gradient(top, bottom, mid=None, mid_pos=0.5):
    """竖直渐变背景（线性色），尺寸为带边距的背景图。"""
    v = np.linspace(0, 1, BH, dtype=np.float32)
    stops = [(0.0, top), (1.0, bottom)] if mid is None else [(0.0, top), (mid_pos, mid), (1.0, bottom)]
    col = ramp(v, stops)
    return np.ascontiguousarray(np.broadcast_to(col[:, None, :], (BH, BW, 3)), np.float32).copy()


def radial(cx, cy, rx, ry=None, power=2.0, w=BW // 4, h=BH // 4, scale=4):
    """低分辨率径向衰减（坐标为背景图像素）。"""
    ry = ry or rx
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32) * scale
    d = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    return np.clip(1 - d, 0, 1) ** power


def wx(x):
    """世界坐标 → 背景图像素。"""
    return x + MARGIN


# 1/4 分辨率平滑背景层：渐变、雾、光晕、光束都在这里算，最后一次放大
SW, SH = BW // 4, BH // 4
_SY, _SX = np.mgrid[0:SH, 0:SW].astype(np.float32)
WXs = _SX * 4 + 2 - MARGIN       # 小图像素中心对应的世界坐标
WYs = _SY * 4 + 2 - MARGIN


def s_grad(stops, y0=0.0, y1=float(H)):
    v = np.clip((WYs[:, :1] - y0) / (y1 - y0), 0, 1)
    col = ramp(v[:, 0], stops)
    return np.ascontiguousarray(np.broadcast_to(col[:, None, :], (SH, SW, 3)), np.float32).copy()


def s_glow(sm, x, y, rx, ry, color, amt, halo=0.0):
    d2 = ((WXs - x) / rx) ** 2 + ((WYs - y) / ry) ** 2
    g = np.exp(-d2)
    if halo:
        g = g + halo / (1 + d2 * 4)
    sm += g[..., None] * (lin(color) * amt)


def s_beam(sm, x0, y0, ang, half, length, color, amt, mod=None, floor=None):
    """体积光束：从 (x0,y0) 朝 ang（度，0 为正下方）照射，半角 half；floor 以下光束减弱。"""
    dx, dy = WXs - x0, WYs - y0
    a = np.degrees(np.arctan2(dx, dy)) - ang
    cone = np.clip(1 - np.abs(a) / half, 0, 1) ** 1.6
    dist = np.sqrt(dx * dx + dy * dy)
    v = cone * np.exp(-dist / length) * np.clip(dist / 120, 0, 1)
    if mod is not None:
        v = v * mod
    if floor is not None:
        v = v * np.clip((floor - WYs) / 60 + 0.2, 0.2, 1)
    sm += v[..., None] * (lin(color) * amt)
    return v


def s_burst(sm, x, y, rot, n, color, amt, sharp=6.0, falloff=520.0, seed=0):
    """旋转的放射光芒。"""
    dx, dy = WXs - x, WYs - y
    ang = np.arctan2(dy, dx) + rot
    r = np.sqrt(dx * dx + dy * dy)
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 6.28, 3)
    pat = (0.5 + 0.5 * np.cos(ang * n + ph[0])) ** sharp + 0.6 * (0.5 + 0.5 * np.cos(ang * (n * 0.5 + 3) + ph[1])) ** (sharp * 1.5)
    v = pat / (1 + (r / falloff) ** 2) * np.clip(r / 60, 0, 1)
    sm += v[..., None] * (lin(color) * amt)


def s_fog(sm, t, color, amt, scale=1.0, speed=(0.5, -0.12), idx=0):
    f = noise_field(t, scale, speed, idx) * noise_field(t, scale * 0.55, (-speed[0] * 0.6, speed[1] * 0.5), (idx + 1) % 3)
    sm += (f * 2.2)[..., None] * (lin(color) * amt)
    return f


def s_up(sm):
    return cv2.resize(sm, (BW, BH), interpolation=cv2.INTER_LINEAR)


class Vec:
    """在背景图的一个区域里用 skia 画矢量（U8 预乘 sRGB），再按 alpha 合成进线性 HDR 背景。坐标为世界坐标。"""

    def __init__(self, x0, y0, x1, y1):
        self.x0, self.y0 = int(max(0, wx(x0))), int(max(0, wx(y0)))
        self.x1, self.y1 = int(min(BW, wx(x1))), int(min(BH, wx(y1)))
        self.buf = np.zeros((max(1, self.y1 - self.y0), max(1, self.x1 - self.x0), 4), np.uint8)
        self.surf = skia.Surface(self.buf, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType)
        self.c = self.surf.getCanvas()
        self.c.translate(MARGIN - self.x0, MARGIN - self.y0)

    @staticmethod
    def paint(color, a=1.0, stroke=False, width=1.0, blur=0.0, shader=None):
        r, g, b = [v / 255.0 for v in color]
        p = skia.Paint(AntiAlias=True, Color4f=skia.Color4f(r, g, b, a),
                       Style=skia.Paint.kStroke_Style if stroke else skia.Paint.kFill_Style, StrokeWidth=width,
                       StrokeJoin=skia.Paint.kRound_Join, StrokeCap=skia.Paint.kRound_Cap)
        if blur:
            p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
        if shader is not None:
            p.setShader(shader)
        return p

    def comp(self, img, gain=1.0, mode="over"):
        del self.c
        self.surf = None
        f = self.buf.astype(np.float32) * (1 / 255.0)
        a = np.ascontiguousarray(f[..., 3])
        rgb = cv2.cvtColor(f, cv2.COLOR_RGBA2RGB)
        safe = np.maximum(a, 1e-4)
        rgb = cv2.pow(cv2.divide(rgb, cv2.merge([safe, safe, safe])), 2.2)
        a3 = cv2.merge([a, a, a])
        rgb = cv2.multiply(rgb, a3)
        reg = img[self.y0:self.y1, self.x0:self.x1]
        if mode == "add":
            reg += rgb * gain
        else:
            reg[:] = cv2.add(rgb * gain, cv2.multiply(reg, 1 - a3))


def make_stars(n=900, seed=5):
    rng = np.random.default_rng(seed)
    img = np.zeros((BH, BW), np.float32)
    xs, ys = rng.uniform(0, BW, n), rng.uniform(0, BH, n)
    br = rng.pareto(2.2, n) * 0.25 + 0.05
    for x, y, b in zip(xs, ys, br):
        r = 0.7 + min(b, 2.0) * 0.6
        s = stamp(r)
        R = s.shape[0] // 2
        xi, yi = int(x), int(y)
        if R <= xi < BW - R and R <= yi < BH - R:
            img[yi - R:yi + R + 1, xi - R:xi + R + 1] += s * min(b, 3.0)
    return img


# 柔光点印章（粒子用）
_STAMPS = {}


def stamp(r):
    r = max(0.6, round(r * 2) / 2)
    if r not in _STAMPS:
        R = int(math.ceil(r * 3)) + 1
        yy, xx = np.mgrid[-R:R + 1, -R:R + 1].astype(np.float32)
        _STAMPS[r] = np.exp(-(xx ** 2 + yy ** 2) / (2 * (r * 0.6) ** 2)).astype(np.float32)
    return _STAMPS[r]


def add_stamp(img, x, y, r, color):
    s = stamp(r)
    R = s.shape[0] // 2
    xi, yi = int(round(x)), int(round(y))
    h, w = img.shape[:2]
    x0, y0, x1, y1 = xi - R, yi - R, xi + R + 1, yi + R + 1
    if x1 <= 0 or y1 <= 0 or x0 >= w or y0 >= h:
        return
    sx0, sy0 = max(0, -x0), max(0, -y0)
    sx1, sy1 = s.shape[1] - max(0, x1 - w), s.shape[0] - max(0, y1 - h)
    img[max(0, y0):min(h, y1), max(0, x0):min(w, x1)] += s[sy0:sy1, sx0:sx1, None] * color


class Dust:
    """漂浮的金色尘埃 / 焦外光斑（世界坐标，画进背景图）。"""

    def __init__(self, n=160, seed=3):
        rng = np.random.default_rng(seed)
        self.x = rng.uniform(0, BW, n)
        self.y = rng.uniform(0, BH, n)
        self.z = rng.random(n) ** 1.8          # 0 远 → 1 近
        self.vx = rng.normal(0, 8, n)
        self.vy = -rng.uniform(6, 26, n)
        self.ph = rng.uniform(0, 6.28, n)
        self.fr = rng.uniform(0.3, 1.2, n)

    def draw(self, img, t, color, gain=1.0, speed=1.0, rise=1.0):
        c = lin(color)
        for i in range(len(self.x)):
            z = self.z[i]
            sp = (0.4 + 1.2 * z) * speed
            x = (self.x[i] + (self.vx[i] * t + 18 * math.sin(t * self.fr[i] + self.ph[i])) * sp * U) % BW
            y = (self.y[i] + self.vy[i] * t * sp * rise * U) % BH
            r = (0.9 + 9.0 * z ** 2.2) * U
            tw = 0.55 + 0.45 * math.sin(t * 2.3 * self.fr[i] + self.ph[i] * 3)
            b = gain * tw * (0.7 * (1 - z) + 0.14 * z)      # 远处小而亮，近处大而淡（焦外）
            add_stamp(img, x, y, r, c * b)


# ---------------------------------------------------------------- 加色层（skia 画线/点，再按增益加进 HDR 画面）
class AddCanvas:
    def __init__(self):
        self.buf = np.zeros((H, W, 4), np.uint8)
        self.surf = skia.Surface(self.buf, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType)
        self.c = self.surf.getCanvas()
        self.used = False

    def paint(self, color, a=1.0, width=2.0, blur=0.0, stroke=True):
        r, g, b = [v / 255.0 if max(color) > 1 else v for v in color]
        p = skia.Paint(AntiAlias=True, BlendMode=skia.BlendMode.kPlus,
                       Color4f=skia.Color4f(r * a, g * a, b * a, 1.0),
                       Style=skia.Paint.kStroke_Style if stroke else skia.Paint.kFill_Style,
                       StrokeWidth=width, StrokeCap=skia.Paint.kRound_Cap)
        if blur > 0:
            p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
        self.used = True
        return p

    def result(self, gain=1.0):
        if not self.used:
            return None
        del self.c
        self.surf = None
        rgb = cv2.cvtColor(self.buf, cv2.COLOR_RGBA2RGB).astype(np.float32) * np.float32(1 / 255.0)
        return cv2.multiply(cv2.pow(rgb, 2.2), _s4(gain))


class Burst:
    """火花爆发：解析解运动（线性阻力 + 重力），画成带拖尾的流光线。"""

    def __init__(self, t0, x, y, n=140, speed=(500, 1700), angle=-90.0, spread=360.0, gravity=1100.0,
                 drag=2.6, life=(0.35, 1.1), seed=0, color="gold", width=(1.4, 3.2), ring=0.0):
        rng = np.random.default_rng(seed)
        self.t0, self.x, self.y = t0, x, y
        a = np.radians(angle + rng.uniform(-spread / 2, spread / 2, n))
        v = rng.uniform(*speed, n) * U
        self.vx, self.vy = np.cos(a) * v, np.sin(a) * v
        if ring:   # 从环形区域发射
            self.ox, self.oy = np.cos(a) * ring * U, np.sin(a) * ring * U * 0.6
        else:
            self.ox = self.oy = np.zeros(n)
        self.g, self.k = gravity * U, drag
        self.life = rng.uniform(*life, n)
        self.wd = rng.uniform(*width, n) * U
        self.hot = rng.random(n)
        self.color = color

    def pos(self, age):
        e = 1 - np.exp(-self.k * age)
        x = self.x + self.ox + self.vx / self.k * e
        y = self.y + self.oy + self.vy / self.k * e + self.g / self.k * age - self.g / self.k ** 2 * e
        return x, y

    def draw(self, ac, t, cam, gain=1.0):
        age = t - self.t0
        if age <= 0 or age > self.life.max():
            return
        trail = 0.012 + SHUTTER
        a0 = np.clip(age - trail, 0, None)
        x1, y1 = self.pos(np.full_like(self.life, age))
        x0, y0 = self.pos(a0)
        M = cam_matrix(cam)
        P1 = M @ np.vstack([x1, y1, np.ones_like(x1)])
        P0 = M @ np.vstack([x0, y0, np.ones_like(x0)])
        for i in range(len(self.life)):
            q = age / self.life[i]
            if q >= 1:
                continue
            fade = (1 - q) ** 1.5 * gain
            if self.color == "gold":
                col = (1.0, 0.85 - 0.35 * q, 0.45 - 0.4 * q) if self.hot[i] > 0.3 else (1.0, 0.95, 0.8)
            elif self.color == "red":
                col = (1.0, 0.35 - 0.25 * q, 0.25 - 0.2 * q)
            elif self.color == "blue":
                col = (0.6, 0.8, 1.0)
            else:
                col = (1.0, 1.0, 1.0)
            p = ac.paint(col, fade, self.wd[i] * (1 - 0.5 * q))
            ac.c.drawLine(P0[0, i], P0[1, i], P1[0, i], P1[1, i], p)


# ---------------------------------------------------------------- 后期
def _s4(*v):
    v = v * 3 if len(v) == 1 else v
    return (float(v[0]), float(v[1]), float(v[2]), 0.0)


_DIRT = None


def lens_dirt():
    """镜头脏污纹理（1/2 分辨率）：低频污渍 + 灰尘斑点，强光时才显出来。"""
    global _DIRT
    if _DIRT is None:
        rng = np.random.default_rng(17)
        w, h = W // 2, H // 2
        n = cv2.resize(fbm(512, 6, 77), (w, h), interpolation=cv2.INTER_CUBIC)
        d = np.clip((n - 0.45) * 2.2, 0, 1) ** 1.5 * 0.5
        for _ in range(320):
            x, y = rng.uniform(0, w), rng.uniform(0, h)
            r = rng.uniform(1.0, 9.0) ** 1.2
            a = rng.uniform(0.15, 0.9)
            cv2.circle(d, (int(x * 4), int(y * 4)), int(r * 4), float(a), -1, cv2.LINE_AA, 2)
        for _ in range(26):
            x, y = rng.uniform(0, w), rng.uniform(0, h)
            r = rng.uniform(10, 26)
            cv2.circle(d, (int(x * 4), int(y * 4)), int(r * 4), float(rng.uniform(0.1, 0.35)), 2, cv2.LINE_AA, 2)
        d = cv2.GaussianBlur(d, (0, 0), 1.2)
        _DIRT = (d / d.max()).astype(np.float32)
    return _DIRT


def bloom(img, thr=1.0, strength=0.45, tint=(1.0, 0.92, 0.8), levels=6,
          streak=0.0, st_thr=2.5, st_tint=(0.7, 0.82, 1.0), dirt=0.8):
    """辉光金字塔（软阈值保色）+ 镜头脏污 + 可选变形镜头横向光条。全在 1/2、1/4 分辨率算。"""
    small = cv2.resize(img, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    lum = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
    f = np.maximum(lum - thr, 0) / (lum + 1e-4)
    b = cv2.multiply(small, cv2.merge([f, f, f]))
    cur, pyr = b, []
    for i in range(levels):
        cur = cv2.GaussianBlur(cur, (0, 0), 1.6)
        pyr.append(cur)
        if i < levels - 1:
            cur = cv2.pyrDown(cur)
    acc = pyr[-1]
    wide = None
    for i, l in enumerate(reversed(pyr[:-1])):
        acc = cv2.scaleAdd(cv2.resize(acc, (l.shape[1], l.shape[0]), interpolation=cv2.INTER_LINEAR), 0.85, l)
        if i == 1:
            wide = acc
    acc = cv2.multiply(acc, _s4(*[v * strength / levels * 2.2 for v in tint]))
    if dirt > 0 and wide is not None:
        wd = cv2.resize(wide, (W // 2, H // 2), interpolation=cv2.INTER_LINEAR)
        dd = lens_dirt()
        acc = cv2.add(acc, cv2.multiply(wd, cv2.merge([dd, dd, dd]), scale=dirt * strength * 0.9))
    if streak > 0:
        q = cv2.resize(small, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        ql = cv2.cvtColor(q, cv2.COLOR_RGB2GRAY)
        s = np.maximum(ql - st_thr, 0)
        s = cv2.blur(cv2.blur(cv2.blur(s, (61, 1)), (61, 1)), (31, 1))
        s = cv2.resize(s, (W // 2, H // 2), interpolation=cv2.INTER_LINEAR)
        acc = cv2.add(acc, cv2.multiply(cv2.merge([s, s, s]), _s4(*[v * streak for v in st_tint])))
    return cv2.add(img, cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR))


def god_rays(src, cx, cy, strength=1.0, n=32, decay=0.955, reach=0.65, tint=(255, 216, 150)):
    """径向模糊体积光。src 为线性亮度图（全分辨率或 1/4 分辨率，单通道或三通道），cx/cy 屏幕坐标。"""
    if src.shape[0] != H // 4:
        src = cv2.resize(src, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    small = cv2.cvtColor(src, cv2.COLOR_RGB2GRAY) if src.ndim == 3 else src.astype(np.float32)
    acc = small.copy()
    wsum, w = 1.0, 1.0
    c4x, c4y = cx / 4, cy / 4
    for i in range(1, n):
        f = 1 - reach * i / n
        M = np.float32([[f, 0, c4x * (1 - f)], [0, f, c4y * (1 - f)]])
        w *= decay
        acc = cv2.scaleAdd(cv2.warpAffine(small, M, (W // 4, H // 4), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP), w, acc)
        wsum += w
    acc = cv2.resize(acc * (strength / wsum), (W, H), interpolation=cv2.INTER_LINEAR)
    return cv2.multiply(cv2.merge([acc, acc, acc]), _s4(*lin(tint)))


def shockwave(img, cx, cy, radius, width, amp):
    """环形折射波：环带内像素沿径向位移。只处理环所在包围盒。"""
    cx, cy, radius, width, amp = float(cx), float(cy), float(radius), float(width), float(amp)
    R = radius + 3 * width
    x0, x1 = int(max(0, cx - R)), int(min(W, cx + R))
    y0, y1 = int(max(0, cy - R)), int(min(H, cy + R))
    if x1 <= x0 or y1 <= y0 or amp == 0:
        return img
    X, Y = _XX[y0:y1, x0:x1], _YY[y0:y1, x0:x1]
    dx, dy = X - cx, Y - cy
    r = np.sqrt(dx * dx + dy * dy) + 1e-3
    d = (r - radius) / width
    off = amp * d * np.exp(-d * d)
    mx = (X - dx / r * off).astype(np.float32)
    my = (Y - dy / r * off).astype(np.float32)
    out = img.copy()
    out[y0:y1, x0:x1] = cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    ring = np.exp(-d * d) * abs(amp) / width * 0.08
    out[y0:y1, x0:x1] += ring[..., None] * np.float32([1.0, 0.9, 0.75])
    return out


def chroma(img, k):
    """径向色散：R 向外、B 向内。"""
    if k < 1e-5:
        return img
    out = img.copy()
    for ch, s in ((0, 1 + k), (2, 1 - k)):
        M = np.float32([[s, 0, CX * (1 - s)], [0, s, CY * (1 - s)]])
        out[..., ch] = cv2.warpAffine(img[..., ch], M, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                                      borderMode=cv2.BORDER_REFLECT)
    return out


def glitch(img, amount, seed, color=True):
    """数字故障：横条错位、通道分离、色块。"""
    if amount <= 0.01:
        return img
    rng = np.random.default_rng(seed)
    out = img.copy()
    n = int(2 + amount * 14)
    for _ in range(n):
        y0 = int(rng.integers(0, H - 8))
        h = int(rng.integers(3, int(8 + amount * 90 * U)))
        dx = int(rng.normal(0, amount * 90 * U))
        band = out[y0:y0 + h]
        band[:] = np.roll(band, dx, axis=1)
        if color and rng.random() < 0.6:
            band[..., 0] = np.roll(band[..., 0], int(amount * 26 * U), axis=1)
            band[..., 2] = np.roll(band[..., 2], -int(amount * 26 * U), axis=1)
    for _ in range(int(amount * 6)):
        bw, bh = int(rng.integers(40, 300) * U), int(rng.integers(6, 40) * U)
        x, y = int(rng.integers(0, W - bw)), int(rng.integers(0, H - bh))
        sx, sy = int(rng.integers(0, W - bw)), int(rng.integers(0, H - bh))
        out[y:y + bh, x:x + bw] = out[sy:sy + bh, sx:sx + bw] * rng.uniform(0.6, 1.6)
    return out


def flare(ac, sx, sy, strength, color=(255, 200, 120), ghosts=True):
    """镜头光晕：光源星芒 + 沿中心对称轴的鬼影。"""
    if strength <= 0.01:
        return
    c = ac.c
    p = ac.paint(color, 0.9 * strength, blur=60 * U, stroke=False)
    c.drawCircle(sx, sy, 90 * U, p)
    p = ac.paint((255, 255, 255), 0.9 * strength, blur=10 * U, stroke=False)
    c.drawCircle(sx, sy, 18 * U, p)
    for k in range(6):
        ang = math.radians(k * 30 + 15)
        L = (380 if k % 3 == 0 else 200) * U * (0.6 + strength * 0.6)
        p = ac.paint(color, 0.55 * strength, width=2.2 * U, blur=2 * U)
        c.drawLine(sx - math.cos(ang) * L, sy - math.sin(ang) * L, sx + math.cos(ang) * L, sy + math.sin(ang) * L, p)
    p = ac.paint((170, 200, 255), 0.5 * strength, width=3 * U, blur=3 * U)
    c.drawLine(sx - 900 * U, sy, sx + 900 * U, sy, p)
    if ghosts:
        vx, vy = CX - sx, CY - sy
        for k, (f, r, col, a) in enumerate([(0.55, 40, (255, 170, 90), 0.25), (0.95, 22, (140, 200, 255), 0.3),
                                            (1.35, 70, (255, 120, 80), 0.15), (1.75, 120, (120, 255, 190), 0.1),
                                            (2.1, 34, (255, 220, 160), 0.22)]):
            p = ac.paint(col, a * strength, blur=r * 0.35 * U, stroke=False)
            c.drawCircle(sx + vx * f, sy + vy * f, r * U, p)


_VIG = None
_GRAIN = None


def smooth_arr(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def _vignette():
    global _VIG
    if _VIG is None:
        d = np.sqrt(((_XX - CX) / (W * 0.62)) ** 2 + ((_YY - CY) / (H * 0.62)) ** 2)
        _VIG = (1 - smooth_arr(d - 0.35)).astype(np.float32)        # 0..1，越靠边越小
    return _VIG


def _grains():
    global _GRAIN
    if _GRAIN is None:
        rng = np.random.default_rng(99)
        g = [cv2.GaussianBlur(rng.normal(0, 1, (H + 64, W + 64)).astype(np.float32), (0, 0), 0.65) for _ in range(4)]
        _GRAIN = [x / x.std() for x in g]
    return _GRAIN


def finish(img, exposure=1.0, grain=0.010, seed=0, vignette=0.55, sat=1.0, contrast=1.0,
           gain=(1.0, 1.0, 1.0), offset=(0.0, 0.0, 0.0)):
    """曝光 → ACES → sRGB → 色彩矩阵（饱和度/对比/色偏）→ 暗角 → 颗粒 → uint8。"""
    e = float(exposure)
    x = cv2.transform(img, np.float32([[e, 0, 0], [0, e, 0], [0, 0, e]]))
    x = cv2.max(x, (0.0, 0.0, 0.0, 0.0))
    num = cv2.multiply(x, cv2.add(cv2.multiply(x, _s4(2.51)), _s4(0.03)))
    den = cv2.add(cv2.multiply(x, cv2.add(cv2.multiply(x, _s4(2.43)), _s4(0.59))), _s4(0.14))
    s = cv2.min(cv2.divide(num, den), _s4(1.0))
    s = cv2.pow(s, 1 / 2.2)
    lw = np.float32([0.2126, 0.7152, 0.0722])
    S = (1 - sat) * np.tile(lw, (3, 1)) + sat * np.eye(3, dtype=np.float32)
    M = contrast * np.diag(np.float32(gain)) @ S
    off = 0.5 * (1 - contrast) + np.float32(offset)
    s = cv2.transform(s, np.hstack([M, off[:, None]]).astype(np.float32))
    if vignette:
        v = 1 - (1 - _vignette()) * vignette
        s = cv2.multiply(s, cv2.merge([v, v, v]))
    if grain > 0:
        rng = np.random.default_rng(seed)
        g = _grains()[int(rng.integers(0, 4))]
        ox, oy = int(rng.integers(0, 64)), int(rng.integers(0, 64))
        l = np.clip(cv2.cvtColor(s, cv2.COLOR_RGB2GRAY), 0, 1)
        gw = g[oy:oy + H, ox:ox + W] * (grain * (0.3 + 2.8 * l * (1 - l)))
        s = cv2.add(s, cv2.merge([gw, gw, gw]))
    return cv2.convertScaleAbs(s, alpha=255.0, beta=0.5)
