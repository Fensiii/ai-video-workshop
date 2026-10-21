"""七美德流星 配乐 + 音效：全部 numpy 合成，无人声、无采样素材。

D 小调 i–VI–III–VII（Dm–B♭–F–C），90 BPM：pad + 琶音 + 低音 + 轻底鼓；
每个历史节点：上扬风声 → 钟声（每种美德一个音高），冲击类节点加低频轰鸣。
输出 ../work/audio.wav
"""
import math
import os

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, sosfilt

import virtues as V

SR = 48000
DUR = V.DURATION
N = int(DUR * SR) + SR
RNG = np.random.default_rng(2026)
L = np.zeros(N)
R = np.zeros(N)
SL = np.zeros(N)
SR_ = np.zeros(N)


def tt(d):
    return np.arange(int(d * SR)) / SR


def add(sig, t0, gain=1.0, pan=0.0, rev=0.3):
    i0 = int(t0 * SR)
    if i0 < 0:
        sig, i0 = sig[-i0:], 0
    n = min(len(sig), N - i0)
    if n <= 0:
        return
    a = (pan + 1) * math.pi / 4
    s = sig[:n] * gain
    L[i0:i0 + n] += s * math.cos(a)
    R[i0:i0 + n] += s * math.sin(a)
    SL[i0:i0 + n] += s * math.cos(a) * rev
    SR_[i0:i0 + n] += s * math.sin(a) * rev


def lp(x, fc, order=2):
    return sosfilt(butter(order, fc, btype='low', fs=SR, output='sos'), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, btype='high', fs=SR, output='sos'), x)


def bp(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], btype='band', fs=SR, output='sos'), x)


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


# ---------- 音乐强度曲线（按分镜给点） ----------
EV = V.EV_T
PLAGUE_T = EV[11]
KEYS_INT = [(0, 0.35), (EV[2], 0.55), (EV[5] - 0.5, 0.8), (EV[5] + 1, 1.0), (PLAGUE_T - 0.2, 1.0), (PLAGUE_T, 0.25),
            (PLAGUE_T + 5, 0.4), (EV[12], 0.95), (EV[16], 1.0), (V.T_FINALE, 1.0), (V.T_FINALE + 3.5, 0.55), (DUR, 0.0)]


def intensity(t):
    xs = [k[0] for k in KEYS_INT]
    ys = [k[1] for k in KEYS_INT]
    return np.interp(t, xs, ys)


BPM = 90
BEAT = 60 / BPM
BAR = BEAT * 4
CHORDS = [[50, 53, 57], [46, 50, 53], [53, 57, 60], [48, 52, 55]]   # Dm Bb F C
END_MUSIC = V.T_FINALE + 3.0


def chord_at(t):
    return CHORDS[int(t / (BAR * 2)) % 4]


def pad():
    seg = BAR * 2
    nseg = int(DUR / seg) + 1
    for i in range(nseg):
        t0 = i * seg
        ch = CHORDS[i % 4] if t0 < END_MUSIC else [50, 57, 62]
        d = seg + 1.5
        x = tt(d)
        env = np.minimum(1, x / 1.2) * np.minimum(1, (d - x) / 1.5)
        for m in ch + [ch[0] + 12]:
            for det, pan in [(-0.08, -0.5), (0.08, 0.5)]:
                f = mtof(m + det)
                ph = RNG.uniform(0, 6.28)
                s = (np.sin(2 * np.pi * f * x + ph) * 0.6 + 0.25 * np.sin(4 * np.pi * f * x) + 0.12 * np.sin(6 * np.pi * f * x))
                add(lp(s * env, 1800), t0, 0.035 * float(intensity(t0 + 1)) ** 0.5, pan, 0.5)


def pluck(f, d=0.9):
    x = tt(d)
    env = np.exp(-x * 5.5) * np.minimum(1, x / 0.004)
    s = np.sin(2 * np.pi * f * x) + 0.35 * np.sin(4 * np.pi * f * x) * np.exp(-x * 9)
    return s * env


def arp():
    step = BEAT / 2
    t = 6.0
    i = 0
    pattern = [0, 1, 2, 3, 2, 1, 2, 3]
    while t < END_MUSIC:
        ch = chord_at(t)
        notes = [ch[0] + 12, ch[1] + 12, ch[2] + 12, ch[0] + 24]
        m = notes[pattern[i % 8]]
        g = float(intensity(t))
        if g > 0.3:
            add(pluck(mtof(m)), t, 0.07 * g, 0.35 * math.sin(i * 0.7), 0.45)
        t += step
        i += 1


def bass():
    t = 0.0
    while t < END_MUSIC:
        ch = chord_at(t)
        g = float(intensity(t))
        x = tt(BEAT * 1.9)
        env = np.minimum(1, x / 0.01) * np.exp(-x * 1.2)
        f = mtof(ch[0] - 12)
        s = np.sin(2 * np.pi * f * x) + 0.2 * np.sin(4 * np.pi * f * x)
        add(s * env, t, 0.16 * g, 0, 0.05)
        t += BEAT * 2


