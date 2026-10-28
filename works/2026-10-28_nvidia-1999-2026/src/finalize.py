"""Mux and encode the deliverables after run_render.py and audio.py.

  out/sfx_norm.wav                 sound effects at -14 LUFS / -1.5 dBTP (YouTube reference loudness)
  out/nvidia_1999-2026_16x9.mp4    two-pass H.264, sized to stay under GitHub's 100 MB limit
  out/thumbs.jpg                   12 evenly spaced frames, tile=4x3

    python3 finalize.py [--hq]     # --hq also writes a CRF 17 master for uploading from a computer
"""
import json
import os
import subprocess
import sys

import nvda_common as B

OUT = os.path.join(B.ROOT, 'out')
VID = os.path.join(OUT, 'video_noaudio.mp4')
SFX = os.path.join(OUT, 'sfx.wav')
NORM = os.path.join(OUT, 'sfx_norm.wav')
FINAL = os.path.join(OUT, 'nvidia_1999-2026_16x9.mp4')
TARGET_MB = 88.0
AUDIO_K = 192
COLOR = ['-pix_fmt', 'yuv420p', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709']


def run(cmd, **kw):
    print('+', ' '.join(cmd[:12]), '...' if len(cmd) > 12 else '')
    return subprocess.run(cmd, check=True, **kw)


def loudnorm():
    flt = 'loudnorm=I=-14:TP=-1.5:LRA=11'
    p = run(['ffmpeg', '-hide_banner', '-nostats', '-i', SFX, '-af', flt + ':print_format=json', '-f', 'null', '-'],
            capture_output=True, text=True)
    js = json.loads(p.stderr[p.stderr.rindex('{'):p.stderr.rindex('}') + 1])
    flt2 = (f"{flt}:measured_I={js['input_i']}:measured_TP={js['input_tp']}:measured_LRA={js['input_lra']}"
            f":measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true")
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', SFX, '-af', flt2, '-ar', '48000', NORM])


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
    loudnorm()
    encode_final()
    thumbs()
    if '--hq' in sys.argv:
        encode_hq()
