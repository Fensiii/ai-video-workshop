// 人物：骑士（忠诚）
// 第一幕：黑暗里先亮起头盔眼缝里两道红光，再看见一袋银币从画面上方吊下来，晃着、往下漏钱——像钓钩上的饵；
//        骑士伸手去够它。每次心跳钱袋垂得更低、手伸得更高、银币读数往上跳（9 → 30 枚），胸前心形纹章上的裂纹又爬出一截，眼缝更红。
// 转场：金光斜斩从左下到右上，斩断吊钱袋的线（斩断时刻按斜斩缓动反推 tc），顺势削过头盔眼缝 → 劈开画面。
// 第二幕：钱袋炸开，银币烧成金币四散翻飞；骑士的手一握，剑从光里“长”出来，他把剑一路抡上来，行宣誓礼（剑柄在下颌前，剑身竖直），
//        光从护手一路跑上剑尖，剑脊上的铭文 SEMPER FIDELIS 逐字亮起，胸前的心形纹章亮了、之后一直平稳地跳；
//        之后每 2.4 秒换一个剑姿：举剑过头引下闪电 → 拄剑立誓（剑尖顿地，地面炸开一圈光）→ 宣誓礼 → 举剑 → 宣誓礼，
//        挥剑时拖出光弧，每次定格镜头一震，盔缨和披风一直在风里飘。
// 接口（index.html 调用）：FIG.SLASH / FIG.early / FIG.red / FIG.redTop / FIG.gold / FIG.burst / FIG.flare / FIG.shake / FIG.events
const FIG = {};
FIG.SLASH = { ax: 520, ay: 680, bx: 1900, by: -40 };      // 斜斩：斩断吊钱袋的线，顺势削过头盔眼缝

// ================= 工具 =================
const D2R = Math.PI / 180, dir = a => [Math.cos(a), Math.sin(a)];
const ebk = x => { const c = 1.3; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); };
const sstep = x => x * x * (3 - 2 * x);
const BEATS = heartbeats.filter(h => h > 4.8);
const beatCount = t => BEATS.reduce((s, b) => s + eback(lin(t, b, b + .25)), 0);
const beatHit = t => BEATS.reduce((m, b) => { const d = t - b; return d >= 0 && d < .4 ? Math.max(m, 1 - d / .4) : m; }, 0);
const frame = (o, d) => new DOMMatrix([d[0], d[1], -d[1], d[0], o[0], o[1]]);   // 局部 x 轴沿 d 的正交坐标系
const applyM = m => ctx.transform(m.a, m.b, m.c, m.d, m.e, m.f);
const inFrame = (m, f) => { ctx.save(); applyM(m); f(); ctx.restore(); };
const P = (pts, closed = true) => catmull(pts, closed);

// ================= 头盔（闭面盔，侧面朝左）=================
const HP = [1380, 560];
const HELM = P([[1372, 228], [1328, 236], [1296, 258], [1280, 292], [1276, 322], [1262, 336], [1240, 366], [1224, 394], [1220, 399], [1226, 405], [1240, 426], [1250, 444],
  [1258, 470], [1268, 497], [1284, 518], [1292, 540], [1300, 562], [1442, 562], [1462, 522], [1478, 470], [1482, 420], [1476, 342], [1454, 280], [1418, 246]]);
const SLIT = poly([[1266, 338], [1364, 343], [1367, 353], [1262, 348]]);
const HELM_LINES = (() => { const p = new Path2D();
  p.moveTo(1276, 327); p.quadraticCurveTo(1350, 326, 1394, 362);              // 盔顶下缘（眼缝上沿）
  p.moveTo(1263, 351); p.quadraticCurveTo(1340, 354, 1390, 370);              // 面甲上沿（眼缝下沿）
  p.moveTo(1250, 446); p.quadraticCurveTo(1335, 438, 1392, 388);              // 面甲下沿
  p.moveTo(1286, 354); p.quadraticCurveTo(1258, 388, 1268, 432);              // 鸟喙状面甲的折棱
  p.moveTo(1398, 388); p.quadraticCurveTo(1432, 430, 1452, 500);              // 护颚侧缘
  p.moveTo(1266, 492); p.quadraticCurveTo(1360, 496, 1446, 470);              // 护颚
  p.moveTo(1288, 528); p.quadraticCurveTo(1370, 538, 1462, 522);              // 护喉甲片
  p.moveTo(1294, 546); p.quadraticCurveTo(1372, 556, 1452, 546);
  p.moveTo(1404, 372); p.quadraticCurveTo(1452, 380, 1478, 420);              // 盔顶后缘
  p.moveTo(1296, 272); p.quadraticCurveTo(1352, 226, 1446, 266);              // 盔脊
  return p; })();
const HELM_HOLES = (() => { const p = new Path2D(); // 面甲上的透气孔 + 护颚上一列圆孔
  for (let r = 0; r < 3; r++) for (let c = 0; c < 4; c++) { const x = 1290 + c * 17 + r * 5, y = 395 + r * 12 + c * 1.5; p.roundRect(x, y, 10, 4, 2); }
  for (let i = 0; i < 4; i++) { p.moveTo(1424 + i * 4 + 3.5, 444 + i * 13); p.arc(1424 + i * 4, 444 + i * 13, 3.5, 0, Math.PI * 2); }
  return p; })();
const HELM_RIVETS = [[1398, 376, 9], [1426, 378, 3.5], [1452, 390, 3.5], [1470, 410, 3.5], [1300, 534, 3], [1440, 528, 3]];
const RONDEL = circ(1484, 470, 17), RONDEL_IN = circ(1484, 470, 10), RONDEL_SPIKE = circ(1484, 470, 3.5);
const COMB = P([[1294, 266], [1318, 222], [1366, 202], [1416, 212], [1452, 244], [1446, 262], [1412, 234], [1368, 226], [1326, 240], [1304, 272]]);  // 盔顶的脊冠
const COMB_LINE = (() => { const p = new Path2D(); p.moveTo(1306, 252); p.quadraticCurveTo(1366, 200, 1446, 252); return p; })();
const PLUME_HOLDER = poly([[1444, 262], [1462, 254], [1474, 270], [1458, 282]]);
const PLUME_B = [1462, 268];
function headA(t) {
  if (t < T.flash) return -.04 - .008 * beatCount(t) + .006 * Math.sin(t * 1.3);
  const nod = HITS.reduce((m, h) => { const d = t - h.t; return d >= 0 && d < .9 ? Math.max(m, Math.sin(Math.PI * d / .9) * (h.type === 'salute' ? 1 : .5)) : m; }, 0);
  return mix(-.04 - .008 * BEATS.length, .01, eio(lin(t, T.flash, T.flash + 1))) + .055 * nod + .005 * Math.sin(t * .9);
}
// 头盔整体缩小、拉高一点（头小肩宽才显得英武）；下面的头盔坐标都是缩放前的，HELM_S 在 withHead 里统一套上
const HELM_S = new DOMMatrix().translate(1385, 562).scale(.82, .88).translate(-1385, -562);
const withHead = (t, f) => { ctx.save(); ctx.translate(...HP); ctx.rotate(headA(t)); ctx.translate(-HP[0], -HP[1]); applyM(HELM_S); f(); ctx.restore(); };

// ================= 盔缨（九根长羽，往后飘）=================
function feather(t, i, gold) {
  const n = 16, L = 330 - i * 14, pts = [];
  let a = -1.3 + i * .13 + (gold ? 0 : .55), x = PLUME_B[0], y = PLUME_B[1];
  const amp = gold ? .16 : .07, sp = gold ? 2.6 : 1.1;
  for (let j = 0; j <= n; j++) {
    const s = j / n; pts.push([x, y]);
    a += (gold ? 1.85 : 2.3) / n * (1 + i * .03) + amp * Math.sin(t * sp - s * 4.2 + i * .8) * s / n * 6;
    x += Math.cos(a) * L / n; y += Math.sin(a) * L / n;
  }
  const Lft = [], Rgt = [];
  for (let j = 0; j <= n; j++) {
    const s = j / n, p = pts[j], q = pts[Math.min(n, j + 1)], o = pts[Math.max(0, j - 1)], tx = q[0] - o[0], ty = q[1] - o[1], tl = Math.hypot(tx, ty) || 1;
    const w = (gold ? 15 : 11) * Math.sin(Math.PI * Math.min(1, .12 + s * .95)) * (1 - s * .35) * (gold || j % 3 ? 1 : .55);  // 第一幕羽毛残破
    Lft.push([p[0] - ty / tl * w, p[1] + tx / tl * w]); Rgt.push([p[0] + ty / tl * w, p[1] - tx / tl * w]);
  }
  const body = new Path2D(); body.moveTo(...pts[0]); for (const q of Lft) body.lineTo(...q); for (const q of Rgt.reverse()) body.lineTo(...q); body.closePath();
  const quill = new Path2D(); quill.moveTo(...pts[0]); for (const q of pts) quill.lineTo(...q);
  const barbs = new Path2D(); Rgt.reverse();
  for (let j = 2; j < n - 1; j += 2) { const p = pts[j], m = pts[j - 2], side = (j / 2) % 2 ? Lft : Rgt; barbs.moveTo(mix(p[0], side[j][0], .15), mix(p[1], side[j][1], .15)); barbs.quadraticCurveTo(mix(m[0], side[j - 1][0], .6), mix(m[1], side[j - 1][1], .6), mix(m[0], side[j - 2][0], .85), mix(m[1], side[j - 2][1], .85)); }
  return { body, quill, barbs };
}

// ================= 身体（胸甲 + 腹甲 + 甲裙）=================
const BODY0 = [[1318, 548], [1270, 562], [1222, 590], [1192, 646], [1184, 712], [1196, 790], [1230, 856], [1262, 906], [1262, 960], [1258, 1095], [1592, 1095],
  [1594, 960], [1594, 904], [1620, 840], [1660, 762], [1690, 676], [1672, 618], [1610, 582], [1520, 562], [1440, 552]];
