"""七美德·节制 —— 全合成配乐与音效（numpy），输出 audio.wav（48k 立体声）。
时间点与 story.js 对齐：卡片弹出叮声、心跳加速、斜斩、闪白冲击、金色和弦、标题钟声、慢鼓。"""
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
story = json.loads(src.split('window.STORY = ', 1)[1].split(';\nwindow.STORY.t', 1)[0])
card_times = [c[0] for c in story['cards']]
T = {k: float(v) for k, v in re.findall(r"(\w+):\s*(\d+\.\d+)", src.split('t = {')[1].split('}')[0])}
KF = 2 ** (story.get('key', 0) / 12)  # 每支片子换一个调


def env(n, a, d):
    e = np.ones(n)
    na = max(1, int(a * SR)); e[:na] = np.linspace(0, 1, na)
    e *= np.exp(-np.arange(n) / SR / d)
    return e


def add(sig, at, pan=0.0, gain=1.0):
    i = int(at * SR)
    if i >= N: return
    sig = sig[:N - i] * gain
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
while hb < T['slash'] - .1:
    for k, (dt, g) in enumerate([(0, 1), (.16, .65)]):
        n = int(.25 * SR); tt = np.arange(n) / SR
        f = 55 * np.exp(-tt * 9) + 38
        s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .004, .07)
        add(s, hb + dt, gain=.75 * g * (0.6 + .4 * (hb - 4.4) / 4.5))
    hb += max(.38, .85 - (hb - 4.4) * .11)

# 上扬噪声 riser
n = int((T['slash'] - 5.5) * SR); tt = np.arange(n) / SR
rs = rng.standard_normal(n)
rs = rs - lp_fast(rs, 6)  # 高通感
rs *= (tt / tt[-1]) ** 2.5
sweep = np.sin(2 * np.pi * np.cumsum(200 + 1800 * (tt / tt[-1]) ** 2) / SR) * (tt / tt[-1]) ** 3
add(rs * .18 + sweep * .12, 5.5)

# ---------- 转场 ----------
# 斜斩：金属刷声
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

# 水流细声（第二幕持续）
wn = lp_fast(rng.standard_normal(N), 3) - lp_fast(rng.standard_normal(N), 40)
wn *= (0.6 + .4 * np.sin(2 * np.pi * 3.3 * t) ** 2) * ramp(T['gold'] + .6, T['gold'] + 1.8) * (1 - ramp(T['fadeOut'], DUR))
L += wn * .025; R += wn * .03

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
