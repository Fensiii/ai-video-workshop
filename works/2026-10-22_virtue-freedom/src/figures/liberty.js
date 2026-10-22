// 人物：自由女神像（自由）
// 第一幕：黑暗里先亮起一点将熄的火星——倒垂的火炬口，再隐约勾出七道光芒的皇冠；女神显形时低着头，
//        火炬倒提在身侧（古典图像里“倒垂的火炬”= 熄灭），一圈圈锁链把她连手臂一起捆在身上，胸前挂一把挂锁，
//        手腕上一根铁链往下拽；每次心跳锁链勒紧一圈、再缠上一圈，头垂得更低，挂锁红光一闪。
// 转场：金光斜斩从左下到右上，正好斩过手腕的铁链、挂锁和三圈锁链（斩断时刻按斜斩缓动反推 tc），断口迸火花。
// 第二幕：锁链崩成一节节烧红的链环四散飞走，挂锁弹开坠落；女神抬起头，手臂带着垂落的袖子把火炬一口气举过头顶，
//        火炬“轰”地点燃，皇冠七道光芒从前到后依次亮起射出光束；之后火焰一直燃烧、迸火星，
//        每隔 2.4 秒她把火炬往上一送，火焰里飞出一群金色白鸽，振翅飞出画面。
// 接口（index.html 调用）：FIG.SLASH / FIG.early / FIG.red / FIG.redTop / FIG.gold / FIG.burst / FIG.flare / FIG.events
const FIG = {};
FIG.SLASH = { ax: 1052, ay: 1080, bx: 1900, by: 55 };    // 斜斩：横穿手腕铁链 → 挂锁 → 三圈锁链

// ================= 时间点 =================
const BEATS = heartbeats.filter(h => h > 4.8);           // 每次心跳锁链勒紧
const RISE0 = T.flash + .15, RISE1 = T.flash + 1.2;       // 举起火炬
const TI = RISE1 + .05;                                   // 火炬点燃
const RAY0 = TI + .25, RAY_DT = .11;                      // 皇冠光芒依次亮起
const FLOCKS = [TI + .7, 13.9, 16.3, 18.7, 21.1];         // 放飞白鸽（同时把火炬往上一送）
const ebk = x => { const c = 1.25; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); };
const beatCount = t => BEATS.reduce((s, b) => s + eback(lin(t, b, b + .25)), 0);
const beatHit = t => BEATS.reduce((m, b) => { const d = t - b; return d >= 0 && d < .4 ? Math.max(m, 1 - d / .4) : m; }, 0);
const dir = a => [Math.cos(a), Math.sin(a)];
const D2R = Math.PI / 180;
// 人物整体缩到 0.9 倍、以底边为锚往下沉一点，举起的火炬才不会顶出画面。下面的坐标都是缩放前的“人物坐标”，
// 只有斜斩求交、白鸽（飞出画面）和光晕用 toScr 换到画面坐标。
const FS = .9, FO = [1400, 1100];
const toScr = p => [FO[0] + (p[0] - FO[0]) * FS, FO[1] + (p[1] - FO[1]) * FS];
const scaled = f => { ctx.save(); ctx.translate(...FO); ctx.scale(FS, FS); ctx.translate(-FO[0], -FO[1]); f(); ctx.restore(); };

// ================= 头（侧脸面朝左）+ 皇冠 =================
const HP = [1390, 560];                                   // 低头 / 抬头的转轴（颈根）
const HEAD0 = [[1300, 300], [1288, 322], [1281, 338], [1276, 352], [1268, 370], [1260, 384], [1259, 392], [1270, 398], [1272, 405],
  [1266, 411], [1272, 417], [1268, 423], [1277, 433], [1272, 447], [1284, 463], [1310, 471], [1336, 474], [1334, 510], [1330, 580],
  [1444, 580], [1438, 500], [1440, 452], [1474, 412], [1470, 336], [1434, 292], [1372, 278]];
const P_HEAD = catmull(HEAD0, true);
const P_HAIR = catmull([[1296, 314], [1312, 336], [1336, 352], [1352, 380], [1368, 420], [1392, 452], [1420, 470], [1446, 470], [1470, 448],
  [1486, 414], [1478, 368], [1466, 326], [1420, 314], [1360, 306]], true);
const HAIR_LINES = (() => { const p = new Path2D(); // 往后梳的波浪发绺 + 发髻
  for (let i = 0; i < 6; i++) { const y = 322 + i * 18; p.moveTo(1318 + i * 8, y + 6); p.bezierCurveTo(1360 + i * 6, y - 4 + i * 4, 1390 + i * 4, y + 26, 1440, y + 22 + i * 6); }
  p.moveTo(1446, 420); p.bezierCurveTo(1476, 410, 1478, 450, 1450, 456); p.moveTo(1452, 402); p.quadraticCurveTo(1474, 390, 1478, 420);
  return p; })();
const FACE_LINES = (() => { const f = new Path2D();
  f.moveTo(1286, 351); f.quadraticCurveTo(1297, 344, 1308, 351);          // 上眼睑
  f.moveTo(1289, 357); f.quadraticCurveTo(1299, 360, 1307, 355);          // 下眼睑
  f.moveTo(1266, 388); f.quadraticCurveTo(1274, 393, 1279, 386);          // 鼻翼
  f.moveTo(1271, 417); f.lineTo(1284, 418);                              // 嘴角
  f.moveTo(1290, 459); f.quadraticCurveTo(1338, 464, 1372, 438);          // 下颌线
  f.moveTo(1348, 476); f.quadraticCurveTo(1360, 512, 1350, 560);          // 颈部肌肉
  f.moveTo(1306, 398); f.quadraticCurveTo(1316, 410, 1312, 424);          // 法令纹（雕像的面颊）
  return f; })();
const BROW = (() => { const p = new Path2D(); p.moveTo(1281, 337); p.quadraticCurveTo(1298, 330, 1318, 336); return p; })();
const CROWN_BAND = catmull([[1290, 318], [1330, 308], [1380, 306], [1430, 312], [1466, 326], [1470, 298], [1432, 284], [1380, 278], [1330, 282], [1292, 294]], true);
const CROWN_WIN = (() => { const p = new Path2D(); for (let i = 0; i < 6; i++) { const x = 1314 + i * 25, y = 296 - Math.sin(i / 5 * Math.PI) * 6 + i * 1.2; p.rect(x, y, 12, 8); } return p; })();
const CR = [1376, 382];                                    // 光芒的放射中心
const RAYS = [-152, -133, -113, -92, -71, -50, -30].map((a, i) => {
  const d = dir(a * D2R), n = [-d[1], d[0]], r0 = 98, L = [128, 140, 150, 156, 150, 138, 120][i], hw = 15;
  const b = [CR[0] + d[0] * r0, CR[1] + d[1] * r0], tip = [CR[0] + d[0] * (r0 + L), CR[1] + d[1] * (r0 + L)];
  const path = poly([[b[0] + n[0] * hw, b[1] + n[1] * hw], tip, [b[0] - n[0] * hw, b[1] - n[1] * hw]]);
  const ridge = new Path2D(); ridge.moveTo(...b); ridge.lineTo(mix(b[0], tip[0], .9), mix(b[1], tip[1], .9));
  return { a: a * D2R, d, b, tip, path, ridge, L };
});
function headA(t) {
  if (t < T.flash) return -.1 - .012 * beatCount(t) + .006 * Math.sin(t * 1.4);
  const bow = -.1 - .012 * BEATS.length;
  return mix(bow, .035, eio(lin(t, RISE0 - .05, RISE1 - .1))) + .008 * Math.sin(t * .9);
}
const withHead = (t, f) => { ctx.save(); ctx.translate(...HP); ctx.rotate(headA(t)); ctx.translate(-HP[0], -HP[1]); f(); ctx.restore(); };

