"""Drawing of a (possibly morphing / exploded) car in centered-mm space."""
import math
import numpy as np
import skia
from cars import CARS, N_PART, poly_path, canonical, N_OUTLINE

S = 0.205          # px per mm
CX = 960           # car centre on screen (px)
GROUND = 800       # ground line (px)


def lerp(a, b, t):
    return a + (b - a) * t


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_io(x):
    x = clamp(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_back(x, k=1.9):
    x = clamp(x)
    return 1 + (k + 1) * (x - 1) ** 3 + k * (x - 1) ** 2


def col(rgb, a=1.0):
    r, g, b = [int(clamp(v, 0, 255)) for v in rgb]
    return skia.Color(r, g, b, int(clamp(a) * 255))


def shade(c, k, add=0.0):
    return np.clip(np.asarray(c, float) * k + add, 0, 255)


# ------------------------------------------------------------ brushed steel texture
_rng = np.random.default_rng(7)
_n = _rng.normal(0, 1, (256, 1024)).astype(np.float32)
_k = np.ones(61, np.float32) / 61
_n = np.apply_along_axis(lambda r: np.convolve(np.tile(r, 3), _k, 'same')[1024:2048], 1, _n)
_n = (_n - _n.min()) / (_n.max() - _n.min())
_img = np.zeros((256, 1024, 4), np.uint8)
_img[..., :3] = (128 + (_n[..., None] - 0.5) * 90).astype(np.uint8)
_img[..., 3] = 255
BRUSH = skia.Image.fromarray(_img)


def paint_shader(color, H, belt_y, env, metal, steel=False):
    sky = np.asarray(env['sky_refl'], float)
    grd = np.asarray(env['ground_refl'], float)
    c = np.asarray(color, float)
    lum = c.mean() / 255
    k = 0.05 + 0.10 * metal          # how much environment shows in the clear coat
    bright = 1.0 if lum < 0.75 else 0.97
    stops = [
        (0.0,             shade(c * (1 - k) + grd * k, 0.50)),
        (H * 0.10,        shade(c * (1 - k) + grd * k, 0.64)),
        (H * 0.24,        shade(c * (1 - k) + grd * k, 0.80)),
        (H * 0.40,        shade(c * (1 - k) + sky * k, 0.93 * bright)),
        (belt_y - H * 0.13, shade(c * (1 - k) + sky * k, 1.00 * bright)),
        (belt_y - H * 0.05, shade(c * (1 - k * 1.4) + sky * k * 1.4, 1.10 * bright, 12 * metal + 4)),
        (belt_y - H * 0.025, shade(c, 1.28 if lum < 0.75 else 1.02, 26 * metal + 10)),
        (belt_y - H * 0.008, shade(c, 0.80)),
        (belt_y + H * 0.03, shade(c * (1 - k) + sky * k, 0.96)),
        (H * 1.02,        shade(c * (1 - k * 2) + sky * k * 2, 1.06)),
    ]
    ys = [s_[0] for s_ in stops]
    lo, hiy = ys[0], ys[-1]
    pos = [clamp((y - lo) / (hiy - lo)) for y in ys]
    for i in range(1, len(pos)):
        pos[i] = max(pos[i], pos[i - 1] + 1e-4)
    pos = [min(p_, 1.0) for p_ in pos]
    sh = skia.GradientShader.MakeLinear([skia.Point(0, lo), skia.Point(0, hiy)],
                                        [col(s_[1]) for s_ in stops], pos)
    if steel:
        tex = BRUSH.makeShader(skia.TileMode.kRepeat, skia.TileMode.kRepeat,
                               skia.SamplingOptions(skia.FilterMode.kLinear),
                               skia.Matrix.Scale(3.0, 2.0))
        sh = skia.Shaders.Blend(skia.BlendMode.kOverlay, sh, tex)
    return sh


def glass_shader(H, env):
    sky = np.asarray(env['sky_refl'], float)
    top = np.clip(sky * 0.38 + np.array([14, 18, 24]), 0, 255)
    mid = np.clip(sky * 0.16 + np.array([12, 15, 20]), 0, 255)
    return skia.GradientShader.MakeLinear([skia.Point(0, H * 0.5), skia.Point(0, H)],
                                          [col([10, 12, 15]), col(mid), col(top)], [0, 0.55, 1])


# ------------------------------------------------------------ wheels
def draw_rim(cv, style, r, ang, rc, alpha):
    p = skia.Paint(AntiAlias=True)
    rim_r = r * (0.70 if style not in ('star5',) else 0.66)
    rc = np.asarray(rc, float)
    # brake disc / dark barrel
    p.setColor(col([24, 25, 28], alpha)); cv.drawCircle(0, 0, rim_r, p)
    if style in ('aero', 'gemini', 'ct', 'cab'):
        p.setShader(skia.GradientShader.MakeRadial(skia.Point(-rim_r * 0.3, rim_r * 0.3), rim_r * 1.4,
                                                   [col(shade(rc, 1.35), alpha), col(shade(rc, 0.75), alpha)]))
        cv.drawCircle(0, 0, rim_r * 0.97, p); p = skia.Paint(AntiAlias=True)
    nblur = 4
    for b in range(nblur):
        a = ang - b * 0.07
        aa = alpha * (1.0 if b == 0 else 0.28)
        cv.save(); cv.rotate(math.degrees(a))
        if style == 'star5':
            p.setColor(col(rc, aa))
            for i in range(5):
                cv.save(); cv.rotate(i * 72)
                path = skia.Path(); w0, w1 = rim_r * 0.16, rim_r * 0.09
                path.moveTo(-w0, rim_r * 0.15); path.lineTo(-w1, rim_r * 0.95); path.lineTo(w1, rim_r * 0.95); path.lineTo(w0, rim_r * 0.15); path.close()
                cv.drawPath(path, p); cv.restore()
        elif style == 'turbine10':
            p.setColor(col(rc, aa))
            for i in range(10):
                cv.save(); cv.rotate(i * 36)
                path = skia.Path()
                path.moveTo(-rim_r * 0.06, rim_r * 0.18)
                path.quadTo(-rim_r * 0.20, rim_r * 0.6, -rim_r * 0.10, rim_r * 0.96)
                path.lineTo(rim_r * 0.03, rim_r * 0.96)
                path.quadTo(-rim_r * 0.05, rim_r * 0.6, rim_r * 0.06, rim_r * 0.18); path.close()
                cv.drawPath(path, p); cv.restore()
        elif style == 'aero':
            p.setColor(col(shade(rc, 0.45), aa))
            for i in range(5):
                cv.save(); cv.rotate(i * 72)
                path = skia.Path()
                path.moveTo(rim_r * 0.25, 0); path.quadTo(rim_r * 0.75, rim_r * 0.2, rim_r * 0.92, rim_r * 0.5)
                path.lineTo(rim_r * 0.80, rim_r * 0.58); path.quadTo(rim_r * 0.6, rim_r * 0.25, rim_r * 0.22, rim_r * 0.12); path.close()
                cv.drawPath(path, p); cv.restore()
        elif style == 'gemini':
            p.setColor(col(shade(rc, 1.9), aa))
            for i in range(5):
                cv.save(); cv.rotate(i * 72)
                for off in (-0.07, 0.07):
                    path = skia.Path()
                    path.moveTo(rim_r * (off - 0.03), rim_r * 0.2); path.lineTo(rim_r * (off * 1.6 - 0.03), rim_r * 0.94)
                    path.lineTo(rim_r * (off * 1.6 + 0.03), rim_r * 0.94); path.lineTo(rim_r * (off + 0.03), rim_r * 0.2); path.close()
                    cv.drawPath(path, p)
                cv.restore()
        elif style == 'ct':
            p.setColor(col(shade(rc, 0.55), aa)); p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(rim_r * 0.05)
            for i in range(6):
                cv.save(); cv.rotate(i * 60)
                cv.drawLine(rim_r * 0.18, -rim_r * 0.1, rim_r * 0.95, -rim_r * 0.35, p); cv.restore()
            p.setStyle(skia.Paint.kFill_Style)
        elif style == 'cab':
            p.setColor(col(shade(rc, 0.5), aa)); p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(rim_r * 0.035)
            for i in range(14):
                cv.save(); cv.rotate(i * 360 / 14)
                cv.drawLine(rim_r * 0.3, 0, rim_r * 0.93, rim_r * 0.12, p); cv.restore()
            p.setStyle(skia.Paint.kFill_Style)
        elif style == 'rs2':
            p.setColor(col(shade(rc, 2.2), aa))
            for i in range(10):
                cv.save(); cv.rotate(i * 36)
                path = skia.Path()
                path.moveTo(-rim_r * 0.05, rim_r * 0.2); path.lineTo(-rim_r * 0.12, rim_r * 0.95)
                path.lineTo(rim_r * 0.0, rim_r * 0.95); path.lineTo(rim_r * 0.05, rim_r * 0.2); path.close()
                cv.drawPath(path, p); cv.restore()
        cv.restore()
    # rim lip + hub
    p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(rim_r * 0.06)
    p.setColor(col(shade(rc, 1.15) if style not in ('ct', 'cab') else shade(rc, 0.7), alpha))
    cv.drawCircle(0, 0, rim_r * 0.97, p); p.setStyle(skia.Paint.kFill_Style)
    p.setColor(col(shade(rc, 0.9), alpha)); cv.drawCircle(0, 0, rim_r * 0.17, p)
    p.setColor(col([30, 30, 34], alpha)); cv.drawCircle(0, 0, rim_r * 0.09, p)


def draw_wheel(cv, x, r, ang, styles, env):
    """styles: list of (style, rimcolor, weight)."""
    p = skia.Paint(AntiAlias=True)
    cv.save(); cv.translate(x, r)
    p.setShader(skia.GradientShader.MakeRadial(skia.Point(0, 0), r,
                [col([14, 14, 16]), col([14, 14, 16]), col([46, 47, 52]), col([20, 20, 22])],
                [0, 0.70, 0.86, 1.0]))
    cv.drawCircle(0, 0, r, p)
    p = skia.Paint(AntiAlias=True)
    for st, rc, w in styles:
        if w > 0.01:
            draw_rim(cv, st, r, ang, rc, w)
    cv.restore()


# ------------------------------------------------------------ helpers on polygons
def centroid(poly):
    return poly.mean(0)


def path_of(poly):
    return poly_path(poly)


def kind_fill(car, kind):
    """Returns ('paint'|'glass'|'black'|'head'|'tail'|'dark', color)"""
    if kind in ('lower',):
        return 'paint'
    if kind == 'upper':
        if car.glass_roof:
            return 'glass'
        if car.roof_black:
            return 'black'
        return 'paint'
    if kind == 'glass':
        return 'glass'
    if kind == 'mirror':
        return 'paint' if car.key not in ('roadster',) else 'paint'
    if kind in ('detail', 'nose'):
        return 'black'
    return kind


def fill_paint(kind_style, color, H, belt_y, env, metal, steel, lights=0.0, glow=False):
    p = skia.Paint(AntiAlias=True)
    if kind_style == 'paint':
        p.setShader(paint_shader(color, H, belt_y, env, metal, steel))
    elif kind_style == 'glass':
        p.setShader(glass_shader(H, env))
    elif kind_style == 'black':
        p.setShader(skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(0, H)],
                    [col([12, 12, 14]), col([34, 36, 40])], [0, 1]))
    elif kind_style == 'head':
        p.setColor(col(lerp(np.array([150, 160, 172]), np.array([235, 245, 255]), lights)))
    elif kind_style == 'tail':
        p.setColor(col(lerp(np.array([110, 10, 16]), np.array([255, 40, 50]), lights)))
    return p


