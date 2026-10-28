"""程序合成音效：低频嗡鸣 + 每级脚步 + 上升的圣光和声 + 结尾升腾。输出 48k 立体声 wav。"""
import sys, numpy as np, wave
SR, DUR, RATE = 48000, 3.0, 1.6
t = np.arange(int(SR * DUR)) / SR
rng = np.random.default_rng(1)
out = np.zeros_like(t)
env = lambda a, b: np.clip((t - a) / (b - a), 0, 1)
# 低频嗡鸣，缓慢升调
f = 55 * (1 + 0.12 * env(0, 3) ** 2)
ph = 2 * np.pi * np.cumsum(f) / SR
out += 0.30 * (np.sin(ph) + 0.4 * np.sin(2 * ph)) * env(0, 0.4)
# 圣光和声：五度+八度，随时间渐强，带颤音
for fr, a in ((440, 1), (660, .7), (880, .5), (1320, .3)):
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t)
    p = 2 * np.pi * np.cumsum(fr * vib * (1 + 0.06 * env(0, 3))) / SR
    out += 0.07 * a * np.sin(p) * env(0.3, 2.9) ** 2
# 脚步：每落一级一声闷响
for k in range(1, int(DUR * RATE) + 1):
    t0 = k / RATE
    d = t - t0
    m = d >= 0
    hit = np.zeros_like(t)
    hit[m] = (np.sin(2 * np.pi * 70 * d[m]) * np.exp(-d[m] * 28) + 0.3 * rng.normal(0, 1, m.sum()) * np.exp(-d[m] * 60))
    out += 0.45 * hit
# 结尾升腾：滤波噪声扫频 + 钟声
noise = rng.normal(0, 1, len(t))
sw = np.convolve(noise, np.ones(8) / 8, 'same') * env(1.8, 2.9) ** 3 * 0.18
out += sw
d = t - 2.5
m = d >= 0
for fr in (523.25, 784, 1046.5, 1568):
    out[m] += 0.10 * np.sin(2 * np.pi * fr * d[m]) * np.exp(-d[m] * 2.5)
out *= np.clip((DUR - t) / 0.08, 0, 1)
out = out / np.abs(out).max() * 0.85
st = np.stack([out, np.roll(out, 240) * 0.95], 1)
with wave.open(sys.argv[1], 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype(np.int16).tobytes())
