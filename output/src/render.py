"""Frame renderer for the Bitcoin 16-year history video (skia-python)."""
import math
import os
import zlib

import numpy as np
import skia
from scipy.ndimage import gaussian_filter, gaussian_filter1d, zoom

import btc_common as B
from btc_common import W, H, FPS, EVENTS, NDAYS, LOGP, PRICE, DAYS

CAM = B.get_camera()

# ----------------------------------------------------------------------------
# fonts
# ----------------------------------------------------------------------------

def _tf(name):
    return skia.Typeface.MakeFromFile(os.path.join(B.FONT_DIR, name))


TF = {
    'serif': _tf('NotoSerifSC_900Black.ttf'),
    'serif_b': _tf('NotoSerifSC_700Bold.ttf'),
    'sans': _tf('NotoSansSC_400Regular.ttf'),
    'sans_m': _tf('NotoSansSC_500Medium.ttf'),
    'sans_b': _tf('NotoSansSC_700Bold.ttf'),
    'thin': _tf('Inter_100Thin.ttf'),
    'xlight': _tf('Inter_200ExtraLight.ttf'),
    'light': _tf('Inter_300Light.ttf'),
    'reg': _tf('Inter_400Regular.ttf'),
    'med': _tf('Inter_500Medium.ttf'),
    'semi': _tf('Inter_600SemiBold.ttf'),
    'bold': _tf('Inter_700Bold.ttf'),
}
_FONT_CACHE = {}


def font(key, size):
    k = (key, size)
    f = _FONT_CACHE.get(k)
    if f is None:
        f = skia.Font(TF[key], size)
        f.setSubpixel(True)
        f.setEdging(skia.Font.Edging.kAntiAlias)
        _FONT_CACHE[k] = f
    return f


def col(rgb, a=1.0):
    return skia.Color4f(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0, max(0.0, min(1.0, a)))


def mix(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(c1[i] + (c2[i] - c1[i]) * t for i in range(3))


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_io(x):
    x = clamp(x)
    return x * x * x * (x * (x * 6 - 15) + 10)


def env(t, t0, fin, t1, fout):
    """fade in over fin starting t0, hold, fade out over fout ending t1"""
    if t < t0 or t > t1:
        return 0.0
    a = 1.0
    if fin > 0:
        a = min(a, (t - t0) / fin)
    if fout > 0:
        a = min(a, (t1 - t) / fout)
    return smooth(a)


def text_width(f, s, spacing=0.0):
    if not s:
        return 0.0
    return f.measureText(s) + spacing * (len(s) - 1)


def draw_text(c, s, x, y, f, paint, spacing=0.0, align='left'):
    """draw text with optional letter spacing; align left/right/center"""
    if not s:
        return 0.0
    w = text_width(f, s, spacing)
    if align == 'right':
        x -= w
    elif align == 'center':
        x -= w / 2
    if spacing == 0.0:
        c.drawString(s, x, y, f, paint)
        return w
    glyphs = f.textToGlyphs(s)
    widths = f.getWidths(glyphs)
    pos = []
    cx = x
    for wd in widths:
        pos.append(skia.Point(cx, y))
        cx += wd + spacing
    blob = skia.TextBlob.MakeFromPosText(s, pos, f)
    if blob is not None:
        c.drawTextBlob(blob, 0, 0, paint)
    return w


def P(rgb, a=1.0, **kw):
    p = skia.Paint(AntiAlias=True, Color=col(rgb, a))
    for k, v in kw.items():
        if k == 'stroke':
            p.setStyle(skia.Paint.kStroke_Style)
            p.setStrokeWidth(v)
        elif k == 'blur':
            if v > 0:
                p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, v))
        elif k == 'plus':
            if v:
                p.setBlendMode(skia.BlendMode.kPlus)
        elif k == 'cap':
            p.setStrokeCap(v)
    return p


def radial(c, x, y, r, rgb, a, plus=True, stops=None):
    if r <= 0.5 or a <= 0.002:
        return
    if stops is None:
        colors = [col(rgb, a), col(rgb, a * 0.35), col(rgb, 0)]
        pos = [0.0, 0.35, 1.0]
    else:
        colors = [col(rgb, a * s_a) for s_a, _ in stops]
        pos = [p_ for _, p_ in stops]
    sh = skia.GradientShader.MakeRadial(skia.Point(x, y), r, colors, pos)
    p = skia.Paint(AntiAlias=True, Shader=sh)
    if plus:
        p.setBlendMode(skia.BlendMode.kPlus)
    c.drawCircle(x, y, r, p)


def hstreak(c, x, y, half_len, thick, rgb, a, plus=True):
    if a <= 0.002:
        return
    sh = skia.GradientShader.MakeLinear(
        [skia.Point(x - half_len, y), skia.Point(x + half_len, y)],
        [col(rgb, 0), col(rgb, a * 0.35), col(rgb, a), col(rgb, a * 0.35), col(rgb, 0)],
        [0.0, 0.3, 0.5, 0.7, 1.0])
    p = skia.Paint(AntiAlias=True, Shader=sh)
    if plus:
        p.setBlendMode(skia.BlendMode.kPlus)
    c.drawRect(skia.Rect(x - half_len, y - thick / 2, x + half_len, y + thick / 2), p)


def vstreak(c, x, y0, y1, ypk, thick, rgb, a, a_end=0.0, plus=True, blur=0):
    if a <= 0.002 or y1 <= y0:
        return
    pk = clamp((ypk - y0) / (y1 - y0), 0.001, 0.999)
    sh = skia.GradientShader.MakeLinear(
        [skia.Point(x, y0), skia.Point(x, y1)],
        [col(rgb, 0), col(rgb, a), col(rgb, a_end)], [0.0, pk, 1.0])
    p = skia.Paint(AntiAlias=True, Shader=sh)
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if plus:
        p.setBlendMode(skia.BlendMode.kPlus)
    c.drawRect(skia.Rect(x - thick / 2, y0, x + thick / 2, y1), p)


def star4(c, x, y, size, rgb, a, rot=0.0, plus=True):
    """four-point glint"""
    if a <= 0.003:
        return
    for ang, ln in ((rot, size), (rot + math.pi / 2, size * 0.75)):
        dx, dy = math.cos(ang) * ln, math.sin(ang) * ln
        sh = skia.GradientShader.MakeLinear(
            [skia.Point(x - dx, y - dy), skia.Point(x + dx, y + dy)],
            [col(rgb, 0), col(rgb, a), col(rgb, 0)], [0, 0.5, 1])
        p = skia.Paint(AntiAlias=True, Shader=sh, Style=skia.Paint.kStroke_Style, StrokeWidth=1.6)
        if plus:
            p.setBlendMode(skia.BlendMode.kPlus)
        c.drawLine(x - dx, y - dy, x + dx, y + dy, p)
    radial(c, x, y, size * 0.22, (255, 250, 240), a * 0.9)


# ----------------------------------------------------------------------------
# background assets
# ----------------------------------------------------------------------------
RNG = np.random.default_rng(7)


