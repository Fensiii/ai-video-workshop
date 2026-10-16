"""Cover image: hero lift-off shot + title + evolution timeline strip."""
import sys, numpy as np, skia
from PIL import Image
import render as R, scenes as sc, carrender as cr
from cars import CARS
from carrender import col, poly_path

W, H = 1920, 1080
sc.build_scenes()
R.TEXTS = []
surf = R.frame(53.5)
cv = surf.getCanvas()

# darken top-left for title and bottom for timeline
g = skia.Paint(); g.setShader(skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(900, 520)],
    [col([2, 4, 12], 0.85), col([2, 4, 12], 0)]))
cv.drawRect(skia.Rect(0, 0, W, H), g)
b = skia.Paint(); b.setShader(skia.GradientShader.MakeLinear([skia.Point(0, 820), skia.Point(0, H)],
    [col([2, 4, 12], 0), col([2, 4, 12], 0.92)]))
cv.drawRect(skia.Rect(0, 820, W, H), b)

# title block
sc.draw_logo(cv, 150, 170, 96, col([255, 255, 255]))
FT = skia.Font(skia.Typeface('Noto Sans CJK SC Black'), 128); FT.setEdging(skia.Font.Edging.kAntiAlias)
FS = skia.Font(skia.Typeface('Noto Sans CJK SC Light'), 50); FS.setEdging(skia.Font.Edging.kAntiAlias)
FY = skia.Font(skia.Typeface('Noto Sans CJK SC Medium'), 26); FY.setEdging(skia.Font.Edging.kAntiAlias)
sh = skia.Paint(AntiAlias=True, Color=col([0, 0, 0], 0.6)); sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 14))
title = '特斯拉进化史'
cv.drawString(title, 233, 228, FT, sh)
cv.drawString(title, 230, 224, FT, skia.Paint(AntiAlias=True, Color=col([255, 255, 255])))
cv.drawRect(skia.Rect(234, 262, 238, 316), skia.Paint(Color=col([230, 30, 45])))
cv.drawString('2008  →  2026', 262, 306, FS, skia.Paint(AntiAlias=True, Color=col([215, 235, 255])))

# timeline strip: every generation's true-scale silhouette
s = 0.040
gap = 34
total = sum(c.L for c in CARS) * s + gap * (len(CARS) - 1)
x = (W - total) / 2
base = 1012
for i, c in enumerate(CARS):
    cx = x + c.L * s / 2
    hero = i == len(CARS) - 1
    acc = [230, 30, 45] if hero else [110, 220, 255]
    cv.save(); cv.translate(cx, base); cv.scale(s, -s)
    fill = skia.Paint(AntiAlias=True, Color=col(acc, 0.22 if hero else 0.12)); cv.drawPath(poly_path(c.outline), fill)
    st = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=1.6 / s, Color=col(acc, 0.95))
    cv.drawPath(poly_path(c.outline), st)
    for (wx, r) in (c.wf, c.wr):
        cv.drawCircle(wx, r, r, skia.Paint(AntiAlias=True, Color=col([4, 8, 18])))
        cv.drawCircle(wx, r, r, st)
    cv.restore()
    w = FY.measureText(c.year)
    cv.drawString(c.year, cx - w / 2, base + 40, FY, skia.Paint(AntiAlias=True, Color=col([255, 255, 255], 1 if hero else 0.75)))
    if i < len(CARS) - 1:
        ax = x + c.L * s + gap / 2
        cv.drawLine(ax - 8, base - 22, ax + 6, base - 22, skia.Paint(AntiAlias=True, StrokeWidth=2, Color=col([255, 255, 255], 0.45)))
    x += c.L * s + gap
cv.drawLine(80, base + 2, W - 80, base + 2, skia.Paint(AntiAlias=True, StrokeWidth=1, Color=col([255, 255, 255], 0.25)))

arr = surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)[..., :3]
Image.fromarray(arr).save(sys.argv[1], quality=95) if sys.argv[1].endswith('.jpg') else Image.fromarray(arr).save(sys.argv[1])
