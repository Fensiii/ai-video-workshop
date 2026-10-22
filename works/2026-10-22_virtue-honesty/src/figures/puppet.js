// 人物：提线木偶 → 真正的人（诚实）
// 第一幕：被谎言提线操纵的木偶。每撒一次谎（每次心跳）鼻子长一截，鼻子上冒出枝叶；卡片弹出时手被提线一扯。
// 转场：斜斩正好斩断三根提线，木偶一下子垮下来。
// 第二幕：变成真正的少年——金色长鼻缩回、木关节消散、断线飘落化成光；手按胸口，掌心透出真心之光。
// 接口（index.html 调用）：FIG.SLASH / FIG.early / FIG.red / FIG.redTop / FIG.gold / FIG.burst / FIG.flare
const FIG = { cracks: false };                          // 通用红裂纹会像多出来的提线，这里关掉
FIG.SLASH = { ax: 640, ay: 360, bx: 1900, by: 70 };   // 斜斩：从左下到右上，横穿三根提线

// ================= 第一幕：木偶 =================
const HP = [1345, 468];                                  // 头部转轴（脖子顶端）
const P_HEAD = catmull([[1318, 270], [1292, 288], [1276, 315], [1270, 342], [1267, 362], [1266, 384], [1268, 404], [1264, 416], [1270, 430], [1278, 446],
  [1296, 458], [1322, 462], [1352, 458], [1385, 445], [1415, 420], [1432, 385], [1434, 345], [1424, 305], [1400, 278], [1365, 264]], true);
const NB = [1268, 372], NDIR = [Math.cos(Math.PI + .07), Math.sin(Math.PI + .07)], NPERP = [-NDIR[1], NDIR[0]]; // 鼻根、朝向（左、略上扬）、法向（朝上）
const P_TORSO = catmull([[1290, 526], [1258, 566], [1250, 640], [1252, 760], [1258, 900], [1264, 1095], [1490, 1095], [1496, 900], [1500, 760], [1504, 640], [1494, 572], [1452, 530]], true);
const P_CAP = (() => { const p = new Path2D(); p.moveTo(1286, 302); p.quadraticCurveTo(1352, 214, 1495, 204); p.quadraticCurveTo(1452, 252, 1430, 318); p.quadraticCurveTo(1356, 284, 1286, 302); p.closePath(); return p; })(); // 尖顶条纹帽，往后耷拉
const P_HAIR = (() => { const p = new Path2D(); p.moveTo(1404, 300); p.bezierCurveTo(1430, 320, 1440, 370, 1428, 412); p.quadraticCurveTo(1418, 432, 1400, 440); p.bezierCurveTo(1404, 400, 1396, 352, 1384, 316); p.closePath(); return p; })();
const S0 = [1360, 566], E0 = [1300, 705], W0 = [1176, 622];  // 近侧手臂：肩、肘、腕（被提线吊起）
const FS0 = [1468, 566], FE0 = [1545, 668], FW0 = [1600, 580]; // 远侧手臂（在身体后面，也被吊着）
const BC = [1335, 58];                                   // 控制木架中心
const NOSE_BEATS = heartbeats.filter(h => h > 4.8);       // 每次心跳鼻子长一截
const ARM_TUGS = S.cards.map(c => c[0]).filter(c => c > T.figure);

function noseLen(t) { let L = 34; NOSE_BEATS.forEach((b, i) => { L += (60 + 8 * i) * eback(lin(t, b, b + .2)); }); return L; }
let CUT = null;
function pose(t, raw) {
  let ha = .015 * Math.sin(t * 1.4), aa = .05 * Math.sin(t * 1.9), fa = .05 * Math.sin(t * 1.7 + 1), bob = 3 * Math.sin(t * 1.6), ba = .03 * Math.sin(t * 1.3);
  for (const b of NOSE_BEATS) { const d = t - b; if (d >= 0) ha += .05 * Math.exp(-d * 6); }
  ARM_TUGS.forEach((c, i) => { const d = t - c; if (d >= 0) { if (i % 2) fa -= .14 * Math.exp(-d * 7); else aa += .14 * Math.exp(-d * 7); bob -= 5 * Math.exp(-d * 9); ba += (i % 2 ? .025 : -.025) * Math.exp(-d * 7); } });
  if (!raw && CUT) { // 提线被斩断后垮下来
    aa -= .95 * eout(lin(t, CUT[0].tc, CUT[0].tc + .35));
    ha -= .16 * eout(lin(t, CUT[1].tc, CUT[1].tc + .35));
    fa += .95 * eout(lin(t, CUT[2].tc, CUT[2].tc + .35));
    bob += 26 * eio(lin(t, CUT[1].tc, CUT[1].tc + .4));
  }
  return { ha, aa, fa, bob, ba };
}
function rig(t, raw) { // 当前姿态下各挂点的世界坐标
  const p = pose(t, raw), bob = q => [q[0], q[1] + p.bob], head = q => bob(rot(q, HP, p.ha));
  const dir = (a, b) => { const d = [b[0] - a[0], b[1] - a[1]], l = Math.hypot(...d); return [d[0] / l, d[1] / l]; };
  const W = rot(W0, E0, p.aa), f = dir(E0, W), fp = [-f[1], f[0]];
  const FW = rot(FW0, FE0, p.fa), ff = dir(FE0, FW), ffp = [-ff[1], ff[0]];
  const bar = q => rot(q, BC, p.ba);
  return {
    p, head, bob, E: bob(E0), W: bob(W), f, FE: bob(FE0), FW: bob(FW), ff,
    attach: [bob([W[0] + f[0] * 24 + fp[0] * 16, W[1] + f[1] * 24 + fp[1] * 16]), head([1404, 332]), bob([FW[0] + ff[0] * 24 - ffp[0] * 16, FW[1] + ff[1] * 24 - ffp[1] * 16])],
    top: [bar([1125, 58]), bar([1335, 58]), bar([1545, 58])],
  };
}
function inter(p1, p2, q1, q2) {
  const d = (p2[0] - p1[0]) * (q2[1] - q1[1]) - (p2[1] - p1[1]) * (q2[0] - q1[0]);
  const u = ((q1[0] - p1[0]) * (q2[1] - q1[1]) - (q1[1] - p1[1]) * (q2[0] - q1[0])) / d;
  const v = ((q1[0] - p1[0]) * (p2[1] - p1[1]) - (q1[1] - p1[1]) * (p2[0] - p1[0])) / d;
  return { pt: [p1[0] + (p2[0] - p1[0]) * u, p1[1] + (p2[1] - p1[1]) * u], u, v };
}
CUT = (() => { // 斜斩扫过每根线的时刻和位置
  const R = rig(T.slash, true), A = [FIG.SLASH.ax, FIG.SLASH.ay], B = [FIG.SLASH.bx, FIG.SLASH.by];
  return R.attach.map((a, i) => { const x = inter(a, R.top[i], A, B); return { pt: x.pt, u: x.u, tc: T.slash + .3 * (1 - Math.pow(1 - clamp(x.v), 1 / 3)) }; });
})();

