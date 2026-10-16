"""Tesla evolution - 2D side-scrolling morph film. 1920x1080 @ 60fps.

usage: python3 render.py out.mp4 [--from S] [--to S] [--jobs N] [--still t1,t2,... dir]
"""
import math
import os
import subprocess
import sys
import numpy as np
import skia

import carrender as cr
from carrender import col, clamp, lerp, smooth, ease_io
from cars import CARS
import scenes as sc

W, H, FPS = 1920, 1080, 60
NEAR = sc.SPEED['near']
T_TR = 3.2
TR_START = [5.5, 12.2, 18.9, 25.6, 32.3, 39.5, 46.7]
LIFT_T0 = 51.4
FOOT_T0, FOOT_T1 = 54.0, 56.4
END = 59.4
FOOTAGE = os.environ.get('FOOTAGE', '')

FONT_YEAR = skia.Font(skia.Typeface('Noto Sans CJK SC Light'), 112)
FONT_TITLE = skia.Font(skia.Typeface('Noto Sans CJK SC'), 42)
for f in (FONT_YEAR, FONT_TITLE):
    f.setSubpixel(True); f.setEdging(skia.Font.Edging.kAntiAlias)


def car_state(t):
    for i, t0 in enumerate(TR_START):
        if t0 <= t < t0 + T_TR:
            return cr.CarState(i, i + 1, tau=t - t0)
    n = sum(1 for t0 in TR_START if t >= t0 + T_TR)
    return cr.CarState(n)


def falcon_amount(t):
    return smooth((t - 15.9) / 0.8) * (1 - smooth((t - 17.6) / 0.8))


def text_windows():
    w = []
    for i, c in enumerate(CARS):
        t0 = 2.0 if i == 0 else TR_START[i - 1] + 2.55
        t1 = TR_START[i] - 0.1 if i < len(TR_START) else 53.5
        w.append((c.year, c.title, t0, t1))
    return w


TEXTS = text_windows()


def dist_at(t):
    return NEAR * t


def lift_px(t):
    return 560 * (clamp((t - 52.3) / 1.7) ** 2.2)


# ------------------------------------------------------------------ overlays
def draw_text(cv, t):
    for year, title, t0, t1 in TEXTS:
        if t0 - 0.01 <= t <= t1:
            a = smooth((t - t0) / 0.45) * (1 - smooth((t - (t1 - 0.35)) / 0.35))
            dy = 18 * (1 - smooth((t - t0) / 0.6))
            x, y = 118, 1000 + dy
            sh = skia.Paint(AntiAlias=True, Color=col([0, 0, 0], 0.55 * a))
            sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10))
            cv.drawString(year, x + 2, y + 3, FONT_YEAR, sh)
            cv.drawString(year, x, y, FONT_YEAR, skia.Paint(AntiAlias=True, Color=col([255, 255, 255], a)))
            yw = FONT_YEAR.measureText(year)
            lx = x + yw + 34
            # accent bar grows
            bar = smooth((t - t0 - 0.1) / 0.5)
            cv.drawRect(skia.Rect(lx, y - 70, lx + 4, y - 70 + 72 * bar), skia.Paint(AntiAlias=True, Color=col([230, 30, 45], a)))
            cv.drawString(title, lx + 26 + 2, y - 16 + 3, FONT_TITLE, sh)
            cv.drawString(title, lx + 26, y - 16, FONT_TITLE, skia.Paint(AntiAlias=True, Color=col([255, 255, 255], 0.92 * a)))


def vignette(cv, strength=0.42):
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeRadial(skia.Point(W / 2, H * 0.48), W * 0.72,
                [col([0, 0, 0], 0), col([0, 0, 0], 0), col([0, 0, 0], strength)], [0, 0.55, 1]))
    cv.drawRect(skia.Rect(0, 0, W, H), p)
    lb = skia.Paint(AntiAlias=True)
    lb.setShader(skia.GradientShader.MakeLinear([skia.Point(0, H - 260), skia.Point(0, H)],
                 [col([0, 0, 0], 0), col([0, 0, 0], 0.45)]))
    cv.drawRect(skia.Rect(0, H - 260, W, H), lb)


