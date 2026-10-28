"""Original score for the English edition (writes ../out/music.wav and per-bus stems in ../work/).

Hybrid orchestral: VSCO 2 CE strings / horns / harp / glockenspiel / percussion (CC0) and the
Salamander grand piano (CC BY 3.0), plus a quiet synth pulse and sub. Everything is arranged from
score.py: chords, an energy curve that follows the market (crashes cut it on the frame), theme
statements on the big peaks, and hits / swells on the video's events.
"""
import math
import os
import sys
import time
from itertools import combinations

import numpy as np
from scipy.io import wavfile
from scipy.ndimage import uniform_filter1d
from scipy.signal import butter, oaconvolve, sosfilt

import samplelib as S
import score as SC

SR = S.SR
N = int((SC.DUR + 4.0) * SR)
TS = np.arange(N, dtype=np.float32) / SR
E_ARR = uniform_filter1d(np.interp(TS, SC._ET, SC._EV).astype(np.float32), int(0.04 * SR))
OUT = os.path.join(S.ROOT, 'out')
WORK = os.path.join(S.ROOT, 'work')


def E(t):
    return SC.energy(t)


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def sos_lp(fc, order=2):
    return butter(order, fc, btype='low', fs=SR, output='sos')


def sos_hp(fc, order=2):
    return butter(order, fc, btype='high', fs=SR, output='sos')


class Bus:
    def __init__(self, name, send):
        self.name = name
        self.send = send
        self.x = np.zeros((2, N), np.float32)

    def add(self, sig, t, gain=1.0, pan=0.0):
        if gain <= 1e-4:
            return
        i0 = int(round(t * SR))
        if sig.ndim == 1:
            sig = np.vstack([sig, sig])
        if i0 < 0:
            sig = sig[:, -i0:]
            i0 = 0
        n = min(sig.shape[1], N - i0)
        if n <= 0:
            return
        a = (clamp(pan, -1, 1) + 1) * math.pi / 4
        gl, gr = math.cos(a) * math.sqrt(2), math.sin(a) * math.sqrt(2)
        self.x[0, i0:i0 + n] += sig[0, :n] * (gain * gl)
        self.x[1, i0:i0 + n] += sig[1, :n] * (gain * gr)


# ----------------------------------------------------------------------------
# instruments
# ----------------------------------------------------------------------------

