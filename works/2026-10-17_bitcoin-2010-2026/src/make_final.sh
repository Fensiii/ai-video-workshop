#!/usr/bin/env bash
# 全片出片：并行渲染画面 → 合成音效 → 两遍编码到约 90MB（GitHub 单文件上限 100MB）
set -euo pipefail
cd "$(dirname "$0")"
B=../build
python3 run_render.py "${CHUNKS:-16}"
python3 audio.py
ffmpeg -hide_banner -loglevel error -y -i $B/video_noaudio.mp4 -c:v libx264 -preset slow -b:v 3500k \
  -pass 1 -passlogfile $B/x264 -an -f null /dev/null
ffmpeg -hide_banner -loglevel error -y -i $B/video_noaudio.mp4 -i $B/sfx.wav -map 0:v -map 1:a \
  -c:v libx264 -preset slow -b:v 3500k -maxrate 9000k -bufsize 14000k -pass 2 -passlogfile $B/x264 \
  -profile:v high -pix_fmt yuv420p -colorspace bt709 -color_primaries bt709 -color_trc bt709 \
  -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart $B/final.mp4
rm -f $B/x264*
ls -la $B/final.mp4
