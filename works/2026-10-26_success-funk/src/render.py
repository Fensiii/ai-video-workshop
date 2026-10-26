"""《成功》v2 主渲染：逐帧合成（运动模糊、体积光、冲击波、辉光……）→ ffmpeg。

用法:
  python3 render.py still <t1,t2,...> <输出目录>            关键帧静帧 PNG
  python3 render.py video <out.mp4> <src.mp4> [t0 t1]        渲染视频（4 进程），音轨直接复制原视频
"""
import sys
import os
import math
import time
import subprocess
from multiprocessing import Pool

import numpy as np
import cv2

import engine as E
import scenes as S

FPS, W, H = E.FPS, E.W, E.H
_YS4, _XS4 = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32)
_PTS = np.array([[0, W, 0, W, E.CX], [0, 0, H, H, E.CY], [1, 1, 1, 1, 1]], np.float64)


def _disp_cam(ca, cb, par):
    A, B = E.cam_matrix(ca, par) @ _PTS, E.cam_matrix(cb, par) @ _PTS
    return float(np.max(np.hypot(A[0] - B[0], A[1] - B[1])))


def _disp_items(ia, ib, ca, cb):
    d = 0.0
    for a, b in zip(ia, ib):
        if a["spr"] is not b["spr"]:
            continue
        pa = E._corners(E.cam_matrix(ca, a.get("par", 1.0)) @ a["M"], a["spr"].w, a["spr"].h)
        pb = E._corners(E.cam_matrix(cb, b.get("par", 1.0)) @ b["M"], b["spr"].w, b["spr"].h)
        if pa is None or pb is None:
            continue
        d = max(d, float(np.max(np.hypot(pa[0] - pb[0], pa[1] - pb[1]))))
    return d


def _impact_frame(fa, k, cx, cy, seed):
    """冲击帧（两帧）：黑底白剪影 + 放射速度线，第二帧正负反转。"""
    img = np.zeros((H, W), np.uint8)
    rng = np.random.default_rng(seed)
    for _ in range(90):
        ang = rng.uniform(0, 2 * math.pi)
        r0 = rng.uniform(0.30, 0.55) * H
        r1 = r0 + rng.uniform(0.4, 1.2) * H
        c, s = math.cos(ang), math.sin(ang)
        cv2.line(img, (int((cx + c * r0) * 4), int((cy + s * r0) * 4)), (int((cx + c * r1) * 4), int((cy + s * r1) * 4)),
                 255, int(rng.integers(1, 5)), cv2.LINE_AA, 2)
    if fa is not None:
        img = np.maximum(img, (np.clip(fa * 1.3, 0, 1) * 255).astype(np.uint8))
    if k % 2 == 1:
        img = 255 - img
    return cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)


