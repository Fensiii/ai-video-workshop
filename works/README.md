# 成品视频库

每一支做完交付的最终视频都存在这里，一个作品一个目录：`works/<日期>_<英文短名>/`。
目录里放成片 `.mp4`、缩略拼图 `thumbs.jpg`（全片均匀 12 帧），以及字幕、生成脚本等配套文件。

| 目录 | 成片 | 时长 | 规格 | 说明 |
|---|---|---|---|---|
| `2026-10-17_bitcoin-2010-2026/` | `bitcoin_2010-2026_16x9.mp4` | 3:14 | 1920×1080 30fps | 比特币 2010–2026 走势，一比一复刻 `references/data-history/nasdaq-55y.mp4`；只有合成音效；含镜头晃动、推近和图上标注。生成脚本在 `src/`，经验见 skill `data-history-video` |
| `2026-10-26_shanghai-snow/` | `shanghai-snow_9x16.mp4` | 0:24 | 1080×1920 30fps | 上海下雪竖屏歌词视频：薛之谦《认真的雪》（音频取自 `references/lyric-mv/renzhen-de-xue-shanghai.mp4`，响度归一到 −14 LUFS）。**v2 改为 three.js 真 3D**：外滩机位看陆家嘴雪夜，东方明珠、金茂、环球、上海中心按真实坐标摆放（从左到右明珠→金茂→环球→上海中心），黄浦江镜面倒影、游船、视锥内落雪、护墙积雪越积越厚；`subtitles.srt/.lrc`、`douyin_post.md`；生成脚本 `src/`（scene/city.js + capture.js + compose.py） |
| `2026-10-26_dahua-faruxue/` | `dahua-faruxue_9x16.mp4` | 0:53 | 1080×1920 30fps | 古风抖音竖屏：《大话西游》至尊宝独白 × 周杰伦《发如雪》（音频取自 `references/lyric-mv/dahua-monologue-faruxue.mp4`，响度归一到 −14 LUFS）。程序生成水墨远山、圆月、梅枝、孤舟、落雪，马善政楷书字幕逐字晕开，“我爱你”“一万年”金色。`subtitles.srt/.lrc`；生成脚本 `src/`（PIL 逐帧，字体走 npm `@expo-google-fonts`） |
| `2026-10-17_song-mv-duanfa/` | `duanfa-girl-mv_16x9.mp4` | 1:10 | 1920×1080 | 《幻昼》×《短发女孩》×《take me hand》混剪，带歌词字幕；`lyrics.ass` / `lyrics.lrc` 为歌词时间轴 |

## 不在库里的旧作品

特斯拉三个项目（2D 进化动画、进化史科普配音版、“特斯拉，凭什么？”无配音版）当时只提交了代码，
没有提交成片。代码在分支 `tesla-evolution-video`、`tesla-evolution-explainer`，需要成片时按各自 README 重新渲染后补进这里。

## 存放规则

- 每次交付最终视频时同步存入，并在上表加一行；改版就覆盖同一目录里的成片并更新说明。
- 单文件不能超过 100MB（GitHub 上限），超了用两遍编码压到约 90MB 以内。
