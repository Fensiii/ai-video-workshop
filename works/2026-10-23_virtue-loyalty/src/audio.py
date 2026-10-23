"""美德短片 —— 全合成配乐与音效（numpy），输出 48k 立体声 wav。
转场按 story 的 transition：slash（斜斩 + 劈开撕裂）或 shatter（玻璃两次裂开 + 整屏炸碎 + 碎片慢动作后的呼啸）。
用法：python3 audio.py stories/<id>.js out.wav [events.json]
通用部分与 stories/<id>.js 的时间轴对齐：嗡鸣、卡片叮声、渐快心跳、撕裂电流声、斜斩、劈开、闪白冲击、碎片叮当、
金色和弦 + 和声、标题钟声、慢鼓、第二幕的光之低鸣与光波轻响。
人物专属音效来自 events.json（render.js events 从 FIG.events 导出），每条 {t, kind}，见文件末尾的 EVENT_SYNTH。"""
import json, re, sys, wave
import numpy as np

SR = 48000
DUR = 25.2
N = int(SR * DUR)
rng = np.random.default_rng(7)
t = np.arange(N) / SR
L = np.zeros(N); R = np.zeros(N)

# 从 story.js 读卡片时间和关键时刻
# 用法：python3 audio.py stories/<id>.js out.wav
src = open(sys.argv[1], encoding='utf-8').read()
OUT = sys.argv[2] if len(sys.argv) > 2 else 'audio.wav'
EVENTS = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else []
story = json.loads(src.split('window.STORY = ', 1)[1].split(';\nwindow.STORY.t', 1)[0])
card_times = [c[0] for c in story['cards']]
T = {k: float(v) for k, v in re.findall(r"(\w+):\s*(\d+\.\d+)", src.split('t = {')[1].split('}')[0])}
KF = 2 ** (story.get('key', 0) / 12)  # 每支片子换一个调
SH = story.get('transition') == 'shatter'
T_HIT = T['crack'] if SH else T['slash']  # 第一幕结束的那一击


def env(n, a, d):
    e = np.ones(n)
    na = max(1, int(a * SR)); e[:na] = np.linspace(0, 1, na)
    e *= np.exp(-np.arange(n) / SR / d)
    return e


def add(sig, at, pan=0.0, gain=1.0):
    i = int(at * SR)
    if i >= N: return
    sig = sig[:N - i] * gain; pan = min(1.0, max(-1.0, pan))
    L[i:i + len(sig)] += sig * np.sqrt((1 - pan) / 2)
    R[i:i + len(sig)] += sig * np.sqrt((1 + pan) / 2)


def lp_fast(x, k):
    ker = np.ones(k) / k
    return np.convolve(x, ker, mode='same')


def ramp(a, b):
    return np.clip((t - a) / (b - a), 0, 1)


# ---------- 第一幕 ----------
act1 = t < T['flash']
# 低频不安的嗡鸣（D 小调，带拍频）
drone = (np.sin(2 * np.pi * 36.7 * KF * t) + .6 * np.sin(2 * np.pi * 37.3 * KF * t) + .3 * np.sin(2 * np.pi * 73.4 * KF * t + np.sin(t * 1.3)))
drone *= (.25 + .55 * ramp(0, 9)) * act1 * ramp(0, 1.2)
L += drone * .32; R += drone * .32
# 噪声“嘈杂人声”层：逐渐变大
noise = lp_fast(rng.standard_normal(N), 9) * ramp(2, 9) ** 1.5 * act1
L += noise * .10; R += lp_fast(rng.standard_normal(N), 9) * ramp(2, 9) ** 1.5 * act1 * .10

# 推送“叮”声
for i, ct in enumerate(card_times):
    f = [1318.5, 1568, 1760, 2093, 1174.7][i % 5] * KF * (1 + .03 * (i % 3))
    n = int(.35 * SR); tt = np.arange(n) / SR
    s = (np.sin(2 * np.pi * f * tt) + .35 * np.sin(2 * np.pi * f * 2.01 * tt)) * env(n, .002, .09)
    s += np.sin(2 * np.pi * f * 1.5 * tt) * env(n, .002, .05) * .4
    add(s, ct, pan=((i * 37) % 11 - 5) / 6, gain=.22)

# 心跳：从 4.5s 起，越来越快
hb = 4.4
while hb < 8.95:  # 与 fx.js 的 heartbeats 同一公式、同一截止
    for k, (dt, g) in enumerate([(0, 1), (.16, .65)]):
        n = int(.25 * SR); tt = np.arange(n) / SR
        f = 55 * np.exp(-tt * 9) + 38
        s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .004, .07)
        add(s, hb + dt, gain=.75 * g * (0.6 + .4 * (hb - 4.4) / 4.5))
    hb += max(.38, .85 - (hb - 4.4) * .11)

# 上扬噪声 riser
n = int((T_HIT - 5.5) * SR); tt = np.arange(n) / SR
rs = rng.standard_normal(n)
rs = rs - lp_fast(rs, 6)  # 高通感
rs *= (tt / tt[-1]) ** 2.5
sweep = np.sin(2 * np.pi * np.cumsum(200 + 1800 * (tt / tt[-1]) ** 2) / SR) * (tt / tt[-1]) ** 3
add(rs * .18 + sweep * .12, 5.5)

