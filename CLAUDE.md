# ai-video-workshop

用 Claude Code 做视频的工作区。回复用中文。

## 存档规则（必须遵守，容器会话结束即丢失文件）

1. **成片** → `works/<YYYY-MM-DD>_<英文短名>/`：成片 + `thumbs.jpg`（`tools/thumbs.sh`）+ 字幕 + 生成脚本 `src/`；
   在 `works/README.md` 表格加一行。改版覆盖同一目录。
2. **用户发来的参考素材** → `references/<类型>/`：英文短名 + 同名缩略拼图，`references/README.md` 补一行（时长、风格要点）。
3. 存完就提交并推送到当前工作分支（不推 `main`，不擅自开 PR）。
4. 单文件 ≤100MB；超了用 `tools/fit100.sh` 两遍编码压到约 90MB。

## 按需读（不要一上来全读）

- 做新视频 / 问"上次怎么做的" → skill `video-project-playbook`
- 资产价格历史走势 → skill `data-history-video`
- 找同类参考风格 → `references/README.md`（先看 `.jpg` 拼图，别先开视频）

## 省 token 的工作习惯（质量不降）

- 环境：`tools/setup.sh [字体目录]` 一次装好 skia/scipy/字体/libEGL，只回一行；skia 脚本用 `tools/skpy` 代替 `python3` 跑。
- 看视频：`tools/probe.sh` 一行规格；`tools/thumbs.sh` 一张总览；`tools/sheet.sh` 按段拆片（小格 3×3）；
  `tools/loud.sh` 一行响度。看图优先拼图、缩小尺寸，只对要量像素/取色的关键帧看全分辨率。
- 命令输出：ffmpeg 一律 `-hide_banner -loglevel error`（或 `-nostats`）；pip/npm 加 `-q`；
  长任务放后台、日志写文件，只 `tail -3` 看进度。
- 读大文件：先 `grep -n "^def "` 定位再 `sed -n 'a,bp'` 读片段；比特币 `render.py`（1600 行）按 skill 里的代码地图读。
- 改完别重复回读确认；同一信息不要多次 ffprobe / 截帧。