const P_BODY = P(BODY0);
const BODY_LINES = (() => { const p = new Path2D();
  p.moveTo(1320, 568); p.quadraticCurveTo(1404, 604, 1494, 572);               // 胸甲领口的卷边
  p.moveTo(1326, 582); p.quadraticCurveTo(1404, 618, 1488, 586);
  p.moveTo(1336, 610); p.bezierCurveTo(1306, 700, 1304, 790, 1326, 868);       // 胸甲中脊
  p.moveTo(1262, 908); p.bezierCurveTo(1298, 884, 1314, 826, 1330, 796);       // 腹甲：中间尖起来的拱
  p.bezierCurveTo(1350, 826, 1460, 878, 1594, 906);
  p.moveTo(1262, 922); p.bezierCurveTo(1300, 898, 1316, 842, 1330, 814); p.bezierCurveTo(1348, 842, 1458, 892, 1594, 920);
  for (const y of [952, 994, 1036, 1078]) { p.moveTo(1262, y); p.quadraticCurveTo(1424, y + 18, 1594, y - 4); }  // 甲裙
  p.moveTo(1664, 700); p.quadraticCurveTo(1612, 790, 1600, 900);               // 侧甲
  p.moveTo(1200, 760); p.quadraticCurveTo(1250, 740, 1296, 700);               // 胸甲的弧面
  return p; })();
const FAR_PAUL = P([[1566, 592], [1612, 566], [1664, 570], [1702, 604], [1712, 650], [1694, 690], [1652, 702], [1602, 686], [1574, 646]]);  // 背后那侧露出来的肩甲
const FAR_PAUL_LINES = (() => { const p = new Path2D(); p.moveTo(1580, 650); p.quadraticCurveTo(1640, 684, 1704, 652); p.moveTo(1576, 624); p.quadraticCurveTo(1640, 654, 1708, 624); p.moveTo(1612, 572); p.quadraticCurveTo(1630, 620, 1626, 690); return p; })();
const BODY_ETCH = (() => { const p = new Path2D(); // 胸甲卷边、腹甲边上的蚀刻花纹（一串小菱形）
  for (let i = 0; i <= 14; i++) { const u = i / 14, x = mix(1330, 1484, u), y = 594 + Math.sin(Math.PI * u) * 22; p.moveTo(x, y - 3); p.lineTo(x + 3, y); p.lineTo(x, y + 3); p.lineTo(x - 3, y); p.closePath(); }
  for (let i = 0; i <= 10; i++) { const u = i / 10, x = mix(1340, 1590, u), y = 830 + u * 72 - Math.sin(Math.PI * u) * 8; p.moveTo(x, y - 3); p.lineTo(x + 3, y); p.lineTo(x, y + 3); p.lineTo(x - 3, y); p.closePath(); }
  return p; })();
const BODY_RIVETS = [[1272, 958], [1272, 1000], [1272, 1042], [1584, 952], [1584, 994], [1584, 1036], [1328, 588], [1488, 584]];
// 胸前的盾形纹章 + 心
const EMB = [1478, 740];
const P_SHIELD = (() => { const s = catmull([[-50, -56], [0, -60], [50, -56], [50, 0], [30, 36], [0, 62], [-30, 36], [-50, 0]], true), p = new Path2D(); p.addPath(s, new DOMMatrix().translate(...EMB)); return p; })();
const P_HEART = (() => { const h = new Path2D(); h.moveTo(0, 26); h.bezierCurveTo(-44, -4, -30, -40, 0, -18); h.bezierCurveTo(30, -40, 44, -4, 0, 26); h.closePath();
  const p = new Path2D(); p.addPath(h, new DOMMatrix().translate(EMB[0], EMB[1] - 4)); return p; })();
const SHIELD_IN = (() => { const s = catmull([[-40, -46], [0, -49], [40, -46], [40, -2], [24, 28], [0, 49], [-24, 28], [-40, -2]], true), p = new Path2D(); p.addPath(s, new DOMMatrix().translate(...EMB)); return p; })();
const CRACKS_E = (() => { const r = rng(55), out = []; // 纹章上的裂纹：从心口往外爬
  for (let i = 0; i < 9; i++) { let x = EMB[0] + (r() - .5) * 10, y = EMB[1] - 4 + (r() - .5) * 10, a = r() * Math.PI * 2; const pts = [[x, y]];
    for (let j = 0; j < 10; j++) { a += (r() - .5) * 1.2; const l = 8 + r() * 16; x += Math.cos(a) * l; y += Math.sin(a) * l; pts.push([x, y]); }
    out.push({ pts, order: i }); }
  return out; })();
// 肩甲（层叠甲片）
const S0 = [1292, 628];
// 肩甲：按手臂自然下垂（UA_REST）时的画面坐标设计，再换到局部坐标（原点在肩，x 沿上臂往肘）。
// 顶片（带护颈翼）跟着上臂转一半，下面三层甲片完全跟着上臂走——手一抬，肩甲就跟着翻起来。
const UA_REST = 122 * D2R;
const TO_LOCAL = new DOMMatrix([Math.cos(UA_REST), Math.sin(UA_REST), -Math.sin(UA_REST), Math.cos(UA_REST), S0[0], S0[1]]).inverse();
const local = path => { const p = new Path2D(); p.addPath(path, TO_LOCAL); return p; };
const localPts = pts => pts.map(([x, y, r]) => { const q = TO_LOCAL.transformPoint(new DOMPoint(x, y)); return r ? [q.x, q.y, r] : [q.x, q.y]; });
const PAUL_W = [[1300, 550], [1250, 558], [1212, 580], [1192, 616], [1190, 652], [1206, 682], [1238, 702], [1280, 706], [1328, 692], [1370, 664], [1400, 626], [1396, 586], [1358, 560]];
const PAUL_SC = new DOMMatrix().translate(1296, 600).scale(.86).translate(-1296, -600);  // 整体缩一点
const PAUL = local(P(PAUL_W.map(([x, y]) => { const q = PAUL_SC.transformPoint(new DOMPoint(x, y)); return [q.x, q.y]; })));
const FLANGE = P([[1300, 566], [1310, 534], [1342, 514], [1380, 518], [1404, 548], [1400, 576], [1352, 572]]);   // 护颈翼：肩头翘起来的一片（固定在身上，不跟手臂转）
const FLANGE_L = (() => { const p = new Path2D(); p.moveTo(1312, 540); p.quadraticCurveTo(1350, 526, 1394, 546); return p; })();
const PW = PAUL_W.map(([x, y]) => { const q = PAUL_SC.transformPoint(new DOMPoint(x, y)); return [q.x, q.y]; });
const LAMES = [3, 2, 1].map(i => local(P(PW.slice(4, 10).map(([x, y], j) => [x - 9 * i - j * 1.5, y + 14 * i]).concat(
  PW.slice(4, 10).reverse().map(([x, y], j) => [x - 9 * i + 10 - (5 - j) * 1.5, y + 14 * i - 26])))));                 // 顶片下缘往下错开的三层甲片
const PAUL_LINES = local((() => { const p = new Path2D();
  p.moveTo(1298, 562); p.bezierCurveTo(1276, 610, 1252, 660, 1244, 702);   // 顶片的脊
  p.moveTo(1208, 610); p.quadraticCurveTo(1300, 648, 1394, 606);            // 甲面的弧
  p.moveTo(1302, 528); p.quadraticCurveTo(1340, 516, 1384, 534);            // 护颈翼的卷边
  return p; })());
const PAUL_EDGE = local((() => { const p = new Path2D(); p.addPath(P(PW), new DOMMatrix().translate(1296, 640).scale(.86).translate(-1296, -640)); return p; })());
const PAUL_RIVETS = localPts([[1206, 640, 3.5], [1222, 676, 3.5], [1270, 694, 3.5], [1326, 680, 3.5], [1376, 640, 3.5], [1380, 594, 3.5], [1300, 600, 4.5]]);
const shellM = (ua) => frame(S0, dir(UA_REST + (ua - UA_REST) * .45));
const paulDraw = (R, gold, t) => { // 护颈翼（固定）→ 甲片 → 顶片
  if (gold) { armorFill(FLANGE); sheen(FLANGE, [[1350, 530, 40, 12, .25]]); glowStroke(FLANGE, 2, 10); glowStroke(FLANGE_L, 1, 4); }
  else { darkMetal(FLANGE, 1350, 540, 80); redStroke(FLANGE, 1.6, 8); }
  inFrame(R.mU, () => { for (const l of LAMES) { if (gold) { armorFill(l); sheen(l, [[60, -40, 60, 12, .18]]); glowStroke(l, 2, 9); } else { darkMetal(l, 80, 0, 80); redStroke(l, 1.8, 8); } } });
  inFrame(shellM(R.ua), () => {
    if (gold) { armorFill(PAUL); sheen(PAUL, [[-10, -10, 60, 40, .32], [50, 10, 30, 30, .12]]); gleam(PAUL, t, -140, 140);
      glowStroke(PAUL, 2.6, 14); glowStroke(PAUL_LINES, 1.3, 6); glowStroke(PAUL_EDGE, .7, 3, '#c9944a'); rivets(PAUL_RIVETS, true); }
    else { darkMetal(PAUL, 0, -20, 120); redStroke(PAUL, 2.2, 12);
      ctx.strokeStyle = 'rgba(255,110,70,.55)'; ctx.lineWidth = 1.3; ctx.stroke(PAUL_LINES); ctx.lineWidth = .8; ctx.stroke(PAUL_EDGE); }
  });
};
// 披风（在身后，往右飘）
function capePath(t, gold) {
  const sp = gold ? 1.7 : .9, amp = gold ? 1 : .45, R = [], hem = [];
  for (let k = 0; k <= 9; k++) { const u = k / 9, y = 590 + u * 530; R.push([1650 + u * 330 + (60 * Math.sin(t * sp - u * 3.4) + 22 * Math.sin(t * sp * 1.7 - u * 6)) * u * amp, y - 40 * Math.sin(Math.PI * u) * amp]); }
  for (let k = 1; k <= 8; k++) { const u = k / 8, x = mix(R[9][0], 1480, u); hem.push([x, 1120 - 18 * Math.sin(t * sp * 1.3 + u * 7) * amp + (gold ? 0 : (k % 2 ? 26 : -8))]); }
  const pts = [[1470, 566], [1560, 578], ...R, ...hem, [1470, 900]];
  const folds = new Path2D();
  for (let i = 0; i < 4; i++) { const u0 = .2 + i * .2, a = [1560 + i * 26, 610], b = R[Math.round(3 + i * 1.5)], c = hem[Math.min(7, 1 + i * 2)];
    folds.moveTo(...a); folds.quadraticCurveTo(mix(b[0], a[0], .4), b[1], c[0], c[1] - 20); }
  return { path: P(pts), folds };
}

