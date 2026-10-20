# ai-video-workshop

用 Claude Code 做视频的工作区：数据动画、科普解说、歌词 MV、复刻参考视频。

## 目录

| 路径 | 内容 |
|---|---|
| `works/` | 已完成的成片，一个作品一个目录（成片 + 缩略拼图 + 字幕/生成脚本），索引见 `works/README.md` |
| `references/` | 参考视频库，按风格分类，每个配缩略拼图，`references/README.md` 写了各风格要点 |
| `tools/` | `setup_env.sh` 准备渲染环境；`archive.py` 一条命令存成片/参考素材 |
| `.claude/skills/` | 制作经验：`video-project-playbook`（总手册）、`data-history-video`（资产走势类） |
| `CLAUDE.md` | 给 Claude 的固定规则（存档、提交、文件大小） |

## 常用命令

```bash
source tools/setup_env.sh                                       # 每个新容器先跑一次
python3 tools/archive.py work build/final.mp4 my-video --src src --note "一句话说明"
python3 tools/archive.py ref upload.mp4 knowledge-explainer/dark-gold/new-topic --note "一句话"
```

## 其他分支

| 分支 | 内容 |
|---|---|
| `tesla-evolution-video` | 特斯拉车型进化 2D 动画代码（未提交成片） |
| `tesla-evolution-explainer` | 特斯拉进化史科普（配音版）、“特斯拉，凭什么？”（无配音版）代码 |
| `claude/add-video-toolkit-skills` | 130 个视频相关 skills（Remotion、HyperFrames、配音、自媒体等），尚未合并 |

GitHub 单个文件不能超过 100MB；`tools/archive.py` 会自动把超限视频压缩到约 86MB。
