"""Shared data, timeline and camera precompute for the NVIDIA stock history video.

The x axis is the trading-day index (weekends and holidays removed), so every
"day" below is an index into DATES, not a calendar offset.
"""
import bisect
import csv
import datetime as dt
import math
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_CSV = os.environ.get('NVDA_CSV', os.path.join(ROOT, 'data', 'nvda_daily.csv'))
FONT_DIR = os.path.join(ROOT, 'fonts')

W, H = 1920, 1080
FPS = 30

# ----------------------------------------------------------------------------
# data: split-adjusted daily close
# ----------------------------------------------------------------------------

def load_prices():
    dates, prices = [], []
    for r in csv.DictReader(open(DATA_CSV)):
        if r['close']:
            dates.append(dt.date.fromisoformat(r['date']))
            prices.append(float(r['close']))
    return dates, np.array(prices, dtype=np.float64)


DATES, PRICE = load_prices()
D0 = DATES[0]
NDAYS = len(DATES)
LOGP = np.log10(PRICE)
DAYS = np.arange(NDAYS, dtype=np.float64)
YEAR_DAYS = 252  # trading days per year


def day_of(s):
    """index of the first trading day on or after date string s"""
    d = dt.date.fromisoformat(s) if isinstance(s, str) else s
    return min(bisect.bisect_left(DATES, d), NDAYS - 1)


def date_of(day):
    return DATES[int(min(max(day, 0), NDAYS - 1))]


def close(s):
    return PRICE[day_of(s)]


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
# palette (western convention: green = up, red = down)
# ----------------------------------------------------------------------------
GOLD = (236, 200, 132)
BLUE = (150, 190, 250)
PURPLE = (178, 170, 246)
RED = (246, 112, 100)
GREEN = (112, 222, 146)

CATS = {
    'IPO': GOLD, 'PEAK': GOLD, 'RECORD': GOLD,
    'DEAL': BLUE, 'INDEX': BLUE, 'POLICY': BLUE, 'RANKING': BLUE,
    'LAUNCH': PURPLE, 'AI': PURPLE,
    'CRISIS': RED, 'CRASH': RED, 'BOTTOM': RED,
    'SURGE': GREEN, 'EARNINGS': GREEN,
}
POSITIVE = ('IPO', 'PEAK', 'RECORD', 'SURGE', 'EARNINGS')
NEGATIVE = ('CRISIS', 'CRASH', 'BOTTOM')

# ----------------------------------------------------------------------------
# formatting helpers
# ----------------------------------------------------------------------------

def fmt_price(p, decimals=None):
    if decimals is None:
        decimals = 2 if p >= 1 else 4
    return f'{p:,.{decimals}f}'


def fmt_level(v):
    if v >= 1:
        return f'{v:,.0f}'
    return f'{v:g}'


def fmt_pct(x, nd=1):
    return f'{"+" if x >= 0 else "−"}{abs(x) * 100:,.{nd}f}%'


def fmt_mult(x):
    if x >= 100:
        return f'{x:,.0f}×'
    if x >= 10:
        return f'{x:.0f}×'
    return f'{x:.1f}×'


def _fill(s, date):
    """placeholders in callout text, resolved from the price data:
    {close} close of the event day, {close@D} close on D,
    {pct@D} change from D to the event day, {mult@D} multiple from D."""
    out = ''
    i = 0
    while i < len(s):
        if s[i] == '{':
            j = s.index('}', i)
            key = s[i + 1:j]
            name, _, ref = key.partition('@')
            p1 = close(date)
            if name == 'close':
                out += '$' + fmt_price(close(ref) if ref else p1)
            elif name == 'pct':
                out += fmt_pct(p1 / close(ref) - 1)
            elif name == 'mult':
                out += fmt_mult(p1 / close(ref))
            else:
                raise KeyError(key)
            i = j + 1
        else:
            out += s[i]
            i += 1
    return out


def value_text(spec, date):
    """value line of a callout: 'close', 'ret' (one-day move), ('from', D) or literal"""
    if not spec:
        return ''
    if spec == 'close':
        return '$' + fmt_price(close(date))
    if spec == 'ret':
        i = day_of(date)
        return fmt_pct(PRICE[i] / PRICE[i - 1] - 1)
    if isinstance(spec, tuple) and spec[0] == 'from':
        return fmt_pct(close(date) / close(spec[1]) - 1)
    return spec