# ---------- 转场 ----------
if not SH:  # 斜斩：金属刷声
    n = int(.6 * SR); tt = np.arange(n) / SR
    sl = rng.standard_normal(n); sl = sl - lp_fast(sl, 4)
    sl *= env(n, .01, .12)
    sl += np.sin(2 * np.pi * np.cumsum(3000 - 2000 * tt) / SR) * env(n, .005, .15) * .3
    add(sl, T['slash'], pan=.4, gain=.55)
# 闪白冲击：低频轰 + 噪声爆
n = int(3.5 * SR); tt = np.arange(n) / SR
boom = np.sin(2 * np.pi * np.cumsum(30 + 90 * np.exp(-tt * 6)) / SR) * env(n, .003, .9)
burst = lp_fast(rng.standard_normal(n), 3) * env(n, .001, .25)
add(boom * 1.0 + burst * .45, T['flash'] - .02, gain=.9)
# 碎片的闪烁叮当
for i in range(40):
    at = T['flash'] + rng.uniform(0, 2.2) ** 1.6
    f = rng.choice([2349, 2637, 2960, 3136, 3520, 3951])
    n = int(.5 * SR); tt = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * tt) * env(n, .001, .12 + rng.uniform(0, .1))
    add(s, at, pan=rng.uniform(-.9, .9), gain=.05 * (1 - (at - T['flash']) / 4))

# ---------- 第二幕：金色和弦 ----------
act2 = ramp(T['flash'], T['flash'] + 1.5) * (1 - ramp(T['fadeOut'], DUR))
chords = [  # D 大调：D - A/C# - Bm - G
    (T['flash'], [146.8, 220, 293.7, 370, 440]),
    (14.2, [138.6, 220, 277.2, 329.6, 440]),
    (17.8, [123.5, 185, 246.9, 293.7, 370]),
    (21.0, [98, 196, 246.9, 293.7, 392]),
]
pad = np.zeros(N); padR = np.zeros(N)
for ci, (st, notes) in enumerate(chords):
    en = chords[ci + 1][0] if ci + 1 < len(chords) else DUR
    m = np.clip((t - st) / .8, 0, 1) * np.clip((en + .8 - t) / .8, 0, 1)
    for k, f in enumerate(notes):
        f *= KF
        for det, side in [(-.18, 0), (.18, 1)]:
            ph = 2 * np.pi * (f + det) * t + k
            w = np.sin(ph) + .25 * np.sin(2 * ph) + .1 * np.sin(3 * ph)
            (pad if side == 0 else padR)[:] += w * m * (1.0 if k else 1.4) / len(notes)
pad *= act2; padR *= act2
L += lp_fast(pad, 5) * .32; R += lp_fast(padR, 5) * .32

# 标题钟声
for at, f, g in [(T['tag'], 587.3, .25), (T['title'], 293.7, .55), (T['title'] + .02, 440, .35), (T['latin'], 880, .18)]:
    f *= KF
    n = int(4 * SR); tt = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * r * tt) * a * np.exp(-tt * d) for r, a, d in [(1, 1, 1.1), (2.76, .4, 2.5), (5.4, .2, 4), (.5, .5, .9)])
    s *= env(n, .002, 10)
    add(s, at, gain=g * .5)

# 慢鼓：72BPM 的低沉战鼓
beat = 60 / 72
bt = T['title']
while bt < T['fadeOut'] + .5:
    for dt, g in [(0, 1), (beat * 1.5, .55)]:
        n = int(.6 * SR); tt = np.arange(n) / SR
        f = 50 + 70 * np.exp(-tt * 25)
        s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .002, .22)
        s += lp_fast(rng.standard_normal(n), 6) * env(n, .001, .03) * .3
        add(s, bt + dt, gain=.55 * g * (1 - np.clip((bt - T['fadeOut']) / 1.2, 0, 1)))
    bt += beat * 2

# 第二幕光源的空气感低鸣：高处几条微微走音的正弦 + 轻柔气声
lg = ramp(T['gold'] + .2, T['gold'] + 1.6) * (1 - ramp(T['fadeOut'], DUR))
hum = sum(np.sin(2 * np.pi * f * KF * t + k) * (.5 + .5 * np.sin(2 * np.pi * .23 * (k + 1) * t)) for k, f in enumerate([1174.7, 1176.1, 1760, 2349.3]))
air = lp_fast(rng.standard_normal(N), 3) - lp_fast(rng.standard_normal(N), 30)
L += (hum * .012 + air * .012) * lg; R += (hum * .012 + air * .014) * lg

# ---------- 追加音效 ----------
# 画面撕裂时的电流声（与 fx.js 的 GLITCH 时间一致）
for g0 in [2.1, 3.4, 4.6, 5.9, 6.7, 7.3, 7.8, 8.25, 8.6]:
    n = int(.16 * SR); tt = np.arange(n) / SR
    sq = np.sign(np.sin(2 * np.pi * rng.uniform(80, 400) * tt)) * .5 + rng.standard_normal(n) * .6
    sq = np.round(sq * 4) / 4 * env(n, .002, .08)
    add(sq, g0, pan=rng.uniform(-.6, .6), gain=.16)
# 闪白后的两声气流（释放感）
for at, g in [(T['flash'] + .1, .45), (T['flash'] + .9, .25)]:
    n = int(1.4 * SR); tt = np.arange(n) / SR
    wh = lp_fast(rng.standard_normal(n), 14) - lp_fast(rng.standard_normal(n), 120)
    wh *= np.sin(np.pi * np.clip(tt / 1.2, 0, 1)) ** 2
    add(wh, at, pan=.3, gain=g * 3)
