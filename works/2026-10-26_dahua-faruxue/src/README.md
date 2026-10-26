# 大话西游 × 发如雪（古风竖屏）生成脚本

- `lines.json`：20 句台词 + 起止时间（从原视频字幕区亮度变化逐帧检测，5fps 精度）。`【】` 内金色。改文案/时间只动这里。
- `render.py`：PIL 逐帧合成 1080×1920@30。图层：天空宣纸纹理 → 圆月 → 三层水墨山（视差）+ 流动云雾 → 水面月影 → 孤舟 → 梅枝 → 三层落雪（副歌 19.5s 起变密）→ 暗角 → 竖排标题/朱印 → 字幕逐字晕开 → 片尾署名。

```bash
# 字体（npm 包里有 TTF）：MaShanZheng / ZhiMangXing / NotoSerifSC_500Medium 放进同一目录
for p in @expo-google-fonts/ma-shan-zheng @expo-google-fonts/zhi-mang-xing @expo-google-fonts/noto-serif-sc; do npm pack $p; done
export FONT_DIR=/path/to/fonts
python3 render.py --still 4.6 20.5 41            # 静帧预览 → stills/
for k in 0 1 2 3; do python3 render.py --seg $((k*398)) $(( k==3 ? 1590 : (k+1)*398 )) seg$k.mp4 & done; wait
# 拼接 + 音频（原视频音轨两遍 loudnorm 到 -14 LUFS / TP -1.5，尾部 1.4s 淡出）
```
