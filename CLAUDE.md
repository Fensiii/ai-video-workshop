# 视频制作工作区

`.claude/skills/` 下装了 25 个视频相关 skills。按任务选入口：

| 任务 | 首选 skill |
|---|---|
| 中文口播 / 解说 / 科普视频（已有稿子 + 配音） | `video-talkcraft` |
| 把网页 / 前端项目做成产品宣传片 | `video-shotcraft` |
| 通用 Remotion 开发（新建、预览、渲染、字幕、地图） | `remotion-best-practices`（路由到其余 `remotion-*`） |
| 配音、音效、音乐 | `elevenlabs`、`acestep` |
| AI 生成画面 / 视频片段 / 修图 | `ideogram4`、`ltx2`、`qwen-edit` |
| 录制浏览器演示 | `playwright-recording` |
| 转码、压缩、抽音频 | `ffmpeg` |
| Python 合成短片、给 AI 片段加字 | `moviepy` |
| 云 GPU 部署 | `runpod` |

## 工具包脚本

`elevenlabs`、`ltx2`、`qwen-edit` 等 skill 调用的 Python 脚本放在 `.claude/video-toolkit/`（来自 digitalsamba/claude-code-video-toolkit，MIT）：

```bash
cd .claude/video-toolkit && uv sync      # 安装依赖
cp .env.example .env                     # 填 API key（.env 已被 gitignore）
```

脚本从仓库根目录运行，例如 `uv run --project .claude/video-toolkit python .claude/video-toolkit/tools/voiceover.py ...`。

## 首次使用前

- `video-talkcraft`：`bash .claude/skills/video-talkcraft/runtime/check-runtime.sh --upgrade`（约 760 MB 依赖）。
- `video-shotcraft`：在 skill 目录 `npm install`。

## 许可证

`video-talkcraft` 为 PolyForm Noncommercial（仅限非商业使用）；其余为 MIT / Apache-2.0 / Remotion License。
