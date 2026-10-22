// 人物：瘫着刷手机的胖子 → 雕像般的肌肉男（自律）
// 第一幕：黑暗里先亮起他手里的手机，推送卡片一张张从手机里飞出来；人显形后，每次心跳肚子鼓一圈，肚皮上的体重读数往上跳。
// 转场：玻璃破碎，撞击点就是手机屏幕——手机屏先碎成蛛网，裂纹爬满全屏，整个画面连同那副身体一起炸碎（fx.js 的 glass*）。
// 第二幕：碎片慢动作漂开，胖子的金色轮廓一圈圈收紧、烧掉多余的部分，变成雕像般的肌肉男；
//        左边计数器从第 1 天跑到第 365 天、体重往下掉；他握紧举起的拳头，拳心亮起光，然后一个接一个地摆健美造型
//        （单臂二头 → 前展双二头 → 最多肌肉 → 背阔展 → 双拳举过头 → 前展双二头 → 单臂二头），光源一直在近侧拳头里。
// 接口（index.html 调用）：FIG.IMPACT / FIG.cardFrom / FIG.early / FIG.red / FIG.redTop / FIG.gold / FIG.burst / FIG.flare / FIG.events
const FIG = { cracks: false };                       // 通用红裂纹会和玻璃裂纹抢戏，这里关掉
const PHONE = [1150, 545], PH_ANG = -.5;            // 手机中心、倾角
FIG.IMPACT = PHONE; FIG.cardFrom = PHONE;           // 玻璃从手机屏碎起；推送卡片从手机里飞出来
FIG.cardAvoid = [[1180, 900, 430]];                   // 人显形后卡片再避开肚子（x, y, 半径）

// ================= 第一幕：胖子 =================
const BEATS = heartbeats.filter(h => h > 4.8);       // 每次心跳肚子鼓一圈
const CARD_T = S.cards.map(c => c[0]);
const KG0 = 86.4, KG_STEP = 3.3;
// 头 + 身体的外轮廓（和第二幕的肌肉男一一对应，变形时逐点插值）：头顶 → 脸 → 下巴 → 胸 → 肚子 → 底边 → 后背 → 后脑
const FAT0 = [[1372, 262], [1316, 276], [1282, 312], [1270, 350], [1264, 374], [1244, 400], [1258, 418], [1256, 431], [1264, 441], [1257, 451],
  [1270, 470], [1266, 500], [1286, 528], [1225, 575], [1150, 650], [1080, 760], [1040, 880], [1060, 1000], [1090, 1095],
  [1665, 1095], [1660, 900], [1625, 720], [1560, 585], [1475, 492], [1452, 400], [1430, 300]];
const GROW = { 11: [-1, 1.5], 12: [-1, 2], 13: [-2, 0], 14: [-4, 0], 15: [-9, 2], 16: [-11, 3], 17: [-9, 2], 18: [-5, 0], 20: [3, 0], 21: [3, 0], 22: [2, -1] };
function fatGrow(t) { let g = 0; for (const b of BEATS) g += eback(lin(t, b, b + .22)); return g; }
function fatPts(t) {
  const g = fatGrow(t), br = Math.sin(t * 1.9) * 2.5; // 呼吸
  return FAT0.map((p, i) => { const d = GROW[i]; return d ? [p[0] + d[0] * g + (i >= 14 && i <= 17 ? -br : 0), p[1] + d[1] * g] : p; });
}
const HP = [1365, 482];                              // 头的转轴
function headA(t) { // 低头看手机；每来一条推送，头往手机那边点一下
  let a = -.06 + .012 * Math.sin(t * 1.3);
  for (const c of CARD_T) { const d = t - c - .3; if (d >= 0) a -= .03 * Math.exp(-d * 6) * Math.sin(Math.min(d * 18, Math.PI)); }
  return a;
}
const P_FHEAD = catmull([...FAT0.slice(0, 11), [1274, 494], [1298, 520], [1346, 532], [1402, 508], [1442, 462], FAT0[24], FAT0[25]], true);
const FHAIR = (() => { // 睡塌了的乱发：外缘一圈软塌塌的小发绺，头顶翘起两撮呆毛，额前几绺耷拉下来
  const C = [1368, 352], R = [94, 92], a0 = -2.5, a1 = .45, n = 13, p = new Path2D(), r = rng(91);
  const pt = (a, d) => [C[0] + Math.cos(a) * (R[0] + d), C[1] + Math.sin(a) * (R[1] + d)];
  p.moveTo(...pt(a0, -4));
  for (let i = 1; i <= n; i++) {
    const am = mix(a0, a1, (i - .5) / n), ae = mix(a0, a1, i / n);
    if (i === 6 || i === 8) { p.quadraticCurveTo(...pt(am - .02, 26), ...pt(am + .12, 34 + r() * 6)); p.quadraticCurveTo(...pt(am + .04, 10), ...pt(ae, 2)); } // 呆毛
    else p.quadraticCurveTo(...pt(am, 9 + r() * 5), ...pt(ae, 1 + r() * 3));
  }
  p.quadraticCurveTo(1440, 392, 1424, 380); p.quadraticCurveTo(1410, 356, 1392, 352);  // 耳朵上方
  p.quadraticCurveTo(1356, 330, 1330, 326); p.lineTo(1318, 344); p.lineTo(1310, 324);  // 鬓角、额前一绺
  p.lineTo(1296, 340); p.lineTo(1294, 318); p.lineTo(1282, 330); p.closePath();
  return p;
})();
// 近侧手臂（举着手机）的外轮廓：腋下 → 上臂后侧 → 肘 → 前臂下沿 → 手 → 前臂上沿 → 肘窝 → 上臂前侧 → 肩
const FAT_ARM = [[1404, 700], [1400, 780], [1380, 850], [1340, 905], [1292, 930], [1250, 916], [1222, 872], [1192, 792], [1162, 714],
  [1140, 676], [1128, 640], [1132, 605], [1150, 585], [1176, 582], [1196, 598], [1206, 625], [1210, 650], [1214, 668],
  [1232, 720], [1255, 775], [1272, 808], [1290, 760], [1296, 700], [1302, 650], [1335, 610], [1384, 636]];
