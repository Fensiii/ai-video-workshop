// 七美德金色人像的可替换部件：头饰、五官、胸前徽章、手持道具。
// 依赖 index.html 里的 ctx / glowStroke / catmull / lin / eout / T / S 等全局量（调用时才取）。
const AC = () => S.fig.accent, AG = () => S.fig.glow;
function accentFill(p, blur = 14) { ctx.save(); ctx.fillStyle = AC(); ctx.shadowColor = AG(); ctx.shadowBlur = blur; ctx.fill(p); ctx.restore(); }
function accentStroke(p, w = 2, blur = 10) { ctx.save(); ctx.strokeStyle = AC(); ctx.lineWidth = w; ctx.shadowColor = AG(); ctx.shadowBlur = blur; ctx.stroke(p); ctx.restore(); }
function darkFill(p) { ctx.save(); ctx.fillStyle = '#14100a'; ctx.fill(p); ctx.restore(); }
function circ(x, y, r) { const p = new Path2D(); p.arc(x, y, r, 0, Math.PI * 2); return p; }
function star(x, y, r1, r2, n, rot = 0) {
  const p = new Path2D();
  for (let i = 0; i < n * 2; i++) { const r = i % 2 ? r2 : r1, a = rot - Math.PI / 2 + i * Math.PI / n; i ? p.lineTo(x + Math.cos(a) * r, y + Math.sin(a) * r) : p.moveTo(x + Math.cos(a) * r, y + Math.sin(a) * r); }
  p.closePath(); return p;
}
function heartPath(x, y, s) {
  const p = new Path2D();
  p.moveTo(x, y + s * .9);
  p.bezierCurveTo(x - s * 1.3, y + s * .1, x - s * .9, y - s * .95, x, y - s * .35);
  p.bezierCurveTo(x + s * .9, y - s * .95, x + s * 1.3, y + s * .1, x, y + s * .9);
  p.closePath(); return p;
}
function rays(x, y, r0, r1, n, t, a = .5) {
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  for (let i = 0; i < n; i++) {
    const ang = i / n * Math.PI * 2 + t * .2, l = r1 * (.7 + .3 * Math.sin(t * 2 + i * 1.7));
    const g = ctx.createLinearGradient(x, y, x + Math.cos(ang) * l, y + Math.sin(ang) * l);
    g.addColorStop(0, `rgba(255,240,200,${a})`); g.addColorStop(1, 'rgba(255,240,200,0)');
    ctx.strokeStyle = g; ctx.lineWidth = 1.4;
    ctx.beginPath(); ctx.moveTo(x + Math.cos(ang) * r0, y + Math.sin(ang) * r0); ctx.lineTo(x + Math.cos(ang) * l, y + Math.sin(ang) * l); ctx.stroke();
  }
  ctx.restore();
}

// ---------- 头饰 ----------
function circletPath() { const d = new Path2D(); d.moveTo(1294, 286); d.quadraticCurveTo(1350, 262, 1424, 276); return d; }
function circletPt(u) { const v = 1 - u; return [v * v * 1294 + 2 * v * u * 1350 + u * u * 1424, v * v * 286 + 2 * v * u * 262 + u * u * 276]; }
function drawHead(t, kind) {
  if (kind === 'bare') return;
  if (kind === 'blindfold') {
    const b = new Path2D();
    b.moveTo(1281, 334); b.quadraticCurveTo(1350, 322, 1436, 328); b.lineTo(1438, 356); b.quadraticCurveTo(1350, 350, 1283, 364); b.closePath();
    darkFill(b); glowStroke(b, 2.4, 12);
    const tails = new Path2D();
    const sw = Math.sin(t * 1.6) * 6;
    tails.moveTo(1436, 334); tails.bezierCurveTo(1470, 350, 1480, 390 + sw, 1505, 420 + sw);
    tails.moveTo(1436, 350); tails.bezierCurveTo(1460, 380, 1462, 420 - sw, 1478, 460 - sw);
    glowStroke(tails, 2.6, 12);
    const kn = circ(1438, 342, 9); darkFill(kn); glowStroke(kn, 2, 8);
    glowStroke(circletPath(), 2.4, 12);
    return;
  }
  glowStroke(circletPath(), 3, 14);
  if (kind === 'wreath') {
    for (let i = 0; i < 13; i++) {
      const [x, y] = circletPt(i / 12), side = i % 2 ? 1 : -1;
      ctx.save(); ctx.translate(x, y); ctx.rotate(-.35 + side * .6);
      const leaf = new Path2D(); leaf.ellipse(0, -9 * side, 5, 11, 0, 0, Math.PI * 2);
      darkFill(leaf); glowStroke(leaf, 1.4, 6); ctx.restore();
    }
    for (const u of [.18, .5, .82]) { const [x, y] = circletPt(u); accentFill(star(x, y - 2, 8, 3.5, 5), 12); }
    return;
  }
  for (let i = 0; i < 5; i++) {
    const x = 1305 + i * 27, y = 281 - i * 3.5 - (i == 1 ? 6 : 0), h = i == 1 ? 26 : 15;
    if (i == 1 && kind !== 'circlet') continue;
    const p = new Path2D(); p.moveTo(x - 6, y); p.lineTo(x, y - h); p.lineTo(x + 6, y);
    glowStroke(p, 2, 10);
    ctx.fillStyle = i == 1 ? AC() : '#ffe9b0'; ctx.shadowColor = i == 1 ? AG() : '#ffd27a'; ctx.shadowBlur = 12;
    ctx.beginPath(); ctx.arc(x, y - h - 4, i == 1 ? 5 : 3, 0, 7); ctx.fill(); ctx.shadowBlur = 0;
  }
  const [cx, cy] = circletPt(.27);
  if (kind === 'eye') {
    const e = new Path2D(); e.moveTo(cx - 16, cy - 10); e.quadraticCurveTo(cx, cy - 26, cx + 16, cy - 10); e.quadraticCurveTo(cx, cy + 4, cx - 16, cy - 10); e.closePath();
    darkFill(e); glowStroke(e, 2, 10); accentFill(circ(cx, cy - 11, 4.5), 14);
  } else if (kind === 'cross') {
    const c = new Path2D(); c.rect(cx - 3, cy - 40, 6, 34); c.rect(cx - 12, cy - 30, 24, 6);
    darkFill(c); glowStroke(c, 1.8, 10); accentFill(circ(cx, cy - 27, 3), 12);
  } else if (kind === 'star') {
    const sx = 1352, sy = 168, pul = 1 + .06 * Math.sin(t * 2.4);
    rays(sx, sy, 20, 110, 16, t, .45);
    const g = ctx.createRadialGradient(sx, sy, 0, sx, sy, 70);
    g.addColorStop(0, 'rgba(255,250,220,.6)'); g.addColorStop(1, 'rgba(255,250,220,0)');
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = g; ctx.fillRect(sx - 70, sy - 70, 140, 140); ctx.restore();
    accentFill(star(sx, sy, 30 * pul, 8, 8, t * .1), 24); accentFill(circ(sx, sy, 5), 10);
    const c = new Path2D(); c.moveTo(cx, cy - 6); c.lineTo(cx, cy - 22); glowStroke(c, 2, 8); accentFill(star(cx, cy - 28, 8, 3, 4), 10);
  }
}
function drawFace(kind) {
  const f = new Path2D();
  if (kind !== 'blindfold') {
    f.moveTo(1290, 338); f.quadraticCurveTo(1305, 331, 1322, 337);
    if (kind === 'eye') { // 睁开的眼
      f.moveTo(1292, 354); f.quadraticCurveTo(1305, 344, 1319, 352); f.moveTo(1294, 356); f.quadraticCurveTo(1306, 362, 1317, 355);
    } else {
      f.moveTo(1293, 355); f.quadraticCurveTo(1305, 361, 1318, 354);
      f.moveTo(1302, 361); f.lineTo(1300, 367); f.moveTo(1309, 361); f.lineTo(1309, 368);
    }
  }
  f.moveTo(1272, 422); f.quadraticCurveTo(1280, 424, 1287, 421);
  f.moveTo(1324, 505); f.quadraticCurveTo(1350, 520, 1372, 512);
  glowStroke(f, 1.8, 8);
  if (kind === 'eye') accentFill(circ(1300, 353, 3.2), 10);
}