def _fbm(h, w, seed, scales):
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w))
    for sc, amp in scales:
        hh, ww = max(2, h // sc), max(2, w // sc)
        n = rng.standard_normal((hh + 3, ww + 3))
        n = gaussian_filter(n, 1.0)
        up = zoom(n, (h / hh, w / ww), order=3)[:h, :w]
        if up.shape != (h, w):
            up = np.pad(up, ((0, h - up.shape[0]), (0, w - up.shape[1])), mode='edge')
        out += amp * up
    return out


def _make_nebula():
    h, w = 800, 1440  # covers screen at 1.5x scale with drift margin
    yy, xx = np.mgrid[0:h, 0:w]
    base = _fbm(h, w, 11, [(160, 1.0), (80, 0.55), (40, 0.3), (20, 0.15)])
    wisp = _fbm(h, w, 23, [(60, 1.0), (24, 0.5), (10, 0.25)])
    # big structures: centre-left plume + right side clouds (as in the reference)
    plume = np.exp(-(((xx - 0.42 * w) / (0.16 * w)) ** 2)) * (0.55 + 0.45 * np.exp(-(((yy - 0.62 * h) / (0.38 * h)) ** 2)))
    right = np.exp(-(((xx - 0.86 * w) / (0.16 * w)) ** 2 + ((yy - 0.58 * h) / (0.30 * h)) ** 2))
    topr = np.exp(-(((xx - 0.72 * w) / (0.20 * w)) ** 2 + ((yy - 0.12 * h) / (0.18 * h)) ** 2))
    field = base * 0.9 + 0.8 * plume + 0.55 * right + 0.35 * topr
    field = (field - np.percentile(field, 35)) / (np.percentile(field, 99.6) - np.percentile(field, 35))
    field = np.clip(field, 0, 1) ** 1.6
    detail = np.clip(0.5 + 0.35 * wisp, 0, 1)
    neb = np.clip(field * (0.55 + 0.6 * detail), 0, 1.2)
    # faint secondary haze
    haze = np.clip((_fbm(h, w, 41, [(200, 1.0), (100, 0.4)]) + 1.0) / 2.6, 0, 1) ** 2
    return neb.astype(np.float32), haze.astype(np.float32)


_NEB_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nebula.npz')
if os.path.exists(_NEB_CACHE):
    _z = np.load(_NEB_CACHE)
    NEB, HAZE = _z['neb'], _z['haze']
else:
    NEB, HAZE = _make_nebula()
    np.savez(_NEB_CACHE, neb=NEB, haze=HAZE)

NSTAR = 260
STARS = np.column_stack([RNG.uniform(0, W, NSTAR), RNG.uniform(0, H, NSTAR),
                         RNG.uniform(0.15, 0.6, NSTAR), RNG.uniform(0.6, 1.6, NSTAR),
                         RNG.uniform(0, 6.28, NSTAR)])
NDUST = 46
DUST = np.column_stack([RNG.uniform(0, W, NDUST), RNG.uniform(0, H, NDUST),
                        RNG.uniform(0.15, 0.5, NDUST), RNG.uniform(5, 22, NDUST),
                        RNG.uniform(-25, -6, NDUST), RNG.uniform(-6, 6, NDUST)])

BG_BLUE = np.array([18, 44, 118], np.float32)
BG_WARM = np.array([92, 34, 22], np.float32)
BG_TEAL = np.array([14, 62, 66], np.float32)
BG_BASE = np.array([1, 3, 12], np.float32)

# vignette image
_vy, _vx = np.mgrid[0:270, 0:480]
_vd = np.sqrt(((_vx - 240) / 240.0) ** 2 * 0.9 + ((_vy - 135) / 135.0) ** 2 * 1.1)
_vig = np.clip((_vd - 0.55) / 0.75, 0, 1) ** 1.5 * 0.82
VIG = np.zeros((270, 480, 4), np.uint8)
VIG[..., 3] = (_vig * 255).astype(np.uint8)
VIG_IMG = skia.Image.fromarray(VIG, colorType=skia.kRGBA_8888_ColorType)

SAMP = skia.SamplingOptions(skia.FilterMode.kLinear)


def draw_background(c, t, warm, teal, dim=1.0, drift=(0.0, 0.0)):
    h, w = NEB.shape
    ox = int(clamp(80 + 70 * math.sin(t / 37.0) + drift[0], 0, w - 1280))
    oy = int(clamp(40 + 35 * math.sin(t / 29.0 + 1) + drift[1], 0, h - 720))
    sub = NEB[oy:oy + 720, ox:ox + 1280]
    hz = HAZE[oy:oy + 720, ox:ox + 1280]
    cblue = BG_BLUE * (1 - 0.75 * warm - 0.55 * teal)
    ccol = cblue + BG_WARM * warm + BG_TEAL * teal
    img = BG_BASE[None, None, :] + sub[..., None] * ccol[None, None, :] * dim + hz[..., None] * (ccol * 0.18)[None, None, :] * dim
    rgba = np.empty((720, 1280, 4), np.uint8)
    rgba[..., :3] = np.clip(img, 0, 255).astype(np.uint8)
    rgba[..., 3] = 255
    im = skia.Image.fromarray(rgba, colorType=skia.kRGBA_8888_ColorType)
    c.drawImageRect(im, skia.Rect(0, 0, W, H), SAMP, skia.Paint())
    # stars
    tw = 0.5 + 0.5 * np.sin(STARS[:, 4] + t * 1.3)
    for i in range(0, NSTAR, 1):
        a = STARS[i, 2] * (0.55 + 0.45 * tw[i]) * dim
        if a < 0.05:
            continue
        c.drawCircle(STARS[i, 0], STARS[i, 1], STARS[i, 3] * 0.55, P((200, 215, 255), a * 0.7))


def draw_dust(c, t, dim=1.0, speed=1.0):
    for i in range(NDUST):
        x0, y0, a, ln, vx, vy = DUST[i]
        x = (x0 + vx * t * speed * 2.0) % (W + 100) - 50
        y = (y0 + vy * t * speed + 20 * math.sin(t * 0.3 + i)) % H
        ang = math.atan2(vy, vx)
        dx, dy = math.cos(ang) * ln, math.sin(ang) * ln
        c.drawLine(x, y, x - dx, y - dy, P((190, 205, 235), a * 0.55 * dim, stroke=1.2, cap=skia.Paint.kRound_Cap))


def draw_vignette(c):
    c.drawImageRect(VIG_IMG, skia.Rect(0, 0, W, H), SAMP, skia.Paint())


# ----------------------------------------------------------------------------
# camera / projection
# ----------------------------------------------------------------------------
class Cam:
    def __init__(self, h, lh, k, s, hx, hy, theta, roll):
        self.h, self.lh, self.k, self.s = h, lh, k, s
        self.hx, self.hy, self.theta, self.roll = hx, hy, theta, roll
        self.st, self.ct = math.sin(theta), math.cos(theta)
        self.xh = hx - B.CX
        self.yh = B.CY - hy
        self.f = B.F_CAM

    def proj(self, day, lp):
        u = (np.asarray(day, dtype=np.float64) - self.h) * self.k
        v = (np.asarray(lp, dtype=np.float64) - self.lh) * self.s
        den = self.f - u * self.st
        x = B.CX + self.f * (u * self.ct + self.xh) / den
        y = B.CY - self.f * (v + self.yh) / den
        return x, y, self.f / den

    def u_at_x(self, x):
        return self.f * (x - B.CX - self.xh) / (self.f * self.ct + (x - B.CX) * self.st)

    def day_at_x(self, x):
        return self.h + self.u_at_x(x) / self.k

    def lp_at(self, x, y):
        """log price on the chart plane at screen point"""
        u = self.u_at_x(x)
        den = self.f - u * self.st
        v = (B.CY - y) * den / self.f - self.yh
        return self.lh + v / self.s

    def rot_pt(self, x, y):
        if abs(self.roll) < 1e-6:
            return x, y
        cr, sr = math.cos(self.roll), math.sin(self.roll)
        dx, dy = x - self.hx, y - self.hy
        return self.hx + dx * cr - dy * sr, self.hy + dx * sr + dy * cr


def cam_for_frame(fi, t):
    h = B.HEAD[fi]
    cam = Cam(h, logp_at(h), CAM['k'][fi], CAM['s'][fi], CAM['hx'][fi], CAM['hy'][fi],
              CAM['theta'][fi], CAM['roll'][fi])
    return cam


def logp_at(day):
    return B.logp_at(day)


# overview camera for the ending
def overview_cam():
    h = NDAYS - 1.0
    lh = LOGP[-1]
    theta = math.radians(9.0)
    hx, hy = 1690.0, 318.0
    st, ct = math.sin(theta), math.cos(theta)
    f = B.F_CAM
    xh = hx - B.CX
    u0 = f * (270 - B.CX - xh) / (f * ct + (270 - B.CX) * st)
    k = -u0 / h
    den0 = f - u0 * st
    yh = B.CY - hy
    v0 = (B.CY - 905) * den0 / f - yh
    s = v0 / (LOGP[0] - lh)
    return Cam(h, lh, k, s, hx, hy, theta, 0.0)


OVCAM = overview_cam()


def interp_cam(a, b, x):
    e = ease_io(x)
    k = math.exp(math.log(a.k) * (1 - e) + math.log(b.k) * e)
    s = math.exp(math.log(a.s) * (1 - e) + math.log(b.s) * e)
    return Cam(b.h, b.lh, k, s, a.hx + (b.hx - a.hx) * e, a.hy + (b.hy - a.hy) * e,
               a.theta + (b.theta - a.theta) * e, a.roll * (1 - e))


# ----------------------------------------------------------------------------
# chart layers
# ----------------------------------------------------------------------------
UP_C = np.array([255, 92, 66], np.float64)
DN_C = np.array([34, 222, 168], np.float64)
NE_C = np.array([90, 110, 190], np.float64)


def visible_range(cam, extra=1.2):
    d_left = cam.day_at_x(-40)
    lo = int(max(0, math.floor(min(d_left, cam.h) - 2)))
    hi = int(min(NDAYS - 1, math.floor(cam.h)))
    return lo, hi


def line_points(cam):
    lo, hi = visible_range(cam)
    days = DAYS[lo:hi + 1].copy()
    lps = LOGP[lo:hi + 1].copy()
    if cam.h > hi and hi < NDAYS - 1:
        days = np.append(days, cam.h)
        lps = np.append(lps, cam.lh)
    x, y, sc = cam.proj(days, lps)
    return days, lps, x, y, sc, lo


def draw_curtains(c, cam, t, intensity=1.0):
    """red/green light curtains below the price line, computed at half-res in numpy"""
    days, lps, x, y, sc, lo = line_points(cam)
    if len(days) < 2 or intensity <= 0.01:
        return
    hw, hh = W // 2, H // 2
    xs, ys = x / 2.0, y / 2.0
    idx = np.clip(np.round(days).astype(int), 0, NDAYS - 1)
    r1 = B.RET1[idx]
    r5 = B.RET5[idx]
    trend = np.clip(r5 / 0.035, -1, 1)
    spike = np.clip(np.abs(r1) / 0.045, 0, 1) ** 0.9
    sign = np.sign(0.55 * np.clip(r1 / 0.02, -1, 1) + 0.45 * trend)
    spike = np.clip((np.abs(r1) - 0.004) / 0.05, 0, 1) ** 1.1
    inten = 0.34 * np.abs(trend) + 0.70 * spike + 0.04
    # recent days near the head glow brighter
    age = cam.h - days
    inten *= 1.0 + 1.5 * np.exp(-age / 4.0)
    # wide bars (zoomed in) would read as solid neon blocks: tone them down
    ppd = cam.k / 2.0  # half-res px per day at head depth
    inten *= clamp(5.0 / max(ppd, 1e-3), 0.32, 1.0)
    colr = np.where(sign[:, None] >= 0, UP_C[None, :], DN_C[None, :])
    wneu = np.clip(1 - (np.abs(trend) * 0.7 + spike), 0, 1)[:, None] * 0.55
    colr = colr * (1 - wneu) + NE_C[None, :] * wneu
    # column binning
    cols = np.arange(hw) + 0.5
    order = np.argsort(xs)
    xs_o = xs[order]
    j = np.searchsorted(xs_o, cols) - 1
    valid = (j >= 0) & (j < len(xs_o) - 1)
    jc = np.clip(j, 0, len(xs_o) - 1)
    # dense columns: max over days falling into the column
    edges = np.searchsorted(xs_o, np.arange(hw + 1))
    I_col = inten[order][jc].copy()
    C_col = colr[order][jc].copy()
    cnt = edges[1:] - edges[:-1]
    dense = np.nonzero(cnt > 1)[0]
    if len(dense):
        io = inten[order]
        co = colr[order]
        for ci in dense:
            a, b_ = edges[ci], edges[ci + 1]
            k = a + int(np.argmax(io[a:b_]))
            I_col[ci] = io[a:b_].max()
            wsum = io[a:b_].sum() + 1e-6
            C_col[ci] = (co[a:b_] * io[a:b_, None]).sum(0) / wsum
    ytop = np.interp(cols, xs_o, ys[order])
    scl = np.interp(cols, xs_o, sc[order])
    on = valid & (cols >= xs_o[0]) & (cols <= xs_o[-1])
    I_col = np.where(on, I_col, 0.0) * intensity
    L = 150.0 * scl
    rows = np.arange(hh)[:, None] + 0.5
    z = (rows - ytop[None, :]) / L[None, :]
    prof = np.where(z > 0, np.exp(-z * 1.15) * (1 - np.exp(-z * 18)), 0.0)
    alpha = prof * I_col[None, :]
    img = alpha[..., None] * C_col[None, :, :] * 0.95
    img = gaussian_filter1d(img, 2.2, axis=1)
    img = gaussian_filter1d(img, 2.0, axis=0)
    rgba = np.empty((hh, hw, 4), np.uint8)
    rgba[..., :3] = np.clip(img, 0, 255).astype(np.uint8)
    rgba[..., 3] = 255
    im = skia.Image.fromarray(rgba, colorType=skia.kRGBA_8888_ColorType)
    c.drawImageRect(im, skia.Rect(0, 0, W, H), SAMP, skia.Paint(BlendMode=skia.BlendMode.kPlus))


def line_colors(days):
    idx = np.clip(np.round(days).astype(int), 0, NDAYS - 1)
    m = np.clip(B.RET10[idx] / 0.07, -1, 1)
    m = np.convolve(m, np.ones(3) / 3, mode='same') if len(m) > 3 else m
    return m


def mcolor(m):
    neutral = (255, 238, 218)
    if m >= 0:
        return mix(neutral, (255, 118, 86), m)
    return mix(neutral, (66, 232, 192), -m)


def draw_line(c, cam, t, style=1.0, alpha=1.0):
    days, lps, x, y, sc, lo = line_points(cam)
    if len(days) < 2:
        return
    m = line_colors(days)
    q = np.clip(np.round((m + 1) * 4), 0, 8).astype(int)  # 9 colour buckets
    # build runs
    runs = []
    start = 0
    for i in range(1, len(q)):
        if q[i] != q[start]:
            runs.append((start, i, q[start]))
            start = i
    runs.append((start, len(q) - 1, q[start]))
    pts = [skia.Point(float(a), float(b)) for a, b in zip(x, y)]
    glow_w = 15.0 * style
    for (a, b_, qq) in runs:
        if b_ <= a:
            continue
        mm = qq / 4.0 - 1.0
        rgb = mcolor(mm)
        path = skia.Path.Polygon(pts[a:b_ + 1], False)
        c.drawPath(path, P(rgb, 0.42 * alpha, stroke=glow_w, blur=11 * style, plus=True))
        c.drawPath(path, P(rgb, 0.75 * alpha, stroke=5.0 * style, blur=2.6 * style, plus=True))
    full = skia.Path.Polygon(pts, False)
    for (a, b_, qq) in runs:
        if b_ <= a:
            continue
        mm = qq / 4.0 - 1.0
        rgb = mix((255, 252, 246), mcolor(mm), 0.35)
        path = skia.Path.Polygon(pts[a:b_ + 1], False)
        c.drawPath(path, P(rgb, alpha, stroke=1.9 * max(style, 0.7), plus=False))


def draw_head(c, cam, t, m, scale=1.0, alpha=1.0):
    x, y = cam.hx, cam.hy
    glow = mcolor(m)
    radial(c, x, y, 190 * scale, glow, 0.22 * alpha)
    radial(c, x, y, 62 * scale, (255, 244, 228), 0.75 * alpha)
    radial(c, x, y, 14 * scale, (255, 255, 255), 1.0 * alpha, stops=[(1, 0), (0.9, 0.5), (0, 1)])
    hstreak(c, x, y, 520 * scale, 2.4, glow, 0.65 * alpha)
    hstreak(c, x, y, 300 * scale, 10, glow, 0.12 * alpha)
    vstreak(c, x, y - 110 * scale, y + 110 * scale, y, 1.4, glow, 0.35 * alpha)
    star4(c, x, y, 34 * scale, (255, 250, 240), 0.45 * alpha, rot=t * 0.4)


def nice_levels(lmin, lmax):
    out = []
    for e in range(-3, 7):
        for mlt in (1, 2, 5):
            v = mlt * 10 ** e
            lv = math.log10(v)
            if lmin - 0.5 <= lv <= lmax + 0.5:
                out.append((v, lv, mlt == 1))
    return out


def draw_grid(c, cam, t, alpha=1.0, labels=True, hl=None):
    lo, hi = visible_range(cam)
    seg = LOGP[lo:hi + 1]
    lmin = min(seg.min(), cam.lh) - 0.6
    lmax = max(seg.max(), cam.lh) + 0.6
    # screen y of a level at the label x
    lab_x = 640.0
    u_l = cam.u_at_x(lab_x)
    day_l = cam.h + u_l / cam.k
    levels = nice_levels(lmin, lmax)
    ys = {}
    for v, lv, major in levels:
        _, yy, _ = cam.proj(day_l, lv)
        ys[v] = float(yy)
    xl0 = cam.day_at_x(-60)
    xr0 = cam.day_at_x(W + 60)
    for v, lv, major in levels:
        # spacing to nearest neighbours
        yv = ys[v]
        if yv < -200 or yv > H + 200:
            continue
        neigh = [abs(ys[o] - yv) for o, _, _ in levels if o != v]
        gap = min(neigh) if neigh else 999
        a_vis = smooth((gap - 45) / 50.0) if not major else smooth((gap - 18) / 30.0)
        a = alpha * a_vis
        is_hl = hl is not None and abs(v - hl[0]) < 1e-9
        if a <= 0.01 and not is_hl:
            continue
        x0, y0, _ = cam.proj(xl0, lv)
        x1, y1, _ = cam.proj(xr0, lv)
        if major:
            p = P((175, 190, 225), 0.30 * a, stroke=1.1)
        else:
            p = P((175, 190, 225), 0.22 * a, stroke=1.0)
            p.setPathEffect(skia.DashPathEffect.Make([14.0, 10.0], 0.0))
        c.drawLine(float(x0), float(y0), float(x1), float(y1), p)
        if is_hl and hl[1] > 0:
            c.drawLine(float(x0), float(y0), float(x1), float(y1), P((240, 240, 250), 0.55 * hl[1], stroke=1.6))
        if labels and a > 0.02:
            draw_text(c, B.fmt_level(v), lab_x, yv - 8, font('med', 15), P((147, 151, 169), 0.85 * a), spacing=0.8, align='center')


# ----------------------------------------------------------------------------
# events, milestones
# ----------------------------------------------------------------------------
SPARKS = {}


def sparks_for(key, n, kind):
    s = SPARKS.get(key)
    if s is None:
        rng = np.random.default_rng(zlib.crc32(repr(key).encode()))
        if kind == 'down':
            ang = rng.uniform(math.pi * 0.25, math.pi * 0.75, n)
            spd = rng.uniform(60, 330, n)
        else:
            ang = rng.uniform(0, 2 * math.pi, n)
            spd = rng.uniform(70, 430, n) * rng.uniform(0.4, 1.0, n)
        life = rng.uniform(0.6, 1.6, n)
        ln = rng.uniform(4, 16, n)
        s = np.column_stack([np.cos(ang) * spd, np.sin(ang) * spd, life, ln])
        SPARKS[key] = s
    return s


def draw_sparks(c, x0, y0, age, key, n, rgb, kind='burst', grav=170.0, alpha=1.0):
    s = sparks_for(key, n, kind)
    for vx, vy, life, ln in s:
        if age > life:
            continue
        a = (1 - age / life) ** 1.3 * alpha
        drag = math.exp(-age * 1.6)
        px = x0 + vx * (1 - drag) / 1.6
        py = y0 + vy * (1 - drag) / 1.6 + 0.5 * grav * age * age
        sp = math.hypot(vx * drag, vy * drag + grav * age) + 1e-3
        dx = (vx * drag) / sp * ln
        dy = (vy * drag + grav * age) / sp * ln
        c.drawLine(px, py, px - dx, py - dy, P(rgb, a, stroke=1.3, plus=True, cap=skia.Paint.kRound_Cap))


def event_point(cam, ev):
    x, y, sc = cam.proj(ev.day, LOGP[ev.day])
    return float(x), float(y), float(sc)


def callout_window(i):
    """t_in, t_out for event i callout"""
    ev = EVENTS[i]
    t_in = ev.t - 0.6
    if i + 1 < len(EVENTS):
        t_out = EVENTS[i + 1].t - 0.62
    else:
        t_out = 179.8
    return t_in, t_out


def _label_tops(cam, t):
    """beam top / label baseline per visible event, nudged so labels do not collide"""
    f = font('sans_b', 13)
    placed = []
    tops = {}
    skip = set()
    vis = []
    for i, ev in enumerate(EVENTS):
        if t < ev.t:
            continue
        x, y, _ = event_point(cam, ev)
        if -60 <= x <= W + 60:
            vis.append((x, y, i))
    vis.sort()
    # active milestone labels act as obstacles
    for lv, fd, tm in B.MILESTONE_T:
        if 0 <= t - tm <= 5.0:
            mx, my, _ = cam.proj(fd, math.log10(lv))
            for dy in (-140, -120, -100, -80, -60, -40, -20):
                placed.append((float(mx) - 140, float(my) + dy, 175))
    for x, y, i in vis:
        base = clamp(y - 240, 120, 900)
        if x < 520:
            base = max(base, 385)
        wl = text_width(f, EVENTS[i].label, 0.6) / 2 + 6
        top = base
        for _ in range(8):
            hit = any(abs(x - px) < wl + pw and abs(top - py) < 18 for px, py, pw in placed)
            if not hit:
                break
            top -= 19
        placed.append((x, top, wl))
        tops[i] = top
        if x < 520 and top < 380:
            skip.add(i)
    recent = [i for _, _, i in sorted(vis, key=lambda v: v[2])][-9:]
    for _, _, i in vis:
        if i not in recent:
            skip.add(i)
    return tops, skip


def draw_event_fx(c, cam, t, ending=0.0):
    tops, skip = _label_tops(cam, t)
    for i, ev in enumerate(EVENTS):
        a = t - ev.t
        if a < 0 or i not in tops:
            continue
        x, y, sc = event_point(cam, ev)
        rgb = ev.color
        light = mix(rgb, (255, 255, 255), 0.35)
        # persistent beam / spike
        t_in, t_out = callout_window(i)
        label_a = smooth((t - t_out) / 0.6)
        beam_a = 0.85 * math.exp(-a / 0.9) + 0.26
        top = tops[i]
        if ending > 0:
            top = top + (y - 70 - top) * ending
        bot = H if ending <= 0 else H + (y + 70 - H) * ending
        vstreak(c, x, top, bot, y, 1.6, rgb, beam_a * (1 - 0.3 * ending), a_end=0.12 * (1 - ending))
        if a < 1.5:
            vstreak(c, x, top - 60, H, y, 7, rgb, 0.35 * math.exp(-a / 0.5), blur=4)
        # label for past events
        if label_a > 0 and ending < 0.6 and i not in skip:
            la = label_a * (1 - ending / 0.6) * 0.85
            wl = text_width(font('sans_b', 13), ev.label, 0.6) / 2
            la *= smooth((x - wl - 4) / 40.0) * smooth((W - x - wl - 4) / 40.0)
            draw_text(c, ev.label, x, top - 10, font('sans_b', 13), P(mix(rgb, (255, 255, 255), 0.15), la), spacing=0.6, align='center')
        # flash
        if a < 0.8:
            e = a / 0.8
            radial(c, x, y, 40 + 170 * ease_out(e), light, 0.9 * (1 - e) ** 2)
            hstreak(c, x, y, 380 * (0.4 + 0.6 * ease_out(e)), 2.0, light, 0.8 * (1 - e))
        # ring
        ra = env(a, 0.0, 0.25, 3.3, 0.9)
        if ra > 0 and ending <= 0:
            r = 88 * (0.55 + 0.45 * ease_out(a / 0.35))
            c.drawCircle(x, y, r, P(rgb, 0.55 * ra, stroke=1.5))
            radial(c, x, y, r, rgb, 0.10 * ra)
        # sparks
        if a < 1.7:
            kind = 'down' if ev.negative else 'burst'
            n = 90 if ev.cat in ('开端', '顶点', '新高', '暴涨', '大选') else 55
            draw_sparks(c, x, y, a, ('ev', i), n, light, kind=kind, grav=220 if ev.negative else 120)
        # dot
        if ev.cat in ('上线', '入场', '上市', '法币', '获批', '政策', '科技', '减半'):
            pth = skia.Path()
            r = 5.5
            pth.moveTo(x, y - r)
            pth.lineTo(x + r, y)
            pth.lineTo(x, y + r)
            pth.lineTo(x - r, y)
            pth.close()
            c.drawPath(pth, P(light, 0.9, stroke=1.4))
        else:
            c.drawCircle(x, y, 4.2, P(rgb, 0.95))
            c.drawCircle(x, y, 1.8, P((255, 255, 255), 0.95))


def draw_milestones(c, cam, t, alpha=1.0):
    ms = B.MILESTONE_T
    for mi, (lv, fd, tm) in enumerate(ms):
        a = t - tm
        # an older label gives way as soon as the next milestone fires
        lab_end = 4.6
        if mi + 1 < len(ms):
            lab_end = min(lab_end, ms[mi + 1][2] - tm + 0.1)
        if a < -0.05 or a > 5.0:
            continue
        x, y, sc = cam.proj(fd, math.log10(lv))
        x, y = float(x), float(y)
        e_band = env(a, 0.0, 0.18, 2.8, 1.6) * alpha
        if e_band > 0:
            # level line already highlighted in grid; golden band
            half_l = 230 + 140 * ease_out(a / 0.6)
            for thick, aa, bl in ((16, 0.30, 8), (6, 0.7, 2.5)):
                p = skia.Paint(AntiAlias=True)
                sh = skia.GradientShader.MakeLinear(
                    [skia.Point(x - half_l, y), skia.Point(x + half_l * 1.2, y)],
                    [col((255, 180, 70), 0), col((255, 190, 90), aa * e_band), col((255, 210, 120), aa * e_band),
                     col((255, 190, 90), aa * e_band * 0.9), col((255, 180, 70), 0)],
                    [0.0, 0.25, 0.45, 0.75, 1.0])
                p.setShader(sh)
                p.setBlendMode(skia.BlendMode.kPlus)
                p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, bl))
                c.drawRect(skia.Rect(x - half_l, y - thick / 2, x + half_l * 1.2, y + thick / 2), p)
            vstreak(c, x, y - 200, H - 60, y, 1.5, (255, 200, 120), 0.7 * e_band, a_end=0.15 * e_band)
        if a >= 0 and a < 1.8:
            draw_sparks(c, x, y, a, ('ms', lv), 120, (255, 214, 150), kind='burst', grav=90)
            radial(c, x, y, 60 + 120 * ease_out(a / 0.6), (255, 230, 180), 0.8 * (1 - clamp(a / 0.9)) ** 2)
        # label
        la = env(a, 0.0, 0.45, lab_end, 0.8 if lab_end >= 4.6 else 0.35) * alpha
        if la > 0:
            rise = 10 * (1 - ease_out(a / 0.5))
            num = '$' + f'{lv:,}'
            draw_text(c, num, x - 30, y - 36 + rise, font('light', 70), P((254, 238, 204), la), spacing=0.5, align='right')
            fnum = font('light', 70)
            wnum = text_width(fnum, num, 0.5)
            draw_text(c, '首次突破', x - 30 - wnum / 2 + 0, y - 118 + rise, font('sans_b', 19), P((228, 197, 150), la), spacing=6, align='center')


