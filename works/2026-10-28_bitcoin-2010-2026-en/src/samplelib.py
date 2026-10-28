"""Sample-based instruments for the score: VSCO 2 CE (CC0) strings/brass/percussion + Salamander piano.

VSCO file names put middle C at C3, so their pitched instruments get offset=+12
(checked by pitch detection: every string/horn/bass sample measures exactly 12 semitones above its name).
"""
import glob
import math
import os
import re
from fractions import Fraction

import numpy as np
from pedalboard.io import AudioFile
from scipy.signal import resample_poly

SR = 48000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SDIR = os.path.join(ROOT, 'samples')
_PC = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}


def midi_of(name):
    """'C4' -> 60, 'F#3' -> 54"""
    m = re.fullmatch(r'([A-G]#?)(-?\d)', name)
    return 12 * (int(m.group(2)) + 1) + _PC[m.group(1)]


def load_audio(path):
    """stereo float32 at SR, leading silence trimmed to just before the onset"""
    with AudioFile(path) as f:
        sr = f.samplerate
        x = f.read(f.frames)
    if x.shape[0] == 1:
        x = np.vstack([x, x])
    x = x[:2].astype(np.float64)
    if sr != SR:
        g = math.gcd(SR, int(sr))
        x = resample_poly(x, SR // g, int(sr) // g, axis=1)
    env = np.abs(x).max(0)
    i = int(np.argmax(env > env.max() * 0.02))
    x = x[:, max(0, i - int(0.003 * SR)):]
    return x.astype(np.float32)


def _rms_peak(x, win=0.4):
    n = int(win * SR)
    m = x.mean(0) ** 2
    if len(m) <= n:
        return math.sqrt(m.mean() + 1e-12)
    c = np.cumsum(m)
    return math.sqrt(max((c[n:] - c[:-n]).max() / n, 1e-12))


def shift(x, semis):
    """pitch shift by resampling (changes duration, like a classic sampler)"""
    if abs(semis) < 1e-6:
        return x
    fr = Fraction(2 ** (-semis / 12)).limit_denominator(240)
    return resample_poly(x, fr.numerator, fr.denominator, axis=1).astype(np.float32)


class Instrument:
    """pitched sampler: zones[layer] = sorted list of (root midi, [round-robin arrays])"""

    def __init__(self, pattern, rx, offset=0, max_len=None, layers=None, gain=1.0, norm=True):
        self.zones = {}
        self.gain = gain
        self._cache = {}
        self._rr = {}
        for p in sorted(glob.glob(os.path.join(SDIR, pattern))):
            m = re.search(rx, os.path.basename(p))
            if not m:
                continue
            lay = m.groupdict().get('layer') or '0'
            if layers is not None and lay not in layers:
                continue
            x = load_audio(p)
            if max_len:
                x = x[:, :int(max_len * SR)]
            if norm:
                x = x * (0.25 / _rms_peak(x))
            root = midi_of(m.group('note')) + offset
            z = self.zones.setdefault(lay, {})
            z.setdefault(root, []).append(x)
        assert self.zones, pattern
        self.layer_names = sorted(self.zones, key=lambda s: int(re.sub(r'\D', '', s) or 0))  # soft -> loud

    def roots(self, layer):
        return sorted(self.zones[layer])

    def pick(self, midi, layer):
        """(layer, root): stay near the asked layer but never stretch a sample far - some layers
        only cover part of the range (horn v3/v4 stop at C4)"""
        want = self.layer_names.index(layer)
        best = None
        for li, lay in enumerate(self.layer_names):
            for r in self.zones[lay]:
                cost = abs(r - midi) + 1.5 * abs(li - want) + (0.1 if r < midi else 0.0)
                if best is None or cost < best[0]:
                    best = (cost, lay, r)
        return best[1], best[2]

    def sample(self, midi, layer, rr=None):
        layer, root = self.pick(midi, layer)
        variants = self.zones[layer][root]
        if rr is None:
            k = (layer, root)
            rr = self._rr.get(k, 0)
            self._rr[k] = rr + 1
        key = (layer, root, rr % len(variants), midi)
        y = self._cache.get(key)
        if y is None:
            y = shift(variants[rr % len(variants)], midi - root)
            self._cache[key] = y
        return y

    def note(self, midi, vel=0.7, dur=None, attack=0.0, release=0.35, layer=None, rr=None, offset=0.0):
        """stereo note; dur=None lets the sample ring out. offset skips into the sample (s)."""
        if layer is None:
            k = min(int(vel * len(self.layer_names)), len(self.layer_names) - 1)
            layer = self.layer_names[k]
        y = self.sample(midi, layer, rr)
        if offset > 0:
            y = y[:, int(offset * SR):]
            attack = max(attack, 0.008)   # entering mid-waveform: fade in to avoid a click
        n = y.shape[1]
        if dur is not None:
            n = min(n, int((dur + release) * SR))
        out = y[:, :n] * (self.gain * (0.18 + 0.82 * vel ** 1.6))
        if attack > 0:
            na = min(int(attack * SR), n)
            out[:, :na] *= np.linspace(0, 1, na) ** 2
        if dur is not None:
            r0 = int(dur * SR)
            if r0 < n:
                tail = n - r0
                out[:, r0:] *= np.exp(-np.arange(tail) / (release * SR / 4.0))
        fade = min(int(0.02 * SR), n)
        out[:, n - fade:] *= np.linspace(1, 0, fade)
        return out


class OneShot:
    """unpitched one-shots (drums, cymbals); pick by name with optional pitch shift"""

    def __init__(self, files, gain=1.0):
        self.s = {}
        self.gain = gain
        for k, rel in files.items():
            x = load_audio(os.path.join(SDIR, rel))
            self.s[k] = x
        self._cache = {}

    def hit(self, name, vel=1.0, semis=0.0, dur=None, release=0.3):
        key = (name, round(semis, 3))
        y = self._cache.get(key)
        if y is None:
            y = shift(self.s[name], semis)
            self._cache[key] = y
        out = y * (self.gain * vel)
        if dur is not None:
            r0 = int(dur * SR)
            if r0 < out.shape[1]:
                out = out[:, :r0 + int(release * SR)].copy()
                tail = out.shape[1] - r0
                out[:, r0:] *= np.exp(-np.arange(tail) / (release * SR / 4.0))
        return out
