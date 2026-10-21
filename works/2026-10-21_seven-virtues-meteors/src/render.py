"""七美德流星 逐帧渲染（skia）。

用法：tools/skpy render.py 3 40 80        # 渲染指定秒数的静帧到 ../work/still_*.png
render_frame(fi, arr) 是无状态的，可任意分段并行。
"""
import math
import os
import sys

import numpy as np
import skia

import virtues as V

W, H = V.W, V.H
F = V.FONT_DIR


def tf(name):
    return skia.Typeface.MakeFromFile(os.path.join(F, name))


SANS = tf('NotoSansSC_400Regular.ttf')
SANS_M = tf('NotoSansSC_500Medium.ttf')
SANS_B = tf('NotoSansSC_700Bold.ttf')
SANS_L = tf('NotoSansSC_300Light.ttf')
INTER = tf('Inter_500Medium.ttf')
INTER_L = tf('Inter_300Light.ttf')
MONO = skia.Typeface.MakeFromFile('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf')

GOLD = (236, 200, 126)


def col(c, a=1.0):
    return skia.Color4f(c[0] / 255, c[1] / 255, c[2] / 255, max(0.0, min(1.0, a)))


def paint(c, a=1.0, **kw):
    p = skia.Paint(AntiAlias=True, Color4f=col(c, a))
    for k, v in kw.items():
        getattr(p, 'set' + k)(v)
    return p


def text(canvas, s, x, y, size, c, a=1.0, face=SANS, align='left', spacing=0.0, blur=0.0):
    if a <= 0.003:
        return 0
    font = skia.Font(face, size)
    font.setSubpixel(True)
    p = paint(c, a)
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if spacing == 0:
        w = font.measureText(s)
        if align == 'center':
            x -= w / 2
        elif align == 'right':
            x -= w
        canvas.drawString(s, x, y, font, p)
        return w
    ws = [font.measureText(ch) for ch in s]
    w = sum(ws) + spacing * (len(s) - 1)
    if align == 'center':
        x -= w / 2
    elif align == 'right':
        x -= w
    for ch, cw in zip(s, ws):
        canvas.drawString(ch, x, y, font, p)
        x += cw + spacing
    return w


# ---------------- 背景：可平铺星云 + 星点 + 飞尘 ----------------
def _make_nebula():
    r = np.random.default_rng(7)
    h, w = 540, 1600
    img = np.zeros((h, w, 3))
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    f2 = fx ** 2 + (fy * h / w) ** 2 + 1e-9
    for c, amp, sc in [((70, 50, 140), 1.0, 22), ((30, 70, 140), 0.9, 16), ((120, 40, 80), 0.6, 26), ((30, 110, 110), 0.5, 18)]:
        noise = np.fft.fft2(r.normal(size=(h, w)))
        field = np.real(np.fft.ifft2(noise * np.exp(-f2 * (sc * 60) ** 2 / 2)))
        field = (field - field.mean()) / (field.std() + 1e-9)
        m = np.clip(field - 0.3, 0, None) ** 1.3 * amp
        img += m[..., None] * np.array(c)[None, None] / 255
    img = np.clip(img * 0.10, 0, 1)
    rgba = np.dstack([(img * 255).astype(np.uint8), np.full((h, w), 255, np.uint8)])
    return skia.Image.fromarray(np.ascontiguousarray(rgba), colorType=skia.kRGBA_8888_ColorType)


NEBULA = _make_nebula()
_r = np.random.default_rng(11)
STARS = np.column_stack([_r.uniform(0, W, 700), _r.uniform(0, H, 700), _r.uniform(0.3, 1.0, 700) ** 3,
                         _r.uniform(0, 6.28, 700), _r.uniform(0.5, 2.5, 700)])
DUST = np.column_stack([_r.uniform(0, 1, 260), _r.uniform(0, 1, 260), _r.uniform(0.15, 1.0, 260)])


