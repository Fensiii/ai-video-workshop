"""Tesla side-profile geometry.

All geometry ends up in "centered" millimetre coordinates:
  xc > 0 toward the front bumper (the car faces screen-right), xc = 0 at mid-length
  y  = height above ground in mm
Photo-traced cars are transcribed in reference-photo pixels and mapped onto official
dimensions with a piecewise axle-anchored transform so that length, height, wheelbase
and overhangs are 1:1.
"""
import math
import numpy as np
import skia

N_PART = 96      # resample count for every morphable part outline
N_OUTLINE = 320  # resample count for the full silhouette (wireframe)


# ---------------------------------------------------------------- helpers
def catmull(points, sharp, closed=True, seg=14):
    """Smooth a polygon with Catmull-Rom, keeping corners flagged sharp."""
    n = len(points)
    P = [np.array(p, float) for p in points]
    if not any(sharp):
        out = []
        for i in range(n):
            p0, p1, p2, p3 = P[i - 1], P[i], P[(i + 1) % n], P[(i + 2) % n]
            for k in range(seg):
                t = k / seg
                out.append(_cr(p0, p1, p2, p3, t))
        return np.array(out)
    # rotate so we start on a sharp point
    s0 = sharp.index(True)
    P = P[s0:] + P[:s0]
    S = list(sharp[s0:]) + list(sharp[:s0])
    P.append(P[0]); S.append(True)
    out = []
    chain = [P[0]]
    for i in range(1, len(P)):
        chain.append(P[i])
        if S[i]:
            out.extend(_open_chain(chain, seg))
            chain = [P[i]]
    return np.array(out)


def _open_chain(c, seg):
    if len(c) == 2:
        return [c[0] + (c[1] - c[0]) * k / seg for k in range(seg)]
    ext = [c[0] * 2 - c[1]] + c + [c[-1] * 2 - c[-2]]
    out = []
    for i in range(1, len(ext) - 2):
        for k in range(seg):
            out.append(_cr(ext[i - 1], ext[i], ext[i + 1], ext[i + 2], k / seg))
    return out


def _cr(p0, p1, p2, p3, t):
    t2, t3 = t * t, t * t * t
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                  + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)


def poly_path(pts):
    p = skia.Path()
    p.moveTo(float(pts[0][0]), float(pts[0][1]))
    for x, y in pts[1:]:
        p.lineTo(float(x), float(y))
    p.close()
    return p


def path_contours(path):
    """Return list of polygons (np arrays) for each contour of a path."""
    out = []
    pm = skia.PathMeasure(path, False, 1.0)
    while True:
        L = pm.getLength()
        if L >= 1:
            n = max(8, int(L / 6))
            pts = []
            for i in range(n):
                pos, _ = pm.getPosTan(L * i / n)
                pts.append((pos.x(), pos.y()))
            out.append(np.array(pts))
        if not pm.nextContour():
            break
    return out


def area(poly):
    x, y = poly[:, 0], poly[:, 1]
    return 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)


def resample(poly, n):
    pts = np.vstack([poly, poly[:1]])
    d = np.sqrt(((pts[1:] - pts[:-1]) ** 2).sum(1))
    cum = np.concatenate([[0], np.cumsum(d)])
    tot = cum[-1]
    s = np.linspace(0, tot, n, endpoint=False)
    x = np.interp(s, cum, pts[:, 0])
    y = np.interp(s, cum, pts[:, 1])
    return np.stack([x, y], 1)


def canonical(poly, n):
    """Resample to n points, CCW (in y-up space), starting at the point straight above centroid."""
    if poly is None or len(poly) < 3:
        return None
    if area(poly) < 0:
        poly = poly[::-1]
    r = resample(poly, n)
    c = r.mean(0)
    ang = np.arctan2(r[:, 1] - c[1], r[:, 0] - c[0])
    i0 = int(np.argmin(np.abs(((ang - math.pi / 2) + math.pi) % (2 * math.pi) - math.pi)))
    return np.roll(r, -i0, axis=0)


def tiny(cx, cy, n, rad=2.0):
    a = np.linspace(math.pi / 2, math.pi / 2 + 2 * math.pi, n, endpoint=False)
    return np.stack([cx + rad * np.cos(a), cy + rad * np.sin(a)], 1)


def op(a, b, kind):
    return skia.Op(a, b, kind)