# 第二幕持续的高频闪光
for i in range(60):
    at = rng.uniform(T['gold'] + 1, T['fadeOut'])
    f = rng.choice([1760, 2093, 2349, 2637, 3136]) * KF
    n = int(.8 * SR); tt = np.arange(n) / SR
    add(np.sin(2 * np.pi * f * tt) * env(n, .003, .25), at, pan=rng.uniform(-.9, .9), gain=.025)
# 和声：高八度柔和长音
choir = np.zeros(N)
for ci, (st, notes) in enumerate(chords):
    en = chords[ci + 1][0] if ci + 1 < len(chords) else DUR
    m = np.clip((t - st) / 1.2, 0, 1) * np.clip((en + .8 - t) / 1.2, 0, 1)
    for f in notes[2:]:
        f *= KF * 2
        vib = 1 + .004 * np.sin(2 * np.pi * 5.2 * t)
        choir += np.sin(2 * np.pi * f * vib * t) * m * (1 + .3 * np.sin(2 * np.pi * .3 * t))
choir *= act2 / 3
L += choir * .09; R += choir * .09

# ---------- 劈开、闪白、光波 ----------
# 画面劈开：向下扫的撕裂噪声 + 次低频下坠
if not SH:
    n = int(.5 * SR); tt = np.arange(n) / SR
    rip = rng.standard_normal(n); rip = lp_fast(rip, 2) - lp_fast(rip, int(8 + 40 * 1))
    rip *= np.sin(np.pi * np.clip(tt / .45, 0, 1)) ** 1.5 * (1 + 2 * np.sin(2 * np.pi * 37 * tt) ** 2)
    drop = np.sin(2 * np.pi * np.cumsum(90 * np.exp(-tt * 5) + 28) / SR) * env(n, .01, .3)
    add(rip * .35 + drop * .6, T['split'] - .02, gain=.6)

# ---------- 玻璃破碎（shatter） ----------
def glass_tink(f, d=.35):  # 一小片玻璃的脆响：几条不成谐波的高频正弦
    n = int((d + .1) * SR); tt = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * f * r * tt + rng.uniform(0, 6)) * a * np.exp(-tt / (d * dd)) for r, a, dd in [(1, 1, 1), (2.32, .5, .6), (3.87, .3, .4), (5.1, .15, .3)])


def crackle(dur, n_clicks, accel=1.5):  # 裂纹蔓延：一串越来越密的细碎咔嚓
    n = int(dur * SR); out = np.zeros(n)
    for k in range(n_clicks):
        at = int(n * (k / n_clicks) ** accel)
        m = int(.012 * SR); c = rng.standard_normal(m); c = (c - lp_fast(c, 2)) * np.exp(-np.arange(m) / SR / .002)
        out[at:at + m] += c[:max(0, n - at)] * rng.uniform(.4, 1)
    return out


if SH:
    # 第一击：手机屏被击中——闷响 + 高频脆响 + 一小串裂纹声
    n = int(1.2 * SR); tt = np.arange(n) / SR
    thud = np.sin(2 * np.pi * np.cumsum(60 + 140 * np.exp(-tt * 30)) / SR) * env(n, .001, .12)
    snap = rng.standard_normal(n); snap = (snap - lp_fast(snap, 2)) * env(n, .0002, .015)
    add(thud * .9 + snap * .8, T['crack'], gain=.7)
    for f in [3100, 4400, 5900]: add(glass_tink(f * rng.uniform(.95, 1.05), .5), T['crack'] + rng.uniform(0, .02), pan=rng.uniform(-.4, .4), gain=.09)
    add(crackle(.3, 26, 1.2), T['crack'] + .01, pan=-.2, gain=.35)
    # 第二击：裂纹爬满全屏——更重的闷响 + 一长串加速的裂纹声 + 玻璃受力的尖鸣
    n = int(1.4 * SR); tt = np.arange(n) / SR
    thud = np.sin(2 * np.pi * np.cumsum(45 + 110 * np.exp(-tt * 20)) / SR) * env(n, .001, .25)
    add(thud, T['crack2'], gain=.75)
    add(crackle(.42, 70, .7), T['crack2'], pan=.2, gain=.42); add(crackle(.42, 60, .8), T['crack2'] + .01, pan=-.3, gain=.36)
    n = int((T['flash'] - T['crack2']) * SR); tt = np.arange(n) / SR
    whine = np.sin(2 * np.pi * np.cumsum(2200 + 2600 * (tt / tt[-1]) ** 2) / SR) * (tt / tt[-1]) ** 2 * .5
    swell = rng.standard_normal(n); swell = (swell - lp_fast(swell, 3)) * (tt / tt[-1]) ** 3   # 炸开前倒吸一口气的上扬
    add(whine * .25 + swell * .5, T['crack2'], gain=.4)
    # 整屏炸碎：亮的噪声爆 + 一大把玻璃碎片的叮当（前密后疏，像慢动作）
    n = int(1.6 * SR); tt = np.arange(n) / SR
    burst = rng.standard_normal(n); burst = (burst - lp_fast(burst, 3)) * env(n, .001, .18)
    add(burst, T['flash'] - .01, gain=.55)
    for i in range(90):
        at = T['flash'] + rng.uniform(0, 1) ** 2.4 * 1.1
        add(glass_tink(rng.uniform(2200, 7800), rng.uniform(.15, .5)), at, pan=rng.uniform(-.95, .95), gain=.07 * (1 - (at - T['flash']) / 1.6))
    # 慢动作里碎片悬着：一层很轻的、拉长了的玻璃泛音
    n = int(1.4 * SR); tt = np.arange(n) / SR
    bed = sum(np.sin(2 * np.pi * f * tt + k) for k, f in enumerate([1975, 2637, 3322, 4186])) * np.sin(np.pi * tt / tt[-1]) ** 2
    add(bed, T['flash'] + .2, pan=.1, gain=.02)
    # 碎片加速飞出镜头：呼啸
    n = int(1.3 * SR); tt = np.arange(n) / SR
    wh = rng.standard_normal(n); wh = lp_fast(wh, 6) - lp_fast(wh, 60)
    wh *= np.sin(np.pi * np.clip(tt / 1.1, 0, 1)) ** 2 * (tt / 1.1 + .2)
    add(wh, T['flash'] + 1.15, pan=-.3, gain=1.6); add(wh[::-1].copy(), T['flash'] + 1.2, pan=.4, gain=.8)
