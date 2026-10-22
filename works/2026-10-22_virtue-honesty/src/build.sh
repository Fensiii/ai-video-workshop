#!/bin/bash
# 用法：bash build.sh <virtue> <输出目录>   —— 4 路并行渲染 → 拼接 → 合成音频 → 混音 → 缩略拼图
set -e
V=$1; OUT=$(realpath $2); SRC=$(cd $(dirname $0) && pwd)
TMP=$(mktemp -d); export NODE_PATH=$(npm root -g)
for i in 0 1 2 3; do VIRTUE=$V node $SRC/render.js seg $TMP/s$i.mp4 $((i*189)) $(((i+1)*189)) > $TMP/log$i.txt 2>&1 & done; wait
printf "file s0.mp4\nfile s1.mp4\nfile s2.mp4\nfile s3.mp4\n" > $TMP/l.txt
ffmpeg -v error -y -f concat -i $TMP/l.txt -c copy $TMP/v.mp4
VIRTUE=$V node $SRC/render.js events $TMP/events.json
python3 $SRC/audio.py $SRC/stories/$V.js $TMP/a.wav $TMP/events.json > /dev/null
F=$OUT/virtue-${V}_16x9.mp4
ffmpeg -v error -y -i $TMP/v.mp4 -i $TMP/a.wav -map 0:v -map 1:a -c:v copy -af "loudnorm=I=-16:TP=-1.5:LRA=11" -ar 48000 -c:a aac -b:a 192k -shortest -movflags +faststart $F
ffmpeg -v error -y -i $F -vf "fps=12/25.2,scale=480:-1,tile=4x3" -frames:v 1 $OUT/thumbs.jpg
rm -rf $TMP; echo "DONE $V $(du -h $F | cut -f1)"