# ---------------------------------------------------------------- car specs
# Photo-traced cars: points are in pixels of the user's side-view comparison sheet.
def photo_mapper(anch, L, H, WB, FO):
    tip, fa, ra, tail, ground, roof = anch
    RO = L - WB - FO

    def m(px, py):
        if px <= fa:
            xf = (px - tip) / (fa - tip) * FO
        elif px <= ra:
            xf = FO + (px - fa) / (ra - fa) * WB
        else:
            xf = FO + WB + (px - ra) / (tail - ra) * RO
        y = (ground - py) * H / (ground - roof)
        return (L / 2 - xf, y)
    return m


def mm_mapper(L):
    return lambda xf, y: (L / 2 - xf, y)


SPECS = []


def add(**k):
    SPECS.append(k)


# 1. Roadster 2008 (authored in mm, from-front-tip coordinates)
add(key='roadster', year='2008', title='第一款量产车',
    L=3946, H=1127, WB=2352, FO=780, tire=(600, 635), rim='star5', rimc=(205, 208, 212),
    color=(172, 18, 26), metal=0.55, glass_roof=False, roof_black=False, map='mm',
    outline=[(70, 140, 1), (12, 250, 0), (0, 350, 0), (40, 470, 0), (190, 560, 0), (460, 640, 0),
             (760, 705, 0), (1080, 742, 0), (1260, 765, 1), (1690, 1085, 0), (1900, 1127, 0),
             (2180, 1112, 0), (2430, 1000, 0), (2800, 900, 0), (3300, 880, 0), (3700, 860, 0),
             (3880, 830, 1), (3940, 720, 0), (3946, 560, 0), (3920, 380, 0), (3860, 230, 0), (3780, 160, 1),
             (3500, 150, 0), (2600, 145, 0), (1300, 145, 0), (300, 150, 1)],
    dlo=[(1330, 800), (1690, 1060), (1950, 1080), (2180, 1040), (2290, 860), (1500, 790)],
    belt=((1260, 790), (2330, 900)),
    cuts=[250, 1250, 1800, 2330, 3700], hidden=[2],
    head=[(130, 515), (430, 612), (440, 588), (160, 498)],
    tail=[(3860, 800), (3938, 790), (3940, 700), (3870, 708)],
    mirror=[(1300, 820), (1400, 830), (1420, 760), (1320, 752)],
    detail=[(2420, 630), (2720, 570), (2720, 420), (2470, 470)],
    handles=[(2050, 690, 90)], chrome=False)

# 2. Model S 2012 (traced, row 1 of reference sheet)
add(key='models', year='2012', title='豪华纯电轿车',
    L=4978, H=1435, WB=2960, FO=935, tire=(703, 703), rim='turbine10', rimc=(200, 204, 210),
    color=(22, 24, 28), metal=0.9, glass_roof=False, roof_black=False, map='photo',
    anch=(607, 693.5, 1041, 1141, 192, 39),
    outline=[(617, 172, 1), (608, 145, 0), (607.5, 130, 0), (614, 118, 0), (645, 103, 0), (700, 93, 0),
             (770, 80, 0), (850, 46, 0), (920, 39, 0), (995, 47, 0), (1060, 69, 0), (1124, 77, 1),
             (1131, 88, 0), (1140, 125, 0), (1137, 160, 0), (1110, 174, 1), (1000, 175, 0),
             (740, 175, 0), (650, 173, 1)],
    dlo=[(792, 84), (835, 55), (880, 46), (940, 42), (1000, 46), (1040, 55), (1052, 61), (1000, 71), (900, 79)],
    belt=((785, 85), (1050, 68)),
    cuts=[648, 775, 890, 1000, 1112], hidden=[],
    head=[(611, 118), (655, 107), (659, 116), (618, 126)],
    nose=[(607.5, 128), (617, 124), (619, 150), (609, 148)],
    tail=[(1100, 92), (1130, 87.5), (1132, 100), (1102, 101)],
    mirror=[(790, 75), (818, 71), (822, 86), (796, 88)],
    handles=[(875, 97.5, 26), (997, 90, 24)], chrome=True)