const P_FARM = catmull(FAT_ARM, true);
function skinGrad(x, y, r) { const g = ctx.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, '#6a1f14'); g.addColorStop(.6, '#2f0b07'); g.addColorStop(1, '#140404'); return g; }
function phoneLight(path, a, r = 340) { // 手机屏幕的青光打在身上
  ctx.save(); ctx.clip(path); ctx.globalCompositeOperation = 'lighter';
  const g = ctx.createRadialGradient(...PHONE, 0, ...PHONE, r); g.addColorStop(0, `rgba(120,220,255,${.42 * a})`); g.addColorStop(.5, `rgba(60,150,220,${.14 * a})`); g.addColorStop(1, 'rgba(40,120,200,0)');
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); ctx.restore();
}
const screenA = t => { let a = .78 + .06 * Math.sin(t * 11) * Math.sin(t * 3.7); for (const c of CARD_T) { const d = t - c; if (d >= 0 && d < .4) a += .6 * (1 - d / .4); } return a * lin(t, .25, .7); };
function drawFatHead(t, a) {
  const sa = screenA(t);
  ctx.save(); ctx.globalAlpha *= a;
  ctx.translate(...HP); ctx.rotate(headA(t)); ctx.translate(-HP[0], -HP[1]);
  ctx.fillStyle = skinGrad(1300, 360, 210); ctx.fill(P_FHEAD); phoneLight(P_FHEAD, sa);
  ctx.save(); ctx.clip(P_FHEAD); ctx.globalCompositeOperation = 'lighter'; // 鼓起来的腮帮子
  const ck = ctx.createRadialGradient(1318, 428, 0, 1318, 428, 62); ck.addColorStop(0, 'rgba(255,90,60,.32)'); ck.addColorStop(1, 'rgba(255,60,40,0)'); ctx.fillStyle = ck; ctx.fillRect(1250, 360, 140, 140);
  ctx.restore();
  redStroke(P_FHEAD, 2.6, 16);
  ctx.fillStyle = '#1c0504'; ctx.fill(FHAIR); redStroke(FHAIR, 1.8, 10);
  const hs = new Path2D(), r = rng(19); for (let i = 0; i < 9; i++) { const x = 1320 + i * 14, y = 290 + Math.abs(i - 4) * 6; hs.moveTo(x, y + 30); hs.quadraticCurveTo(x + 8 * (r() - .5), y + 10, x + 10 * (r() - .5), y - 6); }
  ctx.save(); ctx.clip(FHAIR); ctx.strokeStyle = 'rgba(255,110,70,.35)'; ctx.lineWidth = 1.2; ctx.stroke(hs); ctx.restore();
  const ear = new Path2D(); ear.ellipse(1408, 404, 13, 20, .15, 0, Math.PI * 2); ctx.fillStyle = '#2a0906'; ctx.fill(ear); redStroke(ear, 1.6, 6);
  const f = new Path2D(); // 五官：眯着的眼往下看手机、眼袋、圆鼻头、松垮的嘴、鼓出来的腮
  f.moveTo(1276, 364); f.quadraticCurveTo(1291, 356, 1306, 363);   // 上眼皮（耷拉）
  f.moveTo(1279, 373); f.quadraticCurveTo(1292, 377, 1304, 372);   // 下眼皮
  f.moveTo(1280, 384); f.quadraticCurveTo(1294, 392, 1308, 385);   // 眼袋
  f.moveTo(1272, 348); f.quadraticCurveTo(1290, 341, 1310, 346);   // 眉
  f.moveTo(1252, 410); f.quadraticCurveTo(1262, 414, 1264, 405);   // 鼻翼
  f.moveTo(1260, 440); f.quadraticCurveTo(1268, 447, 1278, 444);   // 嘴角
  f.moveTo(1266, 422); f.quadraticCurveTo(1280, 432, 1282, 448);          // 鼻唇沟（被腮帮子挤出来）
  f.moveTo(1272, 476); f.quadraticCurveTo(1316, 500, 1372, 484);          // 双下巴的褶
  f.moveTo(1316, 470); f.quadraticCurveTo(1360, 466, 1396, 440);          // 埋在肉里的下颌线
  redStroke(f, 1.8, 8);
  ctx.fillStyle = '#060101'; ctx.beginPath(); ctx.ellipse(1286, 371, 4, 3, 0, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = `rgba(170,240,255,${.9 * sa})`; ctx.fillRect(1284, 369, 2.5, 2.5);   // 瞳孔里映着手机
  ctx.restore();
}
function drawPhone(t, a) {
  const sa = screenA(t);
  ctx.save(); ctx.globalAlpha *= a; ctx.translate(...PHONE); ctx.rotate(PH_ANG);
  ctx.fillStyle = '#0b0b0e'; ctx.fill(rr(-40, -76, 80, 152, 13)); ctx.strokeStyle = 'rgba(170,220,255,.6)'; ctx.lineWidth = 1.5; ctx.stroke(rr(-40, -76, 80, 152, 13));
  const sg = ctx.createLinearGradient(0, -68, 0, 68); sg.addColorStop(0, `rgba(170,235,255,${.85 * sa})`); sg.addColorStop(1, `rgba(90,170,240,${.75 * sa})`);
  ctx.shadowColor = 'rgba(110,220,255,.95)'; ctx.shadowBlur = 40 * sa; ctx.fillStyle = sg; ctx.fill(rr(-35, -69, 70, 138, 9)); ctx.shadowBlur = 0;
  // 屏幕上的短视频界面：大图、点赞、评论条，往上刷
  ctx.save(); ctx.clip(rr(-35, -69, 70, 138, 9)); const sc = (t * 34) % 46;
  for (let i = -1; i < 4; i++) { const y = -60 + i * 46 - sc; ctx.fillStyle = `rgba(20,60,110,${.45 * sa})`; ctx.fillRect(-29, y, 46, 36); ctx.fillStyle = `rgba(255,255,255,${.55 * sa})`; ctx.fillRect(-29, y + 39, 30, 2.5); }
  ctx.fillStyle = `rgba(255,70,90,${.9 * sa})`; ctx.beginPath(); ctx.arc(24, 18, 4.5, 0, 7); ctx.fill(); ctx.beginPath(); ctx.arc(24, 34, 3, 0, 7); ctx.fill();
  ctx.restore();
  ctx.restore();
  // 屏幕的光晕
  ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha *= a;
  const g = ctx.createRadialGradient(...PHONE, 0, ...PHONE, 260); g.addColorStop(0, `rgba(150,230,255,${.35 * sa})`); g.addColorStop(1, 'rgba(80,180,255,0)');
  ctx.fillStyle = g; ctx.fillRect(PHONE[0] - 260, PHONE[1] - 260, 520, 520);
  ctx.restore();
}
function drawFatArm(t, a) {
  ctx.save(); ctx.globalAlpha *= a;
  ctx.fillStyle = skinGrad(1300, 760, 260); ctx.fill(P_FARM); phoneLight(P_FARM, screenA(t) * .8);
  const sleeve = new Path2D(); sleeve.moveTo(1280, 560); sleeve.lineTo(1430, 560); sleeve.lineTo(1430, 748); sleeve.quadraticCurveTo(1350, 742, 1286, 700); sleeve.closePath();
  ctx.save(); ctx.clip(P_FARM); fillWithText(sleeve, t, 1, .95); ctx.restore(); // 短袖
  redStroke(P_FARM, 2.2, 12);
  const sl = new Path2D(); sl.moveTo(1294, 702); sl.quadraticCurveTo(1350, 744, 1404, 744); redStroke(sl, 2.2, 8); // 袖口勒出一圈肉
  const fold = new Path2D(); fold.moveTo(1236, 842); fold.quadraticCurveTo(1262, 858, 1282, 836); fold.moveTo(1392, 770); fold.quadraticCurveTo(1372, 800, 1384, 830); // 肘窝、上臂的赘肉
  ctx.strokeStyle = 'rgba(255,120,80,.5)'; ctx.lineWidth = 1.5; ctx.stroke(fold);
  ctx.restore();
}
function drawFatHand(t, a) { // 胖乎乎的手指扣在手机边上
  ctx.save(); ctx.globalAlpha *= a;
  const palm = catmull([[1134, 640], [1140, 602], [1168, 586], [1200, 600], [1210, 640], [1186, 672], [1152, 676]], true);
  ctx.fillStyle = skinGrad(1170, 630, 80); ctx.fill(palm); phoneLight(palm, screenA(t)); redStroke(palm, 2, 10);
  for (const [x, y, ang] of [[1112, 560, -.2], [1110, 588, -.1], [1114, 614, 0]]) { // 左边扣住手机背面的三根手指
    const fg = limb([x + 30, y + 12], [x, y], 24, 21); ctx.fillStyle = skinGrad(x, y, 50); ctx.fill(fg); redStroke(fg, 1.6, 8);
  }
  const th = limb([1190, 610], [1172, 548], 26, 22); ctx.fillStyle = skinGrad(1180, 580, 50); ctx.fill(th); phoneLight(th, screenA(t)); redStroke(th, 1.8, 8); // 大拇指在刷屏
  ctx.restore();
}
function kgReadout(t, a) { // 肚皮上的体重读数，每次心跳往上跳
  if (a <= 0) return;
  const kg = KG0 + KG_STEP * fatGrow(t);
  let hit = 0; for (const b of BEATS) { const d = t - b; if (d >= 0 && d < .35) hit = Math.max(hit, 1 - d / .35); }
  const y = 222, s = 1 + .12 * hit, num = kg.toFixed(1);
  ctx.save(); ctx.globalAlpha = a; ctx.textBaseline = 'alphabetic'; ctx.translate(1340, y); ctx.scale(s, s);
  ctx.font = '68px CinzelBold'; const w = ctx.measureText(num).width; ctx.font = '28px SansBold'; const wl = ctx.measureText('体重').width;
  const x = -(wl + 14 + w + 70) / 2;
  ctx.fillStyle = 'rgba(14,3,2,.72)'; ctx.fill(rr(x - 22, -72, wl + w + 128, 92, 12)); ctx.strokeStyle = `rgba(255,80,50,${.45 + .5 * hit})`; ctx.lineWidth = 1.6; ctx.stroke(rr(x - 22, -72, wl + w + 128, 92, 12));
  ctx.fillStyle = '#ffb08a'; ctx.fillText('体重', x, -6);
  ctx.font = '68px CinzelBold'; ctx.shadowColor = '#ff2a10'; ctx.shadowBlur = 22 + 30 * hit; ctx.fillStyle = hit > .5 ? '#ffffff' : '#ffe0d0';
  ctx.fillText(num, x + wl + 14, 0);
  ctx.font = '24px CinzelBold'; ctx.shadowBlur = 10; ctx.fillStyle = '#ff9a7a'; ctx.fillText('KG', x + wl + 22 + w, 0);
  ctx.fillStyle = `rgba(255,70,40,${.65 + .35 * hit})`; ctx.font = '26px SansBold'; ctx.fillText('▲', x + wl + 24 + w, -34 - 8 * hit);
  ctx.restore();
}
FIG.early = t => { // 黑暗里先亮起手机，青光勾出一张低头的脸
  if (t >= T.figure) return;
  const a = lin(t, .3, 1.2);
  if (a <= 0) return;
  ctx.save(); ctx.globalAlpha = .5 * a * (1 - lin(t, T.figure - .6, T.figure));
  ctx.translate(...HP); ctx.rotate(headA(t)); ctx.translate(-HP[0], -HP[1]);
  ctx.strokeStyle = 'rgba(120,220,255,.8)'; ctx.lineWidth = 1.6; ctx.shadowColor = '#40c8ff'; ctx.shadowBlur = 12; ctx.stroke(P_FHEAD);
  ctx.restore();
  drawFatHand(t, a); drawPhone(t, a);
};
FIG.red = (t, k) => {
  const P = fatPts(t), tilt = headA(t);
  const body = catmull([[1300, 468], ...P.slice(11, 24), [1440, 452], [1380, 466]], true);
  fillWithText(body, t, lin(t, T.figure + .4, T.figure + 3.2), k * .95);
  ctx.save(); ctx.globalAlpha = k; phoneLight(body, screenA(t) * .6, 420); ctx.setLineDash([3200 * eio(k), 5000]); redStroke(body, 2.6, 16); ctx.restore();
  ctx.save(); ctx.globalAlpha = k * .8; // T 恤：领口、绷紧的褶子、下摆
  const sh = new Path2D(); sh.moveTo(1288, 540); sh.quadraticCurveTo(1350, 560, 1440, 520);
  const g = fatGrow(t);
  for (let i = 0; i < 4; i++) { const y = 760 + i * 70, x0 = P[15][0] + 40 + i * 6; sh.moveTo(x0, y); sh.quadraticCurveTo(x0 + 70, y - 14 - g * 1.5, x0 + 140 + g * 4, y - 4); }
  redStroke(sh, 1.6, 6);
  ctx.restore();
  const hem = new Path2D(); hem.moveTo(P[17][0] - 10, 975); hem.quadraticCurveTo(1300, 1030, 1700, 990); hem.lineTo(1700, 1100); hem.lineTo(P[18][0] - 40, 1100); hem.closePath();
  ctx.save(); ctx.globalAlpha = k; ctx.clip(body); ctx.fillStyle = skinGrad(1180, 1060, 300); ctx.fill(hem); phoneLight(hem, screenA(t) * .5, 600);
  const hl = new Path2D(); hl.moveTo(P[17][0] - 10, 975); hl.quadraticCurveTo(1300, 1030, 1700, 990); redStroke(hl, 2.2, 10); // 卷起来的 T 恤下摆
  const nv = new Path2D(); nv.moveTo(1128, 1052); nv.quadraticCurveTo(1140, 1064, 1150, 1050); nv.moveTo(1092, 1078); nv.quadraticCurveTo(1170, 1094, 1250, 1080); // 肚脐、肚皮的褶
  ctx.strokeStyle = 'rgba(255,120,80,.6)'; ctx.lineWidth = 1.8; ctx.stroke(nv);
  ctx.restore();
  ctx.save(); ctx.globalAlpha = k; drawFatHead(t, 1); ctx.restore();
  drawFatArm(t, k);
};
FIG.redTop = (t, k) => {
  if (t >= T.figure) { drawFatHand(t, 1); drawPhone(t, 1); }
  kgReadout(t, lin(t, T.figure + 1, T.figure + 1.6));
  // 被手机照亮的眼睛
  const e = lin(t, .4, 1.4) * (.6 + .4 * screenA(t)), eye = rot([1288, 371], HP, headA(t));
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  const gg = ctx.createRadialGradient(...eye, 0, ...eye, 40);
  gg.addColorStop(0, `rgba(210,250,255,${.8 * e})`); gg.addColorStop(.25, `rgba(90,200,255,${.4 * e})`); gg.addColorStop(1, 'rgba(40,140,255,0)');
  ctx.fillStyle = gg; ctx.fillRect(eye[0] - 40, eye[1] - 40, 80, 80);
  ctx.restore();
};

// ================= 第二幕：雕像般的肌肉男 =================
// 头是侧脸（面朝左），身体正面朝外：宽肩、胸肌、六块腹肌；近侧手臂抬起屈肘亮出肱二头肌，拳头举到眼前，拳心发光。
const MUS0 = [[1378, 246], [1322, 254], [1292, 284], [1284, 318], [1278, 338], [1258, 372], [1272, 382], [1271, 396], [1276, 404], [1272, 412],
  [1282, 444], [1316, 462], [1306, 504], [1250, 536], [1176, 568], [1150, 650], [1186, 720], [1208, 860], [1232, 1095],
  [1630, 1095], [1636, 880], [1628, 720], [1590, 600], [1516, 526], [1454, 444], [1440, 300]];
// 举起的手臂（姿势 A）：上臂水平、二头肌高高鼓起，前臂竖直，拳头举到眼前（掌心朝外，指缝里透光）
const FIST = [1008, 352];                                      // 姿势 A 的拳心；摆造型时光源跟着拳头走（curFist）
const M0 = T.flash + .1, M1 = T.flash + 1.3, TC = T.flash + 1.45; // 轮廓收紧的起止、握拳亮光
const MUS_ARM = [[1215, 650], [1170, 672], [1100, 682], [1030, 674], [975, 652], [948, 615], [938, 560], [942, 500], [956, 430],
  [946, 395], [948, 350], [962, 318], [990, 300], [1025, 298], [1050, 312], [1062, 345], [1060, 390], [1036, 430],
  [1042, 470], [1040, 515], [1015, 548], [1062, 502], [1110, 515], [1160, 538], [1208, 556], [1232, 600]];
const P_UPARM = catmull([[1232, 600], [1215, 650], [1170, 672], [1100, 682], [1030, 674], [975, 652], [952, 612], [972, 572], [1015, 548], [1062, 502], [1110, 515], [1160, 538], [1208, 556]], true);
const P_UPARM_EDGE = catmull([[1215, 650], [1170, 672], [1100, 682], [1030, 674], [975, 652], [952, 612], [972, 572], [1015, 548], [1062, 502], [1110, 515], [1160, 538], [1208, 556]], false);
const P_FORE = catmull([[956, 430], [942, 500], [936, 560], [950, 612], [985, 630], [1022, 590], [1040, 530], [1044, 472], [1036, 430]], true);
const P_FIST = catmull([[955, 432], [945, 396], [948, 350], [962, 318], [990, 300], [1025, 298], [1050, 312], [1062, 345], [1062, 382], [1054, 410], [1036, 434]], true);
const P_THUMB = catmull([[952, 430], [968, 404], [1000, 384], [1034, 374], [1044, 386], [1030, 400], [996, 416], [966, 440]], true);
const MHAIR_C = [1376, 318], MHAIR_R = [80, 76];
const mhPt = (a, d = 0) => [MHAIR_C[0] + Math.cos(a) * (MHAIR_R[0] + d), MHAIR_C[1] + Math.sin(a) * (MHAIR_R[1] + d)];
const MHAIR = (() => { // 雕像式短卷发：贴着头骨，外缘一圈小鼓包
  const p = new Path2D(), n = 15, a0 = -2.75, a1 = .62;
  p.moveTo(...mhPt(a0, 0));
  for (let i = 1; i <= n; i++) p.quadraticCurveTo(...mhPt(mix(a0, a1, (i - .5) / n), 14 + 3 * Math.sin(i * 2.1)), ...mhPt(mix(a0, a1, i / n), 3));
  p.quadraticCurveTo(1438, 384, 1426, 380); p.bezierCurveTo(1420, 366, 1412, 352, 1398, 346);  // 耳后、耳上
  p.bezierCurveTo(1380, 336, 1360, 316, 1334, 312); p.quadraticCurveTo(1316, 304, 1302, 300); p.closePath(); // 鬓角、额头发际线
  return p;
})();
const MHAIR_CURLS = (() => {
  const p = new Path2D(), r = rng(23);
  for (const [k, n, a0, a1] of [[.84, 12, -2.6, .5], [.62, 8, -2.4, .2], [.4, 4, -2.1, -.3]]) {
    for (let i = 0; i < n; i++) {
      const a = mix(a0, a1, (i + .5) / n) + (r() - .5) * .08, x = MHAIR_C[0] + Math.cos(a) * MHAIR_R[0] * k, y = MHAIR_C[1] + Math.sin(a) * MHAIR_R[1] * k, r0 = 7 + r() * 2.5, s0 = a + 1.2;
      p.moveTo(x + Math.cos(s0) * r0, y + Math.sin(s0) * r0);
      for (let j = 1; j <= 12; j++) { const u = j / 12, an = s0 + u * 5.4, rad = r0 * (1 - u * .7); p.lineTo(x + Math.cos(an) * rad, y + Math.sin(an) * rad); }
    }
  }
  return p;
})();
// ---------- 摆造型：一套骨骼 + 一串健美姿势关键帧 ----------
// 手臂只画一份（上面那条举拳的近侧手臂 = 姿势 A），每一段按骨骼角度转过去再画；远侧手臂是它以 x=1390 为轴的镜像。
// 姿势参数 [上臂角 ua, 屈肘 rel, 朝向 tw]：tw=-1 是整条手臂沿骨轴翻过来（二头肌朝里、肘往里弯，用于最多肌肉、背阔展）。
// 翻面只在手臂伸直的中间姿势（mid）上发生，看不出跳变。
const S_A = [1205, 605], E_A = [980, 615], W_A = [995, 440], MIRROR_X = 2780;
const UA_A = Math.atan2(E_A[1] - S_A[1], E_A[0] - S_A[0]), FA_A = Math.atan2(W_A[1] - E_A[1], W_A[0] - E_A[0]);
const LU = Math.hypot(E_A[0] - S_A[0], E_A[1] - S_A[1]), REL_A = ((FA_A - UA_A) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI);
// 身体（不含远侧手臂，远侧手臂单独画）
const MUS_T = [...MUS0.slice(0, 19), [1478, 1095], [1492, 960], [1522, 848], [1560, 736], [1618, 668], [1606, 600], ...MUS0.slice(23)];
const POSES = {
  single:  { n: [UA_A, REL_A, 1], f: [1.69, .06, 1], torso: {}, front: 0 },                                     // 单臂二头（另一只手垂着）
  double:  { n: [3.04, 1.78, 1], f: [3.04, 1.78, 1], torso: { 13: [0, -6], 25: [0, -6] }, front: 0 },           // 前展双二头
  relaxC:  { n: [2.0, .08, 1], f: [2.0, .08, 1], torso: {}, front: 0, mid: 1 },                                   // 过渡：手臂垂直伸开
  crab:    { n: [2.05, 1.55, -1], f: [2.05, 1.55, -1], sh: -12, torso: { 12: [0, -6], 13: [0, -18], 25: [0, -18], 14: [0, -10], 24: [0, -10] }, front: 1 }, // 最多肌肉：双拳在腹前对顶，斜方肌耸起
  lat:     { n: [2.18, 1.33, -1], f: [2.18, 1.33, -1], torso: { 16: [-34, 0], 17: [-30, 0], 21: [30, 0], 22: [34, 0] }, front: 1 }, // 前展背阔：双拳叉腰，背阔肌张开
  relaxV:  { n: [3.3, .08, 1], f: [3.3, .08, 1], torso: {}, front: 0, mid: 1 },                                   // 过渡：双臂侧平举伸直
  victory: { n: [4.36, .15, 1], f: [4.36, .15, 1], sh: -10, torso: { 13: [0, -10], 25: [0, -10], 14: [0, -14], 24: [0, -14] }, front: 0 }, // 双拳举过头顶
};
const POSE_KEYS = [[0, 'single'], [12.28, 'single'], [12.7, 'double'], [14.15, 'double'], [14.38, 'relaxC'], [14.6, 'crab'],
  [16.08, 'crab'], [16.5, 'lat'], [17.95, 'lat'], [18.18, 'relaxV'], [18.4, 'victory'], [19.88, 'victory'], [20.3, 'double'],
  [21.78, 'double'], [22.2, 'single'], [99, 'single']];
const POSE_HITS = POSE_KEYS.map((k, i) => ({ t: k[0], i })).filter(({ i }) => i && !POSES[POSE_KEYS[i][1]].mid && POSE_KEYS[i - 1][1] !== POSE_KEYS[i][1])
  .map(({ t, i }) => ({ t, start: POSE_KEYS[i - (POSES[POSE_KEYS[i - 1][1]].mid ? 2 : 1)][0] }));   // 每次定格的时刻、动作起点
const HITS = [TC, ...POSE_HITS.map(h => h.t)];
const ebk = x => { const c = 1.3; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); };  // 带一点回弹的定格
function poseAt(t) {
  let i = 0; while (i < POSE_KEYS.length - 2 && t >= POSE_KEYS[i + 1][0]) i++;
  const [t0, a] = POSE_KEYS[i], [t1, b] = POSE_KEYS[i + 1], A = POSES[a], B = POSES[b], s = lin(t, t0, t1);
  const f = a === b ? 0 : B.mid ? s * s : A.mid ? ebk(s) : ebk(s * s * (3 - 2 * s));
  const arm = (pa, pb) => [mix(pa[0], pb[0], f), mix(pa[1], pb[1], f), A.mid ? pb[2] : pa[2]];
  const torso = MUS_T.map((q, j) => { const da = A.torso[j] || [0, 0], db = B.torso[j] || [0, 0]; return [q[0] + mix(da[0], db[0], f), q[1] + mix(da[1], db[1], f)]; });
  return { n: arm(A.n, B.n), f: arm(A.f, B.f), sh: mix(A.sh || 0, B.sh || 0, f), torso, front: a === b ? A.front : (s > .3 ? B.front : A.front) };
}
const deg = r => r * 180 / Math.PI;
function armMats(p, sh, mirror) { // 一条手臂的两段变换（上臂、前臂 + 拳头）和拳心位置
  const [ua, rel, tw] = p, wf = .72 + .28 * clamp(rel / 1.4), S = [S_A[0], S_A[1] + sh];
  const E = [S[0] + Math.cos(ua) * LU, S[1] + Math.sin(ua) * LU], fa = ua + rel * tw;
  const base = mirror ? new DOMMatrix([-1, 0, 0, 1, MIRROR_X, 0]) : new DOMMatrix();
  const mU = base.translate(S[0], S[1]).rotate(deg(ua)).scale(1, tw * wf).rotate(-deg(UA_A)).translate(-S_A[0], -S_A[1]);
  const mF = base.translate(E[0], E[1]).rotate(deg(fa)).scale(1, tw).rotate(-deg(FA_A)).translate(-E_A[0], -E_A[1]);
  const q = mF.transformPoint(new DOMPoint(FIST[0], FIST[1]));
  return { mU, mF, fist: [q.x, q.y] };
}
function rigAt(t) { const P = poseAt(t); return { ...P, near: armMats(P.n, P.sh, false), far: armMats(P.f, P.sh, true) }; }
const pumpAt = t => HITS.reduce((m, h) => t >= h ? Math.max(m, Math.exp(-(t - h) * 4)) : m, 0); // 每次定格时肌肉充血一下

