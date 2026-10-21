# 七美德系列（之三 ~ 之七）

接着「节制」（`../2026-10-21_seven-virtues-temperance/`）做完剩下五支，结构、时长、时间点完全一致（25.2 秒，1920×1080 30fps）：
红色"负面声音"卡片围攻 → 文字填充的红色人像 → 去色斜斩闪白 → 碎成金片 → 金色美德人像 + 标题卡。

| 成片 | 美德 | 红色阶段的卡片 | 金色人像 |
|---|---|---|---|
| `03_justice_16x9.mp4` | 之三 正义 IUSTITIA | 甩锅、内定、删差评、刷单、"反正没人看见" | 蒙眼，天平从倾斜慢慢摆平，立剑 |
| `04_prudence_16x9.mp4` | 之四 明智 PRUDENTIA | 震惊体、谣言、杀猪盘、"验证码发我一下" | 睁眼，手镜（镜中之眼）+ 油灯 |
| `05_faith_16x9.mp4` | 之五 信念 FIDES | "你也配做梦""停更吧""第 23 封退稿信" | 十字头环，圣杯 + 发光圣饼 + 打开的书 |
| `06_hope_16x9.mp4` | 之六 希望 SPES | 拒信、房租逾期、优化通知、"电量 1%" | 头顶星辰，缠绳的锚，锚尖长出新芽 |
| `07_charity_16x9.mp4` | 之七 仁爱 CARITAS | "小心被讹""捐款都是骗人的""各扫门前雪" | 花冠，燃烧的心 + 面包篮 |

发布用的标题、正文、话题标签见 `captions.md`。每支配乐换一个调，其余音效同「节制」，全部 numpy 合成。

## 代码（`src/`）

- `gen_stories.py`：**全部文案的总表**（卡片、漂浮字、设问、标题、道具、配色、调号），运行后生成 `stories/<id>.js`
- `index.html`：画面引擎，`?v=<id>` 选美德，`renderAt(t)` 无状态
- `props.js`：头饰 / 五官 / 胸前徽章 / 手持道具（壶、天平、手镜、圣杯、锚、心）
- `audio.py stories/<id>.js out.wav`：合成配乐与音效
- `build.sh <id> <输出目录>`：4 路并行渲染 → 拼接 → 混音（loudnorm −16 LUFS）→ 缩略拼图

字体不入库：`npm pack @expo-google-fonts/noto-serif-sc @expo-google-fonts/noto-sans-sc @expo-google-fonts/cinzel`，
把 NotoSerifSC_900Black / NotoSerifSC_700Bold / NotoSansSC_700Bold / NotoSansSC_400Regular / Cinzel_400Regular / Cinzel_700Bold 放进 `src/fonts/`。
