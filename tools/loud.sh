#!/usr/bin/env bash
# 一行响度摘要（目标约 -16 LUFS，真峰值 ≤ -1 dB）。用法：tools/loud.sh a.mp4
ffmpeg -hide_banner -nostats -i "$1" -af ebur128=peak=true -f null - 2>&1 \
  | awk '/Integrated/{getline; i=$2} /LRA:/{l=$2} /True peak:/{getline; p=$2} END{print "I="i" LUFS  LRA="l" LU  TP="p" dBFS"}'