def load_instruments():
    I = {}
    V = 'vsco/Strings/'
    I['vln'] = S.Instrument(V + 'Violin Section/susVib/*.wav', r'_(?P<note>[A-G]#?\d)_(?P<layer>v\d)\.wav', 12, 9.0)
    I['vla'] = S.Instrument(V + 'Viola Section/susvib/*.wav', r'_(?P<note>[A-G]#?\d)_(?P<layer>v\d)_1\.wav', 12, 9.0)
    I['vc'] = S.Instrument(V + 'Cello Section/susvib/*.wav', r'susvib_(?P<note>[A-G]#?\d)_(?P<layer>v\d)_1\.wav', 12, 9.0)
    I['cb'] = S.Instrument(V + 'Solo Contrabass/SusVib/*.wav', r'_(?P<note>[A-G]#?\d)_(?P<layer>v\d)_rr1\.wav', 12, 9.0)
    I['vc_spic'] = S.Instrument(V + 'Cello Section/spic/*.wav', r'spic_(?P<note>[A-G]#?\d)_v2_RR\d\.wav', 12, 1.5)
    I['vln_spic'] = S.Instrument(V + 'Violin Section/Spic/*.wav', r'_(?P<note>[A-G]#?\d)_v2_rr\d\.wav', 12, 1.2)
    I['vla_spic'] = S.Instrument(V + 'Viola Section/spic/*.wav', r'_(?P<note>[A-G]#?\d)_v2_rr\d\.wav', 12, 1.2)
    I['harp'] = S.Instrument(V + 'Harp/*.wav', r'KSHarp_(?P<note>[A-G]#?\d)_', 0, 6.0)
    I['horn'] = S.Instrument('vsco/Brass/F Horn/sus/*.wav', r'_(?P<note>[A-G]#?\d)_(?P<layer>v\d)_1\.wav', 12, 9.0)
    I['glock'] = S.Instrument('vsco/Percussion/Glock/*.wav', r'_(?P<note>[A-G]#?\d)\.wav', 12, 4.0)
    I['piano'] = S.Instrument('salamander/*.flac', r'(?P<note>[A-G]#?\d)(?P<layer>v\d+)\.flac', 0, 10.0)
    P = 'vsco/VSCO 1 Percussion/'
    T = 'vsco/Percussion/Timpani/'
    files = {
        'timp1': T + 'Timpani1_Hit_v1_rr1_Sum.wav', 'timp1b': T + 'Timpani1_Hit_v1_rr2_Sum.wav',
        'timp3': T + 'Timpani1_Hit_v3_rr1_Sum.wav', 'timp3b': T + 'Timpani1_Hit_v3_rr2_Sum.wav',
        'timp_roll': T + 'Rolls/Timpani1_Roll_v3_rr1_Sum.wav',
        'bd_fff': P + 'drums/bass/bdrum_fff_1.wav', 'bd_ff': P + 'drums/bass/bdrum_ff_1.wav',
        'bd_f': P + 'drums/bass/bdrum_f_1.wav', 'bd_mp': P + 'drums/bass/bdrum_mp_1.wav',
        'crash_fff': P + 'varMetal/Cymbals/clash/crash_hit_fff_loose.wav',
        'crash_ff': P + 'varMetal/Cymbals/clash/crash_hit_ff_loose.wav',
        'crash_mp': P + 'varMetal/Cymbals/clash/crash_hit_mp_loose.wav',
        'sus_cresc': P + 'varMetal/Cymbals/susp/susp_hit_softmall_roll2_cresc.wav',
        'sus_hit': P + 'varMetal/Cymbals/susp/susp_hit_hardmall_f.wav',
        'gong_ff': P + 'varMetal/Gong/gong_hit_ff.wav', 'gong_f': P + 'varMetal/Gong/gong_hit_f.wav',
        'snare_roll': P + 'drums/snare/drum2/snare2_nosnare_roll_ff_1.wav',
        'chimes': P + 'varMetal/various/windchimes_slowAsc1.wav',
    }
    for k in ('ff_1', 'ff_2', 'ff_3', 'f_1', 'f_2', 'mf_1', 'mf_2', 'mp_1'):
        files['tenor_' + k] = P + 'drums/tenor/tenor_lower/tenor_' + k + '.wav'
    for k in ('ff_1', 'ff_2', 'f_1', 'f_2', 'mf_1', 'mp_1'):
        files['tenorH_' + k] = P + 'drums/tenor/tenor_higher/tenorH_' + k + '.wav'
    I['perc'] = S.OneShot(files)
    for k, x in I['perc'].s.items():   # one-shots: equal peaks, levels set in the arrangement
        I['perc'].s[k] = (x * (0.5 / (np.abs(x).max() + 1e-9))).astype(np.float32)
    return I


# timpani 1 sits near F2 (89.7 Hz); these shifts tune it to D2 / A2
TIMP_D, TIMP_A, ROLL_D = -3.47, 3.53, -3.68
# legato strings speak slowly (soft violins reach 30 % level after ~320 ms): melody notes skip into the
# sample a little and start early by the rest, so they sound on the beat. (pre-roll s, sample offset s)
ATTACK = {('vln', 'v1'): (0.17, 0.14), ('vln', 'v2'): (0.08, 0.07), ('vc', 'v1'): (0.12, 0.1), ('vc', 'v3'): (0.03, 0.0)}

# ----------------------------------------------------------------------------
# voicing
# ----------------------------------------------------------------------------


def voicing(chord, prev, k, lo, hi, bass_only=False):
    r, pcs, bass_pc = SC.parse_chord(chord)
    if bass_only:
        cands = [m for m in range(lo, hi + 1) if m % 12 == bass_pc]
        ref = prev[0] if prev else (lo + hi) / 2
        return [min(cands, key=lambda m: abs(m - ref))]
    third = [p for p in pcs if (p - r) % 12 in (3, 4)]
    cands = [m for m in range(lo, hi + 1) if m % 12 in pcs]
    best, bc = None, 1e9
    for combo in combinations(cands, k):
        if k > 1 and max(combo) - min(combo) > 14:
            continue
        cost = 6.0 * (k - len({m % 12 for m in combo}))
        if prev and len(prev) == k:
            cost += sum(abs(a - b) for a, b in zip(combo, prev))
        else:
            cost += 0.3 * sum(abs(m - (lo + hi) / 2) for m in combo)
        if k >= 2 and third and not any(m % 12 in third for m in combo):
            cost += 5.0
        if cost < bc:
            best, bc = list(combo), cost
    return best