# ----------------------------------------------------------------------------
# events: (t, date, category, title, value spec, [desc lines], tag, chart label)
# ----------------------------------------------------------------------------
EVENTS_RAW = [
    (8.5, '1999-01-22', 'IPO', 'Nasdaq IPO', 'close',
     ['Priced at $12 a share, closed day one at $19.69', 'Split-adjusted for six splits since'], 'NASDAQ', 'IPO'),
    (15.0, '1999-08-31', 'LAUNCH', 'GeForce 256', '',
     ['Billed as “the world’s first GPU”', 'Graphics gets a processor of its own'], 'GEFORCE', 'GeForce 256'),
    (18.5, '2000-03-06', 'DEAL', 'Wins the Xbox Deal', '',
     ['Microsoft picks NVIDIA graphics for', 'its first console, with $200M upfront'], 'MICROSOFT', 'Xbox deal'),
    (22.0, '2000-12-15', 'DEAL', 'Buys Rival 3dfx', '',
     ['Takes over the assets of its fallen rival', 'NVIDIA wins the graphics card war'], '3DFX', '3dfx'),
    (25.5, '2001-11-30', 'INDEX', 'Joins the S&P 500', '',
     ['Takes the seat of collapsing Enron', 'Best S&P 500 stock of 2001: +308%'], 'S&P 500', 'S&P 500'),
    (29.5, '2002-02-14', 'CRISIS', 'Accounting Probe', 'ret',
     ['Audit review at the SEC’s request', 'Three years of results restated'], 'SEC', 'SEC probe'),
    (34.0, '2002-10-09', 'BOTTOM', 'Dot-Com Bottom', ('from', '2002-01-03'),
     ['Xbox price dispute, delayed GeForce FX', '{close} · lowest close since 1999'], '', '2002 bottom'),
    (41.0, '2006-11-08', 'LAUNCH', 'CUDA Is Born', '',
     ['GeForce 8800 ships with the CUDA platform', 'GPUs become general-purpose computers'], 'CUDA', 'CUDA'),
    (45.0, '2007-10-31', 'PEAK', 'Pre-Crisis Peak', 'close',
     ['{mult@2002-10-09} from the 2002 bottom'], '', '2007 peak'),
    (49.0, '2008-07-03', 'CRASH', 'Defective Chips', 'ret',
     ['Laptop GPUs failing from overheating', '$150–200M charge, sales forecast cut'], 'BUMPGATE', 'Bumpgate'),
    (53.0, '2008-11-20', 'BOTTOM', '2008 Crisis Bottom', ('from', '2007-10-31'),
     ['Lehman collapse drags tech stocks down', '{close} · back to 2003 levels'], '', '2008 bottom'),
    (59.5, '2012-09-30', 'AI', 'AlexNet', '',
     ['A neural net trained on two GeForce GPUs', 'wins ImageNet — deep learning takes off'], 'IMAGENET', 'AlexNet'),
    (66.0, '2016-04-05', 'AI', 'DGX-1 Unveiled', '',
     ['“AI supercomputer in a box”', 'First unit hand-delivered to OpenAI'], 'DGX-1', 'DGX-1'),
    (70.0, '2016-11-11', 'SURGE', 'Blowout Earnings', 'ret',
     ['Data-center sales nearly triple', 'Best S&P 500 stock of 2016'], '', 'Nov 2016'),
    (75.5, '2018-10-01', 'PEAK', 'Crypto-Boom Peak', 'close',
     ['Miners and gamers snap up every GPU'], '', '2018 peak'),
    (78.5, '2018-11-16', 'CRASH', 'Crypto Hangover', 'ret',
     ['Unsold graphics cards pile up', 'after the crypto crash'], '', 'Crypto hangover'),
    (81.5, '2018-12-24', 'BOTTOM', 'Crypto Winter', ('from', '2018-10-01'),
     ['{close} · in less than three months'], '', '2018 bottom'),
    (85.5, '2019-03-11', 'DEAL', 'Buys Mellanox', '',
     ['$6.9 billion for data-center networking', 'Its biggest acquisition ever'], 'MELLANOX', 'Mellanox'),
    (90.0, '2020-03-16', 'CRASH', 'COVID-19 Crash', 'ret',
     ['Global markets in free fall', 'Circuit breakers halt Wall Street'], '', 'COVID'),
    (94.0, '2020-07-08', 'RANKING', 'Overtakes Intel', '',
     ['Becomes the most valuable', 'US chipmaker for the first time'], 'INTEL', 'Passes Intel'),
    (97.5, '2020-09-14', 'DEAL', '$40B Bid for Arm', '',
     ['The largest chip deal ever proposed', 'Abandoned in 2022 under regulatory fire'], 'ARM', 'Arm bid'),
    (103.0, '2021-11-29', 'PEAK', 'Metaverse Peak', 'close',
     ['{mult@2018-12-24} from the 2018 bottom'], '', '2021 peak'),
    (108.5, '2022-09-01', 'POLICY', 'China Chip Ban', 'ret',
     ['US curbs A100 and H100 sales to China'], 'EXPORT RULES', 'China ban'),
    (111.5, '2022-10-13', 'BOTTOM', '2022 Bear Bottom', ('from', '2021-11-29'),
     ['Crypto bust, gaming slump, rate hikes', '{close} · a year of losses'], '', '2022 bottom'),
    (116.0, '2022-11-30', 'AI', 'ChatGPT Launches', '',
     ['Built on NVIDIA GPUs', 'The AI arms race begins'], 'OPENAI', 'ChatGPT'),
    (121.0, '2023-05-25', 'SURGE', 'The Guidance Shock', 'ret',
     ['Guides $11B in quarterly sales', 'vs. about $7B expected'], 'EARNINGS', 'May 2023'),
    (128.0, '2024-02-22', 'SURGE', '+$277B in a Day', 'ret',
     ['Biggest one-day gain in market value', 'in US history at the time'], 'EARNINGS', 'Feb 2024'),
    (132.5, '2024-03-18', 'LAUNCH', 'Blackwell Unveiled', '',
     ['208 billion transistors per GPU', 'The next engine of the AI boom'], 'GTC', 'Blackwell'),
    (138.5, '2024-06-18', 'RECORD', 'World’s Most Valuable', 'close',
     ['Briefly passes Microsoft and Apple', 'one week after a 10-for-1 split'], '', '#1 company'),
    (142.5, '2024-09-03', 'CRASH', '$279B Wiped Out', 'ret',
     ['Largest one-day loss of value', 'in US market history, at the time'], '', 'Sept 2024'),
    (146.0, '2024-11-08', 'INDEX', 'Joins the Dow', '',
     ['Replaces Intel in the', 'Dow Jones Industrial Average'], 'DJIA', 'Dow'),
    (152.0, '2025-01-27', 'CRASH', 'DeepSeek Shock', 'ret',
     ['A low-cost Chinese AI model rattles markets',
      '−$589B: biggest one-day loss in US history'], 'DEEPSEEK', 'DeepSeek'),
    (156.5, '2025-04-04', 'CRASH', 'Tariff Shock', ('from', '2025-04-02'),
     ['Sweeping US “reciprocal” tariffs', 'Two-day rout across global markets'], 'TARIFFS', 'Tariffs'),
    (159.0, '2025-04-09', 'SURGE', 'Tariff-Pause Rally', 'ret',
     ['90-day pause on most new tariffs', 'Best day since 2008 for the Nasdaq'], '', 'Pause rally'),
    (167.0, '2025-09-22', 'DEAL', '$100B OpenAI Pact', '',
     ['Plans to invest up to $100 billion', 'as OpenAI builds out NVIDIA systems'], 'OPENAI', 'OpenAI'),
    (176.0, '2026-02-26', 'CRASH', 'Earnings Selloff', 'ret',
     ['A strong forecast fails to calm', 'fears of an AI bubble'], 'EARNINGS', 'Feb 2026'),
    (178.5, '2026-03-16', 'LAUNCH', 'Vera Rubin', '',
     ['Huang sees $1 trillion of Blackwell', 'and Rubin orders through 2027'], 'GTC', 'Vera Rubin'),
    (182.0, '2026-05-14', 'RECORD', 'All-Time High', 'close',
     ['$5.5 trillion company — first ever', 'Huang joins the US trip to China'], '', '2026 high'),
    (185.5, '2026-07-07', 'BOTTOM', 'The Summer Slide', ('from', '2026-05-14'),
     ['Over $1 trillion erased in two months', 'Investors rotate into memory chips'], '', 'Summer slide'),
    (188.5, '2026-08-27', 'EARNINGS', '$96 Billion Quarter', 'ret',
     ['Revenue +106% year over year', 'Guides $108B for next quarter'], 'EARNINGS', 'Aug 2026'),
    (191.0, '2026-09-28', 'RECORD', '$150B Buyback', '',
     ['Largest buyback boost in US history', 'Record highs follow in October'], 'BUYBACK', 'Buyback'),
]

