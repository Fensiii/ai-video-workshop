"""上海下雪：薛之谦《认真的雪》竖屏歌词视频。

外滩视角的陆家嘴夜景（东方明珠、金茂、环球金融中心、上海中心）+ 黄浦江倒影 + 游船 + 大雪，
近处江堤护墙上的积雪随歌词越积越厚；“突然飘雪”起雪变大。
用法：
  python3 render.py --still 2 9 15 22        # 出静帧 → stills/
  python3 render.py --seg 0 200 seg0.mp4      # 渲染帧区间（无声）
"""
import json, math, os, sys, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.environ.get("FONT_DIR", os.path.join(HERE, "fonts"))
F_SUB = os.path.join(FONT_DIR, "NotoSerifSC_600SemiBold.ttf")
F_UI = os.path.join(FONT_DIR, "NotoSansSC_500Medium.ttf")

W, H, FPS, DUR = 1080, 1920, 30, 24.5
M = 60                      # 镜头运动余量
CW, CH = W + 2 * M, H + 2 * M
SS = 2                      # 静态天际线超采样
F = 1750.0                  # 焦距（像素），决定建筑透视大小
VEX = 1.12                  # 竖向略夸张
Y_BANK = 1200               # 对岸建筑底线（画面坐标）
Y_WALL = 1650               # 近处江堤护墙顶面远边
WALL_TOP = 46               # 护墙顶面厚度（像素）
SUB_Y = 1340
LAMP = (-160.0, 1720.0)     # 画外左下角路灯
HAZE = np.array([62, 58, 86], np.float32)

LINES = json.load(open(os.path.join(HERE, "lines.json"), encoding="utf-8"))["lines"]

BODY = [(24, 27, 40), (30, 30, 44), (20, 24, 36), (34, 32, 48)]
WIN = [(255, 214, 150), (226, 234, 255), (255, 236, 200), (170, 210, 255)]
EDGE = [(110, 220, 255), (255, 120, 200), (255, 205, 120), (235, 240, 255), (150, 140, 255)]


def smooth(e0, e1, x):
    x = min(max((x - e0) / (e1 - e0), 0.0), 1.0)
    return x * x * (3 - 2 * x)


def haze_k(d):
    return 1 - math.exp(-d / 4200)


def mix(c, k):
    c = np.asarray(c, np.float32)
    return tuple(int(v) for v in np.clip(c * (1 - k) + HAZE * k, 0, 255))


def blur_noise(h, w, sigma, rng):
    a = Image.fromarray(rng.uniform(0, 255, (h, w)).astype(np.uint8)).filter(ImageFilter.GaussianBlur(sigma))
    x = np.asarray(a).astype(np.float32)
    return (x - x.mean()) / (x.std() + 1e-6)


def gblur(arr, r):
    """float 数组 (h,w,3) 高斯模糊（经 uint8）。"""
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r))
    return np.asarray(im).astype(np.float32)


def P(x, y):
    """画面坐标 → 超采样画布坐标。"""
    return ((x + M) * SS, (y + M) * SS)


_fonts = {}


def font(path, size):
    if (path, size) not in _fonts:
        _fonts[(path, size)] = ImageFont.truetype(path, size)
    return _fonts[(path, size)]