def voice_lines(lo, hi, k, bass_only=False, t_from=0.0, t_to=SC.DUR, max_tie=8.0):
    """notes (start, end, midi) for one section group, tied across chords when a voice holds its pitch"""
    notes = []
    cur = [None] * k
    prev = None
    for t0, t1, name in SC.chord_segments():
        if t1 <= t_from or t0 >= t_to:
            continue
        t0, t1 = max(t0, t_from), min(t1, t_to)
        v = voicing(name, prev, k, lo, hi, bass_only)
        prev = v
        for i, m in enumerate(v):
            c = cur[i]
            if c and c[1] == m and t1 - c[0] <= max_tie:
                cur[i] = (c[0], m, t1)
            else:
                if c:
                    notes.append((c[0], c[2], c[1]))
                cur[i] = (t0, m, t1)
    for c in cur:
        if c:
            notes.append((c[0], c[2], c[1]))
    return sorted(notes)


# ----------------------------------------------------------------------------
# synth voices
# ----------------------------------------------------------------------------

def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


_PLUCKS = {}


def pluck(m, dur=0.16, bright=1.0):
    """two detuned saws through a decaying low-pass (additive, band-limited)"""
    key = (m, dur, round(bright, 1))
    if key not in _PLUCKS:
        _PLUCKS[key] = _pluck(m, dur, round(bright, 1))
    return _PLUCKS[key]


def _pluck(m, dur, bright):
    n = int((dur + 0.25) * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for det in (-0.07, 0.07):
        f = mtof(m + det)
        K = int(min(9000 / f, 40))
        k = np.arange(1, K + 1)[:, None]
        fc = 500 + 2600 * bright * np.exp(-t / 0.07)
        H = 1.0 / np.sqrt(1 + (k * f / fc[None, :]) ** 4)
        out += (np.sin(2 * np.pi * f * k * t[None, :] + k) / k * H).sum(0)
    env = np.minimum(1, t / 0.003) * np.exp(-t / (dur * 0.45))
    return (out * env * 0.25).astype(np.float32)


def sub_note(m, dur):
    n = int((dur + 0.2) * SR)
    t = np.arange(n) / SR
    f = mtof(m)
    x = np.sin(2 * np.pi * f * t) + 0.18 * np.sin(4 * np.pi * f * t + 0.5)
    x = np.tanh(1.6 * x) / np.tanh(1.6)
    env = np.minimum(1, t / 0.04) * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.06))
    return (x * env * 0.5).astype(np.float32)


# ----------------------------------------------------------------------------
# arrangement
# ----------------------------------------------------------------------------

