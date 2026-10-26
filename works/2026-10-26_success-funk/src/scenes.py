"""《成功》v2 分镜。所有时间点取自音频节拍网格（analyze.py → events.json）。

节奏：105.7 BPM，首个重拍 T0=5.098s。主节奏段每小节 16 个 16 分格里 0/6/10 格最重，
所以每小节的字基本落在 0、6、10 格上。
"""
import math
import json
import os
import bisect

import numpy as np
import cv2
import skia

import engine as E
from engine import W, H, U, CX, CY, lin, smooth, ease_out, ease_in, back_out, spring, pulse, window, clamp01, hash01

HERE = os.path.dirname(os.path.abspath(__file__))
EV = json.load(open(os.path.join(HERE, "events.json")))
T0, BEAT = EV["T0"], EV["BEAT"]
S16, BAR = BEAT / 4, BEAT * 4
END = 32.25          # 与原音轨等长


def slot(b, s=0.0):
    """第 b 小节第 s 个 16 分格的时间（b=0 为第一次 drop）。"""
    return T0 + b * BAR + s * S16


HITS = [(s[0], s[2]) for s in EV["slots"] if s[2] > 0.10]
HIT_T = [h[0] for h in HITS]
SUB = np.array(EV["env"]["sub"], np.float32)


def sub_env(t):
    return float(SUB[min(max(int(t * 60), 0), len(SUB) - 1)])


def hits_between(a, b):
    i = bisect.bisect_left(HIT_T, a)
    j = bisect.bisect_right(HIT_T, b)
    return HITS[i:j]


def hit_level(t, decay=0.09, lo=0.0):
    return sum(s * pulse(t, ht, 0.01, decay) for ht, s in hits_between(t - 0.6, t) if s > lo)


# ---------------------------------------------------------------- 通用小工具
def SP(text, size, font="sans", kind="white", **kw):
    return E.text_sprite(text, round(size * U, 1), font, kind, **kw)


def slam(t, t0, dur=0.14, s0=1.8, c=1.3):
    """重拍砸入：(缩放, 透明度)。"""
    x = (t - t0) / dur
    s = 1 + (s0 - 1) * (1 - back_out(x, c)) if x < 1 else 1.0
    return s, clamp01((t - t0) / 0.025)


def ink_bottom(sp):
    return sp.derived("bottom", lambda s: float(np.nonzero(s.img[..., 3].max(1) > 0.02)[0].max() + 1))


def shadow(sp, x, y, s, a, dy=10.0, sigma=12.0, opacity=0.6):
    return dict(E.item(E.shadow_sprite(sp, sigma * U, opacity), x, y + dy * U, s, a), sil=False)


def refl(sp, x, y, s, a, gap=6.0, strength=0.3):
    r = E.reflect_sprite(sp, strength)
    return dict(E.item(r, x, y + (ink_bottom(sp) - sp.ay) * s + gap * U, s, a), sil=False)


def impact(t, t0, x=CX, y=CY):
    """冲击帧：重拍后两帧黑白剪影。"""
    return (t0, x, y) if 0 <= t - t0 < 2.0 / 60 else None


def shock(t, t0, x, y, speed=2600.0, width=50.0, amp=26.0, life=0.45):
    dt = t - t0
    if dt < 0 or dt > life:
        return None
    return (x, y, speed * dt * U, width * U * (1 + dt * 2), amp * U * (1 - dt / life) ** 1.5)


def spaced(text, size, font, kind, x, y, tracking, a=1.0, s=1.0, **kw):
    """逐字精灵按动态字距排开（字距动画用）。"""
    glyphs, total = E.layout(text, size * U, font, tracking)
    out = []
    for ch, f, gx, adv in glyphs:
        if ch == " ":
            continue
        sp = SP(ch, size, font, kind, **kw)
        out.append(E.item(sp, x + (gx + adv / 2 - total / 2) * s, y, s, a))
    return out


def line_width(text, size, font, tracking=0.0):
    return E.layout(text, size * U, font, tracking)[1]


DUST = E.Dust(170, seed=3)
DUST2 = E.Dust(90, seed=8)
STARS = None


def stars():
    global STARS
    if STARS is None:
        STARS = (E.make_stars(1100, 5), E.make_stars(500, 6))
    return STARS


class Embers:
    """缓慢上升、摇摆闪烁的火星（加色层）。"""

    def __init__(self, n=60, seed=0, x0=0, x1=W, color=(255, 170, 80)):
        rng = np.random.default_rng(seed)
        self.x = rng.uniform(x0, x1, n)
        self.y0 = rng.uniform(0, H + 200, n)
        self.v = rng.uniform(40, 160, n)
        self.ph = rng.uniform(0, 6.28, n)
        self.sz = rng.uniform(1.2, 3.2, n)
        self.color = color

    def draw(self, ac, t, cam, gain=1.0):
        M = E.cam_matrix(cam, 0.8)
        for i in range(len(self.x)):
            y = H + 100 - ((self.y0[i] + self.v[i] * t * U) % (H + 300))
            x = self.x[i] + 30 * U * math.sin(t * 1.7 + self.ph[i])
            fl = 0.5 + 0.5 * math.sin(t * 9 + self.ph[i] * 5)
            P = M @ np.array([x, y, 1.0])
            p = ac.paint(self.color, gain * (0.25 + 0.6 * fl), stroke=False, blur=self.sz[i] * 0.8 * U)
            ac.c.drawCircle(P[0], P[1], self.sz[i] * U, p)


# ---------------------------------------------------------------- 场景基类
class Scene:
    bg_par = 0.55       # 背景视差（远景动得少）
    zoom_hit = 0.010    # 节拍推镜幅度
    shake_amp = 6.0     # 节拍抖动幅度（像素）
    impacts = ()        # 额外的大冲击 [(时间, 强度)]
    zin = 0.0           # 入场：从放大 (1+zin) 倍快速拉回
    zout = 0.0          # 离场：最后 0.08s 快速推近 (1+zout) 倍

    def __init__(self, t0, t1):
        self.t0, self.t1 = t0, t1

    def cam(self, t):
        return {"z": 1.0, "rot": 0.0, "x": 0.0, "y": 0.0}

    def bg(self, t, vx, vy):
        raise NotImplementedError

    def items(self, t):
        return []

    def overlay(self, t, ac, cam):
        pass

    def fx(self, t, ctx):
        return {}

    def light(self, t):
        return None


# ================================================================ 0 前奏：什么是成功？
class Intro(Scene):
    bg_par = 0.5
    A, B = slot(-2, 0), slot(-2, 4)

    def __init__(self, t0, t1):
        super().__init__(t0, t1)
        self.burst = E.Burst(self.B, CX, CY + 40, n=120, speed=(300, 1300), gravity=900, life=(0.3, 0.9),
                             seed=11, ring=150)
        self.impacts = [(self.A, 0.5), (self.B, 1.1)]

    def cam(self, t):
        return {"z": 1.0 + 0.05 * smooth((t - 0.3) / 2.6), "rot": 0.5 * math.sin(t * 0.8), "x": 0.0,
                "y": -12 * smooth(t / 2.8)}

    def bg(self, t, vx, vy):
        on = smooth((t - 0.15) / 0.4)
        fl = 1 + 1.4 * pulse(t, self.A, 0.01, 0.25) + 1.8 * pulse(t, self.B, 0.01, 0.35)
        sm = E.s_grad([(0, (16, 11, 8)), (0.6, (8, 6, 5)), (0.712, (9, 7, 5)), (0.72, (4, 3, 3)), (1, (2, 2, 2))])
        f = E.s_fog(sm, t, (80, 56, 30), 0.10 * on)
        E.s_beam(sm, CX, -160, 0, 15, 1150, (255, 214, 160), 0.55 * on * fl, mod=0.45 + 1.0 * f, floor=CY + 240)
        E.s_glow(sm, CX, CY + 235, 560, 60, (255, 190, 120), 0.22 * on * fl)
        img = E.s_up(sm)
        DUST.draw(img, t, (255, 220, 170), gain=0.55 * on)
        return img

    def items(self, t):
        out = []
        ex = smooth((t - slot(-2, 14)) / (self.t1 - slot(-2, 14)))
        if t >= self.A:
            s, a = slam(t, self.A, 0.12, 1.5)
            out.append(E.item(SP("什么是", 86, "sans_m", "white"), CX, CY - 180 - 60 * ex, s * (1 + 0.25 * ex),
                              a * (1 - ex)))
        if t >= self.B:
            s, a = slam(t, self.B, 0.16, 2.3, 1.2)
            rx = 38 * (1 - ease_out((t - self.B) / 0.25))
            sp = SP("成功？", 240, "serif", "gold", extrude=20)
            ts = slot(-2, 8)
            sh = ((t - ts) / 0.42, 0.07, 1.7) if ts <= t <= ts + 0.5 else None
            sc = s * (1 + 0.6 * ex)
            out.append(E.item(sp, CX + 18 * U, CY + 30, sc, a * (1 - ex), rx=rx, shine=sh))
            out.append(refl(sp, CX + 18 * U, CY + 30, sc, a * (1 - ex) ** 2))
        return out

    def overlay(self, t, ac, cam):
        self.burst.draw(ac, t, cam)

    def fx(self, t, ctx):
        f = {"shock": [x for x in [shock(t, self.B, CX, CY + 30, 2400, 50, 30)] if x],
             "chroma": 0.0012 + 0.004 * pulse(t, self.B, 0.01, 0.12),
             "flash": 0.10 * pulse(t, self.B, 0.005, 0.03), "pop": 0.5 * pulse(t, self.B, 0.005, 0.09),
             "fade": smooth(t / 0.4),
             "bloom": {"thr": 1.0, "strength": 0.5, "streak": 0.2}}
        return f


