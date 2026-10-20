---
name: video-project-playbook
description: 本仓库做视频的总手册：通用流程、环境坑、渲染路线选择、历次项目经验（特斯拉 2D 动画/科普、歌词 MV、比特币走势复刻）、参考素材库各风格该怎么做、存档工具用法。用户要做新视频、复刻参考视频、做科普/解说/动画/歌词 MV、问“上次怎么做的”时先读这里。
---

# 视频项目经验手册（ai-video-workshop）

`main` 上有：成片库 `works/`（比特币、歌曲 MV，含生成脚本）、参考库 `references/`、工具 `tools/`。
特斯拉三个项目的代码只在各自分支：`git fetch origin <分支>` 后用 `git show origin/<分支>:<路径>` 读，
或 `git checkout origin/<分支> -- <目录>` 取回。

| 项目 | 分支 / 目录 | 形式 | 技术栈 |
|---|---|---|---|
| 特斯拉车型进化（2D 动画） | `tesla-evolution-video` / `tesla-evolution/` | 60s、1080p60、无声，车辆拆解变形换代 + 实拍起飞 | skia-python 逐帧 |
| 特斯拉车型进化史（科普） | `tesla-evolution-explainer` / `tesla-evolution/` | 4分20秒、中文配音 + 字幕 | HTML 动画 + Playwright 截帧 + 离线 TTS |
| 特斯拉，凭什么？（无配音） | `tesla-evolution-explainer` / `tesla-success/` | 2分38秒、字幕 + 合成配乐 | Canvas/DOM + Playwright + numpy 配乐 |
| 歌曲混剪 MV | `works/2026-10-17_song-mv-duanfa/`（原分支 `claude/song-music-video`） | 16:9 混剪 + 卡拉 OK 式歌词 | ffmpeg + ASS/LRC 字幕 |
| 比特币 2010–2026 | `works/2026-10-17_bitcoin-2010-2026/`（成片 + `src/`） | 3分14秒复刻、只要音效 | skia-python + numpy 音效 |
| 视频 skills 库 | `claude/add-video-toolkit-skills` / `.claude/` | 130 个 skills（Remotion、HyperFrames、配音、自媒体等） | 见该分支 `CLAUDE.md` |

比特币这类“资产历史走势复刻”有单独的详细 skill：`data-history-video`。

**参考素材库 `references/`**：用户给过的参考视频按风格归档，每个配缩略拼图，`references/README.md` 写了各风格要点。
接新需求先看这里有没有同类参考，再按下表选做法：

| 参考风格 | 目录 | 推荐路线 | 可复用的旧代码 |
|---|---|---|---|
| 数据历史走势 | `data-history/` | skia 逐帧 | `works/2026-10-17_bitcoin-2010-2026/src/`（skill `data-history-video`） |
| 暗金知识科普（Iwanau 系） | `knowledge-explainer/dark-gold/` | HTML/Canvas + Playwright | `tesla-evolution-explainer` 分支 `tesla-success/`（字幕高亮、合成配乐） |
| 深蓝信息图科普 | `knowledge-explainer/navy-infographic/` | HTML + CSS 动画 + Playwright | 同上，版式更简单 |
| 卡通夜景算法演示 | `knowledge-explainer/cartoon-night/` | HTML/Canvas（角色用 SVG） | 同上 |
| 歌词动画 MV | `lyric-mv/` | skia 或 Canvas 画角色，ASS/LRC 对时间轴 | `works/2026-10-17_song-mv-duanfa/`（歌词时间轴） |
| 哲思极简（粒子/点线） | `philosophy-minimal/` | skia 粒子与路径动画 | 比特币 `render.py` 里的粒子、发光、背景代码 |

---

## 一、通用流程（每次都照做）

1. **先吃透需求和参考**：用户给参考视频就逐帧拆（1fps 拼图 + 关键帧全分辨率 + 取色），
   不凭印象。“一比一”指版式、配色、节奏、特效都照抄，只换内容。
2. **确认形式**：比例（默认 16:9 1920×1080）、帧率（动画 30/60）、时长、
   要不要配音/音乐/音效。用户说“只要音效不要配音”时：不配人声、不用音乐素材，音效全部程序合成。
3. **写数据/分镜文件，和渲染代码分开**：`script.json`、`story.json`、`cars.py`、`EVENTS_RAW`。
   改文案只动数据文件。
