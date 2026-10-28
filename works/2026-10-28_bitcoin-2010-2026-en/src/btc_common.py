"""Shared data, timeline and camera precompute for the Bitcoin history video (English edition).

Same timeline, camera and data as the Chinese original (works/2026-10-17_bitcoin-2010-2026);
only the on-screen text is translated. Category keys stay Chinese because the camera/FX logic
keys off them; CAT_EN holds what is shown on screen.
"""
import csv
import datetime as dt
import math
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Coin Metrics PriceUSD trimmed to two columns and frozen at 2026-05-23 (same cut-off as the original)
DATA_CSV = os.path.join(ROOT, 'data', 'btc_price.csv')
DATA_END = '2026-05-23'
FONT_DIR = os.path.join(ROOT, 'fonts')

W, H = 1920, 1080
FPS = 30
DURATION = 194.333
NFRAMES = int(round(DURATION * FPS))  # 5830

# ----------------------------------------------------------------------------
# data
# ----------------------------------------------------------------------------

def load_prices():
    rows = list(csv.DictReader(open(DATA_CSV)))
    dates, prices = [], []
    for r in rows:
        if r['PriceUSD'] and r['time'] <= DATA_END:
            dates.append(dt.date.fromisoformat(r['time']))
            prices.append(float(r['PriceUSD']))
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


MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')


def fmt_date(iso, upper=False):
    """'2011-11-18' -> 'Nov 18, 2011'"""
    d = dt.date.fromisoformat(iso)
    s = f'{MONTHS[d.month - 1]} {d.day}, {d.year}'
    return s.upper() if upper else s


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
# palette
# ----------------------------------------------------------------------------
GOLD = (236, 200, 132)
BLUE = (150, 190, 250)
TEAL = (84, 206, 188)
RED = (244, 128, 100)
PURPLE = (178, 170, 246)

CATS = {
    '开端': GOLD, '顶点': GOLD, '新高': GOLD,
    '上线': BLUE, '入场': BLUE, '上市': BLUE, '法币': BLUE, '获批': BLUE, '政策': BLUE,
    '减半': PURPLE, '科技': PURPLE,
    '危机': TEAL, '暴跌': TEAL, '谷底': TEAL,
    '暴涨': RED, '大选': RED,
}
# what the callout header shows for each category
CAT_EN = {
    '开端': 'START', '顶点': 'PEAK', '新高': 'NEW HIGH',
    '上线': 'LAUNCH', '入场': 'ADOPTION', '上市': 'LISTING', '法币': 'LEGAL TENDER', '获批': 'APPROVAL',
    '政策': 'POLICY', '减半': 'HALVING', '科技': 'BIG TECH',
    '危机': 'CRISIS', '暴跌': 'CRASH', '谷底': 'BOTTOM',
    '暴涨': 'SURGE', '大选': 'ELECTION',
}