// ================= 手臂（骨骼）+ 剑 =================
const LU = 186, LF = 180;
const REREBRACE = P([[20, -46], [80, -46], [LU - 12, -40], [LU + 4, -36], [LU + 4, 36], [LU - 12, 40], [80, 46], [20, 46], [8, 0]]);
const RERE_LINES = (() => { const p = new Path2D(); for (const u of [118, 150]) { p.moveTo(u, -44); p.quadraticCurveTo(u + 9, 0, u, 44); } p.moveTo(100, -22); p.quadraticCurveTo(140, -24, LU - 6, -18); return p; })();
const VAMB = P([[-4, -40], [40, -40], [100, -35], [LF - 36, -31], [LF - 36, 31], [100, 35], [40, 40], [-4, 40]]);
const VAMB_LINES = (() => { const p = new Path2D(); p.moveTo(8, -10); p.quadraticCurveTo(70, -14, LF - 40, -8); p.moveTo(58, -32); p.quadraticCurveTo(66, 0, 58, 32); return p; })();
const CUFF = P([[LF - 44, -31], [LF - 8, -46], [LF + 10, -44], [LF + 13, 0], [LF + 10, 44], [LF - 8, 46], [LF - 44, 31]]);
const CUFF_LINES = (() => { const p = new Path2D(); for (const u of [LF - 26, LF - 9]) { p.moveTo(u, -38); p.quadraticCurveTo(u + 7, 0, u, 38); } return p; })();
// 第一幕：张开去够钱袋的手（前臂坐标里，手指顺着前臂方向往前伸）
const OPEN_PALM = P([[LF - 8, -30], [LF + 30, -36], [LF + 56, -30], [LF + 62, -6], [LF + 58, 22], [LF + 30, 32], [LF - 8, 30]]);
const PALM_LINES = (() => { const p = new Path2D(); p.moveTo(LF + 50, -30); p.quadraticCurveTo(LF + 62, 0, LF + 52, 26); p.moveTo(LF + 22, -34); p.quadraticCurveTo(LF + 30, 0, LF + 22, 30); return p; })();
const FINGER_SEGS = (() => { // 四根铰接的手指（每根三节甲片）+ 拇指，张开往前够
  const out = [];
  const finger = (b, a0, lens, curl, w) => { let p = b, a = a0; lens.forEach((L, k) => { const q = [p[0] + Math.cos(a) * L, p[1] + Math.sin(a) * L]; out.push(limb(p, q, w - k * 2, w - k * 2 - 2)); p = q; a += curl; }); };
  [[-24, -.28], [-9, -.1], [6, .08], [20, .26]].forEach(([v, a], i) => finger([LF + 58, v], a, [28, 23, 18 - i], -.28, 17 - i));
  finger([LF + 18, 28], .95, [26, 22], -.45, 17);
  return out; })();
// 剑（剑的坐标：原点是握把中心，x 沿剑身，手腕在 +y 一侧）
const BL = 640;
const POMMEL = P([[-58, 0], [-64, -13], [-78, -18], [-92, -12], [-98, 0], [-92, 12], [-78, 18], [-64, 13]]), POMMEL_IN = (() => { const p = new Path2D(); p.moveTo(-64, 0); p.lineTo(-94, 0); p.moveTo(-78, -15); p.quadraticCurveTo(-86, 0, -78, 15); return p; })(), POMMEL_GEM = circ(-102, 0, 4.5);
const GRIP = rr(-58, -9, 84, 18, 5);
const GRIP_WRAP = (() => { const p = new Path2D(); for (let x = -54; x < 22; x += 9) { p.moveTo(x, -9); p.lineTo(x + 7, 9); } return p; })();
const GUARD = poly([[24, -12], [30, -86], [36, -96], [46, -90], [40, -12], [40, 12], [46, 90], [36, 96], [30, 86], [24, 12]]);
const GUARD_KNOBS = (() => { const p = new Path2D(); p.arc(40, -96, 7, 0, Math.PI * 2); p.moveTo(47, 96); p.arc(40, 96, 7, 0, Math.PI * 2); return p; })();
const LANGET = poly([[26, -15], [58, 0], [26, 15]]);
const GUARD_GEM = circ(33, 0, 6);
const BLADE = poly([[40, -21], [420, -18], [BL - 60, -11], [BL, 0], [BL - 60, 11], [420, 18], [40, 21]]);
const BLADE_LINES = (() => { const p = new Path2D(); p.moveTo(44, -9); p.lineTo(BL - 30, -1.5); p.moveTo(44, 9); p.lineTo(BL - 30, 1.5); return p; })();
const FULLER = rr(60, -4.5, 360, 9, 4.5);
const RUNES = 'SEMPER · FIDELIS';
// 握剑的铁手套（剑的坐标）
const FIST = P([[-32, 30], [-35, 6], [-33, -16], [-24, -30], [-8, -35], [8, -35], [24, -30], [33, -16], [36, 8], [30, 32], [10, 46], [-16, 46]]);
const FIST_LINES = (() => { const p = new Path2D();
  for (const x of [-17, -1, 15]) { p.moveTo(x, -34); p.quadraticCurveTo(x + 4, -12, x, 10); }       // 指节甲片
  p.moveTo(-32, 12); p.quadraticCurveTo(0, 19, 35, 12);                                            // 指根的护甲脊
  p.moveTo(-28, 28); p.quadraticCurveTo(0, 34, 30, 30);
  for (const x of [-20, -4, 12]) { p.moveTo(x, -27); p.lineTo(x + 6, -27); }                      // 指尖的小甲片
  return p; })();
const THUMB_P = P([[14, -10], [36, -20], [46, -6], [36, 16], [16, 12]]);
const THUMB_L = (() => { const p = new Path2D(); p.moveTo(26, -14); p.quadraticCurveTo(30, 0, 26, 14); return p; })();

// 姿势：H 握把中心、sa 剑的朝向（度，按挥动方向连续写）、side 手腕在剑哪一侧、hint 肘尖大概在哪（解 IK 时选解）
function ik(W, hint) {
  const S = S0, dx = W[0] - S[0], dy = W[1] - S[1], d = Math.min(Math.hypot(dx, dy), LU + LF - 1), ux = dx / Math.hypot(dx, dy), uy = dy / Math.hypot(dx, dy);
  const a = (LU * LU - LF * LF + d * d) / (2 * d), h = Math.sqrt(Math.max(0, LU * LU - a * a)), b = [S[0] + ux * a, S[1] + uy * a];
  const c1 = [b[0] - uy * h, b[1] + ux * h], c2 = [b[0] + uy * h, b[1] - ux * h];
  const E = Math.hypot(c1[0] - hint[0], c1[1] - hint[1]) < Math.hypot(c2[0] - hint[0], c2[1] - hint[1]) ? c1 : c2;
  const Wr = [S[0] + ux * d, S[1] + uy * d];
  return { ua: Math.atan2(E[1] - S[1], E[0] - S[0]), fa: Math.atan2(W[1] - E[1], W[0] - E[0]) };
}
const WR_X = -4, WR_Y = 44;   // 手腕接在铁拳背面的这一点（剑的坐标）
function wristFor(H, sa, side) { const d = dir(sa * D2R), n = [-d[1], d[0]]; return [H[0] + WR_X * d[0] + side * WR_Y * n[0], H[1] + WR_X * d[1] + side * WR_Y * n[1]]; }
const POSE = {
  draw:   { H: [1170, 900], sa: 160, side: -1, hint: [1400, 800] },   // 剑从光里长出来时：低垂在身前
  salute: { H: [1150, 560], sa: 270, side: 1, hint: [1060, 860] },    // 宣誓礼：肘尖朝前下，剑柄在下颌前，剑身竖直
  over:   { H: [1122, 318], sa: 244, side: 1, hint: [1020, 520] },    // 举剑过头：手臂几乎伸直，高举在头盔前上方
  vigil:  { H: [1110, 820], sa: 90, side: -1, hint: [1340, 800] },    // 拄剑：手臂下垂、前臂前伸，手按在身前的剑柄上，剑尖朝下顿地
};
for (const k in POSE) { const p = POSE[k]; Object.assign(p, ik(wristFor(p.H, p.sa, p.side), p.hint)); }
const REACH_HINT = [1240, 840];
const reachW = t => { const g = beatCount(Math.min(t, T.flash)); return [1150 - g, 650 - 5 * g]; };
const OATH = T.flash + 1.3;
const KEYS = [[T.flash, 'reach'], [T.flash + .55, 'draw'], [OATH, 'salute'], [12.45, 'salute'], [12.9, 'over'], [14.85, 'over'], [15.3, 'vigil'],
  [17.25, 'vigil'], [17.7, 'salute'], [19.65, 'salute'], [20.1, 'over'], [22.05, 'over'], [22.5, 'salute'], [99, 'salute']];
const KP = (() => { // 各关键帧的角度，按顺序展开成连续的（不让手臂绕远路）
  const out = []; let pu = null, pf = null;
  for (const [t, name] of KEYS) {
    const p = name === 'reach' ? { ...ik(reachW(T.flash), REACH_HINT), sa: 160, side: -1 } : POSE[name];
    let ua = p.ua, fa = p.fa;
    if (pu !== null) { while (ua - pu > Math.PI) ua -= 2 * Math.PI; while (ua - pu < -Math.PI) ua += 2 * Math.PI; while (fa - pf > Math.PI) fa -= 2 * Math.PI; while (fa - pf < -Math.PI) fa += 2 * Math.PI; }
    pu = ua; pf = fa; out.push({ t, name, ua, fa, sa: p.sa * D2R, side: p.side });
  }
  return out; })();
