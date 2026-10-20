# 成品视频库

每一支做完交付的最终视频都存在这里，一个作品一个目录：`works/<日期>_<英文短名>/`。
存放规则见根目录 `CLAUDE.md`。

| 目录 | 成片 | 时长 | 规格 | 说明 |
|---|---|---|---|---|
| `2026-10-17_bitcoin-2010-2026/` | `bitcoin_2010-2026_16x9.mp4` | 3:14 | 1920×1080 30fps | 比特币 2010–2026 走势，一比一复刻 `references/data-history/nasdaq-55y.mp4`；只有合成音效；含镜头晃动、推近和图上标注。生成脚本在 `src/`，经验见 skill `data-history-video` |
| `2026-10-17_song-mv-duanfa/` | `duanfa-girl-mv_16x9.mp4` | 1:10 | 1920×1080 | 《幻昼》×《短发女孩》×《take me hand》混剪，带歌词字幕；`lyrics.ass` / `lyrics.lrc` 为歌词时间轴 |

## 不在库里的旧作品

特斯拉三个项目（2D 进化动画、进化史科普配音版、“特斯拉，凭什么？”无配音版）当时只提交了代码，
没有提交成片。代码在分支 `tesla-evolution-video`、`tesla-evolution-explainer`，需要成片时按各自 README 重新渲染后补进这里。
