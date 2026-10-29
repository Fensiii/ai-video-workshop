"""Mix, mux and encode the deliverables after run_render.py, audio.py and music.py.

  out/mix.wav                      sound effects + score; the score ducks under big hits
  out/audio_norm.wav               the mix at -14 LUFS / -1.5 dBTP (YouTube reference loudness)
  out/nvidia_1999-2026_16x9.mp4    two-pass H.264, sized to stay under GitHub's 100 MB limit
  out/thumbs.jpg                   12 evenly spaced frames, tile=4x3

    python3 finalize.py [--hq]     # --hq also writes a CRF 17 master for uploading from a computer
    python3 finalize.py --audio    # only redo the audio and swap it into the existing mp4
"""
import json
import os
import subprocess
import sys

import numpy as np
from scipy.io import wavfile
from scipy.ndimage import maximum_filter1d, uniform_filter1d

import nvda_common as B

OUT = os.path.join(B.ROOT, 'out')
VID = os.path.join(OUT, 'video_noaudio.mp4')
SFX = os.path.join(OUT, 'sfx.wav')
MUSIC = os.path.join(OUT, 'music.wav')
MIX = os.path.join(OUT, 'mix.wav')
NORM = os.path.join(OUT, 'audio_norm.wav')
MUSIC_VS_SFX_DB = -1.0   # score loudness relative to the effects
DUCK_DB = 6.0
FINAL = os.path.join(OUT, 'nvidia_1999-2026_16x9.mp4')
TARGET_MB = 88.0
AUDIO_K = 192
COLOR = ['-pix_fmt', 'yuv420p', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709']


def run(cmd, **kw):
    print('+', ' '.join(cmd[:12]), '...' if len(cmd) > 12 else '')
    return subprocess.run(cmd, check=True, **kw)


def lufs(path):
    p = run(['ffmpeg', '-hide_banner', '-nostats', '-i', path, '-af', 'ebur128', '-f', 'null', '-'],
            capture_output=True, text=True)
    tail = p.stderr[p.stderr.rindex('Summary:'):]
    return float(tail.split('I:')[1].split('LUFS')[0])


def mix():
    sr, sfx = wavfile.read(SFX)
    _, mus = wavfile.read(MUSIC)
    sfx = sfx.astype(np.float32) / 32768
    mus = mus.astype(np.float32) / 32768
    n = min(len(sfx), len(mus))
    sfx, mus = sfx[:n], mus[:n]
    g = 10 ** ((lufs(SFX) + MUSIC_VS_SFX_DB - lufs(MUSIC)) / 20)
    env = uniform_filter1d(maximum_filter1d(np.abs(sfx).max(1), size=int(0.02 * sr)), size=int(0.25 * sr))
    lo, hi = np.percentile(env, 50), np.percentile(env, 99.5)
    duck = 10 ** (-DUCK_DB * np.clip((env - lo) / (hi - lo), 0, 1) / 20)
    out = sfx + mus * (g * duck)[:, None]
    wavfile.write(MIX, sr, out.astype(np.float32))
    print(f'music gain {20 * np.log10(g):+.1f} dB, ducking up to {DUCK_DB} dB')


def loudnorm():
    flt = 'loudnorm=I=-14:TP=-1.5:LRA=11'
    p = run(['ffmpeg', '-hide_banner', '-nostats', '-i', MIX, '-af', flt + ':print_format=json', '-f', 'null', '-'],
            capture_output=True, text=True)
    js = json.loads(p.stderr[p.stderr.rindex('{'):p.stderr.rindex('}') + 1])
    flt2 = (f"{flt}:measured_I={js['input_i']}:measured_TP={js['input_tp']}:measured_LRA={js['input_lra']}"
            f":measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true")
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', MIX, '-af', flt2, '-ar', '48000', NORM])


def swap_audio():
    tmp = FINAL + '.tmp.mp4'
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', FINAL, '-i', NORM, '-map', '0:v', '-map', '1:a',
         '-c:v', 'copy', '-c:a', 'aac', '-b:a', f'{AUDIO_K}k', '-shortest', '-movflags', '+faststart', tmp])
    os.replace(tmp, FINAL)
    print('audio swapped ->', FINAL, f'{os.path.getsize(FINAL) / 1e6:.1f} MB')


def encode_final():
    dur = B.NFRAMES / B.FPS
    vk = int(TARGET_MB * 8e6 / dur / 1000) - AUDIO_K - 8
    log = os.path.join(OUT, 'x264pass')
    common = ['-c:v', 'libx264', '-preset', 'slow', '-b:v', f'{vk}k', '-maxrate', f'{int(vk * 1.8)}k',
              '-bufsize', f'{vk * 3}k', '-passlogfile', log] + COLOR
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', VID] + common + ['-pass', '1', '-an', '-f', 'null', '/dev/null'])
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', VID, '-i', NORM] + common +
        ['-pass', '2', '-c:a', 'aac', '-b:a', f'{AUDIO_K}k', '-shortest', '-movflags', '+faststart', FINAL])
    print(f'video {vk} kbps ->', FINAL, f'{os.path.getsize(FINAL) / 1e6:.1f} MB')


def encode_hq():
    hq = os.path.join(OUT, 'nvidia_1999-2026_16x9_HQ.mp4')
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', VID, '-i', NORM, '-c:v', 'libx264', '-preset', 'slow',
         '-crf', '17'] + COLOR + ['-c:a', 'aac', '-b:a', '320k', '-shortest', '-movflags', '+faststart', hq])
    print('hq ->', hq, f'{os.path.getsize(hq) / 1e6:.1f} MB')


def thumbs():
    dur = B.NFRAMES / B.FPS
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', FINAL, '-vf',
         f'fps=12/{dur:.3f},scale=480:270,tile=4x3', '-frames:v', '1', '-q:v', '3', os.path.join(OUT, 'thumbs.jpg')])


if __name__ == '__main__':
    mix()
    loudnorm()
    if '--audio' in sys.argv:
        swap_audio()
        sys.exit(0)
    encode_final()
    thumbs()
    if '--hq' in sys.argv:
        encode_hq()
