---
name: data-history-video
description: 复刻/制作“资产历史走势”类数据动画视频（如纳斯达克 55 年、比特币 16 年、以太坊/Solana 英文 YouTube 版）。当用户上传参考视频要求“一比一”换成另一个资产/指数，或要求做价格历史回顾动画、加镜头晃动/放大/标注、只要音效不要配音、做英文版发 YouTube 时使用。
---

# 数据历史走势视频：经验与流程

参考实现：`works/2026-10-17_bitcoin-2010-2026/src/`（比特币版，可直接改数据和事件复用）
- `btc_common.py`：数据加载、事件表、章节、时间映射、镜头预计算
- `render.py`：skia 逐帧渲染（背景/图表/特效/HUD/片头片尾/镜头 FX）
- `audio.py`：纯合成音效轨（无配音、无音乐素材）
- `run_render.py`：多进程分段渲染 + ffmpeg 拼接

**多资产 + 英文版（YouTube）**：`works/2026-10-28_ethereum-2015-2026/src/`（以太坊、Solana 共用一套代码，
`ASSET=eth|sol` 切换）。新资产优先从这套起步：故事和文案全在 `cfg_<资产>.py`，
`common.py` 自检所有上屏数字，另有 `finalize.py`（音效→响度→两遍编码）、`cover.py`（YouTube 封面）、
`youtube_meta.py`（标题/简介/章节/标签）。

## 1. 分析参考视频（先做，别凭印象）
1. `ffprobe` 看时长/分辨率/音轨。抖音视频常是竖版长画布，16:9 内容在中间：
   `ffmpeg -vf cropdetect` 找内容区，再 `crop=1920:1080:0:Y` 裁出来。
2. 1fps 带时间戳的拼图逐张看全片：
   `-vf "fps=1,scale=640:360,drawtext=...%{pts\:hms}...,tile=3x3"`
3. 关键帧拉全分辨率，取样配色（PIL 取最亮像素均值）、量字号和位置。
4. 声音：先看频谱判断有没有人声（人声在 100–4kHz 有共振峰/音节节奏）。
   原片可能只是背景音乐、根本没有旁白——如实告诉用户。
5. 记下节奏规律：事件前减速停留 1–2 秒、事件间快进；章节大标题；“首次突破”整数关口。

## 2. 环境坑（云端容器）
- 网络只放行少数域名：`raw.githubusercontent.com`、`registry.npmjs.org`、`pypi.org` 可用；
  CoinGecko/Binance API/Yahoo/FRED/Google Fonts 都被 403。
- 价格数据：`https://raw.githubusercontent.com/coinmetrics/data/master/csv/btc.csv`
  （列 `PriceUSD`，日频，有约半年延迟——必须告诉用户数据截止日）。
  **Coin Metrics 的 `sol.csv` 等很多币没有 `PriceUSD` 列**，只有估算市值。
- **最新日线（到昨天）走 Binance 公开数据的 S3 桶**，可访问：
  `https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?prefix=data/spot/monthly/klines/ETHUSDT/1d/`
  列出 zip，整月用 monthly、当月用 daily；2025 年起的文件时间戳是微秒。脚本见 `fetch_binance.py`。
  和 Coin Metrics 拼接前先比重叠区（ETH 中位差 ≈0），拼在 Coin Metrics 最后一天之后。
- 中文/数字字体走 npm：`@expo-google-fonts/noto-serif-sc`、`noto-sans-sc`、`inter`（内含 TTF）；
  英文标题用 `@expo-google-fonts/playfair-display`（900Black/700Bold/Italic）。
- `pip install skia-python` 后缺 `libEGL.so.1`。旧办法是软链 Playwright 自带的
  `/opt/pw-browsers/chromium-*/chrome-linux*/libEGL.so`；**新版 Chromium（1243）的 libEGL 不再导出 egl 符号**，
  会报 `undefined symbol: eglQueryString`。直接编一个桩库（skia 只链 3 个函数，CPU 光栅从不调用）：
  `gcc -shared -fPIC -Wl,-soname,libEGL.so.1 -o libEGL.so.1 egl_stub.c`（源码在上面 src 里）。