T_START = 8.5          # chart starts
T_END = 194.5          # head reaches the final data day


class Event:
    def __init__(self, raw):
        (self.t, self.date, self.cat, self.title, vspec, desc,
         self.tag, self.label) = raw
        self.day = day_of(self.date)
        self.value = value_text(vspec, self.date)
        self.desc = [_fill(s, self.date) for s in desc]
        self.color = CATS[self.cat]
        self.positive = self.cat in POSITIVE
        self.negative = self.cat in NEGATIVE
        # camera push-in strength (0 = none)
        if self.cat == 'IPO':
            self.zoom = 0.0
        elif self.date in BLACK_SWANS or self.cat in ('PEAK', 'BOTTOM'):
            self.zoom = 0.42
        elif self.cat in ('CRISIS', 'CRASH', 'RECORD', 'SURGE', 'EARNINGS', 'POLICY'):
            self.zoom = 0.30
        else:
            self.zoom = 0.18
        # camera shake strength in px
        self.shake = SHAKE.get(self.date, {'PEAK': 6.0, 'BOTTOM': 5.0, 'RECORD': 4.0, 'SURGE': 6.0,
                                           'EARNINGS': 5.0, 'CRISIS': 8.0, 'CRASH': 10.0,
                                           'POLICY': 8.0}.get(self.cat, 0.0))
        b = BRACKETS.get(self.date)
        self.bracket = (day_of(b[0]), day_of(b[1])) if b else None


