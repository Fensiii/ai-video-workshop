# 特斯拉车型进化史（科普视频）

约 4 分 20 秒的 1080p 中文科普视频：Roadster → Model S → Model X → Model 3 → Model Y → Semi → Cybertruck → 焕新/平价版 → Cybercab。

## 文件

- `script.json` — 解说词与画面数据（每行 `[字幕, 朗读文本]`，朗读文本把数字写成汉字，防止 TTS 读错）
- `tts.py` — 用 sherpa-onnx 的离线中文模型 `vits-melo-tts-zh_en` 逐句合成配音，输出 `build/narration.wav` 和 `build/timeline.json`
- `index.html` — 逐帧动画（SVG 车型剪影、年份、参数卡片、字幕、时间轴），`renderAt(t)` 按时间绘制
- `render.js` — 用 Playwright + Chromium 逐帧截图，交给 ffmpeg 合成 `build/tesla-evolution.mp4`

## 重新生成

```bash
pip install sherpa-onnx soundfile
curl -LO https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-melo-tts-zh_en.tar.bz2
tar xjf vits-melo-tts-zh_en.tar.bz2 -C /path/to/models
python3 tts.py /path/to/models/vits-melo-tts-zh_en
NODE_PATH=$(npm root -g) node render.js --preview 40,95   # 预览帧
NODE_PATH=$(npm root -g) node render.js                   # 完整渲染
```