def draw_logo_sweep(cv, cx, cy, h, a, sweep):
    if a <= 0:
        return
    g = skia.Paint(AntiAlias=True, Color=col([230, 30, 45], 0.35 * a))
    g.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 40))
    s = h / 24.0
    cv.save(); cv.translate(cx - 12 * s, cy - 12 * s); cv.scale(s, s)
    cv.drawPath(sc.LOGO, g)
    cv.drawPath(sc.LOGO, skia.Paint(AntiAlias=True, Color=col([255, 255, 255], a)))
    if 0 < sweep < 1:
        cv.clipPath(sc.LOGO, skia.ClipOp.kIntersect, True)
        x = -8 + sweep * 40
        sp = skia.Paint(AntiAlias=True)
        sp.setShader(skia.GradientShader.MakeLinear([skia.Point(x - 4, 0), skia.Point(x + 4, 0)],
                     [col([230, 30, 45], 0), col([230, 30, 45], a), col([230, 30, 45], 0)], [0, 0.5, 1]))
        cv.drawRect(skia.Rect(-10, -10, 40, 40), sp)
    cv.restore()


# ------------------------------------------------------------------ car layer
def head_tail_pos(car):
    hd = [p for k, _, p in car.parts if k == 'head'][0].mean(0)
    tl = [p for k, _, p in car.parts if k == 'tail'][0].mean(0)
    return hd, tl


def draw_beams(cv, st, t, lights, yoff):
    if lights <= 0.01:
        return
    car = CARS[st.b if st.tau is not None and st.tau > 1.6 else st.a]
    if st.tau is not None:
        tp = cr.transition_params(st.tau)
        lights *= max(tp['old_det'], tp['new_det'])
    if lights <= 0.01:
        return
    hd, _ = head_tail_pos(car)
    hx = cr.CX + hd[0] * cr.S; hy = cr.GROUND - hd[1] * cr.S + yoff * 0
    beam = skia.Path()
    beam.moveTo(hx, hy - 8); beam.lineTo(hx + 900, hy - 120); beam.lineTo(hx + 900, cr.GROUND + 60); beam.lineTo(hx, hy + 8); beam.close()
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeLinear([skia.Point(hx, 0), skia.Point(hx + 900, 0)],
                [col([220, 236, 255], 0.30 * lights), col([220, 236, 255], 0)]))
    p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 18))
    cv.drawPath(beam, p)
    pool = skia.Paint(AntiAlias=True)
    pool.setShader(skia.GradientShader.MakeRadial(skia.Point(hx + 380, cr.GROUND + 18 + yoff), 420,
                   [col([220, 236, 255], 0.22 * lights), col([220, 236, 255], 0)]))
    cv.save(); cv.translate(0, 0); cv.scale(1, 1)
    cv.drawOval(skia.Rect(hx - 40, cr.GROUND - 20 + yoff, hx + 800, cr.GROUND + 60 + yoff), pool)
    cv.restore()


def render_car_layer(st, t, env, lights, lift):
    surf = skia.Surface(W, H)
    cv = surf.getCanvas(); cv.clear(skia.Color(0, 0, 0, 0))
    cv.save(); cv.translate(cr.CX, cr.GROUND); cv.scale(cr.S, -cr.S)
    lift_k = clamp(lift / 500)
    info = cr.draw_car(cv, st, env, dist_at(t) / cr.S, lights=lights, falcon=falcon_amount(t) if st.a == 2 and st.tau is None else 0,
                       lift=lift_k)
    cv.restore()
    return surf.makeImageSnapshot(), info


# ------------------------------------------------------------------ lift-off effects
SMOKE = np.random.default_rng(99)
PUFFS = [dict(n=SMOKE.integers(0, 4), t0=SMOKE.uniform(0, 1.8), r=SMOKE.uniform(30, 95), vx=SMOKE.normal(0, 1),
              vy=SMOKE.uniform(10, 140), tint=SMOKE.choice([0, 0, 1, 2])) for _ in range(200)]


def nozzle_xs():
    c = CARS[7]
    return [c.wf[0] - 420, 220, -520, c.wr[0] + 420]


