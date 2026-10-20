#!/usr/bin/env bash
# 每个视频一行规格摘要：时长 分辨率 帧率 视频码率 音频 体积。用法：tools/probe.sh a.mp4 [b.mp4 ...]
for f in "$@"; do
  v=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,codec_name -of csv=p=0 "$f" | sed "s/,*$//")
  a=$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name,sample_rate,channels -of csv=p=0 "$f" | sed "s/,*$//")
  d=$(ffprobe -v error -show_entries format=duration,bit_rate -of csv=p=0 "$f" | sed "s/,*$//")
  printf '%s | dur=%.1fs br=%dk | v=%s | a=%s | %s\n' "$f" "${d%,*}" "$(( ${d#*,} / 1000 ))" "$v" "${a:-无}" "$(du -h "$f" | cut -f1)"
done