# ------------------------------------------------------------ full car state
class CarState:
    """Describe what to draw. a,b: car indices; s: morph 0..1 (global), tau: transition time or None."""
    def __init__(self, a, b=None, tau=None, T=3.2):
        self.a, self.b, self.tau, self.T = a, (a if b is None else b), tau, T


_rngp = np.random.default_rng(11)
FLIGHT = []
for i in range(40):
    FLIGHT.append(dict(mag=_rngp.uniform(420, 820), up=_rngp.uniform(200, 520), rot=_rngp.uniform(-38, 38),
                       flip=_rngp.random() < 0.45, jitter=_rngp.uniform(-0.06, 0.06)))


def transition_params(tau, T=3.2):
    """global schedule values for a transition."""
    return dict(
        seam=smooth(tau / 0.25) * (1 - smooth((tau - 0.35) / 0.35)),
        wire=smooth((tau - 0.25) / 0.4) * (1 - smooth((tau - 2.45) / 0.45)),
        sg=ease_io((tau - 0.85) / 1.15),
        old_det=1 - smooth((tau - 0.1) / 0.25),
        new_det=smooth((tau - 2.55) / 0.3),
        sweep=clamp((tau - 2.5) / 0.7),
    )


def part_schedule(tau, xn, fl):
    """xn: 0 rear .. 1 front."""
    d = 0.28 * (1 - xn) + fl['jitter']
    p_out = ease_io((tau - 0.22 - d) / 0.7)
    p_in = ease_back((tau - 1.8 - d * 0.9) / 0.72)
    s = smooth((tau - 0.85 - d * 0.6) / 0.95)
    amt = p_out * (1 - p_in)
    snap = clamp(1 - abs((tau - 1.8 - d * 0.9) - 0.6) / 0.12) if p_out > 0.5 else 0
    return amt, s, snap


