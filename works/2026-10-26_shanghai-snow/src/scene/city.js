// 外滩看陆家嘴雪夜（three.js）。
// 坐标：米；X 向东，Z 向南，Y 向上；原点 = 东方明珠。地标相对位置按 WGS84 坐标换算：
//   东方明珠 (0,0)  金茂 (635,493)  上海中心 (598,684)  环球金融中心 (~790,600)
// 机位在外滩（明珠以西 601m、以南 100m），站在江堤护墙后 1m，眼高 8.5m（高出墙顶 0.9m）；
// 从左到右：明珠、金茂、环球、上海中心。
// window.renderAt(t) 无状态：同一 t 永远画出同一帧，返回 JPEG dataURL。
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { Reflector } from 'three/addons/objects/Reflector.js';

const Q = new URLSearchParams(location.search);
const SC = parseFloat(Q.get('scale') || '1');
const W = Math.round(1080 * SC), H = Math.round(1920 * SC);
const DUR = 24.5;
const HORIZON_PX = 1180;          // 地平线在 1920 高画面里的位置（移轴）
const FOCAL0 = 1300, FOCAL1 = 1370; // 焦距（像素，按 1080 宽），缓慢推近
const AZ0 = -8.5;                  // 镜头朝向：正东偏南 8.5°
const GROUND = 4;                  // 浦东地面高出江面

