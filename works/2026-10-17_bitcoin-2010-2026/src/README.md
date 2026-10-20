# 比特币 2010–2026 生成脚本

```bash
cd /path/to/ai-video-workshop
source tools/setup_env.sh                                  # 依赖、字体、skia 的 libEGL
cd works/2026-10-17_bitcoin-2010-2026
mkdir -p data && curl -sS -o data/btc_cm.csv \
  https://raw.githubusercontent.com/coinmetrics/data/master/csv/btc.csv
cd src
python3 render.py 16.6 96.3 170.6      # 出静帧到 ../build/test_frames/ 检查版面
./make_final.sh                         # 全片：并行渲染 → 合成音效 → 两遍编码，约 15 分钟
```

成片输出到 `../build/final.mp4`，确认后用 `tools/archive.py work` 存档（会覆盖同名成片）。

| 文件 | 作用 |
|---|---|
| `btc_common.py` | 数据加载、事件表 `EVENTS_RAW`、章节、晃动/推近/测量箭头配置、时间映射、镜头预计算 |
| `render.py` | skia 逐帧渲染：背景、透视图表、光柱、曲线、事件特效、镜头 FX、HUD、片头片尾 |
| `audio.py` | 纯合成音效轨 → `../build/sfx.wav` |
| `run_render.py` | 多进程分段渲染并拼接 → `../build/video_noaudio.mp4` |

注意：Coin Metrics 数据比实际晚约半年；数据更新后结尾日期、片尾倍数文案（`render.py` 的 `draw_ending_text`）要一起改。