def draw_car(cv, st, env, t_wheel, lights=0.0, falcon=0.0, lift=0.0, extra=None):
    """cv: canvas already transformed so that 1 unit = 1 mm, origin at car centre/ground, y up."""
    A, B = CARS[st.a], CARS[st.b]
    tau = st.tau
    if tau is None:
        tp = dict(seam=0, wire=0, sg=0, old_det=1, new_det=0, sweep=0)
    else:
        tp = transition_params(tau, st.T)
    sg = tp['sg']
    L = lerp(A.L, B.L, sg); H = lerp(A.H, B.H, sg)
    wf = (lerp(A.wf[0], B.wf[0], sg), lerp(A.wf[1], B.wf[1], sg))
    wr = (lerp(A.wr[0], B.wr[0], sg), lerp(A.wr[1], B.wr[1], sg))
    belt_y = lerp(np.mean([y for _, y in A.belt]), np.mean([y for _, y in B.belt]), sg)
    color_g = lerp(A.color, B.color, sg)
    p = skia.Paint(AntiAlias=True)

    # --- ground shadow
    sh = skia.Paint(AntiAlias=True, Color=skia.Color(0, 0, 0, int(170 * (1 - lift))))
    sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 60 + lift * 300))
    cv.drawRoundRect(skia.Rect(-L * 0.52, -60, L * 0.52, 70), 60, 60, sh)

    # --- chassis skateboard + wireframe during transition
    if tp['wire'] > 0.01:
        draw_skeleton(cv, A, B, sg, tp['wire'], wf, wr, L, H, extra)

    # --- wheel wells (dark) behind body
    if tau is None or tp['new_det'] > 0.5:
        Cw = A if tau is None else B
        wp_ = skia.Paint(AntiAlias=True, Color=col([10, 10, 12], 1.0 if tau is None else tp['new_det']))
        cv.save(); cv.clipPath(poly_path(Cw.outline), skia.ClipOp.kIntersect, True)
        for (wx, r) in (Cw.wf, Cw.wr):
            cv.drawCircle(wx, r, r * 1.2 + 40, wp_)
        cv.restore()
    # --- wheels
    ang = t_wheel
    for (wx, r) in (wf, wr):
        styles = [(A.rim, A.rimc, 1 - sg), (B.rim, B.rimc, sg)] if st.a != st.b else [(A.rim, A.rimc, 1)]
        if tau is not None:
            styles = [(A.rim, A.rimc, 1 - smooth((sg - 0.35) / 0.3)), (B.rim, B.rimc, smooth((sg - 0.35) / 0.3))]
        draw_wheel(cv, wx, r, -ang / r, styles, env)

    # --- arch shadows (assembled only)
    det = tp['old_det'] if tau is not None else 1
    if tau is None:
        draw_well_shadow(cv, A, 1.0)

    # --- body parts
    nparts = len(A.parts)
    groups = []
    for i in range(nparts):
        kind, k, pa = A.parts[i]
        _, _, pb = B.parts[i]
        if tau is None:
            poly = pa; amt = 0; s_i = 0; snap = 0
        else:
            c0 = centroid(pa)
            xn = clamp((c0[0] / (A.L / 2) + 1) / 2)
            fl = FLIGHT[k * 3 + (0 if kind == 'lower' else 1 if kind in ('upper', 'glass') else 2) + (17 if kind in ('head', 'tail', 'mirror', 'detail', 'nose') else 0)]
            amt, s_i, snap = part_schedule(tau, xn, fl)
            poly = lerp(pa, pb, s_i)
        groups.append((i, kind, k, poly, amt, s_i, snap))

    # find transform per part (glass follows its upper sibling)
    xf = {}
    for (i, kind, k, poly, amt, s_i, snap) in groups:
        if tau is None or amt == 0:
            xf[i] = None
            continue
        key = ('upper', k) if kind == 'glass' else (kind, k)
        fl_id = k * 3 + (0 if kind == 'lower' else 1 if kind in ('upper', 'glass') else 2) + (17 if kind in ('head', 'tail', 'mirror', 'detail', 'nose') else 0)
        fl = FLIGHT[fl_id]
        # use the upper sibling's centroid for glass so they move together
        ref = poly
        if kind == 'glass':
            for g in groups:
                if g[1] == 'upper' and g[2] == k:
                    ref = g[3]
        c = centroid(ref)
        v = np.array([c[0], c[1] - H * 0.45]); n = np.linalg.norm(v) + 1e-6
        d = v / n * fl['mag'] + np.array([0, fl['up']])
        xf[i] = (c, d * amt, fl['rot'] * amt, math.cos(math.pi * clamp(amt * 1.15)) if fl['flip'] else 1.0)

    order = ['lower', 'nose', 'detail', 'upper', 'glass', 'mirror', '#finish', 'head', 'tail']
    # falcon door (Model X)
    fdoor = None
    if falcon > 0 and A.falcon is not None and tau is None:
        fdoor = A.falcon
        draw_cabin_opening(cv, A, fdoor, groups, H)
    for kd in order:
        if kd == '#finish':
            if tau is None:
                draw_finish(cv, A, env, 1.0)
            else:
                if tp['old_det'] > 0.01:
                    draw_finish(cv, A, env, tp['old_det'])
                if tp['new_det'] > 0.01:
                    draw_finish(cv, B, env, tp['new_det'])
            continue
        for (i, kind, k, poly, amt, s_i, snap) in groups:
            if kind != kd:
                continue
            cv.save()
            if fdoor is not None and k == fdoor and kind in ('lower', 'upper', 'glass'):
                apply_falcon(cv, groups, fdoor, falcon, H)
            t = xf.get(i)
            if t is not None:
                c, d, rot, fx = t
                cv.translate(c[0] + d[0], c[1] + d[1]); cv.rotate(rot); cv.scale(fx, 1); cv.translate(-c[0], -c[1])
            ksty = kind_fill(A if s_i < 0.5 else B, kind)
            car_c = lerp(A.color, B.color, s_i)
            metal = lerp(A.metal, B.metal, s_i)
            steel = (A.steel if s_i < 0.5 else B.steel)
            pp = fill_paint(ksty, car_c, H, belt_y, env, metal, steel, lights)
            path = path_of(poly)
            if ksty == 'paint' and kind == 'upper' and (A if s_i < 0.5 else B).roof_black:
                pass
            cv.drawPath(path, pp)
            if kind == 'glass':
                draw_glass_reflection(cv, path, poly, H)
            if amt > 0.02:
                gp = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=14,
                                Color=col(env['accent'], 0.85 * clamp(amt * 3)))
                gp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10))
                cv.drawPath(path, gp)
                gp2 = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=5,
                                 Color=col([235, 250, 255], 0.9 * clamp(amt * 3)))
                cv.drawPath(path, gp2)
            if kind in ('head', 'tail') and lights > 0.05 and amt < 0.05:
                gl = skia.Paint(AntiAlias=True, Color=col([255, 40, 50] if kind == 'tail' else [200, 230, 255], 0.75 * lights))
                gl.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 45))
                cv.drawPath(path, gl)
            cv.restore()
            if snap > 0.01:
                c = centroid(poly)
                fp = skia.Paint(AntiAlias=True, Color=col([230, 250, 255], 0.35 * snap))
                fp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 45))
                cv.drawCircle(c[0], c[1], 70, fp)

    # details: seams, handles, chrome trims
    if tau is None:
        draw_details(cv, A, 1.0, H, falcon)
    else:
        if tp['old_det'] > 0.01:
            draw_details(cv, A, tp['old_det'], H, 0)
        if tp['new_det'] > 0.01:
            draw_details(cv, B, tp['new_det'], H, 0)
            draw_well_shadow(cv, B, tp['new_det'])
        if tp['seam'] > 0.01:
            draw_seam_glow(cv, A, tp['seam'], env)
        if 0 < tp['sweep'] < 1:
            draw_sweep(cv, B, tp['sweep'])

    # headlight beam handled by caller (needs screen space)
    return dict(L=L, H=H, wf=wf, wr=wr)