def draw_jets(cv, t, yoff):
    """jets + nozzles below the car (screen space)."""
    dep = smooth((t - LIFT_T0) / 0.5)
    if dep <= 0:
        return
    ign = smooth((t - (LIFT_T0 + 0.5)) / 0.25)
    for i, nx in enumerate(nozzle_xs()):
        x = cr.CX + nx * cr.S
        y0 = cr.GROUND - 150 * cr.S
        # nozzle
        cv.drawRoundRect(skia.Rect(x - 13, y0 - 6, x + 13, y0 + 26 * dep), 5, 5, skia.Paint(AntiAlias=True, Color=col([40, 42, 48])))
        if ign > 0:
            fl = 1 + 0.12 * math.sin(t * 70 + i * 2)
            ln = (150 + yoff) * (0.4 + 0.6 * ign) * fl
            yb = y0 + 26
            jet = skia.Path(); jet.moveTo(x - 11, yb); jet.lineTo(x + 11, yb); jet.lineTo(x + 34, yb + ln); jet.lineTo(x - 34, yb + ln); jet.close()
            p = skia.Paint(AntiAlias=True)
            p.setShader(skia.GradientShader.MakeLinear([skia.Point(0, yb), skia.Point(0, yb + ln)],
                        [col([255, 255, 255], ign), col([150, 225, 255], 0.85 * ign), col([120, 200, 255], 0)], [0, 0.3, 1]))
            p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 6))
            cv.drawPath(jet, p)
            sc.glow(cv, x, yb + 10, 70, [180, 230, 255], 0.9 * ign)


def draw_smoke(cv, t, yoff):
    tt = t - (LIFT_T0 + 0.55)
    if tt <= 0:
        return
    base = cr.GROUND + yoff
    nx = nozzle_xs()
    for pf in PUFFS:
        age = tt - pf['t0']
        if age <= 0:
            continue
        grow = 1 - math.exp(-age * 1.4)
        r = pf['r'] * (0.5 + 2.2 * grow)
        x = cr.CX + nx[pf['n']] * cr.S + pf['vx'] * 380 * grow
        y = base - pf['vy'] * grow - r * 0.25
        tint = [[226, 232, 238], [196, 226, 244], [244, 206, 212]][pf['tint']]
        a = 0.42 * min(1, age * 4) * (1 - smooth((age - 2.0) / 1.5))
        p = skia.Paint(AntiAlias=True)
        p.setShader(skia.GradientShader.MakeRadial(skia.Point(x, y), r, [col(tint, a), col(tint, a * 0.45), col(tint, 0)], [0, 0.55, 1]))
        cv.drawCircle(x, y, r, p)


# ------------------------------------------------------------------ footage
class Footage:
    def __init__(self, path):
        self.frames = None
        if path and os.path.exists(path):
            raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'rawvideo', '-pix_fmt', 'rgba', '-'],
                                 capture_output=True, check=True).stdout
            self.frames = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 4)

    def get(self, t):
        if self.frames is None:
            return None
        i = int(clamp((t - FOOT_T0) * FPS, 0, len(self.frames) - 1))
        return self.frames[i]


