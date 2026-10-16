"""Parallax 2D environments. Static layers are pre-rendered into seamless tiles."""
import math
import numpy as np
import skia
from carrender import col, clamp, lerp, smooth

W, H = 1920, 1080
HORIZON = 690
MIDBASE = 735
ROAD_T, ROAD_B = 735, 905
SPEED = dict(near=1100.0, mid=450.0, far=140.0)

TESLA_T = ("M12 5.362l2.475-3.026s4.245.09 8.471 2.054c-1.082 1.636-3.231 2.438-3.231 2.438-.146-1.439-1.154-1.79-4.354-1.79"
           "L12 24 8.619 5.034c-3.18 0-4.188.354-4.335 1.792 0 0-2.146-.795-3.229-2.43C5.28 2.431 9.525 2.34 9.525 2.34L12 5.362"
           "l-.004.002H12v-.002zm0-3.899c3.415-.03 7.326.528 11.328 2.28.535-.968.672-1.395.672-1.395C19.625.612 15.528.015 12 0"
           " 8.472.015 4.375.61 0 2.349c0 0 .195.525.672 1.396C4.674 1.989 8.585 1.435 12 1.46v.003z")


def svg_path(d):
    """Minimal SVG path parser (M/L/H/V/C/S/Z, absolute + relative)."""
    import re
    toks = re.findall(r'[MmLlHhVvCcSsZz]|-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?', d)
    p = skia.Path(); i = 0; cmd = None
    cx = cy = sx = sy = 0.0; lc = None

    def num():
        nonlocal i
        v = float(toks[i]); i += 1; return v
    while i < len(toks):
        if toks[i].isalpha():
            cmd = toks[i]; i += 1
            if cmd in 'Zz':
                p.close(); cx, cy = sx, sy; lc = None
                continue
        rel = cmd.islower(); C = cmd.upper()
        ox, oy = (cx, cy) if rel else (0.0, 0.0)
        if C == 'M':
            cx, cy = ox + num(), oy + num(); sx, sy = cx, cy; p.moveTo(cx, cy); cmd = 'l' if rel else 'L'; lc = None
        elif C == 'L':
            cx, cy = ox + num(), oy + num(); p.lineTo(cx, cy); lc = None
        elif C == 'H':
            cx = (cx if rel else 0) + num(); p.lineTo(cx, cy); lc = None
        elif C == 'V':
            cy = (cy if rel else 0) + num(); p.lineTo(cx, cy); lc = None
        elif C == 'C':
            x1, y1, x2, y2, x, y = ox + num(), oy + num(), ox + num(), oy + num(), ox + num(), oy + num()
            p.cubicTo(x1, y1, x2, y2, x, y); lc = (x2, y2); cx, cy = x, y
        elif C == 'S':
            x1, y1 = (2 * cx - lc[0], 2 * cy - lc[1]) if lc else (cx, cy)
            x2, y2, x, y = ox + num(), oy + num(), ox + num(), oy + num()
            p.cubicTo(x1, y1, x2, y2, x, y); lc = (x2, y2); cx, cy = x, y
    return p


LOGO = svg_path(TESLA_T)


def draw_logo(cv, cx, cy, height, color):
    s = height / 24.0
    cv.save(); cv.translate(cx - 12 * s, cy - 12 * s); cv.scale(s, s)
    p = skia.Paint(AntiAlias=True, Color=color)
    cv.drawPath(LOGO, p); cv.restore()


def P(**k):
    return skia.Paint(AntiAlias=True, **k)


def lin(cv, rect, y0, y1, cols, pos=None, x=False):
    p = P()
    pts = [skia.Point(rect.left(), 0), skia.Point(rect.right(), 0)] if x else [skia.Point(0, y0), skia.Point(0, y1)]
    p.setShader(skia.GradientShader.MakeLinear(pts, cols, pos))
    cv.drawRect(rect, p)


def glow(cv, x, y, r, c, a):
    p = P()
    p.setShader(skia.GradientShader.MakeRadial(skia.Point(x, y), r, [col(c, a), col(c, a * 0.35), col(c, 0)], [0, 0.35, 1]))
    cv.drawCircle(x, y, r, p)


def make_tile(w, h, fn, seed):
    surf = skia.Surface(w, h)
    cv = surf.getCanvas(); cv.clear(skia.Color(0, 0, 0, 0))
    fn(cv, w, h, np.random.default_rng(seed))
    return surf.makeImageSnapshot()


def draw_tile(cv, img, offset, y=0, alpha=1.0, flip=False):
    w = img.width()
    x = -(offset % w)
    p = skia.Paint(); p.setAlphaf(alpha)
    while x < W:
        if flip:
            cv.save(); cv.translate(0, 2 * y); cv.scale(1, -1)
            cv.drawImage(img, x, y - img.height(), skia.SamplingOptions(skia.FilterMode.kLinear), p); cv.restore()
        else:
            cv.drawImage(img, x, y, skia.SamplingOptions(skia.FilterMode.kLinear), p)
        x += w