4. **先出静帧预览**（每套代码都有 `--preview`、`--still` 或 `render.py t1 t2`），
   拼成拼图检查版面、重叠、出界，再全片渲染。
5. **并行分段渲染**：4 路分段 → 各自编码 → `ffmpeg concat -c copy` 拼接 → 最后混音。
6. **成片自检**：ffprobe 看规格；抽 8 帧拼图看画面；ebur128 看响度（约 −16 LUFS、真峰值 ≤ −1 dB）。
7. **存参考**：用户上传的参考素材会随容器消失——当场
   `python3 tools/archive.py ref <文件> <类型>/<短名> --note "..."`，再手写风格要点进 `references/README.md`。
8. **存成片**：交付同时 `python3 tools/archive.py work <成片> <短名> --src <脚本目录> --note "..."`
   （自动拼图、超限压缩、写索引）。
9. **交付**：`SendUserFile` 发视频；说明数据截止日、改编点、需要用户复核的文案。
   提交到新分支，不直接推 `main`，不擅自开 PR。

## 二、环境与工具坑（云端容器）

先 `source tools/setup_env.sh`：装 Python 依赖、从 npm 下中文/数字字体到 `.cache/fonts`（导出 `VIDEO_FONT_DIR`）、
给 skia 补 libEGL（导出 `LD_LIBRARY_PATH`）。别写成 `source ... | grep`，管道会让它跑在子 shell 里、环境变量丢失。
下面是它背后的原因，排错时看：

- 网络白名单很窄：`raw.githubusercontent.com`、`registry.npmjs.org`、`pypi.org` 能用；
  多数行情 API、Google Fonts、CDN 被 403。先 `curl -I` 探测，失败就换 npm/GitHub 源。
- **字体**：系统只有文泉驿。好看的中文字体走 npm：
  `@expo-google-fonts/noto-serif-sc`、`noto-sans-sc`、`inter`（内含 TTF，可直接给 skia/PIL 用）；
  网页项目用 `@fontsource/noto-serif-sc`，渲染前 `await document.fonts.ready`。
- **skia-python** 缺 `libEGL.so.1`：把 `/opt/pw-browsers/chromium-*/chrome-linux/libEGL.so`
  软链成 `libEGL.so.1`，目录加进 `LD_LIBRARY_PATH`。
- **Playwright**：Chromium 已预装，不要 `playwright install`；
  `NODE_PATH=$(npm root -g) node render.js`，必要时 `CHROMIUM_PATH=/opt/pw-browsers/chromium`。
- 多进程渲染用 fork；随机数种子别用 Python `hash()`（每进程不同），用 `zlib.crc32` 或固定种子。
- GitHub 单文件上限 100MB：加镜头晃动等高细节画面后 crf19 会超；用两遍编码 `-b:v 3500k`
  （约 3 分钟 ≈ 90MB）。`tools/archive.py` 存档时会自动检查并压缩。
- 渲染中间产物放各作品的 `build/`，下载的数据放 `data/`，都已在 `.gitignore` 里，不会误提交。
- 长任务（全片渲染 10+ 分钟）放后台，用 `until grep ... ; do sleep 10; done` 等完成，不要轮询刷屏。

## 三、三种渲染路线怎么选

| 路线 | 适合 | 代表项目 | 要点 |
|---|---|---|---|
| **skia-python 逐帧** | 发光曲线、粒子、透视图表、矢量变形，追求电影感 | 比特币、特斯拉 2D 动画 | 0.3–0.7 s/帧；numpy 半分辨率算光效再 kPlus 叠加 |
| **HTML/Canvas + Playwright 截帧** | 字幕多、版式多、DOM 排版方便的科普/解说 | 两个特斯拉科普 | 页面暴露 `window.renderAt(t)`，纯函数按时间绘制；截 JPEG 管道给 ffmpeg |
| **ffmpeg 剪辑 + ASS 字幕** | 已有素材的混剪、MV、加歌词 | 歌曲混剪 | ASS 控字体/描边/淡入淡出，另出 LRC 方便复用 |
| Remotion / HyperFrames | 用户点名或需要 React 组件化 | skills 库 | 读 `claude/add-video-toolkit-skills` 分支的 `CLAUDE.md` 路由 |

`renderAt(t)` 必须是**无状态**的（同一 t 永远画出同一帧），这样才能任意分段并行、随时预览。