# ------------------------------------------------------------------ frame
def frame(t, footage=None):
    surf = skia.Surface(W, H)
    cv = surf.getCanvas()
    cv.clear(skia.Color(0, 0, 0))

    if t >= FOOT_T0 and t < FOOT_T1:
        fr = footage.get(t) if footage else None
        if fr is not None:
            img = skia.Image.fromarray(np.ascontiguousarray(fr))
            cv.drawImage(img, 0, 0)
        u = t - FOOT_T0
        wa = 1 - smooth(u / 0.4)
        cv.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Color=col([255, 255, 255], wa)))
        fo = smooth((t - (FOOT_T1 - 0.35)) / 0.35)
        cv.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Color=col([0, 0, 0], fo)))
        vignette(cv, 0.3)
        return surf
    if t >= FOOT_T1:
        a = smooth((t - (FOOT_T1 + 0.3)) / 0.7) * (1 - smooth((t - (END - 0.6)) / 0.55))
        draw_logo_sweep(cv, W / 2, H / 2 - 10, 230, a, clamp((t - (FOOT_T1 + 0.8)) / 1.2))
        return surf

    st = car_state(t)
    a_env, b_env, u = sc.blend_env(t, 1.0)
    env = sc.mix_env(a_env, b_env, u)
    lights = lerp(sc.SCENES[a_env].lights, sc.SCENES[b_env].lights, u)
    lift = lift_px(t) if t > LIFT_T0 else 0.0
    sc.draw_background(cv, t, dist_at(t), yoff=lift)

    # current floor reflectivity under the car
    refl = sc.SCENES[sc.scene_at(t)].refl
    car_img, info = render_car_layer(st, t, env, lights, lift)
    draw_beams(cv, st, t, lights * (1 - clamp(lift / 200)), lift)
    if t > LIFT_T0:
        cv.save(); cv.translate(0, 0)
        draw_smoke(cv, t, lift)
        cv.restore()
    if refl > 0:
        cv.save()
        gy = cr.GROUND + lift
        cv.clipRect(skia.Rect(0, gy, W, H))
        cv.translate(0, 2 * gy); cv.scale(1, -1)
        cv.translate(0, -lift * 0)  # car stays fixed, mirror about the ground line
        p = skia.Paint(); p.setAlphaf(refl * 0.55)
        p.setImageFilter(skia.ImageFilters.Blur(2, 5))
        cv.drawImage(car_img, 0, 0, skia.SamplingOptions(), p)
        cv.restore()
        fade = skia.Paint()
        fade.setShader(skia.GradientShader.MakeLinear([skia.Point(0, gy), skia.Point(0, gy + 260)],
                       [col(sc.SCENES[sc.scene_at(t)].road[1], 0.0), col(sc.SCENES[sc.scene_at(t)].road[1], 0.9)]))
        cv.drawRect(skia.Rect(0, gy, W, gy + 400), fade)
    if t > LIFT_T0:
        draw_jets(cv, t, lift)
    cv.drawImage(car_img, 0, 0)

    vignette(cv)
    draw_text(cv, t)

    # intro: black + logo, garage lights flicker on
    if t < 2.2:
        dark = 1 - smooth((t - 1.0) / 0.9)
        flick = 0.0
        for ft in (1.02, 1.22):
            flick += 0.55 * clamp(1 - abs(t - ft) / 0.05)
        cv.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Color=col([0, 0, 0], clamp(dark - flick))))
        la = smooth((t - 0.1) / 0.5) * (1 - smooth((t - 1.05) / 0.5))
        draw_logo_sweep(cv, W / 2, H / 2 - 30, 210 + 20 * t, la, clamp((t - 0.25) / 0.8))
    # flash into the real footage
    if t > FOOT_T0 - 0.45:
        cv.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Color=col([255, 255, 255], smooth((t - (FOOT_T0 - 0.45)) / 0.45))))
    return surf


def to_rgb(surf):
    return surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)


def encode(out, f0, f1, footage=None):
    if footage is None:
        need = f0 / FPS < FOOT_T1 and f1 / FPS > FOOT_T0
        footage = Footage(FOOTAGE if need else '')
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
           '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
           '-x264-params', 'keyint=120', out]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(f0, f1):
        pr.stdin.write(to_rgb(frame(f / FPS, footage)).tobytes())
    pr.stdin.close(); pr.wait()


def main():
    args = sys.argv[1:]
    sc.build_scenes()
    if args and args[0] == '--still':
        ts = [float(x) for x in args[1].split(',')]
        d = args[2]
        footage = Footage(FOOTAGE)
        from PIL import Image
        for t in ts:
            arr = to_rgb(frame(t, footage))
            Image.fromarray(arr[..., :3]).save(os.path.join(d, f'still_{t:06.2f}.png'))
        return
    out = args[0]
    t_from = float(args[args.index('--from') + 1]) if '--from' in args else 0.0
    t_to = float(args[args.index('--to') + 1]) if '--to' in args else END
    jobs = int(args[args.index('--jobs') + 1]) if '--jobs' in args else 1
    f0, f1 = int(round(t_from * FPS)), int(round(t_to * FPS))
    if jobs == 1:
        encode(out, f0, f1)
        return
    import multiprocessing as mp
    bounds = np.linspace(f0, f1, jobs + 1).astype(int)
    parts = [f'{out}.part{i}.mp4' for i in range(jobs)]
    procs = []
    for i in range(jobs):
        p = mp.Process(target=encode, args=(parts[i], bounds[i], bounds[i + 1]))
        p.start(); procs.append(p)
    for p in procs:
        p.join()
    lst = out + '.txt'
    with open(lst, 'w') as fh:
        for pth in parts:
            fh.write(f"file '{os.path.abspath(pth)}'\n")
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy',
                    '-movflags', '+faststart', out], check=True)
    for pth in parts:
        os.remove(pth)
    os.remove(lst)


if __name__ == '__main__':
    main()