# =============================================================== tile painters
def garage_mid(cv, w, h, r):
    # wall (opaque backdrop to MIDBASE)
    lin(cv, skia.Rect(0, 0, w, h), 0, h, [col([24, 19, 15]), col([52, 40, 31]), col([66, 52, 40])], [0, 0.55, 1])
    for x in range(0, w, 180):
        cv.drawRect(skia.Rect(x, 0, x + 3, h), P(Color=col([20, 15, 12], 0.8)))
        cv.drawRect(skia.Rect(x + 3, 0, x + 5, h), P(Color=col([90, 72, 56], 0.25)))
    # ceiling beam
    lin(cv, skia.Rect(0, 0, w, 70), 0, 70, [col([12, 10, 8]), col([30, 24, 19])])
    for x in range(0, w, 360):
        cv.drawRect(skia.Rect(x, 60, x + 26, h), P(Color=col([34, 27, 21])))
    # workbenches, pegboards, shelves
    x = 120
    while x < w - 600:
        kind = r.integers(0, 3)
        if kind == 0:   # pegboard + bench
            cv.drawRect(skia.Rect(x, 380, x + 420, 560), P(Color=col([70, 56, 42])))
            for i in range(14):
                for j in range(6):
                    cv.drawCircle(x + 15 + i * 29, 393 + j * 28, 2.2, P(Color=col([40, 31, 24])))
            tp = P(Color=col([150, 152, 156]))
            for i in range(5):
                tx = x + 40 + i * 75
                cv.drawRect(skia.Rect(tx, 410, tx + 8, 500 - r.integers(0, 40)), tp)
                cv.drawCircle(tx + 4, 410, 13, P(Style=skia.Paint.kStroke_Style, StrokeWidth=7, Color=col([150, 152, 156])))
            cv.drawRect(skia.Rect(x - 20, 590, x + 460, 612), P(Color=col([96, 70, 46])))
            cv.drawRect(skia.Rect(x - 10, 612, x + 6, MIDBASE), P(Color=col([40, 32, 26])))
            cv.drawRect(skia.Rect(x + 434, 612, x + 450, MIDBASE), P(Color=col([40, 32, 26])))
            cv.drawRect(skia.Rect(x + 20, 640, x + 160, 700), P(Color=col([58, 62, 70])))  # tool chest
            for k in range(3):
                cv.drawRect(skia.Rect(x + 24, 646 + k * 18, x + 156, 648 + k * 18), P(Color=col([30, 32, 38])))
            x += 620
        elif kind == 1:  # shelf with boxes
            for j in range(3):
                yy = 380 + j * 110
                cv.drawRect(skia.Rect(x, yy, x + 300, yy + 10), P(Color=col([60, 48, 38])))
                bx = x + 10
                while bx < x + 280:
                    bw = r.integers(40, 90); bh = r.integers(40, 90)
                    cv.drawRect(skia.Rect(bx, yy - bh, bx + bw, yy), P(Color=col([120 + r.integers(0, 40), 90, 60])))
                    bx += bw + 8
            cv.drawRect(skia.Rect(x, 330, x + 8, MIDBASE), P(Color=col([40, 32, 26])))
            cv.drawRect(skia.Rect(x + 292, 330, x + 300, MIDBASE), P(Color=col([40, 32, 26])))
            x += 460
        else:  # tyre stack
            for j in range(4):
                yy = MIDBASE - 60 - j * 58
                cv.drawRoundRect(skia.Rect(x, yy, x + 200, yy + 56), 20, 20, P(Color=col([22, 22, 24])))
                cv.drawRect(skia.Rect(x + 10, yy + 26, x + 190, yy + 30), P(Color=col([45, 45, 48])))
            x += 360
    # hanging lamps with warm light
    for lx in range(260, w, 560):
        cv.drawRect(skia.Rect(lx - 1, 0, lx + 1, 170), P(Color=col([10, 10, 10])))
        pth = skia.Path(); pth.moveTo(lx - 50, 205); pth.lineTo(lx - 16, 170); pth.lineTo(lx + 16, 170); pth.lineTo(lx + 50, 205); pth.close()
        cv.drawPath(pth, P(Color=col([30, 30, 28])))
        cone = skia.Path(); cone.moveTo(lx - 46, 205); cone.lineTo(lx + 46, 205); cone.lineTo(lx + 330, h); cone.lineTo(lx - 330, h); cone.close()
        cp = P(); cp.setShader(skia.GradientShader.MakeLinear([skia.Point(0, 205), skia.Point(0, h)],
                                                            [col([255, 200, 130], 0.30), col([255, 190, 120], 0.0)]))
        cv.drawPath(cone, cp)
        glow(cv, lx, 208, 120, [255, 210, 150], 0.9)
        cv.drawOval(skia.Rect(lx - 40, 200, lx + 40, 212), P(Color=col([255, 236, 200])))


def country_far(cv, w, h, r):
    xs = np.arange(0, w + 8, 8)
    for layer, (base, amp, c) in enumerate([(560, 70, [150, 172, 186]), (620, 55, [104, 132, 120])]):
        ph = r.uniform(0, 6, 3)
        ys = base - amp * (0.6 * np.sin(xs / w * 2 * math.pi * 2 + ph[0]) + 0.3 * np.sin(xs / w * 2 * math.pi * 5 + ph[1])
                           + 0.15 * np.sin(xs / w * 2 * math.pi * 11 + ph[2]))
        pth = skia.Path(); pth.moveTo(0, h)
        for x, y in zip(xs, ys):
            pth.lineTo(float(x), float(y))
        pth.lineTo(w, h); pth.close()
        cv.drawPath(pth, P(Color=col(c)))
    # distant tree line
    x = 0
    while x < w:
        rr = r.uniform(10, 22)
        cv.drawCircle(x, HORIZON - rr * 0.6, rr, P(Color=col([70, 98, 80])))
        x += r.uniform(14, 30)
    cv.drawRect(skia.Rect(0, HORIZON - 8, w, h), P(Color=col([70, 98, 80])))