# ================================================================ 1 铺垫：是运气？是天赋？
class Question(Scene):
    bg_par = 0.5
    A, B, C, D = slot(-1, 0), slot(-1, 4), slot(-1, 8), slot(-1, 10)

    def cam(self, t):
        p = smooth((t - self.A) / 1.4)
        return {"z": 1.02 + 0.03 * p, "rot": -1.2 + 0.8 * p, "x": 0.0, "y": 0.0}

    def bg(self, t, vx, vy):
        sm = E.s_grad([(0, (10, 9, 10)), (1, (2, 2, 3))])
        E.s_fog(sm, t, (60, 52, 52), 0.10)
        la = smooth((t - self.A) / 0.1) * (1 - 0.6 * smooth((t - self.B) / 0.15))
        lb = smooth((t - self.B) / 0.1)
        suck = smooth((t - self.C) / (self.D - self.C))
        E.s_glow(sm, CX - 430, CY + 150, 330, 55, (255, 200, 150), 0.32 * la * (1 - suck))
        E.s_glow(sm, CX + 430, CY + 150, 330, 55, (255, 200, 150), 0.32 * lb * (1 - suck))
        E.s_beam(sm, CX - 430, -200, 8, 9, 1300, (255, 225, 190), 0.25 * la * (1 - suck))
        E.s_beam(sm, CX + 430, -200, -8, 9, 1300, (255, 225, 190), 0.25 * lb * (1 - suck))
        E.s_glow(sm, CX, CY, 260, 260, (255, 220, 170), 0.9 * suck, halo=0.4)
        img = E.s_up(sm)
        DUST.draw(img, t, (230, 210, 190), gain=0.35)
        return img

    def items(self, t):
        out = []
        suck = ease_in((t - self.C) / (self.D - self.C + 0.02), 2.2)
        cap = window(t, self.A, self.D, 0.15, 0.12)
        out.append(E.item(SP("有人说", 44, "sans_l", "white"), CX, CY - 250, 1.0, 0.7 * cap))
        for txt, tt, x0, y0 in (("是运气？", self.A, CX - 430, CY - 10), ("是天赋？", self.B, CX + 430, CY + 10)):
            if t < tt:
                continue
            s, a = slam(t, tt, 0.10, 1.4)
            jit = (hash01(int(t * 60), tt) - 0.5) * 50 * U if t - tt < 0.07 else 0.0
            dim = 1 - 0.5 * smooth((t - self.B) / 0.12) if tt == self.A else 1.0
            x = x0 + (CX - x0) * suck + jit
            y = y0 + (CY - y0) * suck
            out.append(E.item(SP(txt, 128, "smiley", "white"), x, y, s * (1 - 0.8 * suck), a * dim * (1 - suck)))
        return out

    def fx(self, t, ctx):
        g = 0.6 * (window(t, self.A, self.A + 0.09, 0.0, 0.04) + window(t, self.B, self.B + 0.09, 0.0, 0.04))
        return {"glitch": g, "chroma": 0.0015 + 0.004 * g, "bloom": {"thr": 1.0, "strength": 0.45}}


# ================================================================ 2 倒数 3·2·1
class Countdown(Scene):
    bg_par = 0.7
    zoom_hit = 0.02
    D3, D2, D1, F = slot(-1, 10), slot(-1, 12), slot(-1, 14), slot(-1, 15)
    impacts = ((slot(-1, 10), 0.6), (slot(-1, 12), 0.7), (slot(-1, 14), 0.8))

    def _p(self, t):
        return clamp01((t - self.t0) / (self.t1 - self.t0))

    def cam(self, t):
        p = self._p(t)
        return {"z": 1.0 + 0.16 * ease_in(p, 2.2), "rot": 1.5 * ease_in(p, 2), "x": 0.0, "y": 0.0}

    def bg(self, t, vx, vy):
        p = self._p(t)
        sm = E.s_grad([(0, (8, 6, 5)), (1, (2, 1, 1))])
        E.s_fog(sm, t, (90, 60, 30), 0.12 + 0.2 * p, speed=(1.5, 0.0))
        E.s_glow(sm, CX, CY, 260 + 300 * p, 260 + 300 * p, (255, 200, 120), 0.3 + 1.6 * ease_in(p, 2), halo=0.4)
        img = E.s_up(sm)
        DUST.draw(img, t, (255, 210, 150), 0.5, speed=1 + 4 * p)
        return img

    def items(self, t):
        out = []
        ds = [("3", self.D3), ("2", self.D2), ("1", self.D1), (None, self.t1)]
        for i in range(3):
            d, td = ds[i]
            tn = ds[i + 1][1]
            if td <= t < tn + 0.03:
                s, a = slam(t, td, 0.08, 1.8)
                grow = 1 + 0.45 * clamp01((t - td) / (tn - td)) ** 1.5
                fade = 1 - smooth((t - (tn - 0.04)) / 0.07)
                out.append(E.item(SP(d, 470, "inter", "gold", extrude=16), CX, CY + 10, s * grow, a * fade))
        return out

    def overlay(self, t, ac, cam):
        p = self._p(t)
        M = E.cam_matrix(cam)
        for i in range(120):
            ang = hash01(i, 1) * 6.283
            sp = 0.6 + hash01(i, 2)
            r = (hash01(i, 3) + (t - self.t0) * sp * (0.8 + 3.0 * p)) % 1.0
            r0 = (80 + r ** 2 * 1400) * U
            L = (40 + 300 * p) * (0.4 + r) * U
            P = M @ np.array([[CX + math.cos(ang) * r0, CX + math.cos(ang) * (r0 + L)],
                              [CY + math.sin(ang) * r0, CY + math.sin(ang) * (r0 + L)], [1, 1]])
            pa = ac.paint((255, 220, 170), (0.15 + 0.6 * p) * min(1, r * 3), width=(1.2 + 2 * hash01(i, 4)) * U)
            ac.c.drawLine(P[0, 0], P[1, 0], P[0, 1], P[1, 1], pa)

    def fx(self, t, ctx):
        p = self._p(t)
        fl = 1.8 * ease_in((t - self.F) / (self.t1 - self.F), 2) if t > self.F else 0.0
        sh = [x for x in (shock(t, d, CX, CY, 3000, 40, 22, 0.25) for d in (self.D3, self.D2, self.D1)) if x]
        return {"flash": fl, "chroma": 0.002 + 0.01 * ease_in(p, 2), "shock": sh,
                "bloom": {"thr": 1.0, "strength": 0.55, "streak": 0.3}}


# ================================================================ 3 片名：成功（第一次 drop）
class Title(Scene):
    bg_par = 0.55
    zout = 0.22
    Y = CY - 50

    def __init__(self, t0, t1):
        super().__init__(t0, t1)
        self.burst = E.Burst(T0, CX, self.Y, n=280, speed=(600, 2400), gravity=900, drag=2.2, life=(0.5, 1.5),
                             seed=21, ring=260)
        self.embers = Embers(70, seed=4)
        self.impacts = [(T0, 1.8)]

    def cam(self, t):
        u = t - T0
        return {"z": 1.0 + 0.035 * smooth(u / 2.2), "rot": -0.8 * smooth(u / 2.2), "x": 0.0, "y": 0.0}

    def bg(self, t, vx, vy):
        u = t - T0
        on = smooth(u / 0.08)
        br = 0.8 + 0.4 * sub_env(t)
        sm = E.s_grad([(0, (10, 7, 4)), (0.62, (16, 10, 5)), (1, (3, 2, 1))])
        E.s_fog(sm, t, (90, 60, 26), 0.12)
        E.s_burst(sm, CX, self.Y, u * 0.12, 14, (255, 190, 90), 0.11 * on * br, seed=3)
        E.s_glow(sm, CX, self.Y, 600, 330, (255, 170, 60), 0.12 * on * br, halo=0.15)
        E.s_glow(sm, CX, CY + 175, 950, 20, (255, 200, 120), 0.22 * on)
        img = E.s_up(sm)
        DUST.draw(img, t, (255, 205, 130), 0.6)
        return img

    def items(self, t):
        u = t - T0
        out = []
        s, a = slam(t, T0, 0.2, 2.0, 1.1)
        rx = 34 * (1 - ease_out(u / 0.3))
        sp = SP("成功", 330, "serif", "gold", extrude=26)
        sh = None
        for ts in (slot(0, 5), slot(0, 11)):
            if ts <= t <= ts + 0.5:
                sh = ((t - ts) / 0.45, 0.07, 1.8)
        y = self.Y + 3 * U * math.sin(u * 2.4)
        out.append(E.item(sp, CX, y, s, a, rx=rx, shine=sh))
        out.append(refl(sp, CX, y, s, a * 0.8, strength=0.22))
        ts = slot(0, 2)
        if t >= ts:
            p = ease_out((t - ts) / 0.6)
            out += spaced("SUCCESS", 46, "inter", "white", CX, CY + 228, 1.8 - 1.1 * p, a=0.92 * p)
        return out

    def overlay(self, t, ac, cam):
        self.burst.draw(ac, t, cam, 1.2)
        self.embers.draw(ac, t, cam, 0.8)
        ts = slot(0, 2)
        if t >= ts:
            p = ease_out((t - ts) / 0.6)
            half = line_width("SUCCESS", 46, "inter", 1.8 - 1.1 * p) / 2 + 36 * U
            M = E.cam_matrix(cam)
            for sgn in (-1, 1):
                P = M @ np.array([[CX + sgn * half, CX + sgn * (half + 230 * U * p)], [CY + 228, CY + 228], [1, 1]])
                ac.c.drawLine(P[0, 0], P[1, 0], P[0, 1], P[1, 1], ac.paint((255, 200, 120), 0.8 * p, width=2 * U))

    def fx(self, t, ctx):
        u = t - T0
        return {"impact": impact(t, T0, CX, self.Y),
                "shock": [x for x in [shock(t, T0, CX, self.Y, 2600, 70, 42, 0.55)] if x],
                "rays": {"x": CX, "y": self.Y, "r": 320, "strength": 0.3 + 0.5 * pulse(t, T0, 0.01, 0.3),
                         "reach": 0.7, "tint": (255, 200, 120)},
                "flash": 0.22 * pulse(t, T0, 0.004, 0.03), "pop": 0.8 * pulse(t, T0, 0.005, 0.12),
                "chroma": 0.0015 + 0.007 * pulse(t, T0, 0.01, 0.2),
                "bloom": {"thr": 1.0, "strength": 0.5, "streak": 0.3}}