# 3. Model X 2015 (traced, row 3)
add(key='modelx', year='2015', title='鹰翼门 SUV',
    L=5037, H=1684, WB=2965, FO=980, tire=(747, 747), rim='turbine10', rimc=(196, 200, 205),
    color=(232, 234, 236), metal=0.45, glass_roof=False, roof_black=False, map='photo',
    anch=(606, 692.5, 1040, 1140, 700, 525),
    outline=[(610, 673, 1), (606, 645, 0), (610, 618, 0), (645, 601, 0), (700, 590, 0), (740, 583, 0),
             (800, 549, 0), (880, 526, 0), (930, 525, 0), (1020, 531, 0), (1095, 550, 0),
             (1137, 572, 1), (1132, 585, 0), (1140, 620, 0), (1137, 660, 0), (1110, 676, 1),
             (985, 676, 0), (745, 676, 0), (645, 675, 1)],
    dlo=[(795, 584), (815, 566), (845, 547), (880, 535), (930, 530), (1000, 532), (1040, 537), (1074, 558), (1040, 571), (900, 580)],
    belt=((795, 586), (1072, 563)),
    cuts=[650, 755, 892, 1035, 1105], hidden=[],
    head=[(612, 617), (655, 606), (660, 612), (617, 621)],
    tail=[(1100, 595), (1135, 582.5), (1136, 600), (1104, 600)],
    mirror=[(770, 573), (792, 570), (795, 585), (773, 586)],
    handles=[(895, 593.5, 30)], chrome=True, falcon=3)

# 4. Model 3 2017 (traced, row 2)
add(key='model3', year='2017', title='走向大众',
    L=4694, H=1443, WB=2875, FO=840, tire=(669, 669), rim='aero', rimc=(70, 72, 76),
    color=(150, 14, 22), metal=0.8, glass_roof=True, roof_black=False, map='photo',
    anch=(604, 692.5, 1048.5, 1145, 454, 285),
    outline=[(615, 427, 1), (606, 400, 0), (604, 385, 0), (615, 376, 0), (670, 352, 0), (735, 342, 0),
             (770, 337, 0), (820, 305, 0), (880, 287.5, 0), (930, 285, 0), (1010, 295, 0),
             (1070, 312, 0), (1135, 330, 1), (1138, 343, 0), (1141, 385, 0), (1140, 420, 0),
             (1120, 435, 1), (1000, 437.5, 0), (740, 437.5, 0), (645, 435, 1)],
    dlo=[(782, 339), (815, 318), (850, 305), (900, 300), (1000, 302), (1045, 311), (1062, 320), (1045, 326), (900, 333)],
    belt=((785, 342), (1062, 324)),
    cuts=[650, 757, 902, 1022, 1112], hidden=[],
    head=[(607, 379), (650, 365), (657, 370), (612, 383)],
    tail=[(1105, 340), (1135, 335), (1137, 352), (1115, 348)],
    mirror=[(780, 330), (805, 327.5), (810, 340), (785, 342.5)],
    handles=[(880, 352.5, 24), (1005, 347.5, 24)], chrome=False)

# 5. Model Y 2020 (traced, row 4)
add(key='modely', year='2020', title='更大的空间',
    L=4751, H=1624, WB=2890, FO=875, tire=(712, 712), rim='gemini', rimc=(95, 98, 104),
    color=(150, 154, 160), metal=0.85, glass_roof=True, roof_black=False, map='photo',
    anch=(602.5, 695, 1047.5, 1142.5, 970, 781),
    outline=[(607, 940, 1), (603, 905, 0), (602.5, 895, 0), (610, 880, 0), (660, 861, 0), (735, 840, 0),
             (760, 836, 0), (820, 805, 0), (880, 786, 0), (930, 781, 0), (1020, 790, 0),
             (1095, 812, 0), (1132, 825, 1), (1135, 840, 0), (1140, 875, 0), (1145, 897, 0),
             (1140, 922, 0), (1120, 937, 1), (1000, 945, 0), (742, 945, 0), (640, 942, 1)],
    dlo=[(766, 842), (820, 808), (900, 798), (1050, 800), (1070, 812), (1025, 832), (900, 839)],
    belt=((765, 843), (1070, 816)),
    cuts=[650, 757.5, 900, 1030, 1112], hidden=[],
    head=[(610, 881), (650, 870), (656, 876), (615, 888)],
    tail=[(1100, 842), (1135, 840), (1137, 855), (1110, 852)],
    mirror=[(780, 827.5), (802.5, 825), (805, 840), (782.5, 841.5)],
    handles=[(880, 856, 24), (1005, 847.5, 24)], chrome=False)

