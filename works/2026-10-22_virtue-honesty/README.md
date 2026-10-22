# 美德 · 诚实（HONESTAS · HONESTY）—— 提线木偶版

照七美德短片的两幕结构做的单支，25.2 秒，1920×1080 30fps。**画面上不出现“七美德”**：
标签是「美德 · 以诚待人」，光环刻字 `VERITAS LIBERABIT VOS · HONESTAS`（真理使你自由）。
人物不再用天使，按主题改成**提线木偶 → 真正的少年**（说谎鼻子会变长，人人都懂）。做法总结在 skill `virtue-shorts`。

| 时间 | 画面 |
|---|---|
| 0–4.6s | 黑暗里先垂下三根红色提线和控制木架，一只大手从画面顶上攥着它；木偶的一只眼亮起；“说出口的话”卡片接连弹出 |
| 2.1–8.6s | 画面每撕裂一次，卡片就**闪出真相**：副标题变成青白色大字（其实刚起床 / 只会 Ctrl+C / 倒数的），原话被红线划掉 |
| 4.6–8.9s | 红光环里的木偶：条纹尖帽、漆上去的圆眼和腮红、下巴的活动缝；身体里塞满谎话；每张卡片弹出，提线就扯一下它的手；**每次心跳鼻子长一截**，长到穿过画面，还冒出枝叶 |
| 8.9–9.45s | 去色 → 金光斜斩**依次斩断三根提线**，木偶的手和头一下子垂下来 → 画面沿刀痕劈开 → 闪白 |
| 9.45–12s | 罪字碎片、三重冲击波、木架断成两截飞出画面、木屑；金色的**少年**出现：金色长鼻子缩回去、沿途洒下光点，木关节的印子一圈圈散掉，断线飘落化成光 |
| 12–24s | 披斗篷的卷发少年手按胸口，**掌心透出光**（光芒、十字星芒、一圈圈光波）；标题卡：明明可以骗过去，为什么还要「说真话」？/ **诚实** / HONESTAS · HONESTY |

全片另有：前景虚化光斑、第二幕两次斜向扫光、胶片颗粒、上帝光、绕环光点、上升金尘。

声音全部 numpy 合成：嗡鸣、推送叮声、渐快心跳、撕裂电流声、斩击、劈开撕裂、闪白冲击、碎片叮当、E 大调和弦与和声、钟声、慢鼓、光的低鸣和光波轻响；
木偶专属音效按 `FIG.events` 对齐：鼻子变长的木头吱呀、手被扯的咔嗒、三声断线拨弦、木块落地、鼻子缩回的晶亮音。响度 −16 LUFS。

发布标题和文案见 `captions.md`。

## 代码（`src/`）

- `gen_stories.py`：全部文案（卡片的“原话 / 真相”、漂浮字、罪字、设问、标题、标签、光环刻字、配色、调号、人物名 `figure`）→ `stories/honesty.js`
- `index.html`：引擎（卡片、漂浮字、文字填充、背景、光环、标题卡、主循环），`renderAt(t)` 无状态
- `fx.js`：通用特效库（撕裂、心跳、斜斩、劈开、碎片、冲击波、上帝光、光斑、扫光、颗粒……）
- `figures/puppet.js`：本片人物——木偶（鼻子、提线、木架、关节、垮下）和少年（卷发、斗篷、手按胸口的光、鼻子缩回、关节消散、断线飘落），以及音效时间点 `FIG.events`
- `audio.py stories/honesty.js out.wav events.json`：合成配乐与音效
- `render.js`：`still` 静帧 / `seg` 分段渲染 / `events` 导出人物音效时间点
- `build.sh honesty <输出目录>`：4 路并行渲染 → 拼接 → 导出事件 → 合成音频 → 混音（loudnorm −16 LUFS）→ 缩略拼图

重新出片：在 `src/` 下 `python3 gen_stories.py`，再在本目录 `bash src/build.sh honesty .`。
静帧预览：`NODE_PATH=$(npm root -g) VIRTUE=honesty node src/render.js still out 5.6 8.8 9.2 10 20`。

字体不入库：`npm pack @expo-google-fonts/noto-serif-sc @expo-google-fonts/noto-sans-sc @expo-google-fonts/cinzel`，
把 NotoSerifSC_900Black / NotoSerifSC_700Bold / NotoSansSC_700Bold / NotoSansSC_400Regular / Cinzel_400Regular / Cinzel_700Bold 放进 `src/fonts/`。
