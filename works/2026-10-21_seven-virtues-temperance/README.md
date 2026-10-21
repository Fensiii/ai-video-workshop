# 七美德 · 之二「节制」（第一版小样）

参照 `references/virtue-shorts/seven-virtues-courage.mp4`（七美德·之一「勇气」）的结构做的姊妹篇，25 秒，1920×1080 30fps。

| 时间 | 画面 |
|---|---|
| 0–4.6s | 黑暗中亮起一只红眼，诱惑推送卡片接连弹出（秒杀、外卖、自动播放、额度提升……），红字漂浮 |
| 4.6–8.9s | 红色光环里浮现侧脸人像，身体被"再来一单 · 就一口 · 买它"等文字填满，头顶起火，卡片被推开，镜头开始晃 |
| 8.9–9.45s | 去色 → 金光斜斩 → 闪白 |
| 9.45–12s | 碎成金片，露出金色"节制"女神：头环、面纱，举壶把水倒进另一只壶里；光环刻七美德拉丁名 |
| 12–24s | 标题卡：「七美德 · 之二」/ 明明很想要，为什么还要「停下来」？/ **节制** / TEMPERANTIA · TEMPERANCE |

声音全部用 numpy 合成：低频嗡鸣、推送叮声、渐快心跳、上扬噪声、斩击、冲击轰鸣、碎片叮当，第二幕是 D 大调和弦铺底、钟声和 72BPM 慢鼓。

## 重新生成

```bash
cd src
# 字体（不入库）：npm pack @expo-google-fonts/noto-serif-sc @expo-google-fonts/noto-sans-sc @expo-google-fonts/cinzel，
# 把 NotoSerifSC_900Black / NotoSerifSC_700Bold / NotoSansSC_700Bold / NotoSansSC_400Regular / Cinzel_400Regular / Cinzel_700Bold 的 TTF 放进 src/fonts/
NODE_PATH=$(npm root -g) node render.js still out 6.5 13.2 18      # 静帧
for i in 0 1 2 3; do NODE_PATH=$(npm root -g) node render.js seg s$i.mp4 $((i*189)) $(((i+1)*189)) & done; wait
python3 audio.py story.js                                           # → audio.wav
# concat 四段后：-af loudnorm=I=-16:TP=-1.5:LRA=11 混入音频
```

文案、卡片、时间点都在 `src/story.js`；画面在 `src/index.html`（`renderAt(t)` 无状态）。
