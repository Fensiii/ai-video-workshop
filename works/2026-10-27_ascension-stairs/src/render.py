"""登神长阶：侧面剪影登阶，3 秒 1920x1080 30fps。
用法: python render.py OUT_DIR [t1 t2 ...]   (给 t 只渲染这些时刻的静帧)
"""
import sys, os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from multiprocessing import Pool

W, H = 1920, 1080
FPS, DUR = 30, 3.0
SS = 2                      # 剪影超采样倍数
D, SH = 50.0, 40.0          # 台阶进深 / 高度（世界单位）
RATE = 2.6                  # 每秒登几级
THIGH, SHIN = 72.0, 70.0
LEG = THIGH + SHIN
ANCHOR = np.array([0.36 * W, 0.66 * H])   # 人物胯部固定在屏幕的位置

rng = np.random.default_rng(7)

def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)

# ---------- 云层噪声（预计算） ----------
def fbm(h, w, octaves=5, seed=1):
    r = np.random.default_rng(seed)
    out = np.zeros((h, w))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        gh, gw = 3 * 2 ** o + 1, 6 * 2 ** o + 1
        g = r.random((gh, gw))
        img = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        out += amp * np.asarray(img, np.float64) / 255
        tot += amp
        amp *= 0.5
    return out / tot
CLOUD = fbm(H, W * 2, seed=3)
CLOUD2 = fbm(H, W * 2, seed=11)

YY, XX = np.mgrid[0:H, 0:W].astype(np.float64)

# ---------- 世界/相机 ----------
def stair_y(x):           # 台阶踏面中心连线（世界坐标，y 向上）
    return SH * (x / D + 0.5)

def pose(t):
    u = t * RATE
    hx = (u + 1) * D
    bob = 3.0 * math.cos(2 * math.pi * u)
    hy = stair_y(hx) + 0.8 * LEG + bob
    feet, phases = [], []
    for off in (0.0, 1.0):
        v = (u - off) / 2
        n = math.floor(v)
        p = v - n
        s0 = 2 * n + off
        if p < 0.5:
            s = ease(p * 2)
            k = s0 + 2 * s
            fx = (k + 0.5) * D
            fy = (k + 1) * SH + 38 * math.sin(math.pi * s)
            phases.append(s)
        else:
            k = s0 + 2
            fx, fy = (k + 0.5) * D, (k + 1) * SH
            phases.append(None)
        feet.append(np.array([fx, fy]))
    return np.array([hx, hy]), feet, u

def camera(t):
    hip, _, _ = pose(t)
    z = 1.32 - 0.5 * ease(t / DUR)
    return hip, z

def w2s(p, cam, z):
    p = np.asarray(p, np.float64)
    return np.stack([ANCHOR[0] + (p[..., 0] - cam[0]) * z,
                     ANCHOR[1] - (p[..., 1] - cam[1]) * z], -1)

# 光源：台阶延长线与画面上方相交处
SLOPE = SH / D
LIGHT = np.array([ANCHOR[0] + (ANCHOR[1] - 0.10 * H) / SLOPE + 60, 0.10 * H])

def ik(hip, foot, a, b):
    d = foot - hip
    L = np.linalg.norm(d)
    L = min(L, a + b - 1e-3)
    th = math.atan2(d[1], d[0])
    al = math.acos(max(-1, min(1, (a * a + L * L - b * b) / (2 * a * L))))
    return hip + a * np.array([math.cos(th + al), math.sin(th + al)])

# ---------- 背景 ----------
def background(t, flare):
    dx, dy = XX - LIGHT[0], YY - LIGHT[1]
    r = np.sqrt(dx * dx + dy * dy) / W
    ang = np.arctan2(dy, dx)
    deep = np.array([6, 8, 22.0]) / 255
    mid = np.array([70, 34, 48.0]) / 255
    warm = np.array([255, 170, 80.0]) / 255
    hot = np.array([255, 246, 220.0]) / 255
    g1 = np.clip(1 - r / 1.05, 0, 1) ** 1.6
    g2 = np.clip(1 - r / 0.55, 0, 1) ** 2.2
    g3 = np.exp(-(r / (0.06 + 0.05 * flare)) ** 2)
    img = deep + (mid - deep) * g1[..., None]
    img = img + (warm - img) * g2[..., None] * 0.85
    # 神光光束
    rays = (0.5 + 0.5 * np.sin(ang * 23 + t * 0.6)) * (0.5 + 0.5 * np.sin(ang * 37 - t * 0.9 + 1.3))
    rays += 0.6 * (0.5 + 0.5 * np.sin(ang * 11 + t * 0.35 + 2.0)) ** 3
    rays *= np.clip(1 - r / 1.3, 0, 1) ** 1.3 * (0.55 + 0.6 * flare)
    img = img + warm[None, None] * rays[..., None] * 0.42
    img = img + (hot - img) * np.clip(g3 * (1.0 + 0.6 * flare), 0, 1)[..., None]
    return img, r

