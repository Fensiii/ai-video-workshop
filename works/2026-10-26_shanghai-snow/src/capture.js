// 用无头 Chromium（SwiftShader WebGL）逐帧调用 window.renderAt(t)，存 JPEG。
// 用法：node capture.js <起始帧> <结束帧> <输出目录> [端口] [scale]
//      node capture.js --still <输出目录> <端口> <scale> t1 t2 ...
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const a = process.argv.slice(2);
  const still = a[0] === '--still';
  const [outDir, port, scale] = still ? [a[1], a[2] || 8765, a[3] || 1] : [a[2], a[3] || 8765, a[4] || 1];
  const times = still ? a.slice(4).map(Number) : null;
  fs.mkdirSync(outDir, { recursive: true });
  const b = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: Math.round(1080 * scale), height: Math.round(1920 * scale) } });
  p.on('pageerror', e => console.log('pageerror:', e.message));
  p.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') console.log('console:', m.text().slice(0, 300)); });
  const t0 = Date.now();
  await p.goto(`http://127.0.0.1:${port}/index.html?scale=${scale}`);
  await p.waitForFunction('window.sceneReady === true', null, { timeout: 300000 });
  console.log('scene ready', (Date.now() - t0) / 1000, 's');
  const save = (name, data) => fs.writeFileSync(`${outDir}/${name}`, Buffer.from(data.split(',')[1], 'base64'));
  if (still) {
    for (const t of times) {
      const s = Date.now();
      save(`t${t.toFixed(1).padStart(5, '0')}.jpg`, await p.evaluate(t => window.renderAt(t), t));
      console.log('t', t, (Date.now() - s) / 1000, 's');
    }
  } else {
    const [s0, s1] = [Number(a[0]), Number(a[1])];
    for (let i = s0; i < s1; i++) {
      save(`f${String(i).padStart(4, '0')}.jpg`, await p.evaluate(t => window.renderAt(t), i / 30));
      if (i % 30 === 0) console.log('frame', i, ((Date.now() - t0) / 1000).toFixed(0), 's');
    }
  }
  await b.close();
})();