# 闪白瞬间的脆响
n = int(.25 * SR); tt = np.arange(n) / SR
crk = rng.standard_normal(n); crk = crk - lp_fast(crk, 2)
add(crk * env(n, .0003, .04), T['flash'] - .03, gain=.45)
# 光波：每一圈扩散时一声很轻的玻璃钟（与人物文件里的光波同周期：第 1 + i×0.9 秒起，每 2.7 秒一圈）
for i in range(3):
    st = T['gold'] + 1 + i * .9
    while st < T['fadeOut']:
        f = [2637, 3136, 3951][i] * KF / 2
        n = int(2.5 * SR); tt = np.arange(n) / SR
        s = (np.sin(2 * np.pi * f * tt) + .3 * np.sin(2 * np.pi * f * 2.76 * tt) * np.exp(-tt * 3)) * env(n, .004, .9)
        add(s, st, pan=-.35, gain=.035)
        st += 2.7

# ---------- 人物专属音效（events.json） ----------
def karplus(f, dur, damp=.996):
    n = int(dur * SR); p = max(2, int(SR / f)); buf = rng.uniform(-1, 1, p); out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % p]; buf[i % p] = damp * .5 * (buf[i % p] + buf[(i + 1) % p])
    return out


def ev_creak(e):  # 木头吱呀 + 一声“咚”：木偶鼻子长一截
    n = int(.45 * SR); tt = np.arange(n) / SR
    fr = 180 + 90 * np.sin(2 * np.pi * 7 * tt) + 400 * tt
    sq = np.sign(np.sin(2 * np.pi * np.cumsum(fr) / SR)) * (lp_fast(rng.standard_normal(n), 2) * .6 + .4)
    sq = lp_fast(sq, 6) * np.sin(np.pi * np.clip(tt / .4, 0, 1)) ** .7
    knock = np.sin(2 * np.pi * np.cumsum(420 * np.exp(-tt * 30) + 210) / SR) * env(n, .001, .05)
    add(sq * .5 + knock, e['t'], pan=-.2, gain=.32)


def ev_knock(e):  # 木关节被提线一扯的“咔嗒”
    n = int(.12 * SR); tt = np.arange(n) / SR
    s = np.sin(2 * np.pi * rng.uniform(600, 900) * tt) * env(n, .0005, .02) + lp_fast(rng.standard_normal(n), 2) * env(n, .0003, .008)
    add(s, e['t'], pan=rng.uniform(-.3, .5), gain=.22)


def ev_twang(e):  # 提线被斩断：拨弦一声，音高往下掉
    s = karplus(rng.uniform(330, 520) * KF, 1.2, .994)
    n = len(s); tt = np.arange(n) / SR
    s *= np.exp(-tt * 2.5)
    snap = rng.standard_normal(int(.03 * SR)); snap = snap - lp_fast(snap, 2)
    add(s, e['t'], pan=rng.uniform(-.2, .6), gain=.5); add(snap * env(len(snap), .0002, .01), e['t'], gain=.4)


def ev_clatter(e):  # 木架、木屑落地的一串木头碰撞声
    for i in range(9):
        at = e['t'] + .15 + rng.uniform(0, 1.4) ** 1.3
        n = int(.15 * SR); tt = np.arange(n) / SR
        s = np.sin(2 * np.pi * rng.uniform(300, 1100) * tt) * env(n, .0005, .03) + lp_fast(rng.standard_normal(n), 3) * env(n, .0003, .01) * .6
        add(s, at, pan=rng.uniform(-.8, .8), gain=.12 * (1 - (at - e['t']) / 2))


def ev_retract(e):  # 长鼻子缩回去：一串往上走的晶亮音
    d = e.get('dur', 1.2)
    n = int((d + 1) * SR); tt = np.arange(n) / SR
    f = (900 + 1600 * np.clip(tt / d, 0, 1) ** 1.5) * KF
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * np.clip(tt / d, 0, 1)) ** 1.2 * .4
    for j in range(10):
        at = d * j / 10; m = int(.5 * SR); t2 = np.arange(m) / SR; fj = (1200 + 180 * j) * KF
        s[int(at * SR):int(at * SR) + m] += np.sin(2 * np.pi * fj * t2)[:max(0, n - int(at * SR))] * env(m, .002, .15)[:max(0, n - int(at * SR))] * .35
    add(s, e['t'], pan=-.4, gain=.16)