def draw_finish(cv, car, env, a):
    """Rim light along the roofline, soft long reflection on the doors, rocker occlusion."""
    sky = np.asarray(env['sky_refl'], float)
    if car.__dict__.get('hexarch'):
        draw_cladding(cv, car, a)
    # interior: headrests + B pillar seen through the glass
    cv.save(); cv.clipPath(car.dlo, skia.ClipOp.kIntersect, True)
    (fx, fy), (rx, ry) = car.belt
    hp = skia.Paint(AntiAlias=True, Color=col([4, 5, 7], 0.75 * a))
    hp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10))
    by = (fy + ry) / 2
    seats = [car.cuts[2] + 260] + ([car.cuts[3] + 300] if car.key not in ('roadster', 'cybercab', 'roadster2') else [])
    if car.key == 'cybercab':
        seats = [car.cuts[2] + 100]
    for sx in seats:
        cv.drawRoundRect(skia.Rect(sx - 150, by + 120, sx + 120, by + 340), 80, 80, hp)
        cv.drawRect(skia.Rect(sx - 60, by - 40, sx + 30, by + 140), hp)
    if car.key not in ('roadster', 'cybercab', 'roadster2'):
        bp = skia.Paint(AntiAlias=True, Color=col([8, 9, 11], a))
        bx = car.cuts[2]
        pth = skia.Path(); pth.moveTo(bx - 45, -10); pth.lineTo(bx + 55, -10); pth.lineTo(bx + 15, car.H * 1.2); pth.lineTo(bx - 85, car.H * 1.2); pth.close()
        cv.drawPath(pth, bp)
    cv.restore()
    cv.save(); cv.clipPath(car.body, skia.ClipOp.kIntersect, True)
    # turning-away surfaces at nose and tail
    ep = skia.Paint(AntiAlias=True)
    ep.setShader(skia.GradientShader.MakeLinear([skia.Point(-car.L / 2, 0), skia.Point(car.L / 2, 0)],
                 [col([0, 0, 0], 0.45 * a), col([0, 0, 0], 0), col([0, 0, 0], 0), col([0, 0, 0], 0.40 * a)],
                 [0, 0.09, 0.90, 1]))
    cv.drawRect(skia.Rect(-car.L, -100, car.L, car.H * 1.5), ep)
    # wheel-arch flare highlight
    if not car.__dict__.get('hexarch'):
        fp = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=40,
                        Color=col(np.clip(sky * 0.5 + 120, 0, 255), 0.22 * a))
        fp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 16))
        for (wx, r) in (car.wf, car.wr):
            rect = skia.Rect(wx - r - 110, r - r - 110, wx + r + 110, r + r + 110)
            cv.drawArc(rect, 200, 140, False, fp)
    # rim light: outline stroked, only top part visible
    rp = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=26,
                    Color=col(np.clip(sky * 0.6 + 110, 0, 255), 0.55 * a))
    rp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 8))
    cv.save(); cv.clipRect(skia.Rect(-car.L, car.H * 0.55, car.L, car.H * 2))
    cv.drawPath(poly_path(car.outline), rp); cv.restore()
    # long soft reflection streak across the doors
    (fx, fy), (rx, ry) = car.belt
    yb = (fy + ry) / 2 - car.H * 0.16
    sp = skia.Paint(AntiAlias=True)
    sp.setShader(skia.GradientShader.MakeLinear([skia.Point(car.L * 0.45, 0), skia.Point(-car.L * 0.45, 0)],
                 [col(sky, 0), col(np.clip(sky + 40, 0, 255), 0.16 * a), col(sky, 0.10 * a), col(sky, 0)], [0, 0.35, 0.7, 1]))
    sp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 30))
    cv.drawRect(skia.Rect(-car.L / 2, yb - 70, car.L / 2, yb + 40), sp)
    # rocker / underbody occlusion
    op_ = skia.Paint(AntiAlias=True)
    op_.setShader(skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(0, car.H * 0.2)],
                  [col([0, 0, 0], 0.55 * a), col([0, 0, 0], 0)], [0, 1]))
    cv.drawRect(skia.Rect(-car.L, -50, car.L, car.H * 0.2), op_)
    cv.restore()