const HITS = KP.map((k, i) => ({ k, i })).filter(({ k, i }) => i > 0 && k.name !== KP[i - 1].name && k.name !== 'draw').map(({ k, i }) => ({ t: k.t, type: k.name, start: KP[i - 1].t }));
const SUMMON0 = T.flash + .3, SUMMON1 = T.flash + .95;   // 剑从护手往剑尖“长”出来
function poseAt(t) {
  if (t < T.flash) { const p = ik(reachW(t), REACH_HINT), tug = beatHit(t); return { ua: p.ua, fa: p.fa - .04 * tug, sa: 160 * D2R, side: -1 }; }
  let i = 0; while (i < KP.length - 2 && t >= KP[i + 1].t) i++;
  const A = KP[i], B = KP[i + 1], s = lin(t, A.t, B.t);
  const f = A.name === B.name ? 0 : A.name === 'reach' ? eio(s) : ebk(sstep(s));
  const br = Math.sin(t * 1.2) * .012;
  return { ua: mix(A.ua, B.ua, f) + br, fa: mix(A.fa, B.fa, f) + br * 1.3, sa: mix(A.sa, B.sa, f) + br * .6, side: mix(A.side, B.side, f) };
}
function rig(t) {
  const p = poseAt(t), du = dir(p.ua), df = dir(p.fa), E = [S0[0] + du[0] * LU, S0[1] + du[1] * LU], W = [E[0] + df[0] * LF, E[1] + df[1] * LF];
  const d = dir(p.sa), n = [-d[1], d[0]], sg = p.side >= 0 ? 1 : -1;
  const H = [W[0] - WR_X * d[0] - p.side * WR_Y * n[0], W[1] - WR_X * d[1] - p.side * WR_Y * n[1]];
  const mS = new DOMMatrix([d[0], d[1], n[0] * sg, n[1] * sg, H[0], H[1]]);
  const tip = [H[0] + d[0] * BL, H[1] + d[1] * BL], guard = [H[0] + d[0] * 40, H[1] + d[1] * 40];
  return { ...p, du, df, E, W, H, d, n, sg, mU: frame(S0, du), mF: frame(E, df), mS, tip, guard };
}
const bladeVis = t => t < SUMMON0 ? 0 : eout(lin(t, SUMMON0, SUMMON1));
const swordA = t => lin(t, SUMMON0 - .15, SUMMON0 + .1);

// ================= 钱袋（第一幕）=================
const ANCHOR = [1090, -30];
function purse(t) {
  const tt = Math.min(t, T.flash), drop = 6 * beatCount(tt), sway = .05 * Math.sin(t * 1.25) + .02 * Math.sin(t * 2.9) + .02 * beatHit(t);
  const knot = rot([1090, 360 + drop], ANCHOR, sway);
  return { knot, sway, m: new DOMMatrix().translate(...knot).rotate(sway / D2R) };
}
const SACK = P([[-10, 0], [-22, 14], [-46, 40], [-57, 72], [-48, 102], [-20, 118], [20, 118], [48, 102], [57, 72], [46, 40], [22, 14], [10, 0]]);
const SACK_TOP = P([[-10, 2], [-24, -18], [-8, -10], [0, -24], [8, -10], [24, -18], [10, 2]]);
const SACK_LINES = (() => { const p = new Path2D(); p.moveTo(-16, 8); p.quadraticCurveTo(0, 14, 16, 8); p.moveTo(-30, 40); p.quadraticCurveTo(-40, 80, -26, 108); p.moveTo(26, 36); p.quadraticCurveTo(40, 76, 30, 106); p.moveTo(-6, 118); p.lineTo(-2, 110); p.lineTo(4, 118); return p; })();
const SACK_COIN = circ(4, 70, 20), SACK_COIN_IN = circ(4, 70, 14);
const COIN_T = (() => { const a = []; for (let x = 5.0; x < T.flash - .3; x += .42) a.push(x); return a; })();
const PURSE_CUT = (() => { const p = purse(T.slash), A = [FIG.SLASH.ax, FIG.SLASH.ay], B = [FIG.SLASH.bx, FIG.SLASH.by];
  const r = [p.knot[0] - ANCHOR[0], p.knot[1] - ANCHOR[1]], s = [B[0] - A[0], B[1] - A[1]], den = r[0] * s[1] - r[1] * s[0];
  const u = ((A[0] - ANCHOR[0]) * s[1] - (A[1] - ANCHOR[1]) * s[0]) / den, v = ((A[0] - ANCHOR[0]) * r[1] - (A[1] - ANCHOR[1]) * r[0]) / den;
  return { u, pt: [ANCHOR[0] + r[0] * u, ANCHOR[1] + r[1] * u], tc: T.slash + .3 * (1 - Math.pow(1 - clamp(v), 1 / 3)) }; })();
function drawCoin(x, y, r, spin, style, a = 1) { // 硬币：按自转把椭圆压扁，侧过来时露出厚度
  const c = Math.cos(spin), rx = Math.max(2.5, r * Math.abs(c));
  ctx.save(); ctx.globalAlpha *= a; ctx.translate(x, y);
  const face = new Path2D(); face.ellipse(0, 0, rx, r, 0, 0, Math.PI * 2);
  if (style === 'red') { ctx.fillStyle = '#3a1410'; ctx.fill(face); ctx.strokeStyle = '#ffb0a0'; ctx.lineWidth = 1.6; ctx.shadowColor = '#ff3010'; ctx.shadowBlur = 10; ctx.stroke(face); }
  else { const g = ctx.createLinearGradient(-rx, -r, rx, r); g.addColorStop(0, '#fff2c0'); g.addColorStop(.5, '#e7b44e'); g.addColorStop(1, '#8a5a1a'); ctx.fillStyle = g; ctx.shadowColor = 'rgba(255,200,90,.9)'; ctx.shadowBlur = 12; ctx.fill(face); }
  ctx.shadowBlur = 0;
  if (rx > 5) { const in_ = new Path2D(); in_.ellipse(0, 0, rx * .68, r * .68, 0, 0, Math.PI * 2); ctx.strokeStyle = style === 'red' ? 'rgba(255,150,120,.6)' : 'rgba(120,70,10,.7)'; ctx.lineWidth = 1.2; ctx.stroke(in_); }
  ctx.restore();
}
function drawPurse(t, a) {
  if (a <= 0) return;
  const p = purse(t), cut = t >= PURSE_CUT.tc;
  ctx.save(); ctx.globalAlpha *= a;
  // 吊线（斩断后上半截往上收）
  const top = cut ? mix(PURSE_CUT.pt[1], -40, eout(lin(t, PURSE_CUT.tc, PURSE_CUT.tc + .4))) : null;
  ctx.strokeStyle = 'rgba(255,120,90,.8)'; ctx.lineWidth = 1.6; ctx.shadowColor = '#ff3010'; ctx.shadowBlur = 8;
  ctx.beginPath();
  if (!cut) { ctx.moveTo(...ANCHOR); ctx.lineTo(...p.knot); }
  else { ctx.moveTo(ANCHOR[0], ANCHOR[1]); ctx.lineTo(mix(ANCHOR[0], PURSE_CUT.pt[0], 1), top); const d = eout(lin(t, PURSE_CUT.tc, PURSE_CUT.tc + .3)); ctx.moveTo(PURSE_CUT.pt[0] + 6 * d, PURSE_CUT.pt[1] + 30 * d); ctx.lineTo(...p.knot); }
  ctx.stroke(); ctx.shadowBlur = 0;
  ctx.save(); const fall = cut ? 60 * Math.pow(lin(t, PURSE_CUT.tc, T.flash), 2) : 0; ctx.translate(0, fall); applyM(p.m);
  ctx.fillStyle = '#1e0806'; ctx.fill(SACK); redStroke(SACK, 2.2, 12); ctx.fillStyle = '#240a07'; ctx.fill(SACK_TOP); redStroke(SACK_TOP, 1.6, 8);
  ctx.strokeStyle = 'rgba(255,120,90,.55)'; ctx.lineWidth = 1.3; ctx.stroke(SACK_LINES);
  ctx.fillStyle = '#3a1410'; ctx.fill(SACK_COIN); redStroke(SACK_COIN, 1.6, 8); ctx.strokeStyle = 'rgba(255,170,140,.7)'; ctx.lineWidth = 1.2; ctx.stroke(SACK_COIN_IN);
  ctx.font = '18px SerifBlack'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillStyle = '#ffb49a'; ctx.fillText('银', 4, 71);
  ctx.restore();
  // 袋底漏下来的银币，掉过那只手往下落
  for (const [j, c0] of COIN_T.entries()) {
    const age = t - c0; if (age < 0 || age > 1.4) continue;
    const q = purse(c0), b = new DOMMatrix(q.m).transformPoint(new DOMPoint(0, 116));
    drawCoin(b.x + (j % 3 - 1) * 14 * age + 18 * age, b.y + 260 * age * age + 30 * age, 12, age * 9 + j, 'red', 1 - lin(age, 1, 1.4));
  }
  ctx.restore();
}
function coinReadout(t, a) { // 银币读数：每次心跳往上跳
  if (a <= 0) return;
  const n = Math.min(30, 9 + Math.round(3 * beatCount(t))), hit = beatHit(t), s = 1 + .12 * hit;
  ctx.save(); ctx.globalAlpha = a; ctx.textBaseline = 'alphabetic'; ctx.translate(820, 600); ctx.scale(s, s);
  ctx.font = '28px SansBold'; const wl = ctx.measureText('银币 ×').width; ctx.font = '72px CinzelBold'; const wn = ctx.measureText(String(n)).width;
  const x = -(wl + wn + 70) / 2;
  ctx.fillStyle = 'rgba(14,3,2,.75)'; ctx.fill(rr(x - 24, -74, wl + wn + 120, 96, 12)); ctx.strokeStyle = `rgba(255,80,50,${.45 + .5 * hit})`; ctx.lineWidth = 1.6; ctx.stroke(rr(x - 24, -74, wl + wn + 120, 96, 12));
  ctx.font = '28px SansBold'; ctx.fillStyle = '#ffb08a'; ctx.fillText('银币 ×', x, -8);
  ctx.font = '72px CinzelBold'; ctx.shadowColor = '#ff2a10'; ctx.shadowBlur = 22 + 30 * hit; ctx.fillStyle = hit > .5 ? '#ffffff' : '#ffe0d0'; ctx.fillText(String(n), x + wl + 12, 0);
  ctx.font = '24px SansBold'; ctx.shadowBlur = 8; ctx.fillStyle = '#ff9a7a'; ctx.fillText('枚', x + wl + wn + 18, 0);
  ctx.fillStyle = `rgba(255,70,40,${.65 + .35 * hit})`; ctx.font = '24px SansBold'; ctx.fillText('▲', x + wl + wn + 52, -36 - 8 * hit);
  ctx.restore();
}

