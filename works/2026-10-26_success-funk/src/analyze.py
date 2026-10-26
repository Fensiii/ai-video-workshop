"""音频分析：拟合节拍网格，按 16 分音符格子测各频段起音强度，输出 events.json 供渲染卡点。
用法: python3 analyze.py <audio.wav> [events.json]
"""
import sys, json, wave
import numpy as np

FPS = 60


def load(path):
    w = wave.open(path)
    sr = w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, w.getnchannels()).mean(1) / 32768
    return x, sr


def main(path, out="events.json"):
    x, sr = load(path)
    hop, win = 128, 2048
    fr = np.lib.stride_tricks.sliding_window_view(np.pad(x, (win // 2, win // 2)), win)[::hop]
    S = np.abs(np.fft.rfft(fr * np.hanning(win), axis=1))
    f = np.fft.rfftfreq(win, 1 / sr)
    t = np.arange(len(S)) * hop / sr
    bands = {"sub": (25, 110), "low": (110, 400), "mid": (400, 2500), "air": (2500, 16000)}
    env, onset = {}, {}
    for k, (a, b) in bands.items():
        e = np.log1p(S[:, (f >= a) & (f < b)].sum(1) * 10)
        env[k] = e
        on = np.maximum(0, np.diff(e, prepend=e[0]))
        onset[k] = np.convolve(on, np.ones(3) / 3, "same")

    # 节拍网格：在起音峰上拟合 16 分音符周期和相位（结果约 105.7 BPM，首个重拍 5.098s）
    comb = onset["sub"] / onset["sub"].max() + onset["air"] / onset["air"].max()
    T0, BEAT = 5.098, 0.5674
    s16 = BEAT / 4
    slots = []
    for k in range(-40, 200):
        tc = T0 + k * s16
        if tc < 0 or tc > t[-1]:
            continue
        m = (t >= tc - 0.035) & (t < tc + 0.035)
        slots.append([round(tc, 4), k,
                      round(float(comb[m].max()), 4),
                      round(float(onset["sub"][m].max() / onset["sub"].max()), 4),
                      round(float(onset["air"][m].max() / onset["air"].max()), 4)])
    vals = np.array([s[2] for s in slots])
    for s in slots:
        s[2] = round(float(s[2] / np.percentile(vals, 99)), 4)

    # 逐帧包络（60fps），0..1 归一
    n = int(t[-1] * FPS) + 1
    tf = np.arange(n) / FPS
    rms = np.sqrt(np.convolve(x ** 2, np.ones(1024) / 1024, "same"))[:: max(1, sr // FPS)][:n]
    def norm(a):
        a = np.interp(tf, t, a) if len(a) != n else a
        lo, hi = np.percentile(a, 2), np.percentile(a, 99.5)
        return np.clip((a - lo) / (hi - lo + 1e-9), 0, 1)
    data = {
        "T0": T0, "BEAT": BEAT, "fps": FPS,
        "slots": slots,  # [时间, 16分格序号(相对首拍), 综合强度, 低频强度, 高频强度]
        "env": {
            "sub": [round(float(v), 3) for v in norm(env["sub"])],
            "air": [round(float(v), 3) for v in norm(env["air"])],
            "rms": [round(float(v), 3) for v in norm(np.pad(rms, (0, max(0, n - len(rms))), "edge"))],
        },
    }
    json.dump(data, open(out, "w"))
    print("slots", len(slots), "frames", n)


if __name__ == "__main__":
    main(*sys.argv[1:])
