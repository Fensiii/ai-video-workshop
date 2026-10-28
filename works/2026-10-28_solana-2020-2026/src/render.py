"""Frame renderer for the crypto price-history videos (skia-python, English copy)."""
import math
import os
import zlib

import numpy as np
import skia
from scipy.ndimage import gaussian_filter, gaussian_filter1d, zoom

import common as B
from common import W, H, FPS, EVENTS, NDAYS, LOGP, PRICE, DAYS, CFG, T_END

CAM = B.get_camera()

# ----------------------------------------------------------------------------
# fonts
# ----------------------------------------------------------------------------

def _tf(name):
    return skia.Typeface.MakeFromFile(os.path.join(B.FONT_DIR, name))


TF = {
    'serif': _tf('PlayfairDisplay_900Black.ttf'),
    'serif_b': _tf('PlayfairDisplay_700Bold.ttf'),
    'serif_i': _tf('PlayfairDisplay_700Bold_Italic.ttf'),
    'thin': _tf('Inter_100Thin.ttf'),
    'xlight': _tf('Inter_200ExtraLight.ttf'),
    'light': _tf('Inter_300Light.ttf'),
    'reg': _tf('Inter_400Regular.ttf'),
    'med': _tf('Inter_500Medium.ttf'),
    'semi': _tf('Inter_600SemiBold.ttf'),
    'bold': _tf('Inter_700Bold.ttf'),
    'xbold': _tf('Inter_800ExtraBold.ttf'),
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


def fit_font(key, size, s, max_w, spacing=0.0, min_size=None):
    """largest font <= size whose text fits max_w"""
    f = font(key, size)
    w = text_width(f, s, spacing)
    if w <= max_w:
        return f
    new = max(size * max_w / w, min_size or size * 0.6)
    return font(key, round(new * 2) / 2)


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


_NEB_CACHE = os.path.join(B.WORK, 'nebula.npz')
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
BG_UP = np.array([12, 70, 56], np.float32)      # rallies: green-teal tint
BG_DOWN = np.array([96, 26, 22], np.float32)    # sell-offs: red tint
BG_BASE = np.array([1, 3, 12], np.float32)

# vignette image
_vy, _vx = np.mgrid[0:270, 0:480]
_vd = np.sqrt(((_vx - 240) / 240.0) ** 2 * 0.9 + ((_vy - 135) / 135.0) ** 2 * 1.1)
_vig = np.clip((_vd - 0.55) / 0.75, 0, 1) ** 1.5 * 0.82
VIG = np.zeros((270, 480, 4), np.uint8)
VIG[..., 3] = (_vig * 255).astype(np.uint8)
VIG_IMG = skia.Image.fromarray(VIG, colorType=skia.kRGBA_8888_ColorType)

SAMP = skia.SamplingOptions(skia.FilterMode.kLinear)


def draw_background(c, t, upm, dnm, dim=1.0, drift=(0.0, 0.0)):
    h, w = NEB.shape
    ox = int(clamp(80 + 70 * math.sin(t / 37.0) + drift[0], 0, w - 1280))
    oy = int(clamp(40 + 35 * math.sin(t / 29.0 + 1) + drift[1], 0, h - 720))
    sub = NEB[oy:oy + 720, ox:ox + 1280]
    hz = HAZE[oy:oy + 720, ox:ox + 1280]
    cblue = BG_BLUE * (1 - 0.75 * upm - 0.55 * dnm)
    ccol = cblue + BG_UP * upm + BG_DOWN * dnm
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


def overview_cam(x_left=270.0, hx=1690.0, OV_TOP=425.0, OV_BOT=950.0, theta_deg=9.0):
    """whole-history camera: first day at x_left, head at hx, closes fitted between y=OV_TOP..OV_BOT"""
    h = NDAYS - 1.0
    lh = LOGP[-1]
    theta = math.radians(theta_deg)
    st, ct = math.sin(theta), math.cos(theta)
    f = B.F_CAM
    xh = hx - B.CX
    u0 = f * (x_left - B.CX - xh) / (f * ct + (x_left - B.CX) * st)
    k = -u0 / h
    u = (DAYS - h) * k
    g = f / (f - u * st)          # perspective factor per day
    a = LOGP - lh

    def ys(s_, hy_):              # screen y of every close: CY - g_i * (a_i * s + CY - hy)
        return B.CY - g * (a * s_ + B.CY - hy_)

    def hy_for(s_):               # head height that puts the highest close on OV_TOP
        hy_ = 318.0
        for _ in range(40):
            hy_ += OV_TOP - ys(s_, hy_).min()
        return hy_

    lo, hi = 1.0, 3000.0          # vertical scale so the lowest close lands on OV_BOT
    for _ in range(60):
        s = 0.5 * (lo + hi)
        if ys(s, hy_for(s)).max() > OV_BOT:
            hi = s
        else:
            lo = s
    return Cam(h, lh, k, lo, hx, hy_for(lo), theta, 0.0)


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
UP_C = np.array([30, 204, 150], np.float64)    # up days glow green
DN_C = np.array([255, 84, 66], np.float64)     # down days glow red
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
    """green/red light curtains below the price line, computed at half-res in numpy"""
    days, lps, x, y, sc, lo = line_points(cam)
    if len(days) < 2 or intensity <= 0.01:
        return
    hw, hh = W // 2, H // 2
    xs, ys = x / 2.0, y / 2.0
    idx = np.clip(np.round(days).astype(int), 0, NDAYS - 1)
    r1 = B.RET1[idx]
    r5 = B.RET5[idx]
    trend = np.clip(r5 / 0.035, -1, 1)
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
        return mix(neutral, (92, 236, 186), m)
    return mix(neutral, (255, 108, 86), -m)


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


LABEL_BOXES = []   # world-space boxes of event labels this frame (grid labels avoid them)


def _hits_label(x, y, w, h):
    for bx0, by0, bx1, by1 in LABEL_BOXES:
        if x - w / 2 < bx1 and x + w / 2 > bx0 and y - h < by1 and y + 4 > by0:
            return True
    return False


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
    fl = font('med', 15)
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
            sx_, sy_ = map_pt(*cam.rot_pt(lab_x, yv - 8))
            a *= keepout(sx_, sy_)
            txt = B.fmt_level(v)
            if _hits_label(lab_x, yv - 8, text_width(fl, txt, 0.8) + 10, 16):
                a *= 0.0
        if labels and a > 0.02:
            draw_text(c, B.fmt_level(v), lab_x, yv - 8, fl, P((147, 151, 169), 0.85 * a), spacing=0.8, align='center')


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
        t_out = T_END + 0.8
    return t_in, t_out


LABEL_FONT = ('semi', 13)


def _label_tops(cam, t):
    """beam top / label baseline per visible event, nudged so labels do not collide"""
    f = font(*LABEL_FONT)
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


def draw_event_fx(c, cam, t, ending=0.0, tops_skip=None):
    tops, skip = tops_skip if tops_skip else _label_tops(cam, t)
    fl = font(*LABEL_FONT)
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
            wl = text_width(fl, ev.label, 0.6) / 2
            la *= smooth((x - wl - 4) / 40.0) * smooth((W - x - wl - 4) / 40.0)
            sx_, sy_ = map_pt(*cam.rot_pt(x, top - 10))
            la *= keepout(sx_, sy_)
            draw_text(c, ev.label, x, top - 10, fl, P(mix(rgb, (255, 255, 255), 0.15), la), spacing=0.6, align='center')
        # flash
        if a < 0.8:
            e = a / 0.8
            radial(c, x, y, 40 + 170 * ease_out(e), light, 0.9 * (1 - e) ** 2)
            hstreak(c, x, y, 380 * (0.4 + 0.6 * ease_out(e)), 2.0, light, 0.8 * (1 - e))
        # ring
        rlife = 3.3
        if i + 1 < len(EVENTS):
            rlife = min(rlife, max(EVENTS[i + 1].t - ev.t + 0.25, 1.6))
        ra = env(a, 0.0, 0.25, rlife, 0.5)
        if ra > 0 and ending <= 0:
            r = 88 * (0.55 + 0.45 * ease_out(a / 0.35))
            c.drawCircle(x, y, r, P(rgb, 0.55 * ra, stroke=1.5))
            radial(c, x, y, r, rgb, 0.10 * ra)
        # sparks
        if a < 1.7:
            kind = 'down' if ev.negative else 'burst'
            n = 90 if ev.kind in B.BRIGHT else 55
            draw_sparks(c, x, y, a, ('ev', i), n, light, kind=kind, grav=220 if ev.negative else 120)
        # dot
        if ev.kind in ('info', 'tech'):
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


def label_boxes(cam, t, tops_skip):
    """world-space boxes of the event labels drawn this frame"""
    tops, skip = tops_skip
    fl = font(*LABEL_FONT)
    out = []
    for i, ev in enumerate(EVENTS):
        if i not in tops or i in skip or t < ev.t:
            continue
        t_in, t_out = callout_window(i)
        if t < t_out:
            continue
        x, y, _ = event_point(cam, ev)
        wl = text_width(fl, ev.label, 0.6) / 2 + 8
        top = tops[i]
        out.append((x - wl, top - 26, x + wl, top - 4))
    return out


def draw_milestones(c, cam, t, alpha=1.0):
    ms = B.MILESTONE_T
    for mi, (lv, fd, tm) in enumerate(ms):
        a = t - tm
        # an older label gives way as soon as the next milestone fires
        lab_end = 4.6
        if mi + 1 < len(ms):
            lab_end = min(lab_end, ms[mi + 1][2] - tm + 0.1)
        nxt = [ev.t for ev in EVENTS if ev.t > tm + 0.3]
        if nxt:
            lab_end = min(lab_end, max(nxt[0] - tm + 0.15, 1.2))
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
            fnum = font('light', 70)
            draw_text(c, num, x - 30, y - 36 + rise, fnum, P((254, 238, 204), la), spacing=0.5, align='right')
            wnum = text_width(fnum, num, 0.5)
            draw_text(c, 'FIRST CLOSE ABOVE', x - 30 - wnum / 2, y - 118 + rise, font('bold', 16),
                      P((228, 197, 150), la), spacing=3.5, align='center')


def grid_highlight(t):
    for lv, fd, tm in B.MILESTONE_T:
        a = t - tm
        e = env(a, 0.0, 0.15, 3.4, 1.2)
        if e > 0:
            return (lv, e)
    return None


# ----------------------------------------------------------------------------
# camera FX: push-in on key moments, shake on black swans and violent swings
# ----------------------------------------------------------------------------
CUR_M = skia.Matrix()   # world -> screen transform of the current frame
CUR_T = 0.0
CUR_HOFF = (0.0, 0.0)   # small share of the shake applied to the HUD
FOCUS = (1015.0, 560.0)


def zoom_env(a):
    if a < -0.55 or a > 2.9:
        return 0.0
    if a < 0.3:
        return ease_io((a + 0.55) / 0.85)
    if a < 1.75:
        return 1.0
    return 1.0 - ease_io((a - 1.75) / 1.15)


def _wave(t, freqs, seed):
    out = 0.0
    for k, f in enumerate(freqs):
        ph = (seed * 2.399 + k * 1.618) % (2 * math.pi)
        out += math.sin(2 * math.pi * f * t + ph) / (k + 1) ** 0.5
    return out / 1.9


def shake_impulse(t):
    amp = 0.0
    for ev in EVENTS:
        a = t - ev.t
        if ev.shake > 0 and 0 <= a < 3.0:
            amp += ev.shake * math.exp(-a / 0.5) * smooth(a / 0.025)
    for lv, fd, tm in B.MILESTONE_T:
        a = t - tm
        if 0 <= a < 2.0:
            amp += 5.0 * math.exp(-a / 0.35) * smooth(a / 0.025)
    return amp


def camera_fx(fi, t, cam):
    """world matrix, background matrix, HUD offset, shake impulse, zoom"""
    srcs = []
    if B.T_START <= t <= T_END + 0.5:
        for ev in EVENTS:
            if ev.zoom > 0:
                e = zoom_env(t - ev.t)
                if e > 0:
                    x, y, _ = event_point(cam, ev)
                    srcs.append((ev.zoom * e, e, cam.rot_pt(x, y)))
        for lv, fd, tm in B.MILESTONE_T:
            e = zoom_env(t - tm)
            if e > 0:
                x, y, _ = cam.proj(fd, math.log10(lv))
                srcs.append((0.26 * e, e, cam.rot_pt(float(x), float(y))))
    wsum = sum(w for w, _, _ in srcs)
    if wsum > 0:
        ax = sum(w * p[0] for w, _, p in srcs) / wsum
        ay = sum(w * p[1] for w, _, p in srcs) / wsum
        S = 1.0 + max(w for w, _, _ in srcs)
        sf = 0.8 * max(e for _, e, _ in srcs)
        afx = ax + (FOCUS[0] - ax) * sf
        afy = ay + (FOCUS[1] - ay) * sf
    else:
        S, ax, ay, afx, afy = 1.0, 960.0, 540.0, 960.0, 540.0
    imp = shake_impulse(t)
    vol = float(CAM['volshake'][fi]) if t < T_END else 0.0
    dx = imp * _wave(t, (7.3, 11.9, 16.1), 1) + vol * _wave(t, (3.1, 5.3, 7.9), 2)
    dy = imp * _wave(t, (8.9, 13.1, 15.3), 3) + vol * _wave(t, (2.7, 4.9, 8.3), 4)
    rot = 0.022 * imp * _wave(t, (6.1, 10.7, 14.3), 5) + 0.05 * vol * _wave(t, (1.9, 3.7), 6)
    os_ = 1.0 + (imp + vol) * 2.6 / 1080.0
    m = skia.Matrix()
    m.setTranslate(-ax, -ay)
    m.postScale(S, S)
    m.postTranslate(afx, afy)
    m.postScale(os_, os_, 960, 540)
    m.postRotate(rot, 960, 540)
    m.postTranslate(dx, dy)
    mb = skia.Matrix()
    sb = (1.0 + 0.25 * (S - 1.0)) * 1.03 * os_
    mb.setScale(sb, sb, 960, 540)
    mb.postRotate(rot * 0.6, 960, 540)
    mb.postTranslate(dx * 0.6, dy * 0.6)
    return m, mb, (dx * 0.22, dy * 0.22), imp, S


def keepout(sx, sy):
    """visibility factor for world labels that would land on the HUD or the callout panel"""
    a = smooth((sx - 540) / 40.0) if sy < 350 else 1.0
    if sy < 350 and sx < 540:
        a = min(a, smooth((sy - 330) / 20.0))
    if sx > 1280 and 270 < sy < 620:
        a = min(a, smooth((1280 - sx + 40) / 40.0))
    return clamp(a)


def map_pt(x, y):
    p = CUR_M.mapXY(float(x), float(y))
    return p.x(), p.y()


def world_pt(cam, day, lp):
    x, y, _ = cam.proj(day, lp)
    x, y = cam.rot_pt(float(x), float(y))
    return map_pt(x, y)


def _reticle(c, px, py, r, rgb, al, ln=15):
    p = P(rgb, 0.95 * al, stroke=2.2)
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        cx_, cy_ = px + sx * r, py + sy * r
        c.drawLine(cx_, cy_, cx_ - sx * ln, cy_, p)
        c.drawLine(cx_, cy_, cx_, cy_ - sy * ln, p)
    c.drawCircle(px, py, 3.0, P((255, 255, 255), al))


def _pill_text(c, txt, x, y, f, rgb, al, align='left', spacing=0.6, txt_rgb=(235, 240, 248)):
    w = text_width(f, txt, spacing)
    if align == 'right':
        x0 = x - w - 22
    elif align == 'center':
        x0 = x - w / 2 - 11
    else:
        x0 = x
    h = f.getSize()
    rect = skia.Rect(x0, y - h - 6, x0 + w + 22, y + 9)
    c.drawRoundRect(rect, 4, 4, P((6, 12, 24), 0.84 * al))
    c.drawRoundRect(rect, 4, 4, P(rgb, 0.75 * al, stroke=1.2))
    draw_text(c, txt, x0 + 11, y, f, P(txt_rgb, al), spacing=spacing)
    return rect


def draw_marks(c, cam, t):
    """lock-on reticle, price/date tag, measurement arrow, ATH line"""
    if t < B.T_START or t > T_END + 1.0:
        return
    for lv, fd, tm in B.MILESTONE_T:
        a = t - tm
        if 0 <= a <= 2.8:
            al = env(a, 0.0, 0.2, 2.8, 0.6)
            px, py = world_pt(cam, fd, math.log10(lv))
            _reticle(c, px, py, 34 + 30 * (1 - ease_out(a / 0.35)), (255, 214, 150), al)
    for ei, ev in enumerate(EVENTS):
        a = t - ev.t
        life = 3.4
        if ei + 1 < len(EVENTS):
            life = min(life, max(EVENTS[ei + 1].t - ev.t + 0.25, 1.6))
        if a < 0 or a > life or ev.kind == 'genesis':
            continue
        al = env(a, 0.0, 0.2, life, 0.5)
        if al <= 0:
            continue
        rgb = ev.color
        light = mix(rgb, (255, 255, 255), 0.3)
        px, py = world_pt(cam, ev.day, LOGP[ev.day])
        r = 40 + 34 * (1 - ease_out(a / 0.35))
        _reticle(c, px, py, r, light, al)
        # price + date tag next to the lock-on
        tag = f'${B.fmt_price(PRICE[ev.day])}  ·  {ev.date.replace("-", ".")}'
        f = font('med', 17)
        tw = text_width(f, tag, 0.6) + 22
        ty = py + r + 34 if ev.negative else py - r - 10
        if ty > 950 or ty < 120:
            ty = py - r - 10 if ev.negative else py + r + 34
        if px - r - 12 - tw > 20:
            _pill_text(c, tag, px - r - 12, ty, f, rgb, al * ease_out(a / 0.3), align='right')
        else:
            _pill_text(c, tag, px + r + 12, ty, f, rgb, al * ease_out(a / 0.3))
        # all-time-high guide line
        if ev.kind in ('peak', 'high'):
            ga = al * ease_out((a - 0.1) / 0.4)
            if ga > 0:
                xe = min(px + r + 40 + 230 * ease_out(a / 0.6), 1285)
                dp = P(light, 0.8 * ga, stroke=1.5)
                dp.setPathEffect(skia.DashPathEffect.Make([8.0, 6.0], 0.0))
                c.drawLine(px + r + 4, py, xe, py, dp)
                draw_text(c, 'ATH' if PRICE[ev.day] >= B.ATH[ev.day] else 'HIGH', xe, py - 8,
                          font('bold', 15), P(light, ga), spacing=2.5, align='right')
        # measurement arrow: from the reference level to the end level
        if ev.bracket:
            d0, d1 = ev.bracket
            tb = max(ev.t, float(B.time_of_day(d1)))
            ba = env(t, tb, 0.25, ev.t + life, 0.5)
            if ba > 0:
                x0, y0 = world_pt(cam, d0, LOGP[d0])
                x1, y1 = world_pt(cam, d1, LOGP[d1])
                pct = PRICE[d1] / PRICE[d0] - 1
                bx = max(x1, px) + 0.6 * r + 16
                dp = P(light, 0.8 * ba, stroke=1.4)
                dp.setPathEffect(skia.DashPathEffect.Make([7.0, 6.0], 0.0))
                xs0 = max(x0, 560.0) if y0 < 350 else x0
                c.drawLine(xs0, y0, bx + 14, y0, dp)
                if xs0 == x0:
                    c.drawCircle(x0, y0, 4.0, P(light, ba))
                c.drawLine(x1 + 6, y1, bx + 14, y1, dp)
                g = ease_out((t - tb) / 0.45)
                ye = y0 + (y1 - y0) * g
                ap = P(light, ba, stroke=2.4)
                c.drawLine(bx, y0, bx, ye, ap)
                dirn = 1.0 if y1 > y0 else -1.0
                head = skia.Path()
                head.moveTo(bx, ye + 2 * dirn)
                head.lineTo(bx - 8, ye - 12 * dirn)
                head.lineTo(bx + 8, ye - 12 * dirn)
                head.close()
                c.drawPath(head, P(light, ba))
                label = f'{"+" if pct >= 0 else "−"}{abs(pct) * 100:,.1f}%'
                fl = font('semi', 28)
                lw = text_width(fl, label, 0.5) + 22
                lx = bx + 12
                if lx + lw > 1296:
                    lx = bx - 16 - lw
                ly = (y0 + y1) / 2 + 12
                _pill_text(c, label, lx, ly, fl, rgb, ba * g, txt_rgb=light, spacing=0.5)


def draw_flash(c, t):
    for ev in EVENTS:
        a = t - ev.t
        if ev.shake >= 16 and 0 <= a < 0.6:
            c.drawRect(skia.Rect(0, 0, W, H), P(mix(ev.color, (255, 255, 255), 0.5), 0.20 * math.exp(-a / 0.11), plus=True))


def hud_pulse(t):
    p = 0.0
    for ev in EVENTS:
        a = t - ev.t
        if 0 <= a < 1.6:
            p = max(p, math.exp(-a / 0.45))
    return p


# ----------------------------------------------------------------------------
# HUD
# ----------------------------------------------------------------------------
TXT_GRAY = (162, 166, 184)
UP_TXT = (110, 224, 186)
DOWN_TXT = (246, 128, 112)
GOLD_TXT = (240, 196, 118)


def sublabel(i, h):
    """returns (text, rgb) for the line under the value"""
    if h < 90:
        return None
    st = int(SUBTYPE[i])
    if st == 1:
        return ('▲ ALL-TIME HIGH', GOLD_TXT)
    if st == 2:
        return (f'▼ −{B.DRAWDOWN[i] * 100:.1f}% FROM ATH', DOWN_TXT)
    if st == 3:
        j = max(i - 365, 0)
        ch = PRICE[i] / PRICE[j] - 1
        s = f'{"+" if ch >= 0 else "−"}{abs(ch) * 100:,.1f}% VS. 1 YEAR AGO'
        return (s, UP_TXT if ch >= 0 else DOWN_TXT)
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


def _scrim(c, x, y, rx, ry, a):
    """soft dark pool behind HUD text so a bright line passing underneath does not swallow it"""
    c.save()
    c.translate(x, y)
    c.scale(rx / ry, 1.0)
    sh = skia.GradientShader.MakeRadial(skia.Point(0, 0), ry, [col((2, 5, 14), a), col((2, 5, 14), a * 0.6), col((2, 5, 14), 0)],
                                        [0.0, 0.55, 1.0])
    c.drawCircle(0, 0, ry, skia.Paint(AntiAlias=True, Shader=sh))
    c.restore()


def draw_hud(c, t, h, valc, alpha=1.0):
    if alpha <= 0.002:
        return
    _scrim(c, 250, 200, 400, 190, 0.55 * alpha)
    _scrim(c, 1640, 160, 400, 150, 0.45 * alpha)
    d = B.date_of(h)
    i = int(min(max(round(h), 0), NDAYS - 1))
    # top-left
    draw_text(c, CFG.HUD_LINE1, 96, 84, font('bold', 15), P((162, 166, 184), alpha), spacing=5.2)
    draw_text(c, CFG.HUD_LINE2, 96, 118, font('semi', 20), P((204, 207, 221), alpha), spacing=1.2)
    draw_text(c, str(d.year), 96, 253, font('xlight', 128), P((253, 254, 255), alpha), spacing=2)
    draw_text(c, f'{d.month:02d} · {d.day:02d}', 98, 309, font('light', 31), P((207, 207, 219), alpha), spacing=6.5)
    # top-right
    draw_text(c, 'CLOSING PRICE', 1818, 90, font('bold', 15), P((165, 168, 177), alpha), spacing=4.5, align='right')
    price = 10 ** logp_at(h)
    if valc >= 0:
        vrgb = mix((250, 250, 253), (132, 232, 196), valc)
    else:
        vrgb = mix((250, 250, 253), (246, 140, 120), -valc)
    pulse = hud_pulse(t)
    if pulse > 0.01:
        draw_text(c, B.fmt_price(price), 1818, 187, font('xlight', 100), P(vrgb, 0.75 * pulse * alpha, blur=9), spacing=1.5, align='right')
    draw_text(c, B.fmt_price(price), 1818, 187, font('xlight', 100), P(vrgb, alpha), spacing=1.5, align='right')
    sl = sublabel(i, h)
    if sl:
        draw_text(c, sl[0], 1822, 238, font('semi', 21), P(sl[1], alpha), spacing=1.2, align='right')


MM_X0, MM_X1 = 96.0, 1824.0
MM_LMIN, MM_LMAX = math.log10(CFG.MM_RANGE[0]), math.log10(CFG.MM_RANGE[1])
MM_YEARS = CFG.MM_YEARS


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


CO_X0, CO_X1 = 1305.0, 1823.0
CO_TXT_X = 1342.0
CO_TXT_W = 1796.0 - CO_TXT_X


def _callout_box(c, cam, ev, a, slide):
    x0, x1, y0 = CO_X0, CO_X1, 292.0 + slide
    ty = y0 + 110
    vy = ty + 70 if ev.value else ty
    dy0 = vy + 46
    last = dy0 + 37 * (len(ev.desc) - 1) if ev.desc else vy
    y1 = last + 33
    rgb = ev.color
    # leader line
    ex, ey, _ = event_point(cam, ev)
    ex, ey = cam.rot_pt(ex, ey)
    ex, ey = map_pt(ex, ey)
    ex, ey = ex - CUR_HOFF[0], ey - CUR_HOFF[1]
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
    # header: category · date · tag
    fcat = font('bold', 16)
    wcat = draw_text(c, ev.cat, CO_TXT_X, y0 + 46, fcat, P(rgb, a), spacing=2.6)
    draw_text(c, ev.date.replace('-', '.'), CO_TXT_X + wcat + 18, y0 + 46, font('reg', 18), P((156, 165, 182), a), spacing=1.2)
    if ev.tag:
        draw_text(c, ev.tag, 1792, y0 + 45, font('semi', 13), P((169, 173, 186), a), spacing=3.2, align='right')
    a_ev = CUR_T - ev.t
    ftitle = fit_font('serif', 46, ev.title, CO_TXT_W, 0.4, min_size=34)
    if not ev.value and a_ev >= 0 and ev.kind != 'genesis':
        sw = ease_out(a_ev / 0.4)
        tw_ = text_width(ftitle, ev.title, 0.4)
        c.drawRect(skia.Rect(CO_TXT_X - 6, ty - ftitle.getSize() * 0.98, CO_TXT_X - 6 + (tw_ + 14) * sw, ty + 12),
                   P(rgb, (0.26 * math.exp(-a_ev / 1.2) + 0.10) * a))
    draw_text(c, ev.title, CO_TXT_X, ty, ftitle, P((255, 255, 255), a), spacing=0.4)
    if ev.value:
        vrgb = mix(rgb if ev.kind != 'genesis' else B.GOLD, (255, 255, 255), 0.08)
        fv = font('light', 60)
        if a_ev >= 0 and ev.kind != 'genesis':
            sw = ease_out(a_ev / 0.4)
            vw = text_width(fv, ev.value, 1.0)
            c.drawRect(skia.Rect(CO_TXT_X - 8, vy - 50, CO_TXT_X - 8 + (vw * 1.06 + 18) * sw, vy + 11),
                       P(rgb, (0.30 * math.exp(-a_ev / 1.2) + 0.12) * a))
        pop = 1.0 + 0.24 * (1 - ease_out(a_ev / 0.45)) if 0 <= a_ev else 1.0
        c.save()
        c.translate(CO_TXT_X - 2, vy)
        c.scale(pop, pop)
        c.translate(-(CO_TXT_X - 2), -vy)
        if 0 <= a_ev < 1.8:
            draw_text(c, ev.value, CO_TXT_X - 2, vy, fv, P(vrgb, 0.7 * math.exp(-a_ev / 0.6) * a, blur=10), spacing=1.0)
        draw_text(c, ev.value, CO_TXT_X - 2, vy, fv, P(vrgb, a), spacing=1.0)
        c.restore()
    for k, line in enumerate(ev.desc):
        fd = fit_font('med', 21, line, CO_TXT_W + 14, 0.2, min_size=17)
        draw_text(c, line, CO_TXT_X, dy0 + 37 * k, fd, P((218, 226, 239), 0.93 * a), spacing=0.2)


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
        c.saveLayer(skia.Rect(0, 650, 1200, 960), lp)
        draw_text(c, label, 97, 777, font('light', 28), P((214, 196, 150), 1.0), spacing=9.5)
        f = fit_font('serif', 92, title, 1000, 1.5)
        draw_text(c, title, 94, 888, f, P((255, 250, 240), 0.35, blur=10), spacing=1.5)
        draw_text(c, title, 94, 888, f, P((255, 255, 255), 1.0), spacing=1.5)
        c.restore()
        c.restore()


# ----------------------------------------------------------------------------
# intro
# ----------------------------------------------------------------------------
PREV_X0, PREV_X1 = 228.0, 1702.0
PREV_Y0, PREV_Y1 = 842.0, 158.0
_PLO, _PHI = float(LOGP.min()), float(LOGP.max())


def prev_xy(day):
    x = PREV_X0 + (PREV_X1 - PREV_X0) * np.asarray(day) / (NDAYS - 1)
    lp = np.interp(day, DAYS, LOGP)
    y = PREV_Y0 + (lp - _PLO) / (_PHI - _PLO) * (PREV_Y1 - PREV_Y0)
    return x, y


PREV_STEP = max(1, int(round(NDAYS / 1450)))
PREV_IDX = np.arange(0, NDAYS, PREV_STEP)
PREV_XS, PREV_YS = prev_xy(PREV_IDX)
GLINT_DAYS = [B.day_of(s) for s in CFG.GLINT_DATES]


def draw_intro(c, t):
    # ---- title card 0 - 2.9s
    ta = 1.0 - smooth((t - 2.3) / 0.55)
    if ta > 0.002:
        blur = 10 * smooth((t - 2.3) / 0.55)
        lp = skia.Paint(Alphaf=ta)
        if blur > 0.3:
            lp.setImageFilter(skia.ImageFilters.Blur(blur, blur))
        c.saveLayer(None, lp)
        draw_text(c, CFG.INTRO_KICKER, 960, 374, font('semi', 18), P((150, 151, 163), 1.0), spacing=9.0, align='center')
        sp = 14
        f = font('serif', 150)
        title = CFG.INTRO_TITLE
        tw = text_width(f, title, sp)
        tx = 960 - tw / 2
        draw_text(c, title, tx, 578, f, P((240, 200, 120), 0.45, blur=16), spacing=sp)
        sh = skia.GradientShader.MakeLinear([skia.Point(0, 455), skia.Point(0, 585)],
                                            [col((250, 236, 196)), col((241, 220, 165)), col((218, 180, 112))],
                                            [0.0, 0.5, 1.0])
        tp = skia.Paint(AntiAlias=True, Shader=sh)
        draw_text(c, title, tx, 578, f, tp, spacing=sp)
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
            draw_text(c, CFG.INTRO_SUB, 960, 712, font('light', 40), P((242, 245, 253), sa), spacing=2.0, align='center')
        # glint on the title corner
        gl = 0.5 + 0.5 * math.sin(t * 5.5)
        star4(c, tx + tw + 10, 462, 26 + 10 * gl, (255, 250, 235), 0.85 * (0.6 + 0.4 * gl), rot=0.0)
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
    # ---- "It all began at $x"
    xa = env(t, 6.35, 0.45, 8.05, 0.55)
    if xa > 0:
        words, num = CFG.INTRO_START
        f1 = font('serif_b', 46)
        f2 = font('xlight', 64)
        parts = [(words, f1, (255, 255, 255), 0.6), ('  ' + num, f2, (243, 217, 160), 1.0)]
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

def draw_ending_text(c, t, cam):
    T = T_END
    # questions
    f = font('serif', 56)
    qx = 1312
    widest = max(text_width(f, s, 1.5) + text_width(f, '?') for s in CFG.END_QUESTIONS)
    qx = min(qx, 1840 - widest)
    for k, s in enumerate(CFG.END_QUESTIONS):
        tq = T + 1.0 + k
        a = env(t, tq, 0.5, T + 4.2, 0.6)
        if a <= 0:
            continue
        blur = 8 * (1 - ease_out((t - tq) / 0.5))
        lp = skia.Paint(Alphaf=a)
        if blur > 0.3:
            lp.setImageFilter(skia.ImageFilters.Blur(blur, blur))
        c.saveLayer(None, lp)
        y = 400 + 78 * k
        w_ = draw_text(c, s, qx, y, f, P((255, 255, 255), 1.0), spacing=1.5)
        draw_text(c, '?', qx + w_ + 3, y, f, P((240, 200, 120), 1.0))
        c.restore()
    # overview labels
    if t >= T + 8.4:
        f = font('semi', 16)
        for k, (ds, txt, ckey, above) in enumerate(CFG.OV_LABELS):
            a = env(t, T + 8.4 + 0.09 * k, 0.5, 999, 0)
            if a <= 0:
                continue
            rgb = B.COLOR_KEYS[ckey]
            day = B.day_of(ds)
            x, y, _ = cam.proj(day, LOGP[day])
            x, y = float(x), float(y)
            yy = y - 32 if above else y + 44
            align = 'center'
            if k == 0:
                yy, x, align = y + 6, x - 18, 'right'
            draw_text(c, txt, x, yy, f, P(mix(rgb, (255, 255, 255), 0.1), a * 0.95), spacing=1.0, align=align)
    # summary block
    d0, d1 = B.DATES[0], B.DATES[-1]
    a1 = env(t, T + 9.4, 0.6, 999, 0)
    if a1 > 0:
        draw_text(c, f'{d0:%Y.%m.%d}  →  {d1:%Y.%m.%d}', 130, 148, font('reg', 28), P((149, 163, 199), a1), spacing=6.5)
    a2 = env(t, T + 9.9, 0.6, 999, 0)
    if a2 > 0:
        txt = f'${PRICE[0]:,.2f} → ${B.fmt_price(PRICE[-1])}'
        draw_text(c, txt, 128, 244, font('xlight', 78), P((245, 250, 255), a2), spacing=1.5)
    a3 = env(t, T + 10.5, 0.5, 999, 0)
    if a3 > 0:
        sc = 1.0 + 0.08 * (1 - ease_out((t - T - 10.5) / 0.6))
        c.save()
        c.translate(130, 360)
        c.scale(sc, sc)
        c.translate(-130, -360)
        f = font('serif', 98)
        mult = CFG.END_SUMMARY_MULT
        draw_text(c, mult, 128, 372, f, P((245, 196, 110), 0.45 * a3, blur=16), spacing=3)
        sh = skia.GradientShader.MakeLinear([skia.Point(0, 290), skia.Point(0, 377)],
                                            [col((252, 230, 175), a3), col((243, 198, 112), a3)], [0, 1])
        draw_text(c, mult, 128, 372, f, skia.Paint(AntiAlias=True, Shader=sh), spacing=3)
        c.restore()
    a4 = env(t, T + 11.6, 0.8, 999, 0)
    if a4 > 0:
        blur = 10 * (1 - ease_out((t - T - 11.6) / 0.8))
        lp = skia.Paint(Alphaf=a4)
        if blur > 0.3:
            lp.setImageFilter(skia.ImageFilters.Blur(blur, blur))
        c.saveLayer(None, lp)
        f = font('serif_i', 64)
        draw_text(c, CFG.END_SLOGAN, 1762, 888, f, P((255, 240, 210), 0.35, blur=12), spacing=1.0, align='right')
        draw_text(c, CFG.END_SLOGAN, 1762, 888, f, P((246, 240, 230), 1.0), spacing=1.0, align='right')
        c.restore()
    a5 = env(t, T + 12.6, 0.7, 999, 0)
    if a5 > 0:
        draw_text(c, CFG.END_SOURCE, 960, 1031, font('reg', 16), P((132, 135, 149), a5), spacing=0.8, align='center')


# ----------------------------------------------------------------------------
# frame
# ----------------------------------------------------------------------------
END_T0 = T_END + 4.0
END_T1 = T_END + 9.0
_CAM_END_START = None


def render_frame(fi, arr=None):
    global _CAM_END_START, CUR_M, CUR_T, CUR_HOFF, LABEL_BOXES
    t = fi / FPS
    if arr is None:
        arr = np.zeros((H, W, 4), np.uint8)
    surf = skia.Surface(arr)
    c = surf.getCanvas()
    c.clear(skia.Color4f(0.004, 0.012, 0.047, 1))
    upm, dnm, valc = CAM['up'][fi], CAM['down'][fi], CAM['valcol'][fi]
    h = B.HEAD[fi]
    CUR_T = t
    hud_a = smooth((t - 7.3) / 0.8) * (1 - smooth((t - (T_END + 3.7)) / 0.6))
    if t < B.T_START:
        CUR_M = skia.Matrix()
        CUR_HOFF = (0.0, 0.0)
        draw_background(c, t, upm, dnm)
        draw_dust(c, t)
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
    m_world, m_bg, hoff, imp, zoom_s = camera_fx(fi, t, cam)
    CUR_M = m_world
    CUR_HOFF = hoff

    c.save()
    c.concat(m_bg)
    draw_background(c, t, upm, dnm)
    draw_dust(c, t)
    c.restore()

    tops_skip = _label_tops(cam, t)
    LABEL_BOXES = label_boxes(cam, t, tops_skip) if ending < 0.6 else []
    c.save()
    c.concat(m_world)
    if abs(cam.roll) > 1e-6:
        c.rotate(math.degrees(cam.roll), cam.hx, cam.hy)
    draw_grid(c, cam, t, alpha=1.0 - 0.45 * ending, labels=ending < 0.3, hl=grid_highlight(t))
    draw_curtains(c, cam, t, intensity=1.0 - 0.55 * ending)
    draw_event_fx(c, cam, t, ending=ending, tops_skip=tops_skip)
    style = 1.0 - 0.35 * ending
    draw_line(c, cam, t, style=style)
    draw_milestones(c, cam, t)
    m = float(np.clip(B.RET10[int(min(round(h), NDAYS - 1))] / 0.07, -1, 1))
    if t >= T_END:
        m *= max(0.0, 1 - (t - T_END) / 2.0)
    draw_head(c, cam, t, m, scale=1.0 - 0.3 * ending)
    c.restore()

    draw_flash(c, t)
    draw_vignette(c)
    draw_marks(c, cam, t)
    c.save()
    c.translate(hoff[0], hoff[1])
    draw_callout(c, cam, t)
    draw_era(c, t)
    if hud_a > 0:
        draw_hud(c, t, h, valc, hud_a)
        draw_minimap(c, t, h, valc, hud_a)
    c.restore()
    if t >= T_END + 0.5:
        draw_ending_text(c, t, cam)
    # chromatic split on violent hits
    if imp > 9.0:
        k = int(min(5, round((imp - 6.0) * 0.25)))
        if k >= 1:
            arr[:, :, 0] = np.roll(arr[:, :, 0], k, axis=1)
            arr[:, :, 2] = np.roll(arr[:, :, 2], -k, axis=1)
    return arr


if __name__ == '__main__':
    import sys
    import time
    out = os.path.join(B.OUT, 'test_frames')
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
