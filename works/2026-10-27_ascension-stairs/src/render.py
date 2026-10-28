"""登神长阶：侧面剪影登阶，暴雨雷电 → 云开天晴，5 秒 1920x1080 30fps。
用法: python render.py OUT_DIR [t1 t2 ...]   (给 t 只渲染这些时刻的静帧)
"""
import sys, os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from multiprocessing import Pool

W, H = 1920, 1080
FPS, DUR = 30, 5.0
SS = 2                      # 剪影超采样倍数
D, SH = 50.0, 40.0          # 台阶进深 / 高度（世界单位）
RATE = 1.6                  # 每秒登几级
THIGH, SHIN = 58.0, 56.0
LEG = THIGH + SHIN
ANCHOR = np.array([0.38 * W, 0.68 * H])   # 人物胯部固定在屏幕的位置

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

def smooth(x):
    return ease(x)

FOOT = 20.0   # 脚长（脚跟到脚尖）

def pose(t):
    """返回胯部、两只脚（脚尖位置 + 脚掌角度）、步相 u。
    每只脚一次跨两级：先蹬地抬脚跟，再抬腿过台阶边、前送、落地。"""
    u = t * RATE
    hx = (u + 1) * D + 3.0 * math.sin(2 * math.pi * u)
    hy = stair_y(hx) + 0.88 * LEG - 5.0 * math.cos(2 * math.pi * u)
    feet = []
    for off in (0.0, 1.0):
        v = (u - off) / 2
        n = math.floor(v)
        p = v - n
        s0 = 2 * n + off
        if p < 0.5:                       # 摆动
            s = p * 2
            x0, y0 = (s0 + 0.5) * D + 11, (s0 + 1) * SH
            tx = x0 + 2 * D * smooth(s)
            ty = y0 + 2 * SH * smooth(s / 0.55) + 20 * math.sin(math.pi * s)
            a = -0.6 * (1 - smooth(s / 0.35)) + 0.25 * math.sin(math.pi * smooth((s - 0.3) / 0.7))
        else:                             # 支撑，末段抬脚跟
            k = s0 + 2
            tx, ty = (k + 0.5) * D + 11, (k + 1) * SH
            a = -0.6 * smooth((p - 0.8) / 0.2)
        toe = np.array([tx, ty])
        ankle = toe - FOOT * np.array([math.cos(a), math.sin(a)]) + np.array([0, 8 * math.cos(a)])
        feet.append((toe, ankle))
    return np.array([hx, hy]), feet, u


def camera(t):
    hip, _, _ = pose(t)
    z = 2.3 - 0.5 * ease(t / DUR)
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

# ---------- 天气 ----------
STRIKES = [(0.45, 1.0, 0.62), (1.30, 0.85, 0.20), (1.95, 0.5, 0.80)]   # 时刻、强度、横向位置

def weather(t):
    storm = 1 - ease((t - 2.0) / 2.0)          # 1=暴雨，0=晴
    rain = 1 - ease((t - 1.8) / 1.6)
    flash = 0.0
    for t0, amp, _ in STRIKES:
        d = t - t0
        if d >= 0:
            flash += amp * (math.exp(-d / 0.06) + (0.7 * math.exp(-(d - 0.12) / 0.05) if d > 0.12 else 0))
    return storm, rain, min(flash, 1.3)

def bolt_mask(t):
    m = Image.new("L", (W, H), 0)
    dm = ImageDraw.Draw(m)
    any_ = False
    for i, (t0, amp, xf) in enumerate(STRIKES):
        d = t - t0
        if not (0 <= d < 0.2) or (0.07 < d < 0.12):
            continue
        any_ = True
        br = np.random.default_rng(100 + i)
        def branch(x, y, ang, length, w, depth):
            pts = [(x, y)]
            while length > 0:
                seg = 25 + 30 * br.random()
                ang2 = ang + br.normal(0, 0.45)
                x, y = x + seg * math.sin(ang2), y + seg * math.cos(ang2)
                pts.append((x, y)); length -= seg
                if depth < 2 and br.random() < 0.12:
                    branch(x, y, ang + br.choice([-0.7, 0.7]), length * 0.45, max(1, w - 2), depth + 1)
            dm.line(pts, fill=int(255 * min(1, amp)), width=w)
        branch(xf * W, -20, br.normal(0, 0.15), H * 0.62, 5, 0)
    if not any_:
        return None
    a = np.asarray(m, np.float64) / 255
    g = np.asarray(m.filter(ImageFilter.GaussianBlur(14)), np.float64) / 255
    return a, g