def draw_background(canvas, t, fin):
    canvas.clear(skia.Color(7, 9, 18))
    # 暗角渐变底
    sh = skia.GradientShader.MakeRadial((W * 0.62, H * 0.42), W * 0.9,
                                        [skia.Color(20, 24, 44), skia.Color(6, 7, 14)])
    canvas.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Shader=sh))
    # 星云：慢速卷动
    off = -t * V.SPEED * 0.035
    m = skia.Matrix()
    m.setScale(W / 1600 * 1.25, H / 540 * 1.25)
    m.postTranslate(off, -off * 0.3)
    nsh = NEBULA.makeShader(skia.TileMode.kRepeat, skia.TileMode.kRepeat,
                            skia.SamplingOptions(skia.FilterMode.kLinear), m)
    p = skia.Paint(Shader=nsh, BlendMode=skia.BlendMode.kPlus)
    p.setAlphaf(0.9 * (1 - 0.6 * fin))
    canvas.drawRect(skia.Rect(0, 0, W, H), p)
    # 星点（极慢视差 + 闪烁）
    sp = skia.Paint(AntiAlias=True)
    for x, y, b, ph, fr in STARS:
        xx = (x - t * 4 * b) % W
        a = b * (0.55 + 0.45 * math.sin(t * fr + ph))
        sp.setColor4f(skia.Color4f(0.85, 0.9, 1.0, a * 0.9))
        canvas.drawCircle(xx, y, 0.6 + 1.2 * b, sp)
    # 飞尘：沿运动反方向划过，体现速度
    dp = skia.Paint(AntiAlias=True, StrokeWidth=1.2, StrokeCap=skia.Paint.kRound_Cap)
    d = V.DIR
    for u, v, z in DUST:
        sx = (u * (W + 400) - t * V.SPEED * z * 1.3) % (W + 400) - 200
        sy = (v * (H + 400) + t * V.SPEED * z * 1.3 * 0.30) % (H + 400) - 200
        ln = 4 + 26 * z
        dp.setColor4f(skia.Color4f(0.75, 0.8, 1.0, 0.10 + 0.25 * z))
        canvas.drawLine(sx, sy, sx - d[0] * ln, sy - d[1] * ln, dp)


# ---------------- 流星 ----------------
TRAIL_T = 2.6
NSAMP = 48


def trail_points(k, t):
    fw = V.smooth((t - V.T_FINALE - 1.0) / 3.0)      # 结尾：拖尾拉长并散成彩色丝带
    t0 = max(t - TRAIL_T * (1 + 0.6 * fw), V.BIRTH_T.get(k, t))
    if t - t0 < 0.02:
        return None
    taus = np.linspace(t0, t, NSAMP + int(40 * fw))
    ph = V.KEYS.index(k) * 0.9
    px, py = -V.DIR[1], V.DIR[0]
    pts = []
    for tau in taus:
        x, y = V.head_pos(k, tau)
        s = (t - tau) * V.SPEED
        x, y = x - V.DIR[0] * s, y - V.DIR[1] * s
        if fw > 0:
            q = min(s / 900.0, 1.6) ** 1.6
            off = fw * q * (70 * math.sin(s * 0.006 + ph + t * 0.8) + 45 * math.sin(s * 0.017 + ph * 2.3 - t * 1.3))
            x, y = x + px * off, y + py * off
        pts.append((x, y))
    return pts