def grid_highlight(t):
    for lv, fd, tm in B.MILESTONE_T:
        a = t - tm
        e = env(a, 0.0, 0.15, 3.4, 1.2)
        if e > 0:
            return (lv, e)
    return None


# ----------------------------------------------------------------------------
# HUD
# ----------------------------------------------------------------------------
TXT_GRAY = (162, 166, 184)
TEAL_TXT = (119, 227, 212)
SALMON_TXT = (244, 142, 125)
GOLD_TXT = (240, 196, 118)


def sublabel(i, h):
    """returns (text, rgb) for the line under the value"""
    if h < 90:
        return None
    st = int(SUBTYPE[i])
    if st == 1:
        return ('▲ 历史新高', GOLD_TXT)
    if st == 2:
        return (f'▼ 距最高点 −{B.DRAWDOWN[i] * 100:.1f}%', TEAL_TXT)
    if st == 3:
        j = max(i - 365, 0)
        ch = PRICE[i] / PRICE[j] - 1
        s = f'较一年前 {"+" if ch >= 0 else "−"}{abs(ch) * 100:,.1f}%'
        return (s, SALMON_TXT if ch >= 0 else TEAL_TXT)
    return None


def _subtypes():
    st = np.zeros(NDAYS, np.int8)
    mode = 0
    for i in range(NDAYS):
        dd = B.DRAWDOWN[i]
        if i - B.ATH_DAY[i] <= 5 and dd < 0.01:
            m = 1
        elif dd >= 0.10 or (mode == 2 and dd >= 0.075):
            m = 2
        elif i >= 365:
            m = 3
        else:
            m = 0
        mode = m
        st[i] = m
    return st


