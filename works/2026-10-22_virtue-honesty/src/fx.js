// 通用特效库：和人物无关，任何美德短片都能直接用。
// 依赖 index.html 的 ctx / cv / W / H / HC / HR / T / S / rng / lin / eout / eio / mix / noise / clamp（调用时取）；
// 劈开转场的刀痕取 FIG.SLASH（人物文件里定义）。

// ---------- 第一幕 ----------
function embers(t) { // 上升的火星
  const r = rng(77), k = lin(t, 1, 6);
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  for (let i = 0; i < 120; i++) {
    const x0 = r() * W, sp = 40 + r() * 120, ph = r() * 20, sz = 1 + r() * 2.8, life = 3 + r() * 3;
    if (i > 120 * k) continue;
    const age = (t + ph) % life, x = x0 + Math.sin(t * 1.3 + i) * 30 + age * 10, y = H + 20 - age * sp - (r() * 200);
    const a = Math.sin(age / life * Math.PI) * (.5 + .5 * Math.sin(t * 13 + i));
    ctx.fillStyle = `rgba(255,${120 + (i % 5) * 20},40,${a})`; ctx.fillRect(x, y, sz, sz);
  }
  ctx.restore();
}
const CRACKS = (() => { // 人像周围逐条亮起的裂纹
  const r = rng(31), a = [];
  for (let i = 0; i < 9; i++) {
    let x = HC[0] + (r() - .5) * 200, y = HC[1] + (r() - .5) * 300, ang = r() * Math.PI * 2; const pts = [[x, y]];
    for (let j = 0; j < 14; j++) { ang += (r() - .5) * 1.1; const l = 30 + r() * 50; x += Math.cos(ang) * l; y += Math.sin(ang) * l; pts.push([x, y]); }
    a.push({ pts, t0: 6.6 + i * .2 });
  }
  return a;
})();
function cracks(t) {
  ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.lineCap = 'round';
  for (const c of CRACKS) {
    const k = lin(t, c.t0, c.t0 + .5); if (k <= 0) continue;
    const n = Math.max(2, Math.ceil(c.pts.length * k)), p = new Path2D(); p.moveTo(...c.pts[0]);
    for (let i = 1; i < n; i++) p.lineTo(...c.pts[i]);
    const fl = .7 + .3 * Math.sin(t * 30 + c.t0 * 10);
    ctx.strokeStyle = `rgba(255,70,30,${.4 * fl})`; ctx.lineWidth = 6; ctx.shadowColor = '#ff2000'; ctx.shadowBlur = 20; ctx.stroke(p);
    ctx.strokeStyle = `rgba(255,220,180,${.7 * fl})`; ctx.lineWidth = 1.4; ctx.shadowBlur = 0; ctx.stroke(p);
  }
  ctx.restore();
}
// 心跳：4.4s 起越来越快（audio.py 用同一公式）
const heartbeats = (() => { const a = []; let hb = 4.4; while (hb < 8.95) { a.push(hb); hb += Math.max(.38, .85 - (hb - 4.4) * .11); } return a; })();
function pulse(t) { // 心跳同步的红色暗角
  let a = 0;
  for (const h of heartbeats) { const d = t - h; if (d >= 0 && d < .35) a = Math.max(a, (1 - d / .35) ** 2); }
  if (a <= 0) return;
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  const g = ctx.createRadialGradient(W / 2, H / 2, H * .2, W / 2, H / 2, H);
  g.addColorStop(0, 'rgba(120,0,0,0)'); g.addColorStop(1, `rgba(200,20,10,${.35 * a})`);
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); ctx.restore();
}
const GLITCH = [2.1, 3.4, 4.6, 5.9, 6.7, 7.3, 7.8, 8.25, 8.6]; // audio.py 同步
const gbuf = document.createElement('canvas'); gbuf.width = W; gbuf.height = H;
function glitch(t) { // 画面撕裂：切片错位 + 红青色线
  const g = GLITCH.find(g0 => t >= g0 && t < g0 + .1 + (g0 > 7 ? .05 : 0)); if (g === undefined) return;
  const r = rng(Math.floor(t * 30) + 5), gc = gbuf.getContext('2d');
  gc.clearRect(0, 0, W, H); gc.drawImage(cv, 0, 0);
  ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0);
  for (let i = 0; i < 9; i++) {
    const y = r() * H, h = 8 + r() * 70, dx = (r() - .5) * 120;
    ctx.drawImage(gbuf, 0, y, W, h, dx, y, W, h);
  }
  ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = .28;
  ctx.drawImage(gbuf, 10, 0); ctx.globalAlpha = .18; ctx.drawImage(gbuf, -8, 2);
  ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 1;
  for (let i = 0; i < 4; i++) { ctx.fillStyle = i % 2 ? 'rgba(80,255,255,.35)' : 'rgba(255,40,40,.45)'; ctx.fillRect(0, r() * H, W, 1 + r() * 3); }
  ctx.restore();
}
function truthFlip(t) { return GLITCH.some(g0 => t >= g0 && t < g0 + .12); } // 撕裂那一下，卡片闪出真相
function scanlines(a) {
  ctx.save(); ctx.fillStyle = `rgba(0,0,0,${a})`;
  for (let y = 0; y < H; y += 4) ctx.fillRect(0, y, W, 1.5);
  ctx.restore();
}

