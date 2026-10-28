"""Final mix: score (music.wav) + effects (sfx.wav), mastered for YouTube, then muxed with the picture.

Loudness target -14 LUFS integrated, true peak <= -1 dBTP (YouTube's playback reference), via a
look-ahead limiter whose detector runs 4x oversampled. Outputs in ../out/:
  mix.wav                         48 kHz float master
  bitcoin_2010-2026_en_master.mp4 picture stream copied from the CRF-15 render + AAC 384k (for upload)
  bitcoin_2010-2026_en_16x9.mp4   two-pass H.264 under 100 MB (archive copy for the repo)
"""
import math
import os
import subprocess
import sys

import numpy as np
import pyloudnorm as pyln
from scipy.io import wavfile
from scipy.ndimage import maximum_filter1d, minimum_filter1d, uniform_filter1d
from scipy.signal import resample_poly

import btc_common as B

OUT = os.path.join(B.ROOT, 'out')
SR = 48000
SFX_DB = -5.0          # effects sit this far under the score (both stems are at -20 LUFS)
TARGET, CEIL = -14.0, -1.2


def read(name):
    sr, x = wavfile.read(os.path.join(OUT, name))
    assert sr == SR
    scale = 1 / 32768.0 if x.dtype.kind == 'i' else 1.0
    return x.astype(np.float64) * scale


def true_peak_env(x):
    """per-sample true-peak estimate (max over channels, 4x oversampled)"""
    up = resample_poly(x, 4, 1, axis=0)
    a = np.abs(up).max(1)
    return a[:len(x) * 4].reshape(len(x), 4).max(1)


def limit(x, ceil_db):
    ceil = 10 ** (ceil_db / 20)
    pk = maximum_filter1d(true_peak_env(x), int(0.004 * SR))
    g = np.minimum(1.0, ceil / (pk + 1e-12))
    look = int(0.005 * SR)
    g = minimum_filter1d(g, 2 * look + 1)                  # reach full reduction before the peak
    g = uniform_filter1d(g, look)                           # smooth the attack
    rel = np.exp(-1.0 / (0.08 * SR))                        # 80 ms release
    out = np.empty_like(g)
    cur = 1.0
    for i, v in enumerate(g):                               # (plain loop is fine: ~9 M samples once)
        cur = v if v < cur else v + (cur - v) * rel
        out[i] = cur
    return x * out[:, None]


def mix_audio():
    music, sfx = read('music.wav'), read('sfx.wav')
    meter = pyln.Meter(SR)
    n = min(len(music), len(sfx))
    music = music[:n] * 10 ** ((-20 - meter.integrated_loudness(music[:n])) / 20)
    sfx = sfx[:n] * 10 ** ((-20 - meter.integrated_loudness(sfx[:n])) / 20)
    x = music + sfx * 10 ** (SFX_DB / 20)
    gain = 0.0
    for _ in range(4):   # limiting lowers loudness a little; converge on the target
        y = limit(x * 10 ** (gain / 20), CEIL)
        lu = meter.integrated_loudness(y)
        if abs(lu - TARGET) < 0.05:
            break
        gain += TARGET - lu
    tp = 20 * math.log10(true_peak_env(y).max())
    wavfile.write(os.path.join(OUT, 'mix.wav'), SR, y.astype(np.float32))
    print(f'mix: {lu:.2f} LUFS, true peak {tp:.2f} dBTP, makeup {gain:+.1f} dB')


def ff(*args):
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', *args], check=True)


def mux():
    v = os.path.join(OUT, 'video_noaudio.mp4')
    a = os.path.join(OUT, 'mix.wav')
    master = os.path.join(OUT, 'bitcoin_2010-2026_en_master.mp4')
    ff('-i', v, '-i', a, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '384k',
       '-ar', '48000', '-movflags', '+faststart', '-shortest', master)
    # archive copy: two-pass to ~95 MB (GitHub's limit is 100 MB per file)
    arch = os.path.join(OUT, 'bitcoin_2010-2026_en_16x9.mp4')
    vb = int((95e6 * 8 / B.DURATION - 256e3) / 1e3)
    common = ['-c:v', 'libx264', '-preset', 'slow', '-b:v', f'{vb}k', '-maxrate', f'{2 * vb}k', '-bufsize', f'{4 * vb}k',
              '-x264-params', 'aq-mode=3', '-pix_fmt', 'yuv420p', '-colorspace', 'bt709', '-color_primaries', 'bt709',
              '-color_trc', 'bt709']
    log = os.path.join(B.ROOT, 'work', 'x264_2pass')
    ff('-i', v, *common, '-pass', '1', '-passlogfile', log, '-an', '-f', 'mp4', '/dev/null')
    ff('-i', v, '-i', a, '-map', '0:v', '-map', '1:a', *common, '-pass', '2', '-passlogfile', log,
       '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-movflags', '+faststart', '-shortest', arch)
    for p in (master, arch):
        print(os.path.basename(p), f'{os.path.getsize(p) / 1e6:.1f} MB')


if __name__ == '__main__':
    if '--mux-only' not in sys.argv:
        mix_audio()
    if '--audio-only' not in sys.argv:
        mux()
