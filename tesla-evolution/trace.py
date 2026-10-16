import sys, numpy as np
from PIL import Image, ImageDraw, ImageFont
from cars import SPECS, catmull
SRC = Image.open('/root/.claude/uploads/81d729bb-573f-5c02-b33c-cc74684c9975/791e989a-image.jpg').convert('RGB')
F = ImageFont.truetype('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc', 13)
K = 3
def run(i, out):
    sp = SPECS[i]; tip, fa, ra, tail, ground, roof = sp['anch']
    x0, x1 = int(tip) - 15, int(tail) + 15; y0, y1 = int(roof) - 15, int(ground) + 8
    im = SRC.crop((x0, y0, x1, y1)).resize(((x1 - x0) * K, (y1 - y0) * K), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    T = lambda x, y: ((x - x0) * K, (y - y0) * K)
    for gx in range(x0 - x0 % 10 + 10, x1, 10):
        d.line([T(gx, y0), T(gx, y1)], fill=(0, 140, 255) if gx % 50 else (255, 0, 255), width=1)
        if gx % 50 == 0: d.text((T(gx, y0)[0] + 2, 2), str(gx), fill=(255, 0, 255), font=F)
    for gy in range(y0 - y0 % 10 + 10, y1, 10):
        d.line([T(x0, gy), T(x1, gy)], fill=(0, 140, 255) if gy % 50 else (255, 0, 255), width=1)
        d.text((2, T(x0, gy)[1] + 1), str(gy), fill=(255, 255, 0), font=F)
    o = sp['outline']; dense = catmull([(p[0], p[1]) for p in o], [bool(p[2]) for p in o], seg=12)
    d.line([T(*p) for p in np.vstack([dense, dense[:1]])], fill=(0, 255, 100), width=2)
    for p in o: d.ellipse([T(p[0], p[1])[0] - 4, T(p[0], p[1])[1] - 4, T(p[0], p[1])[0] + 4, T(p[0], p[1])[1] + 4], outline=(0, 255, 100))
    dl = sp['dlo']; d.line([T(*p) for p in dl + dl[:1]], fill=(255, 220, 0), width=2)
    for k in ('head', 'tail', 'mirror'):
        v = sp.get(k)
        if v: d.line([T(*p) for p in v + v[:1]], fill=(255, 80, 80), width=2)
    for c in sp['cuts']: d.line([T(c, y0), T(c, y1)], fill=(255, 255, 255), width=1)
    r = sp['tire'][0] / 2 * (ground - roof) / sp['H']
    for cx in (fa, ra):
        a, b = T(cx - r, ground - 2 * r), T(cx + r, ground)
        d.ellipse([a, b], outline=(255, 0, 255), width=2)
    im.save(out)
for i in map(int, sys.argv[2:]):
    run(i, f'{sys.argv[1]}/tr_{SPECS[i]["key"]}.png')