def ev_swell(e):  # 肚子鼓一圈：低沉的“咕噜”往上一挺 + 衣服绷紧的吱一声
    n = int(.6 * SR); tt = np.arange(n) / SR
    f = 55 + 70 * np.clip(tt / .2, 0, 1) ** .6 + 6 * np.sin(2 * np.pi * 9 * tt)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * np.clip(tt / .5, 0, 1)) ** .8
    st = rng.standard_normal(n); st = (lp_fast(st, 3) - lp_fast(st, 20)) * np.exp(-((tt - .14) / .05) ** 2)
    add(s + st * .5, e['t'], pan=.15, gain=.4)


def ev_buzz(e):  # 手机震动：嗡嗡两下
    n = int(.42 * SR); tt = np.arange(n) / SR
    s = np.tanh(3 * np.sin(2 * np.pi * 172 * tt)) * (((tt % .21) < .13) * 1.0) * np.exp(-tt * 2)
    add(lp_fast(s, 8), e['t'] + .02, pan=-.25, gain=.07)


def ev_contract(e):  # 轮廓收紧、脂肪烧掉：往上走的闪烁 + 滋滋的火星
    d = e.get('dur', 1.2); n = int((d + .6) * SR); tt = np.arange(n) / SR; u = np.clip(tt / d, 0, 1)
    f = (220 + 660 * u ** 1.4) * KF
    tone = sum(np.sin(2 * np.pi * np.cumsum(f * r) / SR) * a for r, a in [(1, 1), (1.5, .5), (2, .35)]) * np.sin(np.pi * u) ** .8
    siz = rng.standard_normal(n); siz = (siz - lp_fast(siz, 2)) * (rng.uniform(0, 1, n) < .02) * 3 + (siz - lp_fast(siz, 3)) * .15
    siz *= np.sin(np.pi * u) * (tt < d + .3)
    add(tone * .3 + siz * .5, e['t'], pan=.2, gain=.22)


def ev_counter(e):  # 计数器从第 1 天跑到第 365 天：先快后慢的滴答，最后“叮”
    t0, t1 = e['t'], e['t1']
    def eio(x): return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
    ts = np.linspace(t0, t1, 4000); vals = np.array([eio((x - t0) / (t1 - t0)) for x in ts])
    for d in range(10, 365, 14):
        at = ts[np.searchsorted(vals, d / 365)]
        m = int(.03 * SR); tk = np.sin(2 * np.pi * 2900 * KF * np.arange(m) / SR) * np.exp(-np.arange(m) / SR / .006)
        add(tk, at, pan=-.5, gain=.05)
    add(glass_tink(1760 * KF, .9), t1, pan=-.5, gain=.16)


def ev_clench(e):  # 握紧拳头：皮革吱一声 + 沉的一击 + 光亮起来的和弦
    n = int(.25 * SR); tt = np.arange(n) / SR
    cr = rng.standard_normal(n); cr = (lp_fast(cr, 2) - lp_fast(cr, 12)) * (np.sin(2 * np.pi * 38 * tt) > .3) * np.exp(-tt * 9)
    add(cr, e['t'] - .12, pan=-.4, gain=.35)
    n = int(2.5 * SR); tt = np.arange(n) / SR
    hit = np.sin(2 * np.pi * np.cumsum(42 + 90 * np.exp(-tt * 18)) / SR) * env(n, .002, .5)
    shine = sum(np.sin(2 * np.pi * f * KF * tt) for f in [587.3, 880, 1174.7, 1760]) * env(n, .02, .9) * .2
    add(hit + shine, e['t'], pan=-.3, gain=.6)


def ev_pose(e):  # 摆一个造型：挥臂的呼啸越来越近 → 定格的一声闷击 + 和弦重音 + 高处的闪光
    pre = e.get('pre', .42); n = int((pre + .08) * SR); tt = np.arange(n) / SR
    wh = rng.standard_normal(n); wh = lp_fast(wh, 4) - lp_fast(wh, 40)
    wh *= np.clip(tt / pre, 0, 1) ** 2 * np.clip((pre + .08 - tt) / .08, 0, 1)
    add(wh, e['t'] - pre, pan=.25, gain=.9)
    n = int(1.8 * SR); tt = np.arange(n) / SR
    hit = np.sin(2 * np.pi * np.cumsum(48 + 80 * np.exp(-tt * 22)) / SR) * env(n, .002, .35)
    stab = sum(np.sin(2 * np.pi * f * KF * tt) for f in [293.7, 440, 587.3, 880]) * env(n, .005, .45) * .18
    shimmer = sum(np.sin(2 * np.pi * f * KF * tt + k) for k, f in enumerate([1760, 2349.3, 2960])) * env(n, .01, .7) * .06
    add(hit + stab + shimmer, e['t'], pan=-.1, gain=.5)


