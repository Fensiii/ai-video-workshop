"""程序合成音效：暴雨 + 雷声 → 放晴后圣光和声；全程脚步与低频嗡鸣。输出 48k 立体声 wav。"""
import sys, numpy as np, wave
SR, DUR, RATE = 48000, 5.0, 1.6
STRIKES = [(0.45, 1.0), (1.30, 0.85), (1.95, 0.5)]
t = np.arange(int(SR * DUR)) / SR
rng = np.random.default_rng(1)
ramp = lambda a, b: np.clip((t - a) / (b - a), 0, 1)
sm = lambda x: x * x * (3 - 2 * x)
def lowpass(x, n):
    return np.convolve(x, np.ones(n) / n, 'same')
storm = 1 - sm(ramp(2.0, 4.0))
rain = 1 - sm(ramp(1.8, 3.4))
out = np.zeros_like(t)
# 雨声：亮噪声 + 密集雨滴
nz = rng.normal(0, 1, len(t))
out += 0.22 * (nz - lowpass(nz, 6)) * rain
out += 0.10 * lowpass(nz, 3) * rain
# 雷声：近处炸裂 + 长尾滚雷
for t0, amp in STRIKES:
    d = t - t0 - 0.08
    m = d >= 0
    crack = np.zeros_like(t); crack[m] = rng.normal(0, 1, m.sum()) * np.exp(-d[m] * 18)
    roll = np.zeros_like(t); roll[m] = rng.normal(0, 1, m.sum()) * np.exp(-d[m] * 1.4) * (1 + 0.6 * np.sin(2 * np.pi * 3.1 * d[m]))
    out += amp * (0.5 * lowpass(crack, 4) + 2.2 * lowpass(lowpass(roll, 120), 60))
# 低频嗡鸣：雨中阴沉，放晴后升调
f = 49 * (1 + 0.12 * sm(ramp(2.5, 5)))
ph = 2 * np.pi * np.cumsum(f) / SR
out += 0.22 * (np.sin(ph) + 0.4 * np.sin(2 * ph)) * ramp(0, 0.5)
# 圣光和声：云开后渐强
for fr, a in ((440, 1), (660, .7), (880, .5), (1320, .3)):
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t)
    p = 2 * np.pi * np.cumsum(fr * vib * (1 + 0.04 * ramp(2.5, 5))) / SR
    out += 0.08 * a * np.sin(p) * sm(ramp(2.6, 4.8)) ** 1.5
# 脚步：每落一级一声（雨中带水声）
for k in range(1, int(DUR * RATE) + 1):
    t0 = k / RATE
    d = t - t0; m = d >= 0
    hit = np.zeros_like(t)
    wet = 1 - sm(min(max((t0 - 2.0) / 2.0, 0), 1))
    hit[m] = np.sin(2 * np.pi * 70 * d[m]) * np.exp(-d[m] * 28) + (0.3 + 0.5 * wet) * rng.normal(0, 1, m.sum()) * np.exp(-d[m] * 40)
    out += 0.4 * hit
# 结尾升腾 + 钟声
out += lowpass(nz, 8) * sm(ramp(3.6, 4.9)) ** 3 * 0.18
d = t - 4.4; m = d >= 0
for fr in (523.25, 784, 1046.5, 1568):
    out[m] += 0.10 * np.sin(2 * np.pi * fr * d[m]) * np.exp(-d[m] * 2.5)
out *= np.clip((DUR - t) / 0.08, 0, 1)
out = out / np.abs(out).max() * 0.85
st = np.stack([out, np.roll(out, 240) * 0.95], 1)
with wave.open(sys.argv[1], 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype(np.int16).tobytes())