// ---------- 胸前徽章（原点在徽章中心） ----------
function drawEmblem(kind) {
  const p = new Path2D();
  if (kind === 'drop') { p.moveTo(0, -13); p.bezierCurveTo(9, -2, 10, 4, 0, 11); p.bezierCurveTo(-10, 4, -9, -2, 0, -13); accentFill(p); return; }
  if (kind === 'heart') { accentFill(heartPath(0, -1, 11)); return; }
  if (kind === 'cross') { p.rect(-2.5, -14, 5, 26); p.rect(-9, -7, 18, 5); accentFill(p); return; }
  if (kind === 'star') { accentFill(star(0, 0, 14, 5, 8)); return; }
  if (kind === 'eye') {
    p.moveTo(-14, 0); p.quadraticCurveTo(0, -14, 14, 0); p.quadraticCurveTo(0, 14, -14, 0); accentStroke(p, 2); accentFill(circ(0, 0, 4.5)); return;
  }
  if (kind === 'scales') {
    p.moveTo(0, -13); p.lineTo(0, 12); p.moveTo(-12, -7); p.lineTo(12, -7); p.moveTo(-7, 12); p.lineTo(7, 12);
    p.moveTo(-16, 4); p.quadraticCurveTo(-12, 9, -8, 4); p.moveTo(8, 4); p.quadraticCurveTo(12, 9, 16, 4);
    p.moveTo(-12, -7); p.lineTo(-16, 4); p.moveTo(-12, -7); p.lineTo(-8, 4); p.moveTo(12, -7); p.lineTo(8, 4); p.moveTo(12, -7); p.lineTo(16, 4);
    accentStroke(p, 1.8); return;
  }
  if (kind === 'anchor') {
    p.arc(0, -10, 4, 0, Math.PI * 2); p.moveTo(0, -6); p.lineTo(0, 13); p.moveTo(-7, -2); p.lineTo(7, -2);
    p.moveTo(-12, 4); p.quadraticCurveTo(-8, 14, 0, 13); p.quadraticCurveTo(8, 14, 12, 4);
    accentStroke(p, 2); return;
  }
}

