"""YouTube thumbnail (1280x720 JPEG): the video's own overview chart, ending on the 2025 all-time high,
with a short, phone-legible hook. Writes ../out/youtube_thumbnail.jpg."""
import math
import os

import numpy as np
import skia
from PIL import Image

import btc_common as B
import render as R
from btc_common import W, H

ATH_DAY = B.day_of('2025-10-06')


def cam_to(day, hx=1640.0, hy=300.0, x0=330.0, y0=930.0):
    """overview framing (as render.overview_cam) with the head on `day`"""
    lh = B.LOGP[day]
    theta = math.radians(9.0)
    st, ct = math.sin(theta), math.cos(theta)
    f = B.F_CAM
    xh = hx - B.CX
    u0 = f * (x0 - B.CX - xh) / (f * ct + (x0 - B.CX) * st)
    k = -u0 / day
    v0 = (B.CY - y0) * (f - u0 * st) / f - (B.CY - hy)
    s = v0 / (B.LOGP[0] - lh)
    return R.Cam(float(day), lh, k, s, hx, hy, theta, 0.0)


def gold(y0, y1, a=1.0):
    sh = skia.GradientShader.MakeLinear([skia.Point(0, y0), skia.Point(0, y1)],
                                        [R.col((255, 238, 196), a), R.col((246, 205, 128), a), R.col((214, 160, 80), a)],
                                        [0.0, 0.55, 1.0])
    return skia.Paint(AntiAlias=True, Shader=sh)


def main():
    arr = np.zeros((H, W, 4), np.uint8)
    c = skia.Surface(arr).getCanvas()
    c.clear(skia.Color4f(0.004, 0.012, 0.047, 1))
    cam = cam_to(ATH_DAY, hx=1770.0, hy=320.0, x0=760.0, y0=1000.0)
    t = 150.0
    R.CUR_M = skia.Matrix()
    R.draw_background(c, t, 0.35, 0.0)
    R.draw_dust(c, t, dim=0.6)
    R.draw_grid(c, cam, t, alpha=0.5, labels=False)
    R.draw_curtains(c, cam, t, intensity=0.75)
    R.draw_line(c, cam, t, style=1.3)
    R.draw_head(c, cam, t, 0.6, scale=1.25)
    R.draw_vignette(c)
    # hook text, top-left (the chart rises bottom-left -> top-right, leaving this corner open)
    x = 108
    R.draw_text(c, 'BITCOIN PRICE HISTORY', x + 4, 168, R.font('bold', 46), R.P((206, 196, 172)), spacing=9)
    f1 = R.font('black', 150)
    R.draw_text(c, '$0.08', x, 352, f1, R.P((255, 255, 255)), spacing=-1)
    w1 = R.text_width(f1, '$0.08', -1)
    R.draw_text(c, '→', x + w1 + 34, 340, R.font('bold', 120), R.P((236, 200, 132)))
    f2 = R.font('black', 250)
    R.draw_text(c, '$124K', x - 6, 600, f2, R.P((255, 200, 110), 0.55, blur=22), spacing=-3)
    R.draw_text(c, '$124K', x - 6, 600, f2, gold(400, 600), spacing=-3)
    R.draw_text(c, '16 YEARS IN 3 MINUTES', x + 6, 690, R.font('bold', 52), R.P((235, 238, 246)), spacing=6)
    img = Image.fromarray(arr[..., :3].copy()).resize((1280, 720), Image.LANCZOS)
    out = os.path.join(B.ROOT, 'out', 'youtube_thumbnail.jpg')
    img.save(out, quality=92, optimize=True)
    print(out, f'{os.path.getsize(out) / 1e3:.0f} kB')


if __name__ == '__main__':
    main()
