"""Original adaptive score for the history videos.

Instruments: FluidR3_GM SoundFont notes (CC BY 3.0, see fetch_samples.py) for piano, strings, choir,
pad, pizzicato, horn, celesta, timpani and taiko; kick, snare, hats, cymbals, bass and the arp are
synthesised here. Tempo is 120 BPM: every story beat in the videos sits on a multiple of 0.5 s, so
hits, drops and lifts land exactly on the picture.

The arrangement follows the market: rallies drive in the "epic" progression, sell-offs switch to a
minor tension progression, black-swan crashes cut the music on the impact, bottoms fall back to piano,
new highs get a two-bar lift and open up with choir. The outro builds over the camera pull-back and
lands a V-VI deceptive cadence on the final summary hit.

ASSET=eth python3 music.py   ->  out/<asset>/music.wav
"""
import itertools
import math
import os

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, sosfilt

import common as B

SR = 48000
BPM = 120.0
BEAT = 60.0 / BPM
BAR = 4 * BEAT
DUR = B.DURATION
N = int((DUR + 4.0) * SR)
SF_DIR = os.environ.get('MUSIC_SAMPLES', os.path.join(B.ROOT, 'samples'))
KEY = {'eth': 2, 'sol': 4}[B.ASSET]          # tonic pitch class: D minor / E minor
RNG = np.random.default_rng(2026)

# ----------------------------------------------------------------------------
# harmony
# ----------------------------------------------------------------------------
CHORDS = {'i': (0, 'min'), 'iv': (5, 'min'), 'v': (7, 'min'), 'V': (7, 'maj'),
          'VI': (8, 'maj'), 'VII': (10, 'maj'), 'III': (3, 'maj')}
PROG = {'main': [['i', 'VI', 'III', 'VII'], ['i', 'VII', 'VI', 'VII']],
        'tension': [['i', 'iv', 'VI', 'V'], ['i', 'VI', 'iv', 'V']]}


def chord_pcs(sym):
    root, q = CHORDS[sym]
    third = 3 if q == 'min' else 4
    return [(KEY + root) % 12, (KEY + root + third) % 12, (KEY + root + 7) % 12]


def root_in(sym, lo):
    """lowest MIDI note >= lo with the chord root's pitch class"""
    pc = chord_pcs(sym)[0]
    return lo + (pc - lo) % 12


def voicing(pcs, prev, lo, hi, n):
    """n notes in [lo, hi] covering the chord (root + fifth when n = 2), closest to the previous voicing"""
    need = set(pcs) if n >= len(pcs) else {pcs[0], pcs[2]}
    cands = [m for m in range(lo, hi + 1) if m % 12 in need]
    best, best_cost = None, 1e9
    for combo in itertools.combinations(cands, n):
        if set(m % 12 for m in combo) != need or combo[-1] - combo[0] > 16:
            continue
        if prev:
            cost = sum(abs(a - b) for a, b in zip(combo, prev))
        else:
            cost = abs(sum(combo) / n - (lo + hi) / 2)
        if cost < best_cost:
            best, best_cost = combo, cost
    return list(best)


def mf(m):
    return 440.0 * 2 ** ((m - 69) / 12)


# ----------------------------------------------------------------------------
# DSP helpers
# ----------------------------------------------------------------------------

def lp(x, fc, order=2):
    return sosfilt(butter(order, fc, btype='low', fs=SR, output='sos'), x, axis=0)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, btype='high', fs=SR, output='sos'), x, axis=0)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], btype='band', fs=SR, output='sos'), x, axis=0)


