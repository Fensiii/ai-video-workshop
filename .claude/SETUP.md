# 首次使用前要装的依赖

| 位置 | 命令 |
|---|---|
| 工具包脚本（`elevenlabs`、`ltx2`、`qwen-edit` 等调用） | `cd .claude/video-toolkit && uv sync && cp .env.example .env`，在仓库根目录运行 `uv run --project .claude/video-toolkit python .claude/video-toolkit/tools/<脚本>.py` |
| `video-talkcraft` | `bash .claude/skills/video-talkcraft/runtime/check-runtime.sh --upgrade`（约 760 MB） |
| `video-shotcraft` | 在 skill 目录 `npm install` |
| `social-skills--*` | `cd .claude/vendor/social-skills && uv sync` |
| chubbyskills 转写类 | `cd .claude/vendor/chubbyskills && uv sync`，配置参考 `chubby.example.yaml` |
| `douyin` | `bash .claude/skills/douyin/scripts/setup_venv.sh`；Cookie 存在 `cookie_data/`（已 gitignore） |
| `shorts` | `pip install -r .claude/skills/shorts/requirements.txt` |
| `runpod` | 仓库缺 RunPod Dockerfile，优先用 Modal |

`.env`、Cookie、`.venv/` 都不要提交。

## 许可证

`video-talkcraft`（PolyForm Noncommercial）和 `lianyun-video-*`（CC BY-NC 4.0）仅限非商业使用；`douyin` 原仓库未声明许可证；官方 `remotion-*` 适用 Remotion License（个人和小团队免费，公司规模较大需购买授权）；其余为 MIT / MIT-0 / Apache-2.0。