def rain_mask(t, rain, flash):
    m = Image.new("L", (W, H), 0)
    if rain <= 0.01:
        return None
    dm = ImageDraw.Draw(m)
    rr = np.random.default_rng(int(t * FPS) + 9)
    n = int(1100 * rain)
    xs, ys = rr.random(n) * (W + 300), rr.random(n) * H
    ln = 40 + 70 * rr.random(n)
    vv = 60 + 140 * rr.random(n)
    for x, y, l, v in zip(xs, ys, ln, vv):
        dm.line([(x, y), (x - 0.22 * l, y + l)], fill=int(v), width=2 if v > 150 else 1)
    return np.asarray(m.filter(ImageFilter.GaussianBlur(0.7)), np.float64) / 255

def storm_sky(t, storm, flash, r):
    # 压顶乌云：阈值随放晴升高，云层被撕开
    ox = int(t * 60) % W
    n = CLOUD2[:, ox:ox + W] * 0.6 + CLOUD[:, (ox * 2) % W:(ox * 2) % W + W] * 0.4
    thr = 0.12 + 0.8 * (1 - storm) ** 1.5
    dens = np.clip((n - thr) * 4.0, 0, 1)
    shade = np.clip(1.25 - 1.6 * (n - 0.35), 0.35, 1.3)
    c = np.array([34, 38, 50.0]) / 255 * shade[..., None]
    c = c + np.array([0.55, 0.6, 0.75]) * flash * 0.5 * n[..., None]
    sun = np.clip(1 - r / 0.6, 0, 1) ** 2 * (1 - storm)
    c = c + np.array([1.0, 0.7, 0.35]) * (sun * np.clip(1 - dens * 1.5 + 0.5, 0, 1))[..., None] * 0.6
    return c, dens

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

    lean = math.radians(4 + 2 * math.sin(2 * math.pi * u + 0.6))
    up = np.array([math.sin(lean), math.cos(lean)])
    side = np.array([up[1], -up[0]])          # 朝前的法向
    sh = hip + 80 * up
    # 火柴人：等粗线条 + 实心圆头
    SW = 9
    neck = sh + up * 8
    limb(hip, neck, SW)
    head = neck + up * 22
    hc = P(head)
    hr = 22 * z * S
    df.ellipse([hc[0] - hr, hc[1] - hr, hc[0] + hr, hc[1] + hr], fill=255)

    for toe, ankle in feet:
        knee = ik(hip, ankle, THIGH, SHIN)
        limb(hip, knee, SW)
        limb(knee, ankle, SW)
        limb(ankle, ankle + (toe - ankle) * 0.6, SW)
    # 手臂与对侧腿同向摆动
    for i in (0, 1):
        rel = (feet[1 - i][1][0] - hip[0]) / D
        sw = 0.42 * max(-1.2, min(1.2, rel))
        a1 = -math.pi / 2 + lean * 0.5 + sw
        sho = sh
        elbow = sho + 40 * np.array([math.cos(a1), math.sin(a1)])
        a2 = a1 + 0.3 + 0.55 * max(0.0, sw)
        hand = elbow + 38 * np.array([math.cos(a2), math.sin(a2)])
        limb(sho, elbow, SW)
        limb(elbow, hand, SW)

    def down(im, blur=0):
        im = im.resize((W, H), Image.LANCZOS)
        if blur:
            im = im.filter(ImageFilter.GaussianBlur(blur))
        return np.asarray(im, np.float64) / 255
    return down(stairs), down(edges), down(fig), cam, z