def draw_meteor(canvas, k, t, lead, fin):
    name, latin, c = V.VIRTUES[k]
    pts = trail_points(k, t)
    if pts is None:
        return
    b = V.brightness(k, t)
    born = V.ease_out((t - V.BIRTH_T[k]) / 1.2)
    is_lead = (k == lead) and fin < 0.5
    alpha = (0.38 + 0.62 * b) * born
    hx, hy = pts[-1]
    path = skia.Path()
    path.moveTo(*pts[0])
    for p in pts[1:]:
        path.lineTo(*p)
    tail = pts[0]
    cols = [col(c, 0.0), col(c, 0.35 * alpha), col(c, alpha)]
    sh = skia.GradientShader.MakeLinear([tail, (hx, hy)], [x.toColor() for x in cols], [0.0, 0.6, 1.0])
    # 外层辉光
    g = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=9 + 6 * b, Shader=sh,
                   StrokeCap=skia.Paint.kRound_Cap, StrokeJoin=skia.Paint.kRound_Join,
                   MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 7))
    g.setAlphaf(0.55)
    g.setBlendMode(skia.BlendMode.kPlus)
    canvas.drawPath(path, g)
    # 核心细线
    cp = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=1.6 + 1.6 * b, Shader=sh,
                    StrokeCap=skia.Paint.kRound_Cap, StrokeJoin=skia.Paint.kRound_Join)
    cp.setBlendMode(skia.BlendMode.kPlus)
    canvas.drawPath(path, cp)
    # 白色内芯（靠近头部）
    n = len(pts)
    p2 = skia.Path()
    p2.moveTo(*pts[int(n * 0.72)])
    for p in pts[int(n * 0.72) + 1:]:
        p2.lineTo(*p)
    wsh = skia.GradientShader.MakeLinear([pts[int(n * 0.72)], (hx, hy)],
                                         [skia.Color4f(1, 1, 1, 0).toColor(), skia.Color4f(1, 1, 1, 0.8 * alpha).toColor()])
    canvas.drawPath(p2, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=1.2 + 1.4 * b,
                                   Shader=wsh, StrokeCap=skia.Paint.kRound_Cap))

    # 头部光晕
    R = 26 + 34 * b + (30 if is_lead else 0)
    rg = skia.GradientShader.MakeRadial((hx, hy), R, [col(c, 0.55 * alpha).toColor(), col(c, 0.12 * alpha).toColor(), col(c, 0).toColor()], [0, 0.35, 1])
    canvas.drawCircle(hx, hy, R, skia.Paint(Shader=rg, BlendMode=skia.BlendMode.kPlus))
    core = 3.2 + 3.5 * b + (2.5 if is_lead else 0)
    canvas.drawCircle(hx, hy, core * 1.8, paint(c, 0.5 * alpha, MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 4)))
    canvas.drawCircle(hx, hy, core, paint((255, 255, 255), min(1, alpha * 1.2)))

    if is_lead:
        # 星芒 + 光环
        sp = skia.Paint(AntiAlias=True, BlendMode=skia.BlendMode.kPlus)
        for ang, ln, wd in [(62, 150, 1.4), (152, 120, 1.4), (20, 70, 1.0), (110, 70, 1.0)]:
            a = math.radians(ang + 4 * math.sin(t * 0.7))
            dx, dy = math.cos(a) * ln, math.sin(a) * ln
            lg = skia.GradientShader.MakeLinear([(hx - dx, hy - dy), (hx + dx, hy + dy)],
                                                [skia.Color4f(1, 1, 1, 0).toColor(), skia.Color4f(1, 1, 1, 0.75).toColor(), skia.Color4f(1, 1, 1, 0).toColor()])
            sp.setShader(lg)
            sp.setStrokeWidth(wd)
            canvas.drawLine(hx - dx, hy - dy, hx + dx, hy + dy, sp)
        canvas.drawCircle(hx, hy, 48, paint(c, 0.22, Style=skia.Paint.kStroke_Style, StrokeWidth=2.0))
        canvas.drawCircle(hx, hy, 48, paint(c, 0.08))
    return hx, hy


def draw_labels(canvas, k, t, lead, hx, hy, fin, lead_mix, heads):
    name, latin, c = V.VIRTUES[k]
    born = V.ease_out((t - V.BIRTH_T[k] - 0.6) / 1.0)
    a = born * (1 - fin)
    if k != lead:
        # 靠得太近的暗星让位给更亮的星，避免标签叠字
        bk = V.brightness(k, t)
        for o, (ox, oy) in heads.items():
            if o == k or not (o == lead or V.brightness(o, t) > bk):
                continue
            d = math.hypot(ox - hx, (oy - hy) * 1.6)
            a *= V.smooth((d - 40) / 60) if o != lead else V.smooth((d - 80) / 80)
    if a <= 0:
        return
    b = V.brightness(k, t)
    m = lead_mix.get(k, 0.0)  # 0 普通标签 → 1 榜首标签
    if m < 1:
        aa = a * (1 - m) * (0.55 + 0.45 * b)
        text(canvas, name, hx + 22, hy - 4, 24, (235, 238, 245), aa, SANS_M)
        text(canvas, latin, hx + 22, hy + 18, 14, c, aa * 0.9, INTER, spacing=1.5)
    if m > 0:
        aa = a * m
        text(canvas, 'NO.1', hx + 30, hy - 48, 17, GOLD, aa, INTER, spacing=3)
        text(canvas, name, hx + 30, hy - 6, 40, (255, 255, 255), aa, SANS_B)
        text(canvas, latin, hx + 32, hy + 22, 19, c, aa, INTER, spacing=3)


# ---------------- HUD ----------------
def fmt_year(y):
    return (f'{-y}', 'BC') if y < 0 else (f'{y}', 'AD')