# ================================================================ 4 不是运气，不是天赋，而是——
class Negation(Scene):
    bg_par = 0.5
    zin = 0.18
    A, SA, XA = slot(1, 0), slot(1, 3), slot(1, 4)
    B, SB, XB = slot(1, 6), slot(1, 8), slot(1, 9)
    C = slot(1, 10)
    impacts = ((slot(1, 0), 0.7), (slot(1, 6), 0.7), (slot(1, 10), 0.9))

    def __init__(self, t0, t1):
        super().__init__(t0, t1)
        self.sp_a = E.Burst(self.SA + 0.02, CX, CY, n=90, speed=(400, 1500), angle=-30, spread=80, gravity=1300,
                            color="red", seed=31, life=(0.3, 0.8))
        self.sp_b = E.Burst(self.SB + 0.02, CX, CY, n=90, speed=(400, 1500), angle=-150, spread=80, gravity=1300,
                            color="red", seed=32, life=(0.3, 0.8))

    def _riser(self, t):
        return ease_in((t - self.C - 0.12) / (self.t1 - self.C - 0.12), 3.0)

    def cam(self, t):
        r = self._riser(t)
        return {"z": 1.0 + 0.75 * r, "rot": 4 * r, "x": 0.0, "y": 0.0}

    def bg(self, t, vx, vy):
        r = self._riser(t)
        red = pulse(t, self.SA, 0.01, 0.2) + pulse(t, self.SB, 0.01, 0.2)
        sm = E.s_grad([(0, (9, 9, 12)), (1, (2, 2, 3))])
        E.s_fog(sm, t, (60, 62, 72), 0.11, speed=(0.8, 0.1))
        E.s_glow(sm, CX, CY, 560, 240, (255, 40, 40), 0.12 * red)
        E.s_glow(sm, CX, CY, 500, 500, (255, 200, 120), 0.7 * r * r, halo=0.4)
        img = E.s_up(sm)
        DUST.draw(img, t, (210, 210, 225), 0.35, speed=1 + 6 * r)
        return img

    def items(self, t):
        out = []
        for txt, ta, tx, seed in (("不是运气", self.A, self.XA, 1), ("不是天赋", self.B, self.XB, 2)):
            sp = SP(txt, 165, "sans", "white")
            if ta <= t < tx:
                s, a = slam(t, ta, 0.10, 1.5)
                out.append(E.item(sp, CX, CY, s, a))
            elif tx <= t < tx + (0.7 if seed == 1 else 0.4):
                u = t - tx
                life, boost = (0.7, 1.0) if seed == 1 else (0.4, 2.2)
                for k, (piece, (ox, oy)) in enumerate(E.shatter(sp, 34, seed)):
                    h1, h2, h3 = hash01(k, seed), hash01(k, seed + 7), hash01(k, seed + 3)
                    vx = (ox * 2.4 * boost + (h1 - 0.5) * 700) * U
                    vy = (oy * 1.6 * boost - 250 - 550 * h2) * U
                    x = CX + ox + vx * u
                    y = CY + oy + vy * u + 1700 * U * u * u
                    out.append(E.item(piece, x, y, 1.0 + 0.5 * (boost - 1) * u, (1 - u / life) ** 1.5,
                                      rot=(h3 - 0.5) * 760 * u))
        if t >= self.C:
            s, a = slam(t, self.C, 0.14, 1.8)
            out.append(E.item(SP("而是", 210, "serif", "gold", extrude=16), CX, CY, s, a))
        return out

    def overlay(self, t, ac, cam):
        M = E.cam_matrix(cam)
        for ts, ang in ((self.SA, -16.0), (self.SB, 16.0)):
            u = t - ts
            if 0 <= u < 0.4:
                grow = ease_out(u / 0.06)
                fade = 1 - smooth((u - 0.06) / 0.3)
                L = 1000 * U
                c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
                x0, y0 = CX - c * L / 2, CY - s * L / 2
                P = M @ np.array([[x0, x0 + c * L * grow], [y0, y0 + s * L * grow], [1, 1]])
                ac.c.drawLine(P[0, 0], P[1, 0], P[0, 1], P[1, 1], ac.paint((255, 40, 30), fade, width=34 * U, blur=16 * U))
                ac.c.drawLine(P[0, 0], P[1, 0], P[0, 1], P[1, 1], ac.paint((255, 230, 220), fade, width=5 * U))
        self.sp_a.draw(ac, t, cam)
        self.sp_b.draw(ac, t, cam)

    def fx(self, t, ctx):
        r = self._riser(t)
        g = 0.4 * (window(t, self.XA, self.XA + 0.07, 0, 0.03) + window(t, self.XB, self.XB + 0.07, 0, 0.03))
        hit = pulse(t, self.SA, 0.004, 0.06) + pulse(t, self.SB, 0.004, 0.06)
        fw = 1.5 * ease_in((t - (self.t1 - 0.09)) / 0.09, 2) if t > self.t1 - 0.09 else 0.0
        return {"glitch": g, "flash": 0.04 * hit + fw, "pop": 0.4 * hit,
                "flash_col": (255, 120, 100) if fw < 0.05 else (255, 240, 225),
                "chroma": 0.0015 + 0.016 * r + 0.004 * g,
                "bloom": {"thr": 1.0, "strength": 0.45 + 0.4 * r, "streak": 0.25}}


# ================================================================ 5 跌倒 · 爬起 · 再来（主节奏进入）
class FallRise(Scene):
    bg_par = 0.6
    shake_amp = 8.0
    A, B, C = slot(2, 0), slot(2, 6), slot(2, 10)
    LAND = slot(2, 0) + 0.05
    FLOOR = CY + 175

    def __init__(self, t0, t1):
        super().__init__(t0, t1)
        self.puff = E.Burst(self.LAND, CX, self.FLOOR, n=80, speed=(150, 700), angle=-90, spread=170, gravity=500,
                            drag=4.0, color="white", life=(0.3, 0.8), width=(1.0, 2.4), seed=41)
        self.sparks = E.Burst(self.C, CX, CY - 10, n=220, speed=(500, 2100), ring=220, seed=42, life=(0.4, 1.2))
        self.impacts = [(self.LAND, 1.6), (self.B, 0.8), (self.C, 1.4)]

    def _roll(self, t):
        r = 0.0
        if t >= self.LAND:
            r = -5.5 * (1 - spring(t - self.LAND, 1.6, 5.0))
        if t >= self.B:
            r = -5.5 * spring(t - self.B, 1.5, 5.0)
        return r

    def cam(self, t):
        return {"z": 1.02, "rot": self._roll(t), "x": 0.0, "y": 0.0}

    def bg(self, t, vx, vy):
        sm = E.s_grad([(0, (12, 9, 7)), (0.66, (14, 10, 7)), (0.67, (6, 5, 4)), (1, (2, 2, 2))])
        E.s_fog(sm, t, (90, 64, 36), 0.10, speed=(0.9, -0.1))
        E.s_glow(sm, CX, self.FLOOR, 1100, 18, (255, 200, 130), 0.35)
        E.s_glow(sm, CX, CY - 40, 700, 360, (255, 170, 70), 0.08 + 0.15 * pulse(t, self.C, 0.01, 0.25), halo=0.15)
        img = E.s_up(sm)
        DUST.draw(img, t, (255, 210, 160), 0.45)
        return img

    def items(self, t):
        out = []
        sp1 = SP("跌倒", 290, "smiley", "white")
        ground = self.FLOOR - (ink_bottom(sp1) - sp1.ay)
        if self.A <= t < self.B + 0.08:
            u = t - self.A
            rot, sx, sy = 0.0, 1.0, 1.0
            if u < 0.05:
                y = ground - (1 - (u / 0.05) ** 2) * 300 * U
                sy = 1.12
                sx = 0.92
            else:
                v = u - 0.05
                y = ground - 34 * U * abs(math.sin(v * 13)) * math.exp(-v * 8)
                rot = -9 * (1 - spring(v, 1.5, 6.0))
                sq = pulse(t, self.LAND, 0.004, 0.07)
                sx, sy = 1 + 0.16 * sq, 1 - 0.2 * sq
            a = 1 - smooth((t - self.B) / 0.07)
            y += 260 * U * ease_in((t - self.B) / 0.08, 2)
            out.append(E.item(sp1, CX, y, 1.0, a, rot=rot, sx=sx, sy=sy))
            gap = ground - y          # 离地高度
            r = E.reflect_sprite(sp1, 0.2)
            out.append(dict(E.item(r, CX, self.FLOOR + gap + 6 * U, 1.0, a * 0.8 * clamp01(1 - gap / (160 * U)), rot=-rot,
                                   sx=sx, sy=sy), sil=False))
        sp2 = SP("爬起", 290, "smiley", "white")
        if self.B <= t < self.C + 0.08:
            u = t - self.B
            rise = 1 - spring(u, 1.7, 6.5)          # 0→1，带过冲
            y = ground + (1 - rise) * 700 * U
            a = clamp01(u / 0.04) * (1 - smooth((t - self.C) / 0.06))
            y -= 380 * U * ease_in((t - self.C) / 0.08, 2)
            stretch = 1 + 0.25 * math.exp(-u * 14)
            out.append(E.item(sp2, CX, y, 1.0, a, sx=1 / stretch ** 0.5, sy=stretch))
        if t >= self.C:
            s, a = slam(t, self.C, 0.16, 2.0, 1.2)
            sp3 = SP("再来", 300, "serif", "gold", extrude=24)
            sh = ((t - slot(2, 12)) / 0.4, 0.07, 1.8) if slot(2, 12) <= t <= slot(2, 12) + 0.5 else None
            out.append(E.item(sp3, CX, CY - 20, s, a, rx=26 * (1 - ease_out((t - self.C) / 0.25)), shine=sh))
            out.append(refl(sp3, CX, CY - 20, s, a * 0.8, strength=0.22))
        return out

    def overlay(self, t, ac, cam):
        self.puff.draw(ac, t, cam, 0.5)
        self.sparks.draw(ac, t, cam, 1.1)

    def fx(self, t, ctx):
        tail = smooth((t - slot(2, 15)) / (self.t1 - slot(2, 15)))
        return {"impact": impact(t, self.A, CX, CY),
                "shock": [x for x in (shock(t, self.LAND, CX, self.FLOOR, 2200, 40, 26, 0.4),
                                      shock(t, self.C, CX, CY - 20, 2800, 60, 40, 0.5)) if x],
                "flash": 0.12 * pulse(t, self.C, 0.004, 0.03) + 0.05 * pulse(t, self.LAND, 0.004, 0.03),
                "pop": 0.6 * pulse(t, self.C, 0.005, 0.1) + 0.35 * pulse(t, self.LAND, 0.005, 0.08),
                "glitch": 0.7 * tail, "chroma": 0.0015 + 0.006 * pulse(t, self.C, 0.01, 0.15) + 0.01 * tail,
                "rays": {"x": CX, "y": CY - 20, "r": 300, "strength": 0.35 * smooth((t - self.C) / 0.1),
                         "reach": 0.6, "tint": (255, 200, 120)} if t >= self.C else None,
                "bloom": {"thr": 1.0, "strength": 0.5, "streak": 0.3}}