def arrange(I):
    buses = {k: Bus(k, s) for k, s in (
        ('pad_vln', 0.42), ('pad_vla', 0.4), ('pad_vc', 0.34), ('pad_cb', 0.25), ('horn_pad', 0.42),
        ('mel_vln', 0.42), ('mel_horn', 0.45), ('ost', 0.24), ('spic_hi', 0.3), ('piano', 0.32),
        ('harp', 0.38), ('glock', 0.45), ('timp', 0.3), ('drums', 0.18), ('cym', 0.3), ('synth', 0.22),
        ('sub', 0.0))}
    beat = SC.BEAT

    def soft_or_loud(inst, t, thr=0.55):
        names = I[inst].layer_names
        return names[0] if E(t) < thr else names[-1]

    # ---- string pads (the bed of the whole piece)
    groups = [('cb', 'pad_cb', 1, (31, 45), True, -0.0), ('vc', 'pad_vc', 2, (43, 60), False, 0.35),
              ('vla', 'pad_vla', 2, (55, 69), False, 0.15), ('vln', 'pad_vln', 3, (62, 77), False, -0.35)]
    for inst, bus, k, (lo, hi), bass, pan in groups:
        for t0, t1, m in voice_lines(lo, hi, k, bass):
            sig = I[inst].note(m, 0.8, dur=t1 - t0, attack=0.3, release=0.7, layer=soft_or_loud(inst, t0))
            buses[bus].add(sig, t0 - 0.05, 1.0, pan + (0.1 if bass else 0.0))
    # low horns hold root + fifth under the climaxes
    for t0, t1, m in voice_lines(41, 55, 2, False):
        if E(t0 + 0.1) < 0.7:
            continue
        sig = I['horn'].note(m, 0.8, dur=t1 - t0, attack=0.25, release=0.6, layer=I['horn'].layer_names[-2])
        buses['horn_pad'].add(sig, t0 - 0.05, 1.0, -0.2)

    # ---- theme statements
    for t0, inst, notes in SC.MELODY:
        for b, d, m, vel in notes:
            ts, dur = t0 + b * beat, d * beat
            if inst == 'piano':
                buses['piano'].add(I['piano'].note(m, vel, dur=dur + 0.4, release=0.9), ts, 1.0, 0.05)
            elif inst == 'glock':
                buses['glock'].add(I['glock'].note(m, vel, dur=None), ts, 0.9, 0.3)
                buses['piano'].add(I['piano'].note(m - 12, 0.32, dur=dur + 0.3, release=0.8), ts, 0.8, 0.0)
            elif inst == 'horn':
                lay = 'v1' if vel < 0.6 else 'v3'
                pre, skip = ATTACK['vc', lay]
                buses['mel_horn'].add(I['vc'].note(m, vel, dur=dur + 0.06, release=0.45, layer=lay, offset=skip), ts - pre, 1.0, 0.25)
                hl = I['horn'].layer_names[min(2, int(vel * 3))]
                buses['mel_horn'].add(I['horn'].note(m, vel, dur=dur + 0.06, attack=0.04, release=0.45, layer=hl), ts - 0.04, 0.55, -0.25)
            elif inst == 'violin':
                lay = 'v1' if vel < 0.65 else 'v2'
                pre, skip = ATTACK['vln', lay]
                buses['mel_vln'].add(I['vln'].note(m, vel, dur=dur + 0.08, release=0.5, layer=lay, offset=skip), ts - pre, 1.0, -0.3)

    # ---- cello spiccato ostinato (8ths) - the engine of every rally; the figure changes with each era
    pats = [(0.0, [0, 0, 12, 0, 7, 0, 12, 7]), (62.2, [0, 12, 7, 12, 0, 12, 7, 12]),
            (88.1, [0, 0, 0, 12, 0, 0, 7, 0]), (102.2, [0, 0, 12, 0, 7, 0, 12, 7]),
            (141.9, [0, 7, 12, 7, 0, 7, 12, 7]), (159.0, [0, 12, 7, 12, 0, 12, 7, 12]),
            (183.0, [0, 0, 0, 0, 0, 0, 0, 0])]
    acc = [1.0, 0.55, 0.8, 0.55, 0.9, 0.55, 0.8, 0.65]
    t = SC.tb(4)
    k = 0
    while t < 188.4:
        e = E(t)
        if e >= 0.45:
            r, pcs, bass_pc = SC.parse_chord(SC.chord_at(t + 0.01))
            base = [m for m in range(38, 50) if m % 12 == bass_pc][0]
            pat = [p for t_, p in pats if t_ <= t][-1]
            off = pat[k % 8]
            if off == 7 and (bass_pc + 7) % 12 not in pcs:
                off = 12
            vel = clamp((e - 0.38) / 0.5) * acc[k % 8]
            buses['ost'].add(I['vc_spic'].note(base + off, vel), t, 1.0, 0.3)
            if e >= 0.62:   # violas double an octave up on the strong eighths
                if k % 2 == 0:
                    buses['ost'].add(I['vla_spic'].note(base + off + 12, vel * 0.8), t, 0.7, 0.1)
        t += beat / 2
        k += 1

    # ---- violin spiccato 16ths at full energy
    t = SC.tb(4)
    k = 0
    while t < 188.4:
        e = E(t)
        if e >= 0.72:
            tones = SC.chord_tones_at(t + 0.01, 67, 84)[:4]
            seq = [0, 1, 2, 1, 0, 1, 2, 3 if len(tones) > 3 else 1]
            m = tones[seq[k % 8] % len(tones)]
            vel = clamp((e - 0.65) / 0.3) * (1.0 if k % 4 == 0 else 0.62)
            buses['spic_hi'].add(I['vln_spic'].note(m, vel), t, 1.0, -0.4)
        t += beat / 4
        k += 1

    # ---- piano: left hand under the soft parts, final arpeggio
    for t0, t1, name in SC.chord_segments():
        e = E(t0 + 0.05)
        quiet = e < 0.45 and (t0 < SC.tb(15) or SC.tb(64) <= t0 < SC.tb(71) or t0 >= SC.tb(89) or 50.5 <= t0 < 62.0
                              or 86.5 <= t0 < 102.0)
        if not quiet or t1 - t0 < 0.9:
            continue
        r, pcs, bass_pc = SC.parse_chord(name)
        lo = [m for m in range(38, 50) if m % 12 == bass_pc][0]
        buses['piano'].add(I['piano'].note(lo, 0.38, dur=t1 - t0 + 0.3, release=1.2), t0, 0.9, -0.05)
        fifth = [m for m in range(lo + 5, lo + 10) if m % 12 in pcs]
        if fifth:
            buses['piano'].add(I['piano'].note(fifth[0] + 12, 0.28, dur=t1 - t0, release=1.2), t0 + beat, 0.7, 0.05)
    for j, m in enumerate((38, 45, 50, 54, 57, 62, 66, 69, 74)):   # D major spread on the tagline
        buses['piano'].add(I['piano'].note(m, 0.4 + 0.02 * j, dur=3.6 - 0.12 * j, release=1.5), SC.tb(95) + 0.11 * j, 0.75, 0.0)

    # ---- harp: intro sweep with the preview line, arpeggios in the hopeful stretches
    n_g = 22
    for j in range(n_g):
        ts = 3.3 + 1.2 * j / n_g
        tones = SC.chord_tones_at(ts, 46, 91)
        m = tones[min(int(j / n_g * len(tones)), len(tones) - 1)]
        buses['harp'].add(I['harp'].note(m, 0.5 + 0.3 * j / n_g), ts, 0.8, -0.4)
    harp_spans = [(SC.tb(4), 30.0), (59.5, 62.4), (99.5, 102.4), (142.0, 157.5), (SC.tb(94), SC.tb(95) - 0.1)]
    up = [0, 1, 2, 3, 4, 3, 2, 1]
    for a, b in harp_spans:
        t = a
        k = 0
        while t < b:
            e = E(t)
            if e >= 0.15:
                tones = SC.chord_tones_at(t + 0.01, 50, 79)
                m = tones[up[k % 8] % len(tones)]
                vel = 0.42 + 0.25 * (k % 8 == 0)
                buses['harp'].add(I['harp'].note(m, vel), t, 0.75 if e < 0.7 else 0.5, -0.4)
            t += beat / 2
            k += 1
    # a last glissando up through D major as the tagline lands
    tones = SC.chord_tones_at(SC.tb(95) + 0.01, 50, 93)
    for j, m in enumerate(tones):
        buses['harp'].add(I['harp'].note(m, 0.45 + 0.02 * j), SC.tb(95) + 0.07 * j, 0.6, -0.4)

    # ---- percussion on the events
    perc = I['perc']
    rr = [0]

    def timp(t, semis, loud, g):
        rr[0] += 1
        key = ('timp3' if loud else 'timp1') + ('b' if rr[0] % 2 else '')
        buses['timp'].add(perc.hit(key, 1.0, semis), t, g, -0.1)

    def stab(t, g):
        """short low-string sforzando on the chord root"""
        r, pcs, bass_pc = SC.parse_chord(SC.chord_at(t + 0.01))
        lo = [m for m in range(31, 43) if m % 12 == bass_pc][0]
        buses['pad_cb'].add(I['cb'].note(lo, 1.0, dur=0.5, release=0.5, layer='v3'), t, 1.6 * g, 0.1)
        buses['pad_vc'].add(I['vc'].note(lo + 12, 1.0, dur=0.5, release=0.5, layer='v3'), t, 1.4 * g, 0.3)

    def sparkle(t, g, n=4):
        tones = SC.chord_tones_at(t, 79, 98)
        for j in range(n):
            buses['glock'].add(I['glock'].note(tones[(j * 2) % len(tones)], 0.6), t + 0.07 * j, g * (1 - 0.15 * j), 0.3)

    for t, kind, s in SC.accents():
        if kind == 'peak':
            timp(t, TIMP_D, True, 0.85 * s)
            buses['drums'].add(perc.hit('bd_ff'), t, 0.8 * s)
            buses['cym'].add(perc.hit('crash_ff'), t, 0.55 * s, 0.25)
            sparkle(t, 0.5)
        elif kind == 'swan':
            timp(t, TIMP_D, True, 1.0)
            timp(t + 0.004, TIMP_A - 12, True, 0.7)
            buses['drums'].add(perc.hit('bd_fff'), t, 1.0)
            buses['cym'].add(perc.hit('gong_ff'), t - 0.02, 0.8, -0.15)
            buses['cym'].add(perc.hit('crash_fff'), t, 0.45, 0.3)
            stab(t, 1.0)
        elif kind == 'crash':
            timp(t, TIMP_D, True, 0.8 * s / 0.75)
            buses['drums'].add(perc.hit('bd_ff'), t, 0.75)
            stab(t, 0.7)
        elif kind == 'bottom':
            timp(t, TIMP_D, False, 0.7)
            buses['drums'].add(perc.hit('bd_mp'), t, 0.6)
            buses['cym'].add(perc.hit('gong_f'), t, 0.25, -0.2)
        elif kind == 'tech':
            sparkle(t, 0.45, 3)
            timp(t, TIMP_A, False, 0.45)
        elif kind == 'adopt':
            sparkle(t, 0.4, 3)
            timp(t, TIMP_A, False, 0.5)
        elif kind == 'milestone':
            sparkle(t, 0.7, 5)
            buses['cym'].add(perc.hit('crash_mp'), t, 0.45, 0.35)
            buses['cym'].add(perc.hit('chimes'), t - 0.1, 0.25, 0.4)
        elif kind == 'era':   # era titles fall between beats: hit on the next eighth so it locks with the pulse
            tq = SC.T0 + math.ceil((t - SC.T0) / (beat / 2) - 1e-6) * (beat / 2)
            buses['drums'].add(perc.hit('bd_f'), tq, 0.55)
            timp(tq, TIMP_D, False, 0.55)

    # swells cresting on the big moments: suspended-cymbal roll + timpani roll (+ snare roll on the top three)
    roll = perc.hit('timp_roll', 1.0, ROLL_D)
    for T in SC.SWELLS:
        cym = perc.hit('sus_cresc')
        pk = int(3.84 * SR)
        seg = cym[:, :pk + int(0.12 * SR)].copy()
        seg[:, pk:] *= np.linspace(1, 0, seg.shape[1] - pk)
        buses['cym'].add(seg, T - 3.84, 0.7, 0.2)
        L = 2.6
        r_ = roll[:, :int(L * SR)].copy()
        r_ *= (np.linspace(0, 1, r_.shape[1]) ** 2.2)[None, :]
        buses['timp'].add(r_, T - L, 0.9, -0.1)
        if T in (80.5, 125.0, 170.5):
            sn = perc.hit('snare_roll')
            pk2 = int(2.62 * SR)
            sn = sn[:, :pk2].copy() * (np.linspace(0.3, 1, pk2) ** 2)[None, :]
            buses['drums'].add(sn, T - 2.62, 0.5, 0.1)
    # the ending hit under "≈ 890,000×" and a soft gong for the tagline
    timp(189.5, TIMP_D, True, 0.9)
    buses['drums'].add(perc.hit('bd_ff'), 189.5, 0.8)
    buses['cym'].add(perc.hit('crash_ff'), 189.5, 0.5, 0.25)
    buses['cym'].add(perc.hit('gong_f'), SC.tb(95), 0.35, -0.2)

    # ---- tenor drums: the epic engine (8ths), bass drum on downbeats at the top
    PAT = ([1.0, 0, 0.45, 0, 0.75, 0.35, 0, 0.5], [1.0, 0, 0.45, 0.35, 0.8, 0, 0.55, 0.7])
    t = SC.tb(4)
    k = 0
    while t < 188.4:
        e = E(t)
        a = PAT[(k // 8) % 2][k % 8]
        if e >= 0.66 and a > 0:
            v = clamp((e - 0.58) / 0.32) * a
            if a >= 0.75:
                key = ('tenor_ff_1', 'tenor_ff_2', 'tenor_ff_3')[k % 3]
            elif a >= 0.5:
                key = ('tenorH_f_1', 'tenorH_f_2')[k % 2]
            else:
                key = ('tenorH_mf_1', 'tenor_mf_1', 'tenor_mf_2')[k % 3]
            buses['drums'].add(perc.hit(key), t, 0.8 * v, 0.05 * ((k % 3) - 1))
        if e >= 0.82 and k % 8 == 0:
            buses['drums'].add(perc.hit('bd_f'), t, 0.55 * clamp((e - 0.78) / 0.2))
        t += beat / 2
        k += 1
    # 16th-note tenor fill over the last beat and a half before each swell crests (on-grid swells only)
    for T in SC.SWELLS:
        if abs((T - SC.T0) / (beat / 2) - round((T - SC.T0) / (beat / 2))) > 0.02:
            continue
        for j in range(6):
            ts = T - (6 - j) * beat / 4
            v = 0.45 + 0.55 * j / 5
            key = ('tenorH_f_1', 'tenorH_f_2', 'tenor_f_1', 'tenor_f_2', 'tenor_ff_1', 'tenor_ff_2')[j]
            buses['drums'].add(perc.hit(key), ts, 0.75 * v, 0.15 * (-1) ** j)

    # ---- synth: 16th pulse in the 'machine' stretches, sub under the rallies
    pulse_spans = [(88.5, 96.0), (SC.tb(51), 118.0), (118.5, 127.4), (142.0, 173.5)]
    for a, b in pulse_spans:
        t = a
        k = 0
        while t < b:
            e = E(t)
            if e >= 0.3:
                tones = SC.chord_tones_at(t + 0.01, 62, 76)
                m = tones[(0, 2, 1, 2)[k % 4] % len(tones)]
                buses['synth'].add(pluck(m, 0.14, 0.6 + 0.6 * e), t, 0.5 * e * (1.0 if k % 4 == 0 else 0.7), 0.25 * (1 if k % 2 else -1))
            t += beat / 4
            k += 1
    for t0, t1, name in SC.chord_segments():
        e = E(t0 + 0.05)
        if e < 0.6:
            continue
        r, pcs, bass_pc = SC.parse_chord(name)
        m = [x for x in range(26, 38) if x % 12 == bass_pc][0]
        buses['sub'].add(sub_note(m, t1 - t0), t0, clamp((e - 0.55) / 0.35))
    return buses


# ----------------------------------------------------------------------------
# energy shaping, reverb, master
# ----------------------------------------------------------------------------

def shape(buses):
    e = E_ARR
    ramp = lambda x, a, b: np.clip((x - a) / (b - a), 0, 1)
    g = {
        'pad_vln': 0.24 + 0.76 * e,
        'pad_vla': 0.32 + 0.68 * e,
        'pad_vc': 0.42 + 0.58 * e,
        'pad_cb': 0.40 + 0.60 * e,
        'horn_pad': ramp(e, 0.66, 0.9),
        'synth': 0.4 + 0.6 * ramp(e, 0.3, 0.9),
    }
    for k, env in g.items():
        buses[k].x *= env[None, :].astype(np.float32)
    # the pulse ducks behind the 8th-note ostinato only a little; keep it as texture
    buses['synth'].x[:] = sosfilt(sos_lp(5200), buses['synth'].x, axis=1)
    # ping-pong dotted eighth on the pulse
    d = int(0.375 * SR)
    x = buses['synth'].x
    echo = np.zeros_like(x)
    echo[1, d:] += 0.38 * x[0, :-d]
    echo[0, 2 * d:] += 0.3 * x[1, :-2 * d]
    echo[1, 3 * d:] += 0.18 * x[0, :-3 * d]
    buses['synth'].x += echo
    buses['sub'].x[:] = sosfilt(sos_lp(140, 4), buses['sub'].x, axis=1)


def hall_ir(rt60=2.6, length=3.4, seed=11):
    rng = np.random.default_rng(seed)
    n = int(length * SR)
    t = np.arange(n) / SR
    ir = np.zeros((2, n))
    for ch in range(2):
        w = rng.standard_normal(n)
        low = sosfilt(sos_lp(700), w) * np.exp(-6.91 * t / (rt60 * 1.15))
        mid = sosfilt(butter(2, [700, 4000], btype='band', fs=SR, output='sos'), w) * np.exp(-6.91 * t / rt60)
        hi = sosfilt(sos_hp(4000), w) * np.exp(-6.91 * t / (rt60 * 0.5)) * 0.5
        tail = (low + mid + hi) * np.clip(t / 0.08, 0, 1)
        for j in range(16):   # early reflections
            dt = rng.uniform(0.008, 0.07)
            tail[int(dt * SR)] += rng.uniform(-1, 1) * 6.0 * math.exp(-dt / 0.05)
        pre = int(0.022 * SR)
        ir[ch, pre:] = tail[:n - pre]
    ir /= np.sqrt((ir ** 2).sum(1, keepdims=True))
    return ir.astype(np.float32)


def lufs(x):
    import pyloudnorm as pyln
    return pyln.Meter(SR).integrated_loudness(x.T.astype(np.float64))


LEVELS = {  # bus gains (dB) - balanced against short-term loudness at the climaxes, see report()
    'pad_vln': -1.0, 'pad_vla': -3.0, 'pad_vc': -1.5, 'pad_cb': -2.5, 'horn_pad': -5.0,
    'mel_vln': 1.0, 'mel_horn': -1.0, 'ost': -3.0, 'spic_hi': -8.0, 'piano': -1.0, 'harp': -4.0,
    'glock': -6.0, 'timp': -2.0, 'drums': -1.0, 'cym': -8.0, 'synth': -10.0, 'sub': -12.0,
}


def master(mix):
    """air EQ, a slow leveler that narrows the section-to-section range for phone speakers, glue compression"""
    from pedalboard import Compressor, HighShelfFilter, PeakFilter, Pedalboard
    n = int(SC.DUR * SR)
    mix = mix * (10 ** ((-20 - lufs(mix[:, :n])) / 20))
    eq = Pedalboard([PeakFilter(cutoff_frequency_hz=260, gain_db=-1.5, q=0.8),
                     PeakFilter(cutoff_frequency_hz=3000, gain_db=1.0, q=0.9),
                     HighShelfFilter(cutoff_frequency_hz=7000, gain_db=2.5, q=0.7)])
    mix = eq(mix, SR)
    # leveler: 2 s loudness envelope, pull 25 % of each section's deviation back toward the median
    det = sosfilt(sos_hp(120), mix.mean(0))
    env = np.sqrt(uniform_filter1d(det.astype(np.float64) ** 2, int(2.0 * SR)) + 1e-10)
    db = 20 * np.log10(env)
    ref = np.median(db[int(9 * SR):n])
    gain_db = np.clip(-0.25 * (db - ref), -4.0, 5.0)
    gain_db = uniform_filter1d(gain_db, int(1.0 * SR))
    mix = mix * (10 ** (gain_db / 20)).astype(np.float32)[None, :]
    glue = Pedalboard([Compressor(threshold_db=-22, ratio=2.0, attack_ms=30, release_ms=250)])
    return glue(mix.astype(np.float32), SR)


def mixdown(buses):
    ir = hall_ir()
    send = np.zeros((2, N), np.float32)
    dry = np.zeros((2, N), np.float32)
    for k, b in buses.items():
        g = 10 ** (LEVELS[k] / 20)
        dry += b.x * g
        if b.send > 0:
            send += b.x * (g * b.send)
    send = sosfilt(sos_hp(180), send, axis=1).astype(np.float32)
    wet = np.stack([oaconvolve(send[0], ir[0])[:N], oaconvolve(send[1], ir[1])[:N]]).astype(np.float32)
    mix = sosfilt(sos_hp(30), dry + 0.9 * wet, axis=1).astype(np.float32)
    mix = master(mix)
    # final fade with the picture
    fade = np.clip((SC.DUR - TS) / 1.2, 0, 1) ** 1.5
    mix *= fade[None, :]
    return mix.astype(np.float32)


def report(buses):
    """short-term level of each bus in a few windows (for balancing LEVELS)"""
    wins = [('intro', 0.5, 8.0), ('geek', 9, 16), ('2013 peak', 44, 50), ('dark 2015', 51, 59), ('2017 peak', 79, 84),
            ('winter', 129, 140), ('2021 peak', 120, 127), ('2025 peak', 167, 173), ('ending', 189, 194)]
    print(f'{"bus":10s}' + ''.join(f'{w[0]:>11s}' for w in wins))
    for k, b in buses.items():
        g = 10 ** (LEVELS[k] / 20)
        row = []
        for _, a, c in wins:
            seg = b.x[:, int(a * SR):int(c * SR)] * g
            rms = math.sqrt(float((seg.astype(np.float64) ** 2).mean()) + 1e-12)
            row.append(f'{20 * math.log10(rms):11.1f}')
        print(f'{k:10s}' + ''.join(row))


def main():
    t0 = time.time()
    I = load_instruments()
    print(f'instruments loaded in {time.time() - t0:.0f}s', flush=True)
    buses = arrange(I)
    print(f'arranged in {time.time() - t0:.0f}s', flush=True)
    shape(buses)
    report(buses)
    mix = mixdown(buses)
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(WORK, exist_ok=True)
    n = int(SC.DUR * SR)
    peak = float(np.abs(mix[:, :n]).max())
    mix = mix[:, :n] * (0.5 / peak)
    wavfile.write(os.path.join(OUT, 'music.wav'), SR, mix.T.astype(np.float32))
    print(f'music.wav written: {n / SR:.2f}s, integrated {lufs(mix):.1f} LUFS (peak-normalised to -6 dBFS), '
          f'total {time.time() - t0:.0f}s')
    if '--stems' in sys.argv:
        for k, b in buses.items():
            wavfile.write(os.path.join(WORK, f'stem_{k}.wav'), SR, (b.x[:, :n] * 10 ** (LEVELS[k] / 20)).T.astype(np.float32))


if __name__ == '__main__':
    main()