def clouds(t, cam, z, r):
    # 两层视差云海，铺在下方
    acc = np.zeros((H, W))
    col = np.zeros((H, W, 3))
    for tex, par, base, a in ((CLOUD, 0.25, 0.70, 0.75), (CLOUD2, 0.45, 0.80, 0.9)):
        ox = int(cam[0] * par * z * 0.6 + t * 40) % W
        oy = int(-(cam[1] - 200) * par * z * 0.6)
        n = np.roll(tex[:, ox:ox + W], 0, 0)
        hmask = np.clip((YY + oy - base * H) / (0.18 * H), 0, 1)
        dens = np.clip((n - 0.48) * 3.0, 0, 1) * hmask
        light = np.clip(1 - r / 0.9, 0, 1) ** 1.5
        c = np.array([40, 30, 52.0]) / 255 + (np.array([255, 180, 110.0]) / 255) * light[..., None] * (0.35 + 0.65 * n[..., None])
        col = col * (1 - dens[..., None] * a) + c * dens[..., None] * a
        acc = acc * (1 - dens * a) + dens * a
    return col, acc

# ---------- 剪影 ----------
def draw_scene_masks(t):
    cam, z = camera(t)
    hip, feet, u = pose(t)
    S = SS
    stairs = Image.new("L", (W * S, H * S), 0)
    edges = Image.new("L", (W * S, H * S), 0)
    fig = Image.new("L", (W * S, H * S), 0)
    ds, de, df = ImageDraw.Draw(stairs), ImageDraw.Draw(edges), ImageDraw.Draw(fig)

    def P(p):
        s = w2s(p, cam, z) * S
        return (float(s[0]), float(s[1]))

    # 台阶：锯齿顶 + 平行底面，向光延伸
    k0 = int(cam[0] / D) - 40
    k1 = int(cam[0] / D) + 60
    top = []
    for k in range(k0, k1):
        top += [P((k * D, k * SH)), P((k * D, (k + 1) * SH))]
    thick = 150
    bottom = [P((k1 * D, k1 * SH - thick)), P((k0 * D, k0 * SH - thick))]
    ds.polygon(top + bottom, fill=255)
    for k in range(k0, k1):
        a, b = P((k * D, (k + 1) * SH)), P(((k + 1) * D, (k + 1) * SH))
        de.line([a, b], fill=255, width=max(2, int(3 * z * S)))

    # 人物
    lw = lambda v: max(1, int(v * z * S))
    def limb(a, b, w):
        A, B = P(a), P(b)
        df.line([A, B], fill=255, width=lw(w))
        rr = lw(w) / 2
        for q in (A, B):
            df.ellipse([q[0] - rr, q[1] - rr, q[0] + rr, q[1] + rr], fill=255)

    lean = math.radians(14)
    sh = hip + 112 * np.array([math.sin(lean), math.cos(lean)])
    head = sh + np.array([10, 34])
    # 披风（身后飘动）
    up, lo = [], []
    N = 14
    for i in range(N + 1):
        s = i / N
        wave = 14 * math.sin(2 * math.pi * (s * 1.4 - t * 1.6)) * s
        base = sh + np.array([-8, -2]) + np.array([-s * 190, -s * 120]) + np.array([0, wave])
        nrm = np.array([0.53, -0.85])
        wdt = 6 + 42 * s ** 0.8
        up.append(P(base - nrm * wdt * 0.2))
        lo.append(P(base + nrm * wdt))
    df.polygon(up + lo[::-1], fill=255)

    phase = 2 * math.pi * u / 2
    for side, foot in enumerate(feet):
        knee = ik(hip, foot, THIGH, SHIN)
        limb(hip, knee, 27)
        limb(knee, foot, 20)
        limb(foot, foot + np.array([22, -2]), 12)
    for side in (0, 1):
        sw = 0.55 * math.sin(phase + side * math.pi)
        a1 = -math.pi / 2 + sw
        elbow = sh + 52 * np.array([math.cos(a1), math.sin(a1)])
        a2 = a1 + 0.35 + 0.25 * max(0, sw)
        hand = elbow + 48 * np.array([math.cos(a2), math.sin(a2)])
        limb(sh, elbow, 15)
        limb(elbow, hand, 12)
    limb(hip, sh, 40)
    limb(sh, sh + np.array([6, 18]), 18)
    hc = P(head)
    hr = 21 * z * S
    df.ellipse([hc[0] - hr, hc[1] - hr, hc[0] + hr, hc[1] + hr], fill=255)

    def down(im, blur=0):
        im = im.resize((W, H), Image.LANCZOS)
        if blur:
            im = im.filter(ImageFilter.GaussianBlur(blur))
        return np.asarray(im, np.float64) / 255
    return down(stairs), down(edges), down(fig), cam, z