// ---------- 手持道具 ----------
const HAND = [1035, 624];
function sword(x, yTip, yGuard, t) {
  const b = new Path2D(); b.moveTo(x, yTip); b.lineTo(x + 13, yTip + 40); b.lineTo(x + 11, yGuard); b.lineTo(x - 11, yGuard); b.lineTo(x - 13, yTip + 40); b.closePath();
  const g = ctx.createLinearGradient(x - 13, 0, x + 13, 0); g.addColorStop(0, '#b7a37a'); g.addColorStop(.5, '#fff8e6'); g.addColorStop(1, '#8a7650');
  ctx.save(); ctx.fillStyle = g; ctx.shadowColor = 'rgba(255,230,170,.8)'; ctx.shadowBlur = 20; ctx.fill(b); ctx.restore();
  glowStroke(b, 1.6, 8);
  const fuller = new Path2D(); fuller.moveTo(x, yTip + 50); fuller.lineTo(x, yGuard - 10); glowStroke(fuller, 1.2, 4, '#c9a45a');
  const gd = new Path2D(); gd.moveTo(x - 62, yGuard - 6); gd.quadraticCurveTo(x, yGuard + 4, x + 62, yGuard - 6); gd.lineTo(x + 50, yGuard + 10); gd.quadraticCurveTo(x, yGuard + 18, x - 50, yGuard + 10); gd.closePath();
  darkFill(gd); glowStroke(gd, 2.4, 12);
  const grip = new Path2D(); grip.rect(x - 7, yGuard + 14, 14, 64); darkFill(grip); glowStroke(grip, 2, 8);
  const pm = circ(x, yGuard + 88, 10); darkFill(pm); glowStroke(pm, 2, 8); accentFill(circ(x, yGuard + 88, 4), 10);
  accentFill(star(x, yGuard + 4, 7, 3, 4), 12);
}
const PROPS = {
  jugs(t) {
    drawJug(LOWER, t);
    stream(t, eout(lin(t, T.gold + .6, T.gold + 1.6)));
    drawJug(UPPER, t);
  },
  // 正义：天平（逐渐摆平） + 立剑
  scales(t) {
    sword(1185, 760, 975, t);
    const age = Math.max(0, t - T.gold), P = [1035, 512];
    const ang = .26 * Math.exp(-age * .55) * Math.cos(age * 2.4) + .008 * Math.sin(t * 1.3);
    const rod = new Path2D(); rod.moveTo(HAND[0], HAND[1] - 4); rod.lineTo(P[0], P[1] - 8);
    glowStroke(rod, 3.2, 12); const fin = circ(P[0], P[1] - 16, 8); darkFill(fin); glowStroke(fin, 2, 8);
    const L = 138, c = Math.cos(ang), s = Math.sin(ang);
    const E = [[P[0] - L * c, P[1] - L * s], [P[0] + L * c, P[1] + L * s]];
    const beam = new Path2D(); beam.moveTo(...E[0]); beam.lineTo(...E[1]); glowStroke(beam, 3.6, 14);
    for (const [ex, ey] of E) {
      const py = ey + 118, ch = new Path2D();
      ch.moveTo(ex, ey); ch.lineTo(ex - 44, py); ch.moveTo(ex, ey); ch.lineTo(ex + 44, py); ch.moveTo(ex, ey); ch.lineTo(ex, py);
      glowStroke(ch, 1.2, 6);
      const pan = new Path2D(); pan.moveTo(ex - 50, py); pan.quadraticCurveTo(ex, py + 34, ex + 50, py); pan.closePath();
      darkFill(pan); glowStroke(pan, 2.4, 12);
      accentFill(circ(ex, py - 9, 9 + .6 * Math.sin(t * 2)), 20);
      darkFill(circ(ex, ey, 5)); glowStroke(circ(ex, ey, 5), 1.6, 6);
    }
    const piv = circ(...P, 9); darkFill(piv); glowStroke(piv, 2.2, 10); accentFill(circ(...P, 3.5), 10);
  },
  // 明智：手镜 + 油灯
  mirror(t) {
    lamp(1185, 985, t);
    const C = [998, 588], rot = -.22;
    const hd = new Path2D(); hd.moveTo(HAND[0] + 2, HAND[1] + 6); hd.lineTo(C[0] + 22, C[1] + 92);
    glowStroke(hd, 7, 12); glowStroke(hd, 2, 4, '#2a1f10');
    ctx.save(); ctx.translate(...C); ctx.rotate(rot);
    const outer = new Path2D(); outer.ellipse(0, 0, 66, 84, 0, 0, Math.PI * 2);
    const inner = new Path2D(); inner.ellipse(0, 0, 54, 72, 0, 0, Math.PI * 2);
    darkFill(outer); glowStroke(outer, 3.2, 16);
    const g = ctx.createRadialGradient(-12, -20, 0, 0, 0, 80);
    g.addColorStop(0, 'rgba(210,255,245,.85)'); g.addColorStop(.5, 'rgba(70,160,150,.55)'); g.addColorStop(1, 'rgba(15,40,40,.9)');
    ctx.fillStyle = g; ctx.fill(inner); glowStroke(inner, 1.6, 8);
    ctx.save(); ctx.clip(inner);
    const sx = -90 + ((t * 40) % 260);
    const sh = ctx.createLinearGradient(sx - 20, 0, sx + 20, 0); sh.addColorStop(0, 'rgba(255,255,255,0)'); sh.addColorStop(.5, 'rgba(255,255,255,.55)'); sh.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.rotate(.5); ctx.fillStyle = sh; ctx.fillRect(-120, -120, 240, 240); ctx.restore();
    const e = new Path2D(); e.moveTo(-30, 0); e.quadraticCurveTo(0, -26, 30, 0); e.quadraticCurveTo(0, 26, -30, 0);
    ctx.save(); ctx.globalAlpha *= .8; glowStroke(e, 1.6, 8, '#eafffa'); ctx.restore();
    ctx.fillStyle = '#eafffa'; ctx.beginPath(); ctx.arc(0, 0, 7, 0, 7); ctx.fill();
    for (let i = 0; i < 12; i++) { const a = i / 12 * Math.PI * 2; ctx.fillStyle = '#ffe9b0'; ctx.beginPath(); ctx.arc(Math.cos(a) * 60, Math.sin(a) * 78, 2.4, 0, 7); ctx.fill(); }
    ctx.restore();
  },
  // 信念：圣杯 + 发光圣饼 + 打开的书
  chalice(t) {
    book(1180, 985, t);
    const x = 1018, top = 520;
    const cup = new Path2D(); cup.moveTo(x - 48, top); cup.lineTo(x + 48, top); cup.bezierCurveTo(x + 46, top + 52, x + 20, top + 70, x + 6, top + 74);
    cup.lineTo(x + 6, top + 112); cup.quadraticCurveTo(x + 40, top + 120, x + 42, top + 134); cup.lineTo(x - 42, top + 134); cup.quadraticCurveTo(x - 40, top + 120, x - 6, top + 112);
    cup.lineTo(x - 6, top + 74); cup.bezierCurveTo(x - 20, top + 70, x - 46, top + 52, x - 48, top); cup.closePath();
    darkFill(cup); glowStroke(cup, 3, 16);
    const band = new Path2D(); band.moveTo(x - 44, top + 18); band.quadraticCurveTo(x, top + 26, x + 44, top + 18); band.moveTo(x - 14, top + 92); band.lineTo(x + 14, top + 92);
    glowStroke(band, 1.6, 8);
    accentFill(star(x, top + 40, 8, 3, 4), 12);
    const hy = top - 36 + 3 * Math.sin(t * 1.8);
    rays(x, hy, 22, 120, 20, t, .5);
    const host = circ(x, hy, 20); accentFill(host, 30);
    const cr = new Path2D(); cr.moveTo(x, hy - 11); cr.lineTo(x, hy + 11); cr.moveTo(x - 11, hy); cr.lineTo(x + 11, hy);
    glowStroke(cr, 1.6, 4, '#c79a45');
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    const lg = ctx.createLinearGradient(0, hy, 0, top + 10); lg.addColorStop(0, 'rgba(255,245,210,.35)'); lg.addColorStop(1, 'rgba(255,245,210,0)');
    ctx.fillStyle = lg; ctx.fillRect(x - 30, hy, 60, top + 10 - hy); ctx.restore();
  },
  // 希望：缠绳的锚
  anchor(t) {
    const x = 1035, ry = 548;
    const sh = new Path2D(); sh.moveTo(x, ry + 18); sh.lineTo(x, 938);
    glowStroke(sh, 9, 14); glowStroke(sh, 3, 4, '#2a1f10');
    const ring = circ(x, ry, 19); glowStroke(ring, 4, 14);
    const st = new Path2D(); st.moveTo(x - 66, ry + 44); st.lineTo(x + 66, ry + 44);
    glowStroke(st, 7, 12); darkFill(circ(x - 70, ry + 44, 7)); glowStroke(circ(x - 70, ry + 44, 7), 2, 6); darkFill(circ(x + 70, ry + 44, 7)); glowStroke(circ(x + 70, ry + 44, 7), 2, 6);
    const fl = new Path2D(); fl.moveTo(x - 112, 852); fl.bezierCurveTo(x - 100, 930, x - 40, 950, x, 948); fl.bezierCurveTo(x + 40, 950, x + 100, 930, x + 112, 852);
    glowStroke(fl, 8, 14); glowStroke(fl, 2.4, 4, '#2a1f10');
    for (const sgn of [-1, 1]) {
      const tip = new Path2D(); tip.moveTo(x + sgn * 112, 832); tip.lineTo(x + sgn * 130, 872); tip.lineTo(x + sgn * 94, 866); tip.closePath();
      darkFill(tip); glowStroke(tip, 2.4, 10);
    }
    const rope = new Path2D();
    for (let i = 0; i <= 60; i++) { const y = 640 + i * 4.4, xx = x + Math.sin(i * .62 + t * 1.2) * 16; i ? rope.lineTo(xx, y) : rope.moveTo(xx, y); }
    accentStroke(rope, 2.4, 12);
    // 锚尖处冒出的新芽
    const grow = eout(lin(t, T.gold + .8, T.gold + 3));
    if (grow > 0) {
      const sp = new Path2D(); sp.moveTo(x - 112, 852); sp.quadraticCurveTo(x - 150, 820 - 40 * grow, x - 132, 790 - 60 * grow);
      accentStroke(sp, 2.2, 10);
      for (const [u, side] of [[.5, 1], [.85, -1]]) {
        if (grow < u) continue;
        const lx = mix(x - 112, x - 132, u) - 10, ly = mix(852, 790 - 60 * grow, u);
        const lf = new Path2D(); lf.ellipse(lx + side * 12, ly, 12, 5, side * .5, 0, Math.PI * 2); accentFill(lf, 12);
      }
    }
  },
  // 仁爱：燃烧的心 + 面包篮
  heart(t) {
    basket(1180, 985, t);
    const x = 985, y = 560, pul = 1 + .05 * Math.sin(t * 3.2);
    const st = new Path2D(); st.moveTo(HAND[0] - 4, HAND[1]); st.quadraticCurveTo(1010, 610, x + 8, y + 52); glowStroke(st, 3, 10);
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    for (let i = 0; i < 7; i++) {
      const bx = x - 30 + i * 10, sway = noise(t * 3 + i, i) * 10, h = (46 + 30 * Math.sin(i * 2.1) ** 2) * (.85 + .15 * Math.sin(t * 8 + i));
      const p = new Path2D(); p.moveTo(bx - 10, y - 14); p.quadraticCurveTo(bx - 4 + sway * .4, y - 14 - h * .5, bx + sway, y - 14 - h); p.quadraticCurveTo(bx + 6, y - 14 - h * .45, bx + 10, y - 14);
      const g = ctx.createLinearGradient(0, y - 10, 0, y - 14 - h); g.addColorStop(0, 'rgba(255,230,170,.9)'); g.addColorStop(.5, 'rgba(255,140,90,.6)'); g.addColorStop(1, 'rgba(255,80,60,0)');
      ctx.fillStyle = g; ctx.fill(p);
    }
    ctx.restore();
    rays(x, y + 6, 50, 150, 22, t, .35);
    const hp = heartPath(x, y + 8, 46 * pul);
    const g = ctx.createRadialGradient(x - 12, y - 6, 0, x, y + 8, 70);
    g.addColorStop(0, '#fff0e0'); g.addColorStop(.4, AC()); g.addColorStop(1, '#8a2a20');
    ctx.save(); ctx.fillStyle = g; ctx.shadowColor = AG(); ctx.shadowBlur = 40; ctx.fill(hp); ctx.restore();
    glowStroke(hp, 2.6, 14);
    const hl = new Path2D(); hl.moveTo(x - 26, y - 6); hl.quadraticCurveTo(x - 30, y + 14, x - 14, y + 30); glowStroke(hl, 1.6, 6, '#fff4e6');
  },
};
function lamp(x, y, t) {
  const b = new Path2D(); b.moveTo(x - 70, y - 28); b.quadraticCurveTo(x - 60, y + 22, x, y + 24); b.quadraticCurveTo(x + 60, y + 22, x + 64, y - 18);
  b.quadraticCurveTo(x + 30, y - 34, x - 20, y - 30); b.lineTo(x - 70, y - 28); b.closePath();
  darkFill(b); glowStroke(b, 2.8, 14);
  const ft = new Path2D(); ft.ellipse(x, y + 34, 34, 8, 0, 0, Math.PI * 2); darkFill(ft); glowStroke(ft, 2, 8);
  const hd = new Path2D(); hd.moveTo(x + 62, y - 14); hd.bezierCurveTo(x + 100, y - 30, x + 100, y + 20, x + 50, y + 12); glowStroke(hd, 3, 10);
  const fx = x - 72, fy = y - 34, h = 46 + 6 * Math.sin(t * 9) + 4 * Math.sin(t * 13);
  const fl = new Path2D(); fl.moveTo(fx - 11, fy); fl.quadraticCurveTo(fx - 12, fy - h * .5, fx + Math.sin(t * 5) * 4, fy - h); fl.quadraticCurveTo(fx + 12, fy - h * .5, fx + 11, fy); fl.closePath();
  const g = ctx.createRadialGradient(fx, fy - 10, 0, fx, fy - 30, 60); g.addColorStop(0, 'rgba(255,255,240,1)'); g.addColorStop(1, 'rgba(255,200,90,0)');
  ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = g; ctx.fillRect(fx - 60, fy - 90, 120, 120); ctx.restore();
  accentFill(fl, 26);
}
function book(x, y, t) {
  for (const s of [-1, 1]) {
    const p = new Path2D(); p.moveTo(x, y - 30); p.quadraticCurveTo(x + s * 50, y - 46, x + s * 96, y - 36); p.lineTo(x + s * 90, y + 34); p.quadraticCurveTo(x + s * 46, y + 24, x, y + 38); p.closePath();
    darkFill(p); glowStroke(p, 2.6, 12);
    const l = new Path2D(); for (let i = 0; i < 5; i++) { const yy = y - 18 + i * 11; l.moveTo(x + s * 14, yy); l.quadraticCurveTo(x + s * 46, yy - 10, x + s * 80, yy - 4); }
    glowStroke(l, 1, 4, '#c9a45a');
  }
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  const g = ctx.createRadialGradient(x, y - 30, 0, x, y - 30, 120); g.addColorStop(0, `rgba(255,245,210,${.35 + .1 * Math.sin(t * 2)})`); g.addColorStop(1, 'rgba(255,245,210,0)');
  ctx.fillStyle = g; ctx.fillRect(x - 120, y - 150, 240, 200); ctx.restore();
}
function basket(x, y, t) {
  for (const [dx, dy, r] of [[-38, -34, 26], [10, -42, 30], [52, -30, 22]]) {
    const b = new Path2D(); b.ellipse(x + dx, y + dy, r * 1.25, r * .8, -.1, 0, Math.PI * 2);
    darkFill(b); glowStroke(b, 2.2, 10);
    const sc = new Path2D(); sc.moveTo(x + dx - r * .5, y + dy - r * .3); sc.lineTo(x + dx - r * .1, y + dy + r * .2); sc.moveTo(x + dx, y + dy - r * .4); sc.lineTo(x + dx + r * .4, y + dy + r * .1);
    glowStroke(sc, 1.2, 4, '#c9a45a');
  }
  const bk = new Path2D(); bk.moveTo(x - 92, y - 20); bk.lineTo(x + 92, y - 20); bk.lineTo(x + 72, y + 52); bk.lineTo(x - 72, y + 52); bk.closePath();
  darkFill(bk); glowStroke(bk, 2.8, 14);
  const w = new Path2D(); for (let i = 1; i < 4; i++) { const yy = y - 20 + i * 18; w.moveTo(x - 92 + i * 5, yy); w.lineTo(x + 92 - i * 5, yy); }
  for (let i = -3; i <= 3; i++) { w.moveTo(x + i * 26, y - 20); w.lineTo(x + i * 21, y + 52); }
  glowStroke(w, 1.1, 4, '#c9a45a');
  const hd = new Path2D(); hd.moveTo(x - 80, y - 20); hd.bezierCurveTo(x - 70, y - 120, x + 70, y - 120, x + 80, y - 20); glowStroke(hd, 2.6, 10);
}