// ================= 身体（长袍）=================
const BODY0 = [[1328, 524], [1296, 556], [1258, 588], [1226, 626], [1206, 700], [1196, 820], [1192, 960], [1186, 1095], [1670, 1095],
  [1662, 920], [1640, 760], [1600, 640], [1540, 586], [1478, 556], [1444, 530], [1390, 572]];
const P_BODY = catmull(BODY0, true);
const ROBE_LINES = (() => { const p = new Path2D(); // 斜披的长袍褶子、袍带、下面竖直的衣褶、领口
  p.moveTo(1336, 532); p.quadraticCurveTo(1390, 590, 1442, 536);
  p.moveTo(1500, 574); p.bezierCurveTo(1440, 650, 1330, 740, 1214, 790); p.moveTo(1526, 590); p.bezierCurveTo(1462, 670, 1350, 764, 1210, 820);
  p.moveTo(1590, 650); p.bezierCurveTo(1510, 760, 1390, 850, 1204, 900);
  p.moveTo(1630, 760); p.bezierCurveTo(1550, 860, 1420, 940, 1198, 990);
  p.moveTo(1650, 870); p.bezierCurveTo(1580, 950, 1460, 1010, 1300, 1050);
  for (const [x, w] of [[1290, -8], [1372, 6], [1460, -6], [1556, 8]]) { p.moveTo(x, 940 + (x - 1290) * -.2); p.bezierCurveTo(x + w, 990, x - w, 1040, x + w * .5, 1095); }
  p.moveTo(1240, 640); p.quadraticCurveTo(1260, 600, 1300, 590);
  return p; })();
// 第二幕：左臂抱着的铭牌（JULY IV MDCCLXXVI）
const TAB = [[1132, 772], [1262, 744], [1292, 1012], [1162, 1040]];
const P_TAB = poly(TAB);

// ================= 手臂（骨骼）+ 火炬 =================
// 手臂只画一份：上臂、前臂各自的局部坐标（x 沿骨头），按骨骼角度换到画面坐标。袖子按重力往下垂（画面坐标里算）。
const SH = [1250, 600], LU = 185;
const UA_DOWN = 100 * D2R, FA_DOWN = 112 * D2R, UA_UP = 243 * D2R, FA_UP = 257 * D2R;
const UPPER = [[-14, -36], [40, -39], [100, -35], [160, -30], [196, -27], [206, 0], [196, 27], [160, 31], [100, 36], [40, 40], [-14, 38], [-26, 0]];
const FORE = [[-10, -28], [40, -30], [100, -25], [150, -19], [150, 19], [100, 23], [40, 28], [-10, 28], [-20, 0]];
const FIST = [[146, -24], [170, -29], [195, -27], [210, -18], [215, 0], [210, 18], [195, 27], [170, 29], [146, 24], [140, 0]];
const THUMB = [[150, -22], [176, -36], [202, -33], [208, -24], [186, -20], [160, -12]];
const HANDLE = [[128, -9], [252, -9], [252, 9], [128, 9]];
const KNOB = [[250, -15], [260, -15], [260, 15], [250, 15]];
const CUP = [[260, -13], [276, -20], [290, -33], [300, -43], [306, -47], [306, 47], [300, 43], [290, 33], [276, 20], [260, 13]];
const GALLERY = [[306, -52], [314, -52], [314, 52], [306, 52]];
const FLAME_AT = 314;
function lift(t) { // 每次放飞白鸽前把火炬往上一送
  let b = 0; for (const f of FLOCKS) { const d = t - f + .35; if (d > 0 && d < 1.4) b = Math.max(b, Math.sin(Math.PI * Math.min(1, d / .45)) * Math.exp(-Math.max(0, d - .45) * 3) * (d < .45 ? 1 : 1)); }
  return b;
}
function armPose(t) {
  if (t < T.flash) { const tug = beatHit(t); return { ua: UA_DOWN + .03 * tug, fa: FA_DOWN + .05 * tug }; }
  const k = ebk(lin(t, RISE0, RISE1)), b = lift(t), sw = Math.sin(t * .9) * .012 * lin(t, RISE1, RISE1 + 1);
  return { ua: mix(UA_DOWN, UA_UP, k) + .06 * b + sw, fa: mix(FA_DOWN, FA_UP, Math.min(1, k * 1.04)) + .05 * b + sw * .6 };
}
function armGeo(t) {
  const { ua, fa } = armPose(t), du = dir(ua), df = dir(fa);
  const E = [SH[0] + du[0] * LU, SH[1] + du[1] * LU];
  const U = (u, v) => [SH[0] + du[0] * u - du[1] * v, SH[1] + du[1] * u + du[0] * v];
  const F = (u, v) => [E[0] + df[0] * u - df[1] * v, E[1] + df[1] * u + df[0] * v];
  return { du, df, E, U, F, flame: F(FLAME_AT, 0), hand: F(180, 0) };
}
function sleevePath(g, t) { // 宽袖：盖住上臂，从手臂下侧顺着重力垂下来，下摆微微飘
  const n = [g.du[1], -g.du[0]], fall = .35 + .65 * clamp(-g.du[1]), pts = [];
  for (const u of [0, .2, .4, .6, .8, .9]) pts.push(g.U(u * LU, -42 * (u < .85 ? 1 : .9)));
  pts.push(g.U(.97 * LU, 0));
  for (const u of [.9, .75, .58, .4, .22, .05]) {
    const b = g.U(u * LU, 42), sw = Math.sin(t * 1.3 + u * 3) * 6 * u;
    pts.push([b[0] + n[0] * 8 + sw, b[1] + (30 + 150 * u) * fall + n[1] * 8]);
  }
  pts.push(g.U(-20, 30));
  const folds = new Path2D();
  for (const u of [.3, .55, .8]) { const a = g.U(u * LU, 30), b = g.U((u - .12) * LU, 42); folds.moveTo(...a); folds.quadraticCurveTo(b[0], b[1] + 40 * fall, b[0] + n[0] * 6, b[1] + (22 + 130 * u) * fall); }
  const cuff = new Path2D(); { const a = g.U(.9 * LU, -40), b = g.U(.97 * LU, 0), c = g.U(.9 * LU, 44); cuff.moveTo(...a); cuff.quadraticCurveTo(...b, ...c); }
  return { path: catmull(pts, true), folds, cuff };
}
const mapPts = (pts, f) => pts.map(p => f(p[0], p[1]));
function armParts(g) {
  const fl = new Path2D(); for (const x of [170, 184, 198]) { const a = g.F(x, -27), b = g.F(x + 7, 0), c = g.F(x, 27); fl.moveTo(...a); fl.quadraticCurveTo(...b, ...c); }
  const cupL = new Path2D(); for (const x of [270, 286]) { const a = g.F(x, -(13 + (x - 260) * .62)), b = g.F(x, 13 + (x - 260) * .62); cupL.moveTo(...a); cupL.lineTo(...b); }
  { const a = g.F(262, 0), b = g.F(304, 0); cupL.moveTo(...a); cupL.lineTo(...b); }
  return {
    upper: catmull(mapPts(UPPER, g.U), true), fore: catmull(mapPts(FORE, g.F), true), fist: catmull(mapPts(FIST, g.F), true),
    thumb: catmull(mapPts(THUMB, g.F), true), handle: poly(mapPts(HANDLE, g.F)), knob: poly(mapPts(KNOB, g.F)), cup: catmull(mapPts(CUP, g.F), true),
    gallery: poly(mapPts(GALLERY, g.F)), fingers: fl, cupLines: cupL,
  };
}

