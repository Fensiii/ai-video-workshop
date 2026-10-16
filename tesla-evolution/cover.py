"""Cover image: the 2026 Roadster blasting off, every earlier generation streaming behind it as a ghost trail."""
import math
import sys
import numpy as np
import skia
import cv2
from PIL import Image

import carrender as cr
import scenes as sc
from carrender import col, poly_path
from cars import CARS

W, H = 1920, 1080
RNG = np.random.default_rng(2026)
ENV = dict(sky_refl=[120, 170, 230], ground_refl=[30, 40, 70], accent=[90, 235, 255])
HERO_S = 0.205
HERO_X, HERO_Y = 1360, 700      # car centre / ground contact point of the hero (before tilt)
TILT = -9.0                     # degrees, nose up


def P(**k):
    return skia.Paint(AntiAlias=True, **k)


def radial(cv, x, y, r, stops):
    p = P()
    p.setShader(skia.GradientShader.MakeRadial(skia.Point(x, y), r, [col(c, a) for c, a, _ in stops], [s for _, _, s in stops]))
    cv.drawCircle(x, y, r, p)


def background(cv):
    p = P()
    p.setShader(skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(0, H)],
                [col([2, 3, 10]), col([6, 12, 34]), col([14, 30, 66]), col([4, 6, 14])], [0, 0.45, 0.72, 1]))
    cv.drawRect(skia.Rect(0, 0, W, H), p)
    for _ in range(260):
        x, y = RNG.uniform(0, W), RNG.uniform(0, 620)
        cv.drawCircle(x, y, RNG.uniform(0.5, 1.8), P(Color=col([220, 235, 255], RNG.uniform(0.2, 0.8))))
    # god rays from behind the car
    cx, cy = HERO_X + 60, HERO_Y - 160
    cv.save()
    for i in range(36):
        a = math.radians(i * 10 + RNG.uniform(-3, 3))
        w = math.radians(RNG.uniform(1.0, 3.5))
        L = 2600
        pth = skia.Path(); pth.moveTo(cx, cy)
        pth.lineTo(cx + L * math.cos(a - w), cy + L * math.sin(a - w)); pth.lineTo(cx + L * math.cos(a + w), cy + L * math.sin(a + w)); pth.close()
        rp = P()
        c = [120, 220, 255] if i % 3 else [255, 120, 140]
        rp.setShader(skia.GradientShader.MakeRadial(skia.Point(cx, cy), 1300, [col(c, 0.20), col(c, 0)]))
        cv.drawPath(pth, rp)
    cv.restore()
    radial(cv, cx, cy, 900, [([90, 200, 255], 0.55, 0), ([40, 90, 200], 0.25, 0.35), ([10, 20, 60], 0, 1)])
    # future skyline silhouettes
    x = -40
    while x < W:
        bw = RNG.uniform(40, 120); bh = RNG.uniform(180, 520)
        top = 760 - bh
        pth = skia.Path(); tp = RNG.uniform(0.1, 0.3) * bw
        pth.moveTo(x, 900); pth.lineTo(x + tp, top + 20); pth.quadTo(x + bw / 2, top - 30, x + bw - tp, top + 20); pth.lineTo(x + bw, 900); pth.close()
        tg = P(); tg.setShader(skia.GradientShader.MakeLinear([skia.Point(x, 0), skia.Point(x + bw, 0)], [col([16, 30, 62], 0.9), col([8, 14, 32], 0.9)]))
        cv.drawPath(pth, tg)
        lc = [[80, 230, 255], [150, 160, 255], [255, 80, 120]][RNG.integers(0, 3)]
        cv.drawLine(x + bw / 2, top + 6, x + bw / 2, 760, P(StrokeWidth=2, Color=col(lc, 0.55)))
        x += bw + RNG.uniform(10, 60)
    # ground
    g = P(); g.setShader(skia.GradientShader.MakeLinear([skia.Point(0, 760), skia.Point(0, H)], [col([10, 16, 34]), col([2, 3, 8])]))
    cv.drawRect(skia.Rect(0, 760, W, H), g)
    # perspective grid on the ground, rushing toward the viewer
    vx = HERO_X - 100
    for i in range(-30, 31):
        cv.drawLine(vx + i * 30, 760, vx + i * 260, H + 200, P(StrokeWidth=1.2, Color=col([90, 235, 255], 0.14)))
    for k in range(10):
        y = 760 + (H - 760) * (k / 10) ** 1.8
        cv.drawLine(0, y, W, y, P(StrokeWidth=1, Color=col([90, 235, 255], 0.10 + 0.02 * k)))


