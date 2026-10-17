#!/usr/bin/env bash
# Render the video in parallel segments, then join them and add the narration.
set -euo pipefail
cd "$(dirname "$0")"
JOBS=${JOBS:-4}
export NODE_PATH=${NODE_PATH:-$(npm root -g)}
total=$(python3 -c "import json,math;print(math.ceil(json.load(open('story.json'))['duration']*30))")
per=$(( (total + JOBS - 1) / JOBS ))
rm -f build/seg_*.mp4 build/segments.txt
for i in $(seq 0 $((JOBS - 1))); do
  node render.js "build/seg_$i.mp4" --frames $((i * per)),$(((i + 1) * per)) > "build/seg_$i.log" 2>&1 &
  echo "file 'seg_$i.mp4'" >> build/segments.txt
done
wait
ffmpeg -y -loglevel error -f concat -safe 0 -i build/segments.txt -i build/music.wav \
  -c:v copy -af "loudnorm=I=-16:TP=-1.5:LRA=11" -c:a aac -b:a 192k -shortest \
  -movflags +faststart build/tesla-success.mp4
echo "wrote build/tesla-success.mp4"