- 多进程用 fork；随机种子不要用 `hash()`（每进程不同），用 `zlib.crc32`。

## 3. 渲染架构要点
- 透视图表：日期为 u、log 价格为 v，绕 Y 轴旋转 ~36° 的针孔投影；
  曲线头固定在屏幕约 (1173–1236, 600)，可视天数随时间增长，镜头参数用 EMA 顺序预计算并缓存。
- 光柱（红涨绿跌）在半分辨率 numpy 里按列算、高斯模糊后 kPlus 叠加；
  放大时柱子变宽会变成霓虹块——按“每天像素数”降亮度。
- 时间映射：事件时刻为锚点，锚点间 smootherstep 混 25% 线性 → 自然“到事件减速”。
  **整数关口（里程碑）也给显式时刻当锚点**，否则关口离下一事件只差几天时，标签只闪 1 秒就被让位。
- 标签防重叠：按 x 排序逐个上移；HUD 区和右侧卡片区设“禁入区”淡出；
  每个事件只保留最近 ~9 个历史标签；里程碑标签在下一事件出现时让位；
  网格刻度数字碰到事件标签就隐藏（比特币版有“100,000”压“MicroStrategy”的问题）。
- HUD 后面垫一层柔和暗色椭圆，曲线从年份/价格下面穿过时字仍清楚。
- 卡片/标注/光环的寿命 = min(默认, 下一事件时刻 + 0.25s)，否则相邻事件叠成一团。
- 暗角要画在 HUD 之前，否则压暗文字。

## 4. 镜头 FX（用户明确要求过，默认就要做）
- **晃动**：冲击型 `amp·exp(-a/0.5)`，频率 7–16Hz（不要 >20Hz，30fps 下像频闪）；
  黑天鹅 16–26px、一般暴跌 8–14px、新高 4–6px；
  震荡行情：近 3 日最大单日涨跌 >3% 起触发，最大约 5px 的低频手持晃。
  HUD 只跟 22% 的晃动；冲击 >9 时加 1–5px RGB 色散 + 0.2 白闪。
- **推近**：事件前 0.55s 开始、停 1.45s、1.15s 拉回；黑天鹅/顶点/谷底 1.42×，
  暴跌/新高 1.30×，其余 1.18×；锚点向屏幕焦点 (1015,560) 拉 80%。
  用 `skia.Matrix` 组合，背景只跟 25% 缩放。
- **标点**：四角锁定框 + “$价格 · 日期”标签（跌在下方、涨在上方）、
  ATH 虚线、从参考点到终点的测量箭头 + 百分比胶囊、卡片关键数字弹出放大 + 高亮条。
- 每个 FX 配一个音效（推镜呼啸、锁定滴答、测量划过、冲击轰鸣）。

## 5. 音效（只要音效不要配音）
全部 numpy/scipy 合成：铃音（多泛音指数衰减）、轰鸣（扫频正弦+低通噪声）、
呼啸（扫频带通噪声）、火花（随机高频短音）、月/年滴答、底噪随行情冷暖变化；
混响 = 指数衰减噪声卷积；母带归一到约 −16 LUFS，用前瞻峰值限制器（别用 tanh，会失真）。
**发 YouTube 的按 −14 LUFS、真峰值 ≤ −1 dBTP**（预限幅 RMS −14.3 dB、限幅阈 0.84 即可）。
用频谱图核对音效时刻与画面事件对齐。

## 5b. 原创配乐（用户说“没有音乐，加个合适的音乐”时）
实现见 `works/2026-10-28_ethereum-2015-2026/src/music.py` + `mix.py`。
- **别用现成曲子**（YouTube Content ID 会认领），也拿不到曲库；自己编曲生成。
- 乐器采样：`raw.githubusercontent.com/gleitz/midi-js-soundfonts/gh-pages/FluidR3_GM/<乐器>-mp3.js`
  （CC BY 3.0，简介里署名即可），`fetch_samples.py` 解码成 npz。每个音 3.14 s：
  钢琴/定音鼓自然衰减；弦乐/合唱/Pad 是持续音，长音要用 0.9–3.05 s 段等功率交叉淡化循环。