def kick(gain):
    x = tt(0.45)
    f = 50 + 70 * np.exp(-x * 30)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-x * 9) * gain


def drums():
    t = EV[2]
    i = 0
    while t < END_MUSIC:
        g = float(intensity(t))
        if g > 0.7:
            add(kick(1), t, 0.30 * (g - 0.5), 0, 0.05)
            if i % 2 == 1:
                n = hp(RNG.normal(size=int(0.08 * SR)), 7000) * np.exp(-tt(0.08) * 50)
                add(n, t, 0.04 * g, 0.3, 0.2)
        t += BEAT
        i += 1


# ---------- 音效 ----------
VIRTUE_NOTE = {'pru': 74, 'jus': 77, 'for': 69, 'tem': 81, 'fid': 72, 'spe': 79, 'car': 76}


def bell(f, d=4.0):
    x = tt(d)
    s = np.zeros_like(x)
    for r, a, dec in [(1, 1, 1.2), (2.01, 0.5, 2.0), (3.0, 0.25, 3.0), (4.17, 0.18, 4.5), (5.43, 0.1, 6.0)]:
        s += a * np.sin(2 * np.pi * f * r * x) * np.exp(-x * dec)
    return s * np.minimum(1, x / 0.003)


def whoosh(d=1.2):
    x = tt(d)
    n = RNG.normal(size=len(x))
    env = (x / d) ** 2.2 * np.minimum(1, (d - x) / 0.06)
    out = np.zeros_like(x)
    blk = 2048
    for i in range(0, len(x), blk):
        u = i / len(x)
        lo, hi = 300 + 2500 * u, 900 + 6000 * u
        out[i:i + blk] = bp(n[i:i + blk + 0], lo, hi)[:len(out[i:i + blk])]
    return lp(out, 9000) * env


def boom(d=3.0):
    x = tt(d)
    f = 38 + 30 * np.exp(-x * 4)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 1.4)
    n = lp(RNG.normal(size=len(x)), 400) * np.exp(-x * 3) * 0.6
    return (s + n) * np.minimum(1, x / 0.005)


def shimmer(d=2.5):
    x = tt(d)
    s = np.zeros_like(x)
    for _ in range(14):
        f = mtof(RNG.choice([86, 88, 89, 91, 93, 96, 98]))
        t0 = RNG.uniform(0, d * 0.5)
        e = np.where(x > t0, np.exp(-(x - t0) * 3.5), 0)
        s += np.sin(2 * np.pi * f * x) * e * 0.15
    return s


def sfx():
    for i, e in enumerate(V.EVENTS_RAW):
        t = EV[i]
        add(whoosh(1.3), t - 1.25, 0.10, -0.4 + 0.08 * (i % 10), 0.3)
        changed = i == 0 or V.LEADERS[i - 1] != e[2]
        if changed:
            f = mtof(VIRTUE_NOTE[e[2]])
            add(bell(f), t, 0.10, 0.3, 0.6)
            add(bell(f * 2), t + 0.02, 0.03, -0.3, 0.6)
        if e[5] == 'burst':
            add(shimmer(3.0), t, 0.8, 0, 0.7)
            add(boom(2.5), t, 0.25, 0, 0.2)
        if e[5] in ('shake', 'plague'):
            add(boom(3.5), t, 0.55 if e[5] == 'plague' else 0.4, 0, 0.3)
        if e[5] == 'constellation':
            for j, k in enumerate(V.KEYS):
                add(bell(mtof(VIRTUE_NOTE[k] + 12), 2.5), t + 0.15 + j * 0.16, 0.045, -0.6 + j * 0.2, 0.7)
    # 结尾：长上扬 → 汇聚轰鸣 + 长和弦
    tf = V.T_FINALE
    add(whoosh(3.0), tf + 0.0, 0.14, 0, 0.5)
    add(boom(5.0), tf + 3.0, 0.5, 0, 0.5)
    add(shimmer(5.0), tf + 3.0, 1.0, 0, 0.8)
    for m in [62, 69, 74, 77, 81]:
        add(bell(mtof(m), 8.0), tf + 3.0, 0.06, 0, 0.8)


def reverb(x, d=3.2):
    t = tt(d)
    ir = RNG.normal(size=len(t)) * np.exp(-t * 2.2)
    ir = lp(ir, 6000)
    ir /= np.sqrt(np.sum(ir ** 2))
    return fftconvolve(x, ir)[:len(x)]


if __name__ == '__main__':
    pad()
    arp()
    bass()
    drums()
    sfx()
    outL = L + reverb(SL) * 0.9
    outR = R + reverb(SR_) * 0.9
    st = np.stack([outL, outR], 1)[:int(DUR * SR)]
    fade = np.minimum(1, (DUR - np.arange(len(st)) / SR) / 2.0)[:, None]
    st *= np.clip(fade, 0, 1)
    st /= np.max(np.abs(st)) + 1e-9
    st *= 0.89
    out = os.path.join(V.ROOT, 'work', 'audio_raw.wav')
    wavfile.write(out, SR, (st * 32767).astype(np.int16))
    print('wrote', out, len(st) / SR)