def country_mid(cv, w, h, r):
    # fence
    fp = P(Color=col([110, 86, 60]))
    cv.drawRect(skia.Rect(0, MIDBASE - 42, w, MIDBASE - 36), fp)
    cv.drawRect(skia.Rect(0, MIDBASE - 22, w, MIDBASE - 17), fp)
    for x in range(10, w, 70):
        cv.drawRect(skia.Rect(x, MIDBASE - 55, x + 7, MIDBASE), P(Color=col([90, 70, 50])))
    # trees
    x = 80
    while x < w - 200:
        th = r.uniform(170, 300)
        cv.drawRect(skia.Rect(x - 8, MIDBASE - th, x + 8, MIDBASE), P(Color=col([70, 52, 38])))
        for k in range(5):
            cx = x + r.uniform(-60, 60); cy = MIDBASE - th - r.uniform(-20, 60); rr = r.uniform(50, 85)
            g = P(); g.setShader(skia.GradientShader.MakeRadial(skia.Point(cx - rr * 0.3, cy - rr * 0.4), rr * 1.3,
                                                              [col([120, 150, 80]), col([54, 84, 50])]))
            cv.drawCircle(cx, cy, rr, g)
        x += r.uniform(380, 700)
    # utility poles + wires
    poles = list(range(300, w, 600))
    for px in poles:
        cv.drawRect(skia.Rect(px - 6, 250, px + 6, MIDBASE), P(Color=col([60, 46, 34])))
        cv.drawRect(skia.Rect(px - 60, 270, px + 60, 278), P(Color=col([60, 46, 34])))
    wp = P(Style=skia.Paint.kStroke_Style, StrokeWidth=2, Color=col([40, 34, 30], 0.8))
    allp = [p - 600 for p in poles[:1]] + poles + [poles[-1] + 600]
    for a, b in zip(allp[:-1], allp[1:]):
        for dx in (-50, 50):
            pth = skia.Path(); pth.moveTo(a + dx, 272); pth.quadTo((a + b) / 2 + dx, 330, b + dx, 272)
            cv.drawPath(pth, wp)


def highway_far(cv, w, h, r):
    xs = np.arange(0, w + 8, 8)
    ph = r.uniform(0, 6, 4)
    ys = 520 - 120 * np.abs(np.sin(xs / w * math.pi * 3 + ph[0])) ** 1.5 - 40 * np.sin(xs / w * 2 * math.pi * 7 + ph[1])
    pth = skia.Path(); pth.moveTo(0, h)
    for x, y in zip(xs, ys):
        pth.lineTo(float(x), float(y))
    pth.lineTo(w, h); pth.close()
    pp = P(); pp.setShader(skia.GradientShader.MakeLinear([skia.Point(0, 380), skia.Point(0, HORIZON)], [col([96, 60, 110]), col([150, 82, 110])]))
    cv.drawPath(pth, pp)
    # distant skyline
    x = 0
    while x < w:
        bw = r.uniform(18, 50); bh = r.uniform(30, 140)
        cv.drawRect(skia.Rect(x, HORIZON - bh, x + bw, HORIZON), P(Color=col([70, 44, 80])))
        for k in range(int(bh / 14)):
            if r.random() < 0.4:
                cv.drawRect(skia.Rect(x + 4, HORIZON - bh + 6 + k * 14, x + 7, HORIZON - bh + 9 + k * 14), P(Color=col([255, 200, 140], 0.7)))
        x += bw + r.uniform(0, 40)


def highway_mid(cv, w, h, r):
    # guardrail
    lin(cv, skia.Rect(0, MIDBASE - 34, w, MIDBASE - 18), MIDBASE - 34, MIDBASE - 18, [col([200, 170, 170]), col([90, 70, 80])])
    for x in range(0, w, 90):
        cv.drawRect(skia.Rect(x, MIDBASE - 34, x + 8, MIDBASE), P(Color=col([70, 56, 64])))
    # lamp posts
    for x in range(200, w, 520):
        cv.drawRect(skia.Rect(x - 5, 300, x + 5, MIDBASE - 18), P(Color=col([40, 30, 44])))
        pth = skia.Path(); pth.moveTo(x, 305); pth.quadTo(x + 10, 280, x + 80, 284)
        cv.drawPath(pth, P(Style=skia.Paint.kStroke_Style, StrokeWidth=7, Color=col([40, 30, 44])))
        cv.drawRoundRect(skia.Rect(x + 62, 280, x + 120, 292), 6, 6, P(Color=col([46, 34, 50])))
        glow(cv, x + 92, 294, 70, [255, 214, 160], 0.55)
    # occasional gantry sign (blank)
    gx = r.integers(400, w - 800)
    for d in (0, 520):
        cv.drawRect(skia.Rect(gx + d, 200, gx + d + 14, MIDBASE - 18), P(Color=col([60, 46, 64])))
    cv.drawRect(skia.Rect(gx - 10, 205, gx + 544, 222), P(Color=col([60, 46, 64])))
    cv.drawRoundRect(skia.Rect(gx + 120, 225, gx + 420, 330), 8, 8, P(Color=col([20, 86, 60])))
    cv.drawRoundRect(skia.Rect(gx + 126, 231, gx + 414, 324), 6, 6, P(Style=skia.Paint.kStroke_Style, StrokeWidth=3, Color=col([220, 230, 220], 0.8)))