def hero_transform(cv):
    cv.translate(HERO_X, HERO_Y); cv.rotate(TILT); cv.scale(HERO_S, -HERO_S)


def ghost_trail(cv):
    """Earlier generations rising along a light path from the road (lower left) toward the hero."""
    n = len(CARS) - 1
    p0 = np.array([120.0, 1012.0]); p1 = np.array([930.0, 805.0]); ctrl = np.array([560.0, 1015.0])
    pts = []
    for i in range(n):
        u = i / (n - 1)
        pts.append((1 - u) ** 2 * p0 + 2 * (1 - u) * u * ctrl + u ** 2 * p1)
    # energy path
    path = skia.Path(); path.moveTo(*p0); path.quadTo(*ctrl, *p1)
    path.quadTo(1060, 730, HERO_X - 430, HERO_Y - 40)
    for w, a, bl in ((26, 0.35, 16), (6, 0.8, 3), (2, 1.0, 0)):
        p = P(Style=skia.Paint.kStroke_Style, StrokeWidth=w, StrokeCap=skia.Paint.kRound_Cap)
        p.setShader(skia.GradientShader.MakeLinear([skia.Point(*p0), skia.Point(HERO_X - 430, HERO_Y - 40)],
                    [col([90, 220, 255], 0.0), col([90, 220, 255], a), col([255, 70, 100], a)], [0, 0.55, 1]))
        if bl:
            p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, bl))
        cv.drawPath(path, p)
    fy = skia.Font(skia.Typeface('Noto Sans CJK SC Bold'), 24); fy.setEdging(skia.Font.Edging.kAntiAlias)
    for i in range(n):
        c = CARS[i]
        u = i / (n - 1)
        s_ = 0.030 + 0.022 * u
        x, y = pts[i]
        a = 0.55 + 0.4 * u
        acc = [90, 220, 255]
        cv.save(); cv.translate(x, y - 14); cv.rotate(TILT * u * 0.6); cv.scale(s_, -s_)
        f = P(); f.setShader(skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(0, c.H)], [col([10, 30, 60], 0.85), col(acc, 0.35)]))
        cv.drawPath(poly_path(c.outline), f)
        gl = P(Style=skia.Paint.kStroke_Style, StrokeWidth=3 / s_ * 3, Color=col(acc, 0.55 * a))
        gl.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 6 / s_))
        cv.drawPath(poly_path(c.outline), gl)
        cv.drawPath(poly_path(c.outline), P(Style=skia.Paint.kStroke_Style, StrokeWidth=1.8 / s_, Color=col([225, 250, 255], a)))
        for (wx, r) in (c.wf, c.wr):
            cv.drawCircle(wx, r, r, P(Color=col([12, 30, 58])))
            cv.drawCircle(wx, r, r, P(Style=skia.Paint.kStroke_Style, StrokeWidth=1.8 / s_, Color=col([225, 250, 255], a)))
        cv.restore()
        tw = fy.measureText(c.year)
        cv.drawString(c.year, x - tw / 2, y + 30, fy, P(Color=col([255, 255, 255], 0.55 + 0.4 * u)))


def speed_lines(cv):
    for _ in range(140):
        y = RNG.uniform(560, 880); x = RNG.uniform(500, W - 500); L = RNG.uniform(120, 620)
        c = [150, 230, 255] if RNG.random() < 0.8 else [255, 110, 130]
        p = P(); p.setShader(skia.GradientShader.MakeLinear([skia.Point(x, y), skia.Point(x + L, y)], [col(c, 0), col(c, RNG.uniform(0.15, 0.55))]))
        cv.drawRect(skia.Rect(x, y - RNG.uniform(0.6, 1.8), x + L, y + 1.8), p)


NOZZLES = [1500, 380, -520, -1480]


def nozzle_pts():
    m = skia.Matrix(); m.setTranslate(HERO_X, HERO_Y); m.preRotate(TILT); m.preScale(HERO_S, -HERO_S)
    return [m.mapXY(x, 120) for x in NOZZLES]


def smoke(cv):
    pts = nozzle_pts()
    for _ in range(300):
        nx = pts[RNG.integers(0, 4)]
        spread = RNG.normal(0, 1)
        x = nx.x() + spread * 260
        y = 935 - abs(RNG.normal(0, 1)) * 50 + RNG.uniform(-10, 60)
        r = RNG.uniform(30, 110) * (1 + abs(spread) * 0.3)
        lit = max(0, 1 - abs(x - nx.x()) / 500)
        c = np.array([150, 170, 200]) * (1 - lit) + np.array([200, 240, 255]) * lit
        if RNG.random() < 0.15:
            c = np.array([255, 150, 170])
        a = RNG.uniform(0.05, 0.16)
        radial(cv, x, y, r, [(c, a, 0), (c, a * 0.45, 0.55), (c, 0, 1)])