// ================= 第一幕 =================
function darkMetal(path, x = 1320, y = 600, r = 500) { const g = ctx.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, '#3a100b'); g.addColorStop(.6, '#1c0605'); g.addColorStop(1, '#0c0303'); ctx.fillStyle = g; ctx.fill(path); }
function eyeGlow(t, a, gold) { // 头盔眼缝里的光
  if (a <= 0) return;
  ctx.save(); ctx.globalAlpha *= a;
  ctx.fillStyle = gold ? '#fff4dc' : '#ff5a30'; ctx.shadowColor = gold ? '#ffb040' : '#ff2000'; ctx.shadowBlur = 18; ctx.fill(SLIT);
  ctx.globalCompositeOperation = 'lighter';
  for (const [x, y] of [[1296, 345], [1336, 347]]) {
    const R0 = gold ? 46 : 54, g = ctx.createRadialGradient(x, y, 0, x, y, R0); g.addColorStop(0, gold ? 'rgba(255,240,200,.45)' : 'rgba(255,120,80,.6)'); g.addColorStop(1, gold ? 'rgba(255,200,120,0)' : 'rgba(255,30,0,0)');
    ctx.fillStyle = g; ctx.fillRect(x - R0, y - R0, R0 * 2, R0 * 2);
    ctx.fillStyle = gold ? 'rgba(255,255,245,.8)' : 'rgba(255,230,200,.9)'; ctx.fillRect(x - 22, y - 1, 44, 2);
  }
  const st = ctx.createLinearGradient(1250, 0, 1560, 0); // 光痕：从眼缝往后拖出去
  st.addColorStop(0, 'rgba(255,255,255,0)'); st.addColorStop(.3, gold ? 'rgba(255,246,220,.75)' : 'rgba(255,140,100,.75)'); st.addColorStop(1, 'rgba(255,200,120,0)');
  ctx.fillStyle = st; ctx.beginPath(); ctx.moveTo(1262, 345); ctx.lineTo(1560, 342 + Math.sin(t * 2) * 3); ctx.lineTo(1560, 346 + Math.sin(t * 2) * 3); ctx.lineTo(1262, 351); ctx.fill();
  ctx.restore();
}
function eyeK(t) { return lin(t, .4, 1.2) * (.65 + .2 * Math.sin(t * 3.1) + .15 * beatHit(t)) * (1 + .04 * beatCount(t)); }
function drawPlume(t, gold) {
  for (let i = 8; i >= 0; i--) {
    const f = feather(t, i, gold);
    if (gold) { bodyFill(f.body); glowStroke(f.body, 1.6, 8); ctx.save(); ctx.clip(f.body); glowStroke(f.barbs, .7, 3, '#d9a54c'); ctx.restore(); glowStroke(f.quill, 1.2, 5, '#fff0c4'); }
    else { ctx.fillStyle = '#1a0504'; ctx.fill(f.body); redStroke(f.body, 1.3, 6); ctx.save(); ctx.clip(f.body); ctx.strokeStyle = 'rgba(255,100,60,.35)'; ctx.lineWidth = .8; ctx.stroke(f.barbs); ctx.restore(); }
  }
}
function drawHelmRed(t) {
  drawPlume(t, false);
  ctx.fillStyle = '#1a0504'; ctx.fill(PLUME_HOLDER); redStroke(PLUME_HOLDER, 1.4, 6);
  darkMetal(COMB, 1370, 220, 80); redStroke(COMB, 1.6, 8);
  darkMetal(HELM, 1330, 330, 260); redStroke(HELM, 2.6, 16);
  darkMetal(RONDEL, 1484, 470, 30); redStroke(RONDEL, 1.6, 8); ctx.strokeStyle = 'rgba(255,110,70,.6)'; ctx.lineWidth = 1.1; ctx.stroke(RONDEL_IN);
  ctx.fillStyle = '#050101'; ctx.fill(SLIT);
  redStroke(HELM_LINES, 1.5, 6);
  ctx.fillStyle = `rgba(255,70,40,${.35 + .4 * beatHit(t)})`; ctx.fill(HELM_HOLES);
  ctx.strokeStyle = 'rgba(255,120,90,.7)'; ctx.lineWidth = 1.2; ctx.stroke(HELM_HOLES);
  for (const [x, y, r] of HELM_RIVETS) { ctx.fillStyle = '#2a0a06'; ctx.fill(circ(x, y, r)); ctx.strokeStyle = 'rgba(255,120,90,.8)'; ctx.lineWidth = 1.2; ctx.stroke(circ(x, y, r)); }
}
function drawArmRed(t, k) {
  const R = rig(t);
  ctx.save(); ctx.globalAlpha *= k;
  inFrame(R.mU, () => { darkMetal(REREBRACE, 80, 0, 160); redStroke(REREBRACE, 2, 10); ctx.strokeStyle = 'rgba(255,110,70,.5)'; ctx.lineWidth = 1.2; ctx.stroke(RERE_LINES); });
  paulDraw(R, false, t);
  inFrame(R.mF, () => {
    darkMetal(VAMB, 80, 0, 160); redStroke(VAMB, 2, 10); ctx.strokeStyle = 'rgba(255,110,70,.5)'; ctx.lineWidth = 1.2; ctx.stroke(VAMB_LINES);
    darkMetal(CUFF, LF, 0, 60); redStroke(CUFF, 1.8, 8); ctx.stroke(CUFF_LINES);
    darkMetal(OPEN_PALM, LF + 20, 0, 80); redStroke(OPEN_PALM, 1.8, 8);
    ctx.strokeStyle = 'rgba(255,110,70,.55)'; ctx.lineWidth = 1.1; ctx.stroke(PALM_LINES);
    for (const f of FINGER_SEGS) { ctx.fillStyle = '#240806'; ctx.fill(f); redStroke(f, 1.4, 6); }
  });
  couter(R, false);
  ctx.restore();
}
function couter(R, gold) { // 护肘：杯形肘盘 + 背后一片扇形翼（坐标 x 朝肘尖外侧）
  const out = [R.du[0] - R.df[0], R.du[1] - R.df[1]], ol = Math.hypot(...out) || 1, m = frame(R.E, [out[0] / ol, out[1] / ol]);
  inFrame(m, () => {
    if (gold) { armorFill(COUTER_WING); sheen(COUTER_WING, [[30, -10, 20, 26, .16]]); glowStroke(COUTER_WING, 1.8, 8); glowStroke(COUTER_FLUTE, .9, 4); armorFill(COUTER_CUP); sheen(COUTER_CUP, [[14, -12, 18, 14, .3]]); glowStroke(COUTER_CUP, 2.2, 10); glowStroke(COUTER_RIDGE, 1.1, 5); accentFill(circ(16, 0, 2.6), 5); }
    else { darkMetal(COUTER_WING, 20, 0, 60); redStroke(COUTER_WING, 1.4, 6); darkMetal(COUTER_CUP, 10, 0, 40); redStroke(COUTER_CUP, 1.8, 8); ctx.strokeStyle = 'rgba(255,110,70,.55)'; ctx.lineWidth = 1.1; ctx.stroke(COUTER_RIDGE); }
  });
}
const COUTER_WING = P([[-8, -44], [24, -40], [46, -20], [52, 0], [46, 20], [24, 40], [-8, 44], [6, 0]]);
const COUTER_FLUTE = (() => { const p = new Path2D(); for (const a of [-1.1, -.55, 0, .55, 1.1]) { p.moveTo(4, 0); p.lineTo(4 + Math.cos(a) * 42, Math.sin(a) * 38); } return p; })();
const COUTER_CUP = P([[-24, -30], [6, -33], [26, -22], [33, 0], [26, 22], [6, 33], [-24, 30]]);
const COUTER_RIDGE = (() => { const p = new Path2D(); p.moveTo(-6, -30); p.quadraticCurveTo(20, 0, -6, 30); p.moveTo(10, -24); p.quadraticCurveTo(30, 0, 10, 24); return p; })();
function emblemRed(t, k) {
  ctx.save(); ctx.globalAlpha *= k;
  ctx.fillStyle = '#1e0605'; ctx.fill(P_SHIELD); redStroke(P_SHIELD, 2, 10); ctx.strokeStyle = 'rgba(255,110,70,.45)'; ctx.lineWidth = 1; ctx.stroke(SHIELD_IN);
  ctx.fillStyle = '#2a0806'; ctx.fill(P_HEART); redStroke(P_HEART, 1.8, 8);
  const g = beatCount(t);
  ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.lineCap = 'round';
  for (const c of CRACKS_E) { // 每次心跳裂纹往外爬一截
    const reach = clamp((g - c.order * .25) / 3.5), n = Math.floor(c.pts.length * reach); if (n < 2) continue;
    const p = new Path2D(); p.moveTo(...c.pts[0]); for (let i = 1; i < n; i++) p.lineTo(...c.pts[i]);
    ctx.strokeStyle = `rgba(255,70,30,${.55 + .4 * beatHit(t)})`; ctx.lineWidth = 3.5; ctx.shadowColor = '#ff2000'; ctx.shadowBlur = 14; ctx.stroke(p);
    ctx.strokeStyle = 'rgba(255,230,200,.85)'; ctx.lineWidth = 1; ctx.shadowBlur = 0; ctx.stroke(p);
  }
  ctx.restore(); ctx.restore();
}
FIG.early = t => { // 黑暗里先亮起眼缝的红光，再看见吊下来的钱袋
  if (t >= T.figure + .6) return;
  const a = 1 - lin(t, T.figure, T.figure + .6);
  withHead(t, () => {
    ctx.save(); ctx.globalAlpha = .5 * lin(t, 1.6, 3.6) * a; ctx.strokeStyle = 'rgba(255,90,50,.7)'; ctx.lineWidth = 1.4; ctx.shadowColor = '#ff3010'; ctx.shadowBlur = 10; ctx.stroke(HELM); ctx.stroke(HELM_LINES); ctx.restore();
    eyeGlow(t, eyeK(t) * a, false);
  });
};
FIG.red = (t, k) => {
  const cp = capePath(t, false);
  ctx.save(); ctx.globalAlpha = k; fillWithText(cp.path, t, 1, .7); redStroke(cp.path, 1.8, 10); ctx.strokeStyle = 'rgba(255,110,70,.35)'; ctx.lineWidth = 1.2; ctx.stroke(cp.folds); ctx.restore();
  fillWithText(P_BODY, t, lin(t, T.figure + .4, T.figure + 3.2), k * .95);
  ctx.save(); ctx.globalAlpha = k; ctx.setLineDash([3400 * eio(k), 6000]); redStroke(P_BODY, 2.6, 16); ctx.restore();
  ctx.save(); ctx.globalAlpha = k * .6; ctx.save(); ctx.clip(P_BODY); ctx.strokeStyle = 'rgba(255,120,80,.6)'; ctx.lineWidth = 1.4; ctx.stroke(BODY_LINES); ctx.restore(); ctx.restore();
  emblemRed(t, k);
  ctx.save(); ctx.globalAlpha = k; darkMetal(FAR_PAUL, 1640, 620, 90); redStroke(FAR_PAUL, 2, 10); ctx.strokeStyle = 'rgba(255,110,70,.5)'; ctx.lineWidth = 1.1; ctx.stroke(FAR_PAUL_LINES); ctx.restore();
  withHead(t, () => { ctx.save(); ctx.globalAlpha = k; drawHelmRed(t); ctx.restore(); });
  drawArmRed(t, k);
};
FIG.redTop = (t, k) => {
  drawPurse(t, Math.max(lin(t, 1.2, 2.4) * .6, k));
  coinReadout(t, lin(t, T.figure + 1, T.figure + 1.6));
  withHead(t, () => eyeGlow(t, eyeK(t), false));
  if (t >= PURSE_CUT.tc && t < T.flash + .2) { // 斩断处的火花
    const age = t - PURSE_CUT.tc, r = rng(31);
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    for (let i = 0; i < 30; i++) { const an = (r() - .5) * 6.2, v = 200 + r() * 600, x = PURSE_CUT.pt[0] + Math.cos(an) * v * age, y = PURSE_CUT.pt[1] + Math.sin(an) * v * age + 400 * age * age;
      ctx.strokeStyle = `rgba(255,${200 + r() * 55},140,${1 - age / .5})`; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x - Math.cos(an) * 14, y - Math.sin(an) * 14); ctx.stroke(); }
    ctx.restore();
  }
};