# black swans: strongest push-in and shake
BLACK_SWANS = {'2002-02-14', '2008-07-03', '2018-11-16', '2020-03-16', '2025-01-27'}
SHAKE = {
    '2002-02-14': 14, '2008-07-03': 22, '2018-11-16': 16, '2020-03-16': 20, '2022-09-01': 9,
    '2024-09-03': 14, '2025-01-27': 26, '2025-04-04': 16, '2026-02-26': 9,
}
# measurement arrows drawn on the chart: event date -> (from date, to date)
BRACKETS = {
    '2002-02-14': ('2002-02-13', '2002-02-14'),
    '2002-10-09': ('2002-01-03', '2002-10-09'),
    '2008-07-03': ('2008-07-02', '2008-07-03'),
    '2008-11-20': ('2007-10-31', '2008-11-20'),
    '2016-11-11': ('2016-11-10', '2016-11-11'),
    '2018-11-16': ('2018-11-15', '2018-11-16'),
    '2018-12-24': ('2018-10-01', '2018-12-24'),
    '2020-03-16': ('2020-03-13', '2020-03-16'),
    '2022-09-01': ('2022-08-31', '2022-09-01'),
    '2022-10-13': ('2021-11-29', '2022-10-13'),
    '2023-05-25': ('2023-05-24', '2023-05-25'),
    '2024-02-22': ('2024-02-21', '2024-02-22'),
    '2024-09-03': ('2024-08-30', '2024-09-03'),
    '2025-01-27': ('2025-01-24', '2025-01-27'),
    '2025-04-04': ('2025-04-02', '2025-04-04'),
    '2025-04-09': ('2025-04-08', '2025-04-09'),
    '2026-02-26': ('2026-02-25', '2026-02-26'),
    '2026-07-07': ('2026-05-14', '2026-07-07'),
    '2026-08-27': ('2026-08-26', '2026-08-27'),
}

EVENTS = [Event(r) for r in EVENTS_RAW]

ERAS = [  # (start date, label, title)
    ('1999-01-22', '1999 — 2002', 'Birth of the GPU'),
    ('2003-01-01', '2003 — 2007', 'The CUDA Bet'),
    ('2008-01-01', '2008 — 2011', 'Crisis Years'),
    ('2012-01-01', '2012 — 2015', 'The Deep-Learning Spark'),
    ('2016-01-01', '2016 — 2018', 'Gamers, Miners & AI'),
    ('2019-01-01', '2019 — 2021', 'Data-Center Rising'),
    ('2022-01-01', '2022', 'The Great Reset'),
    ('2022-11-15', '2023 — 2024', 'The AI Gold Rush'),
    ('2025-01-01', '2025 — 2026', 'The Trillion-Dollar Era'),
]

# market-cap milestones: (t, date, big label) -- widely reported first-touch dates
MILESTONES_RAW = [
    (123.0, '2023-05-30', '$1 Trillion'),
    (130.0, '2024-03-01', '$2 Trillion'),
    (135.5, '2024-06-05', '$3 Trillion'),
    (163.0, '2025-07-09', '$4 Trillion'),
    (171.5, '2025-10-29', '$5 Trillion'),
]
MILESTONE_T = [(lab, float(day_of(d)), t, d) for t, d, lab in MILESTONES_RAW]