// ================= 锁链 =================
const LINK = 26;
const LINK_O = (() => { const p = new Path2D(); p.ellipse(0, 0, LINK * .66, 8.5, 0, 0, Math.PI * 2); return p; })(); // 正面的链环
const LINK_E = (() => { const p = new Path2D(); p.moveTo(-LINK * .62, 0); p.lineTo(LINK * .62, 0); return p; })(); // 侧面的链环
function sampleLinks(pts) { // 沿折线每隔一节放一个链环
  const out = []; let carry = 0, idx = 0;
  for (let i = 0; i < pts.length - 1; i++) {
    const [x0, y0] = pts[i], [x1, y1] = pts[i + 1], L = Math.hypot(x1 - x0, y1 - y0), a = Math.atan2(y1 - y0, x1 - x0);
    let s = carry;
    while (s < L) { out.push({ x: x0 + (x1 - x0) * s / L, y: y0 + (y1 - y0) * s / L, a, alt: idx++ % 2, seg: i }); s += LINK * .92; }
    carry = s - L;
  }
  return out;
}
function linksPath(links) {
  const po = new Path2D(), pe = new Path2D();
  for (const l of links) { const m = new DOMMatrix().translate(l.x, l.y).rotate(l.a / D2R + (l.rot || 0)); (l.alt ? pe : po).addPath(l.alt ? LINK_E : LINK_O, m); }
  return { po, pe };
}
function drawChain(links, a = 1, hot = 0) { // 铁链：暗铁 + 烧红的边
  if (!links.length) return;
  const { po, pe } = linksPath(links);
  ctx.save(); ctx.globalAlpha *= a; ctx.lineCap = 'round';
  ctx.strokeStyle = '#1a0605'; ctx.lineWidth = 9; ctx.stroke(po); ctx.lineWidth = 11; ctx.stroke(pe);
  ctx.strokeStyle = `rgba(255,${90 + 80 * hot},${50 + 60 * hot},.95)`; ctx.lineWidth = 2.4 + hot * 1.5; ctx.shadowColor = '#ff2a08'; ctx.shadowBlur = 10 + 14 * hot;
  ctx.stroke(po); ctx.lineWidth = 3.2 + hot * 1.5; ctx.stroke(pe);
  ctx.shadowBlur = 0; ctx.strokeStyle = 'rgba(255,220,190,.55)'; ctx.lineWidth = 1; ctx.stroke(po);
  ctx.restore();
}
// 四圈锁链（绕在身体 + 手臂上，只看得到前半圈）：第一圈随人物出现，之后每两次心跳再缠上一圈
const LOOPS = [{ cy: 652, rx: 236, ry: 46, tilt: -.06 }, { cy: 762, rx: 240, ry: 50, tilt: -.1 }, { cy: 872, rx: 244, ry: 52, tilt: -.05 }, { cy: 980, rx: 248, ry: 50, tilt: -.08 }]
  .map((L, i) => ({ ...L, cx: 1420, t0: i ? BEATS[i * 2 - 1] : T.figure + .3 }));