# ----------------------------------------------------------------------------
# events: (t, date, category, title, value, [desc sentences], tag, short label)
# value colour follows category; numbers verified against the Coin Metrics series.
# Desc sentences are word-wrapped to the callout width by the renderer.
# Tags are tickers / extra context only (a tag that repeats the title was dropped).
# ----------------------------------------------------------------------------
EVENTS_RAW = [
    (8.5, '2010-07-18', '开端', 'Mt.Gox Opens', '$0.0858',
     ['Bitcoin gets its first public market price', 'Two months earlier: 10,000 BTC for two pizzas'], '', '2010 start'),
    (16.5, '2011-06-08', '顶点', 'The First Bubble', '$29.03',
     ['From $1 to $29 in four months'], '', '2011 bubble'),
    (19.5, '2011-06-19', '危机', 'Mt.Gox Hacked', '',
     ['BTC flash-crashes to $0.01 on the exchange', 'Trading halted for nearly a week'], '', 'Mt.Gox hack'),
    (23.5, '2011-11-18', '谷底', 'First Bear Market Ends', '−92.7%',
     ['Nov 18, 2011 · $2.11', '5 months from the peak'], '', '2011 bottom'),
    (28.0, '2012-11-28', '减半', 'The First Halving', '',
     ['Block reward: 50 → 25 BTC', 'Every four years — scarcity written in code'], '', '1st halving'),
    (32.5, '2013-03-16', '暴涨', 'Cyprus Bank Crisis', '+389%',
     ['A levy on bank deposits sends money into BTC', 'Three weeks later it hits $230'], '', 'Cyprus'),
    (36.0, '2013-04-10', '暴跌', 'Mt.Gox Outage Crash', '−64.1%',
     ['Surging volume overwhelms the exchange', 'From $230 to $83 in two days'], '', 'Apr 10 crash'),
    (40.0, '2013-10-02', '危机', 'Silk Road Shut Down', '−18.4%',
     ['FBI seizes the site and ~26,000 BTC', 'A one-day plunge, quickly recovered'], '', 'Silk Road'),
    (45.5, '2013-12-04', '顶点', 'Second Bubble Peaks', '$1,134.93',
     ['Up about 85× in one year', 'Next day China bars its banks from Bitcoin', 'Price halves within two weeks'], '', '2013 peak'),
    (50.5, '2014-02-24', '危机', 'Mt.Gox Collapses', '',
     ['The once-dominant exchange shuts down', 'About 850,000 BTC go missing'], '', 'Mt.Gox collapse'),
    (55.5, '2015-01-14', '谷底', 'Bear Market Bottom', '−84.5%',
     ['Jan 14, 2015 · $175.64', '13 months from the peak'], '', '2015 bottom'),
    (59.5, '2015-07-30', '上线', 'Ethereum Launches', '',
     ['A smart-contract platform is born', 'Setting the stage for the ICO boom'], 'ETH', 'Ethereum'),
    (64.0, '2016-07-09', '减半', 'The Second Halving', '',
     ['Block reward: 25 → 12.5 BTC'], '', '2nd halving'),
    (66.5, '2016-08-02', '危机', 'Bitfinex Hacked', '−13.1%',
     ['Hackers steal about 120,000 BTC', 'A sharp one-day drop'], '', 'Bitfinex'),
    (70.5, '2017-02-23', '新高', '2013 High Reclaimed', '$1,188.86',
     ['3 years and 3 months after the 2013 peak'], '', 'High reclaimed'),
    (75.0, '2017-09-04', '危机', 'China Bans ICOs', '−34.0%',
     ['Seven regulators outlaw token fundraising', 'Domestic exchanges shut down soon after'], '', 'ICO ban'),
    (80.5, '2017-12-16', '顶点', 'ICO Bubble Peaks', '$19,640.51',
     ['Up about 25× in one year', 'CME Bitcoin futures launch the next day'], '', '2017 peak'),
    (86.5, '2018-12-15', '谷底', 'Crypto Winter Bottoms', '−83.8%',
     ['Dec 15, 2018 · $3,185.07', '12 months from the peak'], '', '2018 bottom'),
    (91.5, '2019-06-18', '科技', 'Facebook Unveils Libra', '',
     ['Big Tech steps into crypto', 'A week later BTC climbs to $12,863'], '', 'Libra'),
    (96.0, '2020-03-12', '暴跌', 'COVID-19 Crash', '−37.5%',
     ['Global sell-off: nearly −40% in a single day', 'Remembered as “Black Thursday”'], '', 'Black Thursday'),
    (99.5, '2020-05-11', '减半', 'The Third Halving', '',
     ['Block reward: 12.5 → 6.25 BTC'], '', '3rd halving'),
    (103.5, '2020-08-11', '入场', 'MicroStrategy Buys In', '',
     ['First public company with a Bitcoin treasury', 'First purchase: 21,454 BTC'], 'MSTR', 'MicroStrategy'),
    (110.5, '2021-02-08', '入场', 'Tesla Buys Bitcoin', '+18.2%',
     ['$1.5 billion put into BTC', 'Price jumps the day the news breaks'], 'TSLA', 'Tesla'),
    (114.5, '2021-04-14', '上市', 'Coinbase Goes Public', '',
     ['First major U.S. crypto exchange to go public', 'BTC tops $60,000 around the same time'], 'COIN', 'Coinbase'),
    (118.0, '2021-05-19', '暴跌', 'The May 19 Crash', '−12.0%',
     ['China reiterates its ban on crypto services', 'Intraday low near $30,000'], '', 'May 19 crash'),
    (121.5, '2021-09-07', '法币', 'El Salvador Adopts BTC', '−11.0%',
     ['First country to make Bitcoin legal tender', 'Price drops sharply as the law takes effect'], '', 'El Salvador'),
    (125.0, '2021-11-08', '顶点', 'Bull Market Peak', '$67,541.76',
     ['Intraday high near $69,000', 'Then a long crypto winter begins'], '', '2021 peak'),
    (130.0, '2022-05-09', '暴跌', 'Terra-LUNA Collapse', '−10.6%',
     ['Algorithmic stablecoin UST loses its peg', 'LUNA goes to nearly zero within a week'], '', 'LUNA'),
    (133.5, '2022-06-13', '危机', 'Celsius Freezes Funds', '−16.8%',
     ['Crypto lenders blow up one after another', 'Three Arrows Capital soon goes bust'], '', 'Celsius'),
    (137.5, '2022-11-08', '危机', 'FTX Collapses', '−23.4%',
     ['A bank run topples a top-tier exchange', 'Next day: $15,758, −76.7% from the peak'], '', 'FTX'),
    (142.0, '2023-06-15', '入场', 'BlackRock Files for ETF', '',
     ["The world's largest asset manager steps in", 'Wall Street officially arrives'], 'IBIT', 'BlackRock'),
    (146.0, '2024-01-10', '获批', 'Spot ETFs Approved', '',
     ['U.S. SEC approves 11 spot Bitcoin ETFs', 'Trading begins the next day'], 'SEC', 'ETF approval'),
    (149.0, '2024-03-04', '新高', 'New All-Time High', '$68,091.84',
     ['Two years and four months after the last peak'], '', '2024 ATH'),
    (152.0, '2024-04-20', '减半', 'The Fourth Halving', '',
     ['Block reward: 6.25 → 3.125 BTC'], '', '4th halving'),
    (155.5, '2024-11-05', '大选', 'U.S. Election', '+8.9%',
     ['Markets bet on crypto-friendly policy', 'New all-time high the next day'], '', 'Election'),
    (161.5, '2025-03-06', '政策', 'U.S. Bitcoin Reserve', '',
     ['An executive order creates the reserve', 'Funded with forfeited bitcoin'], 'USA', 'BTC reserve'),
    (164.0, '2025-04-07', '危机', 'Tariff Shock', '−7.5%',
     ['U.S. announces “reciprocal tariffs”', 'BTC briefly drops to $76,000'], '', 'Tariffs'),
    (166.5, '2025-05-22', '新高', 'New All-Time High', '$111,477.01',
     ['Less than two months after the tariff shock'], '', '2025 ATH'),
    (170.5, '2025-10-06', '顶点', 'All-Time High', '$124,824.45',
     ['Oct 6, 2025 close', 'Up about 1.45 million-fold in 16 years'], '', '2025 peak'),
    (173.5, '2025-10-10', '暴跌', 'Record Liquidations', '−6.5%',
     ['Tariff threats set off a liquidation cascade', 'Over $19 billion wiped out in one day'], '', 'Oct 10 wipeout'),
    (176.5, '2026-02-05', '暴跌', 'Panic Selling', '−13.1%',
     ['One-day plunge to $63,495', 'Nearly 50% below the all-time high'], '', '2026 crash'),
]

