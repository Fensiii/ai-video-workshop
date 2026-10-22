// 诚实篇：面具（第一幕戴在脸上、裂开透光）、卡片闪出真相、刀痕劈开画面、面具碎片、
// 第二幕手托真理之光 + 脚下碎成两半的面具，以及全片的前景光斑、扫光、胶片颗粒。
// 依赖 index.html 与 angel.js 的全局量（调用时取）。

// ---------- 第一幕：脸上的微笑面具（侧脸，面朝左） ----------
const MASK_PTS = [
  [1301, 260], [1289, 279], [1280, 305], [1279, 336], [1273, 354], [1261, 374], [1249, 394], [1256, 404], [1268, 408],
  [1265, 416], [1259, 424], [1265, 432], [1261, 443], [1264, 456], [1277, 471], [1297, 479],
  [1318, 471], [1334, 442], [1343, 400], [1347, 352], [1345, 302], [1335, 270], [1319, 256],
];
const MASK = catmull(MASK_PTS, true);
const MASK_EYE = (() => { const p = new Path2D(); p.moveTo(1283, 352); p.quadraticCurveTo(1298, 340, 1314, 349); p.quadraticCurveTo(1298, 359, 1283, 352); p.closePath(); return p; })();
const EYE = [1298, 350];
const earlyMask = t => lin(t, .9, 2.4) * .55;
const MASK_CRACKS = (() => { // 从眼角和嘴角裂开的纹路
  const r = rng(404), a = [];
  const seeds = [[1300, 362, 1.9], [1272, 426, -.6], [1312, 300, 2.6], [1290, 392, .4], [1330, 420, -2.2], [1318, 330, 1.2]];
  seeds.forEach(([x, y, ang], si) => {
    for (let b = 0; b < 2; b++) {
      let px = x, py = y, aa = ang + (b ? .9 : -.4); const pts = [[px, py]];
      for (let j = 0; j < 9; j++) { aa += (r() - .5) * 1.3; const l = 7 + r() * 13; px += Math.cos(aa) * l; py += Math.sin(aa) * l; pts.push([px, py]); }
      a.push({ pts, t0: T.crack + si * .32 + b * .18 });
    }
  });
  return a;
})();
function maskRed(t, a) {
  if (a <= 0) return;
  ctx.save(); ctx.globalAlpha = a;
  // 绑带（飘在脑后）
  const sw = Math.sin(t * 2.2) * 8, sw2 = Math.sin(t * 2.2 + 1) * 10;
  const rib = new Path2D();
  rib.moveTo(1344, 322); rib.bezierCurveTo(1380, 318, 1410, 338 + sw, 1452, 352 + sw);
  rib.moveTo(1345, 336); rib.bezierCurveTo(1378, 350, 1396, 380 + sw2, 1430, 410 + sw2);
  ctx.strokeStyle = '#7a1410'; ctx.lineWidth = 6; ctx.lineCap = 'round'; ctx.stroke(rib);
  ctx.strokeStyle = '#ff5a2a'; ctx.lineWidth = 1.4; ctx.shadowColor = '#ff2a0a'; ctx.shadowBlur = 10; ctx.stroke(rib); ctx.shadowBlur = 0;
  // 瓷白面具，被红光从左边照亮
  const g = ctx.createLinearGradient(1250, 0, 1350, 0);
  g.addColorStop(0, '#f6dcd2'); g.addColorStop(.45, '#d9a99c'); g.addColorStop(1, '#5a2420');
  ctx.fillStyle = g; ctx.shadowColor = 'rgba(255,60,30,.55)'; ctx.shadowBlur = 24; ctx.fill(MASK); ctx.shadowBlur = 0;
  ctx.save(); ctx.clip(MASK);
  // 腮红 + 高光
  const bl = ctx.createRadialGradient(1296, 398, 0, 1296, 398, 30); bl.addColorStop(0, 'rgba(230,60,60,.45)'); bl.addColorStop(1, 'rgba(230,60,60,0)');
  ctx.fillStyle = bl; ctx.fillRect(1260, 360, 80, 80);
  const hl = new Path2D(); hl.moveTo(1292, 272); hl.quadraticCurveTo(1280, 320, 1284, 340); hl.moveTo(1266, 372); hl.lineTo(1255, 392);
  ctx.strokeStyle = 'rgba(255,250,245,.75)'; ctx.lineWidth = 3; ctx.lineCap = 'round'; ctx.stroke(hl);
  ctx.restore();
  ctx.strokeStyle = '#ff7a3a'; ctx.lineWidth = 2; ctx.shadowColor = '#ff3010'; ctx.shadowBlur = 14; ctx.stroke(MASK); ctx.shadowBlur = 0;
  // 描金眉纹、画上去的泪滴、僵硬上扬的笑
  const orn = new Path2D();
  orn.moveTo(1282, 338); orn.quadraticCurveTo(1300, 326, 1322, 334); orn.quadraticCurveTo(1330, 340, 1324, 346);
  ctx.strokeStyle = '#b8862e'; ctx.lineWidth = 1.8; ctx.stroke(orn);
  const tear = new Path2D(); tear.moveTo(1303, 364); tear.quadraticCurveTo(1309, 374, 1303, 380); tear.quadraticCurveTo(1297, 374, 1303, 364);
  ctx.fillStyle = 'rgba(140,20,20,.85)'; ctx.fill(tear);
  const smile = new Path2D(); smile.moveTo(1262, 428); smile.quadraticCurveTo(1282, 436, 1300, 418); smile.quadraticCurveTo(1303, 414, 1301, 410);
  ctx.strokeStyle = '#4a1210'; ctx.lineWidth = 3; ctx.stroke(smile);
  ctx.strokeStyle = 'rgba(255,200,190,.5)'; ctx.lineWidth = 1; ctx.translate(0, 2.5); ctx.stroke(smile); ctx.translate(0, -2.5);
  // 眼洞：里面是燃烧的眼
  ctx.fillStyle = '#0c0202'; ctx.fill(MASK_EYE);
  ctx.globalCompositeOperation = 'lighter';
  const e = (.75 + .25 * Math.sin(t * 7)) * lin(t, .6, 1.6);
  const eg = ctx.createRadialGradient(...EYE, 0, ...EYE, 46);
  eg.addColorStop(0, `rgba(255,240,200,${e})`); eg.addColorStop(.18, `rgba(255,110,40,${e * .8})`); eg.addColorStop(1, 'rgba(255,40,0,0)');
  ctx.fillStyle = eg; ctx.fillRect(EYE[0] - 50, EYE[1] - 50, 100, 100);
  ctx.globalCompositeOperation = 'source-over';
  maskCracks(t);
  ctx.restore();
}
function maskCracks(t) {
  const hbk = heartbeats.reduce((m, h) => { const d = t - h; return d >= 0 && d < .3 ? Math.max(m, 1 - d / .3) : m; }, 0);
  ctx.save(); ctx.clip(MASK); ctx.globalCompositeOperation = 'lighter'; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  for (const c of MASK_CRACKS) {
    const k = lin(t, c.t0, c.t0 + .45); if (k <= 0) continue;
    const n = Math.max(2, Math.ceil(c.pts.length * k)), p = new Path2D(); p.moveTo(...c.pts[0]);
    for (let i = 1; i < n; i++) p.lineTo(...c.pts[i]);
    const fl = (.75 + .25 * Math.sin(t * 31 + c.t0 * 7)) * (.8 + .5 * hbk);
    ctx.strokeStyle = `rgba(255,120,50,${.55 * fl})`; ctx.lineWidth = 6; ctx.shadowColor = '#ff4010'; ctx.shadowBlur = 16; ctx.stroke(p);
    ctx.strokeStyle = `rgba(255,245,215,${.95 * fl})`; ctx.lineWidth = 1.5; ctx.shadowBlur = 0; ctx.stroke(p);
  }
  ctx.restore();
  // 裂开后掉落的瓷片
  const r = rng(505);
  ctx.save();
  for (let i = 0; i < 16; i++) {
    const t0 = T.crack + .4 + r() * (T.grey - T.crack), x0 = 1262 + r() * 70, y0 = 300 + r() * 160, s = 2 + r() * 4, vr = (r() - .5) * 10;
    const age = t - t0; if (age < 0 || age > 2) continue;
    ctx.save(); ctx.translate(x0 - age * 18, y0 + age * 60 + age * age * 160); ctx.rotate(vr * age); ctx.globalAlpha *= 1 - age / 2;
    ctx.fillStyle = '#e9c3b6'; ctx.beginPath(); ctx.moveTo(0, -s); ctx.lineTo(s, s * .6); ctx.lineTo(-s * .8, s * .4); ctx.closePath(); ctx.fill();
    ctx.restore();
  }
  ctx.restore();
}