SUBTYPE = _subtypes()


def draw_hud(c, t, h, valc, alpha=1.0):
    if alpha <= 0.002:
        return
    d = B.date_of(h)
    i = int(min(max(round(h), 0), NDAYS - 1))
    # top-left
    draw_text(c, 'BITCOIN · BTC / USD', 96, 84, font('bold', 15), P((162, 166, 184), alpha), spacing=5.2)
    draw_text(c, '比特币兑美元', 96, 119, font('sans_b', 20), P((204, 207, 221), alpha), spacing=5.5)
    draw_text(c, str(d.year), 96, 253, font('xlight', 128), P((253, 254, 255), alpha), spacing=2)
    draw_text(c, f'{d.month:02d} · {d.day:02d}', 98, 309, font('light', 31), P((207, 207, 219), alpha), spacing=6.5)
    # top-right
    draw_text(c, '收盘价格', 1818, 90, font('sans_b', 17), P((165, 168, 177), alpha), spacing=5.5, align='right')
    price = 10 ** logp_at(h)
    if valc >= 0:
        vrgb = mix((250, 250, 253), (243, 160, 135), valc)
    else:
        vrgb = mix((250, 250, 253), (110, 214, 200), -valc)
    draw_text(c, B.fmt_price(price), 1818, 187, font('xlight', 100), P(vrgb, alpha), spacing=1.5, align='right')
    sl = sublabel(i, h)
    if sl:
        draw_text(c, sl[0], 1822, 238, font('sans_b', 23), P(sl[1], alpha), spacing=0.8, align='right')