// ================= 第二幕 =================
let LIGHT = [1165, 300], LIGHT_K = 0, FIG_BASE = new DOMMatrix();
function lightLocal() { return ctx.getTransform().inverse().multiply(FIG_BASE).transformPoint(new DOMPoint(LIGHT[0], LIGHT[1])); }
function rimLight(path, r = 760, a = .3) {
  if (LIGHT_K <= 0) return;
  const L = lightLocal();
  ctx.save(); ctx.clip(path);
  const g = ctx.createRadialGradient(L.x, L.y, 0, L.x, L.y, r); g.addColorStop(0, `rgba(255,232,175,${a * LIGHT_K})`); g.addColorStop(.45, `rgba(200,150,70,${a * .4 * LIGHT_K})`); g.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = g; ctx.fillRect(-4000, -4000, 8000, 8000); ctx.restore();
}
function bodyFill(path) {
  const g = ctx.createLinearGradient(0, 200, 0, 1080); g.addColorStop(0, '#2a2010'); g.addColorStop(.5, '#161008'); g.addColorStop(1, '#090604');
  ctx.fillStyle = g; ctx.fill(path); rimLight(path);
}
function armorFill(path) { ctx.fillStyle = '#1e160b'; ctx.fill(path); rimLight(path, 560, .44); }
function sheen(path, spots) { // 金属高光：几块柔和的亮斑
  ctx.save(); ctx.clip(path); ctx.globalCompositeOperation = 'lighter';
  for (const [x, y, rx, ry, a] of spots) { ctx.save(); ctx.translate(x, y); ctx.scale(rx, ry); const g = ctx.createRadialGradient(0, 0, 0, 0, 0, 1); g.addColorStop(0, `rgba(255,222,160,${a})`); g.addColorStop(1, 'rgba(255,200,120,0)'); ctx.fillStyle = g; ctx.fillRect(-1, -1, 2, 2); ctx.restore(); }
  ctx.restore();
}
function gleam(path, t, x0, x1) { // 每次定格：一道斜向的亮光扫过盔甲
  for (const h of HITS) { const k = lin(t, h.t, h.t + .55); if (k <= 0 || k >= 1) continue;
    const x = mix(x0, x1, eio(k)); ctx.save(); ctx.clip(path); ctx.globalCompositeOperation = 'lighter';
    const g = ctx.createLinearGradient(x - 60, 0, x + 60, 0); g.addColorStop(0, 'rgba(255,240,200,0)'); g.addColorStop(.5, `rgba(255,248,225,${.5 * Math.sin(Math.PI * k)})`); g.addColorStop(1, 'rgba(255,240,200,0)');
    ctx.setTransform(ctx.getTransform().multiply(new DOMMatrix([1, 0, -.5, 1, 0, 0]))); ctx.fillStyle = g; ctx.fillRect(x - 200, -200, 400, 1600); ctx.restore(); }
}
function rivets(list, gold) { for (const [x, y, r = 3.5] of list) { const p = circ(x, y, r); if (gold) { armorFill(p); glowStroke(p, 1, 4); } } }
function drawHelmGold(t) {
  drawPlume(t, true);
  armorFill(PLUME_HOLDER); glowStroke(PLUME_HOLDER, 1.4, 6);
  armorFill(COMB); sheen(COMB, [[1366, 214, 50, 8, .3]]); glowStroke(COMB, 1.8, 10); glowStroke(COMB_LINE, .9, 4);
  armorFill(HELM); sheen(HELM, [[1350, 262, 80, 28, .34], [1252, 392, 22, 44, .24], [1450, 330, 26, 70, .14], [1310, 470, 44, 20, .14]]);
  gleam(HELM, t, 1200, 1520);
  glowStroke(HELM, 2.8, 16);
  ctx.fillStyle = '#050402'; ctx.fill(SLIT);
  glowStroke(HELM_LINES, 1.4, 6);
  ctx.fillStyle = '#060402'; ctx.fill(HELM_HOLES); glowStroke(HELM_HOLES, .9, 4);
  for (const [x, y, r] of HELM_RIVETS) { const p = circ(x, y, r); armorFill(p); glowStroke(p, 1.2, 5); }
  accentFill(circ(1398, 376, 3.5), 6);
  armorFill(RONDEL); sheen(RONDEL, [[1478, 462, 10, 8, .3]]); glowStroke(RONDEL, 2, 10); glowStroke(RONDEL_IN, 1.1, 5); accentFill(RONDEL_SPIKE, 8);
}
function drawBodyGold(t) {
  const cp = capePath(t, true);
  { // 披风：深红底 + 金边，褶子上一层柔光
    const g = ctx.createLinearGradient(1600, 580, 1900, 1100); g.addColorStop(0, '#5a1812'); g.addColorStop(.5, '#34100b'); g.addColorStop(1, '#160504');
    ctx.fillStyle = g; ctx.fill(cp.path); rimLight(cp.path, 700, .22);
    ctx.save(); ctx.clip(cp.path); ctx.globalCompositeOperation = 'lighter'; ctx.strokeStyle = 'rgba(255,120,80,.12)'; ctx.lineWidth = 22; ctx.filter = 'none'; ctx.stroke(cp.folds); ctx.restore();
    glowStroke(cp.path, 2.4, 14); glowStroke(cp.folds, 1, 5, '#e0a050');
  }
  bodyFill(P_BODY); sheen(P_BODY, [[1290, 700, 90, 70, .24], [1232, 740, 26, 90, .2], [1440, 940, 120, 20, .1], [1440, 640, 110, 34, .14], [1560, 760, 50, 90, .1]]);
  gleam(P_BODY, t, 1150, 1700);
  glowStroke(P_BODY, 3, 20);
  ctx.save(); ctx.clip(P_BODY); glowStroke(BODY_LINES, 1.4, 6); glowStroke(BODY_ETCH, .7, 3, '#c9944a'); ctx.restore();
  armorFill(FAR_PAUL); sheen(FAR_PAUL, [[1640, 590, 50, 14, .26]]); glowStroke(FAR_PAUL, 2.2, 12); glowStroke(FAR_PAUL_LINES, 1.1, 5);
  { // 胸甲中脊上一道锐利的高光
    ctx.save(); ctx.clip(P_BODY); ctx.globalCompositeOperation = 'lighter';
    const g = ctx.createLinearGradient(0, 600, 0, 880); g.addColorStop(0, 'rgba(255,240,200,0)'); g.addColorStop(.35, 'rgba(255,240,200,.5)'); g.addColorStop(1, 'rgba(255,240,200,0)');
    ctx.strokeStyle = g; ctx.lineWidth = 5; ctx.shadowColor = '#ffd27a'; ctx.shadowBlur = 16; ctx.beginPath(); ctx.moveTo(1342, 612); ctx.bezierCurveTo(1312, 700, 1310, 790, 1332, 866); ctx.stroke(); ctx.restore();
  }
  for (const [x, y] of BODY_RIVETS) { const p = circ(x, y, 3.5); armorFill(p); glowStroke(p, 1, 4); }
  // 纹章：心亮起来，之后平稳地跳
  armorFill(P_SHIELD); glowStroke(P_SHIELD, 2.2, 12); glowStroke(SHIELD_IN, 1, 4);
  const lit = lin(t, OATH, OATH + .4), beat = heartGlow(t);
  if (lit > 0) {
    ctx.save(); ctx.globalAlpha *= lit; ctx.translate(EMB[0], EMB[1] - 4); ctx.scale(1 + .06 * beat, 1 + .06 * beat); ctx.translate(-EMB[0], -EMB[1] + 4);
    const g = ctx.createRadialGradient(EMB[0], EMB[1] - 8, 0, EMB[0], EMB[1] - 4, 40); g.addColorStop(0, '#fffdf2'); g.addColorStop(.5, '#ffd884'); g.addColorStop(1, '#d08a2a');
    ctx.fillStyle = g; ctx.shadowColor = '#ffb040'; ctx.shadowBlur = 24 + 20 * beat; ctx.fill(P_HEART); ctx.restore();
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; const big = ctx.createRadialGradient(EMB[0], EMB[1], 0, EMB[0], EMB[1], 220); big.addColorStop(0, `rgba(255,220,150,${(.25 + .25 * beat) * lit})`); big.addColorStop(1, 'rgba(255,200,120,0)'); ctx.fillStyle = big; ctx.fillRect(EMB[0] - 220, EMB[1] - 220, 440, 440);
    for (let i = 0; i < 2; i++) { const ph = ((t - OATH) / 1.05 + i * .5) % 1; if (t < OATH) break; ctx.strokeStyle = `rgba(255,230,180,${.4 * (1 - ph) * lit})`; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(EMB[0], EMB[1] - 4, 30 + ph * 120, 0, 7); ctx.stroke(); }
    ctx.restore();
  } else { armorFill(P_HEART); glowStroke(P_HEART, 1.6, 8); }
}
const HB_PERIOD = 1.05;
function heartGlow(t) { if (t < OATH) return 0; const ph = ((t - OATH) % HB_PERIOD) / HB_PERIOD; return Math.exp(-ph * 14) + .6 * Math.exp(-Math.max(0, ph - .18) * 14) * (ph > .18); }
function drawArmGold(t, R) {
  const vis = bladeVis(t), sa = swordA(t);
  inFrame(R.mU, () => { armorFill(REREBRACE); sheen(REREBRACE, [[80, -14, 70, 9, .22]]); glowStroke(REREBRACE, 2.2, 10); glowStroke(RERE_LINES, 1.1, 5); });
  paulDraw(R, true, t);
  inFrame(R.mF, () => { armorFill(VAMB); sheen(VAMB, [[70, -12, 60, 8, .22]]); glowStroke(VAMB, 2.2, 10); glowStroke(VAMB_LINES, 1.1, 5); armorFill(CUFF); glowStroke(CUFF, 2, 9); glowStroke(CUFF_LINES, 1.1, 5); });
  couter(R, true);
  if (t < SUMMON0 - .15) { // 剑出现之前：还是那只张开的手，在闪白里握紧
    inFrame(R.mF, () => { armorFill(OPEN_PALM); glowStroke(OPEN_PALM, 1.6, 8); glowStroke(PALM_LINES, 1, 4); for (const f of FINGER_SEGS) { armorFill(f); glowStroke(f, 1.3, 6); } });
    return;
  }
  inFrame(R.mS, () => {
    ctx.save(); ctx.globalAlpha *= sa;
    armorFill(POMMEL); glowStroke(POMMEL, 2, 10); glowStroke(POMMEL_IN, 1.2, 5); accentFill(POMMEL_GEM, 10);
    armorFill(GRIP); glowStroke(GRIP, 1.6, 6); glowStroke(GRIP_WRAP, 1, 3, '#d9a54c');
    ctx.restore();
    drawBlade(t, vis);
    ctx.save(); ctx.globalAlpha *= sa;
    armorFill(GUARD); sheen(GUARD, [[34, 0, 10, 80, .25]]); glowStroke(GUARD, 2.2, 12); glowStroke(GUARD_KNOBS, 1.6, 8); armorFill(LANGET); glowStroke(LANGET, 1.4, 6); accentFill(GUARD_GEM, 14);
    armorFill(FIST); sheen(FIST, [[0, 18, 26, 10, .2]]); glowStroke(FIST, 2, 10); glowStroke(FIST_LINES, 1.1, 5); armorFill(THUMB_P); glowStroke(THUMB_P, 1.6, 7); glowStroke(THUMB_L, 1, 4);
    ctx.restore();
  });
}
function drawBlade(t, vis) { // 剑身：从护手往剑尖长出来；之后剑芯发白光，剑脊铭文逐字亮起，定格时光从护手一路跑上剑尖
  if (vis <= 0) return;
  const len = 40 + (BL - 40) * vis;
  ctx.save(); ctx.beginPath(); ctx.rect(0, -40, len, 80); ctx.clip();
  ctx.save(); ctx.globalCompositeOperation = 'lighter'; // 外辉光
  const pul = .8 + .2 * Math.sin(t * 3.3);
  ctx.strokeStyle = `rgba(255,200,110,${.35 * pul})`; ctx.lineWidth = 26; ctx.shadowColor = '#ffb040'; ctx.shadowBlur = 40; ctx.stroke(BLADE);
  ctx.restore();
  const g = ctx.createLinearGradient(0, -21, 0, 21); g.addColorStop(0, '#6a5228'); g.addColorStop(.42, '#fff6dc'); g.addColorStop(.5, '#ffffff'); g.addColorStop(.58, '#fff6dc'); g.addColorStop(1, '#5a4420');
  ctx.fillStyle = g; ctx.fill(BLADE);
  ctx.fillStyle = 'rgba(70,50,20,.85)'; ctx.fill(FULLER);
  glowStroke(BLADE, 2, 12); ctx.strokeStyle = 'rgba(120,90,40,.7)'; ctx.lineWidth = 1; ctx.stroke(BLADE_LINES);
  // 铭文
  ctx.save(); ctx.font = '15px CinzelBold'; ctx.textBaseline = 'middle'; ctx.textAlign = 'center';
  for (let i = 0; i < RUNES.length; i++) {
    const k = lin(t, OATH + .15 + i * .05, OATH + .35 + i * .05); const x = 90 + i * 20;
    ctx.fillStyle = k > 0 ? `rgba(255,${200 + 55 * k},${120 + 120 * k},${.35 + .65 * k})` : 'rgba(200,160,90,.35)';
    ctx.shadowColor = '#ffcf70'; ctx.shadowBlur = 12 * k; ctx.fillText(RUNES[i], x, 1);
  }
  ctx.restore();
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  for (const h of [{ t: SUMMON0 - .2 }, ...HITS]) { // 光跑上剑身
    const k = lin(t, h.t, h.t + .5); if (k <= 0 || k >= 1) continue;
    const x = mix(30, BL + 60, eout(k)), lg = ctx.createLinearGradient(x - 120, 0, x + 30, 0); lg.addColorStop(0, 'rgba(255,240,200,0)'); lg.addColorStop(.8, `rgba(255,252,240,${.95 * (1 - k * .5)})`); lg.addColorStop(1, 'rgba(255,240,200,0)');
    ctx.fillStyle = lg; ctx.fillRect(x - 120, -30, 150, 60);
  }
  for (let i = 0; i < 26; i++) { // 绕着剑身螺旋上升的光点
    const u = ((i / 26) + t * .32) % 1, x = 50 + u * (BL - 60), y = 28 * Math.sin(t * 5 + i * 2.1) * (1 - u * .5), a = Math.sin(Math.PI * u) * .9;
    ctx.fillStyle = `rgba(255,236,190,${a})`; ctx.beginPath(); ctx.arc(x, y, 1.8 + (i % 3), 0, 7); ctx.fill();
  }
  ctx.restore();
  ctx.restore();
  if (vis < 1) { // 正在长出来的剑尖：一团亮光
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; const g2 = ctx.createRadialGradient(len, 0, 0, len, 0, 90); g2.addColorStop(0, 'rgba(255,255,245,1)'); g2.addColorStop(1, 'rgba(255,210,130,0)'); ctx.fillStyle = g2; ctx.fillRect(len - 90, -90, 180, 180); ctx.restore();
  }
}
function swingTrail(t) { // 挥剑的光弧：剑身扫过的扇面
  const segs = [];
  for (let k = 0; k <= 10; k++) { const R = rig(t - k * .016); if (bladeVis(t - k * .016) <= 0) break; segs.push([R.guard, [R.H[0] + R.d[0] * (40 + (BL - 40) * bladeVis(t - k * .016)), R.H[1] + R.d[1] * (40 + (BL - 40) * bladeVis(t - k * .016))]]); }
  if (segs.length < 2) return;
  const mv = Math.hypot(segs[0][1][0] - segs[1][1][0], segs[0][1][1] - segs[1][1][1]); if (mv < 4) return;
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  for (let k = 1; k < segs.length; k++) {
    const [g0, t0] = segs[k - 1], [g1, t1] = segs[k], a = .22 * (1 - k / segs.length) * Math.min(1, mv / 30);
    const gr = ctx.createLinearGradient(...g0, ...t0); gr.addColorStop(0, `rgba(255,210,130,${a * .3})`); gr.addColorStop(1, `rgba(255,245,215,${a})`);
    ctx.fillStyle = gr; ctx.beginPath(); ctx.moveTo(...g0); ctx.lineTo(...t0); ctx.lineTo(...t1); ctx.lineTo(...g1); ctx.closePath(); ctx.fill();
  }
  ctx.strokeStyle = `rgba(255,250,235,${Math.min(.8, mv / 40)})`; ctx.lineWidth = 3; ctx.shadowColor = '#ffcf70'; ctx.shadowBlur = 18; ctx.beginPath(); ctx.moveTo(...segs[0][1]); for (const s of segs) ctx.lineTo(...s[1]); ctx.stroke();
  ctx.restore();
}
function bolt(r, x0, y0, x1, y1, depth) { const p = [[x0, y0]]; const n = 9; for (let i = 1; i < n; i++) { const u = i / n; p.push([mix(x0, x1, u) + (r() - .5) * 60 * depth, mix(y0, y1, u) + (r() - .5) * 60 * depth]); } p.push([x1, y1]); return p; }
function hitFX(t) { // 每次定格的特效
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  HITS.forEach((h, j) => {
    const age = t - h.t; if (age < 0 || age > 1.6) return;
    const R = rig(h.t + .05);
    if (h.type === 'salute') { // 护手处炸开一圈光、火花
      const [x, y] = R.guard, fl = 1 - lin(age, 0, .6);
      if (fl > 0) { ctx.strokeStyle = `rgba(255,240,200,${fl})`; ctx.lineWidth = 2 + 7 * fl; ctx.shadowColor = '#ffd27a'; ctx.shadowBlur = 24; ctx.beginPath(); ctx.arc(x, y, 30 + (1 - fl) * 320, 0, 7); ctx.stroke(); ctx.shadowBlur = 0; }
      const r = rng(700 + j); for (let i = 0; i < 40; i++) { const an = r() * 6.28, v = 150 + r() * 500, life = .5 + r() * .8; if (age > life) continue; ctx.fillStyle = `rgba(255,232,170,${1 - age / life})`; ctx.fillRect(x + Math.cos(an) * v * age, y + Math.sin(an) * v * age + 160 * age * age, 2.6, 2.6); }
    } else if (h.type === 'over') { // 举剑引雷：剑身上爬满电弧，再往四周劈出几道闪电
      if (age > .8) return;
      const r = rng(900 + j * 31 + Math.floor(age * 20)), fl = (1 - age / .8) * (.55 + .45 * r());
      const vis0 = clamp(-R.H[1] / (R.d[1] * BL) || 1), uMax = R.d[1] < 0 ? Math.min(1, (R.H[1] - 10) / (-R.d[1] * BL)) : 1; // 剑身在画面里的那一段
      const strokeBolt = (pts, w) => { const p = new Path2D(); p.moveTo(...pts[0]); for (const q of pts) p.lineTo(...q);
        ctx.strokeStyle = `rgba(255,226,160,${.4 * fl})`; ctx.lineWidth = w * 3.5; ctx.shadowColor = '#ffcf70'; ctx.shadowBlur = 26; ctx.stroke(p);
        ctx.strokeStyle = `rgba(255,255,250,${fl})`; ctx.lineWidth = w; ctx.shadowBlur = 0; ctx.stroke(p); return pts; };
      for (let b = 0; b < 3; b++) { const u0 = .08 + r() * .2, u1 = Math.min(uMax, u0 + .3 + r() * .3); // 沿着剑身爬的电弧
        const a = [R.H[0] + R.d[0] * BL * u0, R.H[1] + R.d[1] * BL * u0], c = [R.H[0] + R.d[0] * BL * u1, R.H[1] + R.d[1] * BL * u1]; strokeBolt(bolt(r, a[0], a[1], c[0], c[1], .45), 1.3); }
      for (let b = 0; b < 4; b++) { // 往外劈的闪电（都落在画面里）
        const u = Math.min(uMax, .25 + r() * .5), sx = R.H[0] + R.d[0] * BL * u, sy = R.H[1] + R.d[1] * BL * u;
        const an = -Math.PI / 2 + (b % 2 ? 1 : -1) * (.6 + r() * .9), L = 260 + r() * 360, ex = sx + Math.cos(an) * L, ey = Math.max(20, sy + Math.sin(an) * L);
        const pts = strokeBolt(bolt(r, sx, sy, ex, ey, 1.2), 2); const m = pts[4]; strokeBolt(bolt(r, m[0], m[1], m[0] + (r() - .5) * 300, m[1] - 60 - r() * 160, .7), 1);
      }
      const ex = R.H[0] + R.d[0] * 300, ey = R.H[1] + R.d[1] * 300, g = ctx.createRadialGradient(ex, ey, 0, ex, ey, 700); g.addColorStop(0, `rgba(255,245,220,${.45 * (1 - age / .8)})`); g.addColorStop(1, 'rgba(255,220,150,0)');
      ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    } else if (h.type === 'vigil') { // 剑尖顿地：地面炸开一圈光，火花往上喷
      const x = R.H[0] + R.d[0] * 210, y = 1080, fl = 1 - lin(age, 0, .9);
      for (const [d, c] of [[0, .9], [.12, .5]]) { const k = lin(age, d, d + 1.1); if (k <= 0 || k >= 1) continue; ctx.strokeStyle = `rgba(255,236,190,${c * (1 - k)})`; ctx.lineWidth = 2 + 6 * (1 - k); ctx.shadowColor = '#ffcf70'; ctx.shadowBlur = 20; ctx.beginPath(); ctx.ellipse(x, y, 40 + eout(k) * 900, 12 + eout(k) * 120, 0, 0, 7); ctx.stroke(); }
      ctx.shadowBlur = 0;
      if (fl > 0) { ctx.save(); ctx.translate(x, 1080); ctx.scale(1, .32); const g = ctx.createRadialGradient(0, 0, 0, 0, 0, 900 * (1.2 - fl * .6)); g.addColorStop(0, `rgba(255,240,200,${.7 * fl})`); g.addColorStop(.4, `rgba(255,200,120,${.25 * fl})`); g.addColorStop(1, 'rgba(255,200,120,0)'); ctx.fillStyle = g; ctx.fillRect(-1200, -1200, 2400, 1200); ctx.restore(); }
      const r = rng(800 + j); for (let i = 0; i < 70; i++) { const an = -Math.PI / 2 + (r() - .5) * 2.2, v = 300 + r() * 900, life = .6 + r() * .9; if (age > life) continue;
        const px = x + Math.cos(an) * v * age, py = y + Math.sin(an) * v * age + 700 * age * age; ctx.strokeStyle = `rgba(255,${200 + r() * 55},140,${1 - age / life})`; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(px - Math.cos(an) * 12, py - Math.sin(an) * 12 + 6); ctx.stroke(); }
    }
  });
  ctx.restore();
}
// ---------- 钱袋炸开：银币烧成金币四散翻飞 ----------
const COINS = (() => { const r = rng(4321), p = purse(T.flash), out = [];
  for (let i = 0; i < 46; i++) { const lx = (r() - .5) * 90, ly = 30 + r() * 80, q = new DOMMatrix(p.m).transformPoint(new DOMPoint(lx, ly));
    const an = Math.atan2(q.y - (p.knot[1] + 70), q.x - p.knot[0]) + (r() - .5) * 1.6, sp = 300 + r() * 900;
    out.push({ x: q.x, y: q.y + 60, vx: Math.cos(an) * sp - 120, vy: Math.sin(an) * sp - 300 - r() * 300, spin: r() * 6, vs: 8 + r() * 14, r: 10 + r() * 8, life: 1.6 + r() * 1.6 }); }
  return out; })();