def draw_well_shadow(cv, car, a):
    """Darken the wheel arch opening edge so wheels sit inside the body."""
    p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=26, Color=col([0, 0, 0], 0.55 * a))
    p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 14))
    cv.save(); cv.clipPath(car.body, skia.ClipOp.kIntersect, True)
    for (wx, r) in (car.wf, car.wr):
        if car.__dict__.get('hexarch'):
            continue
        cv.drawCircle(wx, r, r + 52, p)
    cv.restore()


def draw_cladding(cv, car, a):
    if True:
        # cybertruck black flare cladding
        fp = skia.Paint(AntiAlias=True, Color=col([28, 29, 31], a))
        for (wx, r) in (car.wf, car.wr):
            hx = [(-1.22, -0.2), (-1.05, 0.72), (-0.62, 1.16), (0.62, 1.16), (1.05, 0.72), (1.22, -0.2)]
            outer = [(wx + a_ * r * 1.13, r + b * r * 1.13) for a_, b in hx]
            inner = [(wx + a_ * r, r + b * r) for a_, b in hx]
            path = poly_path(outer + inner[::-1])
            cv.save(); cv.clipPath(car.body, skia.ClipOp.kIntersect, True)
            cv.drawPath(path, fp); cv.restore()
        # bed / lower cladding strip
        cv.save(); cv.clipPath(car.body, skia.ClipOp.kIntersect, True)
        fp.setColor(col([30, 31, 33], a)); cv.drawRect(skia.Rect(-car.L, 0, car.L, 300), fp)
        cv.restore()


