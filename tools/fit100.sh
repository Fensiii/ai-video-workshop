#!/usr/bin/env bash
# 体积 >95MB 时两遍编码压到约 90MB（GitHub 单文件上限 100MB），否则原样复制。
# 用法：tools/fit100.sh in.mp4 out.mp4 [目标MB=90]   FORCE=1 强制压缩
in=$(realpath "$1"); out=$(realpath -m "$2"); mb=${3:-90}
size=$(stat -c %s "$in")
if [ -z "$FORCE" ] && [ "$size" -le $((95 * 1024 * 1024)) ]; then
  [ "$in" != "$out" ] && cp "$in" "$out"; echo "$out 无需压缩 ($((size / 1048576))MB)"; exit 0
fi
d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$in")
ab=192
vb=$(python3 -c "print(int($mb*8*1024/$d - $ab))")
cd "$(mktemp -d)" || exit 1
ffmpeg -hide_banner -loglevel error -y -i "$in" -c:v libx264 -b:v ${vb}k -pass 1 -an -f null /dev/null && \
ffmpeg -hide_banner -loglevel error -y -i "$in" -c:v libx264 -b:v ${vb}k -pass 2 -pix_fmt yuv420p \
  -c:a aac -b:a ${ab}k -movflags +faststart "$out"
echo "$out $(($(stat -c %s "$out") / 1048576))MB (v=${vb}k)"
