"""Shared data, timeline and camera precompute for the crypto history videos.

The asset is picked with the ASSET environment variable (eth | sol); its story,
copy and tuning live in cfg_<asset>.py.
"""
import csv
import datetime as dt
import importlib
import math
import os

import numpy as np

ASSET = os.environ.get('ASSET', 'eth')
CFG = importlib.import_module(f'cfg_{ASSET}')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HERE = os.path.dirname(os.path.abspath(__file__))
DATA_CSV = next(p for p in (os.path.join(_HERE, 'data', CFG.DATA_CSV), os.path.join(ROOT, 'data', CFG.DATA_CSV))
                if os.path.exists(p))
FONT_DIR = os.path.join(ROOT, 'fonts')
WORK = os.path.join(ROOT, 'work')
OUT = os.path.join(ROOT, 'out', ASSET)
os.makedirs(WORK, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

W, H = 1920, 1080
FPS = 30
T_START = 8.5            # chart starts
T_END = CFG.T_END        # head reaches the final data day
END_LEN = 15.333         # outro after T_END
DURATION = T_END + END_LEN
NFRAMES = int(round(DURATION * FPS))

# ----------------------------------------------------------------------------
# data
# ----------------------------------------------------------------------------

def load_prices():
    dates, prices = [], []
    for r in csv.DictReader(open(DATA_CSV)):
        dates.append(dt.date.fromisoformat(r['date']))
        prices.append(float(r['close']))
    return dates, np.array(prices, dtype=np.float64)


DATES, PRICE = load_prices()
D0 = DATES[0]
NDAYS = len(DATES)
LOGP = np.log10(PRICE)
DAYS = np.arange(NDAYS, dtype=np.float64)


def day_of(s):
    return (dt.date.fromisoformat(s) - D0).days


def date_of(day):
    return D0 + dt.timedelta(days=int(day))


# momentum series (log10 returns)
def _ret(n):
    r = np.zeros(NDAYS)
    r[n:] = LOGP[n:] - LOGP[:-n]
    return r


RET1 = _ret(1)
RET5 = _ret(5)
RET10 = _ret(10)
RET30 = _ret(30)
ATH = np.maximum.accumulate(PRICE)
ATH_DAY = np.zeros(NDAYS, dtype=int)
_cur = 0
for _i in range(NDAYS):
    if PRICE[_i] >= ATH[_i]:
        _cur = _i
    ATH_DAY[_i] = _cur
DRAWDOWN = 1.0 - PRICE / ATH

# ----------------------------------------------------------------------------
# palette (western convention: green/teal = up, red = down)
# ----------------------------------------------------------------------------
GOLD = (236, 200, 132)
BLUE = (150, 190, 250)
UP = (84, 214, 178)
DOWN = (246, 112, 96)
PURPLE = (178, 170, 246)
COLOR_KEYS = {'gold': GOLD, 'blue': BLUE, 'up': UP, 'down': DOWN, 'purple': PURPLE}

KIND_COLOR = {
    'genesis': GOLD, 'peak': GOLD, 'high': GOLD,
    'info': BLUE, 'tech': PURPLE,
    'rally': UP,
    'crash': DOWN, 'crisis': DOWN, 'bottom': DOWN,
}
POSITIVE = ('genesis', 'peak', 'high', 'rally')
NEGATIVE = ('crash', 'crisis', 'bottom')
BRIGHT = ('genesis', 'peak', 'high', 'rally')   # big spark bursts

BLACK_SWANS = CFG.BLACK_SWANS
SHAKE = CFG.SHAKE
BRACKETS = CFG.BRACKETS


class Event:
    def __init__(self, raw):
        (self.t, self.date, self.kind, self.cat, self.title, self.value, self.desc,
         self.tag, self.label) = raw
        self.day = day_of(self.date)
        self.color = KIND_COLOR[self.kind]
        self.positive = self.kind in POSITIVE
        self.negative = self.kind in NEGATIVE
        # camera push-in strength (0 = none)
        if self.kind == 'genesis':
            self.zoom = 0.0
        elif self.date in BLACK_SWANS or self.kind in ('peak', 'bottom'):
            self.zoom = 0.42
        elif self.kind in ('crisis', 'crash', 'high', 'rally'):
            self.zoom = 0.30
        else:
            self.zoom = 0.18
        # camera shake strength in px
        self.shake = SHAKE.get(self.date, {'peak': 6.0, 'bottom': 5.0, 'high': 4.0, 'rally': 6.0,
                                           'crisis': 8.0, 'crash': 10.0}.get(self.kind, 0.0))
        b = BRACKETS.get(self.date)
        self.bracket = (day_of(b[0]), day_of(b[1])) if b else None


EVENTS = [Event(r) for r in CFG.EVENTS_RAW]
ERAS = CFG.ERAS


def fmt_price(p, decimals=None):
    if decimals is None:
        decimals = 2 if p >= 1 else 4
    return f'{p:,.{decimals}f}'


def fmt_level(v):
    if v >= 1:
        return f'{v:,.0f}'
    return f'{v:g}'


def crossing_day(lv):
    """fractional day of the first close at or above lv"""
    d = int(np.argmax(PRICE >= lv))
    if d == 0:
        return 0.0
    l0, l1 = LOGP[d - 1], LOGP[d]
    frac = (math.log10(lv) - l0) / (l1 - l0) if l1 != l0 else 1.0
    return d - 1 + frac


# milestones are time anchors too, so the head slows down when it crosses one
MILESTONE_T = [(lv, crossing_day(lv), t) for lv, t in CFG.MILESTONES]

# ----------------------------------------------------------------------------
# time mapping t -> head day (fractional)
# ----------------------------------------------------------------------------

def _smoother(u):
    return u * u * u * (u * (u * 6 - 15) + 10)


ANCHORS = sorted([(e.t, float(e.day)) for e in EVENTS] + [(t, fd) for _, fd, t in MILESTONE_T]
                 + [(T_END, float(NDAYS - 1))])


def head_day(t):
    if t <= ANCHORS[0][0]:
        return 0.0
    if t >= ANCHORS[-1][0]:
        return float(NDAYS - 1)
    for i in range(len(ANCHORS) - 1):
        t0, d0 = ANCHORS[i]
        t1, d1 = ANCHORS[i + 1]
        if t0 <= t < t1:
            u = (t - t0) / (t1 - t0)
            if i == len(ANCHORS) - 2:
                e = _smoother(u)
            else:
                e = 0.75 * _smoother(u) + 0.25 * u
            return d0 + (d1 - d0) * e
    return float(NDAYS - 1)


def logp_at(day):
    """log10 price at fractional day (linear in log space)."""
    day = min(max(day, 0.0), NDAYS - 1.0)
    i = int(math.floor(day))
    if i >= NDAYS - 1:
        return LOGP[-1]
    f = day - i
    return LOGP[i] * (1 - f) + LOGP[i + 1] * f


FRAME_T = np.arange(NFRAMES) / FPS
HEAD = np.array([head_day(t) for t in FRAME_T])


def time_of_day(day):
    """first frame time at which head >= day"""
    idx = np.searchsorted(HEAD, day)
    idx = min(idx, NFRAMES - 1)
    return FRAME_T[idx]


def era_times():
    out = []
    for i, (s, label, title) in enumerate(ERAS):
        if i == 0:
            t = 12.4
        else:
            t = time_of_day(day_of(s)) + 0.6
        out.append((t, label, title))
    return out


ERA_T = era_times()

# ----------------------------------------------------------------------------
# camera precompute (sequential smoothing)
# ----------------------------------------------------------------------------
F_CAM = 1900.0
CX = 960.0
CY = 450.0


def _ema(prev, target, dt_, tau):
    a = 1.0 - math.exp(-dt_ / tau)
    return prev + (target - prev) * a


def theta_at(t):
    return math.radians(36.0 + 3.0 * math.sin(2 * math.pi * t / 41.0))


def precompute_camera():
    n = NFRAMES
    cam = {k: np.zeros(n) for k in ('k', 's', 'C', 'hx', 'hy', 'theta', 'roll', 'vis',
                                       'up', 'down', 'valcol', 'hl', 'volshake')}
    vol_s = 0.0
    dt_ = 1.0 / FPS
    k_log = None
    s_log = None
    C = None
    upm = dnm = 0.0
    valc = 0.0
    for f in range(n):
        t = FRAME_T[f]
        h = HEAD[f]
        theta = theta_at(t)
        hx = 1173.0 + (1236.0 - 1173.0) * _smoother(min(max((t - 8.5) / 7.0, 0), 1)) \
            + 12.0 * math.sin(2 * math.pi * t / 47.0) * min(max((t - 9) / 6, 0), 1)
        xh = hx - CX
        u_left = F_CAM * (CX + xh) / (F_CAM * math.cos(theta) - CX * math.sin(theta))
        vis = min(max(0.62 * h + 40.0, 110.0), 1350.0)
        k_t = u_left / vis
        lh = logp_at(h)
        lo = int(max(0, math.floor(h - vis)))
        hi = int(min(NDAYS - 1, math.ceil(h)))
        seg = LOGP[lo:hi + 1]
        mn = min(seg.min(), lh)
        mx = max(seg.max(), lh)
        rng = max(mx - mn, 0.32)
        s_t = min(430.0 / rng, 1400.0)
        mid = 0.5 * (mn + mx)
        C_t = 0.55 * mid + 0.45 * lh
        if k_log is None:
            k_log, s_log, C = math.log(k_t), math.log(s_t), C_t
        else:
            k_log = _ema(k_log, math.log(k_t), dt_, 0.9)
            s_log = _ema(s_log, math.log(s_t), dt_, 0.8)
            C = _ema(C, C_t, dt_, 0.55)
        s = math.exp(s_log)
        hy = 600.0 - (lh - C) * s
        if hy < 250:
            C = lh - (600 - 250) / s
            hy = 250.0
        elif hy > 860:
            C = lh - (600 - 860) / s
            hy = 860.0
        # mood: rallies tint the nebula green, sell-offs tint it red
        i = int(min(max(round(h), 0), NDAYS - 1))
        m30 = RET30[i]
        m14 = LOGP[i] - LOGP[max(i - 14, 0)]
        dd = DRAWDOWN[i]
        up_t = min(max((m30 - 0.08) / 0.22, 0), 1) * min(max(1 - dd / 0.25, 0), 1)
        dn_t = min(max((-m14 - 0.04) / 0.12, 0), 1)
        if t < 9:
            up_t = dn_t = 0.0
        upm = _ema(upm, up_t, dt_, 1.2)
        dnm = _ema(dnm, dn_t, dt_, 0.9)
        # value colour: -1 red .. +1 green (14-day momentum)
        vt = min(max(m14 / 0.06, -1), 1) if t >= 9 else 0.0
        valc = _ema(valc, vt, dt_, 0.35)
        cam['k'][f] = math.exp(k_log)
        cam['s'][f] = s
        cam['C'][f] = C
        cam['hx'][f] = hx
        cam['hy'][f] = hy
        cam['theta'][f] = theta
        cam['roll'][f] = math.radians(1.1 * math.sin(2 * math.pi * t / 53.0 + 1.0)) * min(max((t - 9) / 5, 0), 1)
        cam['vis'][f] = vis
        cam['up'][f] = upm
        cam['down'][f] = dnm
        cam['valcol'][f] = valc
        cam['hl'][f] = lh
        # hand-held wobble while the market swings hard (big daily moves near the head)
        vmax = float(np.max(np.abs(RET1[max(i - 2, 0):i + 1])))
        v_t = 5.0 * min(max((vmax - 0.03) / 0.05, 0), 1) if 9.0 <= t <= T_END else 0.0
        vol_s = _ema(vol_s, v_t, dt_, 0.22)
        cam['volshake'][f] = vol_s
    return cam


_CAM_CACHE = os.path.join(WORK, f'cam_cache_{ASSET}.npz')


def get_camera():
    src = max(os.path.getmtime(__file__), os.path.getmtime(CFG.__file__), os.path.getmtime(DATA_CSV))
    if os.path.exists(_CAM_CACHE) and os.path.getmtime(_CAM_CACHE) > src:
        z = np.load(_CAM_CACHE)
        return {k: z[k] for k in z.files}
    cam = precompute_camera()
    np.savez(_CAM_CACHE, **cam)
    return cam


# ----------------------------------------------------------------------------
# self-check: every number on screen must match the series
# ----------------------------------------------------------------------------

def _fmt_pct(x):
    s = f'{abs(x) * 100:,.1f}%'
    return ('+' if x >= 0 else '−') + s


def verify():
    ok = True
    ts = [a[0] for a in ANCHORS]
    days = [a[1] for a in ANCHORS]
    if ts != sorted(ts) or days != sorted(days):
        print('!! anchors not monotonic', ANCHORS)
        ok = False
    for a, b in zip(ANCHORS, ANCHORS[1:]):
        if b[0] - a[0] < 2.45:
            print(f'!! anchors too close: {a} {b}')
    for e in EVENTS:
        p = PRICE[e.day]
        notes = []
        if e.value.startswith('$'):
            want = '$' + fmt_price(p)
            if e.value not in (want, '$' + f'{p:,.2f}'.rstrip('0').rstrip('.')):
                notes.append(f'value {e.value} vs close {want}')
        elif e.value and e.bracket:
            d0, d1 = e.bracket
            pct = PRICE[d1] / PRICE[d0] - 1
            if e.value.replace(',', '') not in (_fmt_pct(pct).replace(',', ''), _fmt_pct(pct).replace(',', '').replace('.0%', '%'),
                                                f"{'+' if pct >= 0 else '−'}{abs(pct) * 100:,.0f}%".replace(',', '')):
                notes.append(f'value {e.value} vs bracket {_fmt_pct(pct)}')
        elif e.value:
            pct = PRICE[e.day] / PRICE[e.day - 1] - 1
            if e.value != _fmt_pct(pct):
                notes.append(f'value {e.value} vs 1-day {_fmt_pct(pct)}')
        flag = '!!' if notes else '  '
        if notes:
            ok = False
        print(f'{flag} {e.t:6.1f} {e.date} {e.kind:7s} {e.title:24s} close={p:,.2f} {"; ".join(notes)}')
    print('milestones', [(lv, str(date_of(fd)), round(fd, 1), t) for lv, fd, t in MILESTONE_T])
    print('eras', [(round(t, 2), l, ti) for t, l, ti in ERA_T])
    print('data', D0, DATES[-1], NDAYS, 'frames', NFRAMES, 'duration', DURATION)
    return ok


if __name__ == '__main__':
    print('ALL OK' if verify() else 'CHECK THE !! LINES')