def render(t):
    storm, rain, flash = weather(t)
    sunny = 1 - storm
    flare = ease((t - 4.0) / 1.0)
    bg, r = background(t, flare)
    # 雨天底色：灰蓝压暗，太阳只透一点
    grey = np.array([62, 68, 82.0]) / 255 - np.array([36, 38, 44.0]) / 255 * (YY / H)[..., None]
    k = sunny ** 1.3
    bg = grey * (1 - k) + bg * k
    bg = bg + np.array([0.5, 0.55, 0.7]) * flash * 0.35
    stairs, edges, fig, cam, z = draw_scene_masks(t)
    ccol, cacc = clouds(t, cam, z, r)
    tint = np.array([0.45, 0.5, 0.6]) * (1 - k) + k
    img = bg * (1 - cacc[..., None]) + ccol * tint
    scol, sden = storm_sky(t, storm, flash, r)
    bm = bolt_mask(t)
    if bm is not None:   # 闪电在乌云之后半透出、之下全亮
        img = img + np.array([0.8, 0.85, 1.0]) * (bm[1] * 0.8)[..., None]
    img = img * (1 - sden[..., None]) + scol * sden[..., None]
    if bm is not None:
        img = img + np.array([0.9, 0.93, 1.0]) * (bm[0] * (1 - 0.5 * sden) + bm[1] * 0.5)[..., None]
    bg = img
    # 雾：越靠近光越被光吞没
    fog = np.clip(1 - r / 0.75, 0, 1) ** 1.4
    fog = np.clip(fog * (1.25 + 0.4 * flare) * k, 0, 1)[..., None]
    stone = np.array([12, 10, 18.0]) / 255
    sc = stone * (1 - fog) + bg * fog
    img = img * (1 - stairs[..., None]) + sc * stairs[..., None]
    gold = np.array([255, 200, 120.0]) / 255
    eg = edges * ((0.25 + 0.9 * np.clip(1 - r / 1.0, 0, 1) ** 1.2) * k + 0.12 * (1 - k) + 0.6 * flash)
    ecol = gold * k + np.array([0.6, 0.68, 0.85]) * (1 - k)
    img = img + ecol * eg[..., None] * 0.9
    # 人物：轮廓光（朝光一侧亮边）
    dirv = (LIGHT - ANCHOR) / np.linalg.norm(LIGHT - ANCHOR)
    sx, sy = int(round(-dirv[0] * 3)), int(round(-dirv[1] * 3))
    shifted = np.roll(np.roll(fig, sy, 0), sx, 1)
    rim = np.clip(fig - shifted, 0, 1)
    body = np.array([5, 4, 9.0]) / 255
    img = img * (1 - fig[..., None]) + body * fig[..., None]
    rcol = np.array([255, 225, 170.0]) / 255 * k * (0.9 + 0.5 * flare) + np.array([0.75, 0.82, 1.0]) * (0.15 * (1 - k) + 1.2 * flash)
    img = img + rcol * rim[..., None]
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
    img = img + gold * part[..., None] * 0.6 * k
    rm = rain_mask(t, rain, flash)
    if rm is not None:
        img = img + np.array([0.62, 0.68, 0.8]) * rm[..., None] * (0.35 + 0.5 * flash)
    # 泛光
    bright = np.clip(img - 0.7, 0, None)
    bl = Image.fromarray((np.clip(bright, 0, 1) * 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    bl = bl.filter(ImageFilter.GaussianBlur(18)).resize((W, H), Image.BILINEAR)
    img = img + np.asarray(bl, np.float64) / 255 * 1.2
    # 收尾神光爆发
    img = img + (np.array([1.0, 0.95, 0.85]) - img) * 0.3 * ease((t - 4.5) / 0.5) 
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
