# 美德 · 诚实（HONESTAS · HONESTY）

照七美德短片（尤其是天使篇，分支 `claude/seven-virtues-temperance` 的 `works/2026-10-22_seven-virtues-angels/`）的结构做的单支，
25.2 秒，1920×1080 30fps。**画面上不出现“七美德”**：标签改成「美德 · 以诚待人」，光环刻字改成 `VERITAS LIBERABIT VOS · HONESTAS`（真理使你自由）。

| 时间 | 画面 |
|---|---|
| 0–4.6s | 黑暗里浮出一张**微笑面具**，眼洞里亮着红光；“说出口的话”卡片接连弹出（在路上了、原图直出、精通 Excel、全班第五……） |
| 2.1–8.6s | 画面每次撕裂，卡片都**闪出真相**：副标题变成青白色大字（其实刚起床 / 只会 Ctrl+C / 倒数的），原话被红线划掉 |
| 4.6–8.9s | 文字填满的红色堕天使人像，脸上戴着面具；6.3s 起面具从眼角、嘴角**裂开透光**，随心跳闪烁，瓷片往下掉；余烬、裂纹、红色暗角脉冲 |
| 8.9–9.45s | 去色 → 金光斜斩 → **画面沿刀痕劈成两半错开**，缝里透出白光 → 闪白 |
| 9.45–12s | 面具碎片 + 罪字碎片 + 羽毛爆散、三重冲击波；金色天使展翅，头顶光圈、上帝光 |
| 12–24s | 天使**手托真理之光**（冷白光核、直线 + 波浪光芒、旋转细环、十字星芒、一圈圈扩散的光波），**脱下的面具碎成两半落在脚边**，断口里的红光慢慢熄灭；标题卡：「美德 · 以诚待人」/ 明明可以骗过去，为什么还要「说真话」？/ **诚实** / HONESTAS · HONESTY |

全片另加：前景虚化光斑（景深感）、第二幕两次斜向扫光、胶片颗粒。

声音全部 numpy 合成：天使篇那套（嗡鸣、推送叮声、渐快心跳、撕裂电流声、斩击、冲击、碎片叮当、E 大调和弦、天使和声、钟声、慢鼓），
去掉水流声，新增面具开裂的噼啪声、画面劈开的撕裂下坠声、面具碎裂的脆响和瓷片叮、真理之光的低鸣和光波轻响。响度 −16 LUFS。

发布标题和文案见 `captions.md`。

## 代码（`src/`）

- `gen_stories.py`：全部文案（卡片的“原话 / 真相”、漂浮字、设问、标题、标签、光环刻字、配色、调号）→ `stories/honesty.js`
- `index.html`：画面引擎（天使篇引擎 + 卡片闪真相、面具、劈开、光斑、颗粒的挂点），`renderAt(t)` 无状态
- `angel.js`：翅膀、光圈、余烬、裂纹、撕裂、上帝光、羽毛等（天使篇原样）
- `honesty.js`：本片新增的全部特效和道具（面具、裂纹、劈开、面具碎片、真理之光、碎面具、光斑、扫光、颗粒）
- `props.js`：头饰 / 五官 / 徽章等通用部件（天使篇原样）
- `audio.py stories/honesty.js out.wav`：合成配乐与音效
- `build.sh honesty <输出目录>`：4 路并行渲染 → 拼接 → 混音（loudnorm −16 LUFS）→ 缩略拼图

重新出片：在 `src/` 下 `python3 gen_stories.py`，再 `bash src/build.sh honesty .`（在本目录执行）。
静帧预览：`NODE_PATH=$(npm root -g) VIRTUE=honesty node src/render.js still out 5.5 9.3 20`。

字体不入库：`npm pack @expo-google-fonts/noto-serif-sc @expo-google-fonts/noto-sans-sc @expo-google-fonts/cinzel`，
把 NotoSerifSC_900Black / NotoSerifSC_700Bold / NotoSansSC_700Bold / NotoSansSC_400Regular / Cinzel_400Regular / Cinzel_700Bold 放进 `src/fonts/`。