def jets(cv):
    for i, n in enumerate(nozzle_pts()):
        x, y = n.x(), n.y()
        ln = 935 - y + 60
        for w, c, a, blur in ((70, [80, 180, 255], 0.55, 30), (34, [170, 230, 255], 0.9, 10), (12, [255, 255, 255], 1.0, 3)):
            pth = skia.Path(); pth.moveTo(x - w * 0.35, y); pth.lineTo(x + w * 0.35, y); pth.lineTo(x + w, y + ln); pth.lineTo(x - w, y + ln); pth.close()
            p = P(); p.setShader(skia.GradientShader.MakeLinear([skia.Point(0, y), skia.Point(0, y + ln)], [col(c, a), col(c, a * 0.7), col(c, 0)], [0, 0.6, 1]))
            p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
            cv.drawPath(pth, p)
        # shock diamonds
        for k in range(4):
            yy = y + 40 + k * 55
            radial(cv, x, yy, 16 - k * 2, [([255, 255, 255], 0.9, 0), ([170, 230, 255], 0.0, 1)])
        radial(cv, x, y + 6, 90, [([220, 245, 255], 0.9, 0), ([120, 200, 255], 0.3, 0.3), ([60, 120, 255], 0, 1)])
        radial(cv, x, 935, 220, [([200, 240, 255], 0.55, 0), ([100, 180, 255], 0.2, 0.4), ([40, 80, 200], 0, 1)])


def nozzles(cv):
    cv.save(); hero_transform(cv)
    for x in NOZZLES:
        cv.drawRoundRect(skia.Rect(x - 70, 110, x + 70, 230), 30, 30, P(Color=col([34, 36, 42])))
        cv.drawRect(skia.Rect(x - 60, 110, x + 60, 130), P(Color=col([90, 96, 110])))
    cv.restore()


def sparks(cv):
    for i, n in enumerate(nozzle_pts()):
        for _ in range(26):
            ang = math.radians(RNG.uniform(195, 345)); sp = RNG.uniform(80, 420)
            x0, y0 = n.x(), 935
            x1, y1 = x0 + math.cos(ang) * sp, y0 + math.sin(ang) * sp * 0.45
            c = [255, 210, 150] if RNG.random() < 0.6 else [180, 235, 255]
            p = P(StrokeWidth=RNG.uniform(1.2, 2.6), StrokeCap=skia.Paint.kRound_Cap)
            p.setShader(skia.GradientShader.MakeLinear([skia.Point(x0, y0), skia.Point(x1, y1)], [col(c, 0), col(c, 0.95)]))
            cv.drawLine(x0 + (x1 - x0) * 0.4, y0 + (y1 - y0) * 0.4, x1, y1, p)


def hero(cv):
    st = cr.CarState(len(CARS) - 1)
    cv.save(); hero_transform(cv)
    cr.draw_car(cv, st, ENV, 1234.0, lights=1.0, lift=1.0)
    c = CARS[-1]
    # strong cyan rim light along the roofline + red tail streak
    rim = P(Style=skia.Paint.kStroke_Style, StrokeWidth=30, Color=col([140, 230, 255], 0.75))
    rim.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 14))
    cv.save(); cv.clipRect(skia.Rect(-c.L, c.H * 0.62, c.L, c.H * 2)); cv.drawPath(poly_path(c.outline), rim)
    cv.drawPath(poly_path(c.outline), P(Style=skia.Paint.kStroke_Style, StrokeWidth=7, Color=col([235, 250, 255], 0.9)))
    cv.restore()
    cv.restore()
    # headlight flare and tail-light streak (screen space)
    m = skia.Matrix(); m.setTranslate(HERO_X, HERO_Y); m.preRotate(TILT); m.preScale(HERO_S, -HERO_S)
    hd = [p for k, _, p in c.parts if k == 'head'][0].mean(0); tl = [p for k, _, p in c.parts if k == 'tail'][0].mean(0)
    h = m.mapXY(*hd); t = m.mapXY(*tl)
    radial(cv, h.x(), h.y(), 160, [([235, 248, 255], 1.0, 0), ([120, 200, 255], 0.35, 0.25), ([60, 120, 255], 0, 1)])
    fl = P(); fl.setShader(skia.GradientShader.MakeLinear([skia.Point(h.x() - 700, 0), skia.Point(h.x() + 700, 0)],
                           [col([140, 220, 255], 0), col([230, 248, 255], 0.9), col([140, 220, 255], 0)]))
    cv.drawRect(skia.Rect(h.x() - 700, h.y() - 2, h.x() + 700, h.y() + 2), fl)
    radial(cv, t.x(), t.y(), 90, [([255, 60, 80], 0.95, 0), ([255, 30, 60], 0.3, 0.3), ([255, 0, 40], 0, 1)])
    tp = P(); tp.setShader(skia.GradientShader.MakeLinear([skia.Point(t.x() - 900, 0), skia.Point(t.x(), 0)],
                           [col([255, 40, 70], 0), col([255, 60, 90], 0.8)]))
    cv.drawRect(skia.Rect(t.x() - 900, t.y() - 3, t.x(), t.y() + 3), tp)


