# 特斯拉，凭什么？（无配音版）

约 2 分 38 秒、1080p、16:9 的科普短片：开场直接上市值破万亿的高潮，再回到 2008 年的生死关头，然后讲五个原因：第一性原理、OTA、垂直整合、制造、零广告。最后是数据和结尾。

- `story.json`：分镜时间、字幕（`【】` 标金色，`〔〕` 标红色），以及音乐重音点
- `music.py`：用 numpy 合成配乐，输出 `build/music.wav`，重音和画面对齐
- `index.html`：Canvas + DOM 逐帧动画（`renderAt(t)`）
- `render.sh`：4 路并行逐帧渲染，再拼接、混入音乐

```bash
npm install                 # 衬线中文字体 @fontsource/noto-serif-sc
python3 music.py
NODE_PATH=$(npm root -g) node render.js --preview 4,40   # 预览帧
./render.sh                 # 输出 build/tesla-success.mp4
```
