# 上海下雪 × 认真的雪（竖屏）生成脚本 · v2（three.js 3D）

v1 是 PIL 平面剪影，楼不立体、地标排列也不对（四座楼被平均摊开）。v2 改成真 3D 场景：

- **排列按真实坐标**：以东方明珠为原点（X 东、Z 南，米），金茂 (635, 493)、上海中心 (598, 684)、
  环球 (~790, 600)（由 WGS84 坐标换算；环球坐标各来源有出入，取两家地图换算后的中间值）。
  机位在外滩护墙后（明珠以西 601m、以南 100m，眼高 8.5m），朝东偏南 8.5°，焦距 1300px（按 1080 宽）。
  画面里从左到右：东方明珠（最近、最高）→ 金茂 → 环球（在金茂右后方）→ 上海中心（最右、扭转）。
  镜头用“移轴”（改投影矩阵 elements[9]）把地平线压到 y=1180，楼体竖线保持竖直。
- `scene/city.js`：three.js 场景，`window.renderAt(t)` 无状态出帧。
  - 东方明珠：三根立柱 + 三根斜撑 + 下球/五个小球/上球/太空舱（自写 shader：粉色辉光 + 纬线灯点）+ 天线灯环。
  - 金茂：13 层八角形塔身逐层收分 + 每层金色檐口灯 + 四级冠顶 + 尖塔。
  - 环球：方柱被两道弧面削到顶部一条线（放样），顶部倒梯形洞口 + LED 描边。
  - 上海中心：圆角三角形平面放样，扭转 120°、收分 46%，斜切冠顶，8 道分区灯带 + 缺口盘旋灯带。
  - 约 370 栋配楼（窗格/灯带/LED 竖条/棱线灯/顶部灯箱，挡在地标前的自动压低高度）、江岸树影与灯串、两面 LED 幕墙。
  - 黄浦江：Reflector 半分辨率镜面 + 噪声波纹 + 竖向拉丝；游船从左驶向右，倒影自动生成。
  - 落雪：2.6 万个点精灵只在视锥内生成（大小悬殊、1/60s 快门拖影），8.2s“突然飘雪”起变密。
  - 近景外滩护墙：墙头积雪由细碎雪粒到盖满、越积越厚（shader 里用局部坐标算噪声，避免大数 sin 精度问题）。
  - 雪花、护墙放在 layer 1，不进江面倒影。
- `capture.js`：Playwright 无头 Chromium（SwiftShader WebGL）逐帧截 JPEG，全分辨率约 2.7s/帧；两路并行约 2.3s/帧。
- `compose.py`：叠字幕（逐字落下、由虚到实，【】暖金色）、右上角定位/歌名、暗角、开场失焦→清晰、首尾黑场，和音频一起编码。
- `lines.json`：7 句歌词时间轴（原视频字幕逐帧检测）。

```bash
# 依赖：three@0.170.0（npm pack three@0.170.0 后解压成 vendor/）、playwright（预装）、字体同 v1
# 1) 起本地服务（ES module 不能走 file://）
mkdir site && cd site && ln -s ../scene/index.html . && ln -s ../scene/city.js . && ln -s /path/to/three/package vendor
python3 -m http.server 8766 --bind 127.0.0.1 &
# 2) 预览 / 全片
NODE_PATH=$(npm root -g) node capture.js --still stills 8766 0.5 6 15       # 半分辨率静帧
NODE_PATH=$(npm root -g) node capture.js 0 368 frames 8766 1 & NODE_PATH=$(npm root -g) node capture.js 368 735 frames 8766 1 & wait
# 3) 合成（音频：原视频音轨两遍 loudnorm 到 -14 LUFS / TP -1.5，0.15s 淡入、23.8s 起 0.7s 淡出）
FONT_DIR=/path/to/fonts python3 compose.py frames audio.m4a shanghai-snow_9x16.mp4
```
