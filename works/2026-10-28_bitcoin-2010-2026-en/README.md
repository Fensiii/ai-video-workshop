# Bitcoin Price History 2010–2026（英文版 + 原创配乐）

中文版 `works/2026-10-17_bitcoin-2010-2026/` 的英文翻译版，面向 YouTube 发布。画面、时间轴、数据与中文版完全一致，
只把画面文字全部换成英文，并加了一条按时间轴写的原创配乐（原来的合成音效压低后保留）。

| 文件 | 说明 |
|---|---|
| `bitcoin_2010-2026_en_16x9.mp4` | 成片存档版：1920×1080 30fps，3:14，两遍编码约 95 MB |
| `thumbs.jpg` | 全片均匀 12 帧缩略拼图 |
| `youtube_thumbnail.jpg` | YouTube 封面 1280×720 |
| `youtube.md` | 发布包：标题、描述（含章节时间戳）、标签、中文翻译、上传设置 |
| `data/btc_price.csv` | Coin Metrics 日收盘价，截到 2026-05-23（与中文版同一截止日） |
| `src/` | 全部生成脚本 |

上传 YouTube 建议用更高码率的 `out/bitcoin_2010-2026_en_master.mp4`（约 178 MB，超出 GitHub 单文件上限，不进仓库；
`python3 src/mix.py --mux-only` 可重新生成）。

## 改了什么

- **文字**：事件卡片、年代标题、HUD、片头片尾、图上标签全部英文。标题字体 Source Serif 4（对应中文版的思源宋体），
  其余 Inter；文字经 HarfBuzz 排版（有字距调整）。卡片标题超宽自动缩字号，描述按宽度自动折行且避免孤字。
  事件分类原来的中文键保留在代码里做逻辑，屏幕上显示 `CAT_EN` 的英文。
- **配乐**（`score.py` + `music.py`）：D 小调、120 BPM（所有事件都落在拍点上），弦乐 + 圆号 + 钢琴 + 竖琴 + 钟琴 +
  定音鼓/大鼓/镲 + 少量合成器脉冲。能量曲线跟着行情走：涨到顶点时主题旋律（A-D-E-F 上行）由大提琴/圆号/小提琴奏出，
  暴跌那一帧乐队断掉、只剩低音。结尾在金句出现时转成 D 大调。
- **音效**（`audio.py`）：去掉原来的持续底噪 drone（会和和声打架）；铃声音高全部吸附到当时和弦内音；
  月份滴答对齐到 16 分音符网格，跟配乐节拍咬合。
- **母带**（`mix.py`）：音效比配乐低 5 dB；整体 −14 LUFS、真峰值 ≤ −1 dBTP（YouTube 播放基准）。

## 音源与授权

配乐是为本片原创的，不会被 Content ID 认领。用到的采样：

- VS Chamber Orchestra: Community Edition（`sgossner/VSCO-2-CE`，CC0）
- Salamander Grand Piano V3，Alexander Holm（`sfzinstruments/SalamanderGrandPiano`，CC BY 3.0，需署名，已写进 YouTube 描述）

## 重建步骤（云端容器）

```bash
cd works/2026-10-28_bitcoin-2010-2026-en
# 1. 字体：npm pack @expo-google-fonts/inter 与 @expo-google-fonts/source-serif-4，把 src/render.py
#    FONT_FILES 里列的 TTF 拷进 fonts/
# 2. 采样（约 600 MB，git 忽略）
python3 src/fetch_samples.py
# 3. skia-python 144 需要 libEGL.so.1（Chromium 自带的 libEGL 不导出它要的符号），编一个空桩库：
mkdir -p ~/egl && gcc -shared -fPIC -o ~/egl/libEGL.so.1 -Wl,-soname,libEGL.so.1 src/egl_stub.c
export LD_LIBRARY_PATH=~/egl:$LD_LIBRARY_PATH
pip install skia-python uharfbuzz pedalboard pyloudnorm scipy
cd src
python3 run_render.py 16          # 画面，4 核约 12 分钟 -> out/video_noaudio.mp4
python3 music.py                  # 配乐，约 30 秒 -> out/music.wav（--stems 另存各声部）
python3 audio.py                  # 音效 -> out/sfx.wav
python3 mix.py                    # 混音母带 + 封装 master 与存档版
python3 thumbnail.py              # YouTube 封面
```