// ---------- 卡片闪出真相：和画面撕裂同时 ----------
function truthFlip(t) { return GLITCH.some(g0 => t >= g0 && t < g0 + .12); }

// ---------- 转场：刀痕把画面劈成两半 ----------
const SLASH = { ax: 1000, ay: 1050, bx: 1700, by: 80 };
const sbuf = document.createElement('canvas'); sbuf.width = W; sbuf.height = H;
function splitFrame(t) {
  const k = lin(t, T.split, T.flash); if (k <= 0) return;
  const sc = sbuf.getContext('2d'); sc.clearRect(0, 0, W, H); sc.drawImage(cv, 0, 0);
  const dx = SLASH.bx - SLASH.ax, dy = SLASH.by - SLASH.ay, L = Math.hypot(dx, dy), ux = dx / L, uy = dy / L, nx = -uy, ny = ux; // n 指向右下
  const off = eout(k) * 120, slide = eout(k) * 60, zs = 1 + .2 * eout(k);
  ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0);
  // 缝里的光
  ctx.fillStyle = '#fff3d6'; ctx.fillRect(0, 0, W, H);
  const far = 4000;
  for (const sgn of [-1, 1]) {
    const p = new Path2D();
    p.moveTo(SLASH.ax - ux * far, SLASH.ay - uy * far); p.lineTo(SLASH.ax + ux * far, SLASH.ay + uy * far);
    p.lineTo(SLASH.ax + ux * far + nx * far * sgn, SLASH.ay + uy * far + ny * far * sgn); p.lineTo(SLASH.ax - ux * far + nx * far * sgn, SLASH.ay - uy * far + ny * far * sgn); p.closePath();
    ctx.save(); ctx.translate(nx * off * sgn - ux * slide * sgn, ny * off * sgn - uy * slide * sgn); ctx.clip(p);
    ctx.translate(W / 2, H / 2); ctx.scale(zs, zs); ctx.translate(-W / 2, -H / 2);
    ctx.drawImage(sbuf, 0, 0);
    ctx.restore();
  }
  // 劈口的高光边
  ctx.globalCompositeOperation = 'lighter';
  for (const sgn of [-1, 1]) {
    const ox = nx * off * sgn - ux * slide * sgn, oy = ny * off * sgn - uy * slide * sgn;
    ctx.strokeStyle = 'rgba(255,230,170,.9)'; ctx.lineWidth = 4; ctx.shadowColor = '#ffd27a'; ctx.shadowBlur = 40;
    ctx.beginPath(); ctx.moveTo(SLASH.ax - ux * far + ox, SLASH.ay - uy * far + oy); ctx.lineTo(SLASH.ax + ux * far + ox, SLASH.ay + uy * far + oy); ctx.stroke();
  }
  const cx = (SLASH.ax + SLASH.bx) / 2, cy = (SLASH.ay + SLASH.by) / 2, gl = ctx.createRadialGradient(cx, cy, 0, cx, cy, 900);
  gl.addColorStop(0, `rgba(255,240,200,${.5 * k})`); gl.addColorStop(1, 'rgba(255,240,200,0)');
  ctx.fillStyle = gl; ctx.fillRect(0, 0, W, H);
  ctx.restore();
}

