# 视频 / 自媒体工作区

只有 11 个入口 skill 自动加载（`.claude/skills/`）。另外 119 个放在 `.claude/skill-library/<名字>/SKILL.md`，不占上下文：
- 入口 skill 或用户提到下面某个名字时，用 Read 读那个文件再照做；Skill 工具调用不到它们。
- 用户点名了框架就用它。否则默认 Remotion，`hyperframes` 只在用户明确要时用。
- 来源和本地改动见 `.claude/SOURCES.md`，安装依赖见 `.claude/SETUP.md`。只在需要时读。

## 库（按需读取）

- Remotion：`remotion-create` `remotion-render` `remotion-studio` `remotion-markup` `remotion-captions` `remotion-maps` `remotion-interactivity` `remotion-multimedia` `remotion-saas` `remotion-docs` `remotion-upgrade` `remotion`（工具包组件）
- 动画类型：`explainer-video` `whiteboard-animation` `isometric-animation` `diagram-animation` `wrapped-video` `chart-animation` `animated-infographic` `presentation-video` `map-animation` `text-message-animation` `manim` `short-form-video` `caption-animation` `countdown-video` `lower-thirds`
- 素材后期：`elevenlabs` `acestep` `ideogram4` `ltx2` `qwen-edit` `codex-images` `ffmpeg` `moviepy` `playwright-recording` `runpod`（脚本在 `.claude/video-toolkit/`）
- 剪辑（`editing` 的子 skill）：`short-editing` `broll` `clips` `steal` `vox` `short-translate` `publish` `studio-script` `insta-audit` `video-studio-setup`
- HyperFrames 子 skill：`hyperframes-*` `general-video` `product-launch-video` `faceless-explainer` `motion-graphics` `music-to-video` `talking-head-recut` `pr-to-video` `figma` `embedded-captions` `slideshow` `media-use` `remotion-to-hyperframes`
- 自媒体（`self-media-content-workflow` 的子 skill）：`self-media-` + `content-brief` `content-strategy` `trend-radar` `platform-copywriting` `short-video` `video-publisher` `wechat-publisher` `content-analytics` `content-delivery`
- 小红书（`lingzao` 的子 skill）：`xhs-keyword-to-content-package` `xhs-keyword-design` `xhs-title-writer` `xhs-cover-lab` `xhs-note-breakdown` `xhs-benchmark-account-finder` `xhs-account-diagnosis` `xhs-prepublish-check` `xhs-postpublish-review` `benchmark-copy-rewrite` `handdrawn-route-map-card`
- 讲解视频（`lianyun-video` 的子 skill）：`lianyun-video-content` `lianyun-video-design` `lianyun-video-core`
- 社媒方法论：`social-skills--video-production` `--hook-anatomy` `--content-autopsy` `--platform-fluency` `--repurpose-engine` `--brand-kit` `--voice-matching` `--read-the-room` `--video-formats` `--agent-interview` `--media-acquisition` `--audio-acquisition` `--subject-compositing` `--edit-handoff`；钩子 `viral-hooks`
- 转写入库：`<平台>-transcribe`（bilibili douyin tiktok youtube podcast weibo zhihu），`xiaohongshu-ingest` `wechat-article-ingest` `x-ingest`，整理 `content-enrich` `knowledge-base-management` `learning-notes-automation` `industry-intelligence-radar`