// ---------- 转场 ----------
function slashLine(t) { // 金光斜斩
  const sk = lin(t, T.slash, T.slash + .3); if (sk <= 0) return;
  const { ax, ay, bx, by } = FIG.SLASH, e = eout(sk), ex = mix(ax, bx, e), ey = mix(ay, by, e);
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  ctx.strokeStyle = '#fff6dc'; ctx.lineWidth = 5; ctx.shadowColor = '#ffd27a'; ctx.shadowBlur = 30;
  ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(ex, ey); ctx.stroke();
  ctx.lineWidth = 22; ctx.strokeStyle = 'rgba(255,220,150,.25)'; ctx.stroke();
  ctx.restore();
}
const sbuf = document.createElement('canvas'); sbuf.width = W; sbuf.height = H;
function splitFrame(t) { // 整帧沿刀痕劈成两半错开，缝里透光
  const k = lin(t, T.split, T.flash); if (k <= 0) return;
  const { ax, ay, bx, by } = FIG.SLASH;
  const sc = sbuf.getContext('2d'); sc.clearRect(0, 0, W, H); sc.drawImage(cv, 0, 0);
  const dx = bx - ax, dy = by - ay, L = Math.hypot(dx, dy), ux = dx / L, uy = dy / L, nx = -uy, ny = ux;
  const off = eout(k) * 120, slide = eout(k) * 60, zs = 1 + .2 * eout(k), far = 4000;
  ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.fillStyle = '#fff3d6'; ctx.fillRect(0, 0, W, H);
  for (const sgn of [-1, 1]) {
    const p = new Path2D();
    p.moveTo(ax - ux * far, ay - uy * far); p.lineTo(ax + ux * far, ay + uy * far);
    p.lineTo(ax + ux * far + nx * far * sgn, ay + uy * far + ny * far * sgn); p.lineTo(ax - ux * far + nx * far * sgn, ay - uy * far + ny * far * sgn); p.closePath();
    ctx.save(); ctx.translate(nx * off * sgn - ux * slide * sgn, ny * off * sgn - uy * slide * sgn); ctx.clip(p);
    ctx.translate(W / 2, H / 2); ctx.scale(zs, zs); ctx.translate(-W / 2, -H / 2);
    ctx.drawImage(sbuf, 0, 0);
    ctx.restore();
  }
  ctx.globalCompositeOperation = 'lighter';
  for (const sgn of [-1, 1]) {
    const ox = nx * off * sgn - ux * slide * sgn, oy = ny * off * sgn - uy * slide * sgn;
    ctx.strokeStyle = 'rgba(255,230,170,.9)'; ctx.lineWidth = 4; ctx.shadowColor = '#ffd27a'; ctx.shadowBlur = 40;
    ctx.beginPath(); ctx.moveTo(ax - ux * far + ox, ay - uy * far + oy); ctx.lineTo(ax + ux * far + ox, ay + uy * far + oy); ctx.stroke();
  }
  const cx = (ax + bx) / 2, cy = (ay + by) / 2, gl = ctx.createRadialGradient(cx, cy, 0, cx, cy, 900);
  gl.addColorStop(0, `rgba(255,240,200,${.5 * k})`); gl.addColorStop(1, 'rgba(255,240,200,0)');
  ctx.fillStyle = gl; ctx.fillRect(0, 0, W, H);
  ctx.restore();
}
const SHARDS = (() => { // 闪白后飞散的金色碎片（三成是罪字）
  const r = rng(42), a = [];
  for (let i = 0; i < 220; i++) {
    const x = 1060 + r() * 600, y = 160 + r() * 900, ang = Math.atan2(y - HC[1], x - HC[0]) + (r() - .5) * 1.4;
    a.push({ x, y, vx: Math.cos(ang) * (200 + r() * 900) - 260, vy: Math.sin(ang) * (200 + r() * 700) - 120, s: 6 + r() * 22, rot: r() * 6, vr: (r() - .5) * 8, ch: r() < .35 ? S.chars[i % S.chars.length] : null, gold: r() });
  }
  return a;
})();
function shards(t) {
  const age = t - T.flash; if (age < 0 || age > 3.2) return;
  ctx.save();
  for (const s of SHARDS) {
    const dt = age, x = s.x + s.vx * dt * (1 - dt * .12), y = s.y + s.vy * dt + 40 * dt * dt, a = clamp(1 - dt / 3) * clamp(dt * 8);
    ctx.save(); ctx.translate(x, y); ctx.rotate(s.rot + s.vr * dt); ctx.globalAlpha = a;
    ctx.fillStyle = s.gold < .7 ? '#f6d48a' : (s.gold < .9 ? '#fff2cf' : '#c9902f'); ctx.shadowColor = 'rgba(255,200,90,.8)'; ctx.shadowBlur = 10;
    if (s.ch) { ctx.font = `${s.s * 1.2}px SerifBlack`; ctx.fillText(s.ch, 0, 0); }
    else { ctx.beginPath(); ctx.moveTo(0, -s.s * .6); ctx.lineTo(s.s * .5, s.s * .1); ctx.lineTo(-s.s * .2, s.s * .5); ctx.closePath(); ctx.fill(); }
    ctx.restore();
  }
  ctx.restore();
}
function shockwaves(t) { // 三重冲击波
  const age = t - T.flash; if (age < 0 || age > 2) return;
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  for (const [d, c] of [[0, 'rgba(255,240,200,'], [.18, 'rgba(255,200,110,'], [.4, 'rgba(255,255,255,']]) {
    const k = lin(age, d, d + 1.3); if (k <= 0 || k >= 1) continue;
    ctx.strokeStyle = c + (.75 * (1 - k)) + ')'; ctx.lineWidth = 4 + 10 * (1 - k); ctx.shadowColor = '#ffcf70'; ctx.shadowBlur = 24;
    ctx.beginPath(); ctx.arc(HC[0], HC[1], 120 + eout(k) * 1400, 0, Math.PI * 2); ctx.stroke();
  }
  ctx.restore();
}

