# 七美德流星 · 生成脚本

照 `references/data-history/ai-leaderboard-meteors.mp4` 的版式做的“七美德”版：
每种美德一颗流星，“此刻最亮”的那颗 = 当前历史节点体现的美德（带 NO.1 + 星芒），
左上大号年份（BC/AD）+ 当前最亮美德 + “群星易主 N 次”，底部金色年份 + 白字事件，
结尾七条轨迹汇成一颗星 + 问句。

| 文件 | 作用 |
|---|---|
| `virtues.py` | **数据**：七美德（中文名/拉丁文/颜色）、22 个历史节点 `EVENTS_RAW`、时间轴、流星位置函数 |
| `render.py` | skia 逐帧渲染，`render_frame(fi, arr)` 无状态；`python3 render.py 3 40 80` 出静帧到 `../work/` |
| `run_render.py` | 4 进程分 8 段并行渲染 + concat（约 5 分钟） |
| `audio.py` | numpy 合成配乐（Dm–B♭–F–C，90BPM）+ 风声/钟声/轰鸣音效 |
| `make_final.sh` | 一键出片 |

改文案只动 `virtues.py` 的 `EVENTS_RAW` / `FINAL_Q`；节点间隔 `STEP`（秒）控制全片长度。
特效标记：`shake` 镜头晃动、`plague` 晃动 + 红色压暗、`burst` 新星诞生、`constellation` 七星连线。