function mulberry32(a) {
  return function () {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}
let rng = mulberry32(20261026);
const R = (a, b) => a + (b - a) * rng();
const pick = arr => arr[Math.floor(rng() * arr.length)];
const smooth = (e0, e1, x) => { x = Math.min(Math.max((x - e0) / (e1 - e0), 0), 1); return x * x * (3 - 2 * x); };
const col = (hex, k = 1) => new THREE.Color(hex).multiplyScalar(k);

// ------------------------------------------------------------------ renderer / scene
const renderer = new THREE.WebGLRenderer({ antialias: false, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(W, H);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const FOG_COLOR = col('#4a4060');
scene.fog = new THREE.FogExp2(FOG_COLOR, 0.00046);

const camera = new THREE.PerspectiveCamera(80, W / H, 1.0, 16000);
camera.layers.enable(1);
const CAM0 = new THREE.Vector3(-601, 8.5, 100);

const NOISE_GLSL = `
float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p){ vec2 i = floor(p), f = fract(p); vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y); }
float fbm(vec2 p){ float v = 0.0, a = 0.5; for (int i = 0; i < 5; i++){ v += a * noise(p); p *= 2.03; a *= 0.5; } return v; }
`;

// ------------------------------------------------------------------ 天空（城市灯光映在雪云上：地平线暖、天顶深蓝）
const skyMat = new THREE.ShaderMaterial({
  side: THREE.BackSide, depthWrite: false, fog: false,
  uniforms: { zen: { value: col('#121426') }, mid: { value: col('#382c4c') }, hor: { value: col('#a87884') }, time: { value: 0 } },
  vertexShader: `varying vec3 vDir;
    void main(){ vec4 wp = modelMatrix * vec4(position, 1.0); vDir = wp.xyz - cameraPosition;
      gl_Position = projectionMatrix * viewMatrix * wp; gl_Position.z = gl_Position.w; }`,
  fragmentShader: `uniform vec3 zen, mid, hor; uniform float time; varying vec3 vDir;
    ${NOISE_GLSL}
    void main(){ vec3 d = normalize(vDir); float e = d.y;
      vec3 c = mix(hor, mid, smoothstep(-0.02, 0.20, e));
      c = mix(c, zen, smoothstep(0.18, 0.80, e));
      vec2 uv = d.xz / max(d.y + 0.22, 0.04);
      float n = fbm(uv * 1.3 + vec2(time * 0.015, time * 0.004));
      c *= 0.72 + 0.55 * n;
      gl_FragColor = vec4(c, 1.0); }`,
});
const sky = new THREE.Mesh(new THREE.SphereGeometry(14000, 48, 24), skyMat);
sky.renderOrder = -10;
scene.add(sky);

// 反射环境：玻璃幕墙上映出暖色城市光带
{
  const pm = new THREE.PMREMGenerator(renderer);
  const env = new THREE.Scene();
  env.add(new THREE.Mesh(new THREE.SphereGeometry(100, 64, 32), new THREE.ShaderMaterial({
    side: THREE.BackSide,
    vertexShader: `varying vec3 vD; void main(){ vD = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: `varying vec3 vD; ${NOISE_GLSL}
      void main(){ vec3 d = normalize(vD); float e = d.y;
        vec3 c = mix(vec3(0.16, 0.10, 0.12), vec3(0.03, 0.035, 0.07), smoothstep(-0.05, 0.4, e));
        float lon = atan(d.z, d.x);
        float lights = step(0.62, noise(vec2(lon * 40.0, e * 30.0))) * smoothstep(0.25, 0.0, abs(e - 0.03));
        c += vec3(1.4, 0.95, 0.6) * lights;
        c += vec3(0.35, 0.25, 0.3) * smoothstep(0.12, 0.0, abs(e));
        gl_FragColor = vec4(c, 1.0); }`,
  })));
  scene.environment = pm.fromScene(env, 0.03).texture;
}

scene.add(new THREE.HemisphereLight(col('#7d84c0'), col('#1d151b'), 0.5));
const keyLight = new THREE.DirectionalLight(col('#c8b2c8'), 0.55);   // 来自外滩一侧的泛光，让朝西的面略亮
keyLight.position.set(-800, 300, 200);
scene.add(keyLight);
const rimLight = new THREE.DirectionalLight(col('#6f86d8'), 0.35);
rimLight.position.set(300, 500, -600);
scene.add(rimLight);

// ------------------------------------------------------------------ 纹理
function canvasTex(w, h, draw) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.anisotropy = 8;
  return t;
}
const rgb = (c, k) => `rgb(${Math.round(c[0] * k)},${Math.round(c[1] * k)},${Math.round(c[2] * k)})`;
const WARM = [255, 204, 140], COOL = [205, 222, 255], WHITE = [246, 240, 226], BLUE = [140, 185, 255];
// 窗格贴图：16 列 × 64 层 ≈ 52.8m × 249.6m
const TEX_W = 52.8, TEX_H = 249.6;
function windowTex(style, seed) {
  const r = mulberry32(seed);
  return canvasTex(512, 1024, (g, w, h) => {
    g.fillStyle = '#000'; g.fillRect(0, 0, w, h);
    const cols = 16, rows = 64, cw = w / cols, ch = h / rows;
    const p = { warm: 0.3, cool: 0.36, mixed: 0.3, sparse: 0.1, dense: 0.5 }[style] ?? 0.3;
    if (style === 'office' || style === 'bands') {
      for (let y = 0; y < rows; y++) {
        const lit = r() < (style === 'office' ? 0.45 : 0.25);
        const c = r() < 0.7 ? COOL : WHITE, k = 0.45 + 0.5 * r();
        for (let x = 0; x < cols; x++) {
          if (!lit && r() > 0.12) continue;
          g.fillStyle = rgb(c, lit ? k : 0.5 * k);
          g.fillRect(x * cw + 1, y * ch + 3, cw - 2, ch - 6);
        }
      }
      return;
    }
    if (style === 'led') {
      for (let x = 0; x < cols; x += 2) {
        const c = [BLUE, [255, 120, 210], [120, 230, 255], WHITE][Math.floor(r() * 4)];
        const grd = g.createLinearGradient(0, 0, 0, h);
        grd.addColorStop(0, rgb(c, 1)); grd.addColorStop(1, rgb(c, 0.25));
        g.fillStyle = grd; g.fillRect(x * cw + cw * 0.42, 0, cw * 0.16, h);
      }
      for (let y = 0; y < rows; y++) for (let x = 0; x < cols; x++) if (r() < 0.2) {
        g.fillStyle = rgb(WHITE, 0.3 + 0.3 * r()); g.fillRect(x * cw + 4, y * ch + 4, cw - 8, ch - 8);
      }
      return;
    }
    for (let y = 0; y < rows; y++) {
      const floorOn = r() < 0.85;
      for (let x = 0; x < cols; x++) {
        if (!floorOn || r() > p) continue;
        const c = style === 'warm' ? WARM : style === 'cool' || style === 'dense' ? COOL : (r() < 0.5 ? WARM : COOL);
        g.fillStyle = rgb(c, 0.4 + 0.6 * r());
        g.fillRect(x * cw + 4, y * ch + 3, cw - 8, ch - 6);
      }
    }
  });
}
const STYLES = ['warm', 'cool', 'mixed', 'office', 'sparse', 'dense', 'bands', 'led', 'warm', 'office', 'cool', 'mixed'];
const WIN_TEX = STYLES.map((s, i) => windowTex(s, 1000 + i * 17));

const darkRoof = new THREE.MeshStandardMaterial({ color: col('#0b0c12'), roughness: 0.9, metalness: 0.1 });
function glassMat(tex, repX, repY, opts = {}) {
  const t = tex.clone();
  t.repeat.set(repX, repY);
  t.offset.set(Math.floor(rng() * 16) / 16, Math.floor(rng() * 64) / 64);
  return new THREE.MeshStandardMaterial({
    color: opts.color ?? new THREE.Color().setHSL(0.62, 0.25, R(0.035, 0.07)),
    roughness: opts.roughness ?? 0.28, metalness: opts.metalness ?? 0.8,
    emissive: opts.emissive ?? col('#ffffff'), emissiveMap: t, emissiveIntensity: opts.ei ?? R(0.45, 1.0),
    envMapIntensity: opts.env ?? 1.0,
  });
}
const glowMat = (hex, k) => new THREE.MeshBasicMaterial({ color: col(hex, k) });

// ------------------------------------------------------------------ 几何工具
// 放样：rings = [[ [x,y,z], ... ], ...]，每圈点数相同；自动保证法线朝外
function loft(rings, { flat = false, uTile = 50, vTile = 250 } = {}) {
  const n = rings[0].length, pos = [], uv = [], idx = [];
  for (const ring of rings) {
    let per = 0;
    for (let j = 0; j <= n; j++) {
      const p = ring[j % n];
      if (j > 0) { const q = ring[j - 1]; per += Math.hypot(p[0] - q[0], p[2] - q[2]); }
      pos.push(p[0], p[1], p[2]); uv.push(per / uTile, p[1] / vTile);
    }
  }
  for (let i = 0; i < rings.length - 1; i++) for (let j = 0; j < n; j++) {
    const a = i * (n + 1) + j, b = a + 1, c = a + n + 1, d = c + 1;
    idx.push(a, b, d, a, d, c);
  }
  // 朝向：(x,z) 平面里逆时针排列的环，(a,b,d) 的法线朝内，需要翻转
  const mid = rings[Math.floor(rings.length / 2)];
  let area = 0;
  for (let j = 0; j < n; j++) { const p = mid[j], q = mid[(j + 1) % n]; area += p[0] * q[2] - q[0] * p[2]; }
  if (area > 0) for (let k = 0; k < idx.length; k += 3) { const tmp = idx[k + 1]; idx[k + 1] = idx[k + 2]; idx[k + 2] = tmp; }
  let geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geo.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  geo.setIndex(idx);
  if (flat) geo = geo.toNonIndexed();
  geo.computeVertexNormals();
  return geo;
}
// 凸多边形封顶（扇形三角化），up=true 法线朝上
function cap(ring, up = true) {
  const n = ring.length, pos = [];
  const c = ring.reduce((s, p) => [s[0] + p[0] / n, s[1] + p[1] / n, s[2] + p[2] / n], [0, 0, 0]);
  for (let j = 0; j < n; j++) {
    const a = ring[j], b = ring[(j + 1) % n];
    const tri = [c, a, b];
    const nrmY = (a[2] - c[2]) * (b[0] - c[0]) - (a[0] - c[0]) * (b[2] - c[2]);
    if ((nrmY > 0) !== up) { tri[1] = b; tri[2] = a; }
    for (const p of tri) pos.push(p[0], p[1], p[2]);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geo.setAttribute('uv', new THREE.Float32BufferAttribute(new Array(pos.length / 3 * 2).fill(0), 2));
  geo.computeVertexNormals();
  return geo;
}
function rod(a, b, r, mat, seg = 10) {   // 两点间圆柱
  const A = new THREE.Vector3(...a), B = new THREE.Vector3(...b);
  const len = A.distanceTo(B);
  const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, len, seg, 1, true), mat);
  m.position.copy(A).add(B).multiplyScalar(0.5);
  m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), B.clone().sub(A).normalize());
  return m;
}

const beaconsA = [], beaconsB = [];
const beaconMatA = glowMat('#ff2a1a', 6), beaconMatB = glowMat('#ff2a1a', 6);
const beaconGeo = new THREE.SphereGeometry(1.6, 10, 8);
function beacon(parent, x, y, z, phaseB = false) {
  const m = new THREE.Mesh(beaconGeo, phaseB ? beaconMatB : beaconMatA);
  m.position.set(x, y, z); parent.add(m);
  (phaseB ? beaconsB : beaconsA).push(m);
}

// ------------------------------------------------------------------ 东方明珠
function optSphereMat(rows, cols, k = 1) {
  return new THREE.ShaderMaterial({
    fog: true,
    uniforms: THREE.UniformsUtils.merge([THREE.UniformsLib.fog, {
      cA: { value: new THREE.Color(1.0, 0.30, 0.70).multiplyScalar(1.05 * k) },
      cB: { value: new THREE.Color(0.13, 0.015, 0.10) },
      cDot: { value: new THREE.Color(1.0, 0.85, 0.95).multiplyScalar(3.2) },
      rows: { value: rows }, cols: { value: cols },
    }]),
    vertexShader: `varying vec3 vN; varying vec3 vV; varying vec3 vP;
      #include <fog_pars_vertex>
      void main(){ vP = position; vec4 wp = modelMatrix * vec4(position, 1.0);
        vN = normalize(mat3(modelMatrix) * normal); vV = normalize(cameraPosition - wp.xyz);
        vec4 mvPosition = viewMatrix * wp; gl_Position = projectionMatrix * mvPosition;
        #include <fog_vertex>
      }`,
    fragmentShader: `uniform vec3 cA, cB, cDot; uniform float rows, cols;
      varying vec3 vN; varying vec3 vV; varying vec3 vP;
      #include <fog_pars_fragment>
      void main(){
        float ndv = clamp(dot(normalize(vN), normalize(vV)), 0.0, 1.0);
        vec3 base = mix(cB, cA, pow(ndv, 1.25));
        vec3 p = normalize(vP);
        float lat = asin(clamp(p.y, -1.0, 1.0)), lon = atan(p.z, p.x);
        float rf = abs(fract(lat / 3.14159265 * rows) - 0.5);
        float cf = abs(fract(lon / 6.2831853 * cols) - 0.5);
        float dots = smoothstep(0.17, 0.07, rf) * smoothstep(0.22, 0.09, cf);
        float belt = smoothstep(0.05, 0.0, abs(p.y + 0.12));
        vec3 c = base + cDot * dots * (0.35 + 0.65 * ndv) + vec3(1.0, 0.75, 0.9) * belt * 0.9 * ndv;
        c += cA * pow(1.0 - ndv, 3.0) * 0.5;
        gl_FragColor = vec4(c, 1.0);
        #include <fog_fragment>
      }`,
  });
}
function buildOPT() {
  const g = new THREE.Group();
  const up = canvasTex(64, 512, (c, w, h) => {
    const grd = c.createLinearGradient(0, h, 0, 0);
    grd.addColorStop(0, '#ffffff'); grd.addColorStop(0.5, '#a0607a'); grd.addColorStop(1, '#6a3050');
    c.fillStyle = grd; c.fillRect(0, 0, w, h);
    c.fillStyle = 'rgba(255,255,255,0.9)'; c.fillRect(w * 0.45, 0, w * 0.1, h);
  });
  up.wrapS = up.wrapT = THREE.ClampToEdgeWrapping;
  const colMat = new THREE.MeshStandardMaterial({ color: col('#8f6a9e'), roughness: 0.45, metalness: 0.35, emissive: col('#ff6cc8'), emissiveMap: up, emissiveIntensity: 0.9 });
  const darkCol = new THREE.MeshStandardMaterial({ color: col('#4a3a58'), roughness: 0.5, metalness: 0.3, emissive: col('#ff6cc8'), emissiveMap: up, emissiveIntensity: 0.45 });
  const toCam = Math.atan2(CAM0.z - 0, CAM0.x - 0);          // 明珠指向机位的方向
  const colAng = [toCam + Math.PI, toCam + Math.PI / 3, toCam - Math.PI / 3];
  const legAng = [0, 1, 2].map(i => toCam + i * Math.PI * 2 / 3);
  const P = (r, a, y) => [r * Math.cos(a), y, r * Math.sin(a)];
  for (const a of colAng) {
    const m = rod(P(9.5, a, GROUND), P(9.5, a, GROUND + 292), 4.5, a === colAng[0] ? darkCol : colMat, 20);
    g.add(m);
  }
  for (const a of legAng) g.add(rod(P(44, a, GROUND), P(13, a, GROUND + 72), 3.4, colMat, 14));
  for (const y of [40, 230]) for (let k = 0; k < 3; k++) {
    g.add(rod(P(9.5, colAng[k], GROUND + y), P(9.5, colAng[(k + 1) % 3], GROUND + y), 1.2, colMat, 6));
  }
  // 底座
  const base = new THREE.Mesh(new THREE.CylinderGeometry(52, 56, 14, 48), glassMat(WIN_TEX[0], 4, 14 / TEX_H, { ei: 0.5 }));
  base.position.y = GROUND + 7; g.add(base);
  // 球
  const sph = (r, y, x = 0, z = 0, rows = 6, cols = 18, k = 1) => {
    const m = new THREE.Mesh(new THREE.SphereGeometry(r, 64, 40), optSphereMat(rows, cols, k));
    m.position.set(x, GROUND + y, z); g.add(m);
  };
  sph(25, 93, 0, 0, 7, 22);
  const small = [[130, 0], [152, 1], [174, 2], [196, 0], [218, 1]];
  for (const [y, k] of small) { const p = P(9.5, colAng[k], 0); sph(6, y, p[0], p[2], 3, 8, 0.9); }
  sph(22.5, 272, 0, 0, 6, 20);
  g.add(rod([0, GROUND + 293, 0], [0, GROUND + 337, 0], 4.6, colMat, 20));
  sph(8, 343, 0, 0, 3, 10, 1.1);
  // 天线
  const mastMat = new THREE.MeshStandardMaterial({ color: col('#d8d0e8'), roughness: 0.4, metalness: 0.5, emissive: col('#f4e8ff'), emissiveIntensity: 0.9 });
  const mast = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 2.8, 117, 16), mastMat);
  mast.position.y = GROUND + 351 + 58.5; g.add(mast);
  for (const y of [368, 392, 418, 440]) {
    const ring = new THREE.Mesh(new THREE.CylinderGeometry(3.6, 3.6, 2.2, 16), glowMat('#fff2ff', 2.4));
    ring.position.y = GROUND + y; g.add(ring);
  }
  beacon(g, 0, GROUND + 469, 0);
  return g;
}

// ------------------------------------------------------------------ 金茂大厦（宝塔式逐层收分 + 金色冠顶）
function buildJM() {
  const g = new THREE.Group();
  const tex = canvasTex(256, 512, (c, w, h) => {
    c.fillStyle = '#000'; c.fillRect(0, 0, w, h);
    for (let x = 0; x < w; x += 16) { c.fillStyle = 'rgba(255,214,150,0.85)'; c.fillRect(x + 7, 0, 2, h); }
    const r = mulberry32(77);
    for (let y = 0; y < h; y += 16) for (let x = 0; x < w; x += 16) if (r() < 0.35) {
      c.fillStyle = `rgba(255,200,130,${0.25 + 0.45 * r()})`; c.fillRect(x + 1, y + 4, 5, 8); c.fillRect(x + 10, y + 4, 5, 8);
    }
  });
  const eave = glowMat('#ffd9a0', 3.2);
  let h = GROUND, th = 46;
  for (let i = 0; i < 13; i++) {
    const wb = 54 - i * 1.9, wt = wb - 2.8;
    const k = 1 / (2 * Math.cos(Math.PI / 8));
    const geo = new THREE.CylinderGeometry(wt * k, wb * k, th, 8, 1, true);
    geo.rotateY(Math.PI / 8); geo.translate(0, h + th / 2, 0);
    const m = new THREE.Mesh(geo, glassMat(tex, 8, th / 40, { color: col('#2a2216'), metalness: 0.85, roughness: 0.3, emissive: col('#ffd08a'), ei: 1.0 + 0.03 * i }));
    g.add(m);
    const e = new THREE.Mesh(new THREE.CylinderGeometry(wb * k * 1.035, wb * k * 1.035, 1.4, 8), eave);
    e.geometry.rotateY(Math.PI / 8); e.position.y = h + 0.7; g.add(e);
    h += th; th *= 0.885;
  }
  const crownMat = new THREE.MeshStandardMaterial({ color: col('#3a2c18'), emissive: col('#ffe0a8'), emissiveIntensity: 2.0, roughness: 0.4, metalness: 0.6 });
  for (const [w, hh] of [[28, 11], [22, 10], [16, 9], [11, 8]]) {
    const k = 1 / (2 * Math.cos(Math.PI / 8));
    const geo = new THREE.CylinderGeometry((w - 2) * k, w * k, hh, 8);
    geo.rotateY(Math.PI / 8); geo.translate(0, h + hh / 2, 0);
    g.add(new THREE.Mesh(geo, crownMat));
    const e = new THREE.Mesh(new THREE.CylinderGeometry(w * k * 1.06, w * k * 1.06, 1.0, 8), glowMat('#fff0d2', 4));
    e.geometry.rotateY(Math.PI / 8); e.position.y = h + 0.5; g.add(e);
    h += hh;
  }
  const spire = new THREE.Mesh(new THREE.ConeGeometry(2.2, GROUND + 421 - h, 12), new THREE.MeshStandardMaterial({ color: col('#e8d8b8'), emissive: col('#fff0d0'), emissiveIntensity: 2.2 }));
  spire.position.y = h + (GROUND + 421 - h) / 2; g.add(spire);
  beacon(g, 0, GROUND + 422, 0, true);
  return g;
}

// ------------------------------------------------------------------ 环球金融中心（方柱被两道弧面削成顶部一条线 + 倒梯形洞口）
function buildSWFC() {
  const g = new THREE.Group();
  const HT = 492;
  const e = y => Math.min(40.5, 4.5 + 36 * (1 - Math.pow(y / HT, 1.7)));
  const hex = y => { const ee = e(y); return [[0, 41], [ee, 41 - ee], [ee, -(41 - ee)], [0, -41], [-ee, -(41 - ee)], [-ee, 41 - ee]]; };
  const ap = y => 11 + (25 - 11) * (y - 442) / (478 - 442);   // 洞口半宽
  const toRing = (pts, y) => pts.map(([x, z]) => [x, GROUND + y, z]);
  const tex = WIN_TEX[4];
  const body = glassMat(tex, 1, 1, { color: col('#0e1626'), metalness: 0.85, roughness: 0.22, ei: 0.85 });
  const rings = [];
  for (let k = 0; k <= 60; k++) { const y = 442 * k / 60; rings.push(toRing(hex(y), y)); }
  g.add(new THREE.Mesh(loft(rings, { flat: true, uTile: TEX_W, vTile: TEX_H }), body));
  g.add(new THREE.Mesh(cap(rings[rings.length - 1], true), darkRoof));
  for (const s of [1, -1]) {       // 洞口两侧的立柱
    const pr = [];
    for (let k = 0; k <= 10; k++) {
      const y = 442 + 36 * k / 10, ee = e(y), a = ap(y);
      const pts = [[-ee, s * a], [ee, s * a], [ee, s * (41 - ee)], [0, s * 41], [-ee, s * (41 - ee)]];
      pr.push(toRing(s > 0 ? pts : pts.slice().reverse(), y));
    }
    g.add(new THREE.Mesh(loft(pr, { flat: true, uTile: TEX_W, vTile: TEX_H }), body));
  }
  const beam = [];
  for (let k = 0; k <= 4; k++) { const y = 478 + 14 * k / 4; beam.push(toRing(hex(y), y)); }
  g.add(new THREE.Mesh(loft(beam, { flat: true, uTile: TEX_W, vTile: TEX_H }), body));
  g.add(new THREE.Mesh(cap(beam[0], false), darkRoof));
  g.add(new THREE.Mesh(cap(beam[beam.length - 1], true), darkRoof));
  // 灯带：南北两条竖棱、洞口描边、顶边
  const led = glowMat('#cfe6ff', 3.2), ledBlue = glowMat('#6fb8ff', 3.6);
  for (const s of [1, -1]) g.add(rod([0, GROUND, s * 41], [0, GROUND + HT, s * 41], 0.9, led, 6));
  for (const sx of [1, -1]) {
    const x = sx * (e(460) + 0.4);
    const pts = [[x, 442, -11], [x, 442, 11], [x, 478, 25], [x, 478, -25]];
    for (let i = 0; i < 4; i++) { const a = pts[i], b = pts[(i + 1) % 4]; g.add(rod([a[0], GROUND + a[1], a[2]], [b[0], GROUND + b[1], b[2]], 0.8, ledBlue, 6)); }
    g.add(rod([x, GROUND + HT, -41], [x, GROUND + HT, 41], 0.7, led, 6));
  }
  beacon(g, 0, GROUND + HT + 2, 39); beacon(g, 0, GROUND + HT + 2, -39);
  return g;
}

// ------------------------------------------------------------------ 上海中心（圆角三角形平面，扭转 120°，收分，斜切冠顶 + 缺口灯带）
function buildST() {
  const g = new THREE.Group();
  const HT = 632, BODY = 586, N = 120;
  const rot0 = 2.2;
  const sec = (y, yTop = null) => {
    const f = y / HT, scale = 1 - 0.46 * Math.pow(f, 1.25), Rr = 41 * scale, rot = rot0 + (2 * Math.PI / 3) * f;
    const pts = [];
    for (let k = 0; k < N; k++) {
      const a = k / N * Math.PI * 2;
      let r = Rr * (1 + 0.115 * Math.cos(3 * a));
      const da = Math.atan2(Math.sin(a), Math.cos(a));
      r *= 1 - 0.085 * Math.exp(-(da * da) / (2 * 0.05 * 0.05));
      const yy = yTop ? yTop(a) : y;
      pts.push([r * Math.cos(a + rot), GROUND + yy, r * Math.sin(a + rot)]);
    }
    return pts;
  };
  // 立面：密集冷色窗 + 每个分区的亮灯带
  const tex = canvasTex(512, 1024, (c, w, h) => {
    c.fillStyle = '#000'; c.fillRect(0, 0, w, h);
    const r = mulberry32(5);
    for (let y = 0; y < 64; y++) for (let x = 0; x < 16; x++) if (r() < 0.5) {
      c.fillStyle = rgb(COOL, 0.25 + 0.35 * r()); c.fillRect(x * 32 + 3, y * 16 + 4, 26, 8);
    }
  });
  const bodyMat = glassMat(tex, 1, 1, { color: col('#1a2a3c'), metalness: 0.75, roughness: 0.16, ei: 0.75, env: 1.3 });
  const rings = [];
  for (let k = 0; k <= 70; k++) rings.push(sec(BODY * k / 70));
  g.add(new THREE.Mesh(loft(rings, { uTile: TEX_W, vTile: TEX_H }), bodyMat));
  const aPeak = 0.9;
  const topH = a => 592 + 40 * (0.5 + 0.5 * Math.cos(a - aPeak));
  const crown = [];
  for (let k = 0; k <= 6; k++) crown.push(sec(BODY + k).map((p, j) => {
    const a = j / N * Math.PI * 2, yt = topH(a), s = k / 6;
    return [p[0], GROUND + BODY + (yt - BODY) * s, p[2]];
  }));
  const crownMat = new THREE.MeshStandardMaterial({ color: col('#20324a'), emissive: col('#d8e6ff'), emissiveIntensity: 0.9, roughness: 0.3, metalness: 0.6, side: THREE.DoubleSide });
  g.add(new THREE.Mesh(loft(crown, { uTile: TEX_W, vTile: TEX_H }), crownMat));
  // 分区灯带
  const band = glowMat('#e4eeff', 2.6);
  for (let z = 1; z <= 8; z++) {
    const y = BODY * z / 9;
    const ring = sec(y).map(p => new THREE.Vector3(p[0] * 1.004, p[1], p[2] * 1.004));
    const curve = new THREE.CatmullRomCurve3(ring, true);
    g.add(new THREE.Mesh(new THREE.TubeGeometry(curve, 240, 0.7, 4, true), band));
  }
  // 缺口灯带（随扭转盘旋上升）
  const spine = [];
  for (let k = 0; k <= 80; k++) {
    const y = BODY * k / 80, f = y / HT, scale = 1 - 0.46 * Math.pow(f, 1.25), Rr = 41 * scale * 1.115, rot = rot0 + (2 * Math.PI / 3) * f + 0.11;
    spine.push(new THREE.Vector3(Rr * Math.cos(rot), GROUND + y, Rr * Math.sin(rot)));
  }
  g.add(new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(spine), 200, 0.8, 5), glowMat('#ffffff', 3)));
  const pk = sec(BODY)[Math.round(aPeak / (Math.PI * 2) * N)];
  beacon(g, pk[0] * 0.9, GROUND + HT + 1, pk[2] * 0.9, true);
  return g;
}

// ------------------------------------------------------------------ 普通塔楼
const placed = [];
function free(x, z, r) { for (const p of placed) if (Math.hypot(p.x - x, p.z - z) < p.r + r + 6) return false; return true; }
const LANDMARKS = [
  { x: 0, z: 0, r: 75, top: 468 }, { x: 635, z: 493, r: 45, top: 421 },
  { x: 790, z: 600, r: 55, top: 492 }, { x: 598, z: 684, r: 50, top: 632 },
];
for (const L of LANDMARKS) placed.push({ x: L.x, z: L.z, r: L.r });
const bearing = (x, z) => Math.atan2(-(z - CAM0.z), x - CAM0.x);
const distTo = (x, z) => Math.hypot(x - CAM0.x, z - CAM0.z);

function tower(x, z, w, d, h, kind) {
  const g = new THREE.Group();
  const tex = pick(WIN_TEX);
  let body;
  const rot = pick([0, 0, 0.12, -0.2, Math.PI / 4, 0.35]);
  if (kind === 'cyl') {
    const r = w / 2;
    body = new THREE.Mesh(new THREE.CylinderGeometry(r, r, h, 28, 1), [glassMat(tex, Math.PI * w / TEX_W, h / TEX_H), darkRoof, darkRoof]);
  } else if (kind === 'oct') {
    const k = 1 / (2 * Math.cos(Math.PI / 8));
    body = new THREE.Mesh(new THREE.CylinderGeometry(w * k * 0.92, w * k, h, 8, 1), [glassMat(tex, 3.3 * w / TEX_W, h / TEX_H), darkRoof, darkRoof]);
    body.geometry.rotateY(Math.PI / 8);
  } else {
    const geo = new THREE.BoxGeometry(w, h, d);
    if (kind === 'slant') {
      const p = geo.attributes.position, s = R(0.25, 0.6) * h / Math.max(w, 30) * 0.25;
      for (let i = 0; i < p.count; i++) if (p.getY(i) > 0) p.setY(i, p.getY(i) - (p.getX(i) / w + 0.5) * s * w);
      geo.computeVertexNormals();
    }
    const m = glassMat(tex, w / TEX_W, h / TEX_H);
    body = new THREE.Mesh(geo, [m, m, darkRoof, darkRoof, m, m]);
  }
  body.position.y = GROUND + h / 2;
  body.rotation.y = rot;
  g.add(body);
  if (kind === 'step') {
    const top = new THREE.Mesh(new THREE.BoxGeometry(w * 0.62, h * 0.16, d * 0.62), [glassMat(tex, w * 0.62 / TEX_W, h * 0.16 / TEX_H), null, darkRoof, darkRoof, null, null].map(m => m || glassMat(tex, w * 0.62 / TEX_W, h * 0.16 / TEX_H)));
    top.position.y = GROUND + h + h * 0.08; top.rotation.y = rot; g.add(top);
  }
  const accent = pick(['#bfe4ff', '#ff7ad0', '#ffd08a', '#ffffff', '#8f8cff', '#6fe0ff']);
  if (rng() < 0.28 && kind !== 'cyl') {          // 棱线灯
    const m = glowMat(accent, 2.4);
    for (const [sx, sz] of [[1, 1], [1, -1], [-1, 1], [-1, -1]]) {
      const c = new THREE.Vector3(sx * w / 2, 0, sz * d / 2).applyAxisAngle(new THREE.Vector3(0, 1, 0), rot);
      g.add(rod([c.x, GROUND, c.z], [c.x, GROUND + h, c.z], 0.55, m, 4));
    }
  }
  if (rng() < 0.3) {                              // 顶部灯箱
    const cb = new THREE.Mesh(new THREE.BoxGeometry(w * 0.7, Math.max(4, h * 0.03), (kind === 'cyl' ? w : d) * 0.7), glowMat(accent, 1.8));
    cb.position.y = GROUND + h + Math.max(4, h * 0.03) / 2 + (kind === 'step' ? h * 0.16 : 0); cb.rotation.y = rot; g.add(cb);
  }
  const topY = GROUND + h + (kind === 'step' ? h * 0.16 : 0);
  if (h > 150 && rng() < 0.55) {
    const sh = R(12, 36);
    g.add(rod([0, topY, 0], [0, topY + sh, 0], 0.7, new THREE.MeshStandardMaterial({ color: col('#666670'), emissive: col('#ffffff'), emissiveIntensity: 0.3 }), 6));
    beacon(g, 0, topY + sh + 1, 0, rng() < 0.5);
  } else if (h > 120 && rng() < 0.5) beacon(g, 0, topY + 1, 0, rng() < 0.5);
  g.position.set(x, 0, z);
  scene.add(g);
}

function populate(n, xr, zr, hr, wr, tries = 40) {
  for (let i = 0; i < n; i++) for (let t = 0; t < tries; t++) {
    const x = R(...xr), z = R(...zr), w = R(...wr), d = w * R(0.7, 1.3), r = Math.max(w, d) * 0.72;
    if (!free(x, z, r)) continue;
    let h = R(...hr) * (rng() < 0.08 ? 1.25 : 1);
    // 不挡住地标：在地标视线前方的楼，视高压到地标的 40% 以下
    const az = bearing(x, z), dist = distTo(x, z), half = Math.atan2(r, dist);
    for (const L of LANDMARKS) {
      const azL = bearing(L.x, L.z), dL = distTo(L.x, L.z), halfL = Math.atan2(L.r * 0.8, dL);
      if (dist < dL && Math.abs(az - azL) < half + halfL) h = Math.min(h, 0.4 * L.top * dist / dL);
    }
    if (h < 25) continue;
    const kind = pick(['box', 'box', 'box', 'slant', 'step', 'oct', 'cyl']);
    tower(x, z, w, d, h, kind);
    placed.push({ x, z, r });
    break;
  }
}

// ------------------------------------------------------------------ LED 幕墙（江边大楼面向外滩的灯光秀）
const ledWalls = [];
function ledTower(x, z, w, d, h) {
  const m = glassMat(pick(WIN_TEX), w / TEX_W, h / TEX_H);
  const b = new THREE.Mesh(new THREE.BoxGeometry(d, h, w), [m, m, darkRoof, darkRoof, m, m]);
  b.position.set(x, GROUND + h / 2, z); scene.add(b);
  placed.push({ x, z, r: Math.max(w, d) * 0.72 });
  ledWall(x - d / 2 - 0.3, z, w * 0.92, h * 0.78, GROUND + h * 0.12);
}
function ledWall(x, z, w, h, yb) {
  const m = new THREE.ShaderMaterial({
    fog: true,
    uniforms: THREE.UniformsUtils.merge([THREE.UniformsLib.fog, { time: { value: 0 }, seed: { value: rng() * 10 } }]),
    vertexShader: `varying vec2 vUv;
      #include <fog_pars_vertex>
      void main(){ vUv = uv; vec4 mvPosition = modelViewMatrix * vec4(position, 1.0); gl_Position = projectionMatrix * mvPosition;
      #include <fog_vertex>
      }`,
    fragmentShader: `uniform float time, seed; varying vec2 vUv;
      #include <fog_pars_fragment>
      void main(){
        float w = sin(vUv.y * 7.0 - time * 1.1 + seed + sin(vUv.x * 5.0 + time * 0.7) * 0.9) * 0.5 + 0.5;
        vec3 c = mix(vec3(1.0, 0.25, 0.65), vec3(0.15, 0.55, 1.0), w);
        c = mix(c, vec3(1.0, 0.85, 0.5), smoothstep(0.85, 1.0, sin(vUv.y * 3.0 + time * 0.5 + seed) * 0.5 + 0.5) * 0.6);
        vec2 gg = fract(vUv * vec2(36.0, 110.0));
        c *= (smoothstep(0.0, 0.2, gg.x) * smoothstep(0.0, 0.25, gg.y)) * 0.75 + 0.25;
        gl_FragColor = vec4(c * 0.8, 1.0);
        #include <fog_fragment>
      }`,
  });
  const p = new THREE.Mesh(new THREE.PlaneGeometry(w, h), m);
  p.position.set(x, yb + h / 2, z); p.rotation.y = -Math.PI / 2;
  scene.add(p); ledWalls.push(m);
}

// ------------------------------------------------------------------ 浦东江岸
function buildBank() {
  const stone = new THREE.MeshStandardMaterial({ color: col('#1c1d24'), roughness: 0.9 });
  const wall = new THREE.Mesh(new THREE.BoxGeometry(6, GROUND + 0.6, 4200), stone);
  wall.position.set(-153, (GROUND + 0.6) / 2, 300); scene.add(wall);
  const land = new THREE.Mesh(new THREE.PlaneGeometry(9000, 9000), new THREE.MeshStandardMaterial({ color: col('#0a0b10'), roughness: 1 }));
  land.rotation.x = -Math.PI / 2; land.position.set(-150 + 4500, GROUND, 300); scene.add(land);
  // 护栏灯、亲水平台灯带
  const n = 900, dummy = new THREE.Object3D();
  const lights = new THREE.InstancedMesh(new THREE.SphereGeometry(0.35, 8, 6), glowMat('#ffd9a8', 3.5), n);
  for (let i = 0; i < n; i++) { dummy.position.set(-150.5, GROUND + 1.2, -1500 + i * 4.2); dummy.updateMatrix(); lights.setMatrixAt(i, dummy.matrix); }
  scene.add(lights);
  const strip = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.35, 4200), glowMat('#9cc0ff', 2.2));
  strip.position.set(-156.3, 0.9, 300); scene.add(strip);
  // 行道树（顶上积了雪）+ 树上灯串
  const tn = 330;
  const treeMat = new THREE.MeshStandardMaterial({ color: col('#1a201e'), roughness: 1, emissive: col('#000000') });
  treeMat.onBeforeCompile = sh => {
    sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nvarying float vUpN;')
      .replace('#include <beginnormal_vertex>', '#include <beginnormal_vertex>\nvUpN = normal.y;');
    sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying float vUpN;')
      .replace('#include <color_fragment>', '#include <color_fragment>\ndiffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.75,0.78,0.86), smoothstep(0.35, 0.8, vUpN));');
  };
  const trees = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1, 2), treeMat, tn);
  const fairy = [];
  for (let i = 0; i < tn; i++) {
    const z = -1400 + i * 9.5 + R(-2, 2), x = R(-140, -112), s = R(3.5, 5.5);
    dummy.position.set(x, GROUND + 3 + s, z); dummy.scale.set(s, s * 0.85, s); dummy.updateMatrix(); trees.setMatrixAt(i, dummy.matrix);
    if (rng() < 0.5) for (let k = 0; k < 10; k++) {
      const a = R(0, Math.PI * 2), b = R(-0.6, 0.9);
      fairy.push([x + Math.cos(a) * s * 1.02 * Math.cos(b), GROUND + 3 + s + Math.sin(b) * s * 0.85, z + Math.sin(a) * s * 1.02 * Math.cos(b)]);
    }
  }
  scene.add(trees);
  const fm = new THREE.InstancedMesh(new THREE.SphereGeometry(0.22, 6, 4), glowMat('#ffcf7a', 5), fairy.length);
  fairy.forEach((p, i) => { dummy.position.set(...p); dummy.scale.set(1, 1, 1); dummy.updateMatrix(); fm.setMatrixAt(i, dummy.matrix); });
  scene.add(fm);
}

// ------------------------------------------------------------------ 江面
const WaterShader = {
  name: 'WaterShader',
  uniforms: { color: { value: null }, tDiffuse: { value: null }, textureMatrix: { value: null }, time: { value: 0 },
    camPos: { value: new THREE.Vector3() }, fogC: { value: FOG_COLOR } },
  vertexShader: `uniform mat4 textureMatrix; varying vec4 vUv; varying vec3 vW;
    void main(){ vUv = textureMatrix * vec4(position, 1.0); vec4 wp = modelMatrix * vec4(position, 1.0); vW = wp.xyz;
      gl_Position = projectionMatrix * viewMatrix * wp; }`,
  fragmentShader: `uniform vec3 color; uniform sampler2D tDiffuse; uniform float time; uniform vec3 camPos; uniform vec3 fogC;
    varying vec4 vUv; varying vec3 vW;
    ${NOISE_GLSL}
    void main(){
      float d = length(vW.xz - camPos.xz);
      vec2 p = vW.xz * vec2(0.045, 0.16);
      float n = noise(p + vec2(time * 0.35, -time * 0.18)) + 0.6 * noise(p * 2.7 + vec2(-time * 0.5, time * 0.3)) + 0.3 * noise(p * 7.0 + time * 0.8);
      vec2 uv = vUv.xy / vUv.w;
      float amp = clamp(70.0 / d, 0.08, 1.0);
      uv.x += (n - 0.95) * 0.022 * amp;
      vec3 acc = vec3(0.0); float ws = 0.0;
      for (int i = 0; i < 12; i++){ float o = float(i) / 11.0; float w = 1.0 - 0.7 * o;
        acc += texture2D(tDiffuse, uv + vec2((noise(vec2(o * 9.0, vW.z * 0.05)) - 0.5) * 0.004, (o - 0.25) * 0.05 * (0.4 + amp))).rgb * w; ws += w; }
      vec3 refl = acc / ws;
      float glint = smoothstep(1.15, 1.35, n) * 0.25;
      vec3 c = color * (0.8 + 0.4 * n) + refl * (0.38 + 0.22 * smoothstep(80.0, 400.0, d)) * (0.85 + glint);
      c = mix(c, fogC * 0.6, 1.0 - exp(-pow(d * 0.0006, 2.0)));
      gl_FragColor = vec4(c, 1.0);
    }`,
};
const water = new Reflector(new THREE.PlaneGeometry(8000, 8000), {
  color: col('#0c0d18'), textureWidth: Math.round(W * 0.5), textureHeight: Math.round(H * 0.5), clipBias: 0.002, shader: WaterShader, multisample: 0,
});
water.rotation.x = -Math.PI / 2;
water.position.set(-400, 0, 300);
scene.add(water);

// ------------------------------------------------------------------ 游船
const boat = new THREE.Group();
{
  const hg = new THREE.BoxGeometry(11, 3.2, 60, 1, 1, 12);
  const hp = hg.attributes.position;
  for (let i = 0; i < hp.count; i++) { const z = hp.getZ(i); if (z > 20) hp.setX(i, hp.getX(i) * (1 - 0.9 * (z - 20) / 10)); }
  hg.computeVertexNormals();
  const hull = new THREE.Mesh(hg, new THREE.MeshStandardMaterial({ color: col('#121520'), roughness: 0.6 }));
  hull.position.set(0, 1.6, 0); boat.add(hull);
  const deckTex = canvasTex(256, 32, (c, w, h) => { c.fillStyle = '#000'; c.fillRect(0, 0, w, h); for (let x = 2; x < w; x += 9) { c.fillStyle = 'rgb(255,214,150)'; c.fillRect(x, 8, 6, 16); } });
  const deck1 = new THREE.Mesh(new THREE.BoxGeometry(10, 3.4, 44), new THREE.MeshStandardMaterial({ color: col('#262838'), emissive: col('#ffffff'), emissiveMap: deckTex, emissiveIntensity: 1.6 }));
  deck1.position.set(0, 4.9, 2); boat.add(deck1);
  const deckTex2 = canvasTex(256, 32, (c, w, h) => { c.fillStyle = '#000'; c.fillRect(0, 0, w, h); for (let x = 2; x < w; x += 8) { c.fillStyle = 'rgb(232,238,255)'; c.fillRect(x, 9, 5, 14); } });
  const deck2 = new THREE.Mesh(new THREE.BoxGeometry(8.5, 3, 30), new THREE.MeshStandardMaterial({ color: col('#2c2c40'), emissive: col('#ffffff'), emissiveMap: deckTex2, emissiveIntensity: 2.0 }));
  deck2.position.set(0, 8.1, 4); boat.add(deck2);
  for (const [y, w, l, z, c] of [[3.25, 11.2, 52, 0, '#ffcf88'], [6.7, 10.2, 44.4, 2, '#ff6ac8'], [9.7, 8.7, 30.4, 4, '#6fe2ff']]) {
    for (const s of [1, -1]) boat.add(rod([s * w / 2, y, z - l / 2], [s * w / 2, y, z + l / 2], 0.16, glowMat(c, 4), 4));
  }
  const top = new THREE.Mesh(new THREE.SphereGeometry(0.5, 8, 6), glowMat('#ffffff', 8)); top.position.set(0, 11.5, -10); boat.add(top);
  boat.rotation.y = 0;
  scene.add(boat);
}

// ------------------------------------------------------------------ 近景：外滩江堤护墙 + 墙顶积雪（层 1：不进倒影）
const PARA_X = CAM0.x + 1.0;  // 护墙近边
const PARA_TOP = 7.6;
{
  const gran = canvasTex(512, 512, (c, w, h) => {
    const r = mulberry32(9);
    c.fillStyle = '#5a5a62'; c.fillRect(0, 0, w, h);
    for (let i = 0; i < 14000; i++) { const v = 60 + r() * 80; c.fillStyle = `rgb(${v},${v},${v + 6})`; c.fillRect(r() * w, r() * h, 2, 2); }
    c.fillStyle = 'rgba(20,20,24,0.8)'; c.fillRect(0, 0, 3, h);
  });
  gran.repeat.set(1, 60);
  const para = new THREE.Mesh(new THREE.BoxGeometry(0.95, 1.6, 400), new THREE.MeshStandardMaterial({ map: gran, roughness: 0.85, metalness: 0.05, color: col('#c8c4d4'), emissive: col('#3a3646'), emissiveIntensity: 1.0 }));
  para.position.set(PARA_X + 0.475, PARA_TOP - 0.8, CAM0.z);
  para.layers.set(1); scene.add(para);
}
const lampPos = new THREE.Vector3(CAM0.x + 0.6, 11.0, CAM0.z - 14);
const lamp = new THREE.PointLight(col('#ffb26a'), 7, 40, 2);
lamp.position.copy(lampPos); lamp.layers.enableAll(); scene.add(lamp);
const snowCapMat = new THREE.ShaderMaterial({
  transparent: true, fog: true,
  uniforms: THREE.UniformsUtils.merge([THREE.UniformsLib.fog, { thick: { value: 0.02 }, cover: { value: 0.3 }, time: { value: 0 }, lamp: { value: lampPos },
    origin: { value: new THREE.Vector2(PARA_X, CAM0.z) } }]),
  vertexShader: `uniform float thick; uniform vec2 origin; varying vec3 vW; varying vec2 vQ;
    ${NOISE_GLSL}
    #include <fog_pars_vertex>
    void main(){ vec4 wp = modelMatrix * vec4(position, 1.0);
      vec2 q = wp.xz - origin;                       // 局部坐标，避免大数 sin 精度问题
      float u = uv.x; float prof = sqrt(max(0.0, 1.0 - pow(2.0 * u - 1.0, 2.0)));
      float n = fbm(q * vec2(4.0, 1.3)) + 0.25 * noise(q * 22.0);
      wp.y += thick * (0.3 + 0.7 * prof) * (0.45 + 0.9 * n);
      vW = wp.xyz; vQ = q;
      vec4 mvPosition = viewMatrix * wp; gl_Position = projectionMatrix * mvPosition;
      #include <fog_vertex>
    }`,
  fragmentShader: `uniform float cover, time; uniform vec3 lamp; varying vec3 vW; varying vec2 vQ;
    ${NOISE_GLSL}
    #include <fog_pars_fragment>
    void main(){
      vec2 rq = mat2(0.866, 0.5, -0.5, 0.866) * vQ;                       // 转 30°，打破值噪声的方格感
      float vCov = 0.45 * fbm(vQ * vec2(6.0, 2.5) + 7.0) + 0.55 * fbm(rq * 26.0 + 3.0);   // 逐像素：细碎雪粒
      float a = smoothstep(vCov - 0.12, vCov + 0.03, cover);
      if (a < 0.02) discard;
      vec3 nr = normalize(cross(dFdx(vW), dFdy(vW))); if (nr.y < 0.0) nr = -nr;
      float sky = 0.55 + 0.45 * nr.y;                                         // 天光
      float city = clamp(dot(nr, normalize(vec3(1.0, 0.45, 0.15))), 0.0, 1.0);  // 对岸城市光
      vec3 c = vec3(0.30, 0.33, 0.44) * sky + vec3(0.42, 0.30, 0.42) * city * 0.6;
      c *= 0.7 + 0.3 * a;                                                   // 薄雪偏灰
      c *= 0.9 + 0.2 * noise(vQ * 40.0);
      vec3 L = lamp - vW; float ld = length(L);
      float lw = exp(-pow(ld / 12.0, 2.0)) * clamp(dot(nr, L / ld), 0.0, 1.0);
      c += vec3(1.0, 0.6, 0.3) * lw * 0.5;
      vec2 cell = floor(vQ * 70.0);
      float sp = step(0.985, hash(cell)) * smoothstep(0.6, 1.0, sin(time * 2.0 + hash(cell + 3.1) * 40.0));
      c += sp * 1.4;
      gl_FragColor = vec4(c, a);
      #include <fog_fragment>
    }`,
});
{
  const geo = new THREE.PlaneGeometry(0.95, 400, 10, 2400);
  geo.rotateX(-Math.PI / 2);
  const m = new THREE.Mesh(geo, snowCapMat);
  m.position.set(PARA_X + 0.475, PARA_TOP + 0.003, CAM0.z);
  m.layers.set(1); scene.add(m);
}

// ------------------------------------------------------------------ 落雪（层 1）
const SNOW_N = 26000;
const snowMat = new THREE.ShaderMaterial({
  transparent: true, depthWrite: false,
  uniforms: { time: { value: 0 }, density: { value: 0.5 }, pxScale: { value: 1300 * SC }, camPos: { value: CAM0.clone() }, lamp: { value: lampPos },
    fwd: { value: new THREE.Vector3(1, 0, 0) } },
  vertexShader: `attribute vec4 aSeed; attribute float aSize;
    uniform float time, density, pxScale; uniform vec3 camPos, lamp, fwd;
    varying float vA; varying float vWarm; varying float vSoft; varying float vStretch;
    void main(){
      float fall = 0.75 + 0.8 * fract(aSeed.x * 7.13 + aSeed.y * 3.1);
      float s = 0.8 + 150.0 * pow(aSeed.x, 1.7);              // 前向距离
      float wl = 2.0 * (s * 0.44 + 1.0);                      // 视野宽度
      float sway = sin(time * (0.6 + aSeed.z) + aSeed.w * 40.0) * 0.5;
      float l = mod(aSeed.z * wl + time * 1.1 + sway, wl) - wl * 0.5;
      float y0 = camPos.y - s * 0.62 - 1.0, hy = s * 1.55 + 2.0;  // 视野高度（含移轴）
      vec3 right = vec3(-fwd.z, 0.0, fwd.x);
      vec3 p = camPos + fwd * s + right * l;
      p.y = y0 + mod(aSeed.y * hy - time * fall, hy);
      vec4 mv = viewMatrix * vec4(p, 1.0);
      float dist = -mv.z;
      float ps = aSize * pxScale / max(dist, 0.1);
      float streak = clamp(fall * pxScale / max(dist, 0.1) / 60.0 / max(ps, 1.0), 0.0, 1.6);  // 1/60s 快门里的下落距离
      vStretch = 1.0 + streak;
      gl_PointSize = clamp(ps * vStretch, 1.2, 48.0);
      vA = step(aSeed.w, density) * clamp((ps - 0.35) / 1.4, 0.0, 1.0) * smoothstep(1.2, 3.0, dist) * (1.0 - smoothstep(60.0, 140.0, dist) * 0.7);
      vSoft = smoothstep(4.0, 0.8, dist);
      vWarm = exp(-pow(distance(p, lamp) / 10.0, 2.0));
      gl_Position = projectionMatrix * mv;
    }`,
  fragmentShader: `varying float vA; varying float vWarm; varying float vSoft; varying float vStretch;
    void main(){
      float d = length((gl_PointCoord - 0.5) * vec2(vStretch, 1.0)) * 2.0;
      float a = 1.0 - smoothstep(mix(0.35, 0.0, vSoft), 1.0, d);
      vec3 c = mix(vec3(0.86, 0.89, 0.97), vec3(1.0, 0.82, 0.62), vWarm * 0.8) * (1.0 + vWarm * 0.6);
      gl_FragColor = vec4(c, a * vA * mix(0.9, 0.3, vSoft));
    }`,
});
{
  const g = new THREE.BufferGeometry();
  const seed = new Float32Array(SNOW_N * 4), size = new Float32Array(SNOW_N), pos = new Float32Array(SNOW_N * 3);
  const r = mulberry32(31);
  for (let i = 0; i < SNOW_N; i++) {
    for (let k = 0; k < 4; k++) seed[i * 4 + k] = r();
    size[i] = 0.007 + 0.03 * Math.pow(r(), 3.0);
  }
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('aSeed', new THREE.BufferAttribute(seed, 4));
  g.setAttribute('aSize', new THREE.BufferAttribute(size, 1));
  const pts = new THREE.Points(g, snowMat);
  pts.frustumCulled = false; pts.layers.set(1); pts.renderOrder = 10;
  scene.add(pts);
}

// ------------------------------------------------------------------ 组装
scene.add(buildOPT());
const jm = buildJM(); jm.position.set(635, 0, 493); scene.add(jm);
const swfc = buildSWFC(); swfc.position.set(790, 0, 600);
swfc.rotation.y = -Math.atan2(CAM0.z - 600, CAM0.x - 790) + Math.PI + 0.18;
scene.add(swfc);
const st = buildST(); st.position.set(598, 0, 684); scene.add(st);
buildBank();
ledTower(-55, 125, 38, 28, 115);
ledTower(300, 262, 40, 30, 150);
populate(150, [-110, 1450], [-320, 1350], [70, 200], [26, 56]);
populate(110, [1450, 3600], [-900, 2400], [50, 170], [26, 60]);
populate(70, [250, 3400], [-1900, -320], [40, 140], [24, 52]);
populate(40, [-110, 120], [-300, 1300], [50, 160], [30, 60]);   // 江边一排

// ------------------------------------------------------------------ 渲染
const target = new THREE.WebGLRenderTarget(W, H, { type: THREE.HalfFloatType, samples: 4 });
const composer = new EffectComposer(renderer, target);
composer.setPixelRatio(1); composer.setSize(W, H);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(W, H), 0.7, 0.5, 0.9);
composer.addPass(bloom);
composer.addPass(new OutputPass());

function setCamera(t) {
  const u = t / DUR;
  camera.position.set(CAM0.x, CAM0.y + 0.03 * Math.sin(t * 1.3), CAM0.z - 10 * u);
  const az = THREE.MathUtils.degToRad(AZ0 + 0.5 * u);
  camera.lookAt(camera.position.x + Math.cos(az) * 100, camera.position.y, camera.position.z - Math.sin(az) * 100);
  const f = FOCAL0 + (FOCAL1 - FOCAL0) * smooth(0, DUR, t);
  camera.fov = THREE.MathUtils.radToDeg(2 * Math.atan(960 / f));   // f 以 1080 宽计
  camera.aspect = W / H;
  camera.updateProjectionMatrix();
  camera.projectionMatrix.elements[9] = (HORIZON_PX - 960) / 960;   // 移轴：竖线保持竖直，地平线压到 1180
  camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();
  sky.position.copy(camera.position);
}

window.renderAt = function (t) {
  setCamera(t);
  skyMat.uniforms.time.value = t;
  water.material.uniforms.time.value = t;
  water.material.uniforms.camPos.value.copy(camera.position);
  snowMat.uniforms.time.value = t;
  snowMat.uniforms.camPos.value.copy(camera.position);
  camera.getWorldDirection(snowMat.uniforms.fwd.value);
  snowMat.uniforms.pxScale.value = (FOCAL0 + (FOCAL1 - FOCAL0) * smooth(0, DUR, t)) * SC;
  snowMat.uniforms.density.value = 0.42 + 0.4 * smooth(8.2, 9.6, t) + 0.18 * smooth(14, 16, t);
  snowCapMat.uniforms.time.value = t;
  snowCapMat.uniforms.cover.value = 0.16 + 0.9 * smooth(0.5, 17, t);
  snowCapMat.uniforms.thick.value = 0.012 + 0.05 * smooth(2, 14, t) + 0.1 * smooth(14, 24.5, t);
  for (const m of ledWalls) m.uniforms.time.value = t;
  const ph = (t * 0.75) % 1;
  beaconMatA.color.copy(col('#ff2a1a', ph < 0.35 ? 7 : 0.15));
  const phb = (t * 0.75 + 0.5) % 1;
  beaconMatB.color.copy(col('#ff2a1a', phb < 0.35 ? 7 : 0.15));
  boat.position.set(-395, 0, 30 + 3.6 * t);
  composer.render();
  return renderer.domElement.toDataURL('image/jpeg', 0.93);
};
window.sceneReady = true;