# ================================================================ 6 失败 N 次（红色故障）
class Failure(Scene):
    bg_par = 0.4
    shake_amp = 9.0
    A = slot(3, 0)

    def _n(self, t):
        p = clamp01((t - self.A) / (BAR - S16 * 1.5))
        return max(1, min(99, 1 + int(98 * p ** 1.7)))

    def cam(self, t):
        u = t - self.A
        return {"z": 1.03 + 0.02 * u, "rot": 0.6 * math.sin(u * 7), "x": 6 * U * math.sin(u * 23),
                "y": 4 * U * math.cos(u * 19)}

    def bg(self, t, vx, vy):
        hv = hit_level(t)
        sm = E.s_grad([(0, (14, 1, 2)), (0.5, (9, 1, 1)), (1, (3, 0, 0))])
        E.s_fog(sm, t, (150, 12, 16), 0.10, speed=(1.4, 0.2))
        E.s_glow(sm, CX, CY, 820, 430, (255, 30, 30), 0.06 * (0.6 + 0.8 * hv))
        img = E.s_up(sm)
        DUST.draw(img, t, (255, 90, 80), 0.4)
        return img

    def items(self, t):
        out = []
        u = t - self.A
        s, a = slam(t, self.A, 0.1, 1.5)
        n = self._n(t)
        jit = lambda k: (hash01(int(t * 60), k) - 0.5) * 18 * U * (0.3 + hit_level(t))
        out.append(E.item(SP("失败", 180, "sans", "red"), CX - 360 + jit(1), CY + jit(2), s, a))
        # 数字每次变化轻微弹一下
        nt = self.A + ((max(0, n - 1) / 98) ** (1 / 1.7)) * (BAR - S16 * 1.5)
        pop = 1 + 0.12 * pulse(t, nt, 0.004, 0.05)
        out.append(E.item(SP(str(n), 300, "inter", "red"), CX + 110 + jit(3), CY + 6 + jit(4), s * pop, a))
        out.append(E.item(SP("次", 180, "sans", "red"), CX + 450 + jit(5), CY + jit(6), s, a))
        return out

    def overlay(self, t, ac, cam):
        u = t - self.A
        c = ac.c
        red = (255, 60, 50)
        m, L = 70 * U, 90 * U
        for x, y, dx, dy in ((m, m, 1, 1), (W - m, m, -1, 1), (m, H - m, 1, -1), (W - m, H - m, -1, -1)):
            c.drawLine(x, y, x + dx * L, y, ac.paint(red, 0.8, width=4 * U))
            c.drawLine(x, y, x, y + dy * L, ac.paint(red, 0.8, width=4 * U))
        if int(u * 4) % 2 == 0:
            c.drawCircle(m + 30 * U, m + 60 * U, 9 * U, ac.paint(red, 1.0, stroke=False))
        f = E._font("mono", 30 * U)
        c.drawString("ERROR  ×%02d" % self._n(t), m + 52 * U, m + 71 * U, f, ac.paint(red, 0.9, stroke=False))
        f2 = E._font("mono_m", 24 * U)
        if int(u * 6) % 3 != 0:
            c.drawString("TRY AGAIN", W - m - 170 * U, H - m - 20 * U, f2, ac.paint(red, 0.8, stroke=False))

    def fx(self, t, ctx):
        u = t - self.A
        acc = sum(pulse(t, slot(3, k), 0.004, 0.08) for k in (0, 6, 10))
        g = 0.16 + 0.55 * acc + 0.7 * smooth((u - (BAR - 0.35)) / 0.3)
        return {"glitch": g, "chroma": 0.004 + 0.01 * acc, "scan": 0.22, "sat": 1.1,
                "flash": 0.05 * acc, "pop": 0.3 * acc, "flash_col": (255, 60, 50),
                "bloom": {"thr": 0.9, "strength": 0.5, "tint": (1.0, 0.6, 0.55)}}


# ================================================================ 7 第 100 次 · 依然出发
class Hundred(Scene):
    bg_par = 0.55
    A, B, C = slot(4, 0), slot(4, 6), slot(4, 10)
    Y = CY - 70

    def __init__(self, t0, t1):
        super().__init__(t0, t1)
        self.burst = E.Burst(self.A, CX, self.Y, n=300, speed=(600, 2400), gravity=900, drag=2.2, life=(0.5, 1.4),
                             seed=51, ring=300)
        self.embers = Embers(60, seed=9)
        self.impacts = [(self.A, 1.7), (self.B, 0.6)]

    def _out(self, t):
        return ease_in((t - self.C - 0.25) / (self.t1 - self.C - 0.25), 2.4)

    def cam(self, t):
        o = self._out(t)
        return {"z": 1.0 + 0.03 * smooth((t - self.A) / 2), "rot": 0.0, "x": 500 * U * o, "y": -120 * U * o}

    def bg(self, t, vx, vy):
        u = t - self.A
        br = 0.8 + 0.4 * sub_env(t)
        sm = E.s_grad([(0, (14, 9, 4)), (0.6, (18, 11, 5)), (1, (4, 3, 1))])
        E.s_fog(sm, t, (110, 72, 30), 0.12, speed=(1.0, -0.2))
        E.s_beam(sm, CX, -300, 0, 22, 1500, (255, 210, 140), 0.09 * br)
        E.s_burst(sm, CX, self.Y, u * -0.1, 18, (255, 196, 100), 0.07 * br, seed=7)
        E.s_glow(sm, CX, self.Y, 650, 340, (255, 180, 70), 0.10 * br, halo=0.15)
        img = E.s_up(sm)
        DUST.draw(img, t, (255, 210, 140), 0.6, speed=1 + 3 * smooth((t - self.B) / 0.3))
        return img

    def items(self, t):
        out = []
        o = self._out(t)
        s, a = slam(t, self.A, 0.2, 2.2, 1.1)
        sp = SP((("第", "serif"), ("100", "inter", 1.12), ("次", "serif")), 220, "serif", "gold", extrude=20,
                tracking=0.08)
        sh = ((t - slot(4, 3)) / 0.45, 0.07, 1.9) if slot(4, 3) <= t <= slot(4, 3) + 0.55 else None
        out.append(E.item(sp, CX - 300 * U * o, self.Y, s, a, rx=30 * (1 - ease_out((t - self.A) / 0.3)), shine=sh))
        if t >= self.B:
            u = t - self.B
            x = CX - 900 * U * (1 - ease_out(u / 0.22, 4)) - 300 * U * o
            out.append(E.item(SP("依然出发", 118, "sans", "white", tracking=0.12), x, CY + 140, 1.0,
                              clamp01(u / 0.05), sx=1 + 0.5 * math.exp(-u * 20)))
        return out

    def overlay(self, t, ac, cam):
        self.burst.draw(ac, t, cam, 1.2)
        self.embers.draw(ac, t, cam, 0.7)
        if t >= self.B:
            u = t - self.B
            k = 0.35 + 0.65 * smooth((t - self.C) / 0.2)
            for i in range(70):
                y = (hash01(i, 5) * 1.2 - 0.1) * H
                sp = (2500 + 3500 * hash01(i, 6)) * U * (0.6 + 1.2 * k)
                L = (120 + 520 * hash01(i, 7)) * U * k
                x = W + 200 * U - ((hash01(i, 8) * 3000 * U + sp * u) % (W + 1200 * U))
                ac.c.drawLine(x, y, x + L, y, ac.paint((255, 225, 170), 0.5 * k * (0.3 + hash01(i, 9)),
                                                        width=(1 + 2.5 * hash01(i, 4)) * U))

    def fx(self, t, ctx):
        return {"impact": impact(t, self.A, CX, self.Y),
                "shock": [x for x in [shock(t, self.A, CX, self.Y, 2700, 70, 44, 0.55)] if x],
                "rays": {"x": CX, "y": self.Y, "r": 340, "strength": 0.28 + 0.45 * pulse(t, self.A, 0.01, 0.3),
                         "reach": 0.7, "tint": (255, 205, 130)},
                "flash": 0.2 * pulse(t, self.A, 0.004, 0.03), "pop": 0.7 * pulse(t, self.A, 0.005, 0.12),
                "flash_col": (255, 225, 170),
                "chroma": 0.0015 + 0.006 * pulse(t, self.A, 0.01, 0.2),
                "bloom": {"thr": 1.0, "strength": 0.5, "streak": 0.3}}


