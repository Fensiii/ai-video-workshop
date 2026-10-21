"""七美德流星：数据与时间轴（改文案只动这里）。

版式照搬 references/data-history/ai-leaderboard-meteors：每个美德一颗流星，
"此刻最亮"的那颗 = 当前历史节点所体现的美德，带 NO.1 标签和星芒。
"""
import math
import os
import zlib

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.environ.get('FONT_DIR', os.path.expanduser('~/fonts'))
W, H, FPS = 1920, 1080, 30

# key: (中文名, 拉丁文, 颜色)
VIRTUES = {
    'pru': ('智慧', 'PRUDENTIA', (110, 180, 255)),
    'jus': ('正义', 'IUSTITIA', (185, 155, 255)),
    'for': ('勇气', 'FORTITUDO', (255, 128, 72)),
    'tem': ('节制', 'TEMPERANTIA', (84, 222, 192)),
    'fid': ('信念', 'FIDES', (255, 214, 112)),
    'spe': ('希望', 'SPES', (156, 232, 112)),
    'car': ('仁爱', 'CARITAS', (255, 100, 138)),
}
KEYS = list(VIRTUES)

# (年份(负数=公元前), 年份文字, 最亮的美德, 事件说明, 新出现的美德, 特效)
EVENTS_RAW = [
    (-480, '公元前 480 年', 'for', '温泉关，三百斯巴达人迎战波斯大军', ['for'], 'shake'),
    (-399, '公元前 399 年', 'pru', '苏格拉底饮下毒芹：“未经审视的人生不值得过”', ['pru'], ''),
    (-375, '约公元前 375 年', 'jus', '柏拉图《理想国》：智慧、勇气、节制、正义并称', ['jus', 'tem'], 'burst'),
    (-340, '约公元前 340 年', 'tem', '亚里士多德：美德是“过”与“不及”之间的中道', [], ''),
    (-44, '公元前 44 年', 'jus', '西塞罗《论义务》：正义是美德中最耀眼的光', [], ''),
    (55, '约公元 55 年', 'car', '保罗：“如今常存的有信、有望、有爱，其中最大的是爱”', ['fid', 'spe', 'car'], 'burst'),
    (390, '约公元 390 年', 'pru', '安布罗斯用“枢”（门轴）称呼四德，“枢德”由此得名', [], ''),
    (405, '约公元 405 年', 'fid', '普鲁登修斯《灵魂之战》：美德化身战士，与恶习逐一交锋', [], ''),
    (1270, '约 1270 年', 'pru', '阿奎那《神学大全》：四枢德 + 三超德，七美德成形', [], 'constellation'),
    (1305, '约 1305 年', 'spe', '乔托在帕多瓦礼拜堂画下七美德与七恶习，两两相对', [], ''),
    (1315, '约 1315 年', 'car', '但丁《神曲·炼狱》：三位仙女着红、绿、白，四位着紫', [], ''),
    (1348, '1348 年', 'spe', '黑死病横扫欧洲，人口锐减三成以上', [], 'plague'),
    (1470, '1470 年', 'for', '波提切利画《坚毅》：勇气是一位手握权杖、端坐不动的女子', [], ''),
    (1560, '约 1560 年', 'tem', '老勃鲁盖尔的版画《节制》：钟表、乐谱、算盘挤满画面', [], ''),
    (1784, '1784 年', 'pru', '康德：“要有勇气运用你自己的理智”', [], ''),
    (1948, '1948 年', 'jus', '《世界人权宣言》：人人生而自由，在尊严和权利上一律平等', [], ''),
    (1955, '1955 年', 'for', '罗莎·帕克斯拒绝让座，一个人坐成了一场运动', [], 'shake'),
    (1963, '1963 年', 'spe', '马丁·路德·金：“我有一个梦想”', [], ''),
    (1979, '1979 年', 'car', '特蕾莎修女获诺贝尔和平奖', [], ''),
    (1990, '1990 年', 'fid', '曼德拉在狱中度过 27 年后出狱，选择和解', [], ''),
    (2004, '2004 年', 'pru', '《品格优势与美德》：跨文化找到六种核心美德', [], ''),
    (2026, '2026 年', 'tem', '一块屏幕就能吞掉一整天，最难的美德变成了节制', [], ''),
]

T_FIRST = 1.0
STEP = 6.3
EV_T = [T_FIRST + i * STEP for i in range(len(EVENTS_RAW))]
T_FINALE = EV_T[-1] + 6.0          # 群星汇聚开始
T_END_TEXT = T_FINALE + 3.6        # 结尾金句出现
DURATION = T_FINALE + 15.0
NFRAMES = int(round(DURATION * FPS))