let FIG_BASE = new DOMMatrix(), curFist = FIST;                  // 第二幕的基础变换、此刻拳头（光源）的位置
const applyM = m => ctx.transform(m.a, m.b, m.c, m.d, m.e, m.f);
function bodyFill(path) {
  const g = ctx.createLinearGradient(0, 240, 0, 1080); g.addColorStop(0, '#20180c'); g.addColorStop(.5, '#120d07'); g.addColorStop(1, '#070504');
  ctx.fillStyle = g; ctx.fill(path);
  const L = ctx.getTransform().inverse().multiply(FIG_BASE).transformPoint(new DOMPoint(curFist[0], curFist[1])); // 光源换到当前局部坐标
  ctx.save(); ctx.clip(path); // 拳头的光把身体照亮
  const rim = ctx.createRadialGradient(L.x, L.y, 0, L.x, L.y, 620); rim.addColorStop(0, 'rgba(255,230,170,.26)'); rim.addColorStop(.45, 'rgba(200,150,70,.10)'); rim.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = rim; ctx.fillRect(-4000, -4000, 8000, 8000); ctx.restore();
}
// 肌肉体积：[x, y, rx, ry, 强度]，金色柔光叠在肌肉鼓起来的地方
const TORSO_HL = [[1290, 660, 72, 50, .16], [1440, 668, 84, 52, .13], [1592, 650, 38, 62, .12], [1494, 540, 40, 22, .1], [1360, 470, 34, 30, .08],
  [1308, 800, 34, 36, .14], [1396, 800, 36, 36, .12], [1308, 884, 32, 36, .13], [1398, 884, 34, 36, .11], [1312, 966, 30, 34, .12], [1396, 966, 32, 34, .1],
  [1240, 900, 18, 70, .1], [1330, 300, 40, 50, .08]];