# ================================================================ 8 台阶：早起 · 读书 · 训练 · 复盘
class Stairs(Scene):
    bg_par = 1.0
    zout = 0.2
    zoom_hit = 0.008
    WORDS = ("早起", "读书", "训练", "复盘")
    STEP_W, STEP_H = 430.0, 175.0
    X0, Y0 = 250.0, 800.0

    def _ts(self, i):
        return slot(5, 4 * i)

    def _step(self, i):
        """第 i 级台阶顶面左端 (x, y)。"""
        return self.X0 + i * self.STEP_W, self.Y0 - i * self.STEP_H

    def _cam_target(self, i):
        x, y = self._step(i)
        return (x + self.STEP_W / 2 - CX) * U, (y - 130 - CY - 40) * U

    def cam(self, t):
        k = 0
        for i in range(4):
            if t >= self._ts(i) - 0.08:
                k = i
        x0, y0 = self._cam_target(max(0, k - 1))
        x1, y1 = self._cam_target(k)
        p = ease_out((t - self._ts(k) + 0.08) / 0.34, 3) if k > 0 else 1.0
        cx, cy = x0 + (x1 - x0) * p, y0 + (y1 - y0) * p
        enter = 1 - ease_out((t - self.t0) / 0.3, 3)
        return {"z": 1.0, "rot": -1.5, "x": cx + 250 * U * -enter, "y": cy + 160 * U * enter}

    def _lit(self, t, i):
        return smooth((t - self._ts(i)) / 0.06)

    def bg(self, t, vx, vy):
        sm = E.s_grad([(0, (12, 9, 6)), (1, (3, 2, 2))])
        E.s_fog(sm, t, (100, 70, 36), 0.06)
        ox, oy = vx, vy
        E.s_glow(sm, 2300 * U - ox, -450 * U - oy, 800, 620, (255, 210, 140), 0.75, halo=0.25)
        E.s_beam(sm, 2300 * U - ox, -450 * U - oy, -52, 10, 2600, (255, 220, 160), 0.12)
        img = E.s_up(sm)
        DUST.draw(img, t, (255, 210, 150), 0.5)
        v = E.Vec(-200 - 0, -300, W + 200, H + 300)
        v.c.translate(-ox, -oy)
        for i in range(-1, 6):
            x, y = self._step(i)
            lit = self._lit(t, i) if 0 <= i < 4 else (1.0 if i < 0 else 0.0)
            fw = self.STEP_W + 2
            # 立面
            sh = skia.GradientShader.MakeLinear([(x, y), (x, y + self.STEP_H)],
                                                [skia.Color(46, 34, 22), skia.Color(14, 11, 9)])
            v.c.drawRect(skia.Rect.MakeXYWH(x, y, fw, 1400), v.paint((255, 255, 255), shader=sh))
            # 顶面（略带透视的窄条）
            top = skia.Path()
            top.moveTo(x, y)
            top.lineTo(x + fw, y)
            top.lineTo(x + fw + 26, y - 30)
            top.lineTo(x + 26, y - 30)
            top.close()
            g = int(60 + 140 * lit)
            v.c.drawPath(top, v.paint((g, int(g * 0.78), int(g * 0.5))))
        v.comp(img)
        return img

    def items(self, t):
        out = []
        for i, w in enumerate(self.WORDS):
            ts = self._ts(i)
            if t < ts:
                continue
            u = t - ts
            x, y = self._step(i)
            sp = SP(w, 108, "sans", "white" if i < 3 else "gold", extrude=10 if i == 3 else 0)
            pop = back_out(u / 0.18, 2.2)
            cur = 1.0 if (i == 3 or t < self._ts(i + 1)) else 0.55
            yy = y - 30 - (ink_bottom(sp) - sp.ay)
            out.append(E.item(sp, x + self.STEP_W / 2 + 13, yy + (1 - pop) * 40 * U, 1.0, clamp01(u / 0.05) * cur,
                              sx=1.0, sy=max(0.05, pop)))
        return out

    def overlay(self, t, ac, cam):
        M = E.cam_matrix(cam)
        for i in range(4):
            lit = self._lit(t, i)
            if lit <= 0:
                continue
            x, y = self._step(i)
            fl = 1 + 2.5 * pulse(t, self._ts(i), 0.005, 0.15)
            P = M @ np.array([[x, x + self.STEP_W], [y, y], [1, 1]])
            ac.c.drawLine(P[0, 0], P[1, 0], P[0, 1], P[1, 1], ac.paint((255, 190, 90), 0.55 * lit * fl, width=16 * U, blur=10 * U))
            ac.c.drawLine(P[0, 0], P[1, 0], P[0, 1], P[1, 1], ac.paint((255, 240, 200), 0.9 * lit, width=3 * U))
        # 光球沿抛物线逐级跳上台阶
        k = -1
        for i in range(4):
            if t >= self._ts(i) - 0.2:
                k = i
        if k >= 0:
            x1, y1 = self._step(k)
            x1 += self.STEP_W / 2
            y1 -= 230
            x0, y0 = (self._step(k - 1)[0] + self.STEP_W / 2, self._step(k - 1)[1] - 230) if k > 0 else (x1 - 600, y1 + 300)
            p = clamp01((t - (self._ts(k) - 0.2)) / 0.2)
            px = x0 + (x1 - x0) * p
            py = y0 + (y1 - y0) * p - math.sin(p * math.pi) * 120
            for j in range(10):
                q = max(0.0, p - j * 0.025)
                qx = x0 + (x1 - x0) * q
                qy = y0 + (y1 - y0) * q - math.sin(q * math.pi) * 120
                P = M @ np.array([qx, qy, 1.0])
                ac.c.drawCircle(P[0], P[1], (9 - j * 0.7) * U, ac.paint((255, 220, 150), 0.5 * (1 - j / 10), stroke=False, blur=6 * U))
            P = M @ np.array([px, py, 1.0])
            ac.c.drawCircle(P[0], P[1], 26 * U, ac.paint((255, 200, 110), 0.8, stroke=False, blur=18 * U))
            ac.c.drawCircle(P[0], P[1], 8 * U, ac.paint((255, 250, 235), 1.0, stroke=False, blur=2 * U))

    def fx(self, t, ctx):
        acc = sum(pulse(t, self._ts(i), 0.004, 0.09) for i in range(4))
        return {"flash": 0.03 * acc, "pop": 0.25 * acc, "chroma": 0.0015 + 0.004 * acc,
                "bloom": {"thr": 1.0, "strength": 0.5, "streak": 0.3}}


# ================================================================ 9 熬过的夜
class Night(Scene):
    bg_par = 0.45
    zin = 0.18
    zout = 0.2
    A, B, C = slot(6, 0), slot(6, 6), slot(6, 10)
    MOON = (CX + 640, CY - 300)
    CLOCK = (CX + 260, CY - 10)
    impacts = ((slot(6, 0), 0.6), (slot(6, 6), 1.3))

    def cam(self, t):
        u = t - self.A
        return {"z": 1.0 + 0.03 * u, "rot": 0.8 - 0.5 * u, "x": -20 * U * u, "y": 0.0}

    def bg(self, t, vx, vy):
        u = t - self.A
        sm = E.s_grad([(0, (2, 4, 14)), (0.7, (10, 16, 42)), (1, (5, 7, 18))])
        E.s_fog(sm, t, (40, 60, 120), 0.12, speed=(0.6, 0.05), idx=2)
        E.s_glow(sm, *self.MOON, 260, 260, (150, 180, 255), 0.35, halo=0.5)
        E.s_glow(sm, *self.CLOCK, 500, 500, (80, 120, 255), 0.12 * pulse(t, self.B, 0.01, 0.3))
        img = E.s_up(sm)
        sa, sb = stars()
        rot = cv2.getRotationMatrix2D((E.wx(CX + 900), E.wx(-900)), -u * 2.5, 1.0)
        tw = 0.5 + 0.5 * math.sin(t * 3.1)
        st = cv2.warpAffine(sa * (0.7 + 0.3 * tw) + sb * (1 - 0.6 * tw), rot, (E.BW, E.BH), flags=cv2.INTER_LINEAR)
        img += st[..., None] * lin((200, 215, 255)) * 1.2
        mx, my = E.wx(self.MOON[0]), E.wx(self.MOON[1])
        v = E.Vec(self.MOON[0] - 120, self.MOON[1] - 120, self.MOON[0] + 120, self.MOON[1] + 120)
        moon = skia.Path()
        moon.addCircle(self.MOON[0], self.MOON[1], 62)
        cut = skia.Path()
        cut.addCircle(self.MOON[0] + 30, self.MOON[1] - 18, 56)
        moon = skia.Op(moon, cut, skia.PathOp.kDifference_PathOp)
        v.c.drawPath(moon, v.paint((240, 244, 255)))
        v.comp(img, gain=2.2)
        self._clock(img, t, vx, vy)
        return img

    def _clock(self, img, t, vx, vy):
        """时钟表盘（快转的指针），画进背景层，位于“夜”字后面。"""
        cx, cy = self.CLOCK
        R = 330 * U
        on = smooth((t - self.A) / 0.25)
        fl = 1 + 2 * pulse(t, self.B, 0.005, 0.2)
        v = E.Vec(cx - R - 60, cy - R - 60, cx + R + 60, cy + R + 60)
        v.c.translate(-vx, -vy)
        c = v.c
        col = (150, 180, 255)
        for blur, k in ((6.0, 0.5), (0.0, 1.0)):
            a = 0.33 * on * fl * k
            c.drawCircle(cx, cy, R, v.paint(col, a, stroke=True, width=2.5 * U, blur=blur))
            c.drawCircle(cx, cy, R + 14 * U, v.paint(col, a * 0.35, stroke=True, width=1.2 * U, blur=blur))
            for i in range(60):
                ang = i / 60 * 6.2832
                r0 = R - (26 if i % 5 == 0 else 12) * U
                c.drawLine(cx + math.cos(ang) * r0, cy + math.sin(ang) * r0, cx + math.cos(ang) * R, cy + math.sin(ang) * R,
                           v.paint((170, 195, 255), a * 1.1, stroke=True, width=(3 if i % 5 == 0 else 1.5) * U, blur=blur))
            u = t - self.A
            speed = 1.0 + 3.0 * smooth((t - self.C) / 0.3)
            for L, w, sp in ((R * 0.62, 7 * U, 0.35), (R * 0.88, 4 * U, 3.0)):
                ang = -math.pi / 2 + u * sp * speed * 6.2832
                c.drawLine(cx, cy, cx + math.cos(ang) * L, cy + math.sin(ang) * L,
                           v.paint((200, 220, 255), a * 1.5, stroke=True, width=w, blur=blur))
        v.comp(img, gain=1.4, mode="add")

    def items(self, t):
        out = []
        sp = SP("熬过的", 150, "serif", "white")
        glyphs, total = E.layout("熬过的", 150 * U, "serif")
        x0 = CX - 420 * U
        for k, (ch, f, gx, adv) in enumerate(glyphs):
            tk = self.A + k * 0.07
            if t < tk:
                continue
            s, a = slam(t, tk, 0.1, 1.4)
            out.append(E.item(SP(ch, 150, "serif", "white"), x0 + gx + adv / 2 - total / 2, CY + 40, s, a))
        if t >= self.B:
            s, a = slam(t, self.B, 0.16, 2.2, 1.2)
            out.append(E.item(SP("夜", 360, "serif", "ice", extrude=18, ex_front=(70, 90, 140), ex_back=(10, 14, 30)),
                              self.CLOCK[0], self.CLOCK[1], s, a, rx=22 * (1 - ease_out((t - self.B) / 0.25))))
        return out

    def overlay(self, t, ac, cam):
        c = ac.c
        on = smooth((t - self.A) / 0.25)
        u = t - self.A
        hh = 3 + int(u * 1.3)
        mm = int((u * 1700) % 60)
        txt = "%02d%s%02d" % (hh, ":" if int(t * 2) % 2 == 0 else " ", mm)
        f = E._font("mono", 54 * U)
        c.drawString(txt, 120 * U, 150 * U, f, ac.paint((170, 200, 255), 0.85 * on, stroke=False))
        c.drawString("AM", 120 * U + f.measureText(txt) + 14 * U, 150 * U, E._font("mono_m", 28 * U),
                     ac.paint((170, 200, 255), 0.6 * on, stroke=False))

    def fx(self, t, ctx):
        return {"shock": [x for x in [shock(t, self.B, *self.CLOCK, 2600, 60, 36, 0.5)] if x],
                "flash": 0.08 * pulse(t, self.B, 0.004, 0.03), "pop": 0.5 * pulse(t, self.B, 0.005, 0.1),
                "flash_col": (170, 200, 255),
                "glitch": 0.5 * window(t, self.C, self.C + 0.08, 0, 0.04),
                "chroma": 0.0015 + 0.006 * pulse(t, self.B, 0.01, 0.2),
                "gain": (0.96, 1.0, 1.06),
                "bloom": {"thr": 0.9, "strength": 0.55, "tint": (0.8, 0.88, 1.0), "streak": 0.3}}


