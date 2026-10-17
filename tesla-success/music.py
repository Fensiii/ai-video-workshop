"""Synthesize the background score from story.json timing -> build/music.wav (no samples needed)."""
import json, os
import numpy as np, soundfile as sf

SR = 44100
story = json.load(open("story.json", encoding="utf-8"))
DUR = story["duration"]
N = int(DUR * SR)
t_all = np.arange(N) / SR
rng = np.random.default_rng(7)
L = np.zeros(N); R = np.zeros(N)

BEAT = 60 / 100
# Dm - Bb - F - C, two bars each
CHORDS = [[50, 53, 57, 62], [46, 50, 53, 58], [53, 57, 60, 65], [48, 52, 55, 60]]
hz = lambda m: 440 * 2 ** ((m - 69) / 12)


def add(sig, start, gain=1.0, pan=0.0):
    i = int(start * SR)
    if i >= N: return
    sig = sig[: N - i] * gain
    L[i:i + len(sig)] += sig * (1 - max(pan, 0))
    R[i:i + len(sig)] += sig * (1 + min(pan, 0))


def env(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(t / max(a, 1e-4), 1) * np.exp(-t / d)


def lowpass(x, cutoff):
    # one-pole low-pass; cutoff may be an array (sweeps)
    a = np.exp(-2 * np.pi * np.broadcast_to(cutoff, x.shape) / SR)
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc = (1 - a[i]) * x[i] + a[i] * acc
        y[i] = acc
    return y


def intensity(t):
    """0..1 energy curve for the bed (pad/arp/bass/kick)."""
    pts = [(0, 0), (3.2, 1), (8.3, 1), (8.5, 0), (13.6, 0), (14, .55), (18.2, .35), (30.5, .5), (52.5, .55),
           (67, .65), (88, .75), (107.5, .6), (117.5, .8), (127.2, 1), (135.5, 1), (136, .25), (147.5, .4),
           (150, .7), (154, .5), (158, 0)]
    xs, ys = zip(*pts)
    return np.interp(t, xs, ys)


# ---------- pad ----------
bar = 4 * BEAT
for k in range(int(DUR / (2 * bar)) + 1):
    start = k * 2 * bar
    chord = CHORDS[k % 4]
    n = int(2 * bar * SR * 1.15)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for m in chord:
        for det in (-0.09, 0.0, 0.11):
            f = hz(m) * 2 ** (det / 12)
            sig += np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t + 1)
    sig /= len(chord) * 3
    sig *= np.minimum(t / 0.8, 1) * np.minimum((n / SR - t) / 0.8, 1)
    add(sig, start, 0.20)

# ---------- arpeggio plucks (8ths) + bass pulse + kick ----------
step = BEAT / 2
for j in range(int(DUR / step)):
    t0 = j * step
    e = float(intensity(t0))
    chord = CHORDS[int(t0 / (2 * bar)) % 4]
    if e > 0.3:
        m = chord[[0, 1, 2, 3, 2, 1, 3, 2][j % 8]] + 12
        n = int(0.9 * SR); t = np.arange(n) / SR
        p = (np.sin(2 * np.pi * hz(m) * t) + .35 * np.sin(4 * np.pi * hz(m) * t)) * env(n, .004, .28)
        add(p, t0, 0.10 * e, pan=0.35 * np.sin(j * 1.3))
    if e > 0.6:
        n = int(step * SR); t = np.arange(n) / SR
        b = np.tanh(2.2 * np.sin(2 * np.pi * hz(chord[0] - 24) * t)) * env(n, .005, .18)
        add(b, t0, 0.16 * e)
    if e > 0.85 and j % 2 == 0:
        n = int(0.4 * SR); t = np.arange(n) / SR
        f = 45 + 90 * np.exp(-t / .03)
        kick = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .001, .12)
        add(kick, t0, 0.55 * e)
    if e > 0.9 and j % 4 == 2:
        n = int(0.25 * SR)
        add(rng.standard_normal(n) * env(n, .001, .05), t0, 0.08)

# ---------- opening riser 0 -> 3.2s, and tension 8.9 -> 13.6 ----------
def riser(t0, t1, gain):
    n = int((t1 - t0) * SR); t = np.arange(n) / SR; x = t / t[-1]
    noise = lowpass(rng.standard_normal(n), 200 + 7000 * x ** 2)
    tone = np.sin(2 * np.pi * np.cumsum(110 + 500 * x ** 2) / SR)
    add((noise * .8 + tone * .4) * x ** 2, t0, gain)

riser(0.0, 3.2, 0.5)
riser(11.6, 13.6, 0.35)

# heartbeat during the "差点活不过" beat
for k, t0 in enumerate(np.arange(9.0, 13.4, 0.85)):
    for off, g in ((0, 1), (0.18, .6)):
        n = int(0.3 * SR); t = np.arange(n) / SR
        add(np.sin(2 * np.pi * 48 * t) * env(n, .004, .09), t0 + off, 0.5 * g)
# lonely high drone
n = int(4.6 * SR); t = np.arange(n) / SR
add(np.sin(2 * np.pi * hz(86) * t) * np.minimum(t / .5, 1) * np.minimum((4.6 - t) / 1, 1), 8.9, 0.035)

# ---------- impacts / whooshes ----------
big = {3.2, 13.6, 127.2, 147.5}
for h in story["hits"]:
    if h in big:
        n = int(2.5 * SR); t = np.arange(n) / SR
        f = 32 + 60 * np.exp(-t / .08)
        boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .002, .7)
        crash = lowpass(rng.standard_normal(n), 5000) * env(n, .001, .35)
        add(np.tanh(1.5 * boom) + .5 * crash, h, 0.75)
    else:
        n = int(1.2 * SR); t = np.arange(n) / SR; x = t / t[-1]
        w = lowpass(rng.standard_normal(n), 300 + 3000 * np.sin(np.pi * x)) * np.sin(np.pi * x) ** 2
        add(w, h - 0.6, 0.35)

# ---------- ending: sparse piano notes 136-147 ----------
for k, (t0, m) in enumerate([(136.4, 74), (137.6, 69), (138.8, 72), (140.6, 70), (141.8, 65), (143, 69), (144.2, 67), (145.4, 62)]):
    n = int(3 * SR); t = np.arange(n) / SR; f = hz(m)
    p = sum(np.sin(2 * np.pi * f * h * t) / h ** 1.5 for h in (1, 2, 3, 4)) * env(n, .003, .9)
    add(p, t0, 0.13, pan=.2 * (-1) ** k)

# ---------- reverb (FFT convolution with decaying noise) ----------
def reverb(x, seed):
    r = np.random.default_rng(seed)
    n = int(2.8 * SR)
    ir = r.standard_normal(n) * np.exp(-np.arange(n) / SR / .7)
    ir[0] = 0
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    y = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[: len(x)]
    return y / np.max(np.abs(ir)) * .03

L, R = L + reverb(L, 1), R + reverb(R, 2)
fade = np.minimum(1, (DUR - t_all) / 4)
mix = np.stack([L, R], 1) * fade[:, None]
mix = np.tanh(mix / np.max(np.abs(mix)) * 1.4) * .89
os.makedirs("build", exist_ok=True)
sf.write("build/music.wav", mix.astype(np.float32), SR)
print("wrote build/music.wav", DUR, "s")
