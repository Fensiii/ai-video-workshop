# ai-video-workshop

用 Claude Code 做视频和自媒体内容的工作区：130 个 skills，覆盖中文口播、产品宣传片、短视频剪辑、动画解说、小红书 / 抖音运营和多平台转写。

## 怎么用

在仓库根目录打开 Claude Code，直接说要做什么，例如：

- 「把这份口播稿和配音做成解说视频」→ `video-talkcraft`
- 「把这个网页做成产品宣传片」→ `video-shotcraft`
- 「一句话主题生成一条抖音短视频」→ `tiktok-video`
- 「把这个长视频切成几条竖屏短视频」→ `shorts`
- 「帮我写一篇小红书笔记」→ `lingzao`

## 目录

| 路径 | 内容 |
|---|---|
| `.claude/skills/` | 11 个入口 skill，每次会话自动加载 |
| `.claude/skill-library/` | 其余 119 个 skill，按需读取，不占上下文 |
| `.claude/vendor/` | 依赖整个仓库代码的 skill 包 |
| `.claude/video-toolkit/` | 配音、生图、生视频等 Python 脚本 |
| `CLAUDE.md` | 路由规则和 skill 索引 |
| `.claude/SETUP.md` | 首次使用前要装的依赖、许可证 |
| `.claude/SOURCES.md` | 上游来源、版本和本地改动 |
