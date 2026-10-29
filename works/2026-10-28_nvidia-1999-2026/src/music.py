"""Original score for the NVIDIA video, synthesised in numpy (no samples, so no Content ID claims).

120 BPM with the first downbeat at 0.5 s: every event time in nvda_common (all on a 0.5 s grid)
lands on a beat. D minor; the chord plan follows the eras, the energy follows the story and the
market mood (crashes close the filters and drop the drums), black-swan days cut the band for a bar.

    python3 music.py   ->  ../out/music.wav
"""
import math
import os

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, sosfilt

import nvda_common as B

SR = 48000
DUR = B.NFRAMES / B.FPS
N = int(DUR * SR) + SR
BEAT = 0.5
BAR = 2.0
T0 = 0.5
NBARS = int(math.ceil((DUR - T0) / BAR))
RNG = np.random.default_rng(2026)

STEMS = ('pad', 'bass', 'arp', 'drums', 'lead', 'keys', 'fx')
OUT = {k: np.zeros((2, N), np.float32) for k in STEMS}
SEND = np.zeros((2, N), np.float32)


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def bar_t(i):
    return T0 + i * BAR


def put(stem, sig, t0, gain=1.0, pan=0.0, send=0.0):
    """mix a mono (n,) or stereo (2, n) signal into a stem at time t0"""
    i0 = int(round(t0 * SR))
    if i0 >= N or gain == 0:
        return
    if sig.ndim == 1:
        a = (pan + 1) * math.pi / 4
        sig = np.stack([sig * math.cos(a), sig * math.sin(a)])
    if i0 < 0:
        sig = sig[:, -i0:]
        i0 = 0
    n = min(sig.shape[1], N - i0)
    s = (sig[:, :n] * gain).astype(np.float32)
    OUT[stem][:, i0:i0 + n] += s
    if send:
        SEND[:, i0:i0 + n] += s * send


def tt(d):
    return np.arange(int(d * SR)) / SR


def saw(f, t, phase=0.0):
    """PolyBLEP sawtooth; f may vary per sample"""
    f = np.broadcast_to(np.asarray(f, np.float64), t.shape)
    ph = (np.cumsum(f) / SR + phase) % 1.0 if f.ndim and f.size > 1 and np.ptp(f) > 0 else (f * t + phase) % 1.0
    dt = f / SR
    y = 2.0 * ph - 1.0
    m1 = ph < dt
    x = ph[m1] / dt[m1]
    y[m1] -= x + x - x * x - 1.0
    m2 = ph > 1.0 - dt
    x = (ph[m2] - 1.0) / dt[m2]
    y[m2] -= x * x + x + x + 1.0
    return y


def lp(x, fc, order=2):
    return sosfilt(butter(order, min(fc, SR * 0.45), btype='low', fs=SR, output='sos'), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, btype='high', fs=SR, output='sos'), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], btype='band', fs=SR, output='sos'), x)