def city_far(cv, w, h, r):
    x = 0
    while x < w:
        bw = r.uniform(60, 170); bh = r.uniform(180, 520)
        top = HORIZON - bh
        c = np.array([16, 20, 40]) + r.uniform(0, 14)
        cv.drawRect(skia.Rect(x, top, x + bw, HORIZON + 50), P(Color=col(c)))
        if r.random() < 0.3:
            cv.drawRect(skia.Rect(x + bw * 0.45, top - 40, x + bw * 0.55, top), P(Color=col(c)))
            glow(cv, x + bw * 0.5, top - 42, 10, [255, 60, 60], 0.9)
        warm = r.random() < 0.6
        for yy in np.arange(top + 12, HORIZON, 16):
            for xx in np.arange(x + 8, x + bw - 8, 13):
                if r.random() < 0.33:
                    cc = [255, 214, 140] if warm else [150, 210, 255]
                    cv.drawRect(skia.Rect(xx, yy, xx + 6, yy + 8), P(Color=col(cc, r.uniform(0.35, 0.9))))
        x += bw + r.uniform(4, 30)


def city_mid(cv, w, h, r):
    x = 0
    while x < w:
        bw = r.uniform(240, 420); bh = r.uniform(140, 300)
        top = MIDBASE - bh
        cv.drawRect(skia.Rect(x, top, x + bw, MIDBASE), P(Color=col([24, 26, 40])))
        # shop window glow
        cv.drawRect(skia.Rect(x + 20, MIDBASE - 90, x + bw - 20, MIDBASE - 10), P(Color=col([255, 210, 150], 0.35)))
        for yy in np.arange(top + 20, MIDBASE - 110, 30):
            for xx in np.arange(x + 18, x + bw - 30, 34):
                if r.random() < 0.45:
                    cv.drawRect(skia.Rect(xx, yy, xx + 20, yy + 16), P(Color=col([255, 220, 160], r.uniform(0.3, 0.8))))
        # neon sign (blank)
        if r.random() < 0.7:
            nc = [[255, 60, 180], [60, 230, 255], [255, 150, 40]][r.integers(0, 3)]
            nx = x + r.uniform(30, bw - 150); ny = top + r.uniform(20, 60)
            gp = P(Style=skia.Paint.kStroke_Style, StrokeWidth=10, Color=col(nc, 0.6))
            gp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10))
            rr = skia.Rect(nx, ny, nx + 120, ny + 44)
            cv.drawRoundRect(rr, 10, 10, gp)
            cv.drawRoundRect(rr, 10, 10, P(Style=skia.Paint.kStroke_Style, StrokeWidth=3, Color=col([255, 255, 255], 0.9)))
        x += bw + r.uniform(10, 60)
    for lx in range(150, w, 480):
        cv.drawRect(skia.Rect(lx - 4, 330, lx + 4, MIDBASE), P(Color=col([12, 14, 22])))
        cv.drawRect(skia.Rect(lx, 330, lx + 60, 337), P(Color=col([12, 14, 22])))
        glow(cv, lx + 50, 342, 110, [255, 170, 90], 0.75)
        cv.drawOval(skia.Rect(lx + 34, 336, lx + 66, 346), P(Color=col([255, 230, 190])))


def factory_far(cv, w, h, r):
    lin(cv, skia.Rect(0, 0, w, h), 0, h, [col([54, 60, 70]), col([150, 158, 170]), col([196, 202, 210])], [0, 0.45, 1])
    # roof trusses
    tp = P(Style=skia.Paint.kStroke_Style, StrokeWidth=4, Color=col([40, 44, 52]))
    cv.drawLine(0, 120, w, 120, tp); cv.drawLine(0, 190, w, 190, tp)
    for x in range(0, w, 70):
        cv.drawLine(x, 120, x + 35, 190, tp); cv.drawLine(x + 35, 190, x + 70, 120, tp)
    # ceiling light panels
    for x in range(30, w, 220):
        cv.drawRect(skia.Rect(x, 200, x + 150, 214), P(Color=col([250, 252, 255])))
        glow(cv, x + 75, 214, 140, [230, 240, 255], 0.45)
    # wall panels + Tesla T logo
    for x in range(0, w, 240):
        cv.drawRect(skia.Rect(x, 260, x + 2, HORIZON), P(Color=col([120, 126, 136])))
    for lx in range(500, w, 1600):
        cv.drawRect(skia.Rect(lx - 160, 300, lx + 160, 560), P(Color=col([236, 238, 242])))
        draw_logo(cv, lx, 430, 200, col([200, 24, 34]))
    # distant production line silhouettes
    x = 0
    while x < w:
        bw = r.uniform(120, 260)
        cv.drawRect(skia.Rect(x, HORIZON - r.uniform(40, 110), x + bw, HORIZON), P(Color=col([96, 104, 116])))
        x += bw + r.uniform(30, 120)


