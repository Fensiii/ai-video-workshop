"""Shared data, timeline and camera precompute for the Bitcoin history video."""
import csv
import datetime as dt
import math
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_CSV = os.path.join(ROOT, 'data', 'btc_cm.csv')
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
        if r['PriceUSD']:
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

# ----------------------------------------------------------------------------
# events: (t, date, category, title, value, [desc lines], tag, short label)
# value colour follows category; numbers verified against the Coin Metrics series
# ----------------------------------------------------------------------------
EVENTS_RAW = [
    (8.5, '2010-07-18', '开端', 'Mt.Gox 开启交易', '$0.0858',
     ['比特币首次拥有公开市场价格', '两个月前，1 万枚比特币只换了两个披萨'], '', '2010 开盘'),
    (16.5, '2011-06-08', '顶点', '第一次泡沫', '$29.03',
     ['4 个月从 1 美元涨到 29 美元'], '', '2011 泡沫'),
    (19.5, '2011-06-19', '危机', 'Mt.Gox 首遭黑客攻击', '',
     ['交易所被盗，币价一度闪崩至 0.01 美元', '交易暂停近一周'], 'MT.GOX', 'Mt.Gox 被盗'),
    (23.5, '2011-11-18', '谷底', '第一次熊市见底', '−92.7%',
     ['2011.11.18 · $2.11', '历时 5 个月'], '', '2011 谷底'),
    (28.0, '2012-11-28', '减半', '第一次减半', '',
     ['区块奖励 50 → 25 BTC', '每四年一次，写进代码的通缩'], 'HALVING', '首次减半'),
    (32.5, '2013-03-16', '暴涨', '塞浦路斯危机', '+389%',
     ['储户存款遭强制征税，资金涌入比特币', '三周后升至 $230'], '', '塞浦路斯'),
    (36.0, '2013-04-10', '暴跌', 'Mt.Gox 宕机闪崩', '−64.1%',
     ['交易量激增导致系统瘫痪', '两日内从 $230 跌至 $83'], '', '4·10 闪崩'),
    (40.0, '2013-10-02', '危机', '丝绸之路被查封', '−18.4%',
     ['FBI 查封暗网市场，没收约 2.6 万枚比特币', '单日暴跌后迅速收复'], '', '丝绸之路'),
    (45.5, '2013-12-04', '顶点', '第二次泡沫顶点', '$1,134.93',
     ['一年上涨约 85 倍', '次日中国五部委发文，两周后腰斩'], '', '2013 顶点'),
    (50.5, '2014-02-24', '危机', 'Mt.Gox 倒闭', '',
     ['曾经全球最大的比特币交易所停止运营', '约 85 万枚比特币不知所踪'], 'MT.GOX', 'Mt.Gox 倒闭'),
    (55.5, '2015-01-14', '谷底', '熊市见底', '−84.5%',
     ['2015.01.14 · $175.64', '历时 13 个月'], '', '2015 谷底'),
    (59.5, '2015-07-30', '上线', '以太坊上线', '',
     ['智能合约平台诞生', '为日后的 ICO 狂潮埋下伏笔'], 'ETHEREUM', '以太坊'),
    (64.0, '2016-07-09', '减半', '第二次减半', '',
     ['区块奖励 25 → 12.5 BTC'], 'HALVING', '第二次减半'),
    (66.5, '2016-08-02', '危机', 'Bitfinex 被盗', '−13.1%',
     ['约 12 万枚比特币被黑客盗走', '单日暴跌'], 'BITFINEX', 'Bitfinex'),
    (70.5, '2017-02-23', '新高', '收复 2013 年高点', '$1,188.86',
     ['距上一次高点，整整三年零三个月'], '', '收复高点'),
    (75.0, '2017-09-04', '危机', '中国叫停 ICO', '−34.0%',
     ['七部委发文禁止代币发行融资', '国内交易所随后陆续关停'], '', 'ICO 禁令'),
    (80.5, '2017-12-16', '顶点', 'ICO 泡沫顶点', '$19,640.51',
     ['一年上涨约 25 倍', '次日 CME 比特币期货上线'], '', '2017 顶点'),
    (86.5, '2018-12-15', '谷底', '加密寒冬见底', '−83.8%',
     ['2018.12.15 · $3,185.07', '历时 12 个月'], '', '2018 谷底'),
    (91.5, '2019-06-18', '科技', 'Facebook 发布 Libra', '',
     ['科技巨头入局加密货币', '一周后比特币升至 $12,863'], 'LIBRA', 'Libra'),
    (96.0, '2020-03-12', '暴跌', '新冠疫情冲击', '−37.5%',
     ['全球资产遭抛售，单日暴跌近四成', '史称“312 黑色星期四”'], '', '312'),
    (99.5, '2020-05-11', '减半', '第三次减半', '',
     ['区块奖励 12.5 → 6.25 BTC'], 'HALVING', '第三次减半'),
    (103.5, '2020-08-11', '入场', 'MicroStrategy 买入', '',
     ['首家将比特币作为储备资产的上市公司', '首笔买入 21,454 枚'], 'MSTR', 'MicroStrategy'),
    (110.5, '2021-02-08', '入场', '特斯拉买入', '+18.2%',
     ['斥资 15 亿美元购入比特币', '消息公布当日大涨'], 'TESLA', '特斯拉'),
    (114.5, '2021-04-14', '上市', 'Coinbase 上市', '',
     ['首家在美上市的加密货币交易所', '比特币同期站上 6 万美元'], 'COINBASE', 'Coinbase'),
    (118.0, '2021-05-19', '暴跌', '5·19 大暴跌', '−12.0%',
     ['中国重申禁止加密货币业务', '盘中一度跌至 3 万美元附近'], '', '5·19'),
    (121.5, '2021-09-07', '法币', '萨尔瓦多：法定货币', '−11.0%',
     ['全球首个将比特币定为法定货币的国家', '法案生效当日大跌'], 'EL SALVADOR', '萨尔瓦多'),
    (125.0, '2021-11-08', '顶点', '牛市顶点', '$67,541.76',
     ['盘中最高约 6.9 万美元', '随后开启漫长寒冬'], '', '2021 顶点'),
    (130.0, '2022-05-09', '暴跌', 'LUNA 崩盘', '−10.6%',
     ['算法稳定币 UST 脱锚', 'LUNA 一周内几乎归零'], '', 'LUNA'),
    (133.5, '2022-06-13', '危机', 'Celsius 冻结提款', '−16.8%',
     ['加密借贷平台接连爆雷', '三箭资本随后破产'], '', 'Celsius'),
    (137.5, '2022-11-08', '危机', 'FTX 破产', '−23.4%',
     ['头部交易所 FTX 挤兑崩塌', '次日跌至 $15,758，较高点 −76.7%'], 'FTX', 'FTX'),
    (142.0, '2023-06-15', '入场', '贝莱德申请 ETF', '',
     ['全球最大资管公司提交现货 ETF 申请', '华尔街巨头正式入场'], 'BLACKROCK', '贝莱德'),
    (146.0, '2024-01-10', '获批', '现货 ETF 获批', '',
     ['美国 SEC 批准 11 只比特币现货 ETF', '次日正式上市交易'], 'SPOT ETF', 'ETF 获批'),
    (149.0, '2024-03-04', '新高', '重回历史新高', '$68,091.84',
     ['距上一次高点两年零四个月'], '', '2024 新高'),
    (152.0, '2024-04-20', '减半', '第四次减半', '',
     ['区块奖励 6.25 → 3.125 BTC'], 'HALVING', '第四次减半'),
    (155.5, '2024-11-05', '大选', '美国大选', '+8.9%',
     ['市场押注加密友好政策', '次日创历史新高'], '', '大选'),
    (161.5, '2025-03-06', '政策', '美国战略比特币储备', '',
     ['总统签署行政令建立国家比特币储备', '以没收所得的比特币作为储备来源'], 'USA', '战略储备'),
    (164.0, '2025-04-07', '危机', '关税冲击', '−7.5%',
     ['美国宣布“对等关税”', '比特币一度跌至 7.6 万美元'], '', '关税'),
    (166.5, '2025-05-22', '新高', '重回历史新高', '$111,477.01',
     ['关税冲击后不到两个月'], '', '2025 新高'),
    (170.5, '2025-10-06', '顶点', '历史新高', '$124,824.45',
     ['2025.10.06 收盘', '16 年上涨约 145 万倍'], '', '2025 顶点'),
    (173.5, '2025-10-10', '暴跌', '史上最大清算', '−6.5%',
     ['关税升级引发连环爆仓', '单日清算超 190 亿美元'], '', '10·10 清算'),
    (176.5, '2026-02-05', '暴跌', '恐慌抛售', '−13.1%',
     ['单日暴跌，跌至 $63,495', '较历史高点回撤近五成'], '', '2026 暴跌'),
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
    ('2010-07-18', '2010 — 2012', '极客实验'),
    ('2013-01-01', '2013 — 2015', '野蛮生长'),
    ('2016-01-01', '2016 — 2018', 'ICO 狂潮'),
    ('2019-01-01', '2019 — 2020', '疫情与减半'),
    ('2020-07-01', '2020 — 2021', '机构入场'),
    ('2022-01-01', '2022 — 2023', '加密寒冬'),
    ('2023-06-01', '2023 — 2024', 'ETF 时代'),
    ('2025-01-01', '2025 — 2026', '国家储备'),
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