# ================================================================ 10 流过的汗
class Sweat(Scene):
    bg_par = 0.45
    zin = 0.18
    zout = 0.2
    A, B, C = slot(7, 0), slot(7, 6), slot(7, 10)
    DROP = (CX + 260, CY - 10)
    FLOOR = CY + 285
    impacts = ((slot(7, 0), 0.6), (slot(7, 6), 1.3), (slot(7, 10), 0.6))

    def __init__(self, t0, t1):
        super().__init__(t0, t1)
        self.splash = E.Burst(self.B, *self.DROP, n=160, speed=(400, 1500), gravity=2200, drag=1.5,
                              color="blue", life=(0.4, 1.0), seed=61, ring=150, width=(1.5, 3.5))
        rng = np.random.default_rng(62)
        self.rx = rng.uniform(-300, W + 300, 260)
        self.ry = rng.uniform(0, 1, 260)
        self.rv = rng.uniform(0.8, 1.4, 260)

    def _rain_time(self, t):
        """雨的时间：在“汗”砸下时放慢（时间扭曲），之后恢复。"""
        u = t - self.A
        slow = 0.0
        if t > self.B:
            v = min(t - self.B, 0.5)
            slow = 0.85 * (v - 0.25 * v * v / 0.5) if v < 0.5 else 0.85 * 0.375
        return u - slow

    def cam(self, t):
        u = t - self.A
        return {"z": 1.02 + 0.02 * u, "rot": -0.6 + 0.4 * u, "x": 15 * U * u, "y": 0.0}

    def bg(self, t, vx, vy):
        sm = E.s_grad([(0, (5, 7, 10)), (0.75, (8, 10, 14)), (0.76, (3, 4, 5)), (1, (1, 1, 2))])
        E.s_fog(sm, t, (70, 85, 100), 0.10, speed=(0.3, 0.6), idx=1)
        E.s_glow(sm, CX, -200, 900, 600, (180, 200, 230), 0.14)
        E.s_glow(sm, CX, self.FLOOR, 1100, 14, (160, 190, 230), 0.18)
        img = E.s_up(sm)
        DUST2.draw(img, t, (200, 220, 255), 0.25)
        return img

    def items(self, t):
        out = []
        glyphs, total = E.layout("流过的", 150 * U, "serif")
        x0 = CX - 420 * U
        for k, (ch, f, gx, adv) in enumerate(glyphs):
            tk = self.A + k * 0.07
            if t < tk:
                continue
            s, a = slam(t, tk, 0.1, 1.4)
            out.append(E.item(SP(ch, 150, "serif", "white"), x0 + gx + adv / 2 - total / 2, CY + 40, s, a))
        if t >= self.B:
            u = t - self.B
            y = self.DROP[1] - 700 * U * (1 - min(1.0, u / 0.09) ** 2) if u < 0.09 else self.DROP[1]
            sq = pulse(t, self.B + 0.09, 0.004, 0.08)
            sp = SP("汗", 360, "serif", "ice", extrude=18, ex_front=(80, 100, 130), ex_back=(10, 14, 22))
            out.append(E.item(sp, self.DROP[0], y, 1.0, clamp01(u / 0.03), sx=1 + 0.18 * sq, sy=1 - 0.15 * sq))
            out.append(refl(sp, self.DROP[0], y, 1.0, 0.7 * clamp01(u / 0.03), strength=0.25))
        return out

    def overlay(self, t, ac, cam):
        rt = self._rain_time(t)
        M = E.cam_matrix(cam, 0.7)
        slow = 1.0 - 0.85 * window(t, self.B, self.B + 0.5, 0.02, 0.3)
        for i in range(len(self.rx)):
            fall = (self.ry[i] + rt * 1.6 * self.rv[i]) % 1.0
            y = -100 * U + fall * (H + 200 * U)
            x = self.rx[i] - fall * 260 * U
            L = 70 * U * self.rv[i] * (0.25 + 0.75 * slow)
            P = M @ np.array([[x, x - L * 0.25], [y, y - L], [1, 1]])
            ac.c.drawLine(P[0, 0], P[1, 0], P[0, 1], P[1, 1],
                          ac.paint((200, 220, 250), 0.18 + 0.3 * (self.rv[i] - 0.8), width=(1.2 + 1.4 * (self.rv[i] - 0.8)) * U))
        self.splash.draw(ac, t + 0.0, cam, 0.9)

    def fx(self, t, ctx):
        sh = []
        for d in (0.09, 0.2, 0.34):
            x = shock(t, self.B + d, *self.DROP, 1500, 34, 22 - 40 * d, 0.7)
            if x:
                sh.append(x)
        x = shock(t, self.C, *self.DROP, 1800, 30, 16, 0.6)
        if x:
            sh.append(x)
        return {"shock": sh, "flash": 0.06 * pulse(t, self.B + 0.09, 0.004, 0.03),
                "pop": 0.45 * pulse(t, self.B + 0.09, 0.005, 0.1), "flash_col": (200, 220, 255),
                "chroma": 0.0015 + 0.005 * pulse(t, self.B, 0.01, 0.2), "gain": (0.97, 1.0, 1.04), "sat": 0.9,
                "bloom": {"thr": 1.0, "strength": 0.5, "tint": (0.85, 0.92, 1.0), "streak": 0.25}}


# ================================================================ 11 没人看见的努力
class Unseen(Scene):
    bg_par = 0.5
    zin = 0.18
    zout = 0.2
    A, B, C = slot(8, 0), slot(8, 6), slot(8, 10)
    Y1, Y2 = CY - 150, CY + 95

    def __init__(self, t0, t1):
        super().__init__(t0, t1)
        self.burst = E.Burst(self.B, CX, self.Y2, n=200, speed=(500, 2000), ring=220, seed=71, life=(0.4, 1.2))
        self.impacts = [(self.B, 1.5)]

    def _spot(self, t):
        """聚光灯落点 x：从左扫到右，在“努力”砸下时归中并放大。"""
        p = clamp01((t - self.A) / (self.B - self.A - 0.05))
        x = CX - 760 * U + 1250 * U * ease_io_(p)
        k = smooth((t - self.B + 0.04) / 0.1)
        return x + (CX - x) * k, k

    def cam(self, t):
        u = t - self.A
        return {"z": 1.0 + 0.02 * u, "rot": 0.0, "x": 0.0, "y": 0.0}

    def bg(self, t, vx, vy):
        x, k = self._spot(t)
        sm = E.s_grad([(0, (3, 3, 4)), (1, (1, 1, 1))])
        E.s_fog(sm, t, (60, 55, 50), 0.08)
        E.s_beam(sm, x - 350 * U * (1 - k), -350, 14 * (1 - k), 10 + 18 * k, 1500, (255, 236, 205), 0.55 + 0.4 * k)
        E.s_glow(sm, x, CY + 260, 260 + 600 * k, 40 + 30 * k, (255, 220, 170), 0.3 + 0.3 * k)
        img = E.s_up(sm)
        DUST.draw(img, t, (255, 235, 200), 0.25)
        return img

    def light(self, t):
        x, k = self._spot(t)
        g = 0.05 + 1.25 * np.exp(-(((E._XX - x) / ((300 + 900 * k) * U)) ** 2 + ((E._YY - self.Y1) / ((300 + 700 * k) * U)) ** 2))
        return g.astype(np.float32)

    def items(self, t):
        out = []
        out.append(E.item(SP("没人看见的", 128, "sans_b", "white", tracking=0.06), CX, self.Y1, 1.0, smooth((t - self.A) / 0.1)))
        if t >= self.B:
            s, a = slam(t, self.B, 0.18, 2.2, 1.2)
            sp = SP("努力", 320, "serif", "gold", extrude=26)
            sh = ((t - self.C) / 0.45, 0.07, 1.9) if self.C <= t <= self.C + 0.55 else None
            out.append(E.item(sp, CX, self.Y2, s, a, rx=30 * (1 - ease_out((t - self.B) / 0.28)), shine=sh))
        return out

    def overlay(self, t, ac, cam):
        self.burst.draw(ac, t, cam, 1.1)

    def fx(self, t, ctx):
        return {"impact": impact(t, self.B, CX, self.Y2),
                "shock": [x for x in [shock(t, self.B, CX, self.Y2, 2700, 70, 42, 0.55)] if x],
                "flash": 0.15 * pulse(t, self.B, 0.004, 0.03), "pop": 0.7 * pulse(t, self.B, 0.005, 0.12),
                "rays": {"x": CX, "y": self.Y2, "r": 320, "strength": 0.4 * smooth((t - self.B) / 0.1),
                         "reach": 0.7, "tint": (255, 205, 130)} if t >= self.B else None,
                "chroma": 0.0015 + 0.006 * pulse(t, self.B, 0.01, 0.2),
                "bloom": {"thr": 1.0, "strength": 0.5, "streak": 0.3}}


def ease_io_(x):
    return E.ease_io(x)