def render(t, fi=0):
    sc = S.scene_at(t)
    camt = S.camera(t)

    # 快门内运动量 → 采样次数（运动模糊）
    ta, tb = t - E.SHUTTER / 2, t + E.SHUTTER / 2
    ca, cb = S.camera(ta), S.camera(tb)
    d = max(_disp_cam(ca, cb, 1.0), _disp_items(S.items(ta), S.items(tb), ca, cb))
    K = int(min(12, max(1, math.ceil(d / 1.5))))
    ts = [t] if K == 1 else [ta + (k + 0.5) / K * E.SHUTTER for k in range(K)]
    cams = [camt] if K == 1 else [S.camera(x) for x in ts]

    # 背景：大位移烘焙进背景图，剩下的缩放/旋转/抖动用仿射，多次采样
    par = sc.bg_par
    bg = sc.bg(t, camt["x"] * par, camt["y"] * par)
    off = E.mat_translate(-E.MARGIN, -E.MARGIN)
    Kb = min(K, 6)
    frame = None
    for k in range(Kb):
        c = cams[int((k + 0.5) * K / Kb)]
        cc = {"z": c["z"], "rot": c["rot"], "x": c["x"] - camt["x"], "y": c["y"] - camt["y"]}
        M = (E.cam_matrix(cc, par) @ off)[:2].astype(np.float32)
        w = cv2.warpAffine(bg, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        frame = w if frame is None else cv2.add(frame, w)
    if Kb > 1:
        frame = frame * np.float32(1.0 / Kb)

    # 前景精灵（每个采样时刻单独合成再平均）
    lists = [S.items(x) for x in ts]
    boxes = [b for its, c in zip(lists, cams) for it in its for b in [E.item_bbox(it, c)] if b]
    fg_a4 = fa = None
    if boxes:
        x0 = max(0, int(min(b[0] for b in boxes)) - 2)
        y0 = max(0, int(min(b[1] for b in boxes)) - 2)
        x1 = min(W, int(max(b[2] for b in boxes)) + 3)
        y1 = min(H, int(max(b[3] for b in boxes)) + 3)
        if x1 > x0 and y1 > y0:
            acc = np.zeros((y1 - y0, x1 - x0, 4), np.float32)
            for its, c in zip(lists, cams):
                buf = acc if K == 1 else np.zeros_like(acc)
                for it in its:
                    E.draw_item(buf, (x0, y0), it, c)
                if K > 1:
                    acc += buf
            if K > 1:
                acc *= np.float32(1.0 / K)
            a = np.ascontiguousarray(acc[..., 3])
            rgb = cv2.cvtColor(acc, cv2.COLOR_RGBA2RGB)
            light = sc.light(t)
            if light is not None:
                lr = light[y0:y1, x0:x1]
                rgb = cv2.multiply(rgb, cv2.merge([lr, lr, lr]))
            inv = 1 - a
            frame[y0:y1, x0:x1] = cv2.add(rgb, cv2.multiply(frame[y0:y1, x0:x1], cv2.merge([inv, inv, inv])))
            fa = np.zeros((H, W), np.float32)
            fa[y0:y1, x0:x1] = a
            fg_a4 = cv2.resize(fa, (W // 4, H // 4), interpolation=cv2.INTER_AREA)

    # 加色层：火花、光线、HUD
    ac = E.AddCanvas()
    sc.overlay(t, ac, camt)
    S.hud(t, ac)
    add = ac.result(2.0)
    if add is not None:
        frame = cv2.add(frame, add)

    fx = sc.fx(t, {"cam": camt, "fg_a4": fg_a4}) or {}
    Mc = E.cam_matrix(camt)
    for key in ("rays", "rays2"):
        r = fx.get(key)
        if not r:
            continue
        if r.get("screen"):
            sx, sy = r["x"], r["y"]
        else:
            P = Mc @ np.array([r["x"], r["y"], 1.0])
            sx, sy = P[0], P[1]
        if r.get("src") == "bright":
            l = cv2.cvtColor(cv2.resize(frame, (W // 4, H // 4), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY)
            src = np.maximum(l - r.get("thr", 1.5), 0)
        else:
            rr = r.get("r", 300) * camt["z"] / 4
            src = np.exp(-((_XS4 - sx / 4) ** 2 + (_YS4 - sy / 4) ** 2) / (rr * rr)).astype(np.float32)
        if fg_a4 is not None:
            src = src * (1 - fg_a4)
        frame = cv2.add(frame, E.god_rays(src.astype(np.float32), sx, sy, r["strength"], reach=r.get("reach", 0.7),
                                          tint=r.get("tint", (255, 216, 150))))
    for sw in fx.get("shock") or []:
        x, y, rad, wid, amp = sw
        P = Mc @ np.array([x, y, 1.0])
        frame = E.shockwave(frame, P[0], P[1], rad * camt["z"], wid, amp)
    if fx.get("glitch", 0) > 0.01:
        frame = E.glitch(frame, fx["glitch"], seed=fi * 7 + 3)
    fl = fx.get("flash", 0.0)
    if fl > 0.003:
        c = E.lin(fx.get("flash_col", (255, 240, 220))) * fl
        frame = cv2.add(frame, (float(c[0]), float(c[1]), float(c[2]), 0.0))
    frame = E.bloom(frame, **fx.get("bloom", {}))
    frame = E.chroma(frame, fx.get("chroma", 0.0015))
    out = E.finish(frame, exposure=fx.get("exposure", 1.0) * fx.get("fade", 1.0) * (1 + fx.get("pop", 0.0)),
                   grain=0.011, seed=fi,
                   vignette=0.55, sat=fx.get("sat", 1.0), contrast=fx.get("contrast", 1.04),
                   gain=fx.get("gain", (1.0, 1.0, 1.0)))
    if fx.get("scan"):
        out[::3] = (out[::3] * (1 - fx["scan"])).astype(np.uint8)
    imp = fx.get("impact")
    if imp is not None:
        # 剪影只取本帧时刻的字（不混入快门里跨到上一段的内容）
        th, ix, iy = imp
        sil = np.zeros((H, W, 4), np.float32)
        for it in S.items(max(t, th)):
            if it.get("a", 1.0) > 0.001 and it.get("blend", "over") == "over" and it.get("sil", True):
                E.draw_item(sil, (0, 0), dict(it, a=1.0), camt)
        P = Mc @ np.array([ix, iy, 1.0])
        out = _impact_frame(np.ascontiguousarray(sil[..., 3]), int((t - th) * FPS), P[0], P[1], int(th * 1000))
    return out


def still(times, outdir):
    os.makedirs(outdir, exist_ok=True)
    for t in times:
        t0 = time.time()
        img = render(t, int(round(t * FPS)))
        cv2.imwrite(os.path.join(outdir, "f_%06.3f.png" % t), img[..., ::-1])
        print("%.3f  %.2fs" % (t, time.time() - t0), flush=True)


def _work(fi):
    return render(fi / FPS, fi).tobytes()


def video(out, src, t0=0.0, t1=None, crf=12, procs=4):
    S.warm()
    n0 = int(round(t0 * FPS))
    n1 = int(round((t1 if t1 is not None else S.END) * FPS))
    dur = (n1 - n0) / FPS
    cmd = ["ffmpeg", "-v", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-ss", "%.3f" % t0, "-t", "%.3f" % dur, "-i", src,
           "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "slow", "-crf", str(crf),
           "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
           "-c:a", "copy", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t_start = time.time()
    with Pool(procs) as pool:
        for j, buf in enumerate(pool.imap(_work, range(n0, n1), chunksize=2)):
            p.stdin.write(buf)
            if j % 60 == 0:
                el = time.time() - t_start
                print("frame %d/%d  %.0fs  eta %.0fs" % (j, n1 - n0, el, el / max(1, j) * (n1 - n0 - j)), flush=True)
    p.stdin.close()
    p.wait()
    print("done %.0fs" % (time.time() - t_start))


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "still":
        still([float(x) for x in sys.argv[2].split(",")], sys.argv[3])
    elif mode == "video":
        a = sys.argv[2:]
        video(a[0], a[1], float(a[2]) if len(a) > 2 else 0.0, float(a[3]) if len(a) > 3 else None)
