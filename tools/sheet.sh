#!/usr/bin/env bash
# 逐段拆片：每 STEP 秒一帧、带时间戳，每张 3x3 拼图（小尺寸省 token）。
# 用法：tools/sheet.sh in.mp4 out_dir [STEP=1] [起始秒=0] [时长=全片] [格宽=426]
in=$1; od=$2; step=${3:-1}; ss=${4:-0}; dur=${5:-}; w=${6:-426}
mkdir -p "$od"
ffmpeg -hide_banner -loglevel error -y -ss "$ss" ${dur:+-t "$dur"} -i "$in" \
  -vf "fps=1/$step,scale=$w:-2,setpts=PTS+$ss/TB,drawtext=text='%{pts\:hms}':x=6:y=6:fontsize=18:fontcolor=white:box=1:boxcolor=black@0.6,tile=3x3" \
  -q:v 5 "$od/sheet_%03d.jpg"
echo "$(ls "$od"/sheet_*.jpg | wc -l) 张拼图 → $od（每张 9 格、间隔 ${step}s）"