def metal_hit(f0, d=.6):  # 一块铁的撞击：几条不成谐波的泛音 + 一点噪声
    n = int((d + .1) * SR); tt = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f0 * r * tt + rng.uniform(0, 6)) * a * np.exp(-tt / (d * dd)) for r, a, dd in [(1, 1, 1), (2.41, .6, .5), (3.93, .4, .35), (5.6, .25, .22), (7.9, .15, .15)])
    nz = rng.standard_normal(n); nz = (nz - lp_fast(nz, 3)) * np.exp(-tt / .012)
    return s + nz * .6


def ev_clank(e):  # 锁链缠上一圈：沉的铁链撞击 + 一串链环哗啦
    g = e.get('g', 1)
    n = int(1.2 * SR); tt = np.arange(n) / SR
    thud = np.sin(2 * np.pi * np.cumsum(70 * np.exp(-tt * 14) + 46) / SR) * env(n, .002, .25)
    add(thud, e['t'], gain=.55 * g)
    add(metal_hit(rng.uniform(380, 460), .7), e['t'], pan=.2, gain=.22 * g)
    for i in range(10):
        add(metal_hit(rng.uniform(1400, 3200), .12), e['t'] + .02 + rng.uniform(0, .35) ** 1.4, pan=rng.uniform(-.5, .7), gain=.07 * g)


def ev_rattle(e):  # 心跳时锁链一绷：几声细碎的链环磕碰
    for i in range(5):
        add(metal_hit(rng.uniform(1600, 3400), .09), e['t'] + .01 + rng.uniform(0, .15), pan=rng.uniform(-.3, .7), gain=.05)


def ev_snap(e):  # 斩断一根铁链：高频的铮 + 断裂的咔
    g = e.get('g', 1)
    add(metal_hit(rng.uniform(900, 1300), .9), e['t'], pan=rng.uniform(-.1, .6), gain=.22 * g)
    n = int(.05 * SR); cr = rng.standard_normal(n); cr = (cr - lp_fast(cr, 2)) * env(n, .0002, .01)
    add(cr, e['t'], gain=.4 * g)


def ev_chainfall(e):  # 锁链崩散：几十节链环四散、落地的叮当
    for i in range(46):
        at = e['t'] + .05 + rng.uniform(0, 2.4) ** 1.5
        add(metal_hit(rng.uniform(900, 3600), rng.uniform(.08, .25)), at, pan=rng.uniform(-.9, .9), gain=.07 * (1 - (at - e['t']) / 4))
    n = int(.4 * SR); tt = np.arange(n) / SR
    add(np.sin(2 * np.pi * np.cumsum(140 * np.exp(-tt * 20) + 60) / SR) * env(n, .001, .12), e['t'] + 1.15, pan=-.3, gain=.25)  # 挂锁落地


def ev_rise(e):  # 手臂带着袖子举起火炬：布料呼啦一声 + 往上走的风
    d = e['dur']; n = int((d + .3) * SR); tt = np.arange(n) / SR; u = np.clip(tt / d, 0, 1)
    wh = rng.standard_normal(n); wh = lp_fast(wh, 5) - lp_fast(wh, 50)
    wh *= np.sin(np.pi * u) ** 1.5 * (1 - np.clip((tt - d) / .3, 0, 1))
    cloth = rng.standard_normal(n); cloth = (lp_fast(cloth, 2) - lp_fast(cloth, 8)) * (np.sin(2 * np.pi * 23 * tt) > .2) * np.sin(np.pi * u) * .4
    add(wh + cloth, e['t'], pan=-.3, gain=1.0)


def ev_ignite(e):  # 火炬点燃：“轰”的一声燃气 + 低频冲击 + 亮起来的大和弦
    n = int(2.5 * SR); tt = np.arange(n) / SR
    roar = rng.standard_normal(n); roar = lp_fast(roar, 10) - lp_fast(roar, 200)
    roar *= np.clip(tt / .05, 0, 1) * np.exp(-tt * 1.6)
    hit = np.sin(2 * np.pi * np.cumsum(38 + 100 * np.exp(-tt * 16)) / SR) * env(n, .002, .6)
    pre = rng.standard_normal(int(.35 * SR)); pre = (lp_fast(pre, 3) - lp_fast(pre, 30)) * np.linspace(0, 1, len(pre)) ** 3
    add(pre, e['t'] - .35, pan=-.3, gain=.8)
    shine = sum(np.sin(2 * np.pi * f * KF * tt) for f in [293.7, 440, 587.3, 740, 880, 1174.7]) * env(n, .03, 1.2) * .16
    add(roar * 2.2 + hit + shine, e['t'], pan=-.3, gain=.6)


def ev_ray(e):  # 皇冠的一道光芒亮起：清亮的钟琴，一道比一道高
    f = [587.3, 659.3, 740, 880, 987.8, 1174.7, 1318.5][e['i'] % 7] * KF * 2
    n = int(1.6 * SR); tt = np.arange(n) / SR
    s = (np.sin(2 * np.pi * f * tt) + .35 * np.sin(2 * np.pi * f * 2.0 * tt) * np.exp(-tt * 4) + .15 * np.sin(2 * np.pi * f * 3.01 * tt) * np.exp(-tt * 7)) * env(n, .002, .55)
    add(s, e['t'], pan=-.2 + e['i'] * .1, gain=.09)


