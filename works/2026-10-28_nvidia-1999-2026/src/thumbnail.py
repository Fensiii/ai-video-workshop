"""YouTube thumbnail (1280x720 JPEG): the whole price history plus a few big words."""
import math
import os
import sys

import numpy as np
import skia

import nvda_common as B
import render as R
from nvda_common import W, H, LOGP, NDAYS, PRICE


def poster_cam(x0, y0, xh, yh, theta_deg):
    """camera that maps day 0 to (x0, y0) and the last day to the head at (xh, yh)"""
    h = NDAYS - 1.0
    lh = LOGP[-1]
    theta = math.radians(theta_deg)
    st, ct = math.sin(theta), math.cos(theta)
    f = B.F_CAM
    xoff = xh - B.CX
    u0 = f * (x0 - B.CX - xoff) / (f * ct + (x0 - B.CX) * st)
    k = -u0 / h
    den0 = f - u0 * st
    yoff = B.CY - yh
    v0 = (B.CY - y0) * den0 / f - yoff
    s = v0 / (LOGP[0] - lh)
    return R.Cam(h, lh, k, s, xh, yh, theta, 0.0)


def main(out):
    arr = np.zeros((H, W, 4), np.uint8)
    surf = skia.Surface(arr)
    c = surf.getCanvas()
    c.clear(skia.Color4f(0.004, 0.012, 0.047, 1))
    R.CUR_M = skia.Matrix()
    R.draw_background(c, 40.0, 0.55, 0.0)
    cam = poster_cam(250, 1010, 1730, 330, 14.0)
    R.draw_grid(c, cam, 0.0, alpha=0.55, labels=False)
    R.draw_curtains(c, cam, 0.0, intensity=0.95)
    R.draw_line(c, cam, 0.0, style=0.95)
    R.draw_head(c, cam, 0.0, 0.6, scale=1.2)
    R.draw_vignette(c)
    # title block
    f = R.font('serif_k', 210)
    title = 'NVIDIA'
    sp = 10
    R.draw_text(c, title, 80, 250, f, R.P((150, 220, 90), 0.5, blur=22), spacing=sp)
    sh = skia.GradientShader.MakeLinear([skia.Point(0, 90), skia.Point(0, 255)],
                                        [R.col(R.TITLE_GRAD[0]), R.col(R.TITLE_GRAD[1]), R.col(R.TITLE_GRAD[2])],
                                        [0.0, 0.5, 1.0])
    R.draw_text(c, title, 80, 250, f, skia.Paint(AntiAlias=True, Shader=sh), spacing=sp)
    p0, p1 = PRICE[0], PRICE[-1]
    fp = R.font('light', 92)
    R.draw_text(c, f'${p0:.2f}  →  ${p1:,.0f}', 92, 392, fp, R.P((0, 0, 0), 0.6, blur=14), spacing=1)
    R.draw_text(c, f'${p0:.2f}  →  ${p1:,.0f}', 92, 392, fp, R.P((248, 250, 255)), spacing=1)
    R.draw_text(c, f'{B.D0.year} — {B.DATES[-1].year}', 96, 470, R.font('semi', 44),
                R.P((214, 196, 150)), spacing=10)
    fm = R.font('serif', 132)
    mult = f'{p1 / p0:,.0f}×'
    R.draw_text(c, mult, 86, 650, fm, R.P((245, 196, 110), 0.45, blur=18), spacing=3)
    shg = skia.GradientShader.MakeLinear([skia.Point(0, 555), skia.Point(0, 655)],
                                         [R.col((252, 230, 175)), R.col((243, 198, 112))], [0, 1])
    R.draw_text(c, mult, 86, 650, fm, skia.Paint(AntiAlias=True, Shader=shg), spacing=3)
    im = surf.makeImageSnapshot()
    small = skia.Surface(1280, 720)
    small.getCanvas().drawImageRect(im, skia.Rect(0, 0, 1280, 720),
                                    skia.SamplingOptions(skia.CubicResampler.Mitchell()), skia.Paint())
    small.makeImageSnapshot().save(out, skia.kJPEG, 92)
    print('wrote', out)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(B.ROOT, 'out', 'thumbnail.jpg'))
