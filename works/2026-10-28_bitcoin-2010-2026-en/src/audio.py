"""Synthesised sound-effects stem for the English edition (mixed under the score by mix.py).

Same design as the original, minus the drone bed (the score replaces it); every bell and ping is
snapped to the nearest chord tone of score.py at that moment so the effects sit in the harmony.
"""
import math
import os

import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.io import wavfile

import btc_common as B
import score as SC

SR = 48000
DUR = B.NFRAMES / B.FPS
N = int(DUR * SR) + SR
RNG = np.random.default_rng(1234)

L = np.zeros(N)
R = np.zeros(N)
SEND_L = np.zeros(N)  # reverb send
SEND_R = np.zeros(N)


def tt(d):
    return np.arange(int(d * SR)) / SR


def add(sig, t0, gain=1.0, pan=0.0, rev=0.25):
    """mix mono signal at time t0 with constant-power pan (-1..1)"""
    i0 = int(t0 * SR)
    if i0 >= N:
        return
    if i0 < 0:
        sig = sig[-i0:]
        i0 = 0
    n = min(len(sig), N - i0)
    s = sig[:n] * gain
    a = (pan + 1) * math.pi / 4
    gl, gr = math.cos(a), math.sin(a)
    L[i0:i0 + n] += s * gl
    R[i0:i0 + n] += s * gr
    if rev > 0:
        SEND_L[i0:i0 + n] += s * gl * rev
        SEND_R[i0:i0 + n] += s * gr * rev


def add_st(sl, sr_, t0, gain=1.0, rev=0.2):
    i0 = int(t0 * SR)
    n = min(len(sl), N - i0)
    L[i0:i0 + n] += sl[:n] * gain
    R[i0:i0 + n] += sr_[:n] * gain
    SEND_L[i0:i0 + n] += sl[:n] * gain * rev
    SEND_R[i0:i0 + n] += sr_[:n] * gain * rev


def bp(x, lo, hi, order=2):
    sos = butter(order, [lo, hi], btype='band', fs=SR, output='sos')
    return sosfilt(sos, x)


def lp(x, fc, order=2):
    sos = butter(order, fc, btype='low', fs=SR, output='sos')
    return sosfilt(sos, x)


def hp(x, fc, order=2):
    sos = butter(order, fc, btype='high', fs=SR, output='sos')
    return sosfilt(sos, x)


def sweep_bp(x, f0, f1, q=1.2, curve=1.0):
    """band-pass with centre sweeping f0 -> f1 (block processed)"""
    out = np.zeros_like(x)
    blk = 256
    nb = (len(x) + blk - 1) // blk
    zi = None
    for b in range(nb):
        u = (b / max(nb - 1, 1)) ** curve
        fc = f0 * (f1 / f0) ** u
        lo, hi = fc / (1 + 0.5 / q), min(fc * (1 + 0.5 / q), SR * 0.45)
        sos = butter(2, [lo, hi], btype='band', fs=SR, output='sos')
        if zi is None:
            zi = np.zeros((sos.shape[0], 2))
        seg = x[b * blk:(b + 1) * blk]
        y, zi = sosfilt(sos, seg, zi=zi)
        out[b * blk:b * blk + len(seg)] = y
    return out



def ct(t, f):
    """nearest chord tone (Hz) to f in the score's chord at time t"""
    m = 69 + 12 * math.log2(f / 440.0)
    _, pcs, _ = SC.parse_chord(SC.chord_at(t + 0.01))
    best = min((k for k in range(int(m) - 6, int(m) + 7) if k % 12 in pcs), key=lambda k: abs(k - m))
    return 440.0 * 2 ** ((best - 69) / 12)


def env_ad(n, att, dec, shape=1.0):
    t = np.arange(n) / SR
    e = np.where(t < att, (t / max(att, 1e-4)) ** shape, np.exp(-(t - att) / max(dec, 1e-4)))
    return e


def norm(x):
    m = np.max(np.abs(x)) + 1e-9
    return x / m

# ----------------------------------------------------------------------------
# sound designs
# ----------------------------------------------------------------------------

