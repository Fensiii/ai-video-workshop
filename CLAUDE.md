# 视频 / 自媒体制作工作区

`.claude/skills/` 下装了 130 个 skills。来源、版本和本地改动见 `.claude/SOURCES.md`。

## 路由规则（按顺序判断，命中即停）

1. **用户点名了某个 skill 或框架**（HyperFrames、Manim、moviepy、lianyun……）→ 就用它。
2. **默认框架是 Remotion。** 用户只说「做个视频」时不要走 `hyperframes`；`hyperframes` 及其子 skill（`general-video`、`product-launch-video`、`faceless-explainer`、`motion-graphics`、`music-to-video`、`talking-head-recut`）只在用户要 HyperFrames / HTML 合成，或要下表中 HyperFrames 独有的能力时使用。
3. **其余按下表**选入口；表里写了「入口」的，先读入口 skill，由它再分派子 skill。

## 做视频

| 任务 | 入口 / skill |
|---|---|
| 中文口播、解说、科普（已有稿子 + 配音） | `video-talkcraft` |
| 中文知识讲解、白板教学风 16:9 | 入口 `lianyun-video` |
| 网页 / 前端项目 → 产品宣传片 | `video-shotcraft` |
| 一句话主题 → 完整竖屏短视频（素材、配音、字幕、配乐全自动） | `tiktok-video` |
| 自己拍的口播素材 → 剪成短视频 / 横屏长视频 | 入口 `editing`（`short-editing`、`broll`、`steal`、`vox`、`publish`……） |
| 长视频 → 切多条竖屏短视频 | `shorts`（交互挑片段）或 `clips`（自动打分） |
| 通用 Remotion 开发（新建、预览、渲染、字幕、地图、升级） | 入口 `remotion-best-practices`；工具包扩展组件见 `remotion` |
| 短视频语法、字幕动画、倒计时、人名条 | `short-form-video`、`caption-animation`、`countdown-video`、`lower-thirds` |
| 解说动画：白板、等距 2.5D、流程图、年度总结 | `explainer-video`、`whiteboard-animation`、`isometric-animation`、`diagram-animation`、`wrapped-video` |
| 数据图表、信息图、PPT 转视频 | `chart-animation`、`animated-infographic`、`presentation-video` |
| 地图路线 | `map-animation`、`remotion-maps` |
| 聊天记录 / 短信视频 | `text-message-animation` |
| 数学 / 原理动画 | `manim` |
| HyperFrames 独有：GitHub PR 转视频、Figma 导入、抠像嵌入式字幕、可交互幻灯片 | `pr-to-video`、`figma`、`embedded-captions`、`slideshow` |

## 素材与后期

| 任务 | skill |
|---|---|
| 配音、音效、音乐 | `elevenlabs`、`acestep`；多语种配音翻译 `short-translate` |
| AI 生图 / 视频片段 / 修图 | `ideogram4`、`ltx2`、`qwen-edit`、`codex-images` |
| 录制浏览器演示 | `playwright-recording` |
| 转码、压缩、抽音频 | `ffmpeg` |
| Python 合成、给 AI 片段加字 | `moviepy` |
| 云 GPU | `runpod`（仓库缺 RunPod Dockerfile，优先用 Modal） |
| 素材来源与版权、配乐与音效选择 | `social-skills--media-acquisition`、`social-skills--audio-acquisition` |
| 人物抠像合成 | `social-skills--subject-compositing` |
| 导出到 Premiere / 达芬奇 / 剪映 | `social-skills--edit-handoff` |

## 内容运营

| 任务 | 入口 / skill |
|---|---|
| 自媒体全流程：简报→策略→热点→文案→短视频→发布→复盘 | 入口 `self-media-content-workflow`（`self-media-*`） |
| 小红书：关键词、标题、封面、笔记拆解、账号诊断、发布前后检查 | 入口 `lingzao`（`xhs-*`、`benchmark-copy-rewrite`、`handdrawn-route-map-card`） |
| 抖音视频解析、博主分析（需自己的 Cookie） | `douyin` |
| 脚本、钩子 | `studio-script`、`viral-hooks`、`social-skills--hook-anatomy` |
| 账号审计 / 爆款复盘 | `insta-audit`、`social-skills--content-autopsy`、`self-media-content-analytics` |
| 平台规则、跨平台改写、品牌一致性、模仿语气 | `social-skills--platform-fluency`、`social-skills--repurpose-engine`、`social-skills--brand-kit`、`social-skills--voice-matching` |
| 各平台转写入库（B站、抖音、TikTok、YouTube、播客、微博、知乎、小红书、公众号、X） | `*-transcribe`、`*-ingest`；加工整理 `content-enrich`、`knowledge-base-management`、`learning-notes-automation`、`industry-intelligence-radar` |
| 机器环境检查 | `video-studio-setup` |

## 首次使用前要装的依赖

| 位置 | 命令 |
|---|---|
| 工具包脚本（`elevenlabs`、`ltx2`、`qwen-edit` 等调用） | `cd .claude/video-toolkit && uv sync && cp .env.example .env`，在仓库根目录运行 `uv run --project .claude/video-toolkit python .claude/video-toolkit/tools/<脚本>.py` |
| `video-talkcraft` | `bash .claude/skills/video-talkcraft/runtime/check-runtime.sh --upgrade`（约 760 MB） |
| `video-shotcraft` | 在 skill 目录 `npm install` |
| `social-skills--*` | `cd .claude/vendor/social-skills && uv sync` |
| chubbyskills 转写类 | `cd .claude/vendor/chubbyskills && uv sync`，配置参考 `chubby.example.yaml` |
| `douyin` | `bash .claude/skills/douyin/scripts/setup_venv.sh`；Cookie 存在 `cookie_data/`（已 gitignore） |
| `shorts` | `pip install -r .claude/skills/shorts/requirements.txt` |

`.env`、Cookie、`.venv/` 都不要提交。

## 许可证

`video-talkcraft`（PolyForm Noncommercial）和 `lianyun-video-*`（CC BY-NC 4.0）仅限非商业使用；`douyin` 原仓库未声明许可证；官方 `remotion-*` 适用 Remotion License（个人和小团队免费，公司规模较大需购买授权）；其余为 MIT / MIT-0 / Apache-2.0。
