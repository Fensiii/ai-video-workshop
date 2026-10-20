#!/usr/bin/env python3
"""把成片或参考素材存进仓库：复制、生成缩略拼图、超 95MB 自动压缩、在索引表里追加一行。

  python3 tools/archive.py work <视频> <英文短名> [--src 目录] [--date YYYY-MM-DD] [--note 说明]
  python3 tools/archive.py ref  <视频> <类型/英文短名> [--note 一句话] [--crop W:H:X:Y]
  python3 tools/archive.py thumbs <视频> <输出.jpg>

work → works/<日期>_<短名>/<短名>.mp4 + thumbs.jpg (+ src/)，追加到 works/README.md
ref  → references/<类型>/<短名>.mp4 + 同名 .jpg，追加到 references/README.md 的目录表
风格要点仍需手写进 README 对应小节。
"""
import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIMIT = 95 * 1024 * 1024  # GitHub 单文件上限 100MB，留余量


def probe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=codec_type,width,height,r_frame_rate',
                          '-of', 'json', path], capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    dur = float(j['format']['duration'])
    v = next(s for s in j['streams'] if s['codec_type'] == 'video')
    num, den = (int(x) for x in v['r_frame_rate'].split('/'))
    fps = round(num / den) if den else 0
    return dur, v['width'], v['height'], fps


def mmss(sec):
    sec = int(round(sec))
    return f'{sec // 60}:{sec % 60:02d}'


def thumbs(video, out, crop=None):
    dur = probe(video)[0]
    vf = (f'crop={crop},' if crop else '') + f'fps=12/{dur:.3f},scale=480:-2,tile=4x3'
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', video, '-vf', vf,
                    '-frames:v', '1', '-q:v', '4', out], check=True)


def fit_size(src, dst):
    """复制；超过上限就两遍编码到约 90MB。"""
    if os.path.getsize(src) <= LIMIT:
        shutil.copyfile(src, dst)
        return False
    dur = probe(src)[0]
    vbit = int((86 * 8 * 1024 * 1024) / dur - 192_000)  # 目标约 86MB，噪点多的画面会略超
    log = dst + '.x264'
    common = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', src, '-c:v', 'libx264', '-preset', 'slow',
              '-b:v', str(vbit), '-passlogfile', log]
    subprocess.run(common + ['-pass', '1', '-an', '-f', 'null', '/dev/null'], check=True)
    subprocess.run(common + ['-pass', '2', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
                             '-movflags', '+faststart', dst], check=True)
    for f in os.listdir(os.path.dirname(dst)):
        if f.startswith(os.path.basename(log)):
            os.remove(os.path.join(os.path.dirname(dst), f))
    return True


def append_row(readme, row, anchor_header):
    """在以 anchor_header 开头的表格末尾追加一行。"""
    lines = open(readme, encoding='utf-8').read().split('\n')
    i = next(k for k, l in enumerate(lines) if l.startswith(anchor_header))
    j = i + 2
    while j < len(lines) and lines[j].startswith('|'):
        j += 1
    lines.insert(j, row)
    open(readme, 'w', encoding='utf-8').write('\n'.join(lines))


def cmd_work(a):
    date = a.date or dt.date.today().isoformat()
    d = os.path.join(REPO, 'works', f'{date}_{a.name}')
    os.makedirs(d, exist_ok=True)
    dst = os.path.join(d, f'{a.name}.mp4')
    shrunk = fit_size(a.video, dst)
    thumbs(dst, os.path.join(d, 'thumbs.jpg'))
    if a.src:
        shutil.copytree(a.src, os.path.join(d, 'src'), dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__', 'build', 'out', '*.npz', 'node_modules'))
    dur, w, h, fps = probe(dst)
    rel = os.path.relpath(d, os.path.join(REPO, 'works'))
    readme = os.path.join(REPO, 'works', 'README.md')
    if f'`{rel}/`' not in open(readme, encoding='utf-8').read():
        append_row(readme, f'| `{rel}/` | `{a.name}.mp4` | {mmss(dur)} | {w}×{h} {fps}fps | {a.note or "（待补说明）"} |', '| 目录 |')
    print(f'已存：{os.path.relpath(dst, REPO)}  {mmss(dur)}  {os.path.getsize(dst) / 1e6:.1f}MB' + ('（已压缩）' if shrunk else ''))


def cmd_ref(a):
    cat, name = os.path.split(a.dest)
    d = os.path.join(REPO, 'references', cat)
    os.makedirs(d, exist_ok=True)
    dst = os.path.join(d, f'{name}.mp4')
    shrunk = fit_size(a.video, dst)
    thumbs(dst, os.path.join(d, f'{name}.jpg'), a.crop)
    dur, w, h, _ = probe(dst)
    readme = os.path.join(REPO, 'references', 'README.md')
    key = f'`{cat}/{name}.mp4`'
    if key not in open(readme, encoding='utf-8').read():
        append_row(readme, f'| {key} | {mmss(dur)} | {w}×{h} | {a.note or "（待补一句话）"} |', '| 路径 |')
    print(f'已存：{os.path.relpath(dst, REPO)}  {mmss(dur)}  {os.path.getsize(dst) / 1e6:.1f}MB' + ('（已压缩）' if shrunk else ''))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest='cmd', required=True)
    w = sp.add_parser('work')
    w.add_argument('video'); w.add_argument('name')
    w.add_argument('--src'); w.add_argument('--date'); w.add_argument('--note')
    r = sp.add_parser('ref')
    r.add_argument('video'); r.add_argument('dest')
    r.add_argument('--note'); r.add_argument('--crop')
    t = sp.add_parser('thumbs')
    t.add_argument('video'); t.add_argument('out'); t.add_argument('--crop')
    a = p.parse_args()
    if a.cmd == 'work':
        cmd_work(a)
    elif a.cmd == 'ref':
        cmd_ref(a)
    else:
        thumbs(a.video, a.out, a.crop)


if __name__ == '__main__':
    sys.exit(main())