function woodGrad(x, y, r) { const g = ctx.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, '#74271a'); g.addColorStop(.6, '#350e08'); g.addColorStop(1, '#160404'); return g; }
function joint(c, r, a = 1) {
  ctx.save(); ctx.globalAlpha *= a;
  ctx.fillStyle = woodGrad(c[0] - r * .3, c[1] - r * .3, r * 1.4); ctx.fill(circ(c[0], c[1], r)); redStroke(circ(c[0], c[1], r), 2, 10);
  ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = 'rgba(255,170,110,.8)'; ctx.fill(circ(c[0] - r * .35, c[1] - r * .35, r * .22));
  ctx.restore();
}
function nosePath(L, base = 10) {
  const tip = [NB[0] + NDIR[0] * L, NB[1] + NDIR[1] * L], p = new Path2D(), a = Math.atan2(NDIR[1], NDIR[0]);
  p.moveTo(NB[0] + NPERP[0] * base, NB[1] + NPERP[1] * base);
  p.lineTo(tip[0] + NPERP[0] * 3, tip[1] + NPERP[1] * 3);
  p.arc(tip[0], tip[1], 3, a - Math.PI / 2, a + Math.PI / 2);
  p.lineTo(NB[0] - NPERP[0] * base, NB[1] - NPERP[1] * base); p.closePath();
  return { p, tip };
}
function leaf(x, y, ang, l, w) { const c = Math.cos(ang), s = Math.sin(ang), p = new Path2D(); p.moveTo(x, y); p.quadraticCurveTo(x + c * l * .5 - s * w, y + s * l * .5 + c * w, x + c * l, y + s * l); p.quadraticCurveTo(x + c * l * .5 + s * w, y + s * l * .5 - c * w, x, y); return p; }
function drawNoseRed(t, a) { // 越说越长的鼻子，长了就冒枝叶
  const L = noseLen(t), { p } = nosePath(L);
  ctx.save(); ctx.globalAlpha *= a;
  const g = ctx.createLinearGradient(NB[0], NB[1] - 12, NB[0], NB[1] + 12); g.addColorStop(0, '#7a2414'); g.addColorStop(.5, '#3a0c07'); g.addColorStop(1, '#170404');
  ctx.fillStyle = g; ctx.shadowColor = 'rgba(255,60,20,.7)'; ctx.shadowBlur = 22; ctx.fill(p); ctx.shadowBlur = 0;
  redStroke(p, 2.2, 12);
  const gr = new Path2D(); // 木纹
  for (const o of [-4, 3]) { gr.moveTo(NB[0] + NDIR[0] * 18 + NPERP[0] * o, NB[1] + NDIR[1] * 18 + NPERP[1] * o); gr.lineTo(NB[0] + NDIR[0] * L * .9 + NPERP[0] * o * .3, NB[1] + NDIR[1] * L * .9 + NPERP[1] * o * .3); }
  ctx.strokeStyle = 'rgba(255,140,90,.35)'; ctx.lineWidth = 1; ctx.stroke(gr);
  for (const [u, side, L0, i] of [[.45, 1, 220, 0], [.7, -1, 360, 1], [.86, 1, 480, 2]]) {
    const gk = eback(lin(L, L0, L0 + 60)); if (gk <= 0) continue;
    const bx = NB[0] + NDIR[0] * L * u, by = NB[1] + NDIR[1] * L * u, ang = -Math.PI / 2 * side - .5 * side + Math.sin(t * 2 + i) * .08;
    const ex = bx + Math.cos(ang) * 46 * gk, ey = by + Math.sin(ang) * 46 * gk, tw = new Path2D(); tw.moveTo(bx, by); tw.quadraticCurveTo(bx - 6, (by + ey) / 2, ex, ey);
    redStroke(tw, 2.6, 8);
    for (const [la, ll] of [[ang - .7, 26], [ang + .5, 22]]) { const lf = leaf(ex, ey, la, ll * gk, 7 * gk); ctx.save(); ctx.fillStyle = '#ff6a3a'; ctx.shadowColor = '#ff3010'; ctx.shadowBlur = 14; ctx.fill(lf); ctx.restore(); }
  }
  // 每长一截，鼻尖迸一圈火星
  ctx.globalCompositeOperation = 'lighter';
  for (const b of NOSE_BEATS) {
    const d = t - b; if (d < 0 || d > .5) continue;
    const r = rng(Math.floor(b * 100)), tip = nosePath(noseLen(b + .2)).tip;
    for (let i = 0; i < 14; i++) { const an = r() * Math.PI * 2, v = 60 + r() * 160; ctx.fillStyle = `rgba(255,200,120,${1 - d / .5})`; ctx.fillRect(tip[0] + Math.cos(an) * v * d, tip[1] + Math.sin(an) * v * d, 2.5, 2.5); }
  }
  ctx.restore();
}
function drawHeadRed(t, a) {
  ctx.save(); ctx.globalAlpha *= a;
  ctx.fillStyle = woodGrad(1300, 330, 190); ctx.fill(P_HEAD);
  ctx.save(); ctx.clip(P_HEAD); // 木纹年轮
  ctx.strokeStyle = 'rgba(255,110,70,.16)'; ctx.lineWidth = 1;
  for (let i = 0; i < 7; i++) { ctx.beginPath(); ctx.ellipse(1392, 372, 30 + i * 16, 42 + i * 18, .2, 0, Math.PI * 2); ctx.stroke(); }
  ctx.restore();
  redStroke(P_HEAD, 2.6, 16);
  ctx.fillStyle = '#2a0705'; ctx.fill(P_HAIR); redStroke(P_HAIR, 1.6, 8); // 漆上去的头发
  const hs = new Path2D(); for (let i = 0; i < 4; i++) { hs.moveTo(1396 + i * 8, 316 + i * 6); hs.quadraticCurveTo(1414 + i * 6, 370, 1404 + i * 6, 428 - i * 4); } ctx.strokeStyle = 'rgba(255,120,80,.35)'; ctx.stroke(hs);
  const ear = new Path2D(); ear.ellipse(1384, 382, 11, 17, .1, 0, Math.PI * 2); ctx.fillStyle = '#2a0906'; ctx.fill(ear); redStroke(ear, 1.6, 6);
  // 帽子（三道条纹 + 帽穗）
  ctx.fillStyle = '#2a0705'; ctx.fill(P_CAP);
  ctx.save(); ctx.clip(P_CAP); ctx.strokeStyle = 'rgba(255,90,55,.62)'; ctx.lineWidth = 11;
  for (const k of [.28, .52, .74]) { ctx.beginPath(); ctx.moveTo(mix(1286, 1495, k) - 40, mix(302, 204, k) + 60); ctx.lineTo(mix(1430, 1495, k) + 30, mix(318, 204, k) - 50); ctx.stroke(); }
  ctx.restore();
  redStroke(P_CAP, 2.2, 12);
  const band = new Path2D(); band.moveTo(1284, 306); band.quadraticCurveTo(1356, 288, 1432, 322); redStroke(band, 6, 10);
  const ts = circ(1500, 203 + Math.sin(t * 3) * 2, 10); ctx.fillStyle = '#3a0c07'; ctx.fill(ts); redStroke(ts, 1.8, 10);
  // 五官：漆上去的圆眼、眉、腮红、笑、下巴的活动缝
  ctx.fillStyle = '#f2d8cc'; ctx.fill(circ(1302, 338, 13)); redStroke(circ(1302, 338, 13), 1.4, 6);
  ctx.fillStyle = '#120202'; ctx.fill(circ(1296, 339, 6.5));
  const br = new Path2D(); br.moveTo(1284, 317); br.quadraticCurveTo(1302, 304, 1320, 314); redStroke(br, 2.4, 8);
  ctx.fillStyle = 'rgba(230,50,40,.5)'; ctx.fill(circ(1314, 394, 15));
  const m = new Path2D(); m.moveTo(1267, 414); m.quadraticCurveTo(1284, 428, 1300, 418); m.moveTo(1300, 418); m.lineTo(1303, 455); m.moveTo(1295, 421); m.lineTo(1297, 456);
  ctx.strokeStyle = '#ff8a5a'; ctx.lineWidth = 2; ctx.stroke(m);
  const se = circ(1404, 332, 5); ctx.strokeStyle = '#ffb080'; ctx.lineWidth = 2; ctx.stroke(se); // 吊线的螺丝眼
  ctx.restore();
}
function drawHand(W, f, a, flip = 1) { // 连指手套式的木手（沿前臂方向）
  ctx.save(); ctx.globalAlpha *= a; ctx.translate(...W); ctx.rotate(Math.atan2(f[1], f[0])); ctx.scale(1, flip);
  const palm = catmull([[2, -14], [24, -19], [46, -16], [58, -6], [58, 6], [46, 15], [22, 17], [2, 13]], true);
  const thumb = catmull([[14, 12], [26, 22], [36, 30], [42, 26], [34, 14]], true);
  ctx.fillStyle = woodGrad(30, -6, 60); ctx.fill(thumb); redStroke(thumb, 1.8, 8); ctx.fill(palm); redStroke(palm, 2, 10);
  const fg = new Path2D(); fg.moveTo(40, -4); fg.lineTo(56, -3); fg.moveTo(40, 5); fg.lineTo(55, 6); ctx.strokeStyle = 'rgba(255,140,90,.6)'; ctx.lineWidth = 1.2; ctx.stroke(fg);
  ctx.restore();
}
function drawArmRed(Sh, E, Wr, f, a, flip = 1) {
  const up = limb(Sh, E, 40, 32), fo = limb(E, Wr, 32, 24);
  ctx.save(); ctx.globalAlpha *= a;
  for (const [l, gx] of [[up, Sh], [fo, E]]) { ctx.fillStyle = woodGrad(gx[0], gx[1], 160); ctx.fill(l); redStroke(l, 2, 10); }
  ctx.restore();
  joint(Sh, 22, a); joint(E, 17, a); drawHand(Wr, f, a, flip); joint(Wr, 11, a);
}
FIG.early = t => { // 黑暗里先亮起一只眼和木头脸的轮廓
  const a = lin(t, .6, 1.6) * (1 - lin(t, T.figure + .4, T.figure + 1.6));
  if (a <= 0) return;
  const R = rig(t);
  ctx.save(); ctx.globalAlpha = a * .45; ctx.translate(0, R.p.bob); ctx.translate(...HP); ctx.rotate(R.p.ha); ctx.translate(-HP[0], -HP[1]);
  ctx.strokeStyle = '#ff4a2a'; ctx.lineWidth = 1.5; ctx.stroke(P_HEAD); ctx.stroke(P_CAP); ctx.stroke(nosePath(34).p);
  ctx.restore();
};
FIG.red = (t, k) => {
  const R = rig(t);
  drawArmRed(R.bob(FS0), R.FE, R.FW, R.ff, k * .85, -1); // 远侧手臂在身体后面
  // 身体：木头躯干里塞满谎话
  ctx.save(); ctx.translate(0, R.p.bob);
  fillWithText(P_TORSO, t, lin(t, T.figure + .6, T.figure + 3.4), k * .95);
  ctx.save(); ctx.globalAlpha = k; ctx.setLineDash([3000 * eio(k), 4000]); redStroke(P_TORSO, 2.6, 16); ctx.restore();
  ctx.save(); ctx.globalAlpha = k * .8; // 腰部关节缝 + 纽扣
  const wl = new Path2D(); wl.moveTo(1253, 790); wl.quadraticCurveTo(1375, 810, 1500, 790); wl.moveTo(1254, 805); wl.quadraticCurveTo(1375, 825, 1500, 805);
  redStroke(wl, 1.6, 6);
  for (const y of [600, 660, 720]) { ctx.fillStyle = '#ff9a6a'; ctx.fill(circ(1274 - (y - 600) * .03, y, 4.5)); }
  ctx.restore();
  // 脖子木轴 + 荷叶领
  const nk = limb([1345, 452], [1346, 514], 24, 24); ctx.globalAlpha = k; ctx.fillStyle = woodGrad(1345, 480, 50); ctx.fill(nk); redStroke(nk, 1.8, 8);
  const col = new Path2D(); col.ellipse(1352, 520, 86, 20, .06, 0, Math.PI * 2); ctx.fillStyle = '#240605'; ctx.fill(col); redStroke(col, 2, 10);
  const sc = new Path2D(); for (let i = 0; i < 9; i++) { const x = 1278 + i * 18.5, y = 528 + Math.sin(i / 8 * Math.PI) * 12; sc.moveTo(x - 9, y); sc.quadraticCurveTo(x, y + 14, x + 9, y); } redStroke(sc, 1.6, 6);
  ctx.globalAlpha = 1; ctx.restore();
  // 头
  ctx.save(); ctx.translate(0, R.p.bob); ctx.translate(...HP); ctx.rotate(R.p.ha); ctx.translate(-HP[0], -HP[1]);
  drawHeadRed(t, k);
  ctx.restore();
  drawArmRed(R.bob(S0), R.E, R.W, R.f, k);
};
function drawStringsRed(R, t, a) {
  ctx.save(); ctx.lineCap = 'round';
  R.attach.forEach((at, i) => {
    const top = R.top[i], c = CUT[i], reveal = eout(lin(t, .8 + i * .3, 3 + i * .3));
    const paths = [];
    if (t < c.tc) { // 绷紧的线，微微颤动
      const m = [(at[0] + top[0]) / 2 + Math.sin(t * 23 + i * 2) * 1.5, (at[1] + top[1]) / 2];
      const p = new Path2D(); p.moveTo(...top); p.quadraticCurveTo(...m, mix(top[0], at[0], reveal), mix(top[1], at[1], reveal)); paths.push(p);
    } else { // 斩断：上半截弹回去，下半截松垮落下
      const d = t - c.tc, up = mix(c.pt[0], top[0], eout(lin(d, 0, .3)) * .6), upY = mix(c.pt[1], top[1], eout(lin(d, 0, .3)) * .6);
      const p1 = new Path2D(); p1.moveTo(...top); p1.quadraticCurveTo(up + 18 * Math.sin(d * 30), (upY + top[1]) / 2, up, upY); paths.push(p1);
      const e = [c.pt[0] - 40 * d, c.pt[1] + 90 * d + 900 * d * d], p2 = new Path2D(); p2.moveTo(...at);
      p2.quadraticCurveTo((at[0] + e[0]) / 2 + 60 * d, (at[1] + e[1]) / 2 + 80 * d, ...e); paths.push(p2);
      const sp = lin(d, 0, .25); // 断口火花
      if (sp < 1) { ctx.save(); ctx.globalCompositeOperation = 'lighter'; const g = ctx.createRadialGradient(...c.pt, 0, ...c.pt, 60); g.addColorStop(0, `rgba(255,250,220,${1 - sp})`); g.addColorStop(1, 'rgba(255,200,120,0)'); ctx.fillStyle = g; ctx.fillRect(c.pt[0] - 60, c.pt[1] - 60, 120, 120); ctx.restore(); }
    }
    for (const p of paths) {
      ctx.save(); ctx.globalAlpha = a; ctx.strokeStyle = 'rgba(255,80,40,.55)'; ctx.lineWidth = 4; ctx.shadowColor = '#ff3010'; ctx.shadowBlur = 14; ctx.stroke(p);
      ctx.strokeStyle = 'rgba(255,215,190,.95)'; ctx.lineWidth = 1.3; ctx.shadowBlur = 0; ctx.stroke(p); ctx.restore();
    }
  });
  ctx.restore();
}
function barPath(len = 230) { return limb([BC[0] - len, BC[1]], [BC[0] + len, BC[1]], 18, 18); }
function drawBarRed(R, t, a) { // 控制木架 + 从上面伸下来攥着它的大手
  ctx.save(); ctx.globalAlpha = a; ctx.translate(...BC); ctx.rotate(R.p.ba); ctx.translate(-BC[0], -BC[1]);
  const bar = barPath(), cross = limb([BC[0], BC[1] - 26], [BC[0], BC[1] + 30], 16, 16);
  ctx.fillStyle = woodGrad(BC[0], BC[1], 260); ctx.fill(cross); redStroke(cross, 1.6, 8); ctx.fill(bar); redStroke(bar, 2, 12);
  for (const x of [1125, 1335, 1545]) { ctx.strokeStyle = '#ffb080'; ctx.lineWidth = 2; ctx.stroke(circ(x, 66, 4)); }
  // 手：掌心从画面顶上压下来，四根手指扣住木架
  const palm = catmull([[1270, -30], [1268, 10], [1286, 36], [1330, 44], [1384, 40], [1416, 22], [1420, -30]], true);
  ctx.fillStyle = '#0c0202'; ctx.fill(palm); redStroke(palm, 1.8, 14);
  for (let i = 0; i < 4; i++) {
    const x = 1290 + i * 32, f = limb([x, 34], [x + 4, 78 + (i == 1 || i == 2 ? 6 : 0)], 26, 20);
    ctx.fillStyle = '#0c0202'; ctx.fill(f); redStroke(f, 1.6, 10);
    const nail = new Path2D(); nail.moveTo(x - 5, 76); nail.quadraticCurveTo(x + 4, 84, x + 12, 76); ctx.strokeStyle = 'rgba(255,140,100,.6)'; ctx.lineWidth = 1.2; ctx.stroke(nail);
  }
  ctx.restore();
}
FIG.redTop = (t, k) => {
  const R = rig(t), sA = clamp(lin(t, .8, 3) * .6 + k * .4);
  if (k > 0) { // 鼻子画在卡片上面
    ctx.save(); ctx.translate(0, R.p.bob); ctx.translate(...HP); ctx.rotate(R.p.ha); ctx.translate(-HP[0], -HP[1]);
    drawNoseRed(t, k);
    ctx.restore();
  }
  drawStringsRed(R, t, sA);
  drawBarRed(R, t, sA);
  // 发光的眼
  const e = lin(t, .6, 1.6) * (.75 + .25 * Math.sin(t * 7)), eye = R.head([1300, 338]);
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  const g = ctx.createRadialGradient(...eye, 0, ...eye, 54);
  g.addColorStop(0, `rgba(255,240,200,${e})`); g.addColorStop(.18, `rgba(255,110,40,${e * .8})`); g.addColorStop(1, 'rgba(255,40,0,0)');
  ctx.fillStyle = g; ctx.fillRect(eye[0] - 60, eye[1] - 60, 120, 120);
  ctx.restore();
};

