# 美德 · 自律（DISCIPLINA · DISCIPLINE）—— 胖子 → 肌肉男，玻璃破碎转场

照「诚实」那支的两幕反转结构做的单支，25.2 秒，1920×1080 30fps，无配音。**画面上不出现“七美德”**：
标签是「美德 · 自律即自由」，光环刻字 `FORTISSIMUS EST QUI SE VINCIT · DISCIPLINA`（战胜自己的人最强大）。
人物按主题设计：**瘫着刷手机的胖子 → 雕像般的肌肉男**；转场按要求换成**玻璃破碎**（引擎新增 `transition: 'shatter'`）。

| 时间 | 画面 |
|---|---|
| 0–4.6s | 黑暗里先亮起他手里的手机，青光勾出一张低头的脸；推送卡片**从手机里飞出来**（拖着光尾），一张张贴满画面 |
| 2.1–8.6s | 画面每撕裂一次，卡片就闪出真相：再睡 5 分钟 → 已经按掉第 6 次；明天开始减肥 → 第 47 个明天；一定是秤坏了 → +18.6 kg …… |
| 4.6–8.7s | 红光环里的胖子显形：圆脸、双下巴、睡塌的乱发，T 恤兜不住肚子，身体里塞满“明天再说 / 点外卖 / 躺平”；**每次心跳肚子鼓一圈，头顶的体重读数往上跳**（86.4 → 109.5 kg） |
| 8.7–9.5s | 去色、画面放慢 → **手机屏被击中，先碎成一小片蛛网** → 第二击裂纹沿锯齿放射线和同心圈爬满全屏，缝里透出金光，每一击镜头一震 |
| 9.5–11s | **整屏炸碎**：碎片从手机往外一圈圈依次弹开，再**慢动作悬停**（每片有自己的翻转、反光、厚度边），后面露出金色的第二幕；胖子的金色剪影一圈圈收紧、剥落火星，手臂“转”上去变成举拳；左边计数器从**第 1 天跑到第 365 天**、体重掉到 76.0 kg；然后碎片加速飞出镜头 |
| 10.95s | 他握紧举起的拳头，**拳心亮起光**（指缝漏光、十字星芒、一圈圈光波） |
| 12–24s | 标题卡：明明可以明天再开始，为什么偏要「今天」？/ **自律** / DISCIPLINA · DISCIPLINE |

全片另有：前景虚化光斑、上帝光、绕环光点、上升金尘、两次斜向扫光、胶片颗粒。

声音全部 numpy 合成：嗡鸣、推送叮声 + 手机震动、渐快心跳、撕裂电流声、肚子鼓起的闷响；
玻璃第一击（闷响 + 脆响 + 裂纹声）、第二击（一长串加速的裂纹声 + 受力尖鸣 + 倒吸的上扬）、整屏炸碎（噪声爆 + 九十片玻璃叮当 + 低频冲击）、
慢动作里悬着的玻璃泛音、碎片飞出镜头的呼啸；脂肪烧掉的闪烁和火星、计数器滴答 + 叮、握拳的皮革声 + 重击 + 亮起的和弦；
G 大调和弦与和声、钟声、慢鼓、光波轻响。响度 −16 LUFS。

发布标题和文案见 `captions.md`。

## 代码（`src/`）

引擎沿用 `2026-10-22_virtue-honesty/src/`，这次的改动都做成了通用开关，诚实那支不受影响：

- `index.html`：主循环拆成 `act1(t)` / `act2(t)`；`S.transition === 'shatter'` 时走玻璃破碎（裂开时画面放慢 `slowmo`，碎片贴的是定格的第一幕）；
  卡片可以从人物身上某一点飞出来（`FIG.cardFrom`），还能额外避开某块区域（`FIG.cardAvoid`）；
  去色从 `ctx.filter` 改成整帧 `saturation` 混合——原来破碎前每帧要渲 16 秒，现在几毫秒
- `fx.js`：新增 `glassModel / glassCracks / glassFreeze / glassShatter`（放射线 × 同心圈切出碎片，锯齿裂纹两块碎片共用一条，碎片先弹开 → 慢动作 → 加速飞走）
- `figures/athlete.js`：本片人物——胖子（手机、双下巴、乱发、肉手臂、露出来的肚皮、体重读数）、肌肉男（短卷发、粗脖子、举拳的手臂、胸肌、腹肌、肌肉高光）、
  胖 → 瘦的轮廓变形（躯干逐点插值，手臂按骨骼转动插值）、第 365 天计数器、拳头的光，以及音效时间点 `FIG.events`
- `gen_stories.py`：全部文案 → `stories/discipline.js`（`transition='shatter'` 时时间轴多出 `crack / crack2`）
- `audio.py stories/discipline.js out.wav events.json`：合成配乐与音效（按 `transition` 切换转场音效，新增 `swell / buzz / contract / counter / clench`）
- `render.js` / `build.sh`：同诚实那支

重新出片：在 `src/` 下 `python3 gen_stories.py`，再在本目录 `bash src/build.sh discipline .`（4 核约 2 分钟）。
静帧预览：`NODE_PATH=$(npm root -g) VIRTUE=discipline node src/render.js still out 1 5.6 8.9 9.25 9.8 10.4 11.1 14`。

字体不入库：`npm pack @expo-google-fonts/noto-serif-sc @expo-google-fonts/noto-sans-sc @expo-google-fonts/cinzel`，
把 NotoSerifSC_900Black / NotoSerifSC_700Bold / NotoSansSC_700Bold / NotoSansSC_400Regular / Cinzel_400Regular / Cinzel_700Bold 放进 `src/fonts/`。
