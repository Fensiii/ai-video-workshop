#!/usr/bin/env bash
# 全片均匀取 N 帧拼一张图（默认 12 帧 4x3、每格 480 宽），用于存档 thumbs.jpg 和快速看风格。
# 用法：tools/thumbs.sh in.mp4 out.jpg [列 行 格宽] [--ts]   --ts 在每格左上角打时间戳（拆参考用）
in=$1; out=$2; c=${3:-4}; r=${4:-3}; w=${5:-480}
n=$((c * r))
d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$in")
ts=""; [[ " $* " == *" --ts "* ]] && ts=",drawtext=text='%{pts\:hms}':x=8:y=8:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.6"
ffmpeg -hide_banner -loglevel error -y -i "$in" \
  -vf "fps=$n/$d,scale=$w:-2,setpts=N/($n/$d)/TB$ts,tile=${c}x${r}" -frames:v 1 -q:v 4 "$out"
echo "$out ($n 帧, ${d%.*}s)"
