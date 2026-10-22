// 天使篇：翅膀、头顶光圈，以及两幕的追加特效。
// 依赖 index.html 的 ctx / cv / W / H / HC / T / S / rng / lin / eout / eio / mix / noise / glowStroke（调用时取）。

// ---------- 羽毛与翅膀 ----------
function featherPath(p, x, y, ang, len, w) {
  const c = Math.cos(ang), s = Math.sin(ang), P = (u, v) => [x + u * c - v * s, y + u * s + v * c];
  p.moveTo(...P(0, 0));
  p.quadraticCurveTo(...P(len * .45, -w), ...P(len, 0));
  p.quadraticCurveTo(...P(len * .5, w * .75), ...P(0, 0));
}
function boneAt(pts, u) { // 折线上按长度取点
  const seg = []; let tot = 0;
  for (let i = 1; i < pts.length; i++) { const l = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); seg.push(l); tot += l; }
  let d = u * tot;
  for (let i = 0; i < seg.length; i++) {
    if (d <= seg[i] || i === seg.length - 1) { const k = clamp(d / seg[i]); return [mix(pts[i][0], pts[i + 1][0], k), mix(pts[i][1], pts[i + 1][1], k)]; }
    d -= seg[i];
  }
}
// o: {x, y, dir(+1 向右 / -1 向左), s, open(0 收拢 ~ 1 展开), t, red, seed}
function drawWing(o) {
  const { t } = o, r = rng(o.seed);
  const flap = o.red ? noise(t * 9, o.seed) * .05 : .05 * Math.sin(t * 1.7 + o.seed);
  const a = mix(-1.75, -1.05, o.open) + flap, a2 = a + mix(.15, .3, o.open), a3 = a2 + mix(.2, .35, o.open);
  const E = [Math.cos(a) * 170, Math.sin(a) * 170], Wr = [E[0] + Math.cos(a2) * 190, E[1] + Math.sin(a2) * 190], Tp = [Wr[0] + Math.cos(a3) * 95, Wr[1] + Math.sin(a3) * 95];
  const bone = [[0, 0], E, Wr, Tp];
  ctx.save(); ctx.translate(o.x, o.y); ctx.rotate(o.rot || 0); ctx.scale(o.dir * o.s, o.s);
  const layers = [
    { n: 12, u0: .6, u1: 1, len: [235, 315], w: 25, ang: [a + 2.05, a3 + .12] },   // 初级飞羽
    { n: 13, u0: .03, u1: .6, len: [205, 240], w: 27, ang: [a + 2.45, a + 2.1] },   // 次级飞羽
    { n: 18, u0: 0, u1: .97, len: [105, 125], w: 21, ang: [a + 2.35, a3 + .35] },   // 覆羽
    { n: 16, u0: 0, u1: .9, len: [48, 58], w: 15, ang: [a + 2.3, a3 + .5] },        // 小覆羽
  ];
  for (const L of layers) {
    const fills = [], lines = new Path2D();
    for (let i = 0; i < L.n; i++) {
      const u = mix(L.u0, L.u1, i / (L.n - 1)), [bx, by] = boneAt(bone, u);
      const jitter = (r() - .5) * (o.red ? .25 : .05), ragged = o.red ? (.65 + r() * .45) : 1;
      if (o.red && r() < .18) continue; // 残缺的羽毛
      const ang = mix(L.ang[0], L.ang[1], i / (L.n - 1)) + jitter, len = mix(L.len[0], L.len[1], Math.sin(i / (L.n - 1) * Math.PI * .8)) * ragged;
      const p = new Path2D(); featherPath(p, bx, by, ang, len, L.w); fills.push(p); featherPath(lines, bx, by, ang, len, L.w);
      if (L.len[0] > 150) { const c = Math.cos(ang), s = Math.sin(ang); lines.moveTo(bx, by); lines.lineTo(bx + c * len * .85, by + s * len * .85); }
    }
    ctx.fillStyle = o.red ? '#0b0303' : '#17110a';
    for (const p of fills) ctx.fill(p);
    if (!o.red) { ctx.save(); ctx.globalAlpha *= .35; ctx.fillStyle = 'rgba(255,210,130,.25)'; for (const p of fills) ctx.fill(p); ctx.restore(); }
    ctx.save(); ctx.strokeStyle = o.red ? '#ff5a2a' : '#f0c060'; ctx.lineWidth = 1.6 / o.s; ctx.shadowColor = o.red ? '#ff2a0a' : 'rgba(255,190,80,.9)'; ctx.shadowBlur = 12; ctx.stroke(lines); ctx.restore();
  }
  const b = new Path2D(); b.moveTo(0, 0); b.lineTo(...E); b.lineTo(...Wr); b.lineTo(...Tp);
  ctx.save(); ctx.strokeStyle = o.red ? '#ff7a3a' : '#fff0c4'; ctx.lineWidth = 3.2 / o.s; ctx.shadowColor = o.red ? '#ff3010' : '#ffd27a'; ctx.shadowBlur = 18; ctx.stroke(b); ctx.restore();
  ctx.restore();
}
function wings(t, red) {
  const open = red ? .55 + .05 * Math.sin(t * 3) : mix(.25, 1, eout(lin(t, T.flash + .1, T.flash + 2)));
  const k = red ? lin(t, T.figure + .3, T.figure + 2.5) : 1;
  if (k <= 0) return;
  ctx.save(); ctx.globalAlpha *= k;
  ctx.save(); ctx.globalAlpha *= .75; // 远侧翅膀：同样朝后，偏上、略小、略暗
  drawWing({ x: 1462, y: 560, dir: 1, s: .9, rot: -.42, open, t: t + .3, red, seed: 3 });
  ctx.restore();
  drawWing({ x: 1505, y: 612, dir: 1, s: 1.2, open, t, red, seed: 9 });
  ctx.restore();
}
function angelRing(t, k) { // 头顶光圈
  if (k <= 0) return;
  const y = 196 + 5 * Math.sin(t * 1.4);
  ctx.save(); ctx.globalAlpha *= k; ctx.globalCompositeOperation = 'lighter';
  const g = ctx.createRadialGradient(1362, y, 0, 1362, y, 120); g.addColorStop(0, 'rgba(255,240,190,.35)'); g.addColorStop(1, 'rgba(255,240,190,0)');
  ctx.fillStyle = g; ctx.fillRect(1240, y - 120, 244, 240);
  ctx.translate(1362, y); ctx.rotate(-.08);
  ctx.strokeStyle = '#fff2c8'; ctx.lineWidth = 7; ctx.shadowColor = '#ffd27a'; ctx.shadowBlur = 30;
  ctx.beginPath(); ctx.ellipse(0, 0, 74, 17, 0, 0, Math.PI * 2); ctx.stroke();
  ctx.lineWidth = 2; ctx.strokeStyle = '#ffffff'; ctx.stroke();
  ctx.restore();
}