def sweep_lp(x, fcs):
    """low-pass with a time-varying cutoff (one value per 128-sample block)"""
    out = np.zeros_like(x)
    blk = 128
    zi = None
    for b in range(0, len(x), blk):
        fc = float(np.clip(fcs[min(b // blk, len(fcs) - 1)], 40, SR * 0.45))
        sos = butter(2, fc, btype='low', fs=SR, output='sos')
        if zi is None:
            zi = np.zeros((sos.shape[0], 2))
        y, zi = sosfilt(sos, x[b:b + blk], zi=zi)
        out[b:b + blk] = y
    return out


def saw(freq, n, phase=0.0):
    """band-limited sawtooth (polyBLEP)"""
    dt = freq / SR
    t = (phase + dt * np.arange(n)) % 1.0
    y = 2 * t - 1
    m = t < dt
    u = t[m] / dt
    y[m] -= u + u - u * u - 1
    m = t > 1 - dt
    u = (t[m] - 1) / dt
    y[m] -= u * u + u + u + 1
    return y


def stereo(x, pan=0.0, width=0.0):
    a = (pan + 1) * math.pi / 4
    gl, gr = math.cos(a) * math.sqrt(2), math.sin(a) * math.sqrt(2)
    if x.ndim == 2:
        return np.column_stack([x[:, 0] * gl, x[:, 1] * gr])
    if width > 0:
        d = int(0.011 * SR)
        r = np.concatenate([np.zeros(d), x[:-d]]) if len(x) > d else x
        return np.column_stack([x * gl, (x * (1 - width) + r * width) * gr])
    return np.column_stack([x * gl, x * gr])


def adsr(n, a=0.005, d=0.1, s=0.7, r=0.05, gate=None):
    t = np.arange(n) / SR
    gate = gate if gate is not None else n / SR - r
    e = np.where(t < a, t / max(a, 1e-4), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    rel = t > gate
    e[rel] *= np.exp(-(t[rel] - gate) / max(r / 3, 1e-4))
    return e


def fade_env(n, attack, dur, release):
    t = np.arange(n) / SR
    e = np.ones(n)
    if attack > 0:
        e *= np.sin(np.clip(t / attack, 0, 1) * math.pi / 2) ** 2
    if release > 0:
        e *= np.cos(np.clip((t - dur) / release, 0, 1) * math.pi / 2) ** 2
    return e


# ----------------------------------------------------------------------------
# sampler (FluidR3 notes are 3.14 s; sustained instruments are crossfade-looped)
# ----------------------------------------------------------------------------
class Sampler:
    def __init__(self, name, sustained, ref=62):
        z = np.load(os.path.join(SF_DIR, name + '.npz'))
        self.s = {int(k[1:]): z[k] for k in z.files}
        self.sustained = sustained
        r = self.s[ref]
        seg = r[int(0.4 * SR):int(1.6 * SR)] if sustained else r[:int(0.4 * SR)]
        self.norm = 0.2 / (np.sqrt(np.mean(seg ** 2)) + 1e-9)

    def note(self, midi, dur, vel=1.0, attack=0.0, release=0.4):
        s = self.s[int(np.clip(midi, 21, 108))]
        n = int((dur + release) * SR)
        if self.sustained:
            x = loop_sustain(s, n)
        else:
            x = s[:n]
            if len(x) < n:
                x = np.concatenate([x, np.zeros((n - len(x), 2), np.float32)])
        return x * (fade_env(n, attack, dur, release) * self.norm * vel)[:, None]


def loop_sustain(s, n):
    a, b, c = int(0.9 * SR), int(3.05 * SR), int(0.45 * SR)
    if n <= b:
        return s[:n].astype(np.float64)
    out = s[:b].astype(np.float64)
    seg = s[a:b].astype(np.float64)
    ramp = np.linspace(0, math.pi / 2, c)
    fo, fi = np.cos(ramp)[:, None], np.sin(ramp)[:, None]
    while len(out) < n:
        out = np.concatenate([out[:-c], out[-c:] * fo + seg[:c] * fi, seg[c:]])
    return out[:n]


# ----------------------------------------------------------------------------
# synthesised one-shots
# ----------------------------------------------------------------------------

def tt(d):
    return np.arange(int(d * SR)) / SR


def kick():
    t = tt(0.6)
    f = 46 + 120 * np.exp(-t / 0.032)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.32)
    click = hp(RNG.standard_normal(len(t)), 2500) * np.exp(-t / 0.004) * 0.35
    x = np.tanh(1.6 * (body + click)) / np.tanh(1.6)
    return x * np.minimum(1, t / 0.002)


def snare():
    t = tt(0.55)
    noise = bp(RNG.standard_normal(len(t)), 1200, 9000) * np.exp(-t / 0.16)
    tone = (np.sin(2 * np.pi * 182 * t) + 0.5 * np.sin(2 * np.pi * 331 * t)) * np.exp(-t / 0.07)
    return 0.75 * noise / (np.max(np.abs(noise)) + 1e-9) + 0.6 * tone


def clap():
    t = tt(0.4)
    x = np.zeros(len(t))
    src = bp(RNG.standard_normal(len(t)), 900, 4200)
    for k, off in enumerate((0.0, 0.011, 0.023)):
        i = int(off * SR)
        e = np.exp(-(t[:len(t) - i]) / (0.006 if k < 2 else 0.12))
        x[i:] += src[i:] * e
    return x / (np.max(np.abs(x)) + 1e-9)


def hat(open_=False):
    t = tt(0.35 if open_ else 0.12)
    x = hp(RNG.standard_normal(len(t)), 7000, 4) * np.exp(-t / (0.11 if open_ else 0.035))
    return x / (np.max(np.abs(x)) + 1e-9)


def crash():
    t = tt(3.0)
    x = hp(RNG.standard_normal(len(t)), 3800, 2) * np.exp(-t / 0.9)
    x += 0.5 * bp(RNG.standard_normal(len(t)), 5000, 12000) * np.exp(-t / 0.35)
    return x * np.minimum(1, t / 0.003) / 4


def rev_cymbal(d):
    c = crash()[:int(d * SR)][::-1]
    return c * np.linspace(0, 1, len(c)) ** 1.5


def tom(f0):
    t = tt(0.7)
    f = f0 * (1 + 0.6 * np.exp(-t / 0.04))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.3)
    x += 0.15 * lp(RNG.standard_normal(len(t)), 1500) * np.exp(-t / 0.05)
    return x


def sub_bass(midi, d):
    n = int((d + 0.08) * SR)
    t = np.arange(n) / SR
    f = mf(midi)
    x = np.sin(2 * np.pi * f * t) + 0.18 * np.sin(4 * np.pi * f * t)
    return np.tanh(1.3 * x) * adsr(n, 0.006, 0.4, 0.85, 0.08, gate=d)


def pulse_bass(midi, d):
    n = int((d + 0.06) * SR)
    f = mf(midi)
    x = saw(f, n) * 0.6 + saw(f * 1.004, n, 0.3) * 0.4
    fcs = 260 + 900 * np.exp(-np.arange(0, n, 128) / SR / 0.07)
    x = sweep_lp(x, fcs)
    x += 0.8 * np.sin(2 * np.pi * f * np.arange(n) / SR)
    return x * adsr(n, 0.003, 0.12, 0.55, 0.05, gate=d)


def pluck(midi, d=0.42):
    n = int(d * SR)
    f = mf(midi)
    x = saw(f, n) * 0.7 + saw(f * 1.006, n, 0.5) * 0.5 + np.sign(np.sin(2 * np.pi * f * 0.5 * np.arange(n) / SR)) * 0.15
    fcs = 650 + 4200 * np.exp(-np.arange(0, n, 128) / SR / 0.075)
    x = sweep_lp(x, fcs)
    return x * np.exp(-np.arange(n) / SR / 0.2) * np.minimum(1, np.arange(n) / (0.002 * SR))


# ----------------------------------------------------------------------------
# buses
# ----------------------------------------------------------------------------
BUS_NAMES = ['pad', 'strings', 'choir', 'piano', 'pizz', 'horn', 'celesta', 'bass', 'arp',
             'kick', 'snare', 'hats', 'cymbal', 'toms', 'timp']
BUS = {k: np.zeros((N, 2)) for k in BUS_NAMES}
KICKS = []          # kick times for side-chain pumping
DROP_WIN = []       # (t0, t1): the music stops dead on a black-swan impact until the next bar


def put(bus, x, t, gain=1.0, pan=0.0, width=0.0, through=False):
    i0 = int(round(t * SR))
    if i0 >= N or gain <= 0:
        return
    if not through:
        for d0, d1 in DROP_WIN:
            if d0 - 1e-6 <= t < d1:
                return
            if t < d0 < t + len(x) / SR:
                m = int((d0 - t) * SR)
                f = min(int(0.02 * SR), m)
                x = x[:m].copy()
                x[m - f:] *= np.linspace(1, 0, f)[:, None] if x.ndim == 2 else np.linspace(1, 0, f)
    xs = stereo(x, pan, width)
    if i0 < 0:
        xs = xs[-i0:]
        i0 = 0
    n = min(len(xs), N - i0)
    BUS[bus][i0:i0 + n] += xs[:n] * gain


# ----------------------------------------------------------------------------
# timeline: bar grid, plan
# ----------------------------------------------------------------------------

def bar_grid():
    """regular 2 s bars from 0.5 s; the outro grid is counted back from the final hit at T_END + 10.5,
    with one short bar at the junction when the two grids disagree"""
    T = B.T_END
    target = T + 10.5
    reg = []
    t = 0.5
    while t < T:
        reg.append(t)
        t += BAR
    ends = [target + BAR * j for j in range(-12, 6)]
    ends = [e for e in ends if T - 1.0 < e < DUR + 0.5]
    starts = [s for s in reg if s < ends[0] - 0.75] + ends
    starts.append(starts[-1] + BAR)
    return np.array(starts)


STARTS = bar_grid()
NB = len(STARTS) - 1
K_CHART = int(np.searchsorted(STARTS, B.T_START - 1e-6))
K_END = int(np.searchsorted(STARTS, B.T_END + 0.25))


def bar_of(t):
    return int(np.searchsorted(STARTS, t + 1e-6, side='right') - 1)


def beats(k):
    return int(round((STARTS[k + 1] - STARTS[k]) / BEAT))


def plan():
    mood = {}
    for k in range(K_CHART, K_END):
        tm = 0.5 * (STARTS[k] + STARTS[k + 1])
        d = int(round(B.HEAD[min(int(tm * B.FPS), B.NFRAMES - 1)]))
        r45 = B.LOGP[d] - B.LOGP[max(d - 45, 0)]
        r10 = B.LOGP[d] - B.LOGP[max(d - 10, 0)]
        mood[k] = float(0.7 * np.clip(r45 / 0.10, -1, 1) + 0.3 * np.clip(r10 / 0.05, -1, 1))
    prio = {'drop': 6, 'bottom': 5, 'peak': 4, 'bottom2': 3, 'surge': 3, 'lift2': 2, 'lift1': 1}
    role = {}

    def set_role(k, r):
        if K_CHART < k < K_END and prio[r] > prio.get(role.get(k), 0):
            role[k] = r

    accents = []      # (time, kind) musical punctuation on the beat
    for e in B.EVENTS:
        if e.kind == 'genesis':
            continue
        k = bar_of(e.t)
        if e.kind in ('crash', 'crisis'):
            if e.date in B.BLACK_SWANS:
                set_role(k, 'drop')
                accents.append((e.t, 'drop'))
            else:
                accents.append((e.t, 'hit'))
        elif e.kind == 'bottom':
            set_role(k, 'bottom')
            set_role(k + 1, 'bottom2')
            accents.append((e.t, 'hit'))
        elif e.kind in ('peak', 'high'):
            set_role(k, 'peak')
            set_role(k - 1, 'lift2')
            set_role(k - 2, 'lift1')
            accents.append((e.t, 'peak'))
        elif e.kind == 'rally':
            set_role(k, 'surge')
            accents.append((e.t, 'peak'))
        else:
            accents.append((e.t, 'sparkle'))
    for lv, fd, tm in B.MILESTONE_T:
        accents.append((tm, 'milestone'))
    era_bars = {bar_of(t - 0.5) + 1 for t, _, _ in B.ERA_T[1:]}

    # smooth the mood over neighbouring bars; switch modes only on 2-bar boundaries, with hysteresis
    ks = list(range(K_CHART, K_END))
    sm = {k: 0.25 * mood[max(k - 1, K_CHART)] + 0.5 * mood[k] + 0.25 * mood[min(k + 1, K_END - 1)] for k in ks}
    bars = {}
    mode, prog, phrase, hold = 'bull', 'main', 0, 0
    after_drop = False
    for k in ks:
        m = sm[k]
        r = role.get(k)
        if k in era_bars:
            phrase = 0
        if after_drop:
            mode, prog, phrase, hold = 'bear', 'tension', 0, 0
            after_drop = False
        elif hold >= 2 and phrase % 2 == 0:
            if mode == 'bear' and m > 0.25:
                mode, hold = 'bull', 0
            elif mode == 'bull' and m < -0.25:
                mode, hold = 'bear', 0
        want = 'main' if mode == 'bull' else 'tension'
        if want != prog:
            prog, phrase = want, 0
        chord = PROG[prog][(phrase // 4) % 2][phrase % 4]
        phrase += 1
        hold += 1
        if mode == 'bull':
            L = 1 if m < 0.35 else (2 if m < 0.7 else 3)
        else:
            L = 1 if m > -0.5 else 2
        fill = False
        if r == 'drop':
            L = max(L, 2)
            after_drop = True
        elif r == 'bottom':
            chord, L = 'i', 0
        elif r == 'bottom2':
            chord, L, mode, prog, phrase, hold = 'VI', 0, 'bull', 'main', 2, 0
        elif r == 'lift1':
            chord, L = 'VI', max(L, 2)
        elif r == 'lift2':
            chord, L, fill = 'VII', max(L, 2), True
        elif r == 'peak':
            chord, L, mode, prog, phrase, hold = 'i', 3, 'bull', 'main', 1, 0
        elif r == 'surge':
            L = 3
        if k - 1 in bars and r not in ('peak', 'surge', 'lift2', 'bottom', 'bottom2', 'drop'):
            L = int(np.clip(L, bars[k - 1]['L'] - 1, bars[k - 1]['L'] + 1))
        if k == K_CHART:
            chord, L = 'i', 1
        nxt = role.get(k + 1)
        if nxt in ('peak', 'lift1') or (k + 1) in era_bars:
            fill = True
        bars[k] = dict(chord=chord, L=L, mode=mode, role=r, fill=fill)
    last_theme = B.T_START
    rough = {bar_of(t) for t, kind in accents if kind in ('hit', 'drop')}
    for k in range(K_CHART + 1, K_END - 3):
        run = [bars[j] for j in range(k, k + 4)]
        if ([b['chord'] for b in run] == PROG['main'][0] and all(b['role'] is None and b['L'] <= 2 for b in run)
                and not rough & set(range(k, k + 4)) and STARTS[k] - last_theme >= 20.0):
            for j in range(4):
                bars[k + j]['theme'] = j
            last_theme = STARTS[k]
    # drop windows: music falls silent from the impact to the next bar line
    drops = []
    for t, kind in accents:
        if kind == 'drop':
            k = bar_of(t)
            drops.append((t, STARTS[k + 1]))
    return bars, accents, drops


# ----------------------------------------------------------------------------
# arrangement
# ----------------------------------------------------------------------------
INST = {}


def inst(name, sustained):
    if name not in INST:
        INST[name] = Sampler(name, sustained)
    return INST[name]


# theme in D minor (MIDI, beats from bar start, length in beats); transposed to the key
THEME = [
    [(0, 1, 77), (1, 0.5, 76), (1.5, 0.5, 74), (2, 2, 69)],            # i:   F E D A
    [(0, 1, 74), (1, 0.5, 72), (1.5, 0.5, 70), (2, 2, 65)],            # VI:  D C Bb F
    [(0, 1, 69), (1, 0.5, 70), (1.5, 0.5, 72), (2, 1.5, 77), (3.5, 0.5, 76)],  # III: A Bb C F E
    [(0, 2, 76), (2, 1, 72), (3, 1, 67)],                              # VII: E C G
]
TX = KEY - 2


class Voices:
    def __init__(self):
        self.prev = {}

    def get(self, part, sym, lo, hi, n):
        v = voicing(chord_pcs(sym), self.prev.get(part), lo, hi, n)
        self.prev[part] = v
        return v


V = Voices()


def chord_bar(t0, nb, sym, L, mode, fill=False, peak_at=None, intro=False):
    """one bar of the arrangement"""
    bar_d = nb * BEAT
    pad, strings, choir = inst('pad_2_warm', True), inst('string_ensemble_1', True), inst('choir_aahs', True)
    piano, pizz, horn = inst('acoustic_grand_piano', False), inst('pizzicato_strings', False), inst('french_horn', True)
    # pad: always, recedes as the band fills in
    for m in V.get('pad', sym, 50, 69, 4):
        put('pad', pad.note(m, bar_d + 0.15, 0.55, attack=0.25, release=0.9), t0, {0: 0.6, 1: 0.7, 2: 0.55, 3: 0.5}[L], pan=0.0)
    # strings: sustained chord + low root; violins an octave up at full level
    if L >= 1 or intro:
        g = {0: 0.45, 1: 0.7, 2: 0.85, 3: 1.0}[L]
        att = 0.35 if L <= 1 else 0.12
        up = V.get('strings', sym, 55, 76, 4)
        for j, m in enumerate(up):
            put('strings', strings.note(m, bar_d + 0.1, 0.8, attack=att, release=0.7), t0, g, pan=-0.35 + 0.23 * j)
        put('strings', strings.note(root_in(sym, 40), bar_d + 0.1, 0.9, attack=att, release=0.7), t0, g * 0.9, pan=0.15)
        if L >= 3:
            put('strings', strings.note(up[-1] + 12, bar_d + 0.1, 0.7, attack=0.1, release=0.7), t0, g * 0.8, pan=-0.2)
    # horns: epic weight at full level in the major-key drive
    if L >= 3 and mode == 'bull':
        for m in V.get('horn', sym, 53, 67, 2):
            put('horn', horn.note(m, bar_d, 0.8, attack=0.08, release=0.5), t0, 0.55, pan=0.25)
    # choir on new highs (from the hit) and on the outro
    if peak_at is not None:
        tc = peak_at
        for m in V.get('choir', sym, 57, 72, 3):
            put('choir', choir.note(m, t0 + bar_d - tc + 0.6, 0.9, attack=0.15, release=1.2), tc, 0.9, pan=0.0, width=0.0)
    # piano: arpeggios when it is quiet
    if L <= 1 and not intro:
        r = root_in(sym, 38)
        pcs = chord_pcs(sym)
        third = r + (pcs[1] - pcs[0]) % 12
        fifth = r + 7
        pat = [r, fifth, r + 12, third + 12, fifth + 12, third + 12, r + 12, fifth]
        vel = 0.55 if L == 0 else 0.4
        for i in range(min(8, nb * 2)):
            put('piano', piano.note(pat[i], BEAT * 0.9, vel * (1.0 if i % 2 == 0 else 0.8), release=0.25), t0 + i * BEAT / 2, 1.0, pan=-0.1)
    # bass
    r2 = root_in(sym, 36)
    if L == 0:
        put('bass', sub_bass(r2, bar_d), t0, 0.35)
    elif L == 1:
        put('bass', sub_bass(r2, bar_d), t0, 0.55)
    else:
        for i in range(nb * 2):
            m = r2 + (12 if (L >= 3 and i % 4 == 3) else 0)
            put('bass', pulse_bass(m, BEAT / 2 * 0.85), t0 + i * BEAT / 2, 0.55 if i % 2 == 0 else 0.42)
    # arp (bull) / pizzicato ostinato (bear)
    if L >= 2 and mode == 'bull':
        r = root_in(sym, 62)
        pcs = chord_pcs(sym)
        third = r + (pcs[1] - pcs[0]) % 12
        fifth = r + 7
        pat = [r, fifth, r + 12, third + 12, fifth + 12, third + 12, r + 12, fifth]
        for i in range(nb * 4):
            put('arp', pluck(pat[i % 8]), t0 + i * BEAT / 4, 0.5 if i % 4 == 0 else 0.36, pan=0.0)
    if L >= 1 and mode == 'bear':
        r = root_in(sym, 50)
        pat = [r, r, r + 7, r, r + 12, r, r + 7, r + 3 if CHORDS[sym][1] == 'min' else r + 4]
        for i in range(nb * 2):
            put('pizz', pizz.note(pat[i % 8], 0.18, 0.9 if i % 2 == 0 else 0.7, release=0.1), t0 + i * BEAT / 2, 0.9 if L >= 2 else 0.6, pan=0.3)
    # drums (none under the title card)
    if L >= 1 and not intro:
        drums(t0, nb, L, mode, fill)


ONE = {}


def oneshot(name):
    if name not in ONE:
        ONE[name] = {'kick': kick, 'snare': snare, 'clap': clap, 'hat': hat, 'ohat': lambda: hat(True),
                     'crash': crash, 'tomlo': lambda: tom(72), 'tommid': lambda: tom(98), 'tomhi': lambda: tom(130)}[name]()
    return ONE[name]


def drums(t0, nb, L, mode, fill):
    taiko = inst('taiko_drum', False)
    steps = nb * 2                      # 8th-note steps in the bar
    for i in range(steps):
        t = t0 + i * BEAT / 2
        pos = i % 8
        last_beat = i >= steps - 2
        if L >= 2:
            if pos in (0, 3) or (L >= 3 and pos == 6):
                put('kick', oneshot('kick'), t, 0.9)
                KICKS.append(t)
            if mode == 'bull' and pos == 4:
                put('snare', oneshot('snare'), t, 0.55)
                put('snare', oneshot('clap'), t, 0.35, pan=0.05)
            if mode == 'bear' and pos in (0, 5):
                put('toms', taiko.note(45, 0.6, 1.0, release=0.4), t, 0.9)
            if mode == 'bear' and L >= 2 and pos == 4:
                put('snare', oneshot('snare'), t, 0.35)
        elif pos == 0:
            put('kick', oneshot('kick'), t, 0.55)
            KICKS.append(t)
        # hats
        if L >= 2 or (L == 1 and mode == 'bull'):
            hg = {1: 0.12, 2: 0.22, 3: 0.26}[L]
            put('hats', oneshot('hat'), t, hg * (1.0 if pos % 2 else 0.6), pan=0.35)
            if L >= 3:
                put('hats', oneshot('hat'), t + BEAT / 4, hg * 0.45, pan=0.4)
        elif L == 1 and mode == 'bear':
            put('hats', oneshot('hat'), t, 0.07, pan=0.35)
            put('hats', oneshot('hat'), t + BEAT / 4, 0.05, pan=0.4)
        if fill and last_beat:
            for j in range(2):
                tt_ = t + j * BEAT / 4
                put('toms', oneshot('tomhi' if i == steps - 2 else 'tommid'), tt_, 0.55, pan=-0.2 + 0.2 * j)
                put('snare', oneshot('snare'), tt_, 0.25 + 0.1 * j)


def accent(t, kind, sym):
    timp = inst('timpani', False)
    if kind in ('drop', 'hit'):
        put('timp', timp.note(root_in(sym, 38), 1.5, 1.0, release=0.8), t, 1.0, through=True)
        put('kick', oneshot('kick'), t, 0.8, through=True)
    if kind in ('peak', 'milestone'):
        put('cymbal', oneshot('crash'), t, 0.9 if kind == 'peak' else 0.7, pan=0.2)
        put('kick', oneshot('kick'), t, 0.9)
        put('timp', timp.note(root_in(sym, 38), 1.5, 0.9, release=0.8), t, 0.8)
    if kind == 'sparkle':
        cel = inst('celesta', False)
        r = root_in(sym, 74)
        pcs = chord_pcs(sym)
        for j, m in enumerate((r, r + (pcs[1] - pcs[0]) % 12, r + 7, r + 12)):
            put('celesta', cel.note(m, 0.4, 0.8, release=0.6), t + j * BEAT / 4, 0.7, pan=0.4 - 0.15 * j)


def timpani_roll(t0, d, sym, g0=0.2, g1=0.9):
    timp = inst('timpani', False)
    n = int(d / (BEAT / 4))
    for i in range(n):
        g = g0 + (g1 - g0) * i / max(n - 1, 1)
        put('timp', timp.note(root_in(sym, 38), 0.3, 0.8, release=0.2), t0 + i * BEAT / 4, g)


def melody(t0, notes, vel=0.8, strings_too=False, octave=0):
    piano = inst('acoustic_grand_piano', False)
    strings = inst('string_ensemble_1', True)
    for b, d, m in notes:
        mm = m + TX + 12 * octave
        put('piano', piano.note(mm, d * BEAT, vel, release=0.5), t0 + b * BEAT, 1.0, pan=0.05)
        if strings_too:
            put('strings', strings.note(mm, d * BEAT + 0.05, 0.8, attack=0.05, release=0.4), t0 + b * BEAT, 0.55, pan=-0.05)


def compose():
    bars, accents, drops = plan()
    DROP_WIN.extend(drops)
    # intro: theme over i-VI-III-VII, strings joining, swell into the chart start
    intro = ['i', 'VI', 'III', 'VII']
    for k in range(K_CHART):
        sym = intro[k % 4]
        chord_bar(STARTS[k], beats(k), sym, 0 if k < 1 else 1, 'bull', intro=True)
        melody(STARTS[k], THEME[k % 4], vel=0.75)
    put('cymbal', rev_cymbal(BAR), B.T_START - BAR, 0.6, pan=0.0)
    timpani_roll(B.T_START - BEAT * 2, BEAT * 2, 'VII')
    accent(B.T_START, 'milestone', 'i')
    # chart
    for k in range(K_CHART, K_END):
        b = bars[k]
        peak_at = None
        if b['role'] == 'peak':
            peak_at = next(t for t, kind in accents if kind == 'peak' and bar_of(t) == k)
        chord_bar(STARTS[k], beats(k), b['chord'], b['L'], b['mode'], b['fill'], peak_at)
        if 'theme' in b:
            melody(STARTS[k], THEME[b['theme']], vel=0.7, strings_too=b['L'] >= 2)
        if b['role'] == 'lift2':
            put('cymbal', rev_cymbal(STARTS[k + 1] - STARTS[k]), STARTS[k], 0.5)
            timpani_roll(STARTS[k] + BAR / 2, BAR / 2, b['chord'], 0.15, 0.7)
    for t, kind in accents:
        k = bar_of(t)
        sym = bars[k]['chord'] if k in bars else 'i'
        accent(t, kind, sym)
    # outro: questions -> build over the pull-back -> V-VI deceptive hit -> resolve on i
    T = B.T_END
    plan_end = {0.5: ('iv', 0), 2.5: ('V', 0), 4.5: ('VI', 1), 6.5: ('VII', 2),
                8.5: ('V', 2), 10.5: ('VI', 3), 12.5: ('i', 1), 14.5: ('i', 0)}
    for k in range(K_END, NB):
        t0 = STARTS[k]
        sym, L = plan_end.get(round(t0 - T, 2), ('i', 0))
        if t0 - T >= 12.0:
            continue
        chord_bar(t0, beats(k), sym, L, 'bull', fill=(abs(t0 - T - 8.5) < 0.01), peak_at=t0 if L == 3 else None)
        if abs(t0 - T - 2.5) < 0.01:
            timpani_roll(t0 + BAR / 2, BAR / 2, sym, 0.1, 0.4)
        if abs(t0 - T - 8.5) < 0.01:
            put('cymbal', rev_cymbal(BAR), t0, 0.7)
            timpani_roll(t0, BAR, sym, 0.15, 1.0)
    hit = T + 10.5
    accent(hit, 'peak', 'VI')
    melody(hit, [(0, 1, 74), (1, 0.5, 72), (1.5, 0.5, 70), (2, 2, 65)], vel=0.9, strings_too=True)
    # final resolve: long i chord with choir + strings, piano A -> D
    fin = T + 12.5
    tail = DUR - fin + 0.6
    pad, strings, choir = inst('pad_2_warm', True), inst('string_ensemble_1', True), inst('choir_aahs', True)
    for m in V.get('strings', 'i', 55, 76, 4):
        put('strings', strings.note(m, tail, 0.8, attack=0.2, release=1.0), fin, 0.85)
    put('strings', strings.note(root_in('i', 40), tail, 0.9, attack=0.2, release=1.0), fin, 0.8)
    for m in V.get('choir', 'i', 57, 72, 3):
        put('choir', choir.note(m, tail, 0.8, attack=0.3, release=1.2), fin, 0.7)
    for m in V.get('pad', 'i', 50, 69, 4):
        put('pad', pad.note(m, tail, 0.6, attack=0.3, release=1.2), fin, 0.6)
    put('bass', sub_bass(root_in('i', 36), tail), fin, 0.45)
    melody(fin, [(0, 2, 69), (2, 6, 74)], vel=0.8)
    put('cymbal', oneshot('crash'), fin, 0.35, pan=-0.2)
    return drops


# ----------------------------------------------------------------------------
# mixdown
# ----------------------------------------------------------------------------

def reverb_ir(decay, length, seed, lp_fc=7000):
    rng = np.random.default_rng(seed)
    n = int(length * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal((n, 2)) * np.exp(-t / decay)[:, None]
    ir = lp(ir, lp_fc)
    ir[:int(0.018 * SR)] = 0
    return ir / np.sqrt(np.sum(ir ** 2, axis=0, keepdims=True))


def conv_st(x, ir):
    return np.column_stack([fftconvolve(x[:, 0], ir[:, 0])[:len(x)], fftconvolve(x[:, 1], ir[:, 1])[:len(x)]])


def pingpong(x, d=0.375, fb=0.38, taps=5):
    out = np.zeros_like(x)
    n = int(d * SR)
    g = 1.0
    for k in range(1, taps + 1):
        g *= fb
        sh = n * k
        if sh >= len(x):
            break
        ch = k % 2
        out[sh:, ch] += x[:-sh, 0 if ch else 1] * g
    return out


def gain_env(times, depth, tau=0.13, rel=None):
    g = np.ones(N)
    for t in times:
        i = int(t * SR)
        m = min(N - i, int(0.6 * SR))
        if m <= 0:
            continue
        x = np.arange(m) / SR
        g[i:i + m] = np.minimum(g[i:i + m], 1 - depth * np.exp(-x / tau))
    return g


def mute_env(windows, fade=0.03):
    g = np.ones(N)
    for t0, t1 in windows:
        i0, i1 = int(t0 * SR), int(t1 * SR)
        f = int(fade * SR)
        g[i0:i1] = 0.0
        g[max(i0 - f, 0):i0] = np.minimum(g[max(i0 - f, 0):i0], np.linspace(1, 0, i0 - max(i0 - f, 0)))
        g[i1:i1 + f] = np.minimum(g[i1:i1 + f], np.linspace(0, 1, len(g[i1:i1 + f])))
    return g


GAIN_DB = {'pad': -14, 'strings': -9, 'choir': -10, 'piano': -3, 'pizz': -11.5, 'horn': -12, 'celesta': -13,
           'bass': -11, 'arp': -13, 'kick': -12, 'snare': -3, 'hats': -4, 'cymbal': -10, 'toms': -14, 'timp': -14}
SEND = {'pad': 0.35, 'strings': 0.4, 'choir': 0.5, 'piano': 0.3, 'pizz': 0.25, 'horn': 0.35, 'celesta': 0.5,
        'arp': 0.25, 'snare': 0.25, 'toms': 0.2, 'timp': 0.25, 'cymbal': 0.1}


def mixdown(drops):
    hall = reverb_ir(0.85, 3.2, 11)
    plate = reverb_ir(0.35, 1.4, 12, 9000)
    pump = gain_env(KICKS, 0.32)
    mute = mute_env(drops)
    send_h = np.zeros((N, 2))
    send_p = np.zeros((N, 2))
    dry = np.zeros((N, 2))
    for name in BUS_NAMES:
        x = BUS[name] * 10 ** (GAIN_DB[name] / 20)
        if name not in ('timp', 'kick'):          # the impact itself still lands; everything else stops dead
            x = x * mute[:, None]
        if name == 'bass':
            x = lp(x, 900)
        if name == 'arp':
            x = hp(x, 180) + pingpong(hp(x, 180)) * 0.6
        if name in ('pad', 'strings', 'bass', 'arp', 'choir', 'horn', 'pizz'):
            x = x * pump[:, None]
        if name in ('snare', 'toms'):
            send_p += x * SEND[name]
        elif name in SEND:
            send_h += x * SEND[name]
        dry += x
    wet = conv_st(send_h, hall) * 0.9 + conv_st(send_p, plate) * 0.7
    out = dry + wet
    out = hp(out, 30)
    n_out = int(DUR * SR)
    out = out[:n_out]
    fade = np.clip((DUR - np.arange(n_out) / SR) / 1.2, 0, 1)
    out *= fade[:, None]
    return out


def main():
    drops = compose()
    out = mixdown(drops)
    pk = np.max(np.abs(out))
    out = out / pk * 0.5
    path = os.path.join(B.OUT, 'music.wav')
    wavfile.write(path, SR, out.astype(np.float32))
    print('wrote', path, 'bars', NB, 'chart bars', K_CHART, K_END, 'drops', len(drops), 'peak', pk)


if __name__ == '__main__':
    main()