def draw_details(cv, car, a, H, falcon):
    p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=7, Color=col([0, 0, 0], 0.55 * a))
    cv.save(); cv.clipPath(car.body, skia.ClipOp.kIntersect, True)
    by = {True: None}
    (fx, fy), (rx, ry) = car.belt
    for j, x in enumerate(car.cuts):
        if j in car.hidden:
            continue
        if falcon > 0 and car.falcon is not None and j in (car.falcon - 1, car.falcon):
            continue
        ytop = fy + (ry - fy) * (x - fx) / (rx - fx) if rx != fx else fy
        ytop = clamp(ytop, 0, H) if j in (1, 2, 3) else H * 1.2
        cv.drawLine(x, 0, x + (0 if j not in (1,) else -40), ytop, p)
    # belt crease
    p.setStrokeWidth(5); p.setColor(col([0, 0, 0], 0.35 * a))
    cv.drawLine(fx + 300, fy - 4, rx - 300, ry - 4, p)
    cv.restore()
    # chrome DLO surround
    if car.chrome:
        cp = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=16, Color=col([215, 220, 228], 0.9 * a))
        cv.drawPath(car.dlo, cp)
    else:
        cp = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=12, Color=col([10, 10, 12], 0.8 * a))
        cv.drawPath(car.dlo, cp)
    # handles
    hp = skia.Paint(AntiAlias=True, Color=col([220, 224, 230] if car.chrome else [20, 20, 22], 0.85 * a))
    for (x, y, w) in car.handles:
        cv.drawRoundRect(skia.Rect(x - w / 2, y - 14, x + w / 2, y + 14), 14, 14, hp)