# ================================================================ 12 终将被看见（日出）
class Dawn(Scene):
    bg_par = 0.35
    zin = 0.18
    A, B, C = slot(9, 0), slot(9, 6), slot(9, 10)
    HORIZON = CY + 215

    def __init__(self, t0, t1):
        super().__init__(t0, t1)
        self.impacts = [(self.B, 1.3)]

    def _sun(self, t):
        p = clamp01((t - self.t0) / (self.t1 - self.t0))
        return CX, self.HORIZON + 40 - 165 * U * (0.35 * p + 0.65 * ease_in(p, 2.2))

    def _bright(self, t):
        return 0.6 + 0.4 * smooth((t - self.A) / 0.4) + 1.2 * ease_in((t - self.C) / (self.t1 - self.C), 2.2)

    def cam(self, t):
        u = t - self.A
        return {"z": 1.0 + 0.03 * u + 0.06 * ease_in((t - self.C) / (self.t1 - self.C), 2), "rot": 0.0,
                "x": 0.0, "y": -10 * U * u}

    def bg(self, t, vx, vy):
        sx, sy = self._sun(t)
        b = self._bright(t)
        hz = self.HORIZON
        sm = E.s_grad([(0, (6, 10, 32)), (0.45, (40, 32, 70)), (0.78, (200, 110, 70)), (0.8, (255, 170, 80)),
                       (0.801, (14, 10, 12)), (1, (6, 5, 6))], 0, hz / 0.8)
        f = E.s_fog(sm, t, (255, 140, 80), 0.05 * b, scale=0.7, speed=(0.25, 0.0))
        E.s_glow(sm, sx, sy, 900, 240, (255, 150, 60), 0.32 * b, halo=0.4)
        E.s_glow(sm, sx, sy, 240, 240, (255, 220, 160), 0.45 * b)
        img = E.s_up(sm)
        v = E.Vec(sx - 160, sy - 160, sx + 160, sy + 160)
        v.c.clipRect(skia.Rect.MakeLTRB(sx - 200, -10000, sx + 200, hz))
        v.c.drawCircle(sx, sy, 78, v.paint((255, 246, 225)))
        v.comp(img, gain=2.6 * b)
        gy = int(E.wx(hz))
        img[gy:] *= 0.18
        DUST2.draw(img, t, (255, 210, 170), 0.3)
        return img

    def items(self, t):
        out = []
        if t >= self.A:
            s, a = slam(t, self.A, 0.12, 1.5)
            sp = SP("终将", 120, "serif", "white", tracking=0.25)
            out.append(shadow(sp, CX, CY - 315, s, a, 6, 10, 0.5))
            out.append(E.item(sp, CX, CY - 315, s, a))
        if t >= self.B:
            s, a = slam(t, self.B, 0.18, 2.2, 1.2)
            sp = SP("被看见", 250, "serif", "gold", extrude=22)
            out.append(shadow(sp, CX, CY - 125, s, a * 0.8, 14, 18, 0.55))
            out.append(E.item(sp, CX, CY - 125, s, a, rx=30 * (1 - ease_out((t - self.B) / 0.28))))
        return out

    def overlay(self, t, ac, cam):
        sx, sy = self._sun(t)
        P = E.cam_matrix(cam, self.bg_par) @ np.array([sx, sy, 1.0])
        E.flare(ac, P[0], P[1], 0.35 * self._bright(t) + 0.8 * pulse(t, self.B, 0.01, 0.4))

    def fx(self, t, ctx):
        sx, sy = self._sun(t)
        P = E.cam_matrix(ctx["cam"], self.bg_par) @ np.array([sx, sy, 1.0])
        w = ease_in((t - (self.t1 - 0.12)) / 0.12, 2) if t > self.t1 - 0.12 else 0.0
        return {"rays": {"x": P[0], "y": P[1], "src": "bright", "screen": True, "thr": 1.1, "strength": 0.6 * self._bright(t),
                         "reach": 0.8, "tint": (255, 190, 120)},
                "flash": 0.1 * pulse(t, self.B, 0.004, 0.04) + 2.2 * w, "pop": 0.5 * pulse(t, self.B, 0.005, 0.12),
                "chroma": 0.0015 + 0.005 * pulse(t, self.B, 0.01, 0.2),
                "exposure": 1.0 + 0.15 * ease_in((t - self.C) / (self.t1 - self.C), 2),
                "bloom": {"thr": 1.0, "strength": 0.55, "streak": 0.4}}


# ================================================================ 13 高潮：成功，是熬出来的
_MOUNTAINS = None


def mountains():
    """三层山脊（远→近），中间留出山谷给太阳。返回 [(多边形点列, 颜色, 边缘光强度)]。"""
    global _MOUNTAINS
    if _MOUNTAINS is None:
        layers = []
        rng = np.random.default_rng(81)
        for k, (base, amp, col, rim) in enumerate(((CY + 170, 150, (70, 52, 70), 0.6), (CY + 230, 210, (34, 24, 32), 0.8),
                                                   (CY + 300, 300, (8, 6, 9), 1.0))):
            xs = np.linspace(-300, W + 300, 200)
            n = np.zeros_like(xs)
            for o in range(5):
                fr = (o + 1) * 1.7
                n += rng.normal(0, 1) * np.sin(xs / W * fr * math.pi + rng.uniform(0, 6)) / (o + 1)
            valley = 1 - 0.85 * np.exp(-((xs - Climax.SUN[0]) / (380 + 120 * k)) ** 2)
            ys = base - amp * (0.55 + 0.45 * np.tanh(n)) * valley
            if k == 2:   # 近景主峰（插旗处）在右侧
                ys -= 170 * np.exp(-((xs - (CX + 560)) / 170) ** 2)
            layers.append((np.stack([xs, ys], 1), col, rim))
        _MOUNTAINS = layers
    return _MOUNTAINS


class Climax(Scene):
    bg_par = 0.4
    A = slot(10, 0)
    Y = CY - 225
    SUN = (CX - 400, CY + 150)

    def __init__(self, t0, t1):
        super().__init__(t0, t1)
        self.burst = E.Burst(self.A, CX, self.Y, n=360, speed=(700, 2800), gravity=800, drag=2.0,
                             life=(0.6, 1.8), seed=91, ring=320)
        self.embers = Embers(90, seed=12, color=(255, 190, 100))
        self.impacts = [(self.A, 2.0)]
        rng = np.random.default_rng(93)
        self.gx = rng.uniform(-100, W + 100, 150)
        self.gy = rng.uniform(0, 1, 150)
        self.gv = rng.uniform(0.25, 0.6, 150)

    def cam(self, t):
        u = t - self.A
        return {"z": 1.0 + 0.06 * smooth(u / 2.3), "rot": 0.0, "x": 0.0, "y": -14 * U * smooth(u / 2.3)}

    def peak(self):
        pts = mountains()[2][0]
        i = int(np.argmin(pts[:, 1]))
        return pts[i, 0], pts[i, 1]

    def bg(self, t, vx, vy, dim=1.0):
        u = t - self.A
        br = (0.85 + 0.3 * sub_env(t)) * dim
        sx, sy = self.SUN
        sm = E.s_grad([(0, (10, 16, 44)), (0.45, (70, 50, 90)), (0.8, (255, 160, 80)), (1, (255, 205, 120))],
                      0, CY + 160)
        E.s_fog(sm, t, (255, 170, 110), 0.05, scale=0.7, speed=(0.3, 0.0))
        E.s_burst(sm, sx, sy, u * 0.06, 16, (255, 200, 120), 0.08 * br, falloff=700, seed=5)
        sm *= dim
        sun_k = dim ** 0.4
        E.s_glow(sm, sx, sy, 1100, 300, (255, 160, 70), 0.36 * br / max(dim, 1e-3) * sun_k * dim, halo=0.4)
        E.s_glow(sm, sx, sy, 280, 280, (255, 225, 170), 0.5 * br / max(dim, 1e-3) * sun_k * dim ** 0.5)
        img = E.s_up(sm)
        v = E.Vec(sx - 140, sy - 140, sx + 140, sy + 140)
        v.c.drawCircle(sx, sy, 80, v.paint((255, 248, 230)))
        v.comp(img, gain=3.0 * br)
        v = E.Vec(-300, 0, W + 300, H + 300)
        for pts, col, rim in mountains():
            path = skia.Path()
            path.moveTo(pts[0, 0], H + 400)
            for x, y in pts:
                path.lineTo(x, y)
            path.lineTo(pts[-1, 0], H + 400)
            path.close()
            v.c.drawPath(path, v.paint(col))
            ridge = skia.Path()
            ridge.moveTo(*pts[0])
            for x, y in pts[1:]:
                ridge.lineTo(x, y)
            v.c.drawPath(ridge, v.paint((255, 200, 130), 0.55 * rim, stroke=True, width=2.2, blur=1.2))
        px, py = self.peak()
        v.c.drawLine(px, py, px, py - 120, v.paint((20, 16, 14), stroke=True, width=4))
        flag = skia.Path()
        flag.moveTo(px + 2, py - 120)
        for k in range(13):
            q = k / 12
            flag.lineTo(px + 2 + q * 92, py - 120 + 7 * math.sin(q * 5 - t * 9) * q)
        for k in range(12, -1, -1):
            q = k / 12
            flag.lineTo(px + 2 + q * 92, py - 66 + 7 * math.sin(q * 5 - t * 9) * q)
        flag.close()
        v.c.drawPath(flag, v.paint((210, 30, 28)))
        v.comp(img, gain=dim)
        DUST2.draw(img, t, (255, 220, 170), 0.35 * dim)
        return img

    def items(self, t):
        out = []
        u = t - self.A
        s, a = slam(t, self.A, 0.22, 2.3, 1.0)
        sp = SP("成功", 340, "serif", "gold", extrude=28)
        sh = None
        for ts in (slot(10, 6), slot(10, 13)):
            if ts <= t <= ts + 0.55:
                sh = ((t - ts) / 0.5, 0.07, 2.0)
        out.append(shadow(sp, CX, self.Y, s, a * 0.8, 16, 20, 0.5))
        out.append(E.item(sp, CX, self.Y, s, a, rx=36 * (1 - ease_out(u / 0.32)), shine=sh))
        ts = slot(10, 4)
        if t >= ts:
            glyphs, total = E.layout("是熬出来的", 80 * U, "serif_b", 0.32)
            for k, (ch, f, gx, adv) in enumerate(glyphs):
                p = ease_out((t - ts - k * 0.06) / 0.35)
                if p <= 0:
                    continue
                out.append(E.item(SP(ch, 80, "serif_b", "white"), CX + gx + adv / 2 - total / 2,
                                  CY + 255 + 30 * U * (1 - p), 1.0, p))
        return out

    def overlay(self, t, ac, cam):
        self.burst.draw(ac, t, cam, 1.3)
        self.embers.draw(ac, t, cam, 0.8)
        u = t - self.A
        M = E.cam_matrix(cam, 0.8)
        for i in range(len(self.gx)):
            y = ((self.gy[i] + u * self.gv[i]) % 1.0) * (H + 100) - 50
            x = self.gx[i] + 20 * U * math.sin(u * 2 + i)
            P = M @ np.array([x, y, 1.0])
            fl = 0.5 + 0.5 * math.sin(t * 8 + i * 1.7)
            ac.c.drawCircle(P[0], P[1], (1.5 + 1.5 * hash01(i, 1)) * U,
                            ac.paint((255, 210, 120), 0.5 * fl * smooth(u / 0.3), stroke=False, blur=1.5 * U))
        P = E.cam_matrix(cam, self.bg_par) @ np.array([self.SUN[0], self.SUN[1], 1.0])
        E.flare(ac, P[0], P[1], 0.5 + 0.9 * pulse(t, self.A, 0.01, 0.5))

    def fx(self, t, ctx):
        P = E.cam_matrix(ctx["cam"], self.bg_par) @ np.array([self.SUN[0], self.SUN[1], 1.0])
        return {"impact": impact(t, self.A, CX, self.Y),
                "shock": [x for x in [shock(t, self.A, CX, self.Y, 2800, 80, 48, 0.6)] if x],
                "rays": {"x": P[0], "y": P[1], "src": "bright", "screen": True, "thr": 1.1, "strength": 0.75, "reach": 0.85,
                         "tint": (255, 195, 120)},
                "rays2": {"x": CX, "y": self.Y, "r": 340, "strength": 0.28 + 0.5 * pulse(t, self.A, 0.01, 0.5),
                          "reach": 0.65, "tint": (255, 210, 140)},
                "flash": 0.25 * pulse(t, self.A, 0.004, 0.035), "pop": 0.55 * pulse(t, self.A, 0.005, 0.1),
                "chroma": 0.0015 + 0.008 * pulse(t, self.A, 0.01, 0.25),
                "bloom": {"thr": 1.0, "strength": 0.6, "streak": 0.4}}