def factory_mid(cv, w, h, r):
    for x in range(120, w, 380):
        cv.drawRect(skia.Rect(x, 230, x + 34, MIDBASE), P(Color=col([170, 176, 186])))
        cv.drawRect(skia.Rect(x + 4, 230, x + 10, MIDBASE), P(Color=col([220, 224, 230])))
        cv.save(); cv.clipRect(skia.Rect(x, MIDBASE - 90, x + 34, MIDBASE))
        cv.drawRect(skia.Rect(x, MIDBASE - 90, x + 34, MIDBASE), P(Color=col([240, 190, 20])))
        for k in range(7):
            pth = skia.Path(); y0 = MIDBASE - 90 + k * 22
            pth.moveTo(x, y0); pth.lineTo(x + 34, y0 - 16); pth.lineTo(x + 34, y0 - 5); pth.lineTo(x, y0 + 11); pth.close()
            cv.drawPath(pth, P(Color=col([20, 20, 20])))
        cv.restore()
    # overhead conveyor rail
    cv.drawRect(skia.Rect(0, 250, w, 266), P(Color=col([70, 76, 86])))
    for x in range(0, w, 160):
        cv.drawRect(skia.Rect(x, 266, x + 6, 300), P(Color=col([70, 76, 86])))


def future_far(cv, w, h, r):
    x = 0
    while x < w:
        bw = r.uniform(50, 140); bh = r.uniform(260, 640)
        top = HORIZON - bh
        pth = skia.Path()
        taper = r.uniform(0.15, 0.35) * bw
        pth.moveTo(x, HORIZON + 40); pth.lineTo(x + taper, top + 30); pth.quadTo(x + bw / 2, top - 30, x + bw - taper, top + 30)
        pth.lineTo(x + bw, HORIZON + 40); pth.close()
        pp = P(); pp.setShader(skia.GradientShader.MakeLinear([skia.Point(0, top), skia.Point(0, HORIZON)], [col([22, 38, 74]), col([8, 14, 32])]))
        cv.drawPath(pth, pp)
        lc = [[80, 230, 255], [140, 160, 255], [255, 255, 255]][r.integers(0, 3)]
        gp = P(Style=skia.Paint.kStroke_Style, StrokeWidth=3, Color=col(lc, 0.8))
        cv.drawLine(x + bw / 2, top + 10, x + bw / 2, HORIZON, gp)
        gp2 = P(Style=skia.Paint.kStroke_Style, StrokeWidth=12, Color=col(lc, 0.25))
        gp2.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 8))
        cv.drawLine(x + bw / 2, top + 10, x + bw / 2, HORIZON, gp2)
        for yy in np.arange(top + 60, HORIZON, 46):
            if r.random() < 0.5:
                cv.drawRect(skia.Rect(x + taper * 0.8, yy, x + bw - taper * 0.8, yy + 2), P(Color=col(lc, 0.5)))
        if r.random() < 0.25:  # ring
            rp = P(Style=skia.Paint.kStroke_Style, StrokeWidth=4, Color=col([80, 230, 255], 0.7))
            cv.drawOval(skia.Rect(x - 40, top + 80, x + bw + 40, top + 110), rp)
        x += bw + r.uniform(20, 120)


def future_mid(cv, w, h, r):
    # elevated maglev track
    for x in range(100, w, 420):
        cv.drawRect(skia.Rect(x, 470, x + 26, MIDBASE), P(Color=col([18, 26, 46])))
    lin(cv, skia.Rect(0, 440, w, 476), 440, 476, [col([40, 56, 90]), col([14, 20, 36])])
    gp = P(Style=skia.Paint.kStroke_Style, StrokeWidth=4, Color=col([90, 235, 255]))
    cv.drawLine(0, 476, w, 476, gp)
    gp2 = P(Style=skia.Paint.kStroke_Style, StrokeWidth=16, Color=col([90, 235, 255], 0.35))
    gp2.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10))
    cv.drawLine(0, 478, w, 478, gp2)
    # holographic panels (no text)
    x = 250
    while x < w - 300:
        pw, ph = r.uniform(140, 220), r.uniform(90, 150)
        y = r.uniform(530, 600)
        hc = [[80, 230, 255], [180, 120, 255]][r.integers(0, 2)]
        cv.drawRect(skia.Rect(x, y, x + pw, y + ph), P(Color=col(hc, 0.12)))
        cv.drawRect(skia.Rect(x, y, x + pw, y + ph), P(Style=skia.Paint.kStroke_Style, StrokeWidth=2, Color=col(hc, 0.8)))
        for yy in np.arange(y + 6, y + ph, 6):
            cv.drawRect(skia.Rect(x, yy, x + pw, yy + 1), P(Color=col(hc, 0.10)))
        for k in range(3):
            cv.drawRect(skia.Rect(x + 14, y + 20 + k * 22, x + 14 + pw * r.uniform(0.3, 0.8), y + 28 + k * 22), P(Color=col(hc, 0.45)))
        cv.drawRect(skia.Rect(x + pw / 2 - 2, y + ph, x + pw / 2 + 2, MIDBASE), P(Color=col(hc, 0.3)))
        x += pw + r.uniform(380, 700)