// ---------- 第二幕开场：面具碎片飞散 ----------
const MSHARDS = (() => {
  const r = rng(606), a = [];
  for (let i = 0; i < 46; i++) {
    const x = 1255 + r() * 85, y = 265 + r() * 205, ang = Math.atan2(y - 370, x - 1300) + (r() - .5) * 1.2, v = 300 + r() * 900;
    const pts = []; const n = 3 + Math.floor(r() * 3), s = 10 + r() * 26;
    for (let j = 0; j < n; j++) { const aa = j / n * Math.PI * 2 + r() * .8; pts.push([Math.cos(aa) * s * (.5 + r() * .6), Math.sin(aa) * s * (.5 + r() * .6)]); }
    a.push({ x, y, vx: Math.cos(ang) * v - 120, vy: Math.sin(ang) * v * .8 - 160, rot: r() * 6, vr: (r() - .5) * 9, pts, tone: r() });
  }
  return a;
})();
function maskShards(t) {
  const age = t - T.flash; if (age < 0 || age > 2.6) return;
  ctx.save();
  for (const s of MSHARDS) {
    const x = s.x + s.vx * age * (1 - age * .15), y = s.y + s.vy * age + 220 * age * age;
    ctx.save(); ctx.translate(x, y); ctx.rotate(s.rot + s.vr * age); ctx.globalAlpha = clamp(1 - age / 2.6) * clamp(age * 10);
    const p = new Path2D(); s.pts.forEach((q, i) => i ? p.lineTo(...q) : p.moveTo(...q)); p.closePath();
    const hot = clamp(1 - age * 1.4);
    ctx.fillStyle = s.tone < .7 ? `rgb(${236},${mix(200, 226, 1 - hot) | 0},${mix(186, 205, 1 - hot) | 0})` : '#c99a8c';
    ctx.shadowColor = `rgba(255,${mix(120, 210, 1 - hot) | 0},60,.9)`; ctx.shadowBlur = 14; ctx.fill(p);
    ctx.shadowBlur = 0; ctx.strokeStyle = `rgba(255,${mix(110, 220, 1 - hot) | 0},70,.9)`; ctx.lineWidth = 1.4; ctx.stroke(p);
    ctx.restore();
  }
  ctx.restore();
}