function loopPts(L, t, tt = t) {
  const g = beatCount(Math.min(tt, T.flash)), app = eback(lin(t, L.t0, L.t0 + .32)), s = mix(1.45, 1, app) * (1 - .012 * g);
  const rx = L.rx * s, ry = L.ry * mix(2.2, 1, app) * (1 - .04 * g), pts = [];
  for (let i = 0; i <= 28; i++) { const th = Math.PI * i / 28, p = [L.cx + rx * Math.cos(th), L.cy + ry * Math.sin(th)]; pts.push(rot(p, [L.cx, L.cy], L.tilt)); }
  return pts;
}
const WRIST_ANCHOR = [1040, 1140];
function wristPts(t) { // 手腕上往下拽的铁链（微微下垂，心跳时一绷）
  const h = armGeo(Math.min(t, T.flash - .001)).F(150, 0), sag = 26 * (1 - beatHit(t) * .8), pts = [];
  for (let i = 0; i <= 10; i++) { const u = i / 10; pts.push([mix(h[0], WRIST_ANCHOR[0], u) + Math.sin(Math.PI * u) * sag, mix(h[1], WRIST_ANCHOR[1], u)]); }
  return pts;
}
const LOCK_POS = (() => { const L = LOOPS[0], p = rot([L.cx + L.rx * Math.cos(.6 * Math.PI), L.cy + L.ry * Math.sin(.6 * Math.PI)], [L.cx, L.cy], L.tilt); return p; })();
function drawLock(x, y, ang, open, a, gold) { // 挂锁：锁梁 + 锁身 + 锁孔
  ctx.save(); ctx.globalAlpha *= a; ctx.translate(x, y); ctx.rotate(ang);
  const sh = new Path2D(); sh.moveTo(-17, 26); sh.lineTo(-17, 8); sh.arc(0, 8, 17, Math.PI, 0); sh.lineTo(17, 26 - open * 18);
  ctx.save(); if (open) { ctx.translate(-17, 26); ctx.rotate(-open * .9); ctx.translate(17, -26); }
  ctx.strokeStyle = gold ? '#ffd27a' : '#2a0a06'; ctx.lineWidth = 8; ctx.stroke(sh);
  if (gold) glowStroke(sh, 3, 12); else redStroke(sh, 2.2, 10); ctx.restore();
  const body = rr(-30, 22, 60, 52, 9);
  if (gold) { ctx.fillStyle = 'rgba(70,46,14,.9)'; ctx.fill(body); glowStroke(body, 2.6, 16); }
  else { ctx.fillStyle = '#1c0605'; ctx.fill(body); redStroke(body, 2.4, 14); }
  const kh = new Path2D(); kh.arc(0, 42, 6, 0, Math.PI * 2); kh.moveTo(0, 46); kh.lineTo(0, 60);
  ctx.strokeStyle = gold ? '#fff0c4' : '#ff8a5a'; ctx.lineWidth = 2.5; ctx.stroke(kh);
  ctx.restore();
}
// 斜斩求交：每根链子被斩到的位置、时刻（按 slashLine 的 eout 缓动反推）
function segInter(p, q, A, B) {
  const r = [q[0] - p[0], q[1] - p[1]], s = [B[0] - A[0], B[1] - A[1]], den = r[0] * s[1] - r[1] * s[0];
  if (Math.abs(den) < 1e-9) return null;
  const u = ((A[0] - p[0]) * s[1] - (A[1] - p[1]) * s[0]) / den, v = ((A[0] - p[0]) * r[1] - (A[1] - p[1]) * r[0]) / den;
  return u >= 0 && u <= 1 && v >= 0 && v <= 1 ? { u, v, pt: [p[0] + r[0] * u, p[1] + r[1] * u] } : null;
}
function findCut(pts) {
  const A = [FIG.SLASH.ax, FIG.SLASH.ay], B = [FIG.SLASH.bx, FIG.SLASH.by];
  const sp = pts.map(toScr);
  for (let i = 0; i < pts.length - 1; i++) { const x = segInter(sp[i], sp[i + 1], A, B); if (x) return { i, u: x.u, pt: [mix(pts[i][0], pts[i + 1][0], x.u), mix(pts[i][1], pts[i + 1][1], x.u)], tc: T.slash + .3 * (1 - Math.pow(1 - clamp(x.v), 1 / 3)) }; }
  return { i: Math.floor(pts.length / 2), u: .5, pt: pts[Math.floor(pts.length / 2)], tc: T.flash - .02 }; // 没被斩到的那圈：闪白时崩断
}
const CHAINS = [...LOOPS.map((L, i) => ({ get: t => loopPts(L, t), t0: L.t0 })), { get: wristPts, t0: T.figure }];
const CUTS = CHAINS.map(c => findCut(c.get(T.slash)));
const LOCK_TC = T.slash + .3 * (1 - Math.pow(1 - clamp((1080 - toScr([0, LOCK_POS[1] + 40])[1]) / (1080 - 55)), 1 / 3));
function splitAt(pts, c, t) { // 斩断后：链子从断口分成两段，断头往回弹、往下坠
  if (t < c.tc) return [pts];
  const d = eout(lin(t, c.tc, c.tc + .3)), A = pts.slice(0, c.i + 1).concat([c.pt]), B = [c.pt].concat(pts.slice(c.i + 1));
  const bend = (arr, fromEnd) => arr.map((p, j) => { const k = Math.exp(-(fromEnd ? arr.length - 1 - j : j) / 3); return [p[0] + (fromEnd ? -1 : 1) * 30 * d * k, p[1] + 34 * d * k]; });
  return [bend(A, true), bend(B, false)];
}
function cutSparks(t) { // 斩断处迸出的火花
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  CUTS.forEach((c, j) => {
    const age = t - c.tc; if (age < 0 || age > .7) return;
    const r = rng(300 + j);
    for (let i = 0; i < 26; i++) {
      const an = -Math.PI / 2 + (r() - .5) * 3.4, v = 200 + r() * 600, x = c.pt[0] + Math.cos(an) * v * age, y = c.pt[1] + Math.sin(an) * v * age + 500 * age * age;
      ctx.strokeStyle = `rgba(255,${200 + r() * 55},${120 + r() * 80},${1 - age / .7})`; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x - Math.cos(an) * 14, y - Math.sin(an) * 14 - 8 * age); ctx.stroke();
    }
    const fl = 1 - lin(age, 0, .25); if (fl > 0) { const g = ctx.createRadialGradient(...c.pt, 0, ...c.pt, 70); g.addColorStop(0, `rgba(255,250,230,${fl})`); g.addColorStop(1, 'rgba(255,200,120,0)'); ctx.fillStyle = g; ctx.fillRect(c.pt[0] - 70, c.pt[1] - 70, 140, 140); }
  });
  ctx.restore();
}

