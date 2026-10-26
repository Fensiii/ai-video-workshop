# 上海下雪 × 认真的雪（竖屏）生成脚本

- `lines.json`：7 句歌词 + 起止时间（原视频字幕区亮度逐帧检测，10fps）。`【】` 内暖金色。改词/时间只动这里。
- `render.py`：PIL + numpy 逐帧合成 1080×1920@30，单帧约 0.3s，4 路并行全片约 1 分钟。
  - 天际线（静态，2× 超采样后缩小 + 三档泛光）：外滩视角按真实方位/距离透视——东方明珠 934m、金茂 1490m、
    环球 1802m、上海中心 1642m（竖向 ×1.12），其余楼随机生成（窗格/灯带/LED 竖条/描边），距离越远越雾。
  - 黄浦江：天际线下半截镜像、竖向拉丝，逐行正弦+随机相位横移做波纹；游船和它的倒影随时间移动。
  - 航空障碍灯闪烁、镜头缓推、开场 1.6s 失焦→清晰。
  - 雪：四层（远/中/近/虚焦）+ 斜向雪幕；8.2s“突然飘雪”起变密，14s 再加一档；左下画外路灯把附近雪花染暖。
  - 江堤护墙积雪：撒盐状斑点 → 15s 左右盖满 → 雪冠越积越厚。

```bash
# 字体（npm 包里有 TTF）：NotoSerifSC_600SemiBold（字幕）、NotoSansSC_500Medium（定位/歌名）放同一目录
for p in @expo-google-fonts/noto-serif-sc @expo-google-fonts/noto-sans-sc; do npm pack $p; done
export FONT_DIR=/path/to/fonts
python3 render.py --still 5.5 9.2 15            # 静帧预览 → stills/
for k in 0 1 2 3; do python3 render.py --seg $((k*184)) $(( k==3 ? 735 : (k+1)*184 )) seg$k.mp4 & done; wait
# 拼接 + 音频（原视频音轨两遍 loudnorm 到 -14 LUFS / TP -1.5，0.15s 淡入、23.8s 起 0.7s 淡出）
```