def title(cv):
    sc.draw_logo(cv, 128, 140, 78, col([255, 255, 255]))
    ft = skia.Font(skia.Typeface('Noto Sans CJK SC Black'), 168); ft.setEdging(skia.Font.Edging.kAntiAlias)
    txt = '会飞的车'
    x, y = 96, 360
    sh = P(Color=col([0, 0, 0], 0.8)); sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 22))
    cv.drawString(txt, x + 6, y + 10, ft, sh)
    gl = P(Color=col([90, 220, 255], 0.30)); gl.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 30))
    cv.drawString(txt, x, y, ft, gl)
    mp = P(); mp.setShader(skia.GradientShader.MakeLinear([skia.Point(0, y - 140), skia.Point(0, y + 10)],
                           [col([255, 255, 255]), col([236, 244, 255]), col([150, 170, 196]), col([236, 244, 255])], [0, 0.45, 0.62, 1]))
    cv.drawString(txt, x, y, ft, mp)
    tw = ft.measureText(txt)
    cv.drawRect(skia.Rect(x + 4, y + 34, x + tw, y + 40), P(Color=col([230, 30, 45])))
    fs = skia.Font(skia.Typeface('Noto Sans CJK SC Medium'), 46); fs.setEdging(skia.Font.Edging.kAntiAlias)
    cv.drawString('从公路，到天空', x + 4, y + 108, fs, P(Color=col([225, 238, 255])))
    fy = skia.Font(skia.Typeface('Noto Sans CJK SC Light'), 40)
    s2 = '2008 — 2026  ·  8 代车型'
    cv.drawString(s2, x + 4, y + 168, fy, P(Color=col([150, 210, 255], 0.9)))
    # HERO year stamp
    fb = skia.Font(skia.Typeface('Noto Sans CJK SC Black'), 260)
    yr = '2026'
    p = P(); p.setShader(skia.GradientShader.MakeLinear([skia.Point(0, 140), skia.Point(0, 380)], [col([255, 60, 80], 0.30), col([255, 60, 80], 0.0)]))
    cv.drawString(yr, W - fb.measureText(yr) - 60, 330, fb, p)


def post(arr):
    img = arr.astype(np.float32) / 255
    lum = img.max(axis=2, keepdims=True)
    bright = img * np.clip((lum - 0.62) / 0.38, 0, 1)
    bloom = cv2.GaussianBlur(bright, (0, 0), 18) * 0.9 + cv2.GaussianBlur(bright, (0, 0), 60) * 0.8
    img = 1 - (1 - img) * (1 - np.clip(bloom, 0, 1))
    # chromatic aberration toward edges
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dx = (xx - W / 2) / (W / 2); dy = (yy - H / 2) / (H / 2)
    k = 2.2
    r = cv2.remap(img[..., 0], xx + dx * k, yy + dy * k, cv2.INTER_LINEAR)
    b = cv2.remap(img[..., 2], xx - dx * k, yy - dy * k, cv2.INTER_LINEAR)
    img = np.stack([r, img[..., 1], b], 2)
    v = 1 - 0.55 * np.clip((dx ** 2 + dy ** 2) ** 0.5 - 0.45, 0, 1) ** 1.5
    img *= v[..., None]
    # slight teal/orange grade + contrast
    img = np.clip((img - 0.5) * 1.08 + 0.5, 0, 1)
    img += np.random.default_rng(1).normal(0, 0.012, img.shape).astype(np.float32)
    return (np.clip(img, 0, 1) * 255).astype(np.uint8)


def main(out):
    surf = skia.Surface(W, H); cv = surf.getCanvas()
    background(cv)
    speed_lines(cv)
    ghost_trail(cv)
    smoke(cv)
    jets(cv)
    nozzles(cv)
    hero(cv)
    sparks(cv)
    title(cv)
    arr = surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)[..., :3]
    im = Image.fromarray(post(arr))
    im.save(out, quality=95) if out.endswith('.jpg') else im.save(out)


if __name__ == '__main__':
    main(sys.argv[1])