T_END = 179.0          # head reaches the final data day
T_START = 8.5          # chart starts


class Event:
    def __init__(self, raw):
        (self.t, self.date, self.cat, self.title, self.value, self.desc,
         self.tag, self.label) = raw
        self.day = day_of(self.date)
        self.color = CATS[self.cat]
        self.positive = self.cat in ('开端', '顶点', '新高', '暴涨', '大选')
        self.negative = self.cat in ('危机', '暴跌', '谷底')
        # camera push-in strength (0 = none)
        if self.cat == '开端':
            self.zoom = 0.0
        elif self.date in BLACK_SWANS or self.cat in ('顶点', '谷底'):
            self.zoom = 0.42
        elif self.cat in ('危机', '暴跌', '新高', '暴涨', '大选'):
            self.zoom = 0.30
        else:
            self.zoom = 0.18
        # camera shake strength in px
        self.shake = SHAKE.get(self.date, {'顶点': 6.0, '谷底': 5.0, '新高': 4.0, '暴涨': 6.0,
                                           '大选': 6.0, '危机': 8.0, '暴跌': 10.0}.get(self.cat, 0.0))
        b = BRACKETS.get(self.date)
        self.bracket = (day_of(b[0]), day_of(b[1])) if b else None


# black swans: strongest push-in and shake
BLACK_SWANS = {'2011-06-19', '2013-04-10', '2014-02-24', '2020-03-12', '2022-11-08', '2025-10-10', '2026-02-05'}
SHAKE = {
    '2011-06-19': 16, '2013-04-10': 20, '2013-10-02': 10, '2014-02-24': 16, '2016-08-02': 10,
    '2017-09-04': 12, '2020-03-12': 26, '2021-05-19': 14, '2021-09-07': 8, '2022-05-09': 14,
    '2022-06-13': 12, '2022-11-08': 20, '2025-04-07': 10, '2025-10-10': 18, '2026-02-05': 18,
}
# measurement arrows drawn on the chart: event date -> (from date, to date)
BRACKETS = {
    '2011-11-18': ('2011-06-08', '2011-11-18'),
    '2013-04-10': ('2013-04-09', '2013-04-11'),
    '2013-10-02': ('2013-10-01', '2013-10-02'),
    '2015-01-14': ('2013-12-04', '2015-01-14'),
    '2016-08-02': ('2016-08-01', '2016-08-02'),
    '2017-09-04': ('2017-09-01', '2017-09-14'),
    '2018-12-15': ('2017-12-16', '2018-12-15'),
    '2020-03-12': ('2020-03-11', '2020-03-12'),
    '2021-02-08': ('2021-02-07', '2021-02-08'),
    '2021-05-19': ('2021-05-18', '2021-05-19'),
    '2021-09-07': ('2021-09-06', '2021-09-07'),
    '2022-05-09': ('2022-05-08', '2022-05-09'),
    '2022-06-13': ('2022-06-12', '2022-06-13'),
    '2022-11-08': ('2022-11-07', '2022-11-09'),
    '2024-11-05': ('2024-11-05', '2024-11-06'),
    '2025-04-07': ('2025-04-02', '2025-04-08'),
    '2025-10-10': ('2025-10-09', '2025-10-10'),
    '2026-02-05': ('2026-02-04', '2026-02-05'),
}