// ---------- 前景虚化光斑（景深） ----------
const BOKEH = {};
function bokehSprite(col) {
  if (BOKEH[col]) return BOKEH[col];
  const c = document.createElement('canvas'); c.width = c.height = 128; const g = c.getContext('2d');
  const rg = g.createRadialGradient(64, 64, 0, 64, 64, 62);
  rg.addColorStop(0, `rgba(${col},.55)`); rg.addColorStop(.78, `rgba(${col},.42)`); rg.addColorStop(.9, `rgba(${col},.7)`); rg.addColorStop(1, `rgba(${col},0)`);
  g.fillStyle = rg; g.beginPath(); g.arc(64, 64, 62, 0, Math.PI * 2); g.fill();
  return (BOKEH[col] = c);
}
function bokeh(t, red) {
  const r = rng(red ? 71 : 72), sp = bokehSprite(red ? '255,70,40' : '255,190,90'), sp2 = bokehSprite(red ? '255,150,80' : '200,235,255');
  const k = red ? lin(t, 1.5, 5) : lin(t, T.flash + .3, T.flash + 2.5);
  if (k <= 0) return;
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  for (let i = 0; i < 22; i++) {
    const x0 = r() * W, y0 = r() * H, sz = 40 + r() * 150, vx = (r() - .5) * 30, vy = -8 - r() * 18, ph = r() * 7, alt = r() < .3;
    const x = ((x0 + vx * t) % (W + 300) + W + 300) % (W + 300) - 150, y = ((y0 + vy * t) % (H + 300) + H + 300) % (H + 300) - 150;
    ctx.globalAlpha = k * (.08 + .1 * Math.sin(t * .8 + ph) ** 2) * (sz > 140 ? .7 : 1) * (red ? 1 : .8 * lin(x, 650, 1050));
    ctx.drawImage(alt ? sp2 : sp, x - sz / 2, y - sz / 2, sz, sz);
  }
  ctx.restore();
}

// ---------- 第二幕：斜向扫光 ----------
function lightSweep(t) {
  for (const [t0, dur, a] of [[T.gold + 4.6, 2.6, .14], [T.gold + 11.2, 2.6, .1]]) {
    const k = lin(t, t0, t0 + dur); if (k <= 0 || k >= 1) continue;
    const x = mix(-600, W + 600, eio(k));
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.translate(x, H / 2); ctx.rotate(.38);
    const g = ctx.createLinearGradient(-260, 0, 260, 0);
    g.addColorStop(0, 'rgba(255,236,190,0)'); g.addColorStop(.5, `rgba(255,240,205,${a * Math.sin(k * Math.PI)})`); g.addColorStop(1, 'rgba(255,236,190,0)');
    ctx.fillStyle = g; ctx.fillRect(-260, -1400, 520, 2800);
    ctx.restore();
  }
}

