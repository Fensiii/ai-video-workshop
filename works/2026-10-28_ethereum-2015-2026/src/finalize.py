"""Sound + final encode: synth SFX, normalise to YouTube loudness, mux and two-pass encode under ~95 MB.

ASSET=eth python3 finalize.py OUTPUT.mp4 [target_MB]
"""
import json
import os
import subprocess
import sys

import common as B

OUT = B.OUT


def run(cmd, **kw):
    print('+', ' '.join(cmd), flush=True)
    return subprocess.run(cmd, check=True, **kw)


def loudnorm(src, dst, target=-14.0, tp=-1.5):
    """two-pass EBU R128 normalisation (linear when possible)"""
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', src, '-af',
                        f'loudnorm=I={target}:TP={tp}:LRA=11:print_format=json', '-f', 'null', '-'],
                       capture_output=True, text=True)
    js = r.stderr[r.stderr.rindex('{'):r.stderr.rindex('}') + 1]
    m = json.loads(js)
    print('measured', {k: m[k] for k in ('input_i', 'input_tp', 'input_lra', 'input_thresh')}, flush=True)
    if abs(float(m['input_i']) - target) <= 0.6 and float(m['input_tp']) <= tp + 0.5:
        run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', src, '-ar', '48000', dst])
        return
    af = (f"loudnorm=I={target}:TP={tp}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:"
          f"linear=true:print_format=summary")
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', src, '-af', af, '-ar', '48000', dst])


def main():
    final = sys.argv[1]
    target_mb = float(sys.argv[2]) if len(sys.argv) > 2 else 95.0
    video = os.path.join(OUT, 'video_noaudio.mp4')
    sfx = os.path.join(OUT, 'sfx.wav')
    sfx_yt = os.path.join(OUT, 'sfx_yt.wav')
    run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audio.py')])
    loudnorm(sfx, sfx_yt)
    a_kbps = 192
    v_kbps = int(target_mb * 8e3 / B.DURATION - a_kbps - 40)   # 40 kbps container headroom
    print('video bitrate', v_kbps, 'kbps', flush=True)
    common = ['-c:v', 'libx264', '-preset', 'slow', '-b:v', f'{v_kbps}k', '-maxrate', f'{int(v_kbps * 1.8)}k',
              '-bufsize', f'{int(v_kbps * 3)}k', '-x264-params', 'aq-mode=3', '-pix_fmt', 'yuv420p',
              '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-r', str(B.FPS)]
    log = os.path.join(OUT, 'x264pass')
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', video] + common +
        ['-pass', '1', '-passlogfile', log, '-an', '-f', 'mp4', '/dev/null'])
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', video, '-i', sfx_yt] + common +
        ['-pass', '2', '-passlogfile', log, '-c:a', 'aac', '-b:a', f'{a_kbps}k', '-ar', '48000',
         '-map', '0:v:0', '-map', '1:a:0', '-shortest', '-movflags', '+faststart', final])
    size = os.path.getsize(final) / 1e6
    print(f'final {final}: {size:.1f} MB', flush=True)
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', final, '-filter_complex', 'ebur128=peak=true',
                        '-f', 'null', '-'], capture_output=True, text=True)
    print(r.stderr[r.stderr.rindex('Summary:'):], flush=True)


if __name__ == '__main__':
    main()