// ================= 第二幕：真正的少年 =================
// 古典雕像式的侧脸少年：波浪卷发、清楚的下颌线、肩上披斗篷，前臂从斗篷下伸出，手按胸口。
const G_SIL = catmull([[1360, 248], [1326, 254], [1300, 268], [1284, 292], [1278, 318], [1276, 336], [1273, 348], [1266, 364], [1258, 380], [1261, 388], [1271, 391],
  [1270, 399], [1266, 405], [1271, 410], [1268, 416], [1273, 426], [1271, 440], [1280, 455], [1300, 461], [1322, 466], [1329, 500], [1326, 528], [1300, 548],
  [1266, 590], [1246, 660], [1236, 760], [1230, 900], [1226, 1095], [1600, 1095], [1596, 900], [1584, 760], [1566, 660], [1540, 600], [1500, 568], [1446, 540],
  [1420, 520], [1416, 482], [1424, 458], [1440, 420], [1448, 370], [1444, 322], [1428, 284], [1400, 258]], true);
const G_NOSE = [1258, 380];
const GS = [1478, 600], GE = [1452, 800], GW = [1334, 700];   // 肩（斗篷下）、肘（斗篷边）、腕：手按在胸口
const HEART = [1292, 668];
const HAIR_C = [1366, 356], HAIR_R = [92, 108];               // 卷发贴着头骨的椭圆
const hairPt = (a, d = 0) => [HAIR_C[0] + Math.cos(a) * (HAIR_R[0] + d), HAIR_C[1] + Math.sin(a) * (HAIR_R[1] + d)];
const G_HAIR = (() => { // 雕像式小卷发：外缘一圈小卷鼓包，额前、鬓角、后颈各有发卷
  const p = new Path2D(), n = 17, a0 = -2.62, a1 = 1.02;
  p.moveTo(...hairPt(a0, 2));
  for (let i = 1; i <= n; i++) p.quadraticCurveTo(...hairPt(mix(a0, a1, (i - .5) / n), 20 + 4 * Math.sin(i * 2.3)), ...hairPt(mix(a0, a1, i / n), 4));
  p.quadraticCurveTo(1430, 470, 1418, 468); p.quadraticCurveTo(1414, 452, 1408, 446);   // 后颈的发梢
  p.bezierCurveTo(1414, 420, 1408, 388, 1408, 364);                                     // 耳后
  p.bezierCurveTo(1396, 346, 1388, 330, 1368, 326); p.quadraticCurveTo(1372, 346, 1382, 356); // 鬓角
  p.bezierCurveTo(1356, 344, 1336, 320, 1316, 318);                                     // 额角
  p.quadraticCurveTo(1306, 334, 1294, 330); p.quadraticCurveTo(1296, 316, 1286, 308);  // 额前一卷
  p.closePath();
  return p;
})();
const HAIR_CURLS = (() => { // 发卷：小螺旋
  const p = new Path2D(), r = rng(17);
  for (const [k, n, a0, a1] of [[.86, 13, -2.45, .85], [.66, 9, -2.2, .6], [.45, 5, -1.9, .1]]) {
    for (let i = 0; i < n; i++) {
      const a = mix(a0, a1, (i + .5) / n) + (r() - .5) * .08, x = HAIR_C[0] + Math.cos(a) * HAIR_R[0] * k, y = HAIR_C[1] + Math.sin(a) * HAIR_R[1] * k, rr0 = 8 + r() * 3, s0 = a + 1.2;
      p.moveTo(x + Math.cos(s0) * rr0, y + Math.sin(s0) * rr0);
      for (let j = 1; j <= 14; j++) { const u = j / 14, ang = s0 + u * 5.6, rad = rr0 * (1 - u * .7); p.lineTo(x + Math.cos(ang) * rad, y + Math.sin(ang) * rad); }
    }
  }
  return p;
})();
const G_CLOAK = catmull([[1404, 534], [1468, 546], [1532, 566], [1592, 618], [1632, 760], [1652, 920], [1662, 1095], [1450, 1095], [1450, 940], [1462, 820], [1448, 700], [1420, 600]], true);
function drawBoy(t, k) {
  ctx.save(); ctx.globalAlpha *= k;
  const bg = ctx.createLinearGradient(0, 240, 0, 1080); bg.addColorStop(0, '#1d160c'); bg.addColorStop(.5, '#100c07'); bg.addColorStop(1, '#070504');
  ctx.fillStyle = bg; ctx.fill(G_SIL);
  ctx.save(); ctx.clip(G_SIL); // 胸口的光把身体从里面照亮
  const rim = ctx.createRadialGradient(...HEART, 0, ...HEART, 420); rim.addColorStop(0, 'rgba(170,215,255,.22)'); rim.addColorStop(.5, 'rgba(200,150,70,.10)'); rim.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = rim; ctx.fillRect(0, 0, W, H); ctx.restore();
  glowStroke(G_SIL, 3.2, 22);
  // 下颌线、颈部肌肉、锁骨、领口、衣褶
  const b = new Path2D();
  b.moveTo(1288, 457); b.quadraticCurveTo(1342, 462, 1388, 424);
  b.moveTo(1356, 470); b.quadraticCurveTo(1352, 500, 1336, 528);
  b.moveTo(1326, 528); b.quadraticCurveTo(1362, 566, 1412, 546);
  b.moveTo(1252, 700); b.bezierCurveTo(1262, 820, 1256, 950, 1250, 1080); b.moveTo(1330, 790); b.bezierCurveTo(1324, 900, 1332, 990, 1326, 1080); b.moveTo(1396, 820); b.bezierCurveTo(1402, 920, 1396, 1000, 1400, 1080);
  glowStroke(b, 1.5, 8);
  // 卷发
  darkFill(G_HAIR, '#17110a'); glowStroke(G_HAIR, 2.4, 12);
  ctx.save(); ctx.clip(G_HAIR); glowStroke(HAIR_CURLS, 1.2, 5); ctx.restore();
  // 耳朵、眼睛（睁着，直视前方）、眉、鼻翼、嘴角
  const f = new Path2D();
  f.moveTo(1404, 368); f.bezierCurveTo(1382, 362, 1380, 410, 1400, 412); f.moveTo(1398, 376); f.quadraticCurveTo(1390, 388, 1398, 400);
  f.moveTo(1281, 347); f.quadraticCurveTo(1290, 339, 1301, 342); f.moveTo(1282, 349); f.quadraticCurveTo(1291, 354, 1299, 350);
  f.moveTo(1285, 340); f.quadraticCurveTo(1294, 333, 1304, 337);
  f.moveTo(1270, 385); f.quadraticCurveTo(1277, 389, 1278, 382);
  f.moveTo(1268, 409); f.quadraticCurveTo(1274, 411, 1280, 408);
  glowStroke(f, 1.6, 7);
  const brow = new Path2D(); brow.moveTo(1278, 330); brow.quadraticCurveTo(1292, 322, 1310, 326); glowStroke(brow, 2.6, 8);
  ctx.save(); ctx.fillStyle = '#0c0905'; ctx.beginPath(); ctx.ellipse(1287, 347, 3.2, 4.4, 0, 0, Math.PI * 2); ctx.fill(); ctx.restore();
  accentFill(circ(1286, 346, 1.6), 8);
  // 斗篷（盖住后肩和上臂）+ 前襟扣
  darkFill(G_CLOAK, '#120d07'); glowStroke(G_CLOAK, 2.8, 16);
  const cf = new Path2D(); cf.moveTo(1500, 600); cf.bezierCurveTo(1512, 760, 1506, 920, 1520, 1095); cf.moveTo(1560, 640); cf.bezierCurveTo(1580, 800, 1584, 950, 1590, 1095); cf.moveTo(1610, 720); cf.bezierCurveTo(1622, 860, 1626, 980, 1630, 1095);
  glowStroke(cf, 1.3, 6);
  const clasp = circ(1418, 566, 13); darkFill(clasp); glowStroke(clasp, 2, 8); accentFill(circ(1418, 566, 5), 12);
  // 前臂从斗篷边伸出，手贴在胸口
  const fo = limb(GE, GW, 64, 50); darkFill(fo, '#140f08'); glowStroke(fo, 2.4, 12);
  const edge = new Path2D(); edge.moveTo(1446, 690); edge.bezierCurveTo(1462, 760, 1460, 840, 1452, 900); glowStroke(edge, 2.8, 14); // 斗篷前缘压在手臂上
  const cuff = new Path2D(); cuff.moveTo(1370, 690); cuff.lineTo(1346, 746); glowStroke(cuff, 2, 8);
  ctx.save(); ctx.translate(...GW); ctx.rotate(Math.atan2(GW[1] - GE[1], GW[0] - GE[0]) + .12);
  const hand = catmull([[0, -24], [28, -28], [56, -28], [84, -22], [94, -12], [90, -2], [66, 4], [80, 12], [78, 22], [56, 24], [28, 27], [2, 24]], true);
  darkFill(hand, '#18120a'); glowStroke(hand, 2.2, 10);
  const fl = new Path2D(); fl.moveTo(52, -15); fl.lineTo(88, -14); fl.moveTo(50, -5); fl.lineTo(80, -6); fl.moveTo(38, 14); fl.lineTo(70, 15); glowStroke(fl, 1.1, 4);
  ctx.restore();
  ctx.restore();
}
function heartLight(t, k) { // 掌心透出的真心之光
  if (k <= 0) return;
  const [x, y] = HEART, pul = 1 + .06 * Math.sin(t * 2.4), age = t - T.gold;
  ctx.save(); ctx.globalAlpha *= k; ctx.globalCompositeOperation = 'lighter';
  const big = ctx.createRadialGradient(x, y, 0, x, y, 380); big.addColorStop(0, `rgba(235,248,255,${.38 * pul})`); big.addColorStop(.3, 'rgba(150,210,255,.12)'); big.addColorStop(1, 'rgba(120,190,255,0)');
  ctx.fillStyle = big; ctx.fillRect(x - 380, y - 380, 760, 760);
  for (let i = 0; i < 26; i++) { // 从指缝里漏出来的光芒
    const a = -Math.PI * .95 + i / 25 * Math.PI * 1.15 + Math.sin(t * .8 + i) * .03, l = (110 + 70 * Math.sin(i * 2.7) ** 2) * pul;
    const g = ctx.createLinearGradient(x, y, x + Math.cos(a) * l, y + Math.sin(a) * l); g.addColorStop(0, 'rgba(255,255,255,.7)'); g.addColorStop(1, 'rgba(170,220,255,0)');
    ctx.strokeStyle = g; ctx.lineWidth = i % 3 ? 1.2 : 2.4; ctx.beginPath(); ctx.moveTo(x + Math.cos(a) * 26, y + Math.sin(a) * 26); ctx.lineTo(x + Math.cos(a) * l, y + Math.sin(a) * l); ctx.stroke();
  }
  for (const [rad, al] of [[54, .3], [34, .6], [20, .95]]) { const cg = ctx.createRadialGradient(x, y, 0, x, y, rad * pul); cg.addColorStop(0, `rgba(255,255,255,${al})`); cg.addColorStop(1, 'rgba(190,230,255,0)'); ctx.fillStyle = cg; ctx.fillRect(x - rad * 1.2, y - rad * 1.2, rad * 2.4, rad * 2.4); }
  for (let i = 0; i < 3; i++) { // 一圈圈往外扩散的光波（audio.py 同步）
    if (age < 1 + i * .9) continue;
    const ph = ((age - 1 - i * .9) % 2.7) / 2.7;
    ctx.strokeStyle = `rgba(210,240,255,${.45 * (1 - ph) ** 1.5})`; ctx.lineWidth = 1 + 3 * (1 - ph); ctx.shadowColor = AG(); ctx.shadowBlur = 16;
    ctx.beginPath(); ctx.arc(x, y, 30 + eout(ph) * 420, 0, Math.PI * 2); ctx.stroke(); ctx.shadowBlur = 0;
  }
  for (const [ang, len, w] of [[0, 190, 2.6], [Math.PI / 2, 120, 2]]) { // 十字星芒
    ctx.save(); ctx.translate(x, y); ctx.rotate(ang);
    const g = ctx.createLinearGradient(-len, 0, len, 0); g.addColorStop(0, 'rgba(200,235,255,0)'); g.addColorStop(.5, `rgba(255,255,255,${.85 * pul - .1})`); g.addColorStop(1, 'rgba(200,235,255,0)');
    ctx.fillStyle = g; ctx.fillRect(-len, -w / 2, len * 2, w); ctx.restore();
  }
  ctx.restore();
}
function noseRetract(t) { // 金色的长鼻子缩回去，沿途洒下光点
  const age = t - T.gold, k = eout(lin(age, .35, 1.5)), L0 = noseLen(T.slash) - 20, L = L0 * (1 - k);
  if (age > 2.6) return;
  ctx.save(); ctx.globalAlpha *= clamp(1 - lin(age, 1.4, 1.6));
  if (L > 2) {
    const tip = [G_NOSE[0] + NDIR[0] * L, G_NOSE[1] + NDIR[1] * L], p = new Path2D();
    p.moveTo(G_NOSE[0] + NPERP[0] * 7, G_NOSE[1] + NPERP[1] * 7); p.lineTo(tip[0] + NPERP[0] * 2, tip[1] + NPERP[1] * 2); p.lineTo(tip[0] - NPERP[0] * 2, tip[1] - NPERP[1] * 2); p.lineTo(G_NOSE[0] - NPERP[0] * 7, G_NOSE[1] - NPERP[1] * 7); p.closePath();
    darkFill(p, '#1a130a'); glowStroke(p, 2, 12);
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; const g = ctx.createRadialGradient(...tip, 0, ...tip, 40); g.addColorStop(0, 'rgba(255,250,230,.9)'); g.addColorStop(1, 'rgba(255,220,150,0)'); ctx.fillStyle = g; ctx.fillRect(tip[0] - 40, tip[1] - 40, 80, 80); ctx.restore();
  }
  ctx.restore();
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  const r = rng(321);
  for (let i = 0; i < 60; i++) {
    const u = r(), born = .35 + (1.15) * (1 - Math.cbrt(u)), d = age - born, vx = (r() - .5) * 40, vy = -20 - r() * 50;
    if (d < 0 || d > 1.6) continue;
    const x = G_NOSE[0] + NDIR[0] * L0 * u + vx * d, y = G_NOSE[1] + NDIR[1] * L0 * u + vy * d;
    ctx.fillStyle = `rgba(255,236,180,${1 - d / 1.6})`; ctx.beginPath(); ctx.arc(x, y, 2.2, 0, Math.PI * 2); ctx.fill();
  }
  ctx.restore();
}
function jointsFade(t) { // 木偶关节的印子一圈圈散掉
  const age = t - T.gold; if (age > 2.6) return;
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  for (const [c, r0, d0] of [[[1372, 520], 18, .1], [[1468, 600], 26, .2], [GE, 22, .45], [GW, 16, .7]]) {
    const k = lin(age, d0, d0 + 1.6); if (k >= 1) continue;
    ctx.strokeStyle = `rgba(255,220,150,${.8 * (1 - k)})`; ctx.lineWidth = 2; ctx.shadowColor = '#ffd27a'; ctx.shadowBlur = 12;
    ctx.beginPath(); ctx.arc(...c, r0 + eout(k) * 50, 0, Math.PI * 2); ctx.stroke();
    if (k < .3) { ctx.fillStyle = `rgba(255,240,200,${.6 * (1 - k / .3)})`; ctx.fill(circ(...c, r0 * .4)); }
  }
  ctx.restore();
}
FIG.gold = (t, k) => {
  drawBoy(t, k);
  heartLight(t, eout(lin(t, T.gold + .3, T.gold + 1.8)));
  noseRetract(t);
  jointsFade(t);
};