// ---------- 第二幕 ----------
function godRays(t, k) { // 从头顶斜照下来的光柱
  ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = k;
  const O = [1360, -260];
  for (let i = 0; i < 13; i++) {
    const a = Math.PI / 2 + (i - 6) * .13 + Math.sin(t * .25 + i) * .05, w = .03 + (i % 3) * .015, L = 1500;
    const p = new Path2D(); p.moveTo(...O); p.lineTo(O[0] + Math.cos(a - w) * L, O[1] + Math.sin(a - w) * L); p.lineTo(O[0] + Math.cos(a + w) * L, O[1] + Math.sin(a + w) * L); p.closePath();
    const g = ctx.createLinearGradient(O[0], O[1], O[0], O[1] + L);
    g.addColorStop(0, `rgba(255,236,190,${.16 + .08 * Math.sin(t * .8 + i * 1.3)})`); g.addColorStop(.75, 'rgba(255,236,190,0)');
    ctx.fillStyle = g; ctx.fill(p);
  }
  ctx.restore();
}
function flare(x, y, a, len = 900) { // 横向镜头光晕 + 光斑串
  if (a <= 0) return;
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  const g = ctx.createLinearGradient(x - len, y, x + len, y);
  g.addColorStop(0, 'rgba(255,220,160,0)'); g.addColorStop(.5, `rgba(255,248,230,${a})`); g.addColorStop(1, 'rgba(255,220,160,0)');
  ctx.fillStyle = g; ctx.fillRect(x - len, y - 2.5, len * 2, 5);
  ctx.globalAlpha = a * .5; ctx.fillRect(x - len * .6, y - 9, len * 1.2, 18);
  const b = ctx.createRadialGradient(x, y, 0, x, y, 140); b.addColorStop(0, `rgba(255,255,245,${a})`); b.addColorStop(.25, `rgba(255,220,150,${a * .4})`); b.addColorStop(1, 'rgba(255,200,120,0)');
  ctx.globalAlpha = 1; ctx.fillStyle = b; ctx.fillRect(x - 140, y - 140, 280, 280);
  for (const [k, rr, al] of [[.35, 24, .25], [.7, 40, .15], [1.25, 16, .3]]) {
    ctx.fillStyle = `rgba(190,220,255,${a * al})`; ctx.beginPath(); ctx.arc(mix(x, W / 2, k * 2), mix(y, H / 2, k * 2), rr, 0, Math.PI * 2); ctx.fill();
  }
  ctx.restore();
}
function orbitSparks(t, k) { // 绕光环转的光点
  const r = rng(66);
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  for (let i = 0; i < 36; i++) {
    const rad = HR + 20 + r() * 90, sp = (.2 + r() * .35) * (i % 2 ? 1 : -1), ph = r() * 7, sz = 1.5 + r() * 2.5;
    const a = t * sp + ph, x = HC[0] + Math.cos(a) * rad, y = HC[1] + Math.sin(a) * rad * .96;
    ctx.fillStyle = `rgba(255,236,180,${k * (.4 + .6 * Math.sin(t * 4 + i) ** 2)})`;
    ctx.beginPath(); ctx.arc(x, y, sz, 0, Math.PI * 2); ctx.fill();
  }
  ctx.restore();
}
function goldMotes(t, k) { // 缓缓上升的金尘
  if (k <= 0) return;
  const r = rng(55);
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  for (let i = 0; i < 70; i++) {
    const x0 = 700 + r() * 1250, sp = 14 + r() * 30, ph = r() * 50, sz = 1.2 + r() * 2.6, front = r() < .25;
    const y = H + 40 - ((t * sp + ph * 25) % (H + 80)), x = x0 + Math.sin(t * .7 + i * 2.1) * 30;
    ctx.fillStyle = `rgba(255,232,170,${k * (front ? .8 : .45) * (.5 + .5 * Math.sin(t * 3 + i) ** 2)})`;
    ctx.beginPath(); ctx.arc(x, y, front ? sz * 1.6 : sz, 0, Math.PI * 2); ctx.fill();
  }
  ctx.restore();
}
function titleSparks(t) { // 标题落下时迸出光点，之后持续上飘
  const r = rng(44), x0 = 110, age = t - T.title; if (age < 0) return;
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  for (let i = 0; i < 70; i++) {
    const sx = x0 + r() * 480, sy = 520 + r() * 180, ang = -Math.PI / 2 + (r() - .5) * 2.4, v = 80 + r() * 380, life = .8 + r() * 1.2;
    if (age < life) { const d = age, x = sx + Math.cos(ang) * v * d, y = sy + Math.sin(ang) * v * d + 120 * d * d;
      ctx.fillStyle = `rgba(255,226,150,${1 - d / life})`; ctx.fillRect(x, y, 2.5, 2.5); }
    const ph = r() * 6, lf = 2.5 + r() * 2, aa = ((age + ph) % lf) / lf;
    if (age > .6) { ctx.fillStyle = `rgba(255,236,180,${.6 * Math.sin(aa * Math.PI)})`; ctx.fillRect(sx, sy - aa * 120, 2, 2); }
  }
  ctx.restore();
}
function lightSweep(t) { // 斜向扫光
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

// ---------- 全片 ----------
const BOKEH = {};
function bokehSprite(col) {
  if (BOKEH[col]) return BOKEH[col];
  const c = document.createElement('canvas'); c.width = c.height = 128; const g = c.getContext('2d');
  const rg = g.createRadialGradient(64, 64, 0, 64, 64, 62);
  rg.addColorStop(0, `rgba(${col},.55)`); rg.addColorStop(.78, `rgba(${col},.42)`); rg.addColorStop(.9, `rgba(${col},.7)`); rg.addColorStop(1, `rgba(${col},0)`);
  g.fillStyle = rg; g.beginPath(); g.arc(64, 64, 62, 0, Math.PI * 2); g.fill();
  return (BOKEH[col] = c);
}
function bokeh(t, red) { // 前景虚化光斑（景深）；第二幕避开左侧标题区
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
function vignette(a = .8) {
  const g = ctx.createRadialGradient(W / 2, H / 2, H * .35, W / 2, H / 2, H * 1.05);
  g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, `rgba(0,0,0,${a})`);
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
}
const GRAIN = (() => {
  const c = document.createElement('canvas'); c.width = c.height = 512; const g = c.getContext('2d'), im = g.createImageData(512, 512), r = rng(909);
  for (let i = 0; i < im.data.length; i += 4) { const v = 128 + (r() + r() + r() - 1.5) * 120; im.data[i] = im.data[i + 1] = im.data[i + 2] = v; im.data[i + 3] = 255; }
  g.putImageData(im, 0, 0); return c;
})();
let grainPat = null;
function grain(t) { // 胶片颗粒：每帧随机偏移
  grainPat = grainPat || ctx.createPattern(GRAIN, 'repeat');
  const r = rng(Math.floor(t * 30) * 13 + 1);
  ctx.save(); ctx.setTransform(1, 0, 0, 1, Math.floor(r() * 512), Math.floor(r() * 512));
  ctx.globalCompositeOperation = 'overlay'; ctx.globalAlpha = .07; ctx.fillStyle = grainPat; ctx.fillRect(-512, -512, W + 1024, H + 1024);
  ctx.restore();
}
