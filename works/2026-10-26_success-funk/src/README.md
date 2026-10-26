# 《成功》v2 生成脚本

1920×1080 60fps，32.25 秒。逐帧在线性光 HDR 里合成，最后用 ACES 色调映射。音轨直接复制用户上传视频里的 AAC，不重新编码。

| 文件 | 作用 |
|---|---|
| `analyze.py` | 分析音频：拟合节拍网格（105.7 BPM，首个重拍 5.098s），测每个 16 分格的起音强度，输出 `events.json` |
| `events.json` | 分析结果（已提交，渲染不需要重新分析） |
| `engine.py` | 渲染引擎：skia 字形 → 倒角金属材质（可挤出厚度）、精灵透视变换、运动模糊、粒子、体积光、冲击波折射、辉光/横向光条、镜头光晕、色散、故障、ACES、胶片颗粒 |
| `scenes.py` | 分镜：15 段场景、镜头、底部“成功进度”曲线 |
| `render.py` | 主循环：静帧预览 / 多进程渲染视频 |

## 环境

```bash
apt-get install -y --no-install-recommends libegl1 \
    fonts-noto-cjk fonts-noto-cjk-extra fonts-smiley-sans fonts-lxgw-wenkai
pip install skia-python opencv-python-headless numpy
```

字体：思源宋体/黑体 Heavy（Noto Serif/Sans CJK SC Black）、得意黑、霞鹜文楷、Inter Display、JetBrains Mono（系统自带）。

## 用法

```bash
# 1. 从原视频提取音频（只用于分析；成片音轨直接复制原视频的 AAC）
ffmpeg -i src.mp4 -vn -c:a pcm_s16le -ar 44100 audio.wav
python3 analyze.py audio.wav events.json

# 2. 看关键帧
python3 render.py still 5.6,12.5,28.8 out_frames/

# 3. 渲染母版（4 进程，CRF 12）
python3 render.py video master.mp4 src.mp4

# 4. 压到 100MB 以内（两遍编码）
ffmpeg -y -i master.mp4 -c:v libx264 -preset slow -profile:v high -b:v 20M -pass 1 -an -f null /dev/null
ffmpeg -y -i master.mp4 -c:v libx264 -preset slow -profile:v high -b:v 20M -maxrate 30M -bufsize 40M -pass 2 \
    -pix_fmt yuv420p -colorspace bt709 -color_primaries bt709 -color_trc bt709 -c:a copy -movflags +faststart out.mp4
```

## 分镜（时间来自节拍网格）

| 时间 | 段落 | 画面 |
|---|---|---|
| 0–2.8 | 什么是成功？ | 顶光体积光束，金字砸下带火花、冲击波、地面倒影 |
| 2.8–4.2 | 是运气？是天赋？ | 左右两束追光，故障闪入，最后被吸进中心光点 |
| 4.2–5.1 | 3·2·1 | 隧道速度线加速，光越来越亮直到白屏 |
| 5.1–7.4 | 成功 SUCCESS | 冲击帧（反相）、厚金字、背光体积光、火星 |
| 7.4–9.6 | 不是运气·不是天赋·而是 | 红色光刃斩断，文字碎裂；推镜冲向“而是” |
| 9.6–11.9 | 跌倒·爬起·再来 | 主节奏进入：字自由落体、镜头侧倾，弹簧回正，金字砸下 |
| 11.9–14.2 | 失败 1→99 次 | 红色故障、扫描线、取景框 HUD |
| 14.2–16.4 | 第 100 次·依然出发 | 红转金，速度线，镜头右移 |
| 16.4–18.7 | 早起·读书·训练·复盘 | 台阶逐级点亮，光球一拍跳一级，镜头跟拍上楼 |
| 18.7–21.0 | 熬过的夜 | 星空、月亮、快转的时钟、凌晨时间 |
| 21.0–23.3 | 流过的汗 | 雨幕，“汗”落地溅水、水波折射，雨速放慢 |
| 23.3–25.5 | 没人看见的努力 | 黑暗里追光扫过，“努力”砸下时灯光全亮 |
| 25.5–27.8 | 终将被看见 | 日出、镜头光晕、太阳体积光，白屏进高潮 |
| 27.8–30.1 | 成功，是熬出来的 | 山巅日出、插旗、金粉雨，进度曲线到 100% |
| 30.1–32.25 | 致每一个还在坚持的你 | 暗下来，霞鹜文楷落款，淡出 |