def draw_hud(canvas, t, fin):
    a = 1 - fin
    if a <= 0:
        return
    y = V.year_at(t)
    num, era = fmt_year(y)
    w = text(canvas, num, 80, 118, 84, (245, 245, 248), a, MONO)
    text(canvas, era, 80 + w + 14, 118, 30, (200, 205, 220), a * 0.8, INTER, spacing=2)
    canvas.drawLine(62, 150, 62, 318, paint((150, 160, 190), 0.45 * a, StrokeWidth=1.5))
    text(canvas, 'NO.1  ·  此刻最亮的美德', 82, 172, 19, (190, 195, 210), a * 0.85, SANS, spacing=2)
    # 名字交叉淡入
    i = V.event_index(t, 0.15)
    k = V.LEADERS[i]
    u = V.smooth((t - (V.EV_T[i] - 0.15)) / 0.5) if i > 0 else 1.0
    prev = V.LEADERS[i - 1] if i > 0 else k
    for kk, aa, dy in ([(prev, 1 - u, -10 * u), (k, u, 10 * (1 - u))] if prev != k else [(k, 1.0, 0)]):
        n_, lat, c = V.VIRTUES[kk]
        text(canvas, n_, 82, 228 + dy, 50, c, a * aa, SANS_B)
        text(canvas, lat, 84, 258 + dy, 19, c, a * aa * 0.8, INTER, spacing=3)
    canvas.drawLine(82, 276, 360, 276, paint((150, 160, 190), 0.35 * a, StrokeWidth=1))
    text(canvas, '群星易主', 82, 310, 22, (200, 205, 220), a * 0.9, SANS)
    n = V.CHANGES[i]
    pop = 1 + 0.35 * max(0.0, 1 - (t - V.EV_T[i]) / 0.5) if (i > 0 and V.CHANGES[i] != V.CHANGES[i - 1] and t >= V.EV_T[i]) else 1.0
    cw = text(canvas, str(n), 204, 312, 40 * pop, GOLD, a, MONO, align='center')
    text(canvas, '次', 246, 310, 22, (200, 205, 220), a * 0.9, SANS)


def draw_caption(canvas, t):
    for i, e in enumerate(V.EVENTS_RAW):
        t0 = V.EV_T[i] - 0.25
        t1 = (V.EV_T[i + 1] - 0.5) if i + 1 < len(V.EV_T) else V.T_FINALE + 0.8
        if not (t0 - 0.1 <= t <= t1 + 0.5):
            continue
        a = V.smooth((t - t0) / 0.4) * (1 - V.smooth((t - t1) / 0.4))
        if a <= 0:
            continue
        dy = 12 * (1 - V.ease_out((t - t0) / 0.6))
        # 金色年份 + 两侧细线
        lab = e[1]
        w = text(canvas, lab, W / 2, 920 + dy, 28, GOLD, a, SANS_M, align='center', spacing=4)
        lp = paint(GOLD, 0.45 * a, StrokeWidth=1.2)
        canvas.drawLine(W / 2 - w / 2 - 110, 911 + dy, W / 2 - w / 2 - 24, 911 + dy, lp)
        canvas.drawLine(W / 2 + w / 2 + 24, 911 + dy, W / 2 + w / 2 + 110, 911 + dy, lp)
        # 白字说明（带柔和投影）
        text(canvas, e[3], W / 2, 984 + dy, 44, (0, 0, 0), a * 0.7, SANS_M, align='center', blur=6)
        text(canvas, e[3], W / 2, 984 + dy, 44, (248, 248, 250), a, SANS_M, align='center')