// ---------- 第二幕开场：断线飘落、木架碎块飞走、木屑 ----------
const SPLINTERS = (() => { const r = rng(808), a = []; for (let i = 0; i < 40; i++) { const ang = r() * Math.PI * 2, v = 200 + r() * 700; a.push({ x: 1300 + r() * 160, y: 330 + r() * 400, vx: Math.cos(ang) * v, vy: Math.sin(ang) * v - 200, l: 10 + r() * 26, rot: r() * 6, vr: (r() - .5) * 12 }); } return a; })();
FIG.burst = t => {
  const age = t - T.flash; if (age < 0 || age > 4) return;
  ctx.save(); ctx.lineCap = 'round';
  // 断掉的下半截提线：松开、飘落、从下往上化成光
  const ends = [[1296, 650], [1418, 342], [1600, 600]];
  CUT.forEach((c, i) => {
    const fall = age * age * 60 + age * 30, n = 24, dis = lin(age, .6 + i * .2, 3 + i * .2), p = new Path2D(), pts = [];
    for (let j = 0; j <= n; j++) {
      const u = j / n, x0 = mix(c.pt[0], ends[i][0], u), y0 = mix(c.pt[1], ends[i][1], u);
      pts.push([x0 + Math.sin(u * 9 + age * 3 + i) * 16 * age + (u - .5) * 30 * age, y0 + fall * (1 - u * .5) + Math.sin(u * 5 + age * 2) * 10 * age]);
    }
    const keep = Math.floor(pts.length * (1 - dis));
    if (keep >= 2) { p.moveTo(...pts[0]); for (let j = 1; j < keep; j++) p.lineTo(...pts[j]); glowStroke(p, 1.6, 10, '#ffd88a'); }
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    for (let j = keep; j < pts.length; j++) { const fade = 1 - lin(age, .6 + i * .2 + (1 - j / n) * 2.4, 1.6 + i * .2 + (1 - j / n) * 2.4); if (fade <= 0) continue; ctx.fillStyle = `rgba(255,236,180,${fade})`; ctx.fillRect(pts[j][0] + Math.sin(j) * 6, pts[j][1] - (1 - fade) * 40, 2.4, 2.4); }
    ctx.restore();
  });
  // 木架断成两截，带着上半截线飞出画面
  for (const s of [-1, 1]) {
    const k = eout(lin(age, 0, 1.4)); if (k >= 1) continue;
    ctx.save(); ctx.globalAlpha = 1 - k; ctx.translate(BC[0] + s * 140 + s * 500 * k, BC[1] - 40 - 260 * k); ctx.rotate(s * (.3 + 3 * k));
    const half = limb([-110, 0], [110, 0], 18, 16); darkFill(half, '#1a130a'); glowStroke(half, 2, 10); ctx.restore();
  }
  // 木屑
  for (const s of SPLINTERS) {
    if (age > 1.8) break;
    const x = s.x + s.vx * age * (1 - age * .2), y = s.y + s.vy * age + 300 * age * age;
    ctx.save(); ctx.translate(x, y); ctx.rotate(s.rot + s.vr * age); ctx.globalAlpha = 1 - age / 1.8;
    ctx.strokeStyle = '#e6b468'; ctx.lineWidth = 3; ctx.shadowColor = '#ffb040'; ctx.shadowBlur = 10; ctx.beginPath(); ctx.moveTo(-s.l / 2, 0); ctx.lineTo(s.l / 2, 0); ctx.stroke();
    ctx.restore();
  }
  ctx.restore();
};
FIG.flare = t => flare(HEART[0], HEART[1], (.22 + .12 * Math.sin(t * 2.4)) * lin(t, T.gold + .8, T.gold + 2), 420);
// 人物专属音效时间点（render.js events 导出 → audio.py）
FIG.events = [
  ...NOSE_BEATS.map(t => ({ t, kind: 'creak' })),
  ...ARM_TUGS.map(t => ({ t, kind: 'knock' })),
  ...CUT.map(c => ({ t: c.tc, kind: 'twang' })),
  { t: T.flash, kind: 'clatter' },
  { t: T.gold + .35, kind: 'retract', dur: 1.15 },
];