def draw_glass_reflection(cv, path, poly, H):
    cv.save(); cv.clipPath(path, skia.ClipOp.kIntersect, True)
    x0, x1 = poly[:, 0].min(), poly[:, 0].max()
    p = skia.Paint(AntiAlias=True, Color=skia.Color(255, 255, 255, 34))
    w = (x1 - x0)
    for off, wd in ((0.25, 0.10), (0.42, 0.04)):
        pth = skia.Path()
        xa = x0 + w * off
        pth.moveTo(xa, 0); pth.lineTo(xa + w * wd, 0); pth.lineTo(xa + w * wd + H * 0.6, H * 1.2); pth.lineTo(xa + H * 0.6, H * 1.2); pth.close()
        cv.drawPath(pth, p)
    cv.restore()


def draw_seam_glow(cv, car, a, env):
    p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=16, Color=col(env['accent'], a))
    p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 12))
    cv.save(); cv.clipPath(car.body, skia.ClipOp.kIntersect, True)
    for j, x in enumerate(car.cuts):
        cv.drawLine(x, 0, x, car.H * 1.2, p)
    (fx, fy), (rx, ry) = car.belt
    cv.drawLine(fx + 2000, fy, fx, fy, p); cv.drawLine(fx, fy, rx, ry, p); cv.drawLine(rx, ry, rx - 3000, ry, p)
    cv.restore()
    p2 = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=6, Color=col([235, 250, 255], a))
    cv.drawPath(car.body, p2)


def draw_sweep(cv, car, u):
    cv.save(); cv.clipPath(car.body, skia.ClipOp.kIntersect, True)
    x = car.L / 2 + 600 - u * (car.L + 1400)
    sh = skia.GradientShader.MakeLinear([skia.Point(x - 420, 0), skia.Point(x + 420, car.H * 0.9)],
                                        [skia.Color(255, 255, 255, 0), skia.Color(255, 255, 255, 90), skia.Color(255, 255, 255, 0)], [0, 0.5, 1])
    p = skia.Paint(AntiAlias=True); p.setShader(sh); p.setBlendMode(skia.BlendMode.kPlus)
    cv.drawRect(skia.Rect(-car.L, -100, car.L, car.H * 1.5), p)
    cv.restore()


def _scan(poly, xs):
    """top/bottom y of polygon at given xs."""
    tops, bots = [], []
    P = np.vstack([poly, poly[:1]])
    for x in xs:
        ys = []
        for i in range(len(P) - 1):
            x0, y0 = P[i]; x1, y1 = P[i + 1]
            if (x0 - x) * (x1 - x) <= 0 and x0 != x1:
                ys.append(y0 + (y1 - y0) * (x - x0) / (x1 - x0))
        if ys:
            tops.append(max(ys)); bots.append(min(ys))
        else:
            tops.append(None); bots.append(None)
    return tops, bots