# ---------------------------------------------------------------- 天空
def make_sky():
    rng = np.random.default_rng(1)
    stops = [(0, (9, 12, 26)), (500, (22, 28, 52)), (900, (44, 48, 80)), (1120, (92, 82, 106)),
             (1200, (132, 108, 116)), (1270, (56, 50, 66)), (1920, (14, 16, 24))]
    ys = np.arange(CH) - M
    col = np.stack([np.interp(ys, [s[0] for s in stops], [s[1][c] for s in stops]) for c in range(3)], 1)
    img = np.repeat(col[:, None, :], CW, axis=1)
    blot = blur_noise(CH // 4, CW // 4, 18, rng)
    blot = np.asarray(Image.fromarray(((blot * 40) + 128).clip(0, 255).astype(np.uint8)).resize((CW, CH), Image.BILINEAR)).astype(np.float32)
    img = img * (1 + (blot[..., None] - 128) / 40 * 0.07)
    return img


# ---------------------------------------------------------------- 地标
class Tower:
    def __init__(self, cx, d):
        self.cx, self.d = cx, d
        self.s = F / d
        self.vs = self.s * VEX
        self.k = haze_k(d) * 0.7

    def pt(self, xm, hm):
        return P(self.cx + xm * self.s, Y_BANK - hm * self.vs)

    def poly(self, dr, pts, col):
        dr.polygon([self.pt(x, h) for x, h in pts], fill=col)

    def line(self, dr, a, b, col, wpx=1.0):
        dr.line([self.pt(*a), self.pt(*b)], fill=col, width=max(1, int(round(wpx * SS))))

    def col(self, c, light=False):
        return mix(c, self.k * (0.45 if light else 1.0))


def sphere_sprite(rpx, hi, lo, k, rows=5, cols=12):
    R = int(math.ceil(rpx)) + 2
    yy, xx = (np.mgrid[0:2 * R, 0:2 * R].astype(np.float32) + 0.5 - R) / rpx
    r2 = xx ** 2 + yy ** 2
    a = np.clip((1 - np.sqrt(r2)) * rpx, 0, 1)
    z = np.sqrt(np.clip(1 - r2, 0, 1))
    hi, lo = np.array(hi, np.float32), np.array(lo, np.float32)
    col = lo + (hi - lo) * (0.2 + 0.8 * z ** 0.6)[..., None]
    lat = np.arcsin(np.clip(yy, -1, 1))
    lon = np.arctan2(xx, z + 1e-6)
    band = np.abs(np.sin(lat * rows)) > 0.9
    dots = np.cos(lon * cols) > 0.4
    lights = (band & dots & (r2 < 0.9)).astype(np.float32) * (0.5 + 0.5 * z)
    col = col + (np.array([255, 236, 248], np.float32) - col) * lights[..., None] * 0.8
    col = col * (1 - k) + HAZE * k
    return Image.fromarray(np.dstack([np.clip(col, 0, 255), a * 255]).astype(np.uint8), "RGBA")


def draw_opt(img, dr, cx, d):
    """东方明珠：斜撑 + 三柱 + 下球 + 五小球 + 上球 + 太空舱 + 天线。"""
    T = Tower(cx, d)
    body = T.col((112, 84, 138), True)
    lit = T.col((246, 226, 255), True)
    for sg in (-1, 1):
        T.poly(dr, [(sg * 46, 0), (sg * 38, 0), (sg * 15, 74), (sg * 23, 74)], body)
        T.line(dr, (sg * 42, 2), (sg * 19, 72), lit, 1.2)
    T.poly(dr, [(-3.5, 0), (3.5, 0), (3.5, 290), (-3.5, 290)], T.col((70, 54, 92), True))
    for xo in (-13, 13):
        T.poly(dr, [(xo - 4.5, 0), (xo + 4.5, 0), (xo + 4.5, 292), (xo - 4.5, 292)], body)
        T.line(dr, (xo, 4), (xo, 288), lit, 1.4)
    T.poly(dr, [(-4.5, 290), (4.5, 290), (4.5, 338), (-4.5, 338)], body)
    T.line(dr, (0, 292), (0, 336), lit, 1.2)
    T.poly(dr, [(-2.8, 348), (2.8, 348), (0.7, 468), (-0.7, 468)], T.col((200, 190, 220), True))
    for hm in (372, 400, 428):
        T.poly(dr, [(-4, hm), (4, hm), (4, hm + 4), (-4, hm + 4)], T.col((250, 240, 255), True))
    pink_hi, pink_lo = (255, 120, 196), (122, 30, 98)
    spheres = [(0, 93, 25, 5, 14), (-13, 130, 6.5, 2, 6), (13, 152, 6.5, 2, 6), (-13, 174, 6.5, 2, 6),
               (13, 196, 6.5, 2, 6), (0, 218, 6.5, 2, 6), (0, 272, 22.5, 5, 13), (0, 343, 8, 2, 6)]
    for xm, hm, rm, rows, cols in spheres:
        rpx = rm * T.s * SS
        sp = sphere_sprite(rpx, pink_hi, pink_lo, T.k * 0.5, rows, cols)
        x, y = T.pt(xm, hm)
        img.alpha_composite(sp, (int(x - sp.width / 2), int(y - sp.height / 2)))
    return [T.pt(0, 470)]


def draw_jinmao(dr, cx, d):
    """金茂：宝塔式逐层收分 + 金色冠顶 + 尖塔。"""
    T = Tower(cx, d)
    body = T.col((40, 36, 44))
    gold = T.col((255, 206, 128), True)
    goldd = T.col((190, 150, 92), True)
    h, th = 0.0, 46.0
    for i in range(13):
        wb = 54 - i * 1.9
        wt = wb - 2.6
        T.poly(dr, [(-wb / 2, h), (wb / 2, h), (wt / 2, h + th), (-wt / 2, h + th)], body)
        T.line(dr, (-wb / 2 - 0.8, h + 0.6), (wb / 2 + 0.8, h + 0.6), gold, 1.2)
        for fx in (-0.36, -0.12, 0.12, 0.36):
            T.line(dr, (fx * wb, h + 2), (fx * wt, h + th - 1), goldd, 0.8)
        h += th
        th *= 0.885
    for w_, hh in ((28, 11), (22, 10), (16, 9), (11, 8)):
        T.poly(dr, [(-w_ / 2, h), (w_ / 2, h), (w_ / 2 - 1.5, h + hh), (-w_ / 2 + 1.5, h + hh)], T.col((255, 222, 160), True))
        T.line(dr, (-w_ / 2, h + 0.5), (w_ / 2, h + 0.5), T.col((255, 245, 215), True), 1.2)
        h += hh
    T.poly(dr, [(-1.8, h), (1.8, h), (0.4, 421), (-0.4, 421)], T.col((230, 200, 150), True))
    return [T.pt(0, 423)]


def draw_swfc(dr, cx, d, sky):
    """环球金融中心：微收腰的板楼 + 顶部倒梯形“开瓶器”洞口。"""
    T = Tower(cx, d)
    body = T.col((30, 34, 50))
    edge = T.col((200, 228, 255), True)
    hw = lambda h: 29 - 3.5 * math.sin(math.pi * h / 492)
    hs = np.linspace(0, 492, 40)
    T.poly(dr, [(-hw(h), h) for h in hs] + [(hw(h), h) for h in hs[::-1]], body)
    # 稀疏窗灯
    rng = np.random.default_rng(41)
    for hm in np.arange(8, 430, 4.2):
        for xm in np.arange(-24, 24, 3.4):
            if rng.random() < 0.22:
                T.poly(dr, [(xm, hm), (xm + 1.8, hm), (xm + 1.8, hm + 1.6), (xm, hm + 1.6)], T.col((215, 228, 255), True))
    for sg in (-1, 1):
        T.line(dr, (sg * hw(0), 0), (sg * hw(246), 246), edge, 1.0)
        T.line(dr, (sg * hw(246), 246), (sg * hw(492), 492), edge, 1.0)
    T.line(dr, (-hw(492), 491.5), (hw(492), 491.5), edge, 1.2)
    ap = [(-11, 444), (11, 444), (19, 478), (-19, 478)]
    yy = int(Y_BANK - 460 * T.vs) + M
    sky_c = tuple(int(v) for v in sky[yy, int(cx) + M] * 1.15)
    T.poly(dr, ap, sky_c)
    for a, b in zip(ap, ap[1:] + ap[:1]):
        T.line(dr, a, b, T.col((150, 210, 255), True), 1.6)
    return [T.pt(-hw(492) + 1, 493), T.pt(hw(492) - 1, 493)]


def draw_shtower(dr, cx, d):
    """上海中心：扭转收分 + 分区灯带 + 斜切冠顶。"""
    T = Tower(cx, d)
    body = T.col((28, 36, 54))
    band = T.col((214, 232, 255), True)
    hw = lambda h: 41 - 19 * (h / 600) ** 1.15
    ox = lambda h: 6 * (h / 600)
    hs = np.linspace(0, 596, 50)
    T.poly(dr, [(ox(h) - hw(h), h) for h in hs] + [(ox(596) - hw(596), 604), (ox(596) + hw(596), 632)] +
           [(ox(h) + hw(h), h) for h in hs[::-1]], body)
    rng = np.random.default_rng(42)
    for hm in np.arange(6, 590, 4.4):
        w = hw(hm)
        for xm in np.arange(-w + 2, w - 2, 3.2):
            if rng.random() < 0.16:
                T.poly(dr, [(ox(hm) + xm, hm), (ox(hm) + xm + 1.6, hm), (ox(hm) + xm + 1.6, hm + 1.5), (ox(hm) + xm, hm + 1.5)],
                       T.col((205, 222, 255), True))
    for hb in range(68, 590, 68):
        T.line(dr, (ox(hb) - hw(hb), hb), (ox(hb) + hw(hb), hb), band, 1.3)
    T.line(dr, (ox(0) + hw(0) * 0.2, 0), (ox(590) + hw(590) * 0.85, 590), T.col((170, 205, 255), True), 1.0)
    # 冠顶
    c_l, c_r = ox(596) - hw(596), ox(596) + hw(596)
    T.poly(dr, [(c_l, 596), (c_r, 596), (c_r, 630), (c_l, 603)], T.col((150, 180, 230), True))
    for f_ in (0.25, 0.5, 0.75):
        T.line(dr, (c_l + (c_r - c_l) * f_, 597), (c_l + (c_r - c_l) * f_, 603 + 27 * f_), T.col((235, 245, 255), True), 0.9)
    return [T.pt(c_r - 1, 633)]


def draw_generic(dr, xc, d, wm, hm, rng):
    s = F / d
    vs, k = s * VEX, haze_k(d)
    wpx, hpx = wm * s, hm * vs
    x0, x1 = xc - wpx / 2, xc + wpx / 2
    yb, yt = Y_BANK + 2, Y_BANK - hpx
    body = mix(BODY[rng.integers(len(BODY))], k)
    roof = rng.choice(["flat", "slant", "step", "spire", "crown"], p=[.34, .2, .2, .16, .1])
    if roof == "slant":
        drop = rng.uniform(0.15, 0.5) * wpx
        yl, yr = (yt, yt + drop) if rng.random() < .5 else (yt + drop, yt)
        dr.polygon([P(x0, yb), P(x0, yl), P(x1, yr), P(x1, yb)], fill=body)
        roof_y = lambda x: yl + (yr - yl) * (x - x0) / wpx
    elif roof == "step":
        ys = yt + 0.22 * hpx
        ins = wpx * rng.uniform(0.15, 0.25)
        dr.rectangle([P(x0, ys), P(x1, yb)], fill=body)
        dr.rectangle([P(x0 + ins, yt), P(x1 - ins, ys)], fill=body)
        roof_y = lambda x: yt if x0 + ins <= x <= x1 - ins else ys
    else:
        dr.rectangle([P(x0, yt), P(x1, yb)], fill=body)
        roof_y = lambda x: yt
        if roof == "spire":
            sh = hpx * rng.uniform(0.08, 0.2)
            dr.line([P(xc, yt), P(xc, yt - sh)], fill=body, width=SS)
            dr.ellipse([P(xc - 1.1, yt - sh - 1.1), P(xc + 1.1, yt - sh + 1.1)], fill=mix((255, 70, 60), k * 0.5))
        elif roof == "crown":
            cw_, ch_ = wpx * 0.5, max(3, hpx * 0.05)
            dr.rectangle([P(xc - cw_ / 2, yt - ch_), P(xc + cw_ / 2, yt)], fill=mix(EDGE[rng.integers(len(EDGE))], k * 0.5))
    style = rng.choice(["grid", "bands", "stripes", "dark"], p=[.5, .25, .15, .1])
    fp, cp = max(2.6, 3.8 * vs), max(2.2, 3.4 * s)
    wc = np.array(WIN[rng.integers(len(WIN))], np.float32)
    if style == "grid":
        plit = rng.uniform(.15, .55)
        y = yb - fp
        while y > yt + 2:
            x = x0 + cp * 0.4
            while x + cp * 0.6 < x1:
                if y > roof_y(x) + 2 and y > roof_y(x + cp * .55) + 2 and rng.random() < plit:
                    dr.rectangle([P(x, y), P(x + cp * .55, y + fp * .5)], fill=mix(wc * rng.uniform(.45, 1), k * .45))
                x += cp
            y -= fp
    elif style == "bands":
        n = int(rng.integers(2, 5))
        c = mix(np.array((226, 234, 255)) * rng.uniform(.5, .85), k * .45)
        y, i = yb - fp, 0
        while y > yt + 3:
            if i % n == 0:
                xs = [x for x in np.arange(x0 + 1, x1 - 1, 1.0) if y > roof_y(x) + 2]
                if xs:
                    dr.rectangle([P(xs[0], y), P(xs[-1], y + fp * .35)], fill=c)
            y -= fp
            i += 1
    elif style == "stripes":
        c = mix(np.array(EDGE[rng.integers(len(EDGE))]) * .6, k * .45)
        x = x0 + cp
        while x < x1 - 1:
            dr.line([P(x, yb), P(x, roof_y(x) + 3)], fill=c, width=SS)
            x += cp * 2.2
    if rng.random() < 0.3:
        c = mix(EDGE[rng.integers(len(EDGE))], k * .4)
        dr.line([P(x0, yb), P(x0, roof_y(x0))], fill=c, width=SS)
        dr.line([P(x1, yb), P(x1, roof_y(x1))], fill=c, width=SS)


def make_skyline():
    sky = make_sky()
    img = Image.fromarray(sky.astype(np.uint8)).resize((CW * SS, CH * SS), Image.BILINEAR).convert("RGBA")
    dr = ImageDraw.Draw(img)
    rng = np.random.default_rng(7)
    LM = {"opt": (200, 934), "jm": (465, 1490), "swfc": (760, 1802), "st": (950, 1642)}
    beacons = []
    # 远景
    for _ in range(46):
        draw_generic(dr, rng.uniform(-40, W + 40), rng.uniform(2600, 3800), rng.uniform(30, 60), rng.uniform(80, 250), rng)
    for _ in range(30):
        draw_generic(dr, rng.uniform(-40, W + 40), rng.uniform(1900, 2500), rng.uniform(30, 60), rng.uniform(100, 280), rng)
    beacons += draw_swfc(dr, *LM["swfc"], sky)
    for _ in range(8):
        draw_generic(dr, rng.uniform(-40, W + 40), rng.uniform(1660, 1790), rng.uniform(30, 55), rng.uniform(90, 200), rng)
    beacons += draw_shtower(dr, *LM["st"])
    beacons += draw_jinmao(dr, *LM["jm"])
    for _ in range(22):
        x = rng.uniform(-40, W + 40)
        near_lm = min(abs(x - LM[k][0]) for k in ("jm", "swfc", "st")) < 70
        hm = rng.uniform(70, 130) if near_lm else rng.uniform(80, 210)
        draw_generic(dr, x, rng.uniform(1100, 1450), rng.uniform(34, 70), hm, rng)
    beacons += draw_opt(img, dr, *LM["opt"])
    for _ in range(12):
        x = rng.uniform(-40, W + 40)
        if abs(x - LM["opt"][0]) < 60:
            continue
        draw_generic(dr, x, rng.uniform(700, 950), rng.uniform(30, 70), rng.uniform(18, 50), rng)
    # 对岸江边：树影 + 灯串 + 亲水平台灯带
    xs = np.arange(-M, W + M, 2.0)
    tops = Y_BANK - 7 - 6 * (0.5 + 0.5 * np.sin(xs * 0.07) * np.sin(xs * 0.013 + 1))
    dr.polygon([P(-M, Y_BANK + 3)] + [P(x, y) for x, y in zip(xs, tops)] + [P(W + M, Y_BANK + 3)], fill=mix((14, 16, 24), 0.2))
    for x in np.arange(-M, W + M, 9.0):
        c = (255, 214, 150) if rng.random() < .6 else (190, 220, 255)
        y = Y_BANK - rng.uniform(2, 9)
        dr.ellipse([P(x - .9, y - .9), P(x + .9, y + .9)], fill=mix(c, 0.25))
    dr.line([P(-M, Y_BANK + 2.5), P(W + M, Y_BANK + 2.5)], fill=mix((170, 190, 245), 0.2), width=2 * SS)
    small = img.convert("RGB").resize((CW, CH), Image.LANCZOS)
    arr = np.asarray(small).astype(np.float32)
    # 泛光：雪夜里灯光晕得很开
    lum = arr.max(axis=2)
    bright = arr * np.clip((lum - 140) / 115, 0, 1)[..., None]
    arr = arr + 0.6 * gblur(bright, 3) + 0.5 * gblur(bright, 14) + 0.45 * gblur(bright, 45)
    rng2 = np.random.default_rng(8)
    ys = (np.arange(CH) - M)[:, None].astype(np.float32)
    n = blur_noise(CH // 4, CW // 4, 10, rng2)
    n = np.asarray(Image.fromarray((n * 40 + 128).clip(0, 255).astype(np.uint8)).resize((CW, CH), Image.BILINEAR)).astype(np.float32)
    m = 0.30 * np.exp(-((ys - (Y_BANK - 40)) / 110) ** 2) + 0.10 * np.exp(-((ys - (Y_BANK - 300)) / 260) ** 2)
    m = np.clip(m * (1 + (n - 128) / 40 * 0.35), 0, 0.5) * (ys < Y_BANK + 4)
    arr = arr * (1 - m[..., None]) + np.array([150, 132, 158], np.float32) * m[..., None]
    beacons = [(x / SS - M, y / SS - M) for x, y in beacons]
    return np.clip(arr, 0, 255), beacons


# ---------------------------------------------------------------- 江面
class River:
    def __init__(self, bg):
        self.y0 = Y_BANK + 3
        self.R = Y_WALL - self.y0
        dl = np.arange(self.R, dtype=np.float32) + 3
        src = np.clip(np.round(Y_BANK + M - 1 - dl * 0.8).astype(int), 0, CH - 1)
        refl = bg[src].copy()
        # 竖向拉丝 + 轻微横向模糊
        cs = np.cumsum(np.pad(refl, ((6, 6), (0, 0), (0, 0)), mode="edge"), axis=0)
        refl = (cs[12:] - cs[:-12])[: self.R] / 12
        refl = gblur(refl, 1.2)
        refl = 255 * (refl / 255) ** 1.5 * 0.85
        fade = (1 - 0.45 * (dl / self.R))[:, None, None]
        self.refl = refl * fade
        top, bot = np.array([46, 40, 60], np.float32), np.array([9, 12, 20], np.float32)
        g = (dl / self.R) ** 0.5
        self.base = (top[None, :] * (1 - g[:, None]) + bot[None, :] * g[:, None])[:, None, :]
        self.dl = dl
        rng = np.random.default_rng(12)
        jit = np.convolve(rng.normal(0, 1, self.R + 40), np.ones(9) / 9, mode="same")[20:20 + self.R]
        self.phi = 38 * np.log1p(dl / 6) + 2.2 * jit
        self.amp = 0.8 + 9 * (dl / self.R) ** 1.4
        self.cols = np.arange(CW)

    def render(self, t, extra=None):
        refl = self.refl if extra is None else self.refl + extra
        shift = self.amp * (np.sin(self.phi - 2.3 * t) + 0.5 * np.sin(1.7 * self.phi + 1.4 * t + 1.0))
        idx = np.clip(self.cols[None, :] - np.round(shift)[:, None].astype(int), 0, CW - 1)
        r = np.take_along_axis(refl, idx[..., None].repeat(3, axis=2), axis=1)
        mod = 0.78 + 0.22 * np.sin(1.3 * self.phi - 3.1 * t)
        mod = mod * (0.88 + 0.12 * np.sin(0.45 * self.phi + 1.7 * t))
        return np.clip(self.base + r * mod[:, None, None], 0, 255)


def make_boat():
    """浦江游船：双层甲板、暖色舷窗、彩色灯带。返回 (rgba, glow)。"""
    L, Hh = 250, 60
    S = 3
    im = Image.new("RGBA", (L * S, Hh * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    p = lambda pts: [(x * S, y * S) for x, y in pts]
    d.polygon(p([(0, 42), (L, 40), (L - 14, 58), (12, 58)]), fill=(14, 16, 24, 255))
    d.rectangle([10 * S, 22 * S, (L - 22) * S, 42 * S], fill=(36, 36, 50, 255))
    d.rectangle([44 * S, 8 * S, (L - 66) * S, 22 * S], fill=(42, 40, 56, 255))
    for x in range(16, L - 28, 9):
        d.rectangle([x * S, 27 * S, (x + 5) * S, 35 * S], fill=(255, 212, 140, 255))
    for x in range(50, L - 72, 8):
        d.rectangle([x * S, 12 * S, (x + 4) * S, 18 * S], fill=(235, 238, 255, 255))
    d.line([(44 * S, 8 * S), ((L - 66) * S, 8 * S)], fill=(110, 225, 255, 255), width=2 * S)
    d.line([(10 * S, 22 * S), ((L - 22) * S, 22 * S)], fill=(255, 110, 200, 255), width=2 * S)
    d.line([(0, 42 * S), (L * S, 40 * S)], fill=(255, 205, 120, 255), width=S)
    d.ellipse([(L - 30) * S, 0, (L - 26) * S, 4 * S], fill=(255, 255, 255, 255))
    im = im.resize((L, Hh), Image.LANCZOS)
    arr = np.asarray(im).astype(np.float32)
    rgb = arr[..., :3] * (arr[..., 3:] / 255)
    bright = rgb * np.clip((rgb.max(axis=2) - 150) / 105, 0, 1)[..., None]
    pad = 30
    bp = np.pad(bright, ((pad, pad), (pad, pad), (0, 0)))
    glow = 0.7 * gblur(bp, 3) + 0.6 * gblur(bp, 12)
    return im, glow, pad


# ---------------------------------------------------------------- 江堤护墙 + 积雪
def make_wall():
    rng = np.random.default_rng(3)
    y0 = Y_WALL + M
    h = CH - y0
    yy = np.arange(h)[:, None].astype(np.float32)
    xx = np.arange(CW)[None, :].astype(np.float32)
    top = yy < WALL_TOP
    col = np.where(top[..., None], np.array([50, 51, 60], np.float32), np.array([17, 18, 24], np.float32)) * np.ones((h, CW, 1), np.float32)
    tex = blur_noise(h, CW, 1.2, rng)[..., None] * 2.5 + blur_noise(h, CW, 12, rng)[..., None] * 3
    col = col + tex
    edge = (yy >= WALL_TOP) & (yy < WALL_TOP + 3)
    col = np.where(edge[..., None], col * 1.6 + 8, col)
    for sx in np.arange(150, CW, 230):  # 石块竖缝
        col[WALL_TOP + 3:, int(sx):int(sx) + 2] *= 0.7
    col[WALL_TOP + 120:WALL_TOP + 122] *= 0.7
    lx, ly = LAMP[0] + M, LAMP[1] + M - y0
    lamp = np.exp(-((xx - lx) ** 2 + (yy - ly) ** 2) / (2 * 420.0 ** 2))
    col = col + lamp[..., None] * np.array([46, 30, 14], np.float32)
    return np.clip(col, 0, 255)


class Snowcap:
    def __init__(self):
        rng = np.random.default_rng(5)
        self.y0 = Y_WALL + M - 40
        self.h = WALL_TOP + 40 + 14
        pt = 0.65 * blur_noise(WALL_TOP + 14, CW, 1.3, rng) + 0.35 * blur_noise(WALL_TOP + 14, CW, 7, rng)
        self.patch = (pt - pt.min()) / (np.ptp(pt) + 1e-6)
        self.n1 = blur_noise(1, CW * 4, 30, rng)[0, ::4]
        self.n1 = (self.n1 - self.n1.min()) / (np.ptp(self.n1) + 1e-6)
        self.n2 = blur_noise(1, CW * 4, 50, rng)[0, ::4]
        self.n2 = (self.n2 - self.n2.min()) / (np.ptp(self.n2) + 1e-6)
        xx = np.arange(CW, dtype=np.float32)
        self.warm = np.exp(-((xx - LAMP[0] - M) ** 2) / (2 * 520.0 ** 2))
        self.sparkle = (rng.random((self.h, CW)) > 0.996).astype(np.float32)

    def render(self, t, region):
        """region: 画布行 [y0, y0+h) 的 float 数组，原地叠加积雪。"""
        cover = 0.2 + 0.85 * smooth(0.5, 17, t)
        thick = 2 + 7 * smooth(2, 14, t) + 15 * smooth(14, 24.5, t)
        yy = np.arange(self.h, dtype=np.float32)[:, None]
        far = 40.0
        # 顶面斑块（cover 越大盖得越满）+ 近边垂下的雪檐
        a = np.zeros((self.h, CW), np.float32)
        rows = np.arange(WALL_TOP + 14, dtype=np.float32)[:, None]
        depth = WALL_TOP + 2 + thick * 0.35 * (0.6 + 0.4 * self.n1[None, :])
        a[40:] = np.clip((cover - self.patch) * 14, 0, 1) * np.clip(depth - rows, 0, 1)
        # 远边鼓起的雪冠
        ytop = far - thick * (0.62 + 0.38 * self.n1)
        capa = np.clip((cover - 0.3 * self.n2) * 2.5, 0, 1)
        cap = np.clip(yy - ytop[None, :] + 1, 0, 1) * (yy < far + 2) * capa[None, :]
        a = np.clip(np.maximum(a, cap), 0, 1)
        # 颜色：上亮下暗，左侧暖光
        g = np.clip((yy - ytop[None, :]) / (thick + 8), 0, 1)
        c_hi, c_lo = np.array([232, 238, 250], np.float32), np.array([150, 162, 190], np.float32)
        col = c_hi * (1 - 0.5 * g[..., None]) + c_lo * 0.5 * g[..., None]
        col = col + self.warm[None, :, None] * np.array([30, 6, -30], np.float32)
        col = col + self.sparkle[..., None] * 60
        region[:] = region * (1 - a[..., None]) + col * a[..., None]


# ---------------------------------------------------------------- 雪花
def flake_sprite(r, soft):
    s = int(r * 6 + 6)
    yy, xx = np.mgrid[0:s, 0:s].astype(np.float32) - (s - 1) / 2
    d = np.sqrt(xx ** 2 + yy ** 2)
    if soft:  # 近景虚焦：软边圆盘
        a = np.exp(-(d / r) ** 4 * 1.2) * 0.8
    else:
        a = np.exp(-d ** 2 / (2 * (r * 0.7) ** 2))
    return a


class Snow:
    def __init__(self):
        rng = np.random.default_rng(33)
        self.fl = []
        layers = [  # 数量, 半径, 速度, 透明度, 软
            (600, (0.8, 1.4), (35, 60), (.35, .65), False),
            (380, (1.6, 2.6), (70, 120), (.6, .95), False),
            (80, (3.5, 6.5), (140, 220), (.55, .9), False),
            (7, (14, 22), (240, 320), (.14, .24), True),
        ]
        for n, rr, vv, aa, soft in layers:
            for _ in range(n):
                self.fl.append(dict(x0=rng.uniform(-100, W + 100), y0=rng.uniform(0, H + 200), v=rng.uniform(*vv),
                                    r=rng.uniform(*rr), amp=rng.uniform(6, 30), ph=rng.uniform(0, 6.28),
                                    a=rng.uniform(*aa), th=rng.random(), soft=soft))
        self.cache = {}

    def sprite(self, r, soft, aq, wq):
        key = (round(r * 2) / 2, soft, aq, wq)
        if key not in self.cache:
            a = flake_sprite(key[0], soft) * (aq / 10)
            warm = wq / 3
            c = np.array([236, 240, 252], np.float32) * (1 - warm) + np.array([255, 214, 160], np.float32) * warm
            rgb = np.ones(a.shape + (3,), np.float32) * c
            self.cache[key] = Image.fromarray(np.dstack([rgb, np.clip(a, 0, 1) * 255]).astype(np.uint8), "RGBA")
        return self.cache[key]

    def draw(self, fr, t, dens):
        lx, ly = LAMP
        for f in self.fl:
            if f["th"] > dens:
                continue
            v = f["v"]
            y = (f["y0"] + v * t) % (H + 200) - 100
            x = f["x0"] + 32 * t * (v / 150) + f["amp"] * math.sin(t * (0.6 + v / 300) + f["ph"])
            x = (x + 100) % (W + 200) - 100
            w = math.exp(-((x - lx) ** 2 + (y - ly) ** 2) / (2 * 560.0 ** 2))
            a = min(1.0, f["a"] * (1 + 0.8 * w))
            sp = self.sprite(f["r"], f["soft"], max(1, int(round(a * 10))), int(w * 3.99))
            px, py = int(x - sp.width / 2), int(y - sp.height / 2)
            if px < 0 or py < 0 or px + sp.width > W or py + sp.height > H:
                continue
            fr.alpha_composite(sp, (px, py))


def make_veil():
    """随风飘过的雪幕（大块低频噪声），整片斜向移动。"""
    rng = np.random.default_rng(11)
    hh, ww = (H + 2400) // 8, (W + 1000) // 8
    n = blur_noise(hh, ww, 5, rng)
    a = np.clip((n - 0.3) * 0.05, 0, 0.09)
    im = Image.fromarray((a * 255).astype(np.uint8)).resize((ww * 8, hh * 8), Image.BILINEAR)
    return im


def make_vignette():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.5) / (H * 0.6)) ** 2)
    a = np.clip((r - 0.6) / 0.6, 0, 1) ** 1.5 * 0.7
    col = np.zeros((H, W, 3)); col[:] = (4, 6, 12)
    return Image.fromarray(np.dstack([col, a * 255]).astype(np.uint8), "RGBA")


# ---------------------------------------------------------------- 文字
BLUR = [0, 1.0, 2.0, 3.5, 5.5]
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


TRACK = 8


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
    for ch, col in items:
        out.append((ch, x, SUB_Y - size * 0.7, col, size))
        x += f.getlength(ch) + TRACK
    return out


def draw_line(fr, t, t0, t1, text, size):
    if t < t0 - 0.05 or t > t1 + 0.05:
        return
    items = layout(text, size)
    n = len(items)
    st = min(0.06, 0.55 / max(n, 1))
    q = smooth(t1 - 0.4, t1, t)
    for i, (ch, x, y, col, sz) in enumerate(items):
        p = smooth(t0 + i * st, t0 + i * st + 0.45, t)
        a = p * (1 - q)
        if a <= 0.01:
            continue
        bl = min(4, int(round(4 * max(1 - p, q))))
        g, pad = glyph(ch, sz, col, bl)
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
    w1 = f1.getlength(t1)
    x1 = xr - w1
    d.text((x1, 40), t1, font=f1, fill=(255, 255, 255, 240))
    # 定位图标
    cx, cy = x1 - 26, 62
    d.ellipse([cx - 12, cy - 16, cx + 12, cy + 8], fill=(255, 255, 255, 240))
    d.polygon([(cx - 10, cy), (cx + 10, cy), (cx, cy + 20)], fill=(255, 255, 255, 240))
    d.ellipse([cx - 5, cy - 9, cx + 5, cy + 1], fill=(0, 0, 0, 0))
    w2 = f2.getlength(t2)
    d.text((xr - w2, 100), t2, font=f2, fill=(235, 238, 250, 215))
    a = im.getchannel("A").filter(ImageFilter.GaussianBlur(6)).point(lambda v: int(v * 0.7))
    z = Image.new("L", im.size, 0)
    out = Image.merge("RGBA", [z, z, z, a])
    out.alpha_composite(im)
    return out


# ---------------------------------------------------------------- 合成
class Scene:
    def __init__(self):
        self.bg, self.beacons = make_skyline()
        self.river = River(self.bg)
        wall = make_wall()
        self.bg[Y_WALL + M:] = wall
        self.boat, self.boat_glow, self.boat_pad = make_boat()
        b = np.asarray(self.boat).astype(np.float32)
        brgb = b[..., :3] * (b[..., 3:] / 255)
        self.boat_refl = np.flipud(brgb + self.boat_glow[self.boat_pad:-self.boat_pad, self.boat_pad:-self.boat_pad]) * 0.55
        self.cap = Snowcap()
        self.snow = Snow()
        self.veil = make_veil()
        self.vig = make_vignette()
        self.tags = make_tags()
        self.white = Image.new("RGB", (W, H), (226, 232, 244))
        yy, xx = np.mgrid[-14:15, -14:15].astype(np.float32)
        self.beacon_spr = np.exp(-(xx ** 2 + yy ** 2) / (2 * 4.0 ** 2))[..., None] * np.array([255, 50, 40], np.float32) \
            + np.exp(-(xx ** 2 + yy ** 2) / (2 * 1.2 ** 2))[..., None] * np.array([255, 200, 190], np.float32)

    def frame(self, t):
        arr = self.bg.copy()
        # 游船
        bx = -260 + 24 * t
        by = Y_BANK + 32 + 1.5 * math.sin(1.6 * t)
        R0 = self.river.y0
        extra = np.zeros_like(self.river.refl)
        bw, bh = self.boat.size
        r0 = int(by) - R0
        c0 = int(bx) + M
        rh = min(bh, self.river.R - r0)
        cs0, cs1 = max(0, c0), min(CW, c0 + bw)
        if cs1 > cs0 and rh > 0:
            extra[r0:r0 + rh, cs0:cs1] += self.boat_refl[:rh, cs0 - c0:cs1 - c0]
        arr[R0 + M:R0 + M + self.river.R] = self.river.render(t, extra)
        # 船身 + 船灯光晕
        bimg = np.asarray(self.boat).astype(np.float32)
        y0 = int(by - bh) + M
        if cs1 > cs0:
            seg = arr[y0:y0 + bh, cs0:cs1]
            ba = bimg[:, cs0 - c0:cs1 - c0, 3:] / 255
            seg[:] = seg * (1 - ba) + bimg[:, cs0 - c0:cs1 - c0, :3] * ba
            p = self.boat_pad
            gy0, gx0 = y0 - p, c0 - p
            gh, gw = self.boat_glow.shape[:2]
            ys0, ys1 = max(0, gy0), min(CH, gy0 + gh)
            xs0, xs1 = max(0, gx0), min(CW, gx0 + gw)
            arr[ys0:ys1, xs0:xs1] += self.boat_glow[ys0 - gy0:ys1 - gy0, xs0 - gx0:xs1 - gx0]
        # 航空障碍灯闪烁
        for i, (x, y) in enumerate(self.beacons):
            ph = (t * 0.75 + i * 0.37) % 1.0
            inten = smooth(0.0, 0.08, ph) * (1 - smooth(0.35, 0.5, ph))
            if inten > 0.01:
                xi, yi = int(x) + M, int(y) + M
                arr[yi - 14:yi + 15, xi - 14:xi + 15] += self.beacon_spr * inten
        # 积雪
        c = self.cap
        self.cap.render(t, arr[c.y0:c.y0 + c.h])
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        # 镜头：缓慢推近 + 微微上摇
        z = 1 + 0.06 * (t / DUR)
        cx = M + 8 * math.sin(t / DUR * math.pi)
        cy = M - 18 * (t / DUR)
        a = 1 / z
        img = img.transform((W, H), Image.AFFINE, (a, 0, cx + W / 2 - W / 2 * a, 0, a, cy + H / 2 - H / 2 * a), resample=Image.BILINEAR)
        if t < 1.6:
            img = img.filter(ImageFilter.GaussianBlur(9 * (1 - smooth(0, 1.6, t))))
        fr = img.convert("RGBA")
        dens = 0.45 + 0.4 * smooth(8.2, 9.6, t) + 0.15 * smooth(14, 16, t)
        self.snow.draw(fr, t, dens)
        vx, vy = int(1000 - 40 * t), int(2400 - 90 * t)
        va = self.veil.crop((vx, vy, vx + W, vy + H))
        va = va.point(lambda v: int(v * (0.5 + 0.5 * dens)))
        fr = Image.alpha_composite(fr, Image.merge("RGBA", (*self.white.split(), va)))
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