def whoosh(dur=0.7, f0=300, f1=4000, peak=0.6, q=0.9):
    n = int(dur * SR)
    x = RNG.standard_normal(n)
    y = sweep_bp(x, f0, f1, q=q)
    t = np.arange(n) / n
    e = np.where(t < peak, (t / peak) ** 2, ((1 - t) / (1 - peak)) ** 1.6)
    return norm(y * e)


def boom(dur=2.2, f0=95, f1=38, tail=0.7):
    t = tt(dur)
    f = f1 + (f0 - f1) * np.exp(-t / 0.12)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t / tail)
    click = lp(RNG.standard_normal(len(t)), 1800) * np.exp(-t / 0.02) * 0.6
    rum = lp(RNG.standard_normal(len(t)), 160, 4) * np.exp(-t / (tail * 1.4)) * 1.8
    s = body + click + rum
    s *= np.minimum(1, t / 0.004)
    return norm(s)


def bell(freq, dur=2.5, decay=0.9, partials=((1, 1.0), (2.0, 0.45), (3.01, 0.22), (4.2, 0.12), (5.4, 0.06))):
    t = tt(dur)
    s = np.zeros_like(t)
    for k, (m, a) in enumerate(partials):
        s += a * np.sin(2 * np.pi * freq * m * t + k) * np.exp(-t / (decay / (1 + 0.6 * k)))
    s *= np.minimum(1, t / 0.003)
    return norm(s)


def sparkle(dur=1.4, n=18, fmin=3000, fmax=9000, seed=0):
    rng = np.random.default_rng(seed)
    out = np.zeros(int(dur * SR))
    for _ in range(n):
        t0 = rng.uniform(0, dur * 0.7) ** 1.4 / (dur * 0.7) ** 0.4
        f = rng.uniform(fmin, fmax)
        d = rng.uniform(0.05, 0.25)
        tl = tt(d)
        tone = np.sin(2 * np.pi * f * tl) * np.exp(-tl / (d / 3)) * rng.uniform(0.3, 1.0)
        i0 = int(t0 * SR)
        out[i0:i0 + len(tone)] += tone[:len(out) - i0]
    return norm(out)


def click(freq=2500, dur=0.03, noise=0.4):
    t = tt(dur)
    s = np.sin(2 * np.pi * freq * t) * np.exp(-t / (dur / 4))
    s += noise * hp(RNG.standard_normal(len(t)), 3000) * np.exp(-t / (dur / 6))
    return norm(s)


def ping(f1=1320, f2=1980, dur=0.9):
    a = bell(f1, dur, 0.35, ((1, 1), (2.76, 0.2)))
    b = bell(f2, dur, 0.30, ((1, 1), (2.76, 0.2)))
    s = a.copy()
    off = int(0.07 * SR)
    s[off:] += 0.8 * b[:len(s) - off]
    return norm(s)


def riser(dur=1.2, f0=200, f1=2400):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = RNG.standard_normal(n)
    y = sweep_bp(x, f0, f1, q=1.5, curve=1.6)
    f = f0 * 0.5 * (f1 / f0) ** ((t / dur) ** 1.5)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.25
    e = (t / dur) ** 2.2
    return norm((y + tone) * e)


def glitch(dur=0.5, base=110):
    t = tt(dur)
    sq = np.sign(np.sin(2 * np.pi * base * t)) * 0.5 + np.sign(np.sin(2 * np.pi * base * 4.02 * t)) * 0.25
    gate = (np.sin(2 * np.pi * 18 * t) > -0.2).astype(float)
    s = lp(sq * gate, 3000) * np.exp(-t / 0.18)
    s = np.round(s * 10) / 10  # bit-crush
    return norm(lp(s, 5000))


def ui_swoosh(dur=0.35):
    return whoosh(dur, 900, 6000, peak=0.35, q=1.4)


def rumble(dur=3.0):
    t = tt(dur)
    x = lp(RNG.standard_normal(len(t)), 90, 4)
    e = np.minimum(1, t / 0.3) * np.exp(-t / (dur * 0.45))
    return norm(x * e)