def adsr(n, a, d, s, r, hold=None):
    """attack/decay/sustain/release envelope over n samples (release starts at hold)"""
    t = np.arange(n) / SR
    hold = n / SR - r if hold is None else hold
    e = np.where(t < a, t / max(a, 1e-4), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    rel = np.clip((t - hold) / max(r, 1e-4), 0, 1)
    return e * (1 - rel)


# ----------------------------------------------------------------------------
# harmony and form
# ----------------------------------------------------------------------------
CHORDS = {  # bass root, pad voicing, arpeggio tones
    'Dm': (38, [50, 57, 62, 65, 69], [62, 65, 69, 74, 77]),
    'Bb': (34, [46, 53, 58, 62, 65], [58, 62, 65, 70, 74]),
    'F': (41, [48, 53, 57, 60, 65], [60, 65, 69, 72, 77]),
    'C': (36, [48, 55, 60, 64, 67], [60, 64, 67, 72, 76]),
    'Gm': (31, [43, 50, 55, 58, 62], [62, 67, 70, 74, 79]),
    'A': (33, [45, 52, 57, 61, 64], [61, 64, 69, 73, 76]),
}
P_MAIN = ['Dm', 'Bb', 'F', 'C']
P_DARK = ['Dm', 'Bb', 'Gm', 'A']
P_LIFT = ['F', 'C', 'Dm', 'Bb']
P_HOPE = ['Bb', 'F', 'C', 'Dm']
PLAN = [  # (first bar, progression, bars) -- bar i starts at 0.5 + 2 i seconds
    (0, ['Dm'], 4),               # intro
    (4, P_MAIN, 10),              # 1999-2001
    (14, P_DARK, 4),              # 2002 bust
    (18, P_LIFT, 7),              # 2003-2007
    (25, P_DARK, 4),              # 2008 crash
    (29, P_MAIN, 2),
    (31, P_HOPE, 4),              # 2012-2015 deep-learning spark
    (35, P_MAIN, 8),              # 2016-2018
    (43, P_MAIN, 10),             # 2019-2021
    (53, P_DARK, 5),              # 2022 reset
    (58, P_LIFT, 17),             # 2023-2024 AI gold rush
    (75, P_MAIN, 23),             # 2025-2026
    (98, ['Dm', 'Dm', 'Bb', 'Bb', 'C'], 5),   # questions, pull-back
    (103, ['F'], 4),              # final reveal
]
BAR_CHORD = ['Dm'] * (NBARS + 1)
for b0, prog, nb in PLAN:
    for k in range(nb):
        if b0 + k <= NBARS:
            BAR_CHORD[b0 + k] = prog[k % len(prog)]
SECTION_BARS = [4, 18, 31, 35, 43, 58, 75, 103]
RISE_INTO = [4, 35, 58, 75]           # 2-bar risers into these bars

ENERGY = [(0, .22), (8.4, .3), (8.5, .48), (26, .64), (28.5, .42), (34.5, .3), (36.5, .46), (48, .64),
          (50.5, .42), (54.5, .3), (58.5, .4), (62.5, .42), (70.4, .5), (70.5, .72), (80.5, .82), (86.5, .74),
          (104.5, .9), (106.5, .42), (116.4, .55), (116.5, .92), (139.5, 1.0), (150.4, .96), (150.5, .9),
          (171.0, 1.0), (196.4, .88), (196.5, .32), (201.5, .32), (206.4, .62), (206.5, .95), (210.5, .55),
          (DUR, .3)]
_fr = np.arange(B.NFRAMES) / B.FPS
_cam = B.get_camera()


def energy(t):
    e = float(np.interp(t, *zip(*ENERGY)))
    if B.T_START <= t <= B.T_END:
        cold = float(np.interp(t, _fr, _cam['cold']))
        warm = float(np.interp(t, _fr, _cam['warm']))
        e = e * (1 - 0.4 * cold) + 0.05 * warm
    return min(max(e, 0.0), 1.0)


DROPS = [ev.t for ev in B.EVENTS if ev.shake >= 16]   # black-swan days: the band stops for a bar


def dropped(t):
    return any(d <= t < d + 1.5 for d in DROPS)


def chord_at(t):
    return BAR_CHORD[int(min(max((t - T0) // BAR, 0), NBARS))]


# ----------------------------------------------------------------------------
# instruments
# ----------------------------------------------------------------------------

def render_pad():
    for i in range(-1, NBARS):
        t0 = max(bar_t(i), 0.0)
        name = BAR_CHORD[max(i, 0)]
        _, notes, _ = CHORDS[name]
        e = energy(t0 + 1.0)
        cut = 450 + 3800 * e
        if any(t0 - 0.2 <= d < t0 + BAR for d in DROPS):
            cut *= 0.45
        dur = BAR + 0.7 if i >= 0 else T0 + 0.7
        t = tt(dur)
        sl = np.zeros_like(t)
        sr = np.zeros_like(t)
        for k, m in enumerate(notes):
            f = mtof(m)
            sl += saw(f * 2 ** (-7 / 1200), t, RNG.random()) + 0.6 * saw(f * 2 ** (5 / 1200), t, RNG.random())
            sr += saw(f * 2 ** (7 / 1200), t, RNG.random()) + 0.6 * saw(f * 2 ** (-4 / 1200), t, RNG.random())
            sub = np.sin(2 * np.pi * f / 2 * t) if k == 0 else 0
            sl += 0.25 * sub
            sr += 0.25 * sub
        att = 1.2 if i < 4 else 0.35
        env = adsr(len(t), att, 1.0, 1.0, 0.7)
        sig = np.stack([lp(sl, cut), lp(sr, cut)]) * env / len(notes)
        put('pad', sig, t0, 0.55, send=0.45)
        # high strings on big sections
        if e > 0.66 and i >= 0:
            g = (e - 0.66) / 0.34
            ts = tt(BAR + 0.9)
            vib = 1 + 0.0035 * np.sin(2 * np.pi * 5.2 * ts) * np.clip(ts / 0.6, 0, 1)
            st = np.zeros_like(ts)
            for m in notes[-2:]:
                st += saw(mtof(m + 12) * vib, ts, RNG.random())
            st = lp(st, 3600) * adsr(len(ts), 0.7, 1.0, 1.0, 0.9)
            put('pad', st, t0, 0.10 * g, pan=0.25 * (-1) ** i, send=0.6)


def render_bass():
    for i in range(NBARS):
        t0 = bar_t(i)
        root, _, _ = CHORDS[BAR_CHORD[i]]
        e = energy(t0 + 0.5)
        f = mtof(root)
        cut = 240 + 900 * e
        if e < 0.5:
            steps = [(0.0, BAR)]
        elif e < 0.78:
            steps = [(k * 0.25, 0.25) for k in range(8)]
        else:
            steps = [(k * 0.125, 0.125) for k in range(16)]
        for off, ln in steps:
            ts = t0 + off
            if dropped(ts) or ts >= DUR:
                continue
            n = int((ln + 0.08) * SR)
            t = np.arange(n) / SR
            body = 0.8 * np.sin(2 * np.pi * f * t) + 0.45 * lp(saw(2 * f, t), cut)
            body = np.tanh(1.6 * body)
            if ln >= BAR:
                env = adsr(n, 0.04, 0.8, 0.75, 0.25)
                vel = 0.9
            else:
                env = adsr(n, 0.004, ln * 0.9, 0.35, 0.06, hold=ln)
                beat_pos = (off % BEAT) / BEAT
                vel = 0.55 if beat_pos < 0.01 else 1.0      # leave room for the kick
            put('bass', body * env, ts, 0.30 * vel)


_PLUCK = {}


def pluck(m, dec):
    key = (m, round(dec, 2))
    s = _PLUCK.get(key)
    if s is None:
        t = tt(dec * 5 + 0.05)
        f = mtof(m)
        s = (np.sin(2 * np.pi * f * t) + 0.55 * np.sin(4 * np.pi * f * t) * np.exp(-t / 0.08)
             + 0.35 * np.sin(6 * np.pi * f * t) * np.exp(-t / 0.05) + 0.2 * np.sin(8 * np.pi * f * t) * np.exp(-t / 0.03)
             + 0.1 * np.sin(12 * np.pi * f * t) * np.exp(-t / 0.015))
        s *= np.minimum(t / 0.002, 1) * np.exp(-t / dec)
        _PLUCK[key] = s
    return s


ARP_PAT = [0, 2, 1, 3, 2, 4, 3, 1]


def render_arp():
    j = 0
    for i in range(4, NBARS):
        t0 = bar_t(i)
        _, _, tones = CHORDS[BAR_CHORD[i]]
        e = energy(t0 + 0.5)
        if e < 0.40:
            continue
        sub = 0.125 if e >= 0.6 else 0.25
        for k in range(int(BAR / sub)):
            ts = t0 + k * sub
            if dropped(ts) or ts >= DUR - 1:
                continue
            m = tones[ARP_PAT[j % 8]]
            j += 1
            dec = 0.09 + 0.12 * e
            vel = 1.0 if (k * sub) % BEAT < 1e-6 else 0.72
            sig = pluck(m, dec)
            pan = 0.35 if j % 2 else -0.35
            g = 0.19 * vel * (0.6 + 0.4 * e)
            put('arp', sig, ts, g, pan=pan, send=0.25)
            put('arp', sig, ts + 0.375, g * 0.32, pan=-pan, send=0.3)     # dotted-8th echo
            put('arp', sig, ts + 0.75, g * 0.12, pan=pan, send=0.3)


MOTIF = {  # (slot in 8ths, midi, length in 8ths)
    'F': [(0, 69, 2), (2, 72, 2), (4, 77, 3), (7, 76, 1)],
    'C': [(0, 76, 4), (4, 72, 2), (6, 67, 2)],
    'Dm': [(0, 74, 2), (2, 77, 2), (4, 81, 3), (7, 79, 1)],
    'Bb': [(0, 77, 6), (6, 74, 2)],
}
LEAD_BARS = list(range(62, 74)) + list(range(79, 85)) + list(range(91, 97))


def render_lead():
    for i in LEAD_BARS:
        t0 = bar_t(i)
        name = BAR_CHORD[i]
        for slot, m, ln in MOTIF.get(name, []):
            ts = t0 + slot * 0.25
            if dropped(ts):
                continue
            d = ln * 0.25
            t = tt(d + 0.25)
            vib = 1 + 0.004 * np.sin(2 * np.pi * 5.0 * t) * np.clip((t - 0.2) / 0.3, 0, 1)
            f = mtof(m) * vib
            sig = 0.6 * saw(f, t) + 0.4 * saw(f * 1.004, t, 0.3) + 0.3 * np.sin(2 * np.pi * mtof(m - 12) * t)
            sig = lp(sig, 2300) * adsr(len(t), 0.015, 0.4, 0.8, 0.22, hold=d)
            put('lead', sig, ts, 0.12, pan=0.1, send=0.45)
            put('lead', sig, ts + 0.375, 0.04, pan=-0.4, send=0.5)


def piano(m, dur, vel=1.0):
    t = tt(dur)
    f = mtof(m)
    s = np.zeros_like(t)
    for n in range(1, 9):
        fn = n * f * math.sqrt(1 + 0.0004 * n * n)
        if fn > SR * 0.45:
            break
        s += np.sin(2 * np.pi * fn * t + n) / n ** 1.25 * np.exp(-t / (1.8 / (1 + 0.45 * n)))
    s += 0.02 * hp(RNG.standard_normal(len(t)), 2000) * np.exp(-t / 0.01)
    return s * np.minimum(t / 0.003, 1) * vel


def render_keys():
    # 2012-2015: gentle broken chords
    for i in range(31, 35):
        _, _, tones = CHORDS[BAR_CHORD[i]]
        for k, idx in enumerate([0, 2, 4, 2]):
            put('keys', piano(tones[idx], 2.5, 0.8), bar_t(i) + k * BEAT, 0.16, pan=0.2 * (k - 1.5), send=0.5)
    # ending: the lead motif, slowly, on piano
    seq = [(196.5, 74), (197.5, 77), (198.5, 81), (199.5, 79), (200.5, 77), (201.5, 74),
           (202.5, 70), (203.5, 74), (204.5, 76), (205.5, 72)]
    for k, (t0, m) in enumerate(seq):
        put('keys', piano(m, 3.0, 0.9), t0, 0.22, pan=0.15 * (-1) ** k, send=0.55)
        put('keys', piano(m - 12, 3.0, 0.5), t0, 0.12, pan=-0.1, send=0.55)
    for k, m in enumerate([77, 81, 84, 89]):
        put('keys', piano(m, 4.0, 0.8), 208.0 + 0.5 * k, 0.16, pan=0.2 * (k - 1.5), send=0.6)


# ---- drums
def _kick():
    t = tt(0.45)
    f = 46 + 110 * np.exp(-t / 0.035)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.28)
    s += 0.25 * hp(RNG.standard_normal(len(t)), 3000) * np.exp(-t / 0.004)
    return np.tanh(1.4 * s)


def _snare():
    t = tt(0.4)
    n = bp(RNG.standard_normal(len(t)), 1200, 6500) * np.exp(-t / 0.13)
    tone = np.sin(2 * np.pi * 186 * t) * np.exp(-t / 0.07)
    clap = np.zeros_like(t)
    for d in (0.0, 0.011, 0.022):
        i = int(d * SR)
        clap[i:] += bp(RNG.standard_normal(len(t) - i), 900, 4000) * np.exp(-np.arange(len(t) - i) / SR / 0.012)
    return 0.7 * n + 0.45 * tone + 0.5 * clap


def _hat(dec):
    t = tt(dec * 6)
    return hp(RNG.standard_normal(len(t)), 7000, 4) * np.exp(-t / dec)


def _crash():
    t = tt(2.6)
    s = hp(RNG.standard_normal(len(t)), 3500, 2) * np.exp(-t / 0.9)
    for f in (3170, 4410, 5630, 7210):
        s += 0.08 * np.sin(2 * np.pi * f * t) * np.exp(-t / 0.7)
    return s


KICK, SNARE, HAT_C, HAT_O, CRASH = _kick(), _snare(), _hat(0.028), _hat(0.16), _crash()
KICK_TIMES = []


def render_drums():
    for i in range(4, NBARS):
        t0 = bar_t(i)
        for b in range(4):
            tb = t0 + b * BEAT
            if tb >= DUR - 0.5:
                continue
            e = energy(tb)
            if dropped(tb):
                continue
            if e >= 0.75 or (e >= 0.55 and b in (0, 2)):
                put('drums', KICK, tb, 0.85)
                KICK_TIMES.append(tb)
            if e >= 0.68 and b in (1, 3):
                put('drums', SNARE, tb, 0.44, pan=0.05, send=0.2)
            if e >= 0.5:
                sub = 4 if e >= 0.82 else 2
                for k in range(sub):
                    th = tb + k * BEAT / sub
                    acc = 1.0 if k * 2 // sub == 1 else 0.55
                    if e >= 0.88 and k * 2 // sub == 1 and k % (sub // 2) == 0:
                        put('drums', HAT_O, th, 0.2, pan=0.3, send=0.15)
                    else:
                        put('drums', HAT_C, th, 0.26 * acc, pan=0.3)
        # fill into the next section
        if i + 1 in SECTION_BARS and energy(t0 + 1.5) >= 0.6:
            for k in range(4):
                put('drums', SNARE, t0 + 1.5 + k * 0.125, 0.12 + 0.07 * k, pan=0.05, send=0.2)
    for i in SECTION_BARS:
        if bar_t(i) < DUR - 1:
            put('drums', CRASH, bar_t(i), 0.22, pan=-0.2, send=0.35)
    for lab, fd, tm, _ in B.MILESTONE_T:
        put('drums', CRASH, tm, 0.2, pan=0.25, send=0.35)
    put('drums', CRASH, 208.0, 0.26, pan=0.0, send=0.4)


# ---- fx
def sweep(x, fcs, lo_k=0.7, hi_k=1.4):
    """band-pass whose centre follows fcs (one value per sample), filter state carried across blocks"""
    out = np.zeros_like(x)
    zi = None
    blk = 256
    for b0 in range(0, len(x), blk):
        fc = float(fcs[b0])
        sos = butter(2, [fc * lo_k, min(fc * hi_k, SR * 0.45)], btype='band', fs=SR, output='sos')
        if zi is None:
            zi = np.zeros((sos.shape[0], 2))
        out[b0:b0 + blk], zi = sosfilt(sos, x[b0:b0 + blk], zi=zi)
    return out


def riser(dur):
    t = tt(dur)
    x = t / dur
    noise = sweep(RNG.standard_normal(len(t)), 300 + 7000 * x ** 2)
    tone = saw(110 * 2 ** (3 * x ** 1.5), t)
    return (0.8 * noise + 0.15 * lp(tone, 3000)) * x ** 2.2


def downlifter(dur):
    t = tt(dur)
    x = t / dur
    s = sweep(RNG.standard_normal(len(t)), 2400 * (1 - x) ** 2 + 80, 0.6, 1.5)
    return s * (1 - x) ** 1.5 * np.minimum(t / 0.02, 1)


def subdrop():
    t = tt(1.6)
    f = 30 + 50 * np.exp(-t / 0.35)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.7) * np.minimum(t / 0.005, 1)


def stab(name):
    """short full-chord hit for the market-cap milestones"""
    _, notes, _ = CHORDS[name]
    t = tt(1.4)
    sig = np.zeros((2, len(t)))
    for m in notes + [notes[-2] + 12]:
        sig[0] += saw(mtof(m) * 2 ** (-6 / 1200), t, RNG.random())
        sig[1] += saw(mtof(m) * 2 ** (6 / 1200), t, RNG.random())
    env = np.minimum(t / 0.006, 1) * np.exp(-t / 0.45)
    return np.stack([lp(sig[0], 3200), lp(sig[1], 3200)]) * env / len(notes)


def render_fx():
    for lab, fd, tm, _ in B.MILESTONE_T:
        put('fx', stab(chord_at(tm)), tm, 0.5, send=0.45)
        put('fx', subdrop(), tm, 0.3)
    for i in RISE_INTO:
        put('fx', riser(2 * BAR), bar_t(i) - 2 * BAR, 0.16, send=0.3)
    put('fx', riser(5.0), B.END_T0, 0.18, send=0.3)
    for i in SECTION_BARS:
        put('fx', subdrop(), bar_t(i), 0.35)
    put('fx', subdrop(), 208.0, 0.45)
    for d in DROPS:
        put('fx', downlifter(1.5), d, 0.10, send=0.4)
    rev = CRASH[:int(1.0 * SR)][::-1] * np.linspace(0, 1, int(1.0 * SR)) ** 2
    for i in SECTION_BARS:
        put('fx', rev, bar_t(i) - 1.0, 0.10, send=0.3)


# ----------------------------------------------------------------------------
# mix
# ----------------------------------------------------------------------------

def pump(depth, rel=0.16):
    """sidechain-style gain from the kick times"""
    g = np.ones(N, np.float32)
    t = np.arange(int(0.5 * SR)) / SR
    dip = (depth * np.exp(-t / rel) * np.minimum(t / 0.003, 1) + depth * (t < 0.003)).astype(np.float32)
    for tk in KICK_TIMES:
        i = int(tk * SR)
        n = min(len(dip), N - i)
        g[i:i + n] = np.minimum(g[i:i + n], 1 - dip[:n])
    return g


def reverb():
    n = int(2.6 * SR)
    t = np.arange(n) / SR
    out = np.zeros_like(SEND)
    for ch in range(2):
        ir = RNG.standard_normal(n) * np.exp(-t / 0.75)
        ir = lp(ir, 5200)
        ir[:int(0.018 * SR)] = 0
        ir /= np.sqrt(np.sum(ir ** 2))
        out[ch] = fftconvolve(SEND[ch], ir)[:N]
    return out


def main():
    render_pad()
    render_bass()
    render_arp()
    render_lead()
    render_keys()
    render_drums()
    render_fx()
    p_bass, p_pad = pump(0.55), pump(0.3, 0.2)
    mix = (OUT['pad'] * p_pad + OUT['bass'] * p_bass + OUT['arp'] * pump(0.2) + OUT['drums'] + OUT['lead'] * 1.0
           + OUT['keys'] + OUT['fx'])
    mix += reverb() * 0.55
    mix = hp(mix, 30)
    n_out = int(DUR * SR)
    mix = mix[:, :n_out]
    t = np.arange(n_out) / SR
    mix *= np.clip((DUR - t) / 2.0, 0, 1) * np.clip(t / 0.05, 0, 1)
    mix /= np.max(np.abs(mix)) + 1e-9
    mix *= 0.89
    path = os.path.join(B.ROOT, 'out', 'music.wav')
    wavfile.write(path, SR, (mix.T * 32767).astype(np.int16))
    print('wrote', path, f'{n_out / SR:.2f}s', 'kicks', len(KICK_TIMES))


if __name__ == '__main__':
    main()
