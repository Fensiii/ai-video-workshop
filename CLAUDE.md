# ai-video-workshop

用 Claude Code 做视频的工作区。回复用中文。

## 必须遵守的存档规则

上传的文件和渲染结果都在临时容器里，会话结束就丢失，所以：

1. **最终视频一律存进 `works/`**：每次把成片交付给用户时，同时存到
   `works/<YYYY-MM-DD>_<英文短名>/`，附缩略拼图 `thumbs.jpg`（全片均匀 12 帧，`tile=4x3`）、
   字幕和生成脚本（`src/`），并在 `works/README.md` 表格里加一行。改版覆盖同一目录。
2. **用户发来的参考素材一律存进 `references/<类型>/`**：英文短名、配同名缩略拼图，
   更新 `references/README.md`（时长、风格要点）。
3. **存完就提交并推送**到当前工作分支（不直接推 `main`，不擅自开 PR）。
4. 单文件不超过 100MB；视频超了就两遍编码压到约 90MB。

## 先读这些

- `.claude/skills/video-project-playbook/`：历次项目经验、该用哪套代码
- `.claude/skills/data-history-video/`：资产历史走势类视频
- `references/README.md`：参考素材库与各风格要点
- `works/README.md`：已完成作品