# =============================================================== scene table
class Scene:
    pass


def scene(name, **k):
    s = Scene(); s.name = name; s.__dict__.update(k); return s


SCENES = {}


def build_scenes():
    SCENES['garage'] = scene('garage',
        sky=[[20, 16, 12], [40, 31, 24], [50, 40, 30]], far=None, mid=make_tile(3360, MIDBASE, garage_mid, 1), mid_opaque=True,
        road=[[70, 60, 52], [44, 38, 33]], near=[[44, 38, 33], [26, 22, 19]], refl=0.22, lane=None, seams=300,
        env=dict(sky_refl=[190, 150, 110], ground_refl=[70, 55, 40], accent=[255, 190, 110]), lights=0.6)
    SCENES['country'] = scene('country',
        sky=[[92, 140, 196], [176, 196, 214], [246, 216, 168]], far=make_tile(3200, HORIZON + 10, country_far, 2),
        mid=make_tile(3000, MIDBASE, country_mid, 3), road=[[66, 68, 72], [52, 54, 58]], near=[[86, 112, 60], [52, 72, 38]],
        refl=0.0, lane=[240, 240, 230], env=dict(sky_refl=[200, 205, 215], ground_refl=[90, 92, 70], accent=[110, 220, 255]), lights=0.0,
        sun=(1500, 300, [255, 240, 200], 0.6))
    SCENES['highway'] = scene('highway',
        sky=[[36, 28, 70], [126, 64, 110], [242, 140, 80], [255, 214, 140]], far=make_tile(3600, HORIZON + 10, highway_far, 4),
        mid=make_tile(3120, MIDBASE, highway_mid, 5), road=[[60, 48, 64], [36, 30, 42]], near=[[70, 58, 72], [40, 32, 44]],
        refl=0.10, lane=[255, 236, 210], env=dict(sky_refl=[250, 170, 130], ground_refl=[70, 50, 66], accent=[110, 220, 255]), lights=0.5,
        sun=(1480, 610, [255, 200, 120], 1.0))
    SCENES['city'] = scene('city',
        sky=[[6, 9, 24], [14, 20, 48], [44, 36, 80]], far=make_tile(3400, HORIZON + 50, city_far, 6),
        mid=make_tile(3360, MIDBASE, city_mid, 7), road=[[28, 30, 44], [12, 14, 24]], near=[[30, 32, 46], [14, 16, 26]],
        refl=0.30, lane=[220, 220, 230], env=dict(sky_refl=[110, 120, 180], ground_refl=[30, 30, 50], accent=[110, 220, 255]), lights=1.0)
    SCENES['factory'] = scene('factory',
        sky=[[54, 60, 70], [150, 158, 170], [196, 202, 210]], far=make_tile(3200, HORIZON + 10, factory_far, 8),
        mid=make_tile(3040, MIDBASE, factory_mid, 9), road=[[176, 182, 190], [120, 126, 136]], near=[[130, 136, 146], [92, 98, 108]],
        refl=0.30, lane=[250, 200, 30], env=dict(sky_refl=[225, 230, 240], ground_refl=[140, 145, 155], accent=[90, 220, 255]), lights=0.4,
        robots=True)
    SCENES['future'] = scene('future',
        sky=[[4, 6, 18], [10, 22, 56], [26, 90, 140]], far=make_tile(3400, HORIZON + 50, future_far, 10),
        mid=make_tile(3360, MIDBASE, future_mid, 11), road=[[18, 26, 46], [6, 8, 18]], near=[[10, 16, 32], [4, 6, 14]],
        refl=0.38, lane=[90, 235, 255], glowlane=True, env=dict(sky_refl=[90, 150, 220], ground_refl=[20, 40, 70], accent=[90, 235, 255]),
        lights=1.0, flyers=True, stars=True)


SCHEDULE = [(0.0, 'garage'), (4.6, 'country'), (9.4, 'highway'), (19.4, 'city'), (32.9, 'factory'), (40.4, 'future')]


def scene_at(t):
    cur = SCHEDULE[0][1]
    for t0, n in SCHEDULE:
        if t >= t0:
            cur = n
    return cur


def blend_env(t, width=1.2):
    """Time-blended environment (sky colours, car reflections)."""
    for i, (t0, n) in enumerate(SCHEDULE):
        if i > 0 and abs(t - t0) < width:
            prev = SCHEDULE[i - 1][1]
            u = smooth((t - t0 + width) / (2 * width))
            return prev, n, u
    return scene_at(t), scene_at(t), 0.0


def mix_env(a, b, u):
    ea, eb = SCENES[a].env, SCENES[b].env
    out = {}
    for k in ea:
        out[k] = list(np.array(ea[k], float) * (1 - u) + np.array(eb[k], float) * u)
    return out


