// 用法：
//   VIRTUE=justice node render.js still out_dir t1 t2 ...        # 静帧预览
//   node render.js seg out.mp4 startFrame endFrame # 分段渲染（30fps）
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const FPS = 30;

(async () => {
  const [mode, out, ...rest] = process.argv.slice(2);
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined, args: ['--allow-file-access-from-files'] });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  page.on('pageerror', e => console.error('PAGE ERROR', e.message));
  await page.goto('file://' + path.join(__dirname, 'index.html') + '?v=' + (process.env.VIRTUE || 'temperance'));
  await page.evaluate(() => window.ready);
  const shot = () => page.screenshot({ type: 'jpeg', quality: 93, clip: { x: 0, y: 0, width: 1920, height: 1080 } });
  if (mode === 'still') {
    const fs = require('fs'); fs.mkdirSync(out, { recursive: true });
    for (const t of rest) {
      await page.evaluate(t => window.renderAt(t), +t);
      fs.writeFileSync(path.join(out, `t${(+t).toFixed(2).padStart(6, '0')}.jpg`), await shot());
    }
  } else {
    const [a, b] = rest.map(Number);
    const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
      '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', out], { stdio: ['pipe', 'inherit', 'inherit'] });
    for (let f = a; f < b; f++) {
      await page.evaluate(t => window.renderAt(t), f / FPS);
      if (!ff.stdin.write(await shot())) await new Promise(r => ff.stdin.once('drain', r));
      if (f % 60 === 0) console.log(out, f);
    }
    ff.stdin.end(); await new Promise(r => ff.on('close', r));
  }
  await browser.close();
})();
