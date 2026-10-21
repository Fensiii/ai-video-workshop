# 成品视频库

每一支做完交付的最终视频都存在这里，一个作品一个目录：`works/<日期>_<英文短名>/`。
目录里放成片 `.mp4`、缩略拼图 `thumbs.jpg`（全片均匀 12 帧），以及字幕、生成脚本等配套文件。

| 目录 | 成片 | 时长 | 规格 | 说明 |
|---|---|---|---|---|
| `2026-10-17_bitcoin-2010-2026/` | `bitcoin_2010-2026_16x9.mp4` | 3:14 | 1920×1080 30fps | 比特币 2010–2026 走势，一比一复刻 `references/data-history/nasdaq-55y.mp4`；只有合成音效；含镜头晃动、推近和图上标注。生成脚本在 `src/`，经验见 skill `data-history-video` |
| `2026-10-17_song-mv-duanfa/` | `duanfa-girl-mv_16x9.mp4` | 1:10 | 1920×1080 | 《幻昼》×《短发女孩》×《take me hand》混剪，带歌词字幕；`lyrics.ass` / `lyrics.lrc` 为歌词时间轴 |
| `2026-10-21_seven-virtues-temperance/` | `seven-virtues-temperance_16x9.mp4` | 0:25 | 1920×1080 30fps | 七美德·之二「节制」，参照 `references/virtue-shorts/seven-virtues-courage.mp4`（勇气）的结构：红色诱惑推送围攻 → 文字填充人像 → 金光斜斩碎裂 → 金色持壶倒水女神 + 标题卡；音效配乐全合成。HTML Canvas + Playwright，代码在 `src/` |
| `2026-10-21_seven-virtues-series/` | `03_justice` `04_prudence` `05_faith` `06_hope` `07_charity`（`_16x9.mp4`） | 各 0:25 | 1920×1080 30fps | 七美德之三至之七（正义、明智、信念、希望、仁爱），与「节制」同一套结构，引擎可配置（`src/gen_stories.py` 为文案总表）；每支缩略拼图 `thumbs_0N_<id>.jpg`；发布标题和文案在 `captions.md` |

## 不在库里的旧作品

特斯拉三个项目（2D 进化动画、进化史科普配音版、“特斯拉，凭什么？”无配音版）当时只提交了代码，
没有提交成片。代码在分支 `tesla-evolution-video`、`tesla-evolution-explainer`，需要成片时按各自 README 重新渲染后补进这里。

## 存放规则

- 每次交付最终视频时同步存入，并在上表加一行；改版就覆盖同一目录里的成片并更新说明。
- 单文件不能超过 100MB（GitHub 上限），超了用两遍编码压到约 90MB 以内。