// ================= 第一幕 =================
function skin(x, y, r) { const g = ctx.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, '#5a1a12'); g.addColorStop(.6, '#2a0a07'); g.addColorStop(1, '#120404'); return g; }
function torchTipDown(t) { return armGeo(Math.min(t, T.flash - .001)).flame; }
function emberGlow(t, a) { // 倒垂火炬口里将熄的火星 + 一缕缕往上飘的烟
  const [x, y] = torchTipDown(t), fl = .55 + .3 * Math.sin(t * 7.3) * Math.sin(t * 2.9) + .15 * Math.sin(t * 17);
  ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha *= a;
  const g = ctx.createRadialGradient(x, y, 0, x, y, 90); g.addColorStop(0, `rgba(255,140,60,${.55 * fl})`); g.addColorStop(.3, `rgba(200,40,10,${.25 * fl})`); g.addColorStop(1, 'rgba(120,0,0,0)');
  ctx.fillStyle = g; ctx.fillRect(x - 90, y - 90, 180, 180);
  ctx.fillStyle = `rgba(255,200,140,${.8 * fl})`; ctx.beginPath(); ctx.arc(x, y - 4, 3.5, 0, 7); ctx.fill();
  ctx.restore();
  ctx.save(); ctx.globalAlpha *= a * .5; ctx.lineCap = 'round';
  for (let i = 0; i < 4; i++) {
    const ph = (t * .35 + i * .25) % 1, p = new Path2D(); p.moveTo(x, y - 6);
    for (let j = 1; j <= 12; j++) { const u = j / 12; p.lineTo(x + Math.sin(u * 5 + t * 1.3 + i * 2) * 26 * u + i * 6 * u, y - 6 - u * 300 * (.5 + ph)); }
    ctx.strokeStyle = `rgba(150,90,80,${.35 * (1 - ph)})`; ctx.lineWidth = 6 + 10 * ph; ctx.stroke(p);
  }
  ctx.restore();
}
function crownRed(t, a, dim) {
  ctx.save(); ctx.globalAlpha *= a;
  for (const r of RAYS) { if (!dim) { ctx.fillStyle = '#1a0504'; ctx.fill(r.path); } redStroke(r.path, dim ? 1.4 : 2, dim ? 8 : 12); }
  if (!dim) { ctx.fillStyle = '#1a0504'; ctx.fill(CROWN_BAND); ctx.strokeStyle = 'rgba(255,110,70,.5)'; ctx.lineWidth = 1.2; ctx.stroke(CROWN_WIN); }
  redStroke(CROWN_BAND, dim ? 1.4 : 2, 10);
  ctx.restore();
}
function early(t) { // 黑暗里先亮起倒垂火炬口的火星，再隐约勾出七道光芒的皇冠和低垂的侧脸
  if (t >= T.figure + .6) return;
  const a = lin(t, .3, 1.2) * (1 - lin(t, T.figure, T.figure + .6));
  if (a <= 0) return;
  emberGlow(t, Math.min(1, a * 1.6));
  withHead(t, () => {
    ctx.save(); ctx.globalAlpha = .55 * lin(t, 1.4, 3.2) * a;
    crownRed(t, 1, true);
    ctx.strokeStyle = 'rgba(255,90,50,.6)'; ctx.lineWidth = 1.4; ctx.shadowColor = '#ff3010'; ctx.shadowBlur = 10; ctx.stroke(P_HEAD);
    ctx.restore();
  });
};
function drawArmRed(t, k) {
  const g = armGeo(Math.min(t, T.flash - .001)), P = armParts(g), sl = sleevePath(g, t);
  ctx.save(); ctx.globalAlpha *= k;
  for (const p of [P.handle, P.knob, P.cup, P.gallery]) { ctx.fillStyle = '#160504'; ctx.fill(p); redStroke(p, 1.8, 8); }
  ctx.strokeStyle = 'rgba(255,110,70,.5)'; ctx.lineWidth = 1.2; ctx.stroke(P.cupLines);
  ctx.fillStyle = skin(...g.E, 200); ctx.fill(P.upper); ctx.fill(P.fore); redStroke(P.fore, 2, 10);
  fillWithText(sl.path, t, 1, .9); redStroke(sl.path, 2.2, 12);
  ctx.strokeStyle = 'rgba(255,100,60,.55)'; ctx.lineWidth = 1.4; ctx.stroke(sl.folds); redStroke(sl.cuff, 1.8, 8);
  ctx.fillStyle = skin(...g.hand, 60); ctx.fill(P.fist); redStroke(P.fist, 1.8, 8); ctx.strokeStyle = 'rgba(255,110,70,.6)'; ctx.lineWidth = 1.3; ctx.stroke(P.fingers);
  ctx.fillStyle = '#240806'; ctx.fill(P.thumb); redStroke(P.thumb, 1.5, 6);
  ctx.restore();
}
function red(t, k) {
  fillWithText(P_BODY, t, lin(t, T.figure + .4, T.figure + 3.2), k * .95);
  ctx.save(); ctx.globalAlpha = k; ctx.setLineDash([3400 * eio(k), 6000]); redStroke(P_BODY, 2.6, 16); ctx.restore();
  ctx.save(); ctx.globalAlpha = k * .55; ctx.save(); ctx.clip(P_BODY); ctx.strokeStyle = 'rgba(255,120,80,.6)'; ctx.lineWidth = 1.5; ctx.stroke(ROBE_LINES); ctx.restore(); ctx.restore();
  withHead(t, () => {
    ctx.save(); ctx.globalAlpha = k;
    ctx.fillStyle = skin(1320, 380, 230); ctx.fill(P_HEAD); redStroke(P_HEAD, 2.4, 14);
    ctx.fillStyle = '#1c0504'; ctx.fill(P_HAIR); redStroke(P_HAIR, 1.6, 8);
    ctx.save(); ctx.clip(P_HAIR); ctx.strokeStyle = 'rgba(255,110,70,.4)'; ctx.lineWidth = 1.2; ctx.stroke(HAIR_LINES); ctx.restore();
    redStroke(FACE_LINES, 1.6, 6); redStroke(BROW, 2, 6);
    crownRed(t, 1, false);
    ctx.restore();
  });
  drawArmRed(t, k);
  emberGlow(t, k);
};
function redTop(t, k) {
  if (k <= 0) return;
  // 锁链盖在卡片上面：人物身上的东西里最要紧的就是它
  CHAINS.forEach((c, j) => {
    const a = lin(t, c.t0, c.t0 + .1) * k; if (a <= 0) return;
    for (const part of splitAt(c.get(t), CUTS[j], t)) drawChain(sampleLinks(part), a, beatHit(t) * .8 + lin(t, CUTS[j].tc, CUTS[j].tc + .1));
  });
  const hit = beatHit(t), cut = t >= LOCK_TC, d = eout(lin(t, LOCK_TC, LOCK_TC + .35));
  drawLock(LOCK_POS[0] + (cut ? -10 * d : 0), LOCK_POS[1] + 6 + (cut ? 40 * d : 0), .08 * Math.sin(t * 2) + (cut ? -.5 * d : 0), cut ? d : 0, k, false);
  if (hit > 0) { // 挂锁随心跳红光一闪
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; const [x, y] = [LOCK_POS[0], LOCK_POS[1] + 50];
    const g = ctx.createRadialGradient(x, y, 0, x, y, 140); g.addColorStop(0, `rgba(255,80,40,${.5 * hit})`); g.addColorStop(1, 'rgba(255,0,0,0)'); ctx.fillStyle = g; ctx.fillRect(x - 140, y - 140, 280, 280); ctx.restore();
  }
  cutSparks(t);
}
FIG.early = t => scaled(() => early(t));
FIG.red = (t, k) => scaled(() => red(t, k));
FIG.redTop = (t, k) => scaled(() => redTop(t, k));

