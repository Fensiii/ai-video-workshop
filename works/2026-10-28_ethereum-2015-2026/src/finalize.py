"""Sound + final file: SFX, original score, mix/master to -14 LUFS, then the MP4.

ASSET=eth python3 finalize.py OUTPUT.mp4 [target_MB] [--reuse-video ENCODED.mp4]

With --reuse-video the picture is copied from an already encoded file (no re-encode); otherwise
out/<asset>/video_noaudio.mp4 is two-pass encoded so the whole file stays under target_MB.
"""
import os
import subprocess
import sys

import common as B

OUT = B.OUT
HERE = os.path.dirname(os.path.abspath(__file__))


def run(cmd, **kw):
    print('+', ' '.join(cmd), flush=True)
    return subprocess.run(cmd, check=True, **kw)


def main():
    args = sys.argv[1:]
    reuse = None
    if '--reuse-video' in args:
        i = args.index('--reuse-video')
        reuse = args[i + 1]
        del args[i:i + 2]
    final = args[0]
    target_mb = float(args[1]) if len(args) > 1 else 95.0
    for script in ('audio.py', 'music.py', 'mix.py'):
        run([sys.executable, os.path.join(HERE, script)])
    mix = os.path.join(OUT, 'mix.wav')
    a_kbps = 192
    audio = ['-c:a', 'aac', '-b:a', f'{a_kbps}k', '-ar', '48000']
    if reuse:
        run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', reuse, '-i', mix,
             '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy'] + audio + ['-movflags', '+faststart', final])
    else:
        video = os.path.join(OUT, 'video_noaudio.mp4')
        v_kbps = int(target_mb * 8e3 / B.DURATION - a_kbps - 40)   # 40 kbps container headroom
        print('video bitrate', v_kbps, 'kbps', flush=True)
        enc = ['-c:v', 'libx264', '-preset', 'slow', '-b:v', f'{v_kbps}k', '-maxrate', f'{int(v_kbps * 1.8)}k',
               '-bufsize', f'{int(v_kbps * 3)}k', '-x264-params', 'aq-mode=3', '-pix_fmt', 'yuv420p',
               '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-r', str(B.FPS)]
        log = os.path.join(OUT, 'x264pass')
        run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', video] + enc +
            ['-pass', '1', '-passlogfile', log, '-an', '-f', 'mp4', '/dev/null'])
        run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', video, '-i', mix] + enc +
            ['-pass', '2', '-passlogfile', log] + audio +
            ['-map', '0:v:0', '-map', '1:a:0', '-movflags', '+faststart', final])
    size = os.path.getsize(final) / 1e6
    print(f'final {final}: {size:.1f} MB', flush=True)
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', final, '-filter_complex', 'ebur128=peak=true',
                        '-f', 'null', '-'], capture_output=True, text=True)
    print(r.stderr[r.stderr.rindex('Summary:'):], flush=True)


if __name__ == '__main__':
    main()