def ev_fire(e):  # 火炬持续燃烧：低沉的火焰呼呼声 + 噼啪
    i0 = int(e['t'] * SR); n = N - i0; tt = np.arange(n) / SR
    base = rng.standard_normal(n); base = lp_fast(base, 40) - lp_fast(base, 400)
    base *= (.7 + .3 * np.sin(2 * np.pi * .7 * tt) * np.sin(2 * np.pi * 1.9 * tt)) * np.clip(tt / .4, 0, 1)
    add(base * 1.8, e["t"], pan=-.35, gain=.22)
    at = e['t'] + .2
    while at < e['t1'] - .5:
        m = int(.02 * SR); ck = rng.standard_normal(m); ck = (ck - lp_fast(ck, 2)) * np.exp(-np.arange(m) / SR / .003)
        add(ck, at, pan=rng.uniform(-.6, 0), gain=.045 * rng.uniform(.3, 1))
        at += rng.exponential(.16)


def ev_wings(e):  # 一群白鸽振翅飞出：一串扑棱扑棱，先近后远
    for b in range(e.get('n', 7)):
        st = e['t'] + b * .09; fr = rng.uniform(3.2, 4.4); pan = rng.uniform(-.9, .3)
        for k in range(int(rng.uniform(6, 9))):
            at = st + k / fr; g = .1 * (1 - k / 10) * (1 - b / 14)
            n = int(.11 * SR); tt = np.arange(n) / SR
            fl = rng.standard_normal(n); fl = lp_fast(fl, 4) - lp_fast(fl, 25)
            fl *= np.sin(np.pi * np.clip(tt / .1, 0, 1)) ** 2
            add(fl, at, pan=pan - k * .05, gain=g * 2.2)
    n = int(2.2 * SR); tt = np.arange(n) / SR
    add(sum(np.sin(2 * np.pi * f * KF * tt + k) for k, f in enumerate([1760, 2217.5, 2637])) * env(n, .05, .7) * .05, e['t'], pan=-.4)


def mixs(*sigs):  # 把长短不一的几段声音叠在一起
    out = np.zeros(max(len(x) for x in sigs))
    for x in sigs: out[:len(x)] += x
    return out


def ev_coin(e):  # 一枚银币掉下去：清脆的两声叮
    for k, dt in enumerate([0, .09]):
        n = int(.3 * SR); tt = np.arange(n) / SR; f = rng.uniform(2600, 3400)
        s = (np.sin(2 * np.pi * f * tt) + .5 * np.sin(2 * np.pi * f * 1.48 * tt) + .3 * np.sin(2 * np.pi * f * 2.3 * tt)) * env(n, .0005, .06)
        add(s, e['t'] + dt, pan=-.35, gain=.06 * (1 - k * .5))


def ev_armorcrack(e):  # 心跳时纹章又裂一道：金属崩裂的脆响 + 低沉的吱
    n = int(.06 * SR); cr = rng.standard_normal(n); cr = (cr - lp_fast(cr, 2)) * env(n, .0002, .012)
    add(cr, e['t'] + .02, pan=.25, gain=.35)
    add(metal_hit(rng.uniform(520, 700), .35), e['t'] + .02, pan=.25, gain=.1)
    n = int(.35 * SR); tt = np.arange(n) / SR
    cre = np.sign(np.sin(2 * np.pi * np.cumsum(90 + 40 * np.sin(2 * np.pi * 9 * tt)) / SR)) * np.sin(np.pi * np.clip(tt / .3, 0, 1))
    add(lp_fast(cre, 12), e['t'], pan=.25, gain=.05)


def ev_coinburst(e):  # 钱袋炸开：几十枚金币四散的叮当 + 一声闷
    for i in range(55):
        at = e['t'] + rng.uniform(0, 2.6) ** 1.5
        n = int(.35 * SR); tt = np.arange(n) / SR; f = rng.uniform(2200, 4200)
        s = (np.sin(2 * np.pi * f * tt) + .5 * np.sin(2 * np.pi * f * 1.48 * tt)) * env(n, .0005, .05 + rng.uniform(0, .05))
        add(s, at, pan=rng.uniform(-.9, .9), gain=.05 * (1 - (at - e['t']) / 4))


def ev_summon(e):  # 剑从光里长出来：往上走的光之和声 + 出鞘的“锵”
    d = e['dur']; n = int((d + 1.6) * SR); tt = np.arange(n) / SR; u = np.clip(tt / d, 0, 1)
    sh = sum(np.sin(2 * np.pi * np.cumsum((400 + 1400 * u ** 1.5) * r * KF) / SR) * a for r, a in [(1, 1), (1.5, .5), (2, .35)]) * np.sin(np.pi * u) ** .7
    nz = rng.standard_normal(n); nz = (lp_fast(nz, 2) - lp_fast(nz, 6)) * u ** 2 * (tt < d)
    add(sh * .12 + nz * .25, e['t'], pan=-.3, gain=.6)
    ring = mixs(metal_hit(1180 * KF, 1.4), metal_hit(2360 * KF, .8) * .4)
    add(ring, e['t'] + d, pan=-.3, gain=.16)


def ev_swing(e):  # 挥剑：越来越近的破风声
    pre = e.get('pre', .45); n = int((pre + .1) * SR); tt = np.arange(n) / SR
    wh = rng.standard_normal(n); wh = lp_fast(wh, 3) - lp_fast(wh, 30)
    wh *= np.clip(tt / pre, 0, 1) ** 2.2 * np.clip((pre + .1 - tt) / .1, 0, 1)
    add(wh, e['t'] - pre, pan=-.3, gain=1.0)