const ARM_HL = [[1082, 560, 66, 40, .2], [1190, 610, 32, 44, .14], [1080, 664, 52, 14, .08]], FORE_HL = [[985, 540, 34, 70, .14]];
function sculpt(path, list, pump = 1) {
  ctx.save(); ctx.clip(path); ctx.globalCompositeOperation = 'lighter';
  for (const [x, y, rx, ry, a] of list) {
    ctx.save(); ctx.translate(x - rx * .25, y - ry * .3); ctx.scale(rx, ry);
    const g = ctx.createRadialGradient(0, 0, 0, 0, 0, 1); g.addColorStop(0, `rgba(255,214,140,${Math.min(.5, a * pump)})`); g.addColorStop(1, 'rgba(255,200,120,0)');
    ctx.fillStyle = g; ctx.fillRect(-1, -1, 2, 2); ctx.restore();
  }
  ctx.restore();
}
const TORSO_LINES = (() => { // 下颌、颈、斜方肌、锁骨、胸肌、胸骨、右三角肌、背阔肌、前锯肌、腹外斜肌、人鱼线
  const b = new Path2D();
  b.moveTo(1284, 446); b.quadraticCurveTo(1336, 462, 1396, 440); b.lineTo(1404, 414);
  b.moveTo(1418, 426); b.quadraticCurveTo(1384, 488, 1340, 552);
  b.moveTo(1316, 470); b.quadraticCurveTo(1326, 480, 1318, 492);
  b.moveTo(1440, 470); b.quadraticCurveTo(1500, 520, 1570, 572);
  b.moveTo(1300, 520); b.quadraticCurveTo(1270, 534, 1240, 556);
  b.moveTo(1240, 578); b.quadraticCurveTo(1290, 566, 1336, 566); b.moveTo(1356, 566); b.quadraticCurveTo(1430, 560, 1500, 572);
  b.moveTo(1218, 650); b.bezierCurveTo(1230, 730, 1300, 760, 1346, 724);
  b.moveTo(1352, 724); b.bezierCurveTo(1400, 768, 1490, 752, 1548, 690);
  b.moveTo(1346, 588); b.lineTo(1348, 724);
  b.moveTo(1540, 590); b.bezierCurveTo(1584, 612, 1604, 646, 1604, 688); b.moveTo(1548, 612); b.quadraticCurveTo(1560, 650, 1574, 690);
  b.moveTo(1200, 724); b.quadraticCurveTo(1226, 800, 1222, 880);
  for (const y of [742, 774, 806]) { b.moveTo(1212, y); b.quadraticCurveTo(1236, y + 2, 1250, y + 18); }
  b.moveTo(1238, 830); b.bezierCurveTo(1246, 900, 1256, 960, 1276, 1012);
  b.moveTo(1484, 800); b.bezierCurveTo(1474, 890, 1462, 960, 1444, 1012);
  b.moveTo(1270, 1000); b.quadraticCurveTo(1306, 1044, 1326, 1095); b.moveTo(1440, 1000); b.quadraticCurveTo(1408, 1044, 1390, 1095);
  return b;
})();
const ABS_LINES = (() => { // 腹肌：白线 + 两侧半月线 + 三道横向腱划，线条是弯的，不画成方块
  const abs = new Path2D();
  abs.moveTo(1350, 744); abs.bezierCurveTo(1354, 850, 1352, 960, 1358, 1070);
  abs.moveTo(1278, 760); abs.bezierCurveTo(1262, 840, 1266, 930, 1286, 1010); abs.moveTo(1432, 760); abs.bezierCurveTo(1450, 840, 1446, 930, 1424, 1010);
  for (const [y, d] of [[842, 10], [924, 9], [1004, 7]]) { abs.moveTo(1268, y + 4); abs.quadraticCurveTo(1310, y - d, 1350, y + 2); abs.moveTo(1353, y + 2); abs.quadraticCurveTo(1398, y - d, 1444, y + 4); }
  return abs;
})();
const FACE_LINES = (() => { // 耳朵、眼、鼻翼、嘴、颧骨
  const f = new Path2D();
  f.moveTo(1412, 372); f.bezierCurveTo(1392, 366, 1388, 412, 1408, 416); f.moveTo(1406, 382); f.quadraticCurveTo(1398, 394, 1406, 404);
  f.moveTo(1290, 332); f.quadraticCurveTo(1300, 326, 1312, 330); f.moveTo(1291, 337); f.quadraticCurveTo(1301, 341, 1310, 336);
  f.moveTo(1266, 378); f.quadraticCurveTo(1274, 384, 1276, 376);
  f.moveTo(1272, 404); f.lineTo(1290, 406);
  f.moveTo(1316, 360); f.quadraticCurveTo(1340, 372, 1360, 372);
  return f;
})();
const BROW = (() => { const p = new Path2D(); p.moveTo(1282, 320); p.quadraticCurveTo(1300, 314, 1324, 318); return p; })(); // 压低的眉：专注
const UA_LINES = (() => { const p = new Path2D(); p.moveTo(1214, 566); p.bezierCurveTo(1176, 590, 1176, 640, 1210, 664); // 三角肌
  p.moveTo(1150, 546); p.bezierCurveTo(1120, 596, 1060, 612, 1000, 596); p.moveTo(1150, 660); p.quadraticCurveTo(1090, 646, 1030, 660); return p; })(); // 二头肌下缘、三头肌
