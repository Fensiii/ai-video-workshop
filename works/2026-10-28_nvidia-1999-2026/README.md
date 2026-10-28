# NVIDIA 1999–2026（英文版，发 YouTube）

英伟达上市 27 年股价走势动画，版式、特效、音效沿用 `2026-10-17_bitcoin-2010-2026/`，画面文字全英文。

| 文件 | 说明 |
|---|---|
| `nvidia_1999-2026_16x9.mp4` | 成片，3:33，1920×1080 30fps，只有合成音效（−14 LUFS） |
| `thumbnail.jpg` | YouTube 封面 1280×720 |
| `youtube.md` | YouTube 标题备选、简介（含章节时间戳）、标签 |
| `thumbs.jpg` | 全片均匀 12 帧拼图 |
| `data/nvda_daily.csv` | 1999-01-22 至 2026-10-27 日收盘价（仅拆股调整，不含分红） |
| `src/` | 生成脚本 |

## 数据

云端会话连不上 Yahoo/Stooq，数据取自 GitHub 上两份 Yahoo Finance 公开镜像并拼接（`src/merge_data.py`）：

- 1999-01-22 至 2024-06-18：`debjit-mandal/NVIDIA-Stock-Analysis` 的 `data/NVDA.csv`（`Close` 列）
- 2024-06-19 至 2026-10-27：`yennanliu/finance_data` 的 `data/prices/nvda.csv`（每日自动更新）

两份在 2016-10-27 至 2024-06-18 的 1,922 个交易日逐日一致（差 ≤ $0.005）。
抽查与新闻吻合：2025-01-27 $118.42（−16.97%）、2024-09-03 $108.00（−9.53%）、2025-10-29 $207.04、
2026-05-14 $235.74、2026-10-22 $212.21。

## 复现

```bash
# 字体：npm pack @expo-google-fonts/inter @expo-google-fonts/noto-serif，把 TTF 放进 fonts/
cd src
python3 merge_data.py OLD.csv NEW.csv   # -> ../data/nvda_daily.csv
# 网络能连 Yahoo/Stooq 时也可以直接：python3 fetch_data.py
python3 render.py 17.4 40 152.9         # 单帧预览 -> ../work/test_frames/
python3 run_render.py 16                # 全片，4 核约 25 分钟 -> ../out/video_noaudio.mp4
python3 audio.py                        # 合成音效 -> ../out/sfx.wav
python3 finalize.py                     # 响度 + 两遍编码 + thumbs.jpg
python3 thumbnail.py                    # YouTube 封面
```

改文案、事件、时间只动 `src/nvda_common.py` 里的 `EVENTS_RAW` / `ERAS` / `MILESTONES_RAW`，
涨跌幅、价格、倍数都由数据自动计算。