# 6. Cybertruck 2023 (traced, row 6) - all corners sharp
add(key='cybertruck', year='2023', title='不锈钢车身',
    L=5683, H=1791, WB=3635, FO=1035, tire=(878, 878), rim='ct', rimc=(60, 62, 66),
    color=(158, 160, 158), metal=0.35, glass_roof=False, roof_black=False, map='photo', steel=True,
    anch=(587.5, 670, 1038.5, 1160, 1472.5, 1290),
    outline=[(600, 1445, 1), (587.5, 1405, 1), (587.5, 1370, 1), (607.5, 1360, 1), (822.5, 1290, 1),
             (1157.5, 1332, 1), (1155, 1397, 1), (1160, 1402, 1), (1160, 1420, 1), (1142, 1435, 1),
             (990, 1438, 1), (720, 1438, 1), (605, 1443, 1)],
    dlo=[(662, 1347), (820, 1298), (947, 1307.5), (947, 1332), (735, 1345)],
    belt=((660, 1348), (1150, 1333)),
    cuts=[622, 732.5, 847.5, 952.5, 1130], hidden=[],
    head=[(587.5, 1362), (607.5, 1359.5), (607.5, 1366), (589, 1369)],
    tail=[(1110, 1331), (1157.5, 1332.5), (1157.5, 1337), (1110, 1336)],
    mirror=[(735, 1331), (758, 1326), (761, 1346), (740, 1348)],
    handles=[], chrome=False, hexarch=True)

# 7. Cybercab 2024 (authored; official dims unpublished -> estimated from public imagery)
add(key='cybercab', year='2024', title='自动驾驶出行',
    L=4230, H=1380, WB=2780, FO=760, tire=(720, 720), rim='cab', rimc=(52, 54, 58),
    color=(196, 172, 128), metal=0.75, glass_roof=False, roof_black=False, map='mm',
    outline=[(50, 180, 1), (5, 330, 0), (10, 500, 0), (120, 620, 0), (480, 760, 0), (900, 860, 0),
             (1500, 1240, 0), (2000, 1368, 0), (2400, 1380, 0), (3000, 1300, 0), (3600, 1110, 0),
             (4060, 905, 1), (4230, 830, 1), (4228, 600, 0), (4180, 300, 0), (4100, 170, 1),
             (3700, 150, 0), (1100, 145, 0), (300, 160, 1)],
    dlo=[(980, 890), (1520, 1212), (2250, 1295), (2720, 1190), (2680, 950), (1500, 905)],
    belt=((960, 890), (3300, 1000)),
    cuts=[300, 950, 1850, 2780, 3900], hidden=[2],
    head=[(12, 560), (190, 652), (196, 634), (16, 540)],
    tail=[(4060, 893), (4230, 828), (4230, 812), (4060, 877)],
    mirror=None, handles=[], chrome=False)

# 8. Roadster (2026 lift-off demo; dims estimated)
add(key='roadster2', year='2026', title='腾空',
    L=4500, H=1170, WB=2650, FO=900, tire=(680, 710), rim='rs2', rimc=(46, 48, 52),
    color=(238, 240, 242), metal=0.5, glass_roof=True, roof_black=False, map='mm',
    outline=[(60, 170, 1), (0, 300, 0), (20, 385, 0), (200, 500, 0), (600, 665, 0), (1000, 785, 0),
             (1450, 850, 0), (2000, 1120, 0), (2350, 1170, 0), (2800, 1120, 0), (3300, 1000, 0),
             (3900, 865, 0), (4420, 805, 1), (4500, 780, 1), (4492, 560, 0), (4440, 300, 0),
             (4380, 190, 1), (4000, 165, 0), (1300, 150, 0), (320, 160, 1)],
    dlo=[(1560, 865), (2000, 1100), (2550, 1122), (3000, 1025), (2820, 885)],
    belt=((1450, 860), (3300, 905)),
    cuts=[280, 1450, 2200, 2860, 4100], hidden=[2],
    head=[(60, 425), (380, 525), (392, 505), (72, 405)],
    tail=[(4370, 802), (4500, 782), (4500, 765), (4370, 786)],
    mirror=[(1500, 880), (1610, 890), (1630, 830), (1520, 822)],
    detail=[(2620, 640), (2980, 600), (3010, 540), (2700, 560)],
    handles=[], chrome=False)


# ---------------------------------------------------------------- build
class Car:
    pass