def render(t):
    flare = ease((t - 2.2) / 0.8)
    bg, r = background(t, flare)
    stairs, edges, fig, cam, z = draw_scene_masks(t)
    ccol, cacc = clouds(t, cam, z, r)
    img = bg * (1 - cacc[..., None]) + ccol
    # 雾：越靠近光越被光吞没
    fog = np.clip(1 - r / 0.75, 0, 1) ** 1.4
    fog = np.clip(fog * (1.25 + 0.4 * flare), 0, 1)[..., None]
    stone = np.array([12, 10, 18.0]) / 255
    sc = stone * (1 - fog) + bg * fog
    img = img * (1 - stairs[..., None]) + sc * stairs[..., None]
    gold = np.array([255, 200, 120.0]) / 255
    eg = edges * (0.25 + 0.9 * np.clip(1 - r / 1.0, 0, 1) ** 1.2)
    img = img + gold * eg[..., None] * 0.9
    # 人物：轮廓光（朝光一侧亮边）
    dirv = (LIGHT - ANCHOR) / np.linalg.norm(LIGHT - ANCHOR)
    sx, sy = int(round(-dirv[0] * 3)), int(round(-dirv[1] * 3))
    shifted = np.roll(np.roll(fig, sy, 0), sx, 1)
    rim = np.clip(fig - shifted, 0, 1)
    body = np.array([5, 4, 9.0]) / 255
    img = img * (1 - fig[..., None]) + body * fig[..., None]
    img = img + np.array([255, 225, 170.0]) / 255 * rim[..., None] * (0.9 + 0.5 * flare)
    # 尘埃粒子（向光飘）
    pr = np.random.default_rng(42)
    n = 160
    px0, py0 = pr.random(n) * W, pr.random(n) * H
    sp = 20 + 60 * pr.random(n)
    px = (px0 + dirv[0] * sp * t * 3) % W
    py = (py0 + dirv[1] * sp * t * 3) % H
    part = Image.new("L", (W, H), 0)
    dp = ImageDraw.Draw(part)
    for x, y, s in zip(px, py, pr.random(n)):
        rr = 0.8 + 2.2 * s
        dp.ellipse([x - rr, y - rr, x + rr, y + rr], fill=int(120 + 135 * s))
    part = np.asarray(part.filter(ImageFilter.GaussianBlur(1.2)), np.float64) / 255
    img = img + gold * part[..., None] * 0.6
    # 泛光
    bright = np.clip(img - 0.7, 0, None)
    bl = Image.fromarray((np.clip(bright, 0, 1) * 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    bl = bl.filter(ImageFilter.GaussianBlur(18)).resize((W, H), Image.BILINEAR)
    img = img + np.asarray(bl, np.float64) / 255 * 1.2
    # 收尾神光爆发
    img = img + (np.array([1.0, 0.95, 0.85]) - img) * 0.32 * ease((t - 2.5) / 0.5) 
    # 暗角 + 颗粒
    vig = 1 - 0.55 * np.clip(np.sqrt(((XX - W * 0.6) / W) ** 2 + ((YY - H * 0.45) / H) ** 2) - 0.25, 0, 1)
    img = img * vig[..., None]
    img = img + np.random.default_rng(int(t * 1000)).normal(0, 0.012, (H, W, 1))
    img = 1 - np.exp(-img * 1.25)   # 柔和色调映射
    img = img / (1 - math.exp(-1.25))
    return (np.clip(img, 0, 1) * 255).astype(np.uint8)

def job(i):
    out = sys.argv[1]
    Image.fromarray(render(i / FPS)).save(os.path.join(out, f"f{i:04d}.png"))

if __name__ == "__main__":
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    if len(sys.argv) > 2:
        for s in sys.argv[2:]:
            Image.fromarray(render(float(s))).save(os.path.join(out, f"still_{s}.png"))
    else:
        with Pool(4) as p:
            p.map(job, range(int(FPS * DUR)))