# ---------------- 事件特效 ----------------
def draw_fx(canvas, t, heads):
    for i, e in enumerate(V.EVENTS_RAW):
        dt = t - V.EV_T[i]
        if dt < -0.2 or dt > 3.2:
            continue
        lead = e[2]
        changed = i == 0 or V.LEADERS[i - 1] != lead
        if lead in heads and changed and 0 <= dt < 1.4:
            hx, hy = heads[lead]
            c = V.VIRTUES[lead][2]
            u = dt / 1.4
            r = 30 + 260 * V.ease_out(u)
            canvas.drawCircle(hx, hy, r, paint(c, 0.55 * (1 - u), Style=skia.Paint.kStroke_Style, StrokeWidth=2.5 * (1 - u) + 0.5))
            canvas.drawCircle(hx, hy, r * 0.62, paint((255, 255, 255), 0.25 * (1 - u), Style=skia.Paint.kStroke_Style, StrokeWidth=1.2))
            fl = max(0.0, 1 - dt / 0.35)
            if fl > 0:
                rg = skia.GradientShader.MakeRadial((hx, hy), 220, [skia.Color4f(1, 1, 1, 0.5 * fl).toColor(), skia.Color4f(1, 1, 1, 0).toColor()])
                canvas.drawCircle(hx, hy, 220, skia.Paint(Shader=rg, BlendMode=skia.BlendMode.kPlus))
        if e[5] == 'burst' and 0 <= dt < 2.0:
            # 新星诞生：每颗新星放射状光粒
            for k in e[4]:
                if k not in heads:
                    continue
                hx, hy = heads[k]
                c = V.VIRTUES[k][2]
                r = V.rng_for('burst', i, k)
                for j in range(26):
                    ang = r.uniform(0, math.tau)
                    sp = r.uniform(80, 260)
                    d = sp * V.ease_out(dt / 1.6)
                    px, py = hx + math.cos(ang) * d, hy + math.sin(ang) * d
                    canvas.drawCircle(px, py, r.uniform(1.0, 2.6), paint(c, 0.9 * (1 - dt / 2.0), BlendMode=skia.BlendMode.kPlus))
        if e[5] == 'constellation' and 0 <= dt < 3.2:
            # 七颗星连成星座
            a = V.smooth(dt / 0.6) * (1 - V.smooth((dt - 2.4) / 0.8))
            order = sorted([k for k in heads], key=lambda k: heads[k][0])
            pts = [heads[k] for k in V.KEYS if k in heads]
            pts = sorted(pts, key=lambda p: math.atan2(p[1] - 540, p[0] - 900))
            lp = paint(GOLD, 0.5 * a, Style=skia.Paint.kStroke_Style, StrokeWidth=1.3,
                       PathEffect=skia.DashPathEffect.Make([10, 7], -dt * 30))
            path = skia.Path()
            path.addPoly(pts, True)
            canvas.drawPath(path, lp)
            for p in pts:
                canvas.drawCircle(p[0], p[1], 14, paint(GOLD, 0.5 * a, Style=skia.Paint.kStroke_Style, StrokeWidth=1.2))
            text(canvas, 'VII  VIRTUTES', W / 2, 150, 30, GOLD, a * 0.85, INTER, align='center', spacing=10)


def camera(t, heads, lead):
    """推近 + 晃动 + 色调。返回 (scale, cx, cy, sx, sy, red)"""
    i = V.event_index(t, 0.0)
    dt = t - V.EV_T[i]
    e = V.EVENTS_RAW[i]
    env = V.smooth(dt / 0.8) * (1 - V.smooth((dt - 3.0) / 2.0)) if dt >= 0 else 0.0
    scale = 1 + 0.045 * env
    cx, cy = heads.get(lead, (W / 2, H / 2))
    sx = sy = 0.0
    red = 0.0
    if e[5] in ('shake', 'plague') and 0 <= dt < 1.8:
        amp = (16 if e[5] == 'plague' else 12) * math.exp(-dt * 2.2)
        sx = amp * (math.sin(dt * 71) * 0.6 + math.sin(dt * 47 + 1) * 0.4)
        sy = amp * (math.sin(dt * 59 + 2) * 0.6 + math.sin(dt * 83) * 0.4)
    if e[5] == 'plague':
        red = V.smooth(dt / 0.4) * (1 - V.smooth((dt - 3.5) / 1.5))
    return scale, cx, cy, sx, sy, red