// ---------- 胶片颗粒 ----------
const GRAIN = (() => {
  const c = document.createElement('canvas'); c.width = c.height = 512; const g = c.getContext('2d'), im = g.createImageData(512, 512), r = rng(909);
  for (let i = 0; i < im.data.length; i += 4) { const v = 128 + (r() + r() + r() - 1.5) * 120; im.data[i] = im.data[i + 1] = im.data[i + 2] = v; im.data[i + 3] = 255; }
  g.putImageData(im, 0, 0); return c;
})();
let grainPat = null;
function grain(t) {
  grainPat = grainPat || ctx.createPattern(GRAIN, 'repeat');
  const f = Math.floor(t * 30), r = rng(f * 13 + 1);
  ctx.save(); ctx.setTransform(1, 0, 0, 1, Math.floor(r() * 512), Math.floor(r() * 512));
  ctx.globalCompositeOperation = 'overlay'; ctx.globalAlpha = .07; ctx.fillStyle = grainPat; ctx.fillRect(-512, -512, W + 1024, H + 1024);
  ctx.restore();
}

// ---------- 第二幕：胸前的太阳徽章 ----------
const _emb2 = drawEmblem;
drawEmblem = function (kind) {
  if (kind === 'sun') {
    const p = new Path2D();
    for (let i = 0; i < 12; i++) { const a = i / 12 * Math.PI * 2, r0 = 9, r1 = i % 2 ? 14 : 17; p.moveTo(Math.cos(a) * r0, Math.sin(a) * r0); p.lineTo(Math.cos(a) * r1, Math.sin(a) * r1); }
    accentStroke(p, 1.8); accentFill(circ(0, 0, 6.5), 14); return;
  }
  _emb2(kind);
};

