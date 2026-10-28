# 登神长阶（3 秒）

侧面视角：一个披斗篷的剪影一步一级登上悬空长阶，台阶尽头是神光；镜头跟人并缓慢拉远，
结尾神光爆发、画面泛白。1920×1080 30fps，3.0 秒，程序合成音效（低频嗡鸣、脚步、和声、结尾钟声）。

- `src/render.py OUT_DIR [t...]`：逐帧渲染（PIL + numpy，2× 超采样剪影，4 进程约 2 分钟）；给时间点只出静帧
- `src/audio.py out.wav`：合成音效
- 编码：`ffmpeg -framerate 30 -i f%04d.png -i sfx.wav -c:v libx264 -crf 17 -pix_fmt yuv420p -c:a aac -af loudnorm=I=-16:TP=-1.5`