# ---------------- 结尾 ----------------
def draw_finale(canvas, t):
    dt = t - V.T_FINALE
    if dt < 2.5:
        return
    cx, cy = V.FINAL_C
    g = V.smooth((dt - 2.5) / 2.0)
    pulse = 1 + 0.05 * math.sin(t * 2.2)
    rg = skia.GradientShader.MakeRadial((cx, cy), 520, [skia.Color4f(1, 1, 1, 0.38 * g).toColor(),
                                                         skia.Color4f(0.9, 0.92, 1, 0.08 * g).toColor(),
                                                         skia.Color4f(0, 0, 0, 0).toColor()], [0, 0.25, 1])
    canvas.drawCircle(cx, cy, 520, skia.Paint(Shader=rg, BlendMode=skia.BlendMode.kPlus))
    canvas.drawCircle(cx, cy, 34 * pulse, paint((255, 255, 255), g, MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 14)))
    canvas.drawCircle(cx, cy, 22 * pulse, paint((255, 255, 255), g))
    ring = V.ease_out((dt - 2.5) / 2.5)
    canvas.drawCircle(cx, cy, 160 * ring, paint((220, 225, 240), 0.4 * g, Style=skia.Paint.kStroke_Style, StrokeWidth=2.5))
    sp = skia.Paint(AntiAlias=True, BlendMode=skia.BlendMode.kPlus)
    for j, (ang, ln) in enumerate([(-62, 420), (28, 330), (-150, 260), (118, 300), (-10, 200), (75, 180), (-100, 220), (160, 180)]):
        a = math.radians(ang + 3 * math.sin(t * 0.4 + j))
        L = ln * g
        dx, dy = math.cos(a) * L, math.sin(a) * L
        lg = skia.GradientShader.MakeLinear([(cx, cy), (cx + dx, cy + dy)], [skia.Color4f(1, 1, 1, 0.7).toColor(), skia.Color4f(1, 1, 1, 0).toColor()])
        sp.setShader(lg)
        sp.setStrokeWidth(1.4)
        canvas.drawLine(cx, cy, cx + dx, cy + dy, sp)
    ta = V.smooth((t - V.T_END_TEXT) / 1.0)
    dy = 14 * (1 - V.ease_out((t - V.T_END_TEXT) / 1.2))
    text(canvas, V.FINAL_Q, W / 2, 862 + dy, 66, (0, 0, 0), ta * 0.7, SANS_B, align='center', blur=8)
    text(canvas, V.FINAL_Q, W / 2, 862 + dy, 66, (255, 255, 255), ta, SANS_B, align='center')
    tb = V.smooth((t - V.T_END_TEXT - 1.0) / 1.0)
    text(canvas, V.FINAL_SUB, W / 2, 945, 30, (200, 205, 220), tb * 0.85, SANS_L, align='center', spacing=3)
    text(canvas, V.FOOTNOTE, W / 2, 1045, 16, (150, 155, 170), tb * 0.7, SANS, align='center')


def render_frame(fi, arr):
    t = fi / V.FPS
    surface = skia.Surface(arr, colorType=skia.kRGBA_8888_ColorType)
    canvas = surface.getCanvas()
    fin = V.smooth((t - V.T_FINALE - 1.5) / 2.0)
    draw_background(canvas, t, fin)
    lead = V.leader_at(t)
    alive = [k for k in V.KEYS if t >= V.BIRTH_T.get(k, 1e9)]
    heads = {k: V.head_pos(k, t) for k in alive}
    scale, cx, cy, sx, sy, red = camera(t, heads, lead)
    canvas.save()
    canvas.translate(sx, sy)
    canvas.translate(cx, cy)
    canvas.scale(scale, scale)
    canvas.translate(-cx, -cy)
    # 亮度低的先画，榜首最后画
    order = sorted(alive, key=lambda k: (k == lead, V.brightness(k, t)))
    for k in order:
        draw_meteor(canvas, k, t, lead, fin)
    i = V.event_index(t, 0.15)
    u = V.smooth((t - (V.EV_T[i] - 0.15)) / 0.5)
    mix = {lead: u if i > 0 and V.LEADERS[i - 1] != lead else 1.0}
    if i > 0 and V.LEADERS[i - 1] != lead:
        mix[V.LEADERS[i - 1]] = 1 - u
    for k in order:
        draw_labels(canvas, k, t, lead, *heads[k], fin, mix, heads)
    draw_fx(canvas, t, heads)
    draw_finale(canvas, t)
    canvas.restore()
    if red > 0:
        canvas.drawRect(skia.Rect(0, 0, W, H), paint((150, 20, 20), 0.22 * red, BlendMode=skia.BlendMode.kMultiply))
        rg = skia.GradientShader.MakeRadial((W / 2, H / 2), W * 0.7, [skia.Color4f(0, 0, 0, 0).toColor(), skia.Color4f(0.35, 0.02, 0.02, 0.45 * red).toColor()])
        canvas.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Shader=rg))
    # 开场淡入 / 结尾淡出
    fade = min(V.smooth(t / 0.8), 1 - V.smooth((t - (V.DURATION - 1.2)) / 1.2))
    draw_hud(canvas, t, fin)
    draw_caption(canvas, t)
    if fade < 1:
        canvas.drawRect(skia.Rect(0, 0, W, H), paint((0, 0, 0), 1 - fade))
    surface.flushAndSubmit()


if __name__ == '__main__':
    out = os.path.join(V.ROOT, 'work')
    os.makedirs(out, exist_ok=True)
    arr = np.zeros((H, W, 4), np.uint8)
    for s in sys.argv[1:]:
        fi = int(round(float(s) * V.FPS))
        arr[:] = 0
        render_frame(fi, arr)
        skia.Image.fromarray(arr, colorType=skia.kRGBA_8888_ColorType).save(os.path.join(out, f'still_{float(s):06.1f}.png'))
        print('still', s)