// ---------- 第二幕道具：举起的真理之光 + 脚下碎成两半的面具 ----------
function brokenMask(x, y, t) {
  const age = t - T.gold, k = eout(lin(age, .6, 1.8));
  if (k <= 0) return;
  ctx.save(); ctx.globalAlpha *= k; ctx.translate(x, y); ctx.rotate(-.42); ctx.scale(1.05, .9);
  // 脸形（正面），沿一条折线裂成左右两半，右半略往外错开
  const face = catmull([[0, -82], [30, -76], [50, -56], [57, -25], [54, 10], [44, 42], [26, 66], [0, 80], [-26, 66], [-44, 42], [-54, 10], [-57, -25], [-50, -56], [-30, -76]], true);
  const crack = [[14, -90], [4, -52], [12, -30], [-4, -4], [6, 20], [-6, 48], [2, 90]];
  for (const side of [-1, 1]) {
    ctx.save();
    if (side > 0) { ctx.translate(14, 8); ctx.rotate(.12); }
    const half = new Path2D(); half.moveTo(side * 120, -100); crack.forEach(q => half.lineTo(...q)); half.lineTo(side * 120, 100); half.closePath();
    ctx.save(); ctx.clip(half);
    darkFill(face);
    ctx.save(); ctx.clip(face); const sh = ctx.createLinearGradient(-60, -80, 60, 80); sh.addColorStop(0, 'rgba(255,220,150,.16)'); sh.addColorStop(1, 'rgba(0,0,0,0)'); ctx.fillStyle = sh; ctx.fillRect(-70, -90, 140, 180); ctx.restore();
    glowStroke(face, 2.4, 12);
    // 眼洞、鼻梁、僵住的笑
    const f = new Path2D();
    for (const s of [-1, 1]) { f.moveTo(s * 34, -16); f.quadraticCurveTo(s * 22, -28, s * 9, -18); f.quadraticCurveTo(s * 22, -10, s * 34, -16); f.closePath(); }
    const fe = new Path2D(); for (const s of [-1, 1]) { fe.moveTo(s * 40, -36); fe.quadraticCurveTo(s * 24, -46, s * 8, -36); }
    fe.moveTo(0, -26); fe.lineTo(-2, 10); fe.quadraticCurveTo(4, 16, 9, 10);
    fe.moveTo(-26, 34); fe.quadraticCurveTo(0, 56, 26, 34); fe.moveTo(-26, 34); fe.lineTo(-30, 28); fe.moveTo(26, 34); fe.lineTo(30, 28);
    ctx.fillStyle = '#050403'; ctx.fill(f); glowStroke(f, 1.4, 6); glowStroke(fe, 1.4, 6);
    ctx.restore();
    // 断口
    const edge = new Path2D(); crack.forEach((q, i) => i ? edge.lineTo(...q) : edge.moveTo(...q));
    ctx.save(); ctx.clip(face); glowStroke(edge, 1.6, 8); ctx.restore();
    ctx.restore();
  }
  // 断口里残余的红光慢慢熄灭，透出白光
  const ember = 1 - lin(age, .8, 4.5);
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  const cg = ctx.createLinearGradient(0, -80, 0, 80);
  cg.addColorStop(0, `rgba(255,${mix(240, 90, ember) | 0},${mix(255, 50, ember) | 0},.0)`); cg.addColorStop(.5, `rgba(255,${mix(244, 90, ember) | 0},${mix(255, 50, ember) | 0},${.55})`); cg.addColorStop(1, 'rgba(255,255,255,0)');
  const gap = new Path2D(); crack.forEach((q, i) => i ? gap.lineTo(q[0] + 7, q[1] + 4) : gap.moveTo(q[0] + 7, q[1] + 4));
  ctx.strokeStyle = cg; ctx.lineWidth = 9; ctx.shadowColor = ember > .3 ? '#ff4010' : AG(); ctx.shadowBlur = 22; ctx.stroke(gap);
  ctx.restore();
  // 绑带垂在地上
  const sw = Math.sin(t * 1.3) * 3, rb = new Path2D();
  rb.moveTo(-56, -20); rb.bezierCurveTo(-90, -10, -96, 30 + sw, -130, 44 + sw); rb.moveTo(70, -14); rb.bezierCurveTo(100, 0, 110, 40 - sw, 148, 50 - sw);
  glowStroke(rb, 1.6, 6);
  ctx.restore();
  // 地面光晕 + 往上飘的光尘
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  const gg = ctx.createRadialGradient(x, y + 60, 0, x, y + 60, 230); gg.addColorStop(0, `rgba(255,220,150,${.22 * k})`); gg.addColorStop(1, 'rgba(255,220,150,0)');
  ctx.fillStyle = gg; ctx.fillRect(x - 230, y - 170, 460, 400);
  const r = rng(707);
  for (let i = 0; i < 26; i++) {
    const ph = r() * 4, life = 3 + r() * 2, a2 = (t + ph) % life, xx = x - 70 + r() * 140 + Math.sin(t * .9 + i) * 10, yy = y + 20 - a2 * 45;
    ctx.fillStyle = `rgba(230,246,255,${.7 * k * Math.sin(a2 / life * Math.PI)})`; ctx.fillRect(xx, yy, 2, 2);
  }
  ctx.restore();
}
function truthLight(x, y, t) {
  const age = t - T.gold, k = eout(lin(age, .2, 1.4)), pul = 1 + .05 * Math.sin(t * 2.6);
  if (k <= 0) return;
  ctx.save(); ctx.globalAlpha *= k;
  // 托住光的手掌（掌心向上的弧）
  const palm = new Path2D(); palm.moveTo(HAND[0] - 52, HAND[1] - 6); palm.quadraticCurveTo(HAND[0] - 24, HAND[1] + 16, HAND[0] + 8, HAND[1] - 4);
  glowStroke(palm, 2.6, 10);
  for (const dx of [-44, -32, -20]) { const fg = new Path2D(); fg.moveTo(HAND[0] + dx, HAND[1] + 2); fg.quadraticCurveTo(HAND[0] + dx - 8, HAND[1] - 12, HAND[0] + dx - 4, HAND[1] - 22); glowStroke(fg, 1.8, 6); }
  // 大范围的冷白光
  ctx.globalCompositeOperation = 'lighter';
  const big = ctx.createRadialGradient(x, y, 0, x, y, 420);
  big.addColorStop(0, `rgba(235,248,255,${.42 * pul})`); big.addColorStop(.25, 'rgba(160,215,255,.14)'); big.addColorStop(1, 'rgba(120,190,255,0)');
  ctx.fillStyle = big; ctx.fillRect(x - 420, y - 420, 840, 840);
  // 两层放射光芒：直线 + 波浪
  ctx.save(); ctx.translate(x, y);
  for (let i = 0; i < 24; i++) {
    const a = i / 24 * Math.PI * 2 + t * .12, wavy = i % 2, l = (wavy ? 96 : 130) * pul * (.9 + .1 * Math.sin(t * 3 + i));
    const p = new Path2D();
    if (wavy) { for (let j = 0; j <= 10; j++) { const u = 42 + j / 10 * (l - 42), w = Math.sin(j * 1.6 + t * 4) * 5; const px = Math.cos(a) * u - Math.sin(a) * w, py = Math.sin(a) * u + Math.cos(a) * w; j ? p.lineTo(px, py) : p.moveTo(px, py); } }
    else { p.moveTo(Math.cos(a - .05) * 42, Math.sin(a - .05) * 42); p.lineTo(Math.cos(a) * l, Math.sin(a) * l); p.lineTo(Math.cos(a + .05) * 42, Math.sin(a + .05) * 42); }
    const g = ctx.createRadialGradient(0, 0, 40, 0, 0, l);
    g.addColorStop(0, 'rgba(255,255,255,.95)'); g.addColorStop(1, 'rgba(170,220,255,0)');
    if (wavy) { ctx.strokeStyle = g; ctx.lineWidth = 2.2; ctx.stroke(p); } else { ctx.fillStyle = g; ctx.fill(p); }
  }
  ctx.restore();
  rays(x, y, 50, 260, 28, t, .35);
  for (let i = 0; i < 3; i++) {
    const ph = ((age - 1 + i * .9) % 2.7) / 2.7; if (age < 1 + i * .9) continue;
    ctx.strokeStyle = `rgba(210,240,255,${.5 * (1 - ph) ** 1.5})`; ctx.lineWidth = 1 + 3 * (1 - ph); ctx.shadowColor = AG(); ctx.shadowBlur = 16;
    ctx.beginPath(); ctx.arc(x, y, 40 + eout(ph) * 420, 0, Math.PI * 2); ctx.stroke(); ctx.shadowBlur = 0;
  }
  // 光核：多层同心光球 + 旋转的细环
  for (const [rad, al] of [[60, .25], [44, .5], [34, .9]]) { const cg = ctx.createRadialGradient(x, y, 0, x, y, rad * pul); cg.addColorStop(0, `rgba(255,255,255,${al})`); cg.addColorStop(1, 'rgba(190,230,255,0)'); ctx.fillStyle = cg; ctx.fillRect(x - rad * 1.2, y - rad * 1.2, rad * 2.4, rad * 2.4); }
  ctx.globalCompositeOperation = 'source-over';
  accentFill(circ(x, y, 24 * pul), 40);
  ctx.fillStyle = '#ffffff'; ctx.beginPath(); ctx.arc(x, y, 15 * pul, 0, Math.PI * 2); ctx.fill();
  ctx.save(); ctx.translate(x, y); ctx.globalCompositeOperation = 'lighter';
  for (const [rx, ry, sp, al] of [[62, 20, .7, .7], [70, 24, -.5, .45]]) {
    ctx.save(); ctx.rotate(t * sp); ctx.strokeStyle = `rgba(220,245,255,${al})`; ctx.lineWidth = 1.4; ctx.shadowColor = AG(); ctx.shadowBlur = 12;
    ctx.beginPath(); ctx.ellipse(0, 0, rx, ry, 0, 0, Math.PI * 2); ctx.stroke();
    const a = t * 2.1 * Math.sign(sp); ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(Math.cos(a) * rx, Math.sin(a) * ry, 3, 0, Math.PI * 2); ctx.fill();
    ctx.restore();
  }
  ctx.restore();
  // 十字星芒
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  for (const [ang, len, w] of [[0, 210, 3], [Math.PI / 2, 150, 2.4], [Math.PI / 4, 70, 1.4], [-Math.PI / 4, 70, 1.4]]) {
    ctx.save(); ctx.translate(x, y); ctx.rotate(ang);
    const g = ctx.createLinearGradient(-len, 0, len, 0); g.addColorStop(0, 'rgba(200,235,255,0)'); g.addColorStop(.5, `rgba(255,255,255,${.9 * pul - .1})`); g.addColorStop(1, 'rgba(200,235,255,0)');
    ctx.fillStyle = g; ctx.fillRect(-len, -w / 2, len * 2, w); ctx.restore();
  }
  ctx.restore();
  ctx.restore();
}
Object.assign(PROPS, {
  // 诚实：举起真理之光，脱下的面具碎在脚边
  truth(t) {
    brokenMask(985, 975, t);
    truthLight(1002, 548, t);
  },
});