// ================= 天使篇新增：徽章与道具 =================
const _emb = drawEmblem;
drawEmblem = function (kind) {
  const p = new Path2D();
  if (kind === 'lily') { p.ellipse(0, -5, 4, 9, 0, 0, Math.PI * 2); p.ellipse(-8, 1, 3.5, 8, -.8, 0, Math.PI * 2); p.ellipse(8, 1, 3.5, 8, .8, 0, Math.PI * 2); p.rect(-1.5, 4, 3, 10); accentFill(p); return; }
  if (kind === 'coin') { accentStroke(circ(0, 0, 12), 2); accentFill(circ(0, 0, 6)); return; }
  if (kind === 'hourglass') { p.moveTo(-9, -13); p.lineTo(9, -13); p.lineTo(-9, 13); p.lineTo(9, 13); p.closePath(); accentStroke(p, 2); return; }
  if (kind === 'leaf') { p.moveTo(0, -14); p.quadraticCurveTo(12, 0, 0, 14); p.quadraticCurveTo(-12, 0, 0, -14); accentFill(p); return; }
  if (kind === 'down') { p.moveTo(-11, -7); p.lineTo(11, -7); p.lineTo(0, 12); p.closePath(); accentFill(p); return; }
  _emb(kind);
};
function stemTo(x, y, cx, cy) { const p = new Path2D(); p.moveTo(HAND[0] - 4, HAND[1] + 2); p.quadraticCurveTo(cx, cy, x, y); return p; }
function leafAt(x, y, ang, l, w) { const p = new Path2D(); const c = Math.cos(ang), s = Math.sin(ang); p.moveTo(x, y); p.quadraticCurveTo(x + c * l * .5 - s * w, y + s * l * .5 + c * w, x + c * l, y + s * l); p.quadraticCurveTo(x + c * l * .5 + s * w, y + s * l * .5 - c * w, x, y); return p; }
function lilyFlower(x, y, ang, sz, t, i) {
  ctx.save(); ctx.translate(x, y); ctx.rotate(ang);
  const sway = Math.sin(t * 1.5 + i) * .05; ctx.rotate(sway);
  const pet = new Path2D();
  for (const a of [-.9, -.3, .3, .9]) { const c = Math.cos(a - Math.PI / 2), s = Math.sin(a - Math.PI / 2); pet.moveTo(0, 0); pet.bezierCurveTo(c * sz * .4 - s * sz * .25, s * sz * .4 + c * sz * .25, c * sz * .9 - s * .1, s * sz * .9, c * sz * 1.05 + s * sz * .18, s * sz * 1.05 - c * sz * .18); pet.quadraticCurveTo(c * sz * .5 + s * sz * .3, s * sz * .5 - c * sz * .3, 0, 0); }
  ctx.save(); ctx.fillStyle = 'rgba(255,245,250,.9)'; ctx.shadowColor = AG(); ctx.shadowBlur = 22; ctx.fill(pet); ctx.restore();
  glowStroke(pet, 1.4, 8);
  for (const a of [-.25, 0, .25]) { const st = new Path2D(); st.moveTo(0, 0); st.lineTo(Math.sin(a) * sz * .7, -Math.cos(a) * sz * .7); glowStroke(st, 1, 4); accentFill(circ(Math.sin(a) * sz * .7, -Math.cos(a) * sz * .7, 3), 8); }
  ctx.restore();
}
Object.assign(PROPS, {
  // 贞洁：白百合
  lily(t) {
    glowStroke(stemTo(990, 430, 1010, 540), 3, 10);
    for (const [u, side] of [[.25, 1], [.5, -1], [.7, 1]]) { const y = mix(624, 430, u), x = mix(1031, 990, u) + 6; const lf = leafAt(x, y, side > 0 ? -.5 : Math.PI + .5, 46, 9); ctx.save(); ctx.fillStyle = '#1b1a0c'; ctx.fill(lf); ctx.restore(); glowStroke(lf, 1.6, 8); }
    lilyFlower(990, 432, -.3, 46, t, 0); lilyFlower(1010, 500, .7, 38, t, 1); lilyFlower(972, 540, -.9, 32, t, 2);
    const bud = new Path2D(); bud.ellipse(1036, 470, 7, 18, .5, 0, Math.PI * 2); ctx.save(); ctx.fillStyle = '#fff6f9'; ctx.shadowColor = AG(); ctx.shadowBlur = 14; ctx.fill(bud); ctx.restore();
  },
  // 慷慨：倾倒金币的丰饶之角
  cornucopia(t) {
    const horn = new Path2D(); horn.moveTo(1070, 640); horn.bezierCurveTo(1120, 600, 1110, 520, 1060, 500); horn.bezierCurveTo(1030, 490, 1000, 520, 940, 555);
    horn.lineTo(985, 640); horn.bezierCurveTo(1020, 600, 1050, 600, 1070, 640); horn.closePath();
    darkFill(horn); glowStroke(horn, 2.8, 14);
    const rib = new Path2D(); for (const k of [.3, .5, .7]) { rib.moveTo(mix(1070, 940, k) + 20, mix(640, 555, k) - 40 * Math.sin(k * 3)); rib.lineTo(mix(1070, 985, k), mix(640, 640, k) - 10); } glowStroke(rib, 1.4, 6);
    const mouth = new Path2D(); mouth.ellipse(962, 598, 16, 46, .75, 0, Math.PI * 2); darkFill(mouth); glowStroke(mouth, 2.4, 12);
    const r = rng(12);
    ctx.save();
    for (let i = 0; i < 44; i++) {
      const ph = r(), sp = .55 + r() * .4, life = 1.6, age = ((t * sp + ph * life) % life), vx = -40 - r() * 120, x = 955 + vx * age, y = 610 + 30 * age + 330 * age * age;
      if (t < T.gold + .6 || y > 1100) continue;
      const spin = Math.cos(t * 6 + i * 2), w = 9 * Math.abs(spin) + 1.5;
      ctx.fillStyle = spin > 0 ? '#ffe08a' : '#c99a3a'; ctx.shadowColor = AG(); ctx.shadowBlur = 12;
      ctx.beginPath(); ctx.ellipse(x, y, w, 9, 0, 0, Math.PI * 2); ctx.fill();
    }
    ctx.restore();
    for (let i = 0; i < 6; i++) accentFill(circ(950 + Math.cos(i) * 14, 590 + Math.sin(i * 2) * 20, 8), 14);
    // 地面金光
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; const g = ctx.createRadialGradient(880, 1060, 0, 880, 1060, 260); g.addColorStop(0, 'rgba(255,200,90,.35)'); g.addColorStop(1, 'rgba(255,200,90,0)'); ctx.fillStyle = g; ctx.fillRect(620, 800, 520, 280); ctx.restore();
  },
  // 勤勉：流沙的沙漏 + 书
  hourglass(t) {
    book(1180, 985, t);
    const x = 1000, y = 560, age = clamp((t - T.gold) / 14);
    const plate = new Path2D(); plate.rect(x - 52, y - 104, 104, 12); plate.rect(x - 52, y + 92, 104, 12); darkFill(plate); glowStroke(plate, 2.4, 12);
    const posts = new Path2D(); posts.moveTo(x - 44, y - 92); posts.lineTo(x - 44, y + 92); posts.moveTo(x + 44, y - 92); posts.lineTo(x + 44, y + 92); glowStroke(posts, 3, 10);
    const glass = new Path2D(); glass.moveTo(x - 32, y - 90); glass.bezierCurveTo(x - 34, y - 30, x - 4, y - 14, x - 3, y); glass.bezierCurveTo(x - 4, y + 14, x - 34, y + 30, x - 32, y + 90);
    glass.lineTo(x + 32, y + 90); glass.bezierCurveTo(x + 34, y + 30, x + 4, y + 14, x + 3, y); glass.bezierCurveTo(x + 4, y - 14, x + 34, y - 30, x + 32, y - 90); glass.closePath();
    ctx.save(); ctx.fillStyle = 'rgba(180,220,255,.08)'; ctx.fill(glass); ctx.clip(glass);
    const top = mix(-70, -12, age), bot = mix(84, 22, age);
    ctx.fillStyle = AC(); ctx.shadowColor = AG(); ctx.shadowBlur = 18;
    ctx.fillRect(x - 40, y + top, 80, -top - 4); ctx.beginPath(); ctx.moveTo(x - 40, y + 90); ctx.lineTo(x - 40, y + bot + 20); ctx.quadraticCurveTo(x, y + bot - 14, x + 40, y + bot + 20); ctx.lineTo(x + 40, y + 90); ctx.fill();
    ctx.fillRect(x - 1.5, y, 3, 90);
    for (let i = 0; i < 10; i++) { const yy = y + ((t * 160 + i * 9) % 90); ctx.fillRect(x - 1 + Math.sin(i * 3 + t * 9) * 2, yy, 2, 2); }
    ctx.restore(); glowStroke(glass, 2, 10);
    const hd = new Path2D(); hd.moveTo(HAND[0] - 2, HAND[1]); hd.lineTo(x + 44, y + 70); glowStroke(hd, 3, 8);
  },
  // 忍耐：慢慢烧短的蜡烛 + 慢慢长成开花的幼苗
  candlePlant(t) {
    const g = clamp((t - T.gold - .5) / 13);
    // 花盆
    const pot = new Path2D(); pot.moveTo(1120, 960); pot.lineTo(1240, 960); pot.lineTo(1222, 1050); pot.lineTo(1138, 1050); pot.closePath(); darkFill(pot); glowStroke(pot, 2.6, 12);
    const rim = new Path2D(); rim.rect(1110, 946, 140, 16); darkFill(rim); glowStroke(rim, 2.2, 10);
    const h = 30 + 190 * eio(g), sx = 1180, sy = 946;
    const stem = new Path2D(); stem.moveTo(sx, sy); stem.bezierCurveTo(sx - 20, sy - h * .4, sx + 24, sy - h * .7, sx + 4, sy - h); accentStroke(stem, 2.6, 10);
    for (let i = 0; i < 4; i++) { const u = (i + 1) / 5; if (g < u * .8) continue; const ly = sy - h * u, lx = sx + Math.sin(u * 5) * 14; accentFill(leafAt(lx, ly, i % 2 ? -.6 : Math.PI + .6, 34 * Math.min(1, (g - u * .8) * 5), 9), 10); }
    const bloom = lin(g, .7, 1);
    if (bloom > 0) { const fx = sx + 4, fy = sy - h; for (let i = 0; i < 6; i++) { const a = i / 6 * Math.PI * 2 + t * .1; const pp = new Path2D(); pp.ellipse(fx + Math.cos(a) * 14 * bloom, fy + Math.sin(a) * 14 * bloom, 12 * bloom, 6 * bloom, a, 0, Math.PI * 2); accentFill(pp, 18); } ctx.save(); ctx.fillStyle = '#fff2c8'; ctx.shadowColor = '#ffd27a'; ctx.shadowBlur = 16; ctx.beginPath(); ctx.arc(fx, fy, 6 * bloom, 0, 7); ctx.fill(); ctx.restore(); }
    // 蜡烛
    const x = 1000, base = 640, ch = mix(150, 110, clamp((t - T.gold) / 14));
    const holder = new Path2D(); holder.ellipse(x, base, 50, 12, 0, 0, Math.PI * 2); darkFill(holder); glowStroke(holder, 2.4, 10);
    const hd = new Path2D(); hd.moveTo(HAND[0], HAND[1]); hd.lineTo(x + 40, base); glowStroke(hd, 3, 8);
    const cd = new Path2D(); cd.rect(x - 16, base - ch, 32, ch); ctx.save(); const cg = ctx.createLinearGradient(x - 16, 0, x + 16, 0); cg.addColorStop(0, '#d8cdb8'); cg.addColorStop(.5, '#fff8ea'); cg.addColorStop(1, '#b9ab90'); ctx.fillStyle = cg; ctx.fill(cd); ctx.restore(); glowStroke(cd, 1.6, 8);
    const fy = base - ch - 6, fh = 40 + 5 * Math.sin(t * 8) + 3 * Math.sin(t * 13);
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; const fg = ctx.createRadialGradient(x, fy - 20, 0, x, fy - 20, 110); fg.addColorStop(0, 'rgba(255,240,200,.7)'); fg.addColorStop(1, 'rgba(255,200,120,0)'); ctx.fillStyle = fg; ctx.fillRect(x - 110, fy - 130, 220, 220); ctx.restore();
    const fl = new Path2D(); fl.moveTo(x - 9, fy); fl.quadraticCurveTo(x - 10, fy - fh * .5, x + Math.sin(t * 4) * 3, fy - fh); fl.quadraticCurveTo(x + 10, fy - fh * .5, x + 9, fy); fl.closePath();
    ctx.save(); ctx.fillStyle = '#fff6dc'; ctx.shadowColor = '#ffc860'; ctx.shadowBlur = 30; ctx.fill(fl); ctx.restore();
    accentFill(circ(x, fy - 8, 4), 10);
  },
  // 宽容：橄榄枝 + 绕飞的白鸽
  olive(t) {
    const br = stemTo(930, 470, 1000, 560); glowStroke(br, 3, 10);
    for (let i = 0; i < 9; i++) { const u = .2 + i * .09, x = mix(1031, 930, u), y = mix(624, 470, u) + Math.sin(u * 3) * 14; const lf = leafAt(x, y, (i % 2 ? -1.1 : 2.4) + Math.sin(t + i) * .05, 40, 8); accentFill(lf, 10); if (i % 3 == 1) { ctx.save(); ctx.fillStyle = '#2f3a1a'; ctx.beginPath(); ctx.ellipse(x + 6, y + 10, 6, 8, 0, 0, 7); ctx.fill(); ctx.restore(); glowStroke(circ(x + 6, y + 10, 7), 1.2, 6); } }
    const a = (t - T.gold) * .55, cx = 1060 + Math.cos(a) * 130, cy = 470 + Math.sin(a) * 45, dir = Math.sin(a) > 0 ? 1 : -1;
    dove(cx, cy, dir, t);
  },
  // 谦卑：摘下的王冠，低垂在手中
  crownDown(t) {
    const x = 1000, y = 720;
    const hd = new Path2D(); hd.moveTo(HAND[0], HAND[1]); hd.quadraticCurveTo(1030, 680, x + 30, y - 30); glowStroke(hd, 3, 8);
    ctx.save(); ctx.translate(x, y); ctx.rotate(.55 + .03 * Math.sin(t * 1.2));
    const c = new Path2D(); c.moveTo(-60, 30); c.lineTo(-66, -30); c.lineTo(-36, 0); c.lineTo(-18, -44); c.lineTo(0, -6); c.lineTo(18, -44); c.lineTo(36, 0); c.lineTo(66, -30); c.lineTo(60, 30); c.closePath();
    darkFill(c); glowStroke(c, 2.8, 16);
    const band = new Path2D(); band.rect(-60, 14, 120, 16); darkFill(band); glowStroke(band, 2, 10);
    for (const [px, py] of [[-66, -30], [-18, -44], [18, -44], [66, -30]]) accentFill(circ(px, py - 6, 5), 12);
    for (let i = -2; i <= 2; i++) accentFill(circ(i * 22, 22, 3.5), 10);
    ctx.restore();
    // 王冠上的光尘缓缓落下
    const r = rng(9); ctx.save(); ctx.globalCompositeOperation = 'lighter';
    for (let i = 0; i < 24; i++) { const ph = r() * 3, life = 3, age = (t + ph) % life, xx = x - 30 + r() * 80 + Math.sin(t + i) * 8, yy = y + 20 + age * 70; ctx.fillStyle = `rgba(220,226,255,${.7 * (1 - age / life)})`; ctx.fillRect(xx, yy, 2, 2); }
    ctx.restore();
  },
});
function dove(x, y, dir, t) {
  ctx.save(); ctx.translate(x, y); ctx.scale(dir * 1.5, 1.5);
  const fl = Math.sin(t * 9);
  const body = new Path2D(); body.ellipse(0, 0, 30, 13, -.1, 0, Math.PI * 2);
  const head = circ(-28, -8, 9);
  const tail = new Path2D(); tail.moveTo(24, -2); tail.lineTo(52, -10); tail.lineTo(50, 8); tail.closePath();
  const w1 = new Path2D(); w1.moveTo(-6, -6); w1.quadraticCurveTo(10, -40 * fl - 10, 34, -46 * fl - 6); w1.quadraticCurveTo(20, -14, 10, -2); w1.closePath();
  ctx.save(); ctx.fillStyle = '#fbf7ee'; ctx.shadowColor = AG(); ctx.shadowBlur = 20; ctx.fill(tail); ctx.fill(body); ctx.fill(head); ctx.fill(w1); ctx.restore();
  glowStroke(w1, 1.2, 6);
  ctx.fillStyle = '#c9902f'; ctx.beginPath(); ctx.moveTo(-36, -9); ctx.lineTo(-46, -6); ctx.lineTo(-36, -4); ctx.fill();
  ctx.fillStyle = '#222'; ctx.beginPath(); ctx.arc(-30, -10, 1.8, 0, 7); ctx.fill();
  // 嘴里叼一片橄榄叶
  accentFill(leafAt(-44, -6, 1.9, 16, 4), 6);
  ctx.restore();
}
