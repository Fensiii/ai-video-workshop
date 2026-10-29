"""Mix the score under the sound effects and master for YouTube (-14 LUFS, true peak about -1.5 dBTP).

ASSET=eth python3 mix.py  ->  out/<asset>/mix.wav   (needs out/<asset>/music.wav and sfx.wav)
"""
import os

import numpy as np
import pyloudnorm as pyln
from scipy.io import wavfile
from scipy.ndimage import maximum_filter1d, minimum_filter1d, uniform_filter1d
from scipy.signal import butter, sosfilt

import common as B

SR = 48000
MUSIC_LUFS = -16.5     # the score is the backbone ...
SFX_LUFS = -18.0       # ... the effects punctuate it
TARGET_LUFS = -14.0


def load(path):
    sr, x = wavfile.read(path)
    assert sr == SR, (path, sr)
    if x.dtype == np.int16:
        x = x.astype(np.float64) / 32768.0
    return x.astype(np.float64)


def to_lufs(x, target, meter):
    return x * 10 ** ((target - meter.integrated_loudness(x)) / 20)


def duck_env(sfx, depth_db=4.0):
    """music gain that dips under the low-frequency booms of the effects track"""
    low = sosfilt(butter(2, 180, btype='low', fs=SR, output='sos'), sfx.mean(1))
    lvl = np.abs(low)
    att = int(0.005 * SR)
    lvl = maximum_filter1d(lvl, size=att * 2)
    # 350 ms release
    a = np.exp(-1.0 / (0.35 * SR))
    env = np.empty_like(lvl)
    acc = 0.0
    blk = 64
    for i in range(0, len(lvl), blk):
        m = lvl[i:i + blk].max()
        acc = m if m > acc else acc * a ** blk
        env[i:i + blk] = acc
    ref = np.percentile(env[env > 1e-6], 99.5)
    amt = np.clip((20 * np.log10(env / ref + 1e-9) + 14) / 14, 0, 1)
    return 10 ** (-depth_db * amt / 20)


def limiter(x, ceiling=0.84):
    pk = maximum_filter1d(np.max(np.abs(x), axis=1), size=int(0.006 * SR))
    graw = np.minimum(1.0, ceiling / (pk + 1e-9))
    win = int(0.012 * SR)
    g = uniform_filter1d(minimum_filter1d(graw, size=2 * win), size=win)
    return x * np.minimum(g, graw)[:, None]


def main():
    meter = pyln.Meter(SR)
    music = load(os.path.join(B.OUT, 'music.wav'))
    sfx = load(os.path.join(B.OUT, 'sfx.wav'))
    n = min(len(music), len(sfx))
    music, sfx = music[:n], sfx[:n]
    music = to_lufs(music, MUSIC_LUFS, meter)
    sfx = to_lufs(sfx, SFX_LUFS, meter)
    mix = music * duck_env(sfx)[:, None] + sfx
    for _ in range(3):                      # limiter changes loudness a little: converge
        mix = to_lufs(mix, TARGET_LUFS, meter)
        mix = limiter(mix)
    fade = np.clip((n / SR - np.arange(n) / SR) / 0.8, 0, 1)
    mix *= fade[:, None]
    path = os.path.join(B.OUT, 'mix.wav')
    wavfile.write(path, SR, (np.clip(mix, -1, 1) * 32767).astype(np.int16))
    print('wrote', path, 'LUFS', round(meter.integrated_loudness(mix), 2), 'peak dBFS',
          round(20 * np.log10(np.abs(mix).max()), 2))


if __name__ == '__main__':
    main()