MM_X0, MM_X1 = 96.0, 1824.0
MM_LMIN, MM_LMAX = math.log10(0.05), math.log10(130000)
MM_YEARS = [2012, 2015, 2018, 2021, 2024]


def mm_x(day):
    return MM_X0 + (MM_X1 - MM_X0) * day / (NDAYS - 1)


def mm_y(lp):
    return 1011.0 - (lp - MM_LMIN) / (MM_LMAX - MM_LMIN) * 17.0


def draw_minimap(c, t, h, valc, alpha=1.0):
    if alpha <= 0.002:
        return
    c.drawLine(MM_X0, 1017, MM_X1, 1017, P((150, 160, 190), 0.16 * alpha, stroke=1))
    for yr in MM_YEARS:
        day = (B.dt.date(yr, 1, 1) - B.D0).days
        draw_text(c, str(yr), mm_x(day), 1043, font('med', 14), P((122, 121, 130), alpha), spacing=0.8, align='center')
    hi = int(min(NDAYS - 1, math.floor(h)))
    if hi >= 1:
        step = 3
        idx = list(range(0, hi + 1, step))
        if idx[-1] != hi:
            idx.append(hi)
        pts = [skia.Point(mm_x(j), mm_y(LOGP[j])) for j in idx]
        pts.append(skia.Point(mm_x(h), mm_y(logp_at(h))))
        c.drawPath(skia.Path.Polygon(pts, False), P((225, 230, 240), 0.62 * alpha, stroke=1.3))
    for ev in EVENTS:
        if ev.t <= t:
            c.drawCircle(mm_x(ev.day), mm_y(LOGP[ev.day]), 2.6, P(ev.color, 0.95 * alpha))
    hx, hy = mm_x(h), mm_y(logp_at(h))
    mc = mcolor(valc)
    radial(c, hx, hy, 16, mc, 0.35 * alpha)
    c.drawCircle(hx, hy, 8, P((245, 245, 250), 0.85 * alpha, stroke=1.4))
    c.drawCircle(hx, hy, 3.6, P(mix(mc, (255, 255, 255), 0.2), alpha))