const VEIN_U = (() => { const p = new Path2D(); p.moveTo(1160, 560); p.bezierCurveTo(1130, 552, 1108, 568, 1080, 552); p.quadraticCurveTo(1054, 540, 1030, 556); return p; })();
const VEIN_F = (() => { const p = new Path2D(); p.moveTo(990, 600); p.bezierCurveTo(1000, 560, 984, 520, 996, 470); return p; })();
const FO_LINES = (() => { const p = new Path2D(); p.moveTo(944, 570); p.bezierCurveTo(962, 540, 972, 500, 974, 450); p.moveTo(1026, 580); p.quadraticCurveTo(1018, 520, 1026, 466); return p; })();
const FI_LINES = (() => { const p = new Path2D(); // 弯起来的四根手指（掌心朝外）、指尖、手背一侧的指节
  for (const y of [324, 350, 376]) { p.moveTo(990, y + 2); p.quadraticCurveTo(1026, y - 6, 1061, y + 2); }
  for (const y of [312, 337, 363, 389]) { p.moveTo(996, y - 8); p.quadraticCurveTo(988, y, 996, y + 8); }
  p.moveTo(962, 320); p.quadraticCurveTo(976, 360, 960, 400); return p; })();
function drawUpperArm(m, pump) {
  ctx.save(); applyM(m);
  bodyFill(P_UPARM); sculpt(P_UPARM, ARM_HL, pump); glowStroke(P_UPARM_EDGE, 2.8 + (pump - 1) * .6, 16); glowStroke(UA_LINES, 1.5, 8); glowStroke(VEIN_U, 1, 5, '#e8b85a');
  ctx.restore();
}
function drawForearm(m, pump) {
  ctx.save(); applyM(m);
  bodyFill(P_FORE); sculpt(P_FORE, FORE_HL, pump); glowStroke(P_FORE, 2.6 + (pump - 1) * .6, 14); glowStroke(FO_LINES, 1.4, 7); glowStroke(VEIN_F, 1, 5, '#e8b85a');
  bodyFill(P_FIST); glowStroke(P_FIST, 2.4, 14); glowStroke(FI_LINES, 1.3, 7); darkFill(P_THUMB, '#18120a'); glowStroke(P_THUMB, 2, 10); // 大拇指压在手指上
  ctx.restore();
}
function armTrail(t) { // 换造型时手臂拖出的金色残影
  const R0 = rigAt(t);
  ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.lineJoin = 'round';
  for (const [dt, al] of [[.05, .3], [.1, .18], [.15, .09]]) {
    const R = rigAt(t - dt);
    for (const side of ['near', 'far']) {
      const a = R[side], b = R0[side], moved = Math.hypot(a.fist[0] - b.fist[0], a.fist[1] - b.fist[1]);
      if (moved < 6) continue;
      for (const [m, paths] of [[a.mU, [P_UPARM_EDGE]], [a.mF, [P_FORE, P_FIST]]]) {
        ctx.save(); applyM(m); ctx.strokeStyle = `rgba(255,214,140,${al * Math.min(1, moved / 60)})`; ctx.lineWidth = 3; ctx.shadowColor = '#ffb040'; ctx.shadowBlur = 14;
        for (const p of paths) ctx.stroke(p); ctx.restore();
      }
    }
  }
  ctx.restore();
}
function drawMuscle(t, a) {
  if (a <= 0) return;
  const R = rigAt(t), pump = 1 + 1.2 * pumpAt(t), P = catmull(R.torso, true);
  ctx.save(); ctx.globalAlpha *= a;
  drawUpperArm(R.far.mU, pump);                     // 远侧手臂：上臂总在身体后面，前臂看姿势（最多肌肉、背阔展时在身体前面）
  if (!R.front) drawForearm(R.far.mF, pump);
  bodyFill(P); sculpt(P, TORSO_HL, pump); glowStroke(P, 3.2 + (pump - 1) * .8, 22);
  glowStroke(TORSO_LINES, 1.5, 8); glowStroke(ABS_LINES, 1.4, 7);
  darkFill(MHAIR, '#16100a'); glowStroke(MHAIR, 2.2, 12);
  ctx.save(); ctx.clip(MHAIR); glowStroke(MHAIR_CURLS, 1.1, 5); ctx.restore();
  glowStroke(FACE_LINES, 1.6, 7); glowStroke(BROW, 3, 8);
  ctx.save(); ctx.fillStyle = '#0c0905'; ctx.beginPath(); ctx.ellipse(1297, 333, 3.2, 4, 0, 0, Math.PI * 2); ctx.fill(); ctx.restore();
  accentFill(circ(1296, 332, 1.6), 8);
  if (R.front) drawForearm(R.far.mF, pump);
  drawUpperArm(R.near.mU, pump); drawForearm(R.near.mF, pump);  // 近侧手臂在最前面
  if (t > TC) armTrail(t);
  ctx.restore();
}
function fistLight(t, k) { // 握紧的拳头里透出的光（跟着拳头走）
  if (k <= 0) return;
  const [x, y] = curFist, pul = 1 + .06 * Math.sin(t * 2.4), age = t - T.gold, mF = rigAt(t).near.mF;
  ctx.save(); ctx.globalAlpha *= k; ctx.globalCompositeOperation = 'lighter';
  const big = ctx.createRadialGradient(x, y, 0, x, y, 420); big.addColorStop(0, `rgba(255,246,225,${.26 * pul})`); big.addColorStop(.3, 'rgba(255,200,110,.13)'); big.addColorStop(1, 'rgba(255,180,90,0)');
  ctx.fillStyle = big; ctx.fillRect(x - 420, y - 420, 840, 840);
  for (let i = 0; i < 28; i++) { // 从指缝里漏出来的光芒
    const a = i / 28 * Math.PI * 2 + Math.sin(t * .8 + i) * .03, l = (90 + 80 * Math.sin(i * 2.7) ** 2) * pul;
    const g = ctx.createLinearGradient(x, y, x + Math.cos(a) * l, y + Math.sin(a) * l); g.addColorStop(0, 'rgba(255,255,245,.7)'); g.addColorStop(1, 'rgba(255,210,130,0)');
    ctx.strokeStyle = g; ctx.lineWidth = i % 3 ? 1 : 2; ctx.beginPath(); ctx.moveTo(x + Math.cos(a) * 62, y + Math.sin(a) * 62); ctx.lineTo(x + Math.cos(a) * l, y + Math.sin(a) * l); ctx.stroke();
  }
  ctx.save(); applyM(mF); // 指缝里漏出的光线（跟着拳头转）
  for (const yy of [324, 350, 376]) {
    const g = ctx.createLinearGradient(990, 0, 1100, 0); g.addColorStop(0, 'rgba(255,250,235,.0)'); g.addColorStop(.3, `rgba(255,250,235,${.8 * pul})`); g.addColorStop(1, 'rgba(255,220,150,0)');
    ctx.strokeStyle = g; ctx.lineWidth = 2.2; ctx.beginPath(); ctx.moveTo(990, yy + 2); ctx.quadraticCurveTo(1026, yy - 6, 1100, yy + 4); ctx.stroke();
  }
  ctx.restore();
  for (const [rad, al] of [[44, .22], [26, .5], [14, .9]]) { const cg = ctx.createRadialGradient(x, y, 0, x, y, rad * pul); cg.addColorStop(0, `rgba(255,255,250,${al})`); cg.addColorStop(1, 'rgba(255,220,150,0)'); ctx.fillStyle = cg; ctx.fillRect(x - rad * 1.2, y - rad * 1.2, rad * 2.4, rad * 2.4); }
  for (let i = 0; i < 3; i++) { // 一圈圈往外扩散的光波（audio.py 同步：第 1 + i×0.9 秒起，每 2.7 秒一圈）
    if (age < 1 + i * .9 || t < TC) continue;
    const ph = ((age - 1 - i * .9) % 2.7) / 2.7;
    ctx.strokeStyle = `rgba(255,236,200,${.45 * (1 - ph) ** 1.5})`; ctx.lineWidth = 1 + 3 * (1 - ph); ctx.shadowColor = AG(); ctx.shadowBlur = 16;
    ctx.beginPath(); ctx.arc(x, y, 34 + eout(ph) * 440, 0, Math.PI * 2); ctx.stroke(); ctx.shadowBlur = 0;
  }
  for (const [ang, len, w] of [[0, 210, 2.6], [Math.PI / 2, 130, 2]]) { // 十字星芒
    ctx.save(); ctx.translate(x, y); ctx.rotate(ang);
    const g = ctx.createLinearGradient(-len, 0, len, 0); g.addColorStop(0, 'rgba(255,230,180,0)'); g.addColorStop(.5, `rgba(255,255,250,${.85 * pul - .1})`); g.addColorStop(1, 'rgba(255,230,180,0)');
    ctx.fillStyle = g; ctx.fillRect(-len, -w / 2, len * 2, w); ctx.restore();
  }
  ctx.restore();
}
function hitBursts(t) { // 每次定格：拳头处一圈光环 + 迸出的金色火花，身后闪一下
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  HITS.forEach((h, j) => {
    const age = t - h; if (age < 0 || age > 1.2) return;
    const [x, y] = rigAt(h + .3).near.fist, fl = 1 - lin(age, 0, .5);
    if (fl > 0) { ctx.strokeStyle = `rgba(255,240,200,${fl})`; ctx.lineWidth = 3 + 6 * fl; ctx.shadowColor = '#ffd27a'; ctx.shadowBlur = 24; ctx.beginPath(); ctx.arc(x, y, 40 + (1 - fl) * 260, 0, Math.PI * 2); ctx.stroke(); ctx.shadowBlur = 0; }
    if (j) { const g = ctx.createRadialGradient(HC[0], HC[1] + 200, 0, HC[0], HC[1] + 200, 760); g.addColorStop(0, `rgba(255,214,140,${.2 * (1 - lin(age, 0, .6))})`); g.addColorStop(1, 'rgba(255,200,120,0)'); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); }
    const r = rng(500 + j);
    for (let i = 0; i < 30; i++) {
      const an = r() * Math.PI * 2, v = 160 + r() * 420, life = .5 + r() * .7; if (age > life) continue;
      ctx.fillStyle = `rgba(255,232,170,${1 - age / life})`; ctx.fillRect(x + Math.cos(an) * v * age, y + Math.sin(an) * v * age + 140 * age * age, 2.6, 2.6);
    }
  });
  ctx.restore();
}
// ---------- 胖 → 瘦：金色轮廓一圈圈收紧 ----------
const FAT_END = fatPts(T.flash), MORPH_A = catmullPts(FAT_END, true, 10), MORPH_B = catmullPts(MUS0, true, 10);
const morphK = t => eio(lin(t, M0, M1));
function morphPts(k) { return MORPH_A.map((p, i) => [mix(p[0], MORPH_B[i][0], k), mix(p[1], MORPH_B[i][1], k)]); }
// 手臂变形按骨骼转：轮廓上每个点记在它所属的骨头（上臂 / 前臂）的局部坐标里，骨头的角度和长度插值后再还原，
// 这样胖手臂是“转”上去变成举拳的，中途轮廓不会打结。
const ARM_BONE = i => (i <= 4 || i >= 21) ? 0 : 1;   // 0 上臂、1 前臂和手
const BONES_A = [[1345, 640], [1290, 880], [1160, 610]], BONES_B = [[1200, 600], [990, 630], [1005, 360]]; // 肩、肘、手
function boneFrames(B) { return [0, 1].map(j => { const a = B[j], b = B[j + 1], L = Math.hypot(b[0] - a[0], b[1] - a[1]); return { o: a, L, ang: Math.atan2(b[1] - a[1], b[0] - a[0]) }; }); }
function toLocal(pts, B) { const F = boneFrames(B); return pts.map((p, i) => { const f = F[ARM_BONE(i)], c = Math.cos(f.ang), s = Math.sin(f.ang), dx = p[0] - f.o[0], dy = p[1] - f.o[1]; return [(dx * c + dy * s) / f.L, -dx * s + dy * c]; }); }
const ARM_A = catmullPts(FAT_ARM, true, 1), ARM_B = catmullPts(MUS_ARM, true, 1), LOC_A = toLocal(ARM_A, BONES_A), LOC_B = toLocal(ARM_B, BONES_B);
const FA = boneFrames(BONES_A), FB = boneFrames(BONES_B);
function morphArm(k) { // 举手机的胖手臂 → 举拳的手臂
  const S0 = [mix(FA[0].o[0], FB[0].o[0], k), mix(FA[0].o[1], FB[0].o[1], k)], fr = [];
  let o = S0;
  for (let j = 0; j < 2; j++) { const ang = mix(FA[j].ang, FB[j].ang, k), L = mix(FA[j].L, FB[j].L, k); fr.push({ o, ang, L }); o = [o[0] + Math.cos(ang) * L, o[1] + Math.sin(ang) * L]; }
  const pts = LOC_A.map((a, i) => { const b = LOC_B[i], f = fr[ARM_BONE(i)], u = mix(a[0], b[0], k) * f.L, v = mix(a[1], b[1], k), c = Math.cos(f.ang), s = Math.sin(f.ang); return [f.o[0] + u * c - v * s, f.o[1] + u * s + v * c]; });
  return [catmull(pts, true)];
}
function morphGhost(t) {
  const k = morphK(t), a = lin(t, T.flash, T.flash + .15) * (1 - lin(t, M1 + .05, M1 + .45));
  if (a <= 0) return;
  ctx.save(); ctx.globalAlpha *= a;
  const pts = morphPts(k), p = poly(pts), heat = 1 - lin(t, M1 - .2, M1 + .3), arm = morphArm(k)[0];
  for (const [path, w] of [[p, 3 + 2 * heat], [arm, 2.6 + 1.5 * heat]]) { // 实心剪影：先填暗色（手臂盖住身体的线），再描金边
    bodyFill(path);
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = `rgba(255,190,90,${.06 + .1 * heat})`; ctx.fill(path); ctx.restore();
    glowStroke(path, w, 28, '#ffd27a');
  }
  ctx.restore();
}
const EMBERS = (() => { const r = rng(606), a = []; for (let i = 0; i < 260; i++) a.push({ j: Math.floor(r() * MORPH_A.length), tb: M0 + r() * (M1 - M0 + .1), vx: (r() - .5) * 60, vy: -40 - r() * 120, life: .5 + r() * .7, s: 1.4 + r() * 2.6 }); return a; })();
function burnEmbers(t) { // 收紧时从轮廓上剥落、往上飘的金色火星（烧掉的脂肪）
  if (t < M0 || t > M1 + 1.3) return;
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  for (const e of EMBERS) {
    const d = t - e.tb; if (d < 0 || d > e.life) continue;
    const k = morphK(e.tb), p = [mix(MORPH_A[e.j][0], MORPH_B[e.j][0], k), mix(MORPH_A[e.j][1], MORPH_B[e.j][1], k)];
    const out = [MORPH_A[e.j][0] - MORPH_B[e.j][0], MORPH_A[e.j][1] - MORPH_B[e.j][1]], ol = Math.hypot(...out) || 1;
    const x = p[0] + (out[0] / ol * 90 + e.vx) * d, y = p[1] + (out[1] / ol * 90 + e.vy) * d - 40 * d * d, a = (1 - d / e.life) ** 1.3;
    ctx.fillStyle = `rgba(255,${200 + (e.j % 5) * 10},${110 + (e.j % 3) * 30},${a})`; ctx.beginPath(); ctx.arc(x, y, e.s * (1 - d / e.life * .5), 0, Math.PI * 2); ctx.fill();
  }
  ctx.restore();
}
FIG.gold = (t, k) => {
  FIG_BASE = ctx.getTransform(); curFist = rigAt(t).near.fist;
  const pu = pumpAt(t);
  ctx.save(); ctx.translate(1390, 760); ctx.scale(1 + .012 * pu, 1 + .012 * pu); ctx.translate(-1390, -760); // 定格时整个人鼓一下
  drawMuscle(t, lin(t, M1 - .45, M1 + .15));
  fistLight(t, eout(lin(t, TC, TC + .45)));
  ctx.restore();
  morphGhost(t);
  hitBursts(t);
};
FIG.burst = t => burnEmbers(t);
function dayCounter(t) { // 左边的计数器：第 1 天 → 第 365 天，体重往下掉；标题出来前淡出
  const a = lin(t, M0, M0 + .3) * (1 - lin(t, T.tag - .55, T.tag - .1));
  if (a <= 0) return;
  const k = eio(lin(t, M0 + .05, M1 + .1)), day = Math.max(1, Math.round(365 * k)), kg = mix(KG0 + KG_STEP * BEATS.length, 76.0, k);
  ctx.save(); ctx.globalAlpha = a; const x0 = 112;
  ctx.textBaseline = 'alphabetic'; ctx.shadowColor = 'rgba(255,170,60,.7)'; ctx.shadowBlur = 30;
  ctx.font = '64px SerifBold'; ctx.fillStyle = '#fbf3e2'; ctx.fillText('第', x0, 600);
  ctx.font = '190px CinzelBold'; const g = ctx.createLinearGradient(0, 440, 0, 610); g.addColorStop(0, '#fff7da'); g.addColorStop(.5, '#f6c867'); g.addColorStop(1, '#b8781e');
  ctx.fillStyle = g; const s = String(day); ctx.fillText(s, x0 + 78, 610); const w = ctx.measureText(s).width;
  ctx.font = '64px SerifBold'; ctx.fillStyle = '#fbf3e2'; ctx.fillText('天', x0 + 96 + Math.max(w, 300), 600);
  ctx.shadowBlur = 0; ctx.strokeStyle = 'rgba(232,200,140,.6)'; ctx.lineWidth = 1.4; ctx.beginPath(); ctx.moveTo(x0, 650); ctx.lineTo(x0 + 560, 650); ctx.stroke();
  ctx.font = '34px Sans'; ctx.fillStyle = '#efe2c6'; ctx.fillText('体重', x0, 708);
  ctx.font = '40px CinzelBold'; ctx.fillStyle = '#ffd27a'; ctx.fillText(kg.toFixed(1) + ' KG', x0 + 92, 710);
  ctx.font = '30px SansBold'; ctx.fillStyle = 'rgba(140,230,170,.95)'; ctx.fillText('▼', x0 + 360, 706);
  ctx.restore();
}
FIG.flare = t => {
  const [x, y] = rigAt(t).near.fist;
  flare(x, y, (.22 + .12 * Math.sin(t * 2.4)) * lin(t, TC, TC + .6), 460);
  for (const h of HITS) { const [hx, hy] = rigAt(h + .3).near.fist; flare(hx, hy, (h === TC ? 1.1 : .6) * Math.sin(Math.PI * lin(t, h, h + .7)), 900); } // 每次定格一道横向光晕
  dayCounter(t);
};
// 人物专属音效时间点（render.js events 导出 → audio.py）
FIG.events = [
  ...BEATS.map(t => ({ t, kind: 'swell' })),
  ...CARD_T.map(t => ({ t, kind: 'buzz' })),
  { t: M0, kind: 'contract', dur: M1 - M0 },
  { t: M0 + .05, kind: 'counter', t1: M1 + .1 },
  { t: TC, kind: 'clench' },
  ...POSE_HITS.map(h => ({ t: h.t, kind: 'pose', pre: h.t - h.start })),
];
