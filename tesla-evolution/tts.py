"""Synthesize narration per subtitle line and write build/narration.wav + build/timeline.json."""
import json, os, sys
import numpy as np, soundfile as sf, sherpa_onnx

MODEL_DIR = sys.argv[1] if len(sys.argv) > 1 else "models/vits-melo-tts-zh_en"
LINE_GAP, SCENE_GAP, HEAD, TAIL = 0.35, 0.9, 1.2, 2.5

d = MODEL_DIR.rstrip("/") + "/"
tts = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(
    model=sherpa_onnx.OfflineTtsModelConfig(
        vits=sherpa_onnx.OfflineTtsVitsModelConfig(
            model=d + "model.onnx", lexicon=d + "lexicon.txt",
            tokens=d + "tokens.txt", dict_dir=d + "dict"),
        num_threads=8),
    rule_fsts=",".join(d + f for f in ("date.fst", "phone.fst", "number.fst"))))

script = json.load(open("script.json", encoding="utf-8"))
sr = tts.sample_rate
chunks, t = [np.zeros(int(HEAD * sr), np.float32)], HEAD
timeline = []
for si, scene in enumerate(script["scenes"]):
    start, lines = t, []
    for li, line in enumerate(scene["lines"]):
        audio = np.asarray(tts.generate(line[-1], sid=0, speed=0.88).samples, np.float32)
        dur = len(audio) / sr
        lines.append({"text": line[0], "start": round(t, 3), "end": round(t + dur, 3)})
        chunks += [audio, np.zeros(int(LINE_GAP * sr), np.float32)]
        t += dur + LINE_GAP
        print(f"{scene['id']}[{li}] {dur:.1f}s", flush=True)
    gap = SCENE_GAP if si < len(script["scenes"]) - 1 else TAIL
    chunks.append(np.zeros(int(gap * sr), np.float32))
    t += gap
    timeline.append({**{k: v for k, v in scene.items() if k != "lines"},
                     "start": round(start, 3), "end": round(t, 3), "lines": lines})

os.makedirs("build", exist_ok=True)
sf.write("build/narration.wav", np.concatenate(chunks), sr)
json.dump({"duration": round(t, 3), "scenes": timeline},
          open("build/timeline.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("total", round(t, 1), "s")