function coinBurst(t) {
  const age = t - T.flash; if (age < 0 || age > 3.4) return;
  for (const c of COINS) { if (age > c.life) continue; drawCoin(c.x + c.vx * age * (1 - age * .15), c.y + c.vy * age + 600 * age * age, c.r, c.spin + c.vs * age, 'gold', 1 - lin(age, c.life - .5, c.life)); }
  const p = purse(T.flash); // 钱袋的两片残布翻着落下去
  for (const sg of [-1, 1]) { ctx.save(); ctx.globalAlpha *= 1 - lin(age, .6, 1.4); ctx.translate(p.knot[0] + sg * 120 * age, p.knot[1] + 60 - 200 * age + 800 * age * age); ctx.rotate(sg * age * 4); ctx.scale(.8, .8);
    ctx.save(); ctx.beginPath(); ctx.rect(sg < 0 ? -80 : 0, -40, 80, 200); ctx.clip(); armorFill(SACK); glowStroke(SACK, 2, 10); ctx.restore(); ctx.restore(); }
}
FIG.gold = (t, k) => {
  FIG_BASE = ctx.getTransform();
  const R = rig(t), vis = bladeVis(t), hitB = HITS.reduce((m, h) => { const d = t - h.t; return d >= 0 && d < .6 ? Math.max(m, 1 - d / .6) : m; }, 0);
  LIGHT = [R.H[0] + R.d[0] * 250, R.H[1] + R.d[1] * 250]; LIGHT_K = .25 + .75 * vis * (.85 + .15 * Math.sin(t * 3.3)) + .3 * hitB;
  ctx.save(); ctx.globalAlpha *= k;
  drawBodyGold(t);
  withHead(t, () => { drawHelmGold(t); eyeGlow(t, (.6 + .3 * hitB) * lin(t, T.flash, T.flash + .8), true); });
  drawArmGold(t, R);
  ctx.restore();
  swingTrail(t);
  hitFX(t);
};
FIG.burst = t => coinBurst(t);
FIG.flare = t => {
  const R = rig(t), vis = bladeVis(t);
  if (vis > 0) flare(...R.guard, (.2 + .08 * Math.sin(t * 2.7)) * vis, 420);
  if (vis > 0 && vis < 1) { const len = 40 + (BL - 40) * vis; flare(R.H[0] + R.d[0] * len, R.H[1] + R.d[1] * len, .8, 700); }
  for (const h of HITS) { const a = Math.sin(Math.PI * lin(t, h.t, h.t + .7)); if (a <= 0) continue; const Q = rig(h.t + .05);
    const p = h.type === 'salute' ? Q.guard : h.type === 'over' ? [Q.H[0] + Q.d[0] * 420, Math.max(40, Q.H[1] + Q.d[1] * 420)] : [Q.H[0], 1040];
    flare(p[0], p[1], (h.t === OATH ? 1.1 : .7) * a, 1000); }
};
FIG.shake = t => HITS.reduce((s, h) => { const d = t - h.t; return d >= 0 && d < .5 ? s + (h.type === 'vigil' ? 16 : h.type === 'over' ? 11 : 7) * Math.exp(-d * 9) : s; }, 0);
// 人物专属音效时间点（render.js events 导出 → audio.py）
FIG.events = [
  ...COIN_T.map(t => ({ t: t + .35, kind: 'coin' })),
  ...BEATS.map(t => ({ t, kind: 'armorcrack' })),
  { t: PURSE_CUT.tc, kind: 'twang' },
  { t: T.flash, kind: 'coinburst' },
  { t: SUMMON0 - .2, kind: 'summon', dur: SUMMON1 - SUMMON0 + .2 },
  ...HITS.map(h => ({ t: h.t, kind: 'swing', pre: h.t - h.start })),
  ...HITS.map(h => ({ t: h.t, kind: h.type === 'salute' ? 'oath' : h.type === 'over' ? 'thunder' : 'plant', big: h.t === OATH })),
  { t: OATH, kind: 'heartcalm', period: HB_PERIOD, t1: S.duration },
];