// ================= 第二幕 =================
let LIGHT = [1100, 170], LIGHT_K = 0;                     // 此刻火焰（光源）的位置、亮度
function bodyFill(path) {
  const g = ctx.createLinearGradient(0, 200, 0, 1080); g.addColorStop(0, '#20180c'); g.addColorStop(.5, '#120d07'); g.addColorStop(1, '#070504');
  ctx.fillStyle = g; ctx.fill(path);
  if (LIGHT_K <= 0) return;
  const L = ctx.getTransform().inverse().multiply(FIG_BASE).transformPoint(new DOMPoint(LIGHT[0], LIGHT[1]));
  ctx.save(); ctx.clip(path);
  const rim = ctx.createRadialGradient(L.x, L.y, 0, L.x, L.y, 760); rim.addColorStop(0, `rgba(255,230,170,${.3 * LIGHT_K})`); rim.addColorStop(.45, `rgba(200,150,70,${.12 * LIGHT_K})`); rim.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = rim; ctx.fillRect(-4000, -4000, 8000, 8000); ctx.restore();
}
let FIG_BASE = new DOMMatrix();
const fireOn = t => t < TI ? 0 : eback(lin(t, TI, TI + .35));
function flame(x, y, sc, t, a = 1) { // 火炬的火焰：三层火舌（外橙、中金、内白）+ 脱离的小火苗 + 光晕；火焰永远朝上
  if (sc <= 0) return;
  ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha *= a;
  const big = ctx.createRadialGradient(x, y - 50 * sc, 0, x, y - 50 * sc, 380 * sc); big.addColorStop(0, 'rgba(255,220,150,.42)'); big.addColorStop(.35, 'rgba(255,150,60,.14)'); big.addColorStop(1, 'rgba(255,120,40,0)');
  ctx.fillStyle = big; ctx.fillRect(x - 400 * sc, y - 450 * sc, 800 * sc, 800 * sc);
  for (const [col, ws, hs, al, sd] of [['255,110,30', 1, 1, .6, 1], ['255,180,60', .74, .82, .75, 2], ['255,240,200', .44, .56, .95, 3], ['255,255,250', .22, .3, 1, 4]]) {
    const W0 = 46 * sc * ws, H0 = 172 * sc * hs * (1 + .1 * noise(t * 4.3, sd)), L = [], R = [];
    for (let i = 0; i <= 16; i++) {
      const s = i / 16, cx = x + 18 * sc * Math.pow(s, 1.6) * noise(t * 3.1 - s * 2.4, sd + 7), hw = W0 * Math.pow(1 - s, .8) * (.85 + .35 * Math.sin(Math.PI * s * .9));
      const yy = y - H0 * s;
      L.push([cx - hw * (1 + .14 * noise(t * 8 + s * 7, sd)), yy]); R.push([cx + hw * (1 + .14 * noise(t * 8.6 + s * 6, sd + 3)), yy]);
    }
    const p = new Path2D(); p.moveTo(x - W0 * .9, y + 6); for (const q of L) p.lineTo(...q); for (const q of R.reverse()) p.lineTo(...q); p.lineTo(x + W0 * .9, y + 6); p.closePath();
    const g = ctx.createLinearGradient(0, y, 0, y - H0); g.addColorStop(0, `rgba(${col},${al})`); g.addColorStop(.7, `rgba(${col},${al * .7})`); g.addColorStop(1, `rgba(${col},0)`);
    ctx.fillStyle = g; ctx.shadowColor = `rgba(${col},.9)`; ctx.shadowBlur = 20; ctx.fill(p);
  }
  ctx.shadowBlur = 0;
  for (let i = 0; i < 5; i++) { // 脱离火焰往上飘的小火苗
    const ph = (t * 1.6 + i * .37) % 1, px = x + noise(t * 2 + i * 3, i) * 30 * sc, py = y - (110 + 120 * ph) * sc, s = (1 - ph) * 12 * sc;
    const g = ctx.createRadialGradient(px, py, 0, px, py, s * 2); g.addColorStop(0, `rgba(255,220,140,${.8 * (1 - ph)})`); g.addColorStop(1, 'rgba(255,140,40,0)');
    ctx.fillStyle = g; ctx.beginPath(); ctx.ellipse(px, py, s, s * 1.8, 0, 0, Math.PI * 2); ctx.fill();
  }
  const r = rng(808); // 火星：从火焰顶上卷着往上飞
  for (let i = 0; i < 46; i++) {
    const life = 1 + r() * 1.4, ph = ((t + r() * 9) % life) / life, vx = (r() - .5) * 120, sp = 120 + r() * 220;
    const px = x + vx * ph + Math.sin(ph * 6 + i) * 18, py = y - 60 * sc - sp * ph * life;
    ctx.fillStyle = `rgba(255,${190 + (i % 4) * 15},${90 + (i % 3) * 40},${(1 - ph) * .9})`; ctx.fillRect(px, py, 2.4, 2.4);
  }
  ctx.restore();
}
function drawArmGold(t, g) {
  const P = armParts(g), sl = sleevePath(g, t);
  for (const p of [P.handle, P.knob]) { bodyFill(p); glowStroke(p, 1.8, 8); }
  bodyFill(P.upper); bodyFill(P.fore); glowStroke(P.fore, 2.4, 12);
  bodyFill(sl.path); glowStroke(sl.path, 2.6, 14); glowStroke(sl.folds, 1.3, 6); glowStroke(sl.cuff, 1.8, 8);
  bodyFill(P.fist); glowStroke(P.fist, 2.2, 10); glowStroke(P.fingers, 1.2, 6); darkFill(P.thumb, '#18120a'); glowStroke(P.thumb, 1.8, 8);
  for (const p of [P.cup, P.gallery]) { // 火炬杯：被火焰照亮的金色
    const fo = fireOn(t), gr = ctx.createLinearGradient(...g.F(260, 0), ...g.F(314, 0)); gr.addColorStop(0, '#2a1d0b'); gr.addColorStop(1, fo > 0 ? `rgba(${120 + 100 * Math.min(1, fo)},${80 + 70 * Math.min(1, fo)},30,1)` : '#3a2a10');
    ctx.fillStyle = gr; ctx.fill(p); glowStroke(p, 2.2, 12);
  }
  glowStroke(P.cupLines, 1.2, 6);
}
function crownGold(t) {
  RAYS.forEach((r, i) => {
    const k = eout(lin(t, RAY0 + i * RAY_DT, RAY0 + i * RAY_DT + .25)), pul = .8 + .2 * Math.sin(t * 2.2 + i * .9);
    if (k > 0) { // 亮起的光芒：往外射出的光束
      ctx.save(); ctx.globalCompositeOperation = 'lighter';
      const len = (260 + 260 * k) * pul, e = [r.tip[0] + r.d[0] * len, r.tip[1] + r.d[1] * len], n = [-r.d[1], r.d[0]], w = 22 * k;
      const bg = ctx.createLinearGradient(...r.b, ...e); bg.addColorStop(0, `rgba(255,240,200,${.38 * k})`); bg.addColorStop(1, 'rgba(255,210,130,0)');
      ctx.fillStyle = bg; ctx.beginPath(); ctx.moveTo(r.b[0] + n[0] * 6, r.b[1] + n[1] * 6); ctx.lineTo(e[0] + n[0] * w, e[1] + n[1] * w); ctx.lineTo(e[0] - n[0] * w, e[1] - n[1] * w); ctx.lineTo(r.b[0] - n[0] * 6, r.b[1] - n[1] * 6); ctx.fill();
      ctx.restore();
    }
    const fg = ctx.createLinearGradient(...r.b, ...r.tip); fg.addColorStop(0, `rgba(${mix(32, 255, k)},${mix(24, 226, k)},${mix(12, 160, k)},1)`); fg.addColorStop(1, `rgba(${mix(20, 255, k)},${mix(15, 250, k)},${mix(8, 230, k)},1)`);
    ctx.fillStyle = fg; ctx.fill(r.path); glowStroke(r.path, 2 + k, 12 + 10 * k); glowStroke(r.ridge, 1, 4, '#fff4dc');
    const fl = 1 - lin(t, RAY0 + i * RAY_DT + .05, RAY0 + i * RAY_DT + .5); // 亮起那一下尖端闪光
    if (fl > 0 && fl < 1) {
      ctx.save(); ctx.globalCompositeOperation = 'lighter'; const [x, y] = r.tip;
      const g = ctx.createRadialGradient(x, y, 0, x, y, 90); g.addColorStop(0, `rgba(255,255,245,${fl})`); g.addColorStop(1, 'rgba(255,220,150,0)'); ctx.fillStyle = g; ctx.fillRect(x - 90, y - 90, 180, 180);
      ctx.fillStyle = `rgba(255,255,250,${fl})`; ctx.fillRect(x - 70 * fl, y - 1, 140 * fl, 2); ctx.fillRect(x - 1, y - 50 * fl, 2, 100 * fl);
      ctx.restore();
    }
  });
  bodyFill(CROWN_BAND); glowStroke(CROWN_BAND, 2.2, 12);
  ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = `rgba(255,230,160,${.25 + .6 * lin(t, RAY0, RAY0 + 7 * RAY_DT)})`; ctx.fill(CROWN_WIN); ctx.restore();
}
function drawLiberty(t, a) {
  if (a <= 0) return;
  ctx.save(); ctx.globalAlpha *= a;
  bodyFill(P_BODY); glowStroke(P_BODY, 3, 20);
  ctx.save(); ctx.clip(P_BODY); glowStroke(ROBE_LINES, 1.4, 7); ctx.restore();
  // 铭牌
  bodyFill(P_TAB); glowStroke(P_TAB, 2.4, 14);
  ctx.save(); ctx.translate(...TAB[0]); ctx.rotate(Math.atan2(TAB[1][1] - TAB[0][1], TAB[1][0] - TAB[0][0])); ctx.transform(1, 0, .1, 1, 0, 0);
  ctx.font = '24px CinzelBold'; ctx.textAlign = 'center'; ctx.fillStyle = 'rgba(255,226,160,.92)'; ctx.shadowColor = 'rgba(255,190,80,.9)'; ctx.shadowBlur = 10;
  ctx.fillText('JULY IV', 70, 70); ctx.font = '19px CinzelBold'; ctx.fillText('MDCCLXXVI', 76, 104); ctx.restore();
  withHead(t, () => {
    bodyFill(P_HEAD); glowStroke(P_HEAD, 2.8, 16);
    darkFill(P_HAIR, '#16100a'); glowStroke(P_HAIR, 2, 10);
    ctx.save(); ctx.clip(P_HAIR); glowStroke(HAIR_LINES, 1.1, 5); ctx.restore();
    glowStroke(FACE_LINES, 1.5, 6); glowStroke(BROW, 2.4, 6);
    ctx.fillStyle = '#0c0905'; ctx.beginPath(); ctx.ellipse(1297, 352, 3, 3.6, 0, 0, Math.PI * 2); ctx.fill();
    accentFill(circ(1296, 351, 1.5), 8);
    crownGold(t);
  });
  drawArmGold(t, armGeo(t));
  ctx.restore();
}
// ---------- 锁链崩散：一节节烧红的链环四散飞走 ----------
const DEBRIS = (() => {
  const out = [], r = rng(4242);
  CHAINS.forEach((c, j) => {
    for (const part of splitAt(c.get(T.flash), CUTS[j], T.flash)) for (const l of sampleLinks(part)) {
      const cp = CUTS[j].pt, dx = l.x - cp[0], dy = l.y - cp[1], d = Math.hypot(dx, dy) || 1, ox = l.x - HC[0], oy = l.y - HC[1], od = Math.hypot(ox, oy) || 1;
      const sp = 250 + r() * 650;
      out.push({ ...l, vx: dx / d * sp * .6 + ox / od * sp * .7 + (r() - .5) * 200, vy: dy / d * sp * .5 + oy / od * sp * .5 - 200 - r() * 300, vr: (r() - .5) * 900, life: 1.6 + r() * 1.6 });
    }
  });
  return out;
})();
function chainDebris(t) {
  const age = t - T.flash; if (age < 0 || age > 3.4) return;
  const ls = [];
  for (const l of DEBRIS) { if (age > l.life) continue; ls.push({ x: l.x + l.vx * age * (1 - age * .12), y: l.y + l.vy * age + 520 * age * age, a: l.a, rot: l.vr * age, alt: l.alt }); }
  const { po, pe } = linksPath(ls), heat = 1 - lin(age, 0, 2.2);
  ctx.save(); ctx.globalAlpha *= 1 - lin(age, 2, 3.4); ctx.lineCap = 'round';
  ctx.strokeStyle = '#2a1408'; ctx.lineWidth = 8; ctx.stroke(po); ctx.lineWidth = 10; ctx.stroke(pe);
  ctx.globalCompositeOperation = 'lighter'; ctx.shadowColor = '#ff9a30'; ctx.shadowBlur = 16;
  ctx.strokeStyle = `rgba(255,${150 + 90 * heat},${60 + 120 * heat},.95)`; ctx.lineWidth = 2.6; ctx.stroke(po); ctx.lineWidth = 3.4; ctx.stroke(pe);
  ctx.restore();
  // 挂锁：锁梁弹开，翻着跟头坠落
  const lx = LOCK_POS[0] - 10 - 160 * age, ly = LOCK_POS[1] + 46 - 260 * age + 900 * age * age;
  drawLock(lx, ly, -.5 - age * 5, 1, 1 - lin(age, 1, 1.6), true);
}
// ---------- 白鸽 ----------
// 和平鸽（侧面、头朝 +x）：圆润的身体 + 扇形尾羽，两只翅膀从肩部张开，后缘一排扇贝形的飞羽
const DOVE_BODY = catmull([[34, -8], [28, -14], [18, -13], [4, -8], [-14, -4], [-30, 0], [-14, 7], [6, 9], [22, 4], [32, 0]], true);
const DOVE_TAIL = (() => { const p = new Path2D(); p.moveTo(-24, -2); p.lineTo(-50, -10); p.quadraticCurveTo(-56, -1, -52, 4); p.quadraticCurveTo(-55, 10, -48, 14); p.lineTo(-24, 5); p.closePath(); return p; })();
const DOVE_BEAK = poly([[33, -10], [44, -7], [33, -4]]);
function wingPath(w, sx = 1) { // w：扑动相位（1 上扬 … -1 下扑）；翼尖、后缘飞羽随相位转
  const tip = [-10 * sx, -78 * w * sx], root = [-22, -2], lead = [10, -6], p = new Path2D();
  p.moveTo(...lead); p.bezierCurveTo(14, -30 * w * sx, 4 * sx, -64 * w * sx, ...tip);
  for (let i = 1; i <= 5; i++) {
    const u = i / 5, q = [mix(tip[0], root[0], u), mix(tip[1], root[1], u)], m = [mix(tip[0], root[0], u - .1) - 14 * (1 - u * .5), mix(tip[1], root[1], u - .1)];
    p.quadraticCurveTo(...m, ...q);
  }
  p.closePath();
  return p;
}
function wingVeins(w, sx = 1) { const p = new Path2D(); for (let i = 1; i <= 4; i++) { const u = i / 5; p.moveTo(4, -6); p.lineTo(mix(-10 * sx, -22, u) - 6, mix(-78 * w * sx, -2, u) * .9); } return p; }
const FLOCK_BIRDS = FLOCKS.map((f, j) => { const r = rng(900 + j), a = []; for (let i = 0; i < (j ? 7 : 9); i++) {
  const right = r() < .3, tx = right ? 2150 + r() * 200 : -250 - r() * 200, ty = right ? -200 + r() * 260 : -220 + r() * 640;
  a.push({ t0: f + i * .09, dur: 2.2 + r() * 1.2, tx, ty, cx: (right ? 1300 : 700) + (r() - .5) * 400, cy: -150 + r() * 300, ph: r() * 6, fr: 3.2 + r() * 1.2, s: .9 + r() * .6 });
} return a; });
function birdAt(b, t, src) {
  const u = lin(t, b.t0, b.t0 + b.dur), e = 1 - Math.pow(1 - u, 1.6);
  const x = (1 - e) ** 2 * src[0] + 2 * (1 - e) * e * b.cx + e * e * b.tx, y = (1 - e) ** 2 * src[1] + 2 * (1 - e) * e * b.cy + e * e * b.ty;
  return { u, x, y };
}
function doves(t) {
  ctx.save(); ctx.lineJoin = 'round'; ctx.lineCap = 'round';
  FLOCK_BIRDS.forEach((fl, j) => fl.forEach(b => {
    if (t < b.t0 || t > b.t0 + b.dur) return;
    const src = toScr(armGeo(b.t0).flame), P = birdAt(b, t, [src[0], src[1] - 60]), Q = birdAt(b, t + .02, [src[0], src[1] - 60]);
    const ang = Math.atan2(Q.y - P.y, Q.x - P.x), left = Math.cos(ang) < 0, sc = b.s * (.35 + 1.4 * Math.pow(P.u, .7)), a = lin(P.u, 0, .06) * (1 - lin(P.u, .85, 1));
    for (let k = 1; k <= 6; k++) { // 金色尾迹
      const R = birdAt(b, t - k * .035, [src[0], src[1] - 60]); if (R.u <= 0) break;
      ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = `rgba(255,220,150,${.35 * a * (1 - k / 7)})`; ctx.beginPath(); ctx.arc(R.x, R.y, 3 * sc * (1 - k / 8), 0, 7); ctx.fill(); ctx.restore();
    }
    ctx.save(); ctx.globalAlpha *= a; ctx.translate(P.x, P.y); ctx.rotate(left ? ang - Math.PI : ang); ctx.scale(left ? -sc : sc, sc);
    const w = Math.sin(t * b.fr * Math.PI * 2 + b.ph), w2 = Math.sin(t * b.fr * Math.PI * 2 + b.ph - .35);
    const far = wingPath(w2, .78), near = wingPath(w);
    ctx.fillStyle = 'rgba(26,18,8,.9)'; ctx.fill(far); glowStroke(far, 1.4 / sc, 8, '#c99a45');
    ctx.fillStyle = 'rgba(40,28,12,.92)'; ctx.fill(DOVE_TAIL); ctx.fill(DOVE_BODY);
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = 'rgba(255,230,170,.2)'; ctx.fill(DOVE_BODY); ctx.restore();
    glowStroke(DOVE_TAIL, 1.5 / sc, 8); glowStroke(DOVE_BODY, 1.8 / sc, 10); glowStroke(DOVE_BEAK, 1.2 / sc, 6);
    ctx.fillStyle = 'rgba(40,28,12,.95)'; ctx.fill(near);
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = 'rgba(255,225,160,.18)'; ctx.fill(near); ctx.restore();
    glowStroke(near, 2 / sc, 10); glowStroke(wingVeins(w), .9 / sc, 4);
    accentFill(circ(26, -8, 1.8), 6);
    ctx.restore();
  }));
  ctx.restore();
}
function igniteBurst(t, x, y) { // 点燃那一下：白光、冲击环、四溅的火星
  const age = t - TI; if (age < 0 || age > 1.4) return;
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  const fl = 1 - lin(age, 0, .5);
  if (fl > 0) { const g = ctx.createRadialGradient(x, y - 40, 0, x, y - 40, 520); g.addColorStop(0, `rgba(255,252,240,${fl})`); g.addColorStop(.3, `rgba(255,210,130,${.4 * fl})`); g.addColorStop(1, 'rgba(255,180,80,0)'); ctx.fillStyle = g; ctx.fillRect(x - 520, y - 560, 1040, 1040); }
  for (const [d, w] of [[0, 8], [.12, 4]]) { const k = lin(age, d, d + 1); if (k <= 0 || k >= 1) continue; ctx.strokeStyle = `rgba(255,236,190,${.8 * (1 - k)})`; ctx.lineWidth = w * (1 - k) + 1; ctx.shadowColor = '#ffcf70'; ctx.shadowBlur = 20; ctx.beginPath(); ctx.arc(x, y - 40, 40 + eout(k) * 700, 0, 7); ctx.stroke(); }
  ctx.shadowBlur = 0; const r = rng(77);
  for (let i = 0; i < 70; i++) { const an = r() * Math.PI * 2, v = 200 + r() * 700, life = .5 + r() * .8; if (age > life) continue;
    const px = x + Math.cos(an) * v * age, py = y - 40 + Math.sin(an) * v * age + 300 * age * age;
    ctx.strokeStyle = `rgba(255,${200 + r() * 55},${110 + r() * 100},${1 - age / life})`; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(px - Math.cos(an) * 16, py - Math.sin(an) * 16); ctx.stroke(); }
  ctx.restore();
}
function liftWaves(t, x, y) { // 每次把火炬往上一送：一圈光波
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  for (const f of FLOCKS) { const k = lin(t, f - .05, f + 1.2); if (k <= 0 || k >= 1) continue;
    ctx.strokeStyle = `rgba(255,232,190,${.5 * (1 - k) ** 1.4})`; ctx.lineWidth = 1 + 4 * (1 - k); ctx.shadowColor = AG(); ctx.shadowBlur = 16;
    ctx.beginPath(); ctx.arc(x, y - 50, 50 + eout(k) * 520, 0, 7); ctx.stroke(); }
  ctx.restore();
}
FIG.gold = (t, k) => {
  scaled(() => {
    FIG_BASE = ctx.getTransform();
    const g = armGeo(t), fo = fireOn(t), [fx, fy] = g.flame;
    LIGHT = [fx, fy - 40]; LIGHT_K = .25 + .75 * Math.min(1, fo) * (.9 + .1 * Math.sin(t * 9) * Math.sin(t * 3.3));
    drawLiberty(t, k);
    flame(fx, fy, fo * (1 + .08 * lift(t)), t, k);
    igniteBurst(t, fx, fy);
    liftWaves(t, fx, fy);
  });
  doves(t);
};
FIG.burst = t => scaled(() => chainDebris(t));
FIG.flare = t => {
  const [x, y] = toScr(armGeo(t).flame);
  if (t >= TI) {
    flare(x, y - 60, (.25 + .1 * Math.sin(t * 2.7)) * lin(t, TI, TI + .5), 520);
    flare(x, y - 60, 1.2 * Math.sin(Math.PI * lin(t, TI, TI + .8)), 1100);
    for (const f of FLOCKS.slice(1)) flare(x, y - 60, .55 * Math.sin(Math.PI * lin(t, f - .1, f + .6)), 800);
  }
};
// 人物专属音效时间点（render.js events 导出 → audio.py）
FIG.events = [
  ...LOOPS.slice(1).map(L => ({ t: L.t0, kind: 'clank' })),
  { t: LOOPS[0].t0, kind: 'clank', g: .6 },
  ...BEATS.map(t => ({ t, kind: 'rattle' })),
  ...CUTS.map(c => ({ t: c.tc, kind: 'snap' })),
  { t: LOCK_TC, kind: 'snap', g: 1.3 },
  { t: T.flash, kind: 'chainfall' },
  { t: RISE0, kind: 'rise', dur: RISE1 - RISE0 },
  { t: TI, kind: 'ignite' },
  ...RAYS.map((r, i) => ({ t: RAY0 + i * RAY_DT, kind: 'ray', i })),
  { t: TI, kind: 'fire', t1: S.duration },
  ...FLOCKS.map((f, j) => ({ t: f, kind: 'wings', n: FLOCK_BIRDS[j].length })),
];