EVENTS = [Event(r) for r in EVENTS_RAW]

ERAS = [  # (start date, label, title)
    ('2010-07-18', '2010 — 2012', 'The Geek Experiment'),
    ('2013-01-01', '2013 — 2015', 'The Wild West'),
    ('2016-01-01', '2016 — 2018', 'ICO Mania'),
    ('2019-01-01', '2019 — 2020', 'Pandemic & Halving'),
    ('2020-07-01', '2020 — 2021', 'Institutions Arrive'),
    ('2022-01-01', '2022 — 2023', 'Crypto Winter'),
    ('2023-06-01', '2023 — 2024', 'The ETF Era'),
    ('2025-01-01', '2025 — 2026', 'Strategic Reserve'),
]

MILESTONES = [1, 100, 1000, 10000, 20000, 50000, 100000]


def fmt_price(p, decimals=None):
    if decimals is None:
        decimals = 2 if p >= 1 else 4
    return f'{p:,.{decimals}f}'


def fmt_level(v):
    if v >= 1:
        return f'{v:,.0f}'
    return f'{v:g}'

# ----------------------------------------------------------------------------
# time mapping t -> head day (fractional)
# ----------------------------------------------------------------------------

def _smoother(u):
    return u * u * u * (u * (u * 6 - 15) + 10)


ANCHORS = [(e.t, float(e.day)) for e in EVENTS] + [(T_END, float(NDAYS - 1))]


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


def milestone_times():
    out = []
    for lv in MILESTONES:
        d = int(np.argmax(PRICE >= lv))
        # fractional crossing day between d-1 and d
        if d > 0:
            l0, l1 = LOGP[d - 1], LOGP[d]
            frac = (math.log10(lv) - l0) / (l1 - l0) if l1 != l0 else 1.0
            fd = d - 1 + frac
        else:
            fd = 0.0
        out.append((lv, fd, time_of_day(fd)))
    return out


MILESTONE_T = milestone_times()


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
                                       'warm', 'teal', 'valcol', 'hl', 'volshake')}
    vol_s = 0.0
    dt_ = 1.0 / FPS
    k_log = None
    s_log = None
    C = None
    warm = teal = 0.0
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
        m14 = LOGP[i] - LOGP[max(i - 14, 0)]
        dd = DRAWDOWN[i]
        warm_t = min(max((m30 - 0.08) / 0.22, 0), 1) * min(max(1 - dd / 0.25, 0), 1)
        teal_t = min(max((-m14 - 0.04) / 0.12, 0), 1)
        if t < 9:
            warm_t = teal_t = 0.0
        warm = _ema(warm, warm_t, dt_, 1.2)
        teal = _ema(teal, teal_t, dt_, 0.9)
        # value colour: -1 teal .. +1 salmon (14-day momentum)
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
        cam['warm'][f] = warm
        cam['teal'][f] = teal
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
    src = os.path.getmtime(__file__)
    if os.path.exists(_CAM_CACHE) and os.path.getmtime(_CAM_CACHE) > src:
        z = np.load(_CAM_CACHE)
        return {k: z[k] for k in z.files}
    cam = precompute_camera()
    np.savez(_CAM_CACHE, **cam)
    return cam


if __name__ == '__main__':
    print('days', NDAYS, D0, DATES[-1])
    for e in EVENTS:
        print(f'{e.t:6.1f} {e.date} {e.cat} {e.title} price={PRICE[e.day]:.2f}')
    print('milestones', [(lv, round(fd, 1), round(t, 2)) for lv, fd, t in MILESTONE_T])
    print('eras', [(round(t, 2), l, ti) for t, l, ti in ERA_T])
    for t in [8.5, 10, 12, 14, 20, 30, 60, 100, 150, 178, 179]:
        h = head_day(t)
        print(t, round(h, 1), date_of(h))
