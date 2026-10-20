# ai-video-workshop

用 Claude Code 做视频的工作区。回复用中文。

## 开工前

- 新容器先 `source tools/setup_env.sh`（Python 依赖、中文字体、skia 需要的 libEGL）。
  不要把它接在管道后面跑（`source ... | grep` 会在子 shell 里执行，环境变量带不出来）。
- 先读 `.claude/skills/video-project-playbook/SKILL.md`，再看 `references/README.md` 有没有同类参考、
  `works/README.md` 有没有可复用的旧作品。
- 新任务从最新 `main` 新建分支：`git fetch origin main && git checkout -b <分支名> origin/main`。

## 必须遵守的存档规则

上传的文件和渲染结果都在临时容器里，会话结束就丢失，所以：

1. **成片一律存进 `works/`**：交付给用户的同时执行
   `python3 tools/archive.py work <成片> <英文短名> --src <生成脚本目录> --note "<一句话>"`。
   它会复制到 `works/<日期>_<短名>/`、生成 `thumbs.jpg`、超 95MB 自动压缩、在 `works/README.md` 追加一行。
   改版用同一个短名和 `--date <原日期>` 覆盖。
2. **用户发来的参考素材一律存进 `references/`**：
   `python3 tools/archive.py ref <文件> <类型>/<英文短名> --note "<一句话>"`（竖版画布用 `--crop` 裁出画面），
   然后在 `references/README.md` 对应风格小节手写风格要点；没有合适类型就新建并补一个小节。
3. **存完就提交并推送**到当前工作分支（不直接推 `main`，不擅自开 PR）。
4. 单文件不超过 100MB。
5. 新学到的经验补进 `video-project-playbook`（或对应的专题 skill）。
