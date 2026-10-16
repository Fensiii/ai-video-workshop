import sys, numpy as np, skia
from PIL import Image
import carrender as cr
from cars import CARS
ENV = dict(sky_refl=[170, 185, 205], ground_refl=[60, 60, 64], accent=[90, 220, 255])
W, H = 1920, 1080
def frame(state, falcon=0.0, lights=0.0, bg=(120, 124, 130)):
    surf = skia.Surface(W, H); cv = surf.getCanvas(); cv.clear(skia.Color(*bg))
    cv.save(); cv.translate(cr.CX, cr.GROUND); cv.scale(cr.S, -cr.S)
    cr.draw_car(cv, state, ENV, 0.3, lights=lights, falcon=falcon)
    cv.restore()
    return surf.makeImageSnapshot().toarray()[..., :3][..., ::-1]
if __name__ == '__main__':
    out = sys.argv[1]
    tiles = []
    for i in range(len(CARS)):
        a = frame(cr.CarState(i))
        tiles.append(Image.fromarray(np.ascontiguousarray(a)).crop((260, 340, 1660, 840)).resize((700, 250)))
    sheet = Image.new('RGB', (1400, 1000))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % 2) * 700, (i // 2) * 250))
    sheet.save(out)