# ================================================================ 14 结尾：致每一个还在坚持的你
class Outro(Scene):
    bg_par = 0.4
    A = slot(11, 0)

    def __init__(self, t0, t1, climax):
        super().__init__(t0, t1)
        self.cl = climax

    def _dim(self, t):
        return 1 - 0.75 * smooth((t - self.A) / 1.2)

    def cam(self, t):
        u = t - self.A
        c = self.cl.cam(self.A)
        return {"z": c["z"] + 0.02 * u, "rot": 0.0, "x": 0.0, "y": c["y"] - 10 * U * u}

    def bg(self, t, vx, vy):
        return self.cl.bg(t, vx, vy, dim=self._dim(t))

    def items(self, t):
        out = []
        u = t - self.A
        a = 1 - smooth(u / 0.45)
        if a > 0:
            sp = SP("成功", 340, "serif", "gold", extrude=28)
            out.append(E.item(sp, CX, Climax.Y - 80 * U * ease_in(u / 0.45, 2), 1 - 0.1 * smooth(u / 0.45), a))
            glyphs, total = E.layout("是熬出来的", 80 * U, "serif_b", 0.32)
            for ch, f, gx, adv in glyphs:
                out.append(E.item(SP(ch, 80, "serif_b", "white"), CX + gx + adv / 2 - total / 2, CY + 255, 1.0, a))
        text = "致 每一个还在坚持的你"
        glyphs, total = E.layout(text, 76 * U, "kai", 0.12)
        for k, (ch, f, gx, adv) in enumerate(glyphs):
            if ch == " ":
                continue
            p = ease_out((t - self.A - 0.25 - k * 0.07) / 0.5)
            if p <= 0:
                continue
            sp = SP(ch, 76, "kai", "white")
            x, y = CX + gx + adv / 2 - total / 2, CY - 170 + 24 * U * (1 - p)
            out.append(shadow(sp, x, y, 1.0, p, 5, 8, 0.6))
            out.append(E.item(sp, x, y, 1.0, p))
        return out

    def overlay(self, t, ac, cam):
        p = ease_out((t - self.A - 0.9) / 0.8)
        if p > 0:
            L = 360 * U * p
            ac.c.drawLine(CX - L, CY - 95 * U, CX + L, CY - 95 * U, ac.paint((255, 200, 120), 0.7, width=2 * U))
            f = E._font("inter_b", 26 * U)
            txt = "S U C C E S S"
            ac.c.drawString(txt, CX - f.measureText(txt) / 2, CY - 45 * U, f, ac.paint((255, 210, 140), 0.75 * p, stroke=False))

    def fx(self, t, ctx):
        P = E.cam_matrix(ctx["cam"], self.bg_par) @ np.array([Climax.SUN[0], Climax.SUN[1], 1.0])
        return {"rays": {"x": P[0], "y": P[1], "src": "bright", "screen": True, "thr": 1.1, "strength": 0.6 * self._dim(t),
                         "reach": 0.85, "tint": (255, 195, 120)},
                "fade": 1 - smooth((t - (END - 0.75)) / 0.65),
                "bloom": {"thr": 1.0, "strength": 0.55, "streak": 0.3}}


# ---------------------------------------------------------------- 时间线
_CLIMAX = Climax(slot(10), slot(11))
SCENES = [
    Intro(0.0, slot(-1, 0)),
    Question(slot(-1, 0), slot(-1, 10)),
    Countdown(slot(-1, 10), slot(0)),
    Title(slot(0), slot(1)),
    Negation(slot(1), slot(2)),
    FallRise(slot(2), slot(3)),
    Failure(slot(3), slot(4)),
    Hundred(slot(4), slot(5)),
    Stairs(slot(5), slot(6)),
    Night(slot(6), slot(7)),
    Sweat(slot(7), slot(8)),
    Unseen(slot(8), slot(9)),
    Dawn(slot(9), slot(10)),
    _CLIMAX,
    Outro(slot(11), END + 1.0, _CLIMAX),
]


def scene_at(t):
    for sc in SCENES:
        if sc.t0 <= t < sc.t1:
            return sc
    return SCENES[-1] if t >= SCENES[-1].t0 else SCENES[0]


def camera(t):
    sc = scene_at(t)
    c = dict(sc.cam(t))
    hv, sx, sy, sr = 0.0, 0.0, 0.0, 0.0
    for ht, s in hits_between(t - 0.5, t):
        dt = t - ht
        hv += s * pulse(t, ht, 0.01, 0.09)
        e = s ** 1.6 * math.exp(-dt / 0.07)
        ph = hash01(ht) * 6.283
        sx += e * math.sin(dt * 61 + ph)
        sy += e * math.cos(dt * 53 + ph * 1.3)
        sr += e * math.sin(dt * 47 + ph * 2.1)
    for it, s in sc.impacts:
        dt = t - it
        if 0 <= dt < 0.6:
            e = s * math.exp(-dt / 0.11)
            ph = hash01(it, 7) * 6.283
            sx += e * 2.2 * math.sin(dt * 70 + ph)
            sy += e * 2.2 * math.cos(dt * 59 + ph)
            sr += e * 1.5 * math.sin(dt * 51 + ph)
            hv += s * 1.5 * pulse(t, it, 0.006, 0.12)
    c["z"] *= 1 + sc.zoom_hit * hv
    if sc.zin and t - sc.t0 < 0.14:
        c["z"] *= 1 + sc.zin * (1 - ease_out((t - sc.t0) / 0.14, 2.5))
    if sc.zout and sc.t1 - t < 0.08:
        c["z"] *= 1 + sc.zout * ease_in((t - (sc.t1 - 0.08)) / 0.08, 2)
    c["x"] += sx * sc.shake_amp * U
    c["y"] += sy * sc.shake_amp * U
    c["rot"] += sr * sc.shake_amp * 0.04
    return c


def items(t):
    return scene_at(t).items(t)


# ---------------------------------------------------------------- 底部“成功进度”曲线（贯穿全片的 HUD）
KEYS = [(slot(0), 0.0), (slot(1, 8), 0.06), (slot(2), 0.08), (slot(2, 1), 0.03), (slot(2, 6), 0.10),
        (slot(2, 10), 0.14), (slot(3), 0.15), (slot(3, 4), 0.10), (slot(3, 8), 0.07), (slot(3, 12), 0.04),
        (slot(4), 0.03), (slot(4, 12), 0.18), (slot(5), 0.19), (slot(5, 1), 0.25), (slot(5, 4), 0.25),
        (slot(5, 5), 0.31), (slot(5, 8), 0.31), (slot(5, 9), 0.37), (slot(5, 12), 0.37), (slot(5, 13), 0.43),
        (slot(6), 0.44), (slot(7), 0.53), (slot(8), 0.62), (slot(9), 0.71), (slot(10), 0.82), (slot(10, 5), 1.0),
        (slot(11), 1.0)]
_KT = np.array([k[0] for k in KEYS])
_KV = np.array([k[1] for k in KEYS])


def progress(t):
    v = float(np.interp(t, _KT, _KV))
    if slot(3) < t < slot(4):
        v += 0.012 * math.sin(t * 37) + 0.008 * math.sin(t * 71)
    elif t > slot(5, 12):
        v += 0.006 * math.sin(t * 23) * (1 - v)
    return min(1.0, max(0.0, v))


def hud(t, ac):
    if t < T0 + 0.05:
        return
    a = smooth((t - T0 - 0.05) / 0.5) * (1 - smooth((t - slot(10, 6)) / 0.35))
    if a <= 0.01:
        return
    x0, x1 = 150 * U, W - 150 * U
    yb, yt = H - 56 * U, H - 176 * U
    span = slot(11) - T0
    n = max(2, int((t - T0) / span * 260))
    ts = np.linspace(T0, t, n)
    vals = [progress(x) for x in ts]
    pts = [(x0 + (x1 - x0) * (x - T0) / span, yb - (yb - yt) * v) for x, v in zip(ts, vals)]
    c = ac.c
    c.drawLine(x0, yb, x1, yb, ac.paint((255, 210, 150), 0.18 * a, width=1.2 * U))
    for k in range(11):
        xx = x0 + (x1 - x0) * k / 10
        c.drawLine(xx, yb, xx, yb + 7 * U, ac.paint((255, 210, 150), 0.25 * a, width=1.2 * U))
    red = slot(3) <= t < slot(4) + 0.3
    col = (255, 70, 60) if red else (255, 196, 100)
    path = skia.Path()
    path.moveTo(*pts[0])
    for p in pts[1:]:
        path.lineTo(*p)
    c.drawPath(path, ac.paint(col, 0.45 * a, width=9 * U, blur=7 * U))
    c.drawPath(path, ac.paint((255, 236, 200) if not red else (255, 170, 160), 0.85 * a, width=2.6 * U))
    hx, hy = pts[-1]
    c.drawCircle(hx, hy, 16 * U, ac.paint(col, 0.6 * a, stroke=False, blur=10 * U))
    c.drawCircle(hx, hy, 5 * U, ac.paint((255, 255, 240), a, stroke=False))
    f = E._font("mono", 28 * U)
    pct = "%d%%" % round(progress(t) * 100)
    c.drawString(pct, min(hx + 16 * U, x1 - 40 * U), hy - 16 * U, f, ac.paint(col, 0.95 * a, stroke=False))
    f2 = E._font("sans_m", 26 * U)
    c.drawString("成功进度", x0, yt - 12 * U, f2, ac.paint((255, 210, 150), 0.55 * a, stroke=False))
    if t >= slot(10, 5):
        b = pulse(t, slot(10, 5), 0.01, 0.35)
        c.drawCircle(hx, hy, (20 + 160 * (1 - b)) * U, ac.paint((255, 220, 150), 0.8 * b * a, width=3 * U))


def warm():
    """主进程预热所有精灵缓存（fork 后子进程共享）。"""
    for t in np.arange(0, END, 1 / 30):
        for it in items(float(t)):
            pass
    stars()
    mountains()