def draw_callout(c, cam, t):
    for i, ev in enumerate(EVENTS):
        t_in, t_out = callout_window(i)
        if t < t_in or t > t_out + 0.4:
            continue
        a_in = ease_out((t - t_in) / 0.45)
        a_out = 1 - smooth((t - t_out) / 0.38)
        a = clamp(min(a_in, a_out))
        if a <= 0.003:
            continue
        slide = 14 * (1 - a_in)
        _callout_box(c, cam, ev, a, slide)


CAT_FONT = 18


def _callout_box(c, cam, ev, a, slide):
    x0, x1, y0 = 1305.0, 1823.0, 292.0 + slide
    ty = y0 + 110
    vy = ty + 70 if ev.value else ty
    dy0 = vy + 46
    last = dy0 + 37 * (len(ev.desc) - 1) if ev.desc else vy
    y1 = last + 33
    rgb = ev.color
    # leader line
    ex, ey, _ = event_point(cam, ev)
    ex, ey = cam.rot_pt(ex, ey)
    if ex > -20:
        la = a * smooth((ex + 20) / 60.0)
        pth = skia.Path()
        pth.moveTo(ex, ey)
        ely = y0 + 65
        pth.lineTo(ex + 60, ely)
        pth.lineTo(x0, ely)
        c.drawPath(pth, P(rgb, 0.6 * la, stroke=1.3))
    # box
    c.drawRect(skia.Rect(x0, y0, x1, y1), P((5, 10, 21), 0.80 * a))
    c.drawRect(skia.Rect(x0 + 0.5, y0 + 0.5, x1 - 0.5, y1 - 0.5), P((120, 140, 175), 0.20 * a, stroke=1))
    c.drawRect(skia.Rect(x0, y0 + 21, x0 + 3, y1 - 21), P(rgb, 0.95 * a))
    # header
    fcat = font('sans_b', CAT_FONT)
    wcat = draw_text(c, ev.cat, 1342, y0 + 46, fcat, P(rgb, a), spacing=4.5)
    draw_text(c, ev.date.replace('-', '.'), 1342 + wcat + 20, y0 + 46, font('reg', 19), P((156, 165, 182), a), spacing=1.2)
    if ev.tag:
        draw_text(c, ev.tag, 1792, y0 + 45, font('semi', 14), P((169, 173, 186), a), spacing=4.2, align='right')
    draw_text(c, ev.title, 1342, ty, font('serif', 44), P((255, 255, 255), a), spacing=0.6)
    if ev.value:
        vrgb = rgb if ev.cat not in ('开端',) else B.GOLD
        draw_text(c, ev.value, 1340, vy, font('light', 60), P(mix(vrgb, (255, 255, 255), 0.08), a), spacing=1.0)
    fd = font('sans_m', 21)
    for k, line in enumerate(ev.desc):
        draw_text(c, line, 1342, dy0 + 37 * k, fd, P((218, 226, 239), 0.93 * a), spacing=0.3)


def draw_era(c, t):
    for (te, label, title) in B.ERA_T:
        a = t - te
        if a < 0 or a > 5.4:
            continue
        a_in = clamp(a / 0.7)
        a_out = clamp((5.4 - a) / 1.0)
        al = smooth(min(a_in, a_out))
        blur = 14 * (1 - ease_out(a_in)) + 16 * (1 - smooth(a_out))
        scale = 1.0 + 0.04 * (1 - ease_out(a_in)) + 0.07 * (1 - smooth(a_out))
        c.save()
        c.translate(96, 860)
        c.scale(scale, scale)
        c.translate(-96, -860)
        lp = skia.Paint(Alphaf=al)
        if blur > 0.3:
            lp.setImageFilter(skia.ImageFilters.Blur(blur, blur))
        c.saveLayer(skia.Rect(0, 650, 1100, 960), lp)
        draw_text(c, label, 97, 777, font('light', 28), P((214, 196, 150), 1.0), spacing=9.5)
        c.drawString  # noqa
        tpaint = P((255, 255, 255), 1.0)
        f = font('serif', 88)
        draw_text(c, title, 94, 888, f, P((255, 250, 240), 0.35, blur=10), spacing=13)
        draw_text(c, title, 94, 888, f, tpaint, spacing=13)
        c.restore()
        c.restore()


# ----------------------------------------------------------------------------
# intro
# ----------------------------------------------------------------------------
PREV_X0, PREV_X1 = 228.0, 1702.0
PREV_Y0, PREV_Y1 = 842.0, 158.0


def prev_xy(day):
    lmin, lmax = LOGP.min(), LOGP.max()
    x = PREV_X0 + (PREV_X1 - PREV_X0) * np.asarray(day) / (NDAYS - 1)
    lp = np.interp(day, DAYS, LOGP)
    y = PREV_Y0 + (lp - LOGP[0]) / (lmax - LOGP[0]) * (PREV_Y1 - PREV_Y0)
    return x, y


PREV_STEP = 4
PREV_IDX = np.arange(0, NDAYS, PREV_STEP)
PREV_XS, PREV_YS = prev_xy(PREV_IDX)
# glint spots: cycle peaks and troughs
GLINT_DAYS = [B.day_of(s) for s in ('2011-06-08', '2011-11-18', '2013-12-04', '2015-01-14', '2017-12-16',
                                     '2018-12-15', '2021-11-08', '2022-11-09', '2025-10-06')]