- **卡点诀窍：事件时刻都取 0.5 s 的倍数 → 120 BPM 下每个事件正好落在拍点上**。
  小节网格从 0.5 s 起；片尾网格从“总结大字”时刻倒推，两套网格不对齐就在交界插一个 2/4 小节。
- 按行情编排：45 天动量判牛熊（平滑 + 迟滞，只在两小节边界切换）；牛市 i–VI–III–VII，
  熊市 i–iv–VI–V；黑天鹅那一拍除定音鼓/底鼓外全部切断到下个小节；谷底只剩钢琴 + Pad；
  新高前两小节 VI–VII 铺垫 + 军鼓滚奏 + 反向镲，命中拍合唱/镲片；片尾 V→VI 假终止接主题旋律。
- 音效里的铃声要改成配乐同调（`kf(半音, 八度)`），去掉原来的持续低音 drone，否则和和弦打架。
- **听不到就用数据验**：每个采样做 FFT 核对音高（MIDI 69 = 440 Hz）；逐小节色度对比设计和弦
  （本次 92/93、75/75）；强起音落在 16 分音符网格的比例；黑天鹅窗口内电平。
  色度检查就抓到过一个 bug（片尾和弦表的键用了绝对时间、查表用相对时间）。
- 混音：配乐 −16.5 LUFS、音效 −18 LUFS，大爆炸时配乐自动压低 4 dB，限幅后整体 −14 LUFS。
- 只换音轨时直接 `-c:v copy` 复用已编码画面；**别加 `-shortest`**，会把结尾裁掉几帧。

## 6. 出片与交付
- 测试：`python3 render.py 16.6 30 ...` 出单帧 PNG，拼图检查；改动后再跑小段视频看动态。
- 全片：`python3 run_render.py 16`（4 核约 11–13 分钟，0.4–0.7 s/帧）。
- 编码：GitHub 单文件上限 100MB。加晃动后 crf19 会到 110MB →
  用两遍编码 `-b:v 3500k`，194 秒约 90MB。
- 数字全部用数据核对；没把握的事件原因不要编，写得保守并告知用户。
- 交付时说明：数据截止日、与原片不同的改编点、需要用户复核的文案。
- 提交到新分支（不要直接推 main），不擅自开 PR。

## 7. 复用到新资产的步骤
1. 换 `load_prices()` 数据源与 `PRICE/DATES`。
2. 重写 `EVENTS_RAW`（时刻、日期、类别、标题、数值、描述、标签）、`ERAS`、`MILESTONES`、
   `SHAKE` / `BLACK_SWANS` / `BRACKETS`。
3. 改 HUD 文案（标题、“收盘价格”）、片头片尾文案与倍数。
4. 先出 10 张关键帧确认版面，再全片渲染。

多资产版里这些都集中在 `cfg_<资产>.py`；事件用语义 `kind`（genesis/peak/high/rally/crash/crisis/bottom/info/tech）
决定颜色、推镜、晃动和音效，`category` 只是卡片上显示的英文分类。

## 8. 做英文版 / 发 YouTube 的额外点
- **涨跌配色按西方习惯反过来：绿涨红跌**（中文版是红涨绿跌），光柱、曲线、HUD 数字、背景冷暖都要跟着换。
- 英文标题比中文长：卡片标题、描述、章节标题都做自动缩字号（`fit_font`），标题尽量 ≤ 20 字符。
- 章节名别和事件卡标题重名（如章节“Crypto Winter”和卡片“Crypto Winter”同时出现）。
- 封面 1280×720：大号币名 + 一句钩子（“11 YEARS IN 3 MINUTES”）+ 图上 2 个锁定框（最大回撤、ATH），
  标签别压到标题。
- `youtube_meta.py` 用章节时刻自动生成 YouTube chapters（首个必须 0:00、每段 ≥10 秒）。
- 2026 年这类训练数据之后的事件，用 WebSearch 查到 2 个以上来源再写，描述保守（只写可核对的数字）。