def draw_skeleton(cv, A, B, sg, a, wf, wr, L, H, extra):
    outline = lerp(A.outline, B.outline, sg)
    acc = [90, 220, 255]
    # skateboard battery platform
    x0, x1 = wr[0] - 80, wf[0] + 80
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeLinear([skia.Point(0, 180), skia.Point(0, 380)],
                [col([18, 22, 28], a), col([46, 54, 64], a)], [0, 1]))
    cv.drawRoundRect(skia.Rect(x0, 180, x1, 370), 40, 40, p)
    p = skia.Paint(AntiAlias=True)
    gp = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=5, Color=col(acc, 0.55 * a))
    n = int((x1 - x0) / 170)
    for i in range(1, n):
        xx = x0 + (x1 - x0) * i / n
        cv.drawLine(xx, 200, xx, 350, gp)
    cv.drawLine(x0 + 30, 275, x1 - 30, 275, gp)
    # motors
    mp = skia.Paint(AntiAlias=True, Color=col([60, 66, 74], a))
    for (wx, r) in (wf, wr):
        cv.drawCircle(wx, r, r * 0.45, mp)
        cv.drawCircle(wx, r, r * 0.30, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=8, Color=col(acc, 0.7 * a)))
    # wireframe truss
    xs = np.linspace(-L / 2 + 120, L / 2 - 120, 15)
    tops, bots = _scan(outline, xs)
    wp = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=6, Color=col(acc, 0.6 * a))
    glow = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=22, Color=col(acc, 0.35 * a))
    glow.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 16))
    path = poly_path(outline)
    cv.drawPath(path, glow)
    cv.drawPath(path, wp)
    wp.setStrokeWidth(4); wp.setColor(col(acc, 0.4 * a))
    for i in range(len(xs)):
        if tops[i] is None:
            continue
        bt = max(bots[i], 380)
        if tops[i] > bt:
            cv.drawLine(xs[i], bt, xs[i], tops[i], wp)
        if i + 1 < len(xs) and tops[i + 1] is not None:
            b2 = max(bots[i + 1], 380)
            if i % 2 == 0:
                cv.drawLine(xs[i], bt, xs[i + 1], tops[i + 1], wp)
            else:
                cv.drawLine(xs[i], tops[i], xs[i + 1], b2, wp)
    # joints
    jp = skia.Paint(AntiAlias=True, Color=col([230, 250, 255], 0.8 * a))
    for i in range(len(xs)):
        if tops[i] is not None:
            cv.drawCircle(xs[i], tops[i], 14, jp)


def _falcon_box(groups, fdoor):
    polys = [g[3] for g in groups if g[2] == fdoor and g[1] in ('lower', 'upper', 'glass')]
    P = np.vstack(polys)
    return P[:, 0].min(), P[:, 0].max(), P[:, 1].min(), P[:, 1].max()


def apply_falcon(cv, groups, fdoor, o, H):
    x0, x1, y0, y1 = _falcon_box(groups, fdoor)
    # door rises up and folds over the roof (foreshortened)
    cv.translate(0, y1)
    cv.translate(0, o * (y1 - y0) * 0.62)
    cv.scale(1, 1 - 0.5 * o)
    cv.translate(0, -y1)


def draw_cabin_opening(cv, car, fdoor, groups, H):
    polys = [g[3] for g in groups if g[2] == fdoor and g[1] in ('lower', 'upper')]
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(0, H)],
                [col([8, 8, 10]), col([30, 32, 36])], [0, 1]))
    for poly in polys:
        cv.drawPath(path_of(poly), p)
    # seat silhouette
    x0, x1, y0, y1 = _falcon_box(groups, fdoor)
    sp = skia.Paint(AntiAlias=True, Color=col([52, 54, 60]))
    w = x1 - x0
    seat = skia.Path()
    seat.moveTo(x0 + w * 0.2, y0 + 450); seat.lineTo(x0 + w * 0.75, y0 + 450); seat.lineTo(x0 + w * 0.8, y0 + 560)
    seat.lineTo(x0 + w * 0.3, y0 + 560); seat.lineTo(x0 + w * 0.12, y0 + 1150); seat.lineTo(x0 + w * 0.02, y0 + 1120); seat.close()
    cv.drawPath(seat, sp)