def main():
    # ---------------- intro
    add(bell(ct(0.0, 523.25), 3.5, 1.3), 0.0, 0.16, -0.1, 0.6)
    add(bell(ct(0.04, 783.99), 3.5, 1.2), 0.04, 0.12, 0.15, 0.6)
    add(bell(ct(0.09, 1046.5), 3.0, 1.0), 0.09, 0.08, 0.3, 0.6)
    add(whoosh(1.4, 200, 2500, peak=0.25), 0.0, 0.10, 0.0, 0.5)
    add(sparkle(1.6, 14, seed=1), 0.05, 0.07, 0.2, 0.5)
    add(whoosh(0.9, 600, 5000, peak=0.5), 0.2, 0.06, 0.0, 0.4)
    for tg in (0.75, 1.85):
        add(bell(ct(tg, 4186), 0.8, 0.25, ((1, 1), (2.4, 0.3))), tg, 0.05, 0.45, 0.6)
    add(whoosh(1.0, 3000, 300, peak=0.3), 2.25, 0.10, 0.0, 0.4)
    add(bell(ct(2.45, 2637), 1.5, 0.5, ((1, 1), (2.0, 0.3), (3.0, 0.1))), 2.45, 0.08, -0.7, 0.6)
    add(riser(1.25, 250, 3200), 3.3, 0.12, 0.0, 0.3)
    add(sparkle(1.4, 26, 4000, 10000, seed=2), 3.4, 0.08, 0.3, 0.5)
    add(bell(ct(4.55, 1567.98), 2.0, 0.8), 4.55, 0.10, 0.6, 0.6)
    add(whoosh(0.7, 3500, 250, peak=0.25), 5.0, 0.10, 0.2, 0.4)
    add(whoosh(0.9, 400, 3000, peak=0.6), 5.5, 0.08, -0.4, 0.4)
    add(bell(ct(6.35, 659.25), 2.8, 1.1), 6.35, 0.10, 0.2, 0.7)
    add(bell(ct(6.37, 987.77), 2.4, 0.9), 6.37, 0.06, 0.25, 0.7)
    for k, f in enumerate((1760, 2093, 2637, 3136)):
        add(click(f, 0.04, 0.2), 7.3 + 0.07 * k, 0.05, -0.6 + 0.4 * k, 0.2)
    add(riser(0.9, 150, 1800), 7.6, 0.08, 0.0, 0.3)

    # ---------------- month / year ticks, snapped to the score's 16th-note grid so they lock with the pulse
    prev_m = None
    prev_y = None
    used = set()
    sixteenth = SC.BEAT / 4
    for fi in range(B.NFRAMES):
        t = fi / B.FPS
        if t < 8.5 or t > B.T_END + 0.05:
            continue
        d = B.date_of(B.HEAD[fi])
        slot = round((t - SC.T0) / sixteenth)
        tq = SC.T0 + slot * sixteenth
        if prev_y is not None and d.year != prev_y:
            add(click(1500, 0.05, 0.6), tq, 0.06, -0.55, 0.15)
            add(click(750, 0.06, 0.2), tq, 0.04, -0.55, 0.15)
            used.add(slot)
        elif prev_m is not None and d.month != prev_m and slot not in used:
            add(click(3200 + 300 * (d.month % 3), 0.02, 0.5), tq, 0.013, 0.55, 0.08)
            used.add(slot)
        prev_m, prev_y = d.month, d.year

    # ---------------- events
    for i, ev in enumerate(B.EVENTS):
        t_in = ev.t - 0.6
        add(ui_swoosh(0.4), t_in, 0.05, 0.6, 0.2)
        add(click(2200, 0.03, 0.3), t_in + 0.12, 0.04, 0.6, 0.2)
        te = ev.t
        if ev.cat in ('开端', '顶点', '新高'):
            add(boom(2.4, 90, 40, 0.6), te, 0.30, 0.2, 0.3)
            for f, g in ((659.25, 0.12), (987.77, 0.09), (1318.5, 0.07), (1975.5, 0.05)):
                add(bell(ct(te, f), 3.2, 1.2), te, g, 0.3, 0.7)
            add(sparkle(1.8, 30, 3500, 10000, seed=100 + i), te, 0.10, 0.4, 0.6)
        elif ev.cat in ('暴涨', '大选'):
            add(riser(0.6, 300, 2500), te - 0.6, 0.08, 0.2, 0.2)
            add(boom(1.6, 120, 55, 0.35), te, 0.24, 0.2, 0.3)
            add(sparkle(1.4, 22, 3000, 8000, seed=200 + i), te, 0.08, 0.3, 0.5)
        elif ev.cat in ('危机', '暴跌'):
            add(whoosh(0.55, 4000, 400, peak=0.85), te - 0.5, 0.07, 0.2, 0.2)
            add(boom(3.2, 75, 30, 1.0), te, 0.40, 0.15, 0.35)
            add(rumble(3.5), te, 0.20, 0.0, 0.2)
            add(bell(ct(te, 196.0), 3.0, 1.2, ((1, 1), (2.01, 0.3), (2.98, 0.15))), te, 0.06, 0.2, 0.6)
        elif ev.cat == '谷底':
            add(boom(2.6, 70, 32, 0.8), te, 0.30, 0.1, 0.35)
            add(bell(ct(te, 261.63), 3.2, 1.4, ((1, 1), (2.0, 0.25))), te, 0.07, 0.2, 0.7)
        elif ev.cat in ('减半', '科技'):
            add(glitch(0.55, 110), te, 0.07, 0.3, 0.3)
            add(ping(ct(te, 880), ct(te, 1320), 1.2), te + 0.02, 0.07, 0.3, 0.6)
            add(boom(1.4, 140, 60, 0.3), te, 0.12, 0.2, 0.2)
        else:  # blue: listings, entries, policy
            add(ping(ct(te, 1174.66), ct(te, 1760), 1.2), te, 0.09, 0.35, 0.6)
            add(boom(1.2, 130, 60, 0.25), te, 0.12, 0.2, 0.2)
            add(sparkle(0.9, 8, 3000, 7000, seed=300 + i), te, 0.05, 0.4, 0.5)

    # ---------------- camera push-in, lock-on marks, measurement arrows
    for i, ev in enumerate(B.EVENTS):
        if ev.zoom > 0:
            add(whoosh(0.85, 180, 1400, peak=0.7, q=1.1), ev.t - 0.6, 0.05 + 0.12 * ev.zoom, 0.25, 0.3)
        if ev.cat != '开端':
            add(click(2900, 0.025, 0.2), ev.t + 0.03, 0.035, 0.3, 0.15)
            add(click(3900, 0.02, 0.2), ev.t + 0.11, 0.03, 0.35, 0.15)
        if ev.shake >= 16:
            add(rumble(2.5), ev.t, 0.12, -0.2, 0.2)
        if ev.bracket:
            tb = max(ev.t, float(B.time_of_day(ev.bracket[1])))
            add(whoosh(0.4, 2500, 600, peak=0.3, q=1.6), tb, 0.035, 0.35, 0.2)
            add(click(1600, 0.04, 0.3), tb + 0.42, 0.04, 0.35, 0.2)

    # ---------------- milestones ("首次突破")
    for k, (lv, fd, tm) in enumerate(B.MILESTONE_T):
        add(riser(0.9, 300, 4000), tm - 0.9, 0.09, -0.2, 0.2)
        add(whoosh(0.85, 180, 1400, peak=0.7, q=1.1), tm - 0.6, 0.08, -0.2, 0.3)
        add(boom(2.0, 110, 50, 0.45), tm, 0.22, -0.1, 0.3)
        for f, g in ((783.99, 0.10), (1174.66, 0.08), (1567.98, 0.07), (2349.3, 0.05)):
            add(bell(ct(tm, f), 3.0, 1.1), tm, g, -0.2, 0.7)
        add(sparkle(2.0, 36, 4000, 11000, seed=500 + k), tm, 0.11, -0.2, 0.6)

    # ---------------- era titles
    for k, (te, label, title) in enumerate(B.ERA_T):
        add(whoosh(1.1, 150, 1800, peak=0.55), te - 0.5, 0.11, -0.6, 0.4)
        add(boom(2.5, 60, 30, 0.9), te + 0.05, 0.16, -0.5, 0.4)

    # ---------------- ending
    add(bell(ct(179.0, 392.0), 3.0, 1.2, ((1, 1), (2.0, 0.25))), 179.0, 0.06, 0.0, 0.7)
    for tq in (180.0, 181.0):
        add(boom(3.0, 70, 30, 1.1), tq, 0.32, 0.4, 0.5)
        add(whoosh(0.6, 2500, 300, peak=0.2), tq - 0.05, 0.06, 0.4, 0.4)
    add(whoosh(0.9, 3500, 200, peak=0.2), 182.7, 0.09, 0.0, 0.4)
    add(riser(5.0, 120, 2600), 183.0, 0.16, 0.0, 0.4)
    add(whoosh(5.2, 120, 1200, peak=0.85), 183.0, 0.10, 0.0, 0.4)
    for k in range(11):
        add(click(2600 + 200 * (k % 3), 0.03, 0.3), 187.4 + 0.09 * k, 0.03, -0.5 + 0.1 * k, 0.4)
    add(click(1800, 0.05, 0.3), 188.4, 0.05, -0.6, 0.4)
    add(click(1400, 0.05, 0.3), 188.9, 0.05, -0.6, 0.4)
    add(boom(4.0, 85, 30, 1.4), 189.5, 0.42, -0.3, 0.5)
    for f, g in ((523.25, 0.12), (783.99, 0.10), (1046.5, 0.08), (1567.98, 0.06), (2093.0, 0.04)):
        add(bell(ct(189.5, f), 4.5, 1.8), 189.5, g, -0.3, 0.8)
    add(sparkle(2.5, 40, 4000, 11000, seed=900), 189.5, 0.10, -0.3, 0.7)
    add(boom(4.0, 65, 28, 1.6), 190.6, 0.30, 0.3, 0.6)
    for f, g in ((392.0, 0.10), (587.33, 0.08), (783.99, 0.07), (1174.66, 0.05)):
        add(bell(ct(190.6, f), 4.0, 2.0), 190.6, g, 0.3, 0.8)
    add(whoosh(1.5, 200, 2000, peak=0.4), 191.5, 0.04, 0.0, 0.5)

    # ---------------- reverb; no drone bed (the score takes its place); stem left unlimited for mix.py
    ir_n = int(2.8 * SR)
    ti = np.arange(ir_n) / SR
    irl = RNG.standard_normal(ir_n) * np.exp(-ti / 0.65)
    irr = RNG.standard_normal(ir_n) * np.exp(-ti / 0.65)
    irl = lp(irl, 6000)
    irr = lp(irr, 6000)
    irl[:int(0.012 * SR)] = 0
    irr[:int(0.017 * SR)] = 0
    irl /= np.sqrt(np.sum(irl ** 2))
    irr /= np.sqrt(np.sum(irr ** 2))
    wl = fftconvolve(SEND_L, irl)[:N] * 0.9
    wr = fftconvolve(SEND_R, irr)[:N] * 0.9
    outl = hp(L + wl, 28)
    outr = hp(R + wr, 28)
    n_out = int(DUR * SR)
    st = np.stack([outl[:n_out], outr[:n_out]], axis=1)
    import pyloudnorm as pyln
    gain = 10 ** ((-20.0 - pyln.Meter(SR).integrated_loudness(st)) / 20)   # stem reference: -20 LUFS
    st *= gain
    path = os.path.join(B.ROOT, 'out', 'sfx.wav')
    wavfile.write(path, SR, st.astype(np.float32))
    print('wrote', path, f'peak {20 * math.log10(np.abs(st).max()):.1f} dBFS at -20 LUFS')


if __name__ == '__main__':
    main()