# ----------------------------------------------------------------------------
# time mapping t -> head day (fractional)
# ----------------------------------------------------------------------------

def _smoother(u):
    return u * u * u * (u * (u * 6 - 15) + 10)


ANCHORS = sorted([(e.t, float(e.day)) for e in EVENTS] +
                 [(t, fd) for _, fd, t, _ in MILESTONE_T]) + [(T_END, float(NDAYS - 1))]
for (_ta, _da), (_tb, _db) in zip(ANCHORS, ANCHORS[1:]):
    assert _tb > _ta and _db > _da, ('anchors out of order', _ta, _tb, _da, _db)


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


# ending timeline, relative to T_END (same rhythm as the bitcoin video)
END_Q1 = T_END + 1.0       # first question
END_Q2 = T_END + 2.0
END_T0 = T_END + 4.0       # camera pulls back to the overview
END_T1 = T_END + 9.0
DURATION = T_END + 15.333
NFRAMES = int(round(DURATION * FPS))

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
                                       'warm', 'cold', 'valcol', 'hl', 'volshake')}
    vol_s = 0.0
    dt_ = 1.0 / FPS
    k_log = None
    s_log = None
    C = None
    warm = cold = 0.0
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
        # mood
        i = int(min(max(round(h), 0), NDAYS - 1))
        m30 = RET30[i]
        m10 = LOGP[i] - LOGP[max(i - 10, 0)]
        dd = DRAWDOWN[i]
        warm_t = min(max((m30 - 0.08) / 0.22, 0), 1) * min(max(1 - dd / 0.25, 0), 1)
        cold_t = min(max((-m10 - 0.04) / 0.12, 0), 1)
        if t < 9:
            warm_t = cold_t = 0.0
        warm = _ema(warm, warm_t, dt_, 1.2)
        cold = _ema(cold, cold_t, dt_, 0.9)
        # value colour: -1 red .. +1 green (two-week momentum)
        vt = min(max(m10 / 0.06, -1), 1) if t >= 9 else 0.0
        valc = _ema(valc, vt, dt_, 0.35)
        cam['k'][f] = math.exp(k_log)
        cam['s'][f] = s
        cam['C'][f] = C
        cam['hx'][f] = hx
        cam['hy'][f] = hy
        cam['theta'][f] = theta
        cam['roll'][f] = math.radians(1.1 * math.sin(2 * math.pi * t / 53.0 + 1.0)) * min(max((t - 9) / 5, 0), 1)
        cam['vis'][f] = vis
        cam['warm'][f] = warm
        cam['cold'][f] = cold
        cam['valcol'][f] = valc
        cam['hl'][f] = lh
        # hand-held wobble while the market swings hard (big daily moves near the head)
        vmax = float(np.max(np.abs(RET1[max(i - 2, 0):i + 1])))
        v_t = 5.0 * min(max((vmax - 0.03) / 0.05, 0), 1) if 9.0 <= t <= T_END else 0.0
        vol_s = _ema(vol_s, v_t, dt_, 0.22)
        cam['volshake'][f] = vol_s
    return cam


_CAM_CACHE = os.path.join(ROOT, 'work', 'cam_cache.npz')


def get_camera():
    src = max(os.path.getmtime(__file__), os.path.getmtime(DATA_CSV))
    if os.path.exists(_CAM_CACHE) and os.path.getmtime(_CAM_CACHE) > src:
        z = np.load(_CAM_CACHE)
        if len(z['k']) == NFRAMES:
            return {k: z[k] for k in z.files}
    cam = precompute_camera()
    os.makedirs(os.path.dirname(_CAM_CACHE), exist_ok=True)
    np.savez(_CAM_CACHE, **cam)
    return cam


if __name__ == '__main__':
    print('days', NDAYS, D0, DATES[-1], 'frames', NFRAMES, 'duration', DURATION)
    for e in EVENTS:
        i = e.day
        print(f'{e.t:6.1f} {e.date} ({DATES[i]}) {e.cat:8s} {e.title:28s} close={PRICE[i]:9.4f} '
              f'ret={PRICE[i] / PRICE[i - 1] - 1:+.3f} value={e.value}')
        for d in e.desc:
            print('        ', d)
    print('milestones', [(lab, d, DATES[int(fd)], round(PRICE[int(fd)], 2), t) for lab, fd, t, d in MILESTONE_T])
    print('eras', [(round(t, 2), l, ti) for t, l, ti in ERA_T])