def build(spec):
    c = Car()
    c.__dict__.update(spec)
    L, H, WB, FO = spec['L'], spec['H'], spec['WB'], spec['FO']
    m = photo_mapper(spec['anch'], L, H, WB, FO) if spec['map'] == 'photo' else mm_mapper(L)

    # x positions in from-front coordinates -> centered
    def cx_of(v):
        if spec['map'] == 'photo':
            return m(v, 0)[0]
        return L / 2 - v

    pts = [m(p[0], p[1]) for p in spec['outline']]
    sharp = [bool(p[2]) for p in spec['outline']]
    dense = catmull(pts, sharp, seg=16)
    c.outline_raw = dense
    rf, rr = spec['tire'][0] / 2, spec['tire'][1] / 2
    c.wf = (L / 2 - FO, rf)
    c.wr = (L / 2 - FO - WB, rr)
    body = poly_path(dense)
    for (wx, r) in (c.wf, c.wr):
        if spec.get('hexarch'):
            hx = [(-1.22, -0.2), (-1.05, 0.72), (-0.62, 1.16), (0.62, 1.16), (1.05, 0.72), (1.22, -0.2), (1.22, -1.5), (-1.22, -1.5)]
            arch = poly_path([(wx + a * r, r + b * r) for a, b in hx])
        else:
            arch = skia.Path()
            arch.addCircle(wx, r, r + 38)
            arch.addRect(skia.Rect(wx - r - 38, -500, wx + r + 38, r))
        body = op(body, arch, skia.PathOp.kDifference_PathOp)
    c.body = body
    c.outline = canonical(dense, N_OUTLINE)

    belt = [m(*spec['belt'][0]), m(*spec['belt'][1])]
    (bx0, by0), (bx1, by1) = belt  # bx0 front (larger xc)
    big = 20000
    lower = skia.Path()
    lower.moveTo(big, by0); lower.lineTo(bx0, by0); lower.lineTo(bx1, by1); lower.lineTo(-big, by1)
    lower.lineTo(-big, -big); lower.lineTo(big, -big); lower.close()
    c.belt = belt
    cuts = sorted([cx_of(v) for v in spec['cuts']], reverse=True)  # front to rear
    c.cuts = cuts
    c.hidden = spec.get('hidden', [])
    bounds = [big] + cuts + [-big]
    dlo = poly_path(catmull([m(*p) for p in spec['dlo']], [True] * len(spec['dlo']), seg=2))
    c.dlo = dlo
    parts = []
    for k in range(len(bounds) - 1):
        rect = skia.Path(); rect.addRect(skia.Rect(bounds[k + 1], -big, bounds[k], big))
        slab = op(body, rect, skia.PathOp.kIntersect_PathOp)
        lo = op(slab, lower, skia.PathOp.kIntersect_PathOp)
        up = op(slab, lower, skia.PathOp.kDifference_PathOp)
        gl = op(op(dlo, rect, skia.PathOp.kIntersect_PathOp), body, skia.PathOp.kIntersect_PathOp)
        midx = (max(bounds[k + 1], -L / 2) + min(bounds[k], L / 2)) / 2
        for kind, p, yy in (('lower', lo, H * 0.35), ('upper', up, H * 0.85), ('glass', gl, H * 0.8)):
            cs = path_contours(p)
            poly = max(cs, key=lambda q: abs(area(q))) if cs else None
            if poly is None or abs(area(poly)) < 2000:
                poly = tiny(midx, yy, N_PART)
            parts.append((kind, k, canonical(poly, N_PART)))
    for kind in ('head', 'tail', 'mirror', 'detail', 'nose'):
        v = spec.get(kind)
        if v:
            poly = catmull([m(*p) for p in v], [True] * len(v), seg=3)
            parts.append((kind, 0, canonical(poly, N_PART)))
        else:
            ref = {'head': (L / 2, H * 0.4), 'tail': (-L / 2, H * 0.6), 'mirror': (L * 0.2, H * 0.7),
                   'detail': (-L * 0.2, H * 0.4), 'nose': (L / 2, H * 0.3)}[kind]
            parts.append((kind, 0, tiny(ref[0], ref[1], N_PART, 1.0)))
    c.parts = parts
    c.handles = [(m(x, y)[0], m(x, y)[1], w * (L / ((spec['anch'][3] - spec['anch'][0]) if spec['map'] == 'photo' else L)))
                 for (x, y, w) in spec.get('handles', [])]
    if spec['map'] == 'mm':
        c.handles = [(L / 2 - x, y, w) for (x, y, w) in spec.get('handles', [])]
    c.color = np.array(spec['color'], float)
    c.rimc = np.array(spec['rimc'], float)
    c.falcon = spec.get('falcon')
    c.steel = spec.get('steel', False)
    return c


CARS = [build(s) for s in SPECS]
