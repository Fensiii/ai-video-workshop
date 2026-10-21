#!/usr/bin/env bash
# 一键出片：渲染画面 → 合成音频 → 响度统一 → 合并。需先准备 skia-python、字体（~/fonts，Noto Sans SC + Inter）与 libEGL。
set -e
cd "$(dirname "$0")/.."
python3 src/run_render.py 8
python3 src/audio.py
ffmpeg -v error -y -i work/audio_raw.wav -af loudnorm=I=-16:TP=-1.5:LRA=11 -ar 48000 work/audio.wav
ffmpeg -v error -y -i work/out/video_noaudio.mp4 -i work/audio.wav -c:v copy -c:a aac -b:a 192k -shortest \
  -movflags +faststart seven-virtues-meteors_16x9.mp4