## 四、各项目的具体经验

### 1. 特斯拉车型进化 2D 动画（skia）
- 车型精度：照参考侧面图**描摹轮廓点**，再按官方长、高、轴距、前后悬**分段映射**，比例 1:1；
  官方没公布的车按公开图推算，并在 README 写明。
- 描摹校准工具 `trace.py`：把参考图放大叠网格、轮廓、轮心，逐车对照修点。
- 轮廓用 Catmull-Rom 平滑，角点标 sharp；所有可变形部件重采样到固定点数（96/320）才能插值变形。
- 换代转场：旧车拆成零件 → 空中变形 → 组装成新车；车头朝右、锁定画面中央，背景视差滚动。
- 实拍拼接 `footage.sh`：`delogo` 去台标 → 分段线性 `crop` 跟踪车身 → `hflip` 统一车头方向 →
  `setpts=3*PTS` 慢放 + `minterpolate` 补帧到 60fps → 锐化调色。
- 封面单独脚本 `cover.py`，标题定稿“会飞的车”；封面要有主体动势（倾斜起飞 + 历代残影 + 辉光）。

### 2. 特斯拉进化史科普（配音版）
- `script.json` 每行 `[字幕, 朗读文本]`：**朗读文本把数字、年份写成汉字**，人名间隔号改逗号，
  防止 TTS 读错。
- 离线 TTS：sherpa-onnx + `vits-melo-tts-zh_en`，speed 0.88；逐句合成并记录每句起止时间，
  生成 `timeline.json`，画面和字幕都按它对齐（**画面跟配音走，不是配音跟画面走**）。
- 句间 0.35s、场景间 0.9s、片头 1.2s、片尾 2.5s 留白。
- 混音 `loudnorm=I=-16:TP=-1.5:LRA=11`。

### 3. 特斯拉，凭什么？（无配音版）
- 结构：开场直接上高潮（市值破万亿）→ 回到 2008 生死关头 → 五个原因分章 → 数据 → 结尾。
- 字幕标记：`【】` 渲染成金色、`〔〕` 渲染成红色，关键词一眼可见。
- 配乐用 numpy 合成（和弦 pad、琶音、贝斯、底鼓，100BPM），
  `story.json` 里的 `hits` 是重音时刻，音乐强度曲线按分镜手工给点，**重音和画面切换对齐**。
- 标签/字块防重叠要单独处理（有一次专门修“标签压到合并块”）。

### 4. 歌曲混剪 MV
- 多首歌混剪（《幻昼》×《短发女孩》×《take me hand》），16:9 输出。
- 歌词做成 ASS：歌词样式 78 号白字深色描边、底部居中；片头歌名样式左上角；
  每句 `\fad(120,120)`，片头 `\fad(400,400)`；同时导出 LRC。
- 歌词时间轴要逐句对准演唱；混剪接点放在乐句边界。

### 5. 比特币历史走势复刻
详见 `data-history-video`。要点：数据从 Coin Metrics GitHub CSV 取（有半年延迟）；
到事件时减速；暴跌/黑天鹅镜头冲击晃动（7–16Hz），震荡行情手持晃动；
重要节点推近放大 + 锁定框、价格日期标签、ATH 虚线、涨跌测量箭头；音效全合成。

## 五、用户偏好（已确认过的）

- 回复用中文；视频默认 16:9 1080p。
- “一比一复刻”要求极高：版式、配色、节奏、特效逐项对齐原片。
- 重大波动必须有镜头晃动；关键信息必须推近放大并在画面上标点（锁定框、数值、箭头）。
- 要求“只要音效不要配音”时，不加人声、不加音乐。
- 数字要和真实数据一致；不确定的事实不编，写得保守并告知。
- 每次做完要提交推送；文件别超 GitHub 100MB。

## 六、新项目起手清单

1. 判断类型 → 选上表的渲染路线和最接近的旧项目，取回它的代码当模板。
2. 拆参考 / 写分镜数据文件。
3. 准备字体、数据、素材（注意网络白名单）。
4. 出 6–10 张关键静帧拼图确认 → 出 5–10 秒小样看动态 → 全片并行渲染。
5. 合成音频（配音 / 配乐 / 音效），响度统一后混入。
6. 自检、交付、提交到新分支；把新经验补进本文件。
