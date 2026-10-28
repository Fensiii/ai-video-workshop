"""YouTube thumbnail (1280x720 JPEG) built from the same chart renderer.

ASSET=eth python3 cover.py OUT.jpg
"""
import math
import os
import sys

import numpy as np
import skia
from PIL import Image

import common as B
import render as R
from render import P, col, draw_text, font, radial, mix

COVERS = {
    'eth': dict(title='ETHEREUM', sub='11 YEARS IN 3 MINUTES', kicker='PRICE HISTORY  ·  2015 — 2026',
                marks=[('2018-12-15', '−94%', B.DOWN, 'below'), ('2025-08-22', '$4,831 ATH', B.GOLD, 'right')]),
    'sol': dict(title='SOLANA', sub='THE −96% COMEBACK', kicker='PRICE HISTORY  ·  2020 — 2026',
                marks=[('2022-12-29', '−96%', B.DOWN, 'below'), ('2025-01-18', '$262 ATH', B.GOLD, 'right')]),
}


def pill(c, txt, x, y, f, rgb, align='center'):
    w = R.text_width(f, txt, 1.0)
    x0 = x - w / 2 - 18 if align == 'center' else x
    h = f.getSize()
    rect = skia.Rect(x0, y - h - 12, x0 + w + 36, y + 16)
    c.drawRoundRect(rect, 8, 8, P((6, 12, 24), 0.88))
    c.drawRoundRect(rect, 8, 8, P(rgb, 0.95, stroke=2.4))
    draw_text(c, txt, x0 + 18, y, f, P(mix(rgb, (255, 255, 255), 0.15), 1.0), spacing=1.0)


def main():
    cfg = COVERS[B.ASSET]
    arr = np.zeros((B.H, B.W, 4), np.uint8)
    surf = skia.Surface(arr)
    c = surf.getCanvas()
    c.clear(skia.Color4f(0.004, 0.012, 0.047, 1))
    R.draw_background(c, 40.0, 0.18, 0.05)
    R.draw_dust(c, 40.0)
    cam = R.overview_cam(x_left=-60.0, hx=1640.0, OV_TOP=540.0, OV_BOT=1030.0, theta_deg=20.0)
    R.CUR_M = skia.Matrix()
    R.LABEL_BOXES = []
    R.draw_grid(c, cam, 0.0, alpha=0.8, labels=False)
    R.draw_curtains(c, cam, 0.0, intensity=1.15)
    R.draw_line(c, cam, 0.0, style=1.35)
    R.draw_head(c, cam, 0.0, 0.0, scale=1.2)
    R.draw_vignette(c)
    # lock-on marks
    for ds, txt, rgb, where in cfg['marks']:
        d = B.day_of(ds)
        x, y, _ = cam.proj(d, B.LOGP[d])
        x, y = float(x), float(y)
        radial(c, x, y, 120, rgb, 0.45)
        R._reticle(c, x, y, 46, mix(rgb, (255, 255, 255), 0.3), 1.0, ln=20)
        f = font('xbold', 54)
        if where == 'below':
            pill(c, txt, x, y + 128, f, rgb)
        else:
            pill(c, txt, x + 78, y + 20, f, rgb, align='left')
    # title block
    lp = skia.Paint(AntiAlias=True)
    draw_text(c, cfg['kicker'], 92, 120, font('bold', 30), P((205, 210, 226), 1.0), spacing=7)
    ft = font('serif', 196)
    draw_text(c, cfg['title'], 84, 318, ft, P((240, 196, 110), 0.55, blur=22), spacing=6)
    sh = skia.GradientShader.MakeLinear([skia.Point(0, 170), skia.Point(0, 325)],
                                        [col((255, 242, 205)), col((246, 214, 150)), col((214, 166, 92))], [0.0, 0.5, 1.0])
    lp.setShader(sh)
    draw_text(c, cfg['title'], 84, 318, ft, lp, spacing=6)
    fs = font('xbold', 70)
    draw_text(c, cfg['sub'], 92, 418, fs, P((0, 0, 0), 0.6, blur=10), spacing=3)
    draw_text(c, cfg['sub'], 92, 418, fs, P((255, 255, 255), 1.0), spacing=3)
    img = Image.fromarray(arr[..., :3].copy()).resize((1280, 720), Image.LANCZOS)
    img.save(sys.argv[1], quality=92)
    print('wrote', sys.argv[1], os.path.getsize(sys.argv[1]) // 1024, 'KB')


if __name__ == '__main__':
    main()