def ev_oath(e):  # 宣誓礼定格：剑身长鸣 + 低沉一击 + 大和弦
    big = e.get('big'); g = 1 if big else .6
    n = int(3 * SR); tt = np.arange(n) / SR
    hit = np.sin(2 * np.pi * np.cumsum(40 + 90 * np.exp(-tt * 18)) / SR) * env(n, .002, .5 if big else .3)
    ring = mixs(metal_hit(587.3 * KF, 1.8) * .5, metal_hit(880 * KF, 1.4) * .35)
    chord = sum(np.sin(2 * np.pi * f * KF * tt + k) for k, f in enumerate([146.8, 220, 293.7, 370, 440, 587.3])) * env(n, .04, 1.6 if big else .9) * .12
    add(hit + chord, e['t'], pan=-.2, gain=.6 * g); add(ring[:n], e['t'], pan=-.35, gain=.2 * g)


def ev_thunder(e):  # 举剑引雷：电弧噼啪 + 雷声滚过
    t0 = e['t']; at = t0
    while at < t0 + .8:
        m = int(.012 * SR); ck = rng.standard_normal(m); ck = (ck - lp_fast(ck, 2)) * np.exp(-np.arange(m) / SR / .002)
        add(ck, at, pan=rng.uniform(-.7, .1), gain=.22 * (1 - (at - t0) / .9)); at += rng.exponential(.018)
    n = int(2.6 * SR); tt = np.arange(n) / SR
    rum = lp_fast(rng.standard_normal(n), 60) * (np.clip(tt / .03, 0, 1) * np.exp(-tt * 1.6)) * (1 + .5 * np.sin(2 * np.pi * 3 * tt))
    crack = rng.standard_normal(int(.15 * SR)); crack = (crack - lp_fast(crack, 3)) * env(len(crack), .0005, .04)
    hit = np.sin(2 * np.pi * np.cumsum(34 + 70 * np.exp(-tt * 12)) / SR) * env(n, .002, .45)
    add(rum * 6 + hit, t0, pan=-.2, gain=.55); add(crack, t0, pan=-.3, gain=.5)


def ev_plant(e):  # 剑尖顿地：沉重的一击 + 剑身嗡鸣 + 碎石
    n = int(2.4 * SR); tt = np.arange(n) / SR
    hit = np.sin(2 * np.pi * np.cumsum(30 + 110 * np.exp(-tt * 22)) / SR) * env(n, .001, .55)
    dust = lp_fast(rng.standard_normal(n), 25) * env(n, .002, .3)
    add(hit + dust * 2, e['t'], pan=-.2, gain=.75)
    add(mixs(metal_hit(330 * KF, 1.6) * .6, metal_hit(990 * KF, .9) * .3), e['t'], pan=-.3, gain=.16)
    for i in range(14):
        at = e['t'] + .05 + rng.uniform(0, .9); m = int(.1 * SR)
        s = np.sin(2 * np.pi * rng.uniform(500, 1500) * np.arange(m) / SR) * env(m, .0005, .02)
        add(s, at, pan=rng.uniform(-.7, .3), gain=.07)


def ev_heartcalm(e):  # 第二幕：平稳、有力的心跳（和纹章的脉动同步）
    hb = e['t']
    while hb < e['t1'] - 1.2:
        for dt, g in [(0, 1), (.19, .6)]:
            n = int(.3 * SR); tt = np.arange(n) / SR
            s = np.sin(2 * np.pi * np.cumsum(46 * np.exp(-tt * 7) + 34) / SR) * env(n, .006, .09)
            add(s, hb + dt, gain=.3 * g)
        hb += e['period']


EVENT_SYNTH = dict(creak=ev_creak, knock=ev_knock, twang=ev_twang, clatter=ev_clatter, retract=ev_retract,
                   swell=ev_swell, buzz=ev_buzz, contract=ev_contract, counter=ev_counter, clench=ev_clench, pose=ev_pose,
                   clank=ev_clank, rattle=ev_rattle, snap=ev_snap, chainfall=ev_chainfall, rise=ev_rise, ignite=ev_ignite,
                   ray=ev_ray, fire=ev_fire, wings=ev_wings,
                   coin=ev_coin, armorcrack=ev_armorcrack, coinburst=ev_coinburst, summon=ev_summon, swing=ev_swing,
                   oath=ev_oath, thunder=ev_thunder, plant=ev_plant, heartcalm=ev_heartcalm)
for e in EVENTS:
    EVENT_SYNTH[e['kind']](e)

# ---------- 简易混响 + 母带 ----------
def reverb(x):
    y = x.copy()
    for d, g in [(.031, .35), (.047, .3), (.073, .25), (.109, .2), (.163, .15), (.241, .1)]:
        k = int(d * SR); y[k:] += x[:-k] * g
    return y
L = reverb(L); R = reverb(R)
fade = np.clip(t / .3, 0, 1) * np.clip((DUR - t) / .6, 0, 1)
L *= fade; R *= fade
peak = max(np.abs(L).max(), np.abs(R).max())
L /= peak; R /= peak
L = np.tanh(L * 1.3) / np.tanh(1.3); R = np.tanh(R * 1.3) / np.tanh(1.3)
pcm = (np.stack([L, R], 1) * 32767 * .89).astype(np.int16)
with wave.open(OUT, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('ok', T)