# =============================================================== drawing per frame
def draw_sky(cv, sc, alpha, t):
    cols = [col(c, alpha) for c in sc.sky]
    lin(cv, skia.Rect(0, -900, W, HORIZON + 60), 0, HORIZON + 60, cols)
    if getattr(sc, 'stars', False):
        rng = np.random.default_rng(3)
        for i in range(160):
            x, y = rng.uniform(0, W), rng.uniform(0, 520)
            tw = 0.5 + 0.5 * math.sin(t * 3 + i)
            cv.drawCircle(x, y, rng.uniform(0.6, 1.8), P(Color=col([220, 235, 255], alpha * (0.3 + 0.5 * tw))))
    if getattr(sc, 'sun', None):
        x, y, c, a = sc.sun
        glow(cv, x, y, 520, c, 0.45 * a * alpha)
        cv.drawCircle(x, y, 62, P(Color=col(np.clip(np.array(c) + 30, 0, 255), alpha * a)))


def draw_flyers(cv, t, alpha):
    rng = np.random.default_rng(21)
    for i in range(9):
        y = rng.uniform(120, 460); v = rng.uniform(-260, 180); ph = rng.uniform(0, 3000)
        x = (ph + v * t) % 2600 - 340
        c = [[90, 235, 255], [255, 120, 220], [255, 255, 255]][i % 3]
        tp = P(); tp.setShader(skia.GradientShader.MakeLinear([skia.Point(x, y), skia.Point(x - 120 * np.sign(v), y)],
                                                             [col(c, 0.7 * alpha), col(c, 0)]))
        cv.drawRect(skia.Rect(min(x, x - 120 * np.sign(v)), y - 1.5, max(x, x - 120 * np.sign(v)), y + 1.5), tp)
        glow(cv, x, y, 14, c, 0.9 * alpha)


def draw_robot(cv, x, t, seed):
    """Red industrial robot arm on a pedestal, animated."""
    r = np.random.default_rng(seed)
    ph = r.uniform(0, 6)
    base_y = MIDBASE
    cv.save(); cv.translate(x, base_y); cv.scale(0.62, 0.62); cv.translate(-x, -base_y)
    red = col([196, 28, 36]); dark = col([40, 40, 44])
    cv.drawRect(skia.Rect(x - 40, base_y - 30, x + 40, base_y), P(Color=dark))
    cv.drawRoundRect(skia.Rect(x - 30, base_y - 80, x + 30, base_y - 30), 8, 8, P(Color=red))
    a1 = math.radians(-70 + 20 * math.sin(t * 1.6 + ph))
    a2 = math.radians(80 + 30 * math.sin(t * 2.1 + ph * 1.3))
    j0 = np.array([x, base_y - 80])
    j1 = j0 + 170 * np.array([math.cos(a1), math.sin(a1)])
    j2 = j1 + 140 * np.array([math.cos(a1 + a2), math.sin(a1 + a2)])
    for (pa, pb, wd) in ((j0, j1, 34), (j1, j2, 26)):
        cv.drawLine(pa[0], pa[1], pb[0], pb[1], P(Style=skia.Paint.kStroke_Style, StrokeWidth=wd, StrokeCap=skia.Paint.kRound_Cap, Color=red))
    for j, rr in ((j0, 22), (j1, 18), (j2, 12)):
        cv.drawCircle(j[0], j[1], rr, P(Color=dark))
    cv.drawRect(skia.Rect(j2[0] - 5, j2[1], j2[0] + 5, j2[1] + 30), P(Color=dark))
    if math.sin(t * 9 + ph) > 0.7:
        glow(cv, j2[0], j2[1] + 34, 40, [255, 240, 200], 0.9)
    cv.restore()


def layer_bounds(t, speed):
    """Screen-x boundaries between scenes for a layer of given speed. Returns list of (name, x0, x1)."""
    out = []
    xs = [-1e9] + [960 + (t0 - t) * speed for t0, _ in SCHEDULE[1:]] + [1e9]
    for i, (_, n) in enumerate(SCHEDULE):
        x0, x1 = max(xs[i], 0), min(xs[i + 1], W)
        if x1 > x0:
            out.append((n, x0, x1))
    return out