def draw_intro(c, t):
    gold = (241, 223, 168)
    # ---- title card 0 - 2.9s
    ta = 1.0 - smooth((t - 2.3) / 0.55)
    if ta > 0.002:
        blur = 10 * smooth((t - 2.3) / 0.55)
        lp = skia.Paint(Alphaf=ta)
        if blur > 0.3:
            lp.setImageFilter(skia.ImageFilters.Blur(blur, blur))
        c.saveLayer(None, lp)
        draw_text(c, 'BITCOIN  ·  2010 — 2026', 960, 374, font('semi', 18), P((150, 151, 163), 1.0), spacing=9.0, align='center')
        f = font('serif', 152)
        title = '比特币'
        tw = text_width(f, title, 30)
        tx = 960 - tw / 2
        draw_text(c, title, tx, 578, f, P((240, 200, 120), 0.45, blur=16), spacing=30)
        sh = skia.GradientShader.MakeLinear([skia.Point(0, 440), skia.Point(0, 585)],
                                            [col((250, 236, 196)), col((241, 220, 165)), col((218, 180, 112))],
                                            [0.0, 0.5, 1.0])
        tp = skia.Paint(AntiAlias=True, Shader=sh)
        draw_text(c, title, tx, 578, f, tp, spacing=30)
        # underline
        la = ease_out((t - 0.15) / 0.8)
        if la > 0:
            hl = 190 * la
            sh2 = skia.GradientShader.MakeLinear([skia.Point(960 - hl, 0), skia.Point(960 + hl, 0)],
                                                 [col((210, 200, 180), 0), col((225, 215, 195), 0.7), col((210, 200, 180), 0)],
                                                 [0, 0.5, 1])
            c.drawRect(skia.Rect(960 - hl, 633, 960 + hl, 634.6), skia.Paint(AntiAlias=True, Shader=sh2))
        sa = smooth((t - 0.25) / 0.75)
        if sa > 0:
            draw_text(c, '16年的长牛，从来不是偶然', 960, 712, font('sans_m', 40), P((242, 245, 253), sa), spacing=13, align='center')
        # glint on the title corner
        gl = 0.5 + 0.5 * math.sin(t * 5.5)
        star4(c, tx + tw + 8, 452, 26 + 10 * gl, (255, 250, 235), 0.85 * (0.6 + 0.4 * gl), rot=0.0)
        c.restore()
    # ---- star at left 2.45 - 3.4
    sx0, sy0 = PREV_XS[0], PREV_YS[0]
    if 2.4 <= t < 3.5:
        a = smooth((t - 2.4) / 0.6)
        radial(c, sx0, sy0, 40, (255, 225, 170), 0.6 * a)
        radial(c, sx0, sy0, 9, (255, 255, 250), a)
        hstreak(c, sx0, sy0, 90 * (0.5 + a), 1.6, (255, 220, 160), 0.7 * a)
    # ---- preview line draw 3.3 -> 4.55, hold, retract 5.0 -> 5.6
    if 3.3 <= t < 5.75:
        if t < 4.55:
            p_end = ease_io((t - 3.3) / 1.25)
        elif t < 5.0:
            p_end = 1.0
        else:
            p_end = 1.0 - ease_io((t - 5.0) / 0.6)
        n = max(2, int(len(PREV_IDX) * p_end))
        n = min(n, len(PREV_IDX))
        xs, ys = PREV_XS[:n], PREV_YS[:n]
        pts = [skia.Point(float(a_), float(b_)) for a_, b_ in zip(xs, ys)]
        if len(pts) >= 2:
            pth = skia.Path.Polygon(pts, False)
            c.drawPath(pth, P((255, 205, 130), 0.45, stroke=14, blur=10, plus=True))
            c.drawPath(pth, P((255, 225, 170), 0.8, stroke=5, blur=2.5, plus=True))
            c.drawPath(pth, P((255, 246, 225), 1.0, stroke=2.0))
        hx_, hy_ = float(xs[-1]), float(ys[-1])
        radial(c, hx_, hy_, 120, (255, 210, 150), 0.35)
        radial(c, hx_, hy_, 28, (255, 248, 230), 0.9)
        hstreak(c, hx_, hy_, 260, 2.0, (255, 220, 160), 0.8)
        star4(c, hx_, hy_, 38, (255, 250, 235), 0.7)
        # glints that appear as the line passes
        drawn_day = PREV_IDX[n - 1]
        for gd in GLINT_DAYS:
            if gd <= drawn_day:
                gx, gy = prev_xy(gd)
                age = (drawn_day - gd) / 600.0
                star4(c, float(gx), float(gy), 34 * (1 - 0.4 * clamp(age)), (255, 248, 230), 0.85 * (1 - 0.5 * clamp(age)))
        if t < 5.0:
            # a few drifting sparkles along the drawn line
            for k in range(0, n, max(1, n // 18)):
                tw_ = 0.5 + 0.5 * math.sin(k * 1.7 + t * 9)
                star4(c, float(xs[k]), float(ys[k]), 10 + 8 * tw_, (255, 240, 210), 0.5 * tw_)
    # ---- star travels to centre 5.6 -> 6.4
    tx_, ty_ = 1168.0, 603.0
    if 5.55 <= t < 8.6:
        if t < 6.4:
            e = ease_io((t - 5.55) / 0.85)
            sx = 384 + (tx_ - 384) * e
            sy = 800 + (ty_ - 800) * e - 70 * math.sin(math.pi * e)
        else:
            sx, sy = tx_, ty_
        grow = smooth((t - 7.3) / 1.0)
        # move to chart head position as HUD comes in
        hx_, hy_ = 1173.0, 598.0
        sx = sx + (hx_ - sx) * grow
        sy = sy + (hy_ - sy) * grow
        radial(c, sx, sy, 50 + 100 * grow, (255, 215, 160), 0.55 + 0.2 * grow)
        radial(c, sx, sy, 10 + 18 * grow, (255, 252, 240), 1.0)
        hstreak(c, sx, sy, 230 + 200 * grow, 1.8, (255, 214, 150), 0.85)
        if t < 6.4:
            for k in range(1, 8):
                e2 = ease_io(clamp((t - 0.04 * k - 5.55) / 0.85))
                px = 384 + (tx_ - 384) * e2
                py = 800 + (ty_ - 800) * e2 - 70 * math.sin(math.pi * e2)
                radial(c, px, py, 12, (255, 220, 160), 0.25 * (1 - k / 8))
    # ---- text "一切，从 0.0858 美元开始"
    xa = env(t, 6.35, 0.45, 8.05, 0.55)
    if xa > 0:
        f1 = font('serif', 44)
        f2 = font('xlight', 62)
        parts = [('一切，从', f1, (255, 255, 255), 4), (' 0.0858 ', f2, (243, 217, 160), 1), ('美元开始', f1, (255, 255, 255), 4)]
        total = sum(text_width(f_, s_, sp) for s_, f_, _, sp in parts)
        x = 1098 - total
        lp = skia.Paint(Alphaf=xa)
        c.saveLayer(None, lp)
        for s_, f_, rgb, sp in parts:
            w_ = draw_text(c, s_, x, 625, f_, P(rgb, 1.0), spacing=sp)
            x += w_
        c.restore()


# ----------------------------------------------------------------------------
# ending
# ----------------------------------------------------------------------------
OV_LABELS = [  # (date, text, colour, above)
    ('2010-07-18', '2010 开盘', B.GOLD, True),
    ('2011-06-08', '2011 首次泡沫', B.GOLD, True),
    ('2013-12-04', '2013 顶点', B.GOLD, True),
    ('2015-01-14', '2015 谷底 −85%', B.TEAL, False),
    ('2017-12-16', '2017 ICO 顶点', B.GOLD, True),
    ('2018-12-15', '2018 谷底 −84%', B.TEAL, False),
    ('2020-03-12', '2020 疫情冲击', B.TEAL, False),
    ('2021-11-08', '2021 牛市顶点', B.GOLD, True),
    ('2022-11-09', '2022 FTX 暴雷', B.TEAL, False),
    ('2024-01-10', '2024 ETF 获批', B.PURPLE, False),
    ('2025-10-06', '2025 历史新高', B.GOLD, True),
]


def draw_ending_text(c, t, cam):
    # questions
    qa = env(t, 180.0, 0.5, 183.2, 0.6)
    if qa > 0:
        f = font('serif', 58)
        for k, (s, tq) in enumerate((('牛市终结', 180.0), ('寒冬再临', 181.0))):
            a = env(t, tq, 0.5, 183.2, 0.6)
            if a <= 0:
                continue
            blur = 8 * (1 - ease_out((t - tq) / 0.5))
            lp = skia.Paint(Alphaf=a)
            if blur > 0.3:
                lp.setImageFilter(skia.ImageFilters.Blur(blur, blur))
            c.saveLayer(None, lp)
            y = 400 + 78 * k
            w_ = draw_text(c, s, 1312, y, f, P((255, 255, 255), 1.0), spacing=3)
            draw_text(c, '？', 1312 + w_ + 2, y, f, P((240, 200, 120), 1.0))
            c.restore()
    # overview labels
    if t >= 187.4:
        f = font('sans_b', 16)
        for k, (ds, txt, rgb, above) in enumerate(OV_LABELS):
            a = env(t, 187.4 + 0.09 * k, 0.5, 999, 0)
            if a <= 0:
                continue
            day = B.day_of(ds)
            x, y, _ = cam.proj(day, LOGP[day])
            x, y = float(x), float(y)
            yy = y - 32 if above else y + 44
            align = 'center'
            if ds == '2010-07-18':
                yy, x, align = y + 6, x - 18, 'right'
            draw_text(c, txt, x, yy, f, P(mix(rgb, (255, 255, 255), 0.1), a * 0.95), spacing=1.2, align=align)
    # summary block
    a1 = env(t, 188.4, 0.6, 999, 0)
    if a1 > 0:
        draw_text(c, '2010.07.18  →  2026.05.23', 130, 148, font('reg', 28), P((149, 163, 199), a1), spacing=6.5)
    a2 = env(t, 188.9, 0.6, 999, 0)
    if a2 > 0:
        draw_text(c, '$0.0858 → $76,619.87', 128, 244, font('xlight', 78), P((245, 250, 255), a2), spacing=1.5)
    a3 = env(t, 189.5, 0.5, 999, 0)
    if a3 > 0:
        sc = 1.0 + 0.08 * (1 - ease_out((t - 189.5) / 0.6))
        c.save()
        c.translate(130, 360)
        c.scale(sc, sc)
        c.translate(-130, -360)
        f = font('serif', 94)
        draw_text(c, '约 89 万倍', 128, 372, f, P((245, 196, 110), 0.45 * a3, blur=16), spacing=6)
        sh = skia.GradientShader.MakeLinear([skia.Point(0, 290), skia.Point(0, 377)],
                                            [col((252, 230, 175), a3), col((243, 198, 112), a3)], [0, 1])
        draw_text(c, '约 89 万倍', 128, 372, f, skia.Paint(AntiAlias=True, Shader=sh), spacing=6)
        c.restore()
    a4 = env(t, 190.6, 0.8, 999, 0)
    if a4 > 0:
        blur = 10 * (1 - ease_out((t - 190.6) / 0.8))
        lp = skia.Paint(Alphaf=a4)
        if blur > 0.3:
            lp.setImageFilter(skia.ImageFilters.Blur(blur, blur))
        c.saveLayer(None, lp)
        f = font('serif', 64)
        draw_text(c, '时间，会证明真正的牛市。', 1762, 888, f, P((255, 240, 210), 0.35, blur=12), spacing=4, align='right')
        draw_text(c, '时间，会证明真正的牛市。', 1762, 888, f, P((246, 240, 230), 1.0), spacing=4, align='right')
        c.restore()
    a5 = env(t, 191.6, 0.7, 999, 0)
    if a5 > 0:
        draw_text(c, '数据来源：Coin Metrics（BTC/USD 日收盘价）  ｜  本视频仅为历史数据回顾，不构成任何投资建议',
                  960, 1031, font('sans', 17), P((132, 135, 149), a5), spacing=1.6, align='center')


# ----------------------------------------------------------------------------
# frame
# ----------------------------------------------------------------------------
END_T0 = 183.0
END_T1 = 188.0
_CAM_END_START = None


def render_frame(fi, arr=None):
    global _CAM_END_START
    t = fi / FPS
    if arr is None:
        arr = np.zeros((H, W, 4), np.uint8)
    surf = skia.Surface(arr)
    c = surf.getCanvas()
    c.clear(skia.Color4f(0.004, 0.012, 0.047, 1))
    warm, teal, valc = CAM['warm'][fi], CAM['teal'][fi], CAM['valcol'][fi]
    h = B.HEAD[fi]
    draw_background(c, t, warm, teal)
    draw_dust(c, t)

    hud_a = smooth((t - 7.3) / 0.8) * (1 - smooth((t - 182.7) / 0.6))
    if t < 8.5:
        draw_vignette(c)
        draw_intro(c, t)
        if hud_a > 0:
            draw_hud(c, t, 0.0, 0.0, hud_a)
            draw_minimap(c, t, 0.0, 0.0, hud_a)
        return arr

    # camera
    if t >= END_T0:
        if _CAM_END_START is None:
            fi0 = int(round(END_T0 * FPS))
            _CAM_END_START = cam_for_frame(fi0, END_T0)
        x = (t - END_T0) / (END_T1 - END_T0)
        cam = interp_cam(_CAM_END_START, OVCAM, x)
        ending = ease_io(x)
    else:
        cam = cam_for_frame(fi, t)
        ending = 0.0

    c.save()
    if abs(cam.roll) > 1e-6:
        c.rotate(math.degrees(cam.roll), cam.hx, cam.hy)
    draw_grid(c, cam, t, alpha=1.0 - 0.45 * ending, labels=ending < 0.3, hl=grid_highlight(t))
    draw_curtains(c, cam, t, intensity=1.0 - 0.55 * ending)
    draw_event_fx(c, cam, t, ending=ending)
    style = 1.0 - 0.35 * ending
    draw_line(c, cam, t, style=style)
    draw_milestones(c, cam, t)
    m = float(np.clip(B.RET10[int(min(round(h), NDAYS - 1))] / 0.07, -1, 1))
    if t >= 179.0:
        m *= max(0.0, 1 - (t - 179.0) / 2.0)
    draw_head(c, cam, t, m, scale=1.0 - 0.3 * ending)
    c.restore()

    draw_vignette(c)
    draw_callout(c, cam, t)
    draw_era(c, t)
    if hud_a > 0:
        draw_hud(c, t, h, valc, hud_a)
        draw_minimap(c, t, h, valc, hud_a)
    if t >= 179.5:
        draw_ending_text(c, t, cam)
    return arr


if __name__ == '__main__':
    import sys
    import time
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_frames')
    os.makedirs(out, exist_ok=True)
    ts = [float(a) for a in sys.argv[1:]] or [2.0]
    for tt in ts:
        fi = int(round(tt * FPS))
        t0 = time.time()
        arr = render_frame(fi)
        dt_ = time.time() - t0
        im = skia.Image.fromarray(arr, colorType=skia.kRGBA_8888_ColorType)
        im.save(os.path.join(out, f't_{tt:07.2f}.png'), skia.kPNG)
        print(f'{tt:.2f}s rendered in {dt_ * 1000:.0f} ms')
