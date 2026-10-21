"""七美德流星 并行渲染：splits the timeline into chunks, each encoded by its own ffmpeg."""
import multiprocessing as mp
import os
import subprocess
import sys
import time

import numpy as np

import virtues as B
import render as R

OUT = os.path.join(B.ROOT, 'work', 'out')
PREFIX = os.environ.get('SEG_PREFIX', 'seg_')
os.makedirs(OUT, exist_ok=True)


def work(args):
    ci, f0, f1 = args
    path = os.path.join(OUT, f'{PREFIX}{ci:02d}.mp4')
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
           '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{B.W}x{B.H}', '-r', str(B.FPS), '-i', '-',
           '-c:v', 'libx264', '-preset', 'medium', '-crf', '15', '-threads', '2',
           '-pix_fmt', 'yuv420p', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
           '-movflags', '+faststart', path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    arr = np.zeros((B.H, B.W, 4), np.uint8)
    t0 = time.time()
    for fi in range(f0, f1):
        arr[:] = 0
        R.render_frame(fi, arr)
        p.stdin.write(arr.tobytes())
    p.stdin.close()
    p.wait()
    return ci, f1 - f0, time.time() - t0


if __name__ == '__main__':
    nchunks = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    f_start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    f_end = int(sys.argv[3]) if len(sys.argv) > 3 else B.NFRAMES
    edges = np.linspace(f_start, f_end, nchunks + 1).astype(int)
    jobs = [(i, edges[i], edges[i + 1]) for i in range(nchunks)]
    t0 = time.time()
    with mp.get_context('fork').Pool(4) as pool:
        for ci, n, dt in pool.imap_unordered(work, jobs):
            print(f'chunk {ci} done: {n} frames in {dt:.0f}s ({dt / max(n, 1):.2f}s/f)  elapsed {time.time() - t0:.0f}s', flush=True)
    if PREFIX != 'seg_':
        sys.exit(0)
    with open(os.path.join(OUT, 'segs.txt'), 'w') as f:
        for i in range(nchunks):
            f.write(f"file 'seg_{i:02d}.mp4'\n")
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0',
                    '-i', os.path.join(OUT, 'segs.txt'), '-c', 'copy', os.path.join(OUT, 'video_noaudio.mp4')], check=True)
    print('total', time.time() - t0)
