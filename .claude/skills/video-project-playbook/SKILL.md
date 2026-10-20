---
name: video-project-playbook
description: 本仓库历次视频项目的经验总结与可复用代码索引（特斯拉进化 2D 动画、特斯拉进化科普配音版、特斯拉凭什么无配音版、歌曲混剪 MV 加歌词、比特币历史走势复刻）。用户要做新视频、复刻参考视频、做科普/解说/动画/歌词 MV、问“上次怎么做的”时先读这里，再决定复用哪套代码。
---

# 视频项目经验手册（ai-video-workshop）

## 项目索引

特斯拉代码在别的分支：`git fetch -q origin <分支>` 后先 `git ls-tree -r --name-only origin/<分支> <目录>` 看清单，
再 `git show origin/<分支>:<路径>` 只读需要的文件，或 `git checkout origin/<分支> -- <目录>` 取回。

| 项目 | 分支 / 目录 | 形式 | 技术栈 | 细节 |
|---|---|---|---|---|
| 特斯拉车型进化（2D 动画） | `tesla-evolution-video` / `tesla-evolution/` | 60s、1080p60、无声，拆解变形换代 + 实拍起飞 | skia-python 逐帧 | `projects.md` §1 |
| 特斯拉车型进化史（科普） | `tesla-evolution-explainer` / `tesla-evolution/` | 4分20秒、中文配音 + 字幕 | HTML + Playwright + 离线 TTS | §2 |
| 特斯拉，凭什么？（无配音） | `tesla-evolution-explainer` / `tesla-success/` | 2分38秒、字幕 + 合成配乐 | Canvas/DOM + Playwright + numpy 配乐 | §3 |
| 歌曲混剪 MV | `works/2026-10-17_song-mv-duanfa/` | 16:9 混剪 + 卡拉 OK 式歌词 | ffmpeg + ASS/LRC | §4 |
| 比特币 2010–2026 | `works/2026-10-17_bitcoin-2010-2026/`（成片 + `src/`） | 3分14秒复刻、只要音效 | skia-python + numpy 音效 | skill `data-history-video` |
| 视频 skills 库 | `claude/add-video-toolkit-skills` / `.claude/` | 130 个 skills（Remotion、HyperFrames、配音等） | 只在点名时读该分支 `CLAUDE.md` | — |

`projects.md` 只读和本次相关的那一节。参考素材见 `references/README.md`（先看拼图）。

## 一、通用流程

1. **吃透需求和参考**：`tools/probe.sh` → `tools/thumbs.sh --ts` 总览 → `tools/sheet.sh` 按段拆 →
   只对关键帧拉全分辨率取色/量字号。“一比一”= 版式、配色、节奏、特效都照抄，只换内容。
2. **确认形式**：默认 16:9 1920×1080、动画 30/60fps；时长；配音/音乐/音效。
   “只要音效不要配音”= 无人声、无音乐素材，音效全程序合成。
3. **数据/分镜与渲染代码分开**（`script.json`、`story.json`、`EVENTS_RAW`），改文案只动数据。
4. **先静帧**（`--preview` / `--still` / `render.py t1 t2`）拼图查重叠出界 → 5–10 秒小样 → 全片。
5. **并行分段渲染**：4 路分段 → 各自编码 → `ffmpeg concat -c copy` → 最后混音。后台跑，日志写文件。
6. **自检**：`tools/probe.sh`、`tools/thumbs.sh`、`tools/loud.sh`（约 −16 LUFS、TP ≤ −1 dB）。
7. **存档 + 交付**：按 `CLAUDE.md` 存 `references/`、`works/`；`SendUserFile` 发视频，
   说明数据截止日、改编点、需复核的文案；提交推送到工作分支。

## 二、环境坑（云端容器）

- `tools/setup.sh [字体目录]`（之后用 `tools/skpy` 跑 skia 脚本）：装 skia-python/scipy、软链 libEGL、从 npm 取 Noto Serif/Sans SC + Inter TTF。
- 网络白名单窄：`raw.githubusercontent.com`、`registry.npmjs.org`、`pypi.org` 可用；多数行情 API、
  Google Fonts、CDN 403。先 `curl -sI` 探测，失败换 npm/GitHub 源。
- 网页项目字体用 `@fontsource/noto-serif-sc`，渲染前 `await document.fonts.ready`。
- Playwright：Chromium 已预装，别 `playwright install`；`NODE_PATH=$(npm root -g) node render.js`，
  必要时 `CHROMIUM_PATH=/opt/pw-browsers/chromium`。
- 多进程用 fork；随机种子别用 `hash()`，用 `zlib.crc32` 或固定种子。
- 高细节画面 crf19 会超 100MB → `tools/fit100.sh`（约 3 分钟 ≈ 90MB）。

## 三、渲染路线怎么选

| 路线 | 适合 | 代表 | 要点 |
|---|---|---|---|
| **skia-python 逐帧** | 发光曲线、粒子、透视图表、矢量变形 | 比特币、特斯拉 2D | 0.3–0.7 s/帧；numpy 半分辨率算光效再 kPlus 叠加 |
| **HTML/Canvas + Playwright** | 字幕多、版式多的科普/解说 | 特斯拉科普两部 | 页面暴露无状态 `window.renderAt(t)`；截 JPEG 管道给 ffmpeg |
| **ffmpeg + ASS 字幕** | 已有素材混剪、MV、加歌词 | 歌曲混剪 | ASS 控字体/描边/淡入淡出，另出 LRC |
| Remotion / HyperFrames | 用户点名或要 React 组件化 | skills 库分支 | 读该分支 `CLAUDE.md` 路由 |

`renderAt(t)` / `render_frame(fi)` 必须无状态（同一 t 同一帧），才能任意分段并行、随时预览。

## 四、用户偏好（已确认过的）

- 回复用中文；视频默认 16:9 1080p。
- “一比一复刻”要求极高：版式、配色、节奏、特效逐项对齐原片。
- 重大波动必须有镜头晃动；关键信息必须推近放大并在画面上标点（锁定框、数值、箭头）。
- 要求“只要音效不要配音”时，不加人声、不加音乐。
- 数字要和真实数据一致；不确定的事实不编，写得保守并告知。
- 每次做完要提交推送；文件别超 GitHub 100MB。

## 五、新项目起手清单

1. 判断类型 → 选上表的渲染路线和最接近的旧项目，取回它的代码当模板。
2. 拆参考 / 写分镜数据文件。
3. `tools/setup.sh`；准备数据、素材（注意网络白名单）。
4. 出 6–10 张关键静帧拼图确认 → 出 5–10 秒小样看动态 → 全片并行渲染。
5. 合成音频（配音 / 配乐 / 音效），响度统一后混入。
6. 自检、交付、提交推送；新经验补进 `projects.md` 新一节并在索引表加一行。