// ---------- 第一幕特效 ----------
function embers(t) {
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
const CRACKS = (() => {
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
    ctx.strokeStyle = `rgba(255,70,30,${.5 * fl})`; ctx.lineWidth = 7; ctx.shadowColor = '#ff2000'; ctx.shadowBlur = 20; ctx.stroke(p);
    ctx.strokeStyle = `rgba(255,220,180,${.9 * fl})`; ctx.lineWidth = 1.6; ctx.shadowBlur = 0; ctx.stroke(p);
  }
  ctx.restore();
}
const heartbeats = (() => { const a = []; let hb = 4.4; while (hb < 8.95) { a.push(hb); hb += Math.max(.38, .85 - (hb - 4.4) * .11); } return a; })();
function pulse(t) {
  let a = 0;
  for (const h of heartbeats) { const d = t - h; if (d >= 0 && d < .35) a = Math.max(a, (1 - d / .35) ** 2); }
  if (a <= 0) return;
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  const g = ctx.createRadialGradient(W / 2, H / 2, H * .2, W / 2, H / 2, H);
  g.addColorStop(0, 'rgba(120,0,0,0)'); g.addColorStop(1, `rgba(200,20,10,${.35 * a})`);
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); ctx.restore();
}
const GLITCH = [2.1, 3.4, 4.6, 5.9, 6.7, 7.3, 7.8, 8.25, 8.6];
const gbuf = document.createElement('canvas'); gbuf.width = W; gbuf.height = H;
function glitch(t) {
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
function scanlines(a) {
  ctx.save(); ctx.fillStyle = `rgba(0,0,0,${a})`;
  for (let y = 0; y < H; y += 4) ctx.fillRect(0, y, W, 1.5);
  ctx.restore();
}

// ---------- 第二幕特效 ----------
function godRays(t, k) {
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
function featherRain(t, k) {
  const r = rng(55);
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  for (let i = 0; i < 46; i++) {
    const x0 = 600 + r() * 1400, sp = 30 + r() * 45, ph = r() * 40, sz = 16 + r() * 22, rot0 = r() * 6, front = r() < .3;
    const y = ((t * sp + ph * 30) % (H + 200)) - 100, x = x0 + Math.sin(t * .9 + i * 2.1) * 50;
    const a = k * (front ? .75 : .4) * clamp((y + 100) / 200);
    const p = new Path2D(); featherPath(p, 0, 0, 0, sz * (front ? 1.4 : 1), sz * .22);
    ctx.save(); ctx.translate(x, y); ctx.rotate(rot0 + Math.sin(t * 1.4 + i) * .9); ctx.globalAlpha = a;
    ctx.fillStyle = 'rgba(255,240,205,.8)'; ctx.fill(p); ctx.restore();
  }
  ctx.restore();
}
const FBURST = (() => {
  const r = rng(88), a = [];
  for (let i = 0; i < 90; i++) { const ang = r() * Math.PI * 2, v = 250 + r() * 900; a.push({ ang, v, sz: 22 + r() * 30, rot: r() * 6, vr: (r() - .5) * 5, x: HC[0] + 120 + (r() - .5) * 300, y: HC[1] + 150 + (r() - .5) * 300 }); }
  return a;
})();
function featherBurst(t) {
  const age = t - T.flash; if (age < 0 || age > 3.5) return;
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  for (const f of FBURST) {
    const dec = 1 - Math.exp(-age * 2.2), x = f.x + Math.cos(f.ang) * f.v * dec / 2.2, y = f.y + Math.sin(f.ang) * f.v * dec / 2.2 + age * age * 25;
    const p = new Path2D(); featherPath(p, 0, 0, 0, f.sz, f.sz * .22);
    ctx.save(); ctx.translate(x, y); ctx.rotate(f.rot + f.vr * age + f.ang); ctx.globalAlpha = clamp(1 - age / 3.5) * .9;
    ctx.fillStyle = '#fff1cf'; ctx.shadowColor = '#ffd27a'; ctx.shadowBlur = 10; ctx.fill(p); ctx.restore();
  }
  // 多重冲击波
  for (const [d, c] of [[0, 'rgba(255,240,200,'], [.18, 'rgba(255,200,110,'], [.4, 'rgba(255,255,255,']]) {
    const k = lin(age, d, d + 1.3); if (k <= 0 || k >= 1) continue;
    ctx.strokeStyle = c + (.75 * (1 - k)) + ')'; ctx.lineWidth = 4 + 10 * (1 - k); ctx.shadowColor = '#ffcf70'; ctx.shadowBlur = 24;
    ctx.beginPath(); ctx.arc(HC[0], HC[1], 120 + eout(k) * 1400, 0, Math.PI * 2); ctx.stroke();
  }
  ctx.restore();
}
function flare(x, y, a, len = 900) {
  if (a <= 0) return;
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  const g = ctx.createLinearGradient(x - len, y, x + len, y);
  g.addColorStop(0, 'rgba(255,220,160,0)'); g.addColorStop(.5, `rgba(255,248,230,${a})`); g.addColorStop(1, 'rgba(255,220,160,0)');
  ctx.fillStyle = g; ctx.fillRect(x - len, y - 2.5, len * 2, 5);
  ctx.globalAlpha = a * .5; ctx.fillRect(x - len * .6, y - 9, len * 1.2, 18);
  const b = ctx.createRadialGradient(x, y, 0, x, y, 140); b.addColorStop(0, `rgba(255,255,245,${a})`); b.addColorStop(.25, `rgba(255,220,150,${a * .4})`); b.addColorStop(1, 'rgba(255,200,120,0)');
  ctx.globalAlpha = 1; ctx.fillStyle = b; ctx.fillRect(x - 140, y - 140, 280, 280);
  for (const [k, rr, al] of [[.35, 24, .25], [.7, 40, .15], [1.25, 16, .3]]) { // 光斑串
    ctx.fillStyle = `rgba(190,220,255,${a * al})`; ctx.beginPath(); ctx.arc(mix(x, W / 2, k * 2), mix(y, H / 2, k * 2), rr, 0, Math.PI * 2); ctx.fill();
  }
  ctx.restore();
}
function orbitSparks(t, k) {
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