FINAL_Q = '这七颗星，哪一颗在你心里最亮？'
FINAL_SUB = '七 美 德   ·   公元前 480 — 2026'
FOOTNOTE = '七美德 = 四枢德（智慧·正义·勇气·节制）+ 三超德（信·望·爱）；“最亮” = 该历史节点所体现的美德，按公开史料整理'


def rng_for(*parts):
    return np.random.default_rng(zlib.crc32('|'.join(map(str, parts)).encode()))


def smooth(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def ease_out(u):
    u = min(max(u, 0.0), 1.0)
    return 1 - (1 - u) ** 3


# ---------- 每个节点后的目标亮度 / 车道 ----------
BIRTH_EV = {}
for i, e in enumerate(EVENTS_RAW):
    for k in e[4]:
        BIRTH_EV[k] = i
BIRTH_T = {k: EV_T[i] - 1.6 for k, i in BIRTH_EV.items()}

LANES = np.linspace(250, 820, 7)
BRIGHT = []   # list of dict
LANE_Y = []
_b = {}
for i, e in enumerate(EVENTS_RAW):
    lead = e[2]
    r = rng_for('ev', i)
    nb = {}
    for k in KEYS:
        if k not in BIRTH_EV or BIRTH_EV[k] > i:
            continue
        if k == lead:
            nb[k] = 1.0
        elif k in _b:
            nb[k] = max(0.18, min(0.86, _b[k] * 0.78 + r.uniform(-0.06, 0.1)))
        else:
            nb[k] = r.uniform(0.35, 0.6)
    _b = nb
    BRIGHT.append(dict(nb))
    alive = [k for k in KEYS if k in nb]
    others = [k for k in alive if k != lead]
    r.shuffle(others)
    # 榜首放中间几条车道，其余随机
    n = len(alive)
    slots = list(range(7))
    lead_slot = int(r.integers(2, 5))
    slots.remove(lead_slot)
    r.shuffle(slots)
    ly = {lead: LANES[lead_slot] + r.uniform(-20, 20)}
    for k, s in zip(others, slots):
        ly[k] = LANES[s] + r.uniform(-25, 25)
    LANE_Y.append(ly)

LEADERS = [e[2] for e in EVENTS_RAW]
CHANGES = [0]
for i in range(1, len(LEADERS)):
    CHANGES.append(CHANGES[-1] + (LEADERS[i] != LEADERS[i - 1]))


def event_index(t, lead=0.0):
    i = 0
    for j, et in enumerate(EV_T):
        if t >= et - lead:
            i = j
    return i


def _interp(t, table, k, lead, dur, default):
    """在节点之间平滑过渡 table[i][k]。"""
    val = None
    for i, et in enumerate(EV_T):
        if k not in table[i]:
            continue
        if val is None:
            val = table[i][k]
            continue
        u = smooth((t - (et - lead)) / dur)
        if u <= 0:
            break
        val = val + (table[i][k] - val) * u
    return default if val is None else val


def brightness(k, t):
    return _interp(t, BRIGHT, k, 0.7, 1.5, 0.0)


def head_pos(k, t):
    """流星头在屏幕上的位置（无状态，同一 t 永远同一结果）。"""
    b = brightness(k, t)
    ph = (zlib.crc32(k.encode()) % 1000) / 1000 * math.tau
    x = 470 + 720 * b + 18 * math.sin(0.43 * t + ph)
    y = _interp(t, LANE_Y, k, 1.4, 2.8, 540) + 12 * math.sin(0.61 * t + ph * 1.7)
    bt = BIRTH_T.get(k, 1e9)
    u = ease_out((t - bt) / 1.9)
    x = -260 + (x + 260) * u
    y = y + (1 - u) * 160
    if t > T_FINALE:
        v = smooth((t - T_FINALE) / 4.2)
        x += (FINAL_C[0] - x) * v
        y += (FINAL_C[1] - y) * v
    return x, y


FINAL_C = (1080.0, 420.0)
SPEED = 560.0                 # 屏幕卷动速度 px/s（拖尾由此产生）
DIR = np.array([1.0, -0.30]) / math.hypot(1.0, -0.30)


def year_at(t):
    i = event_index(t)
    if t < EV_T[0] or i == len(EV_T) - 1:
        return EVENTS_RAW[i][0]
    y0, y1 = EVENTS_RAW[i][0], EVENTS_RAW[i + 1][0]
    u = smooth((t - (EV_T[i] + 2.4)) / (STEP - 2.4))
    y = y0 + (y1 - y0) * u
    y = int(round(y))
    if y == 0:
        y = 1 if y1 > 0 else -1
    return y


def leader_at(t):
    return LEADERS[event_index(t, 0.15)]