def draw_background(cv, t, dist, yoff=0.0):
    """dist: px travelled by near layer. yoff: world vertical shift (lift-off)."""
    a, b, u = blend_env(t, 1.0)
    cv.save(); cv.translate(0, yoff * 0.15)
    for name, al in ((a, 1.0), (b, u)):
        if al <= 0.001:
            continue
        sc = SCENES[name]
        draw_sky(cv, sc, al, t)
    cv.restore()
    # far layer: time crossfade
    cv.save(); cv.translate(0, yoff * 0.35)
    for name, al in ((a, 1.0 - (u if a != b else 0)), (b, u)):
        sc = SCENES[name]
        if al > 0.001 and sc.far is not None:
            draw_tile(cv, sc.far, dist * SPEED['far'] / SPEED['near'], 0, al)
        if al > 0.001 and getattr(sc, 'flyers', False):
            draw_flyers(cv, t, al)
    cv.restore()
    # mid + road + near: spatial boundaries scroll in from the right
    cv.save(); cv.translate(0, yoff * 0.7)
    for name, x0, x1 in layer_bounds(t, SPEED['mid']):
        sc = SCENES[name]
        cv.save(); cv.clipRect(skia.Rect(x0, -400, x1, MIDBASE + 2))
        off = dist * SPEED['mid'] / SPEED['near']
        draw_tile(cv, sc.mid, off, 0)
        if name == 'garage' and x1 < W:
            cv.drawRect(skia.Rect(x1 - 60, 0, x1, MIDBASE), P(Color=col([34, 28, 23])))
            cv.drawRect(skia.Rect(x1 - 60, 0, x1 - 54, MIDBASE), P(Color=col([90, 72, 56], 0.5)))
            lin(cv, skia.Rect(x1 - 60, 0, x1, 120), 0, 120, [col([20, 16, 13]), col([46, 38, 30])])
        if getattr(sc, 'robots', False):
            for k in range(-1, 6):
                base = 420 + k * 760
                xx = (base - off) % (760 * 4) - 300
                draw_robot(cv, xx, t, k + 10)
        cv.restore()
    cv.restore()
    cv.save(); cv.translate(0, yoff)
    for name, x0, x1 in layer_bounds(t, SPEED['near']):
        sc = SCENES[name]
        cv.save(); cv.clipRect(skia.Rect(x0, MIDBASE, x1, H + 1200))
        draw_road(cv, sc, dist, t)
        # reflection of the mid layer on glossy floors
        if sc.refl > 0:
            cv.save(); cv.clipRect(skia.Rect(x0, ROAD_T, x1, ROAD_B))
            draw_tile(cv, sc.mid, dist * SPEED['mid'] / SPEED['near'], MIDBASE, sc.refl * 0.6, flip=True)
            cv.restore()
            lin(cv, skia.Rect(x0, ROAD_T, x1, ROAD_B), ROAD_T, ROAD_B, [col(sc.road[0], 0.0), col(sc.road[1], 0.85)])
        cv.restore()
    cv.restore()


def draw_road(cv, sc, dist, t):
    lin(cv, skia.Rect(0, ROAD_T, W, ROAD_B), ROAD_T, ROAD_B, [col(sc.road[0]), col(sc.road[1])])
    lin(cv, skia.Rect(0, ROAD_B, W, H + 1200), ROAD_B, H, [col(sc.near[0]), col(sc.near[1])])
    off = dist % 300
    if sc.name in ('garage',):
        for x in np.arange(-off, W + 300, 300):
            cv.drawRect(skia.Rect(x, ROAD_T, x + 3, H + 1200), P(Color=col([20, 16, 13], 0.6)))
    if sc.name == 'country':
        r = np.random.default_rng(5)
        o = dist % 40
        for x in np.arange(-o, W + 40, 40):
            for k in range(5):
                gx = x + r.uniform(0, 40); gy = ROAD_B + r.uniform(10, 170)
                cv.drawLine(gx, gy, gx + 4, gy - 16, P(Style=skia.Paint.kStroke_Style, StrokeWidth=2, Color=col([110, 140, 70], 0.7)))
    if sc.name in ('factory',):
        o = dist % 120
        for x in np.arange(-o, W + 120, 120):
            pth = skia.Path(); pth.moveTo(x, ROAD_B + 30); pth.lineTo(x + 50, ROAD_B + 30); pth.lineTo(x + 80, ROAD_B + 60); pth.lineTo(x + 30, ROAD_B + 60); pth.close()
            cv.drawPath(pth, P(Color=col([240, 190, 20], 0.85)))
            pth2 = skia.Path(); pth2.moveTo(x + 50, ROAD_B + 30); pth2.lineTo(x + 110, ROAD_B + 30); pth2.lineTo(x + 140, ROAD_B + 60); pth2.lineTo(x + 80, ROAD_B + 60); pth2.close()
            cv.drawPath(pth2, P(Color=col([24, 24, 24], 0.85)))
    if sc.name == 'future':
        o = dist % 80
        for x in np.arange(-o, W + 80, 80):
            cv.drawLine(x, ROAD_B, x - 200, H + 400, P(Style=skia.Paint.kStroke_Style, StrokeWidth=1, Color=col([90, 235, 255], 0.18)))
        for yy in (ROAD_B + 40, ROAD_B + 110):
            cv.drawLine(0, yy, W, yy, P(Style=skia.Paint.kStroke_Style, StrokeWidth=1, Color=col([90, 235, 255], 0.15)))
    if sc.lane is not None:
        lc = sc.lane
        cv.drawRect(skia.Rect(0, ROAD_T + 6, W, ROAD_T + 9), P(Color=col(lc, 0.55)))
        cv.drawRect(skia.Rect(0, ROAD_B - 9, W, ROAD_B - 5), P(Color=col(lc, 0.8)))
        o = dist % 260
        for x in np.arange(-o, W + 260, 260):
            cv.drawRect(skia.Rect(x, 858, x + 140, 866), P(Color=col(lc, 0.85)))
        if getattr(sc, 'glowlane', False):
            gp = P(Style=skia.Paint.kStroke_Style, StrokeWidth=14, Color=col(lc, 0.45))
            gp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 9))
            cv.drawLine(0, ROAD_B - 7, W, ROAD_B - 7, gp)
            cv.drawLine(0, ROAD_T + 7, W, ROAD_T + 7, gp)
            # light pulses racing along the edge
            o2 = (dist * 1.8) % 700
            for x in np.arange(-o2, W + 700, 700):
                glow(cv, x, ROAD_B - 7, 60, lc, 0.9)
    # curb highlight
    cv.drawRect(skia.Rect(0, ROAD_B - 2, W, ROAD_B), P(Color=col([255, 255, 255], 0.12)))
