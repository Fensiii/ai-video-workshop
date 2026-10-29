# Crypto price-history videos (English) — generator

One codebase renders both videos; pick the asset with `ASSET=eth` or `ASSET=sol`.
Derived from the Bitcoin 2010–2026 video (`works/2026-10-17_bitcoin-2010-2026/src/`).

| File | Role |
|---|---|
| `cfg_eth.py`, `cfg_sol.py` | Story and copy per asset: events, milestones, eras, HUD/intro/ending text, shake/zoom tuning |
| `common.py` | Data loading, time mapping (events + milestones are anchors), camera precompute; `python3 common.py` checks every on-screen number against the price series |
| `render.py` | skia frame renderer (English fonts, green-up / red-down palette) |
| `audio.py` | Synthesised sound effects (bells tuned to the score's key; no voice) |
| `music.py` | Original adaptive score at 120 BPM (every story beat is a multiple of 0.5 s, so hits land on beats): FluidR3 samples for piano/strings/choir/pad/pizzicato/horn/celesta/timpani/taiko, synthesised drums, bass and arp; rallies drive, sell-offs go minor, black swans cut the music, bottoms drop to piano, new highs get a lift + choir |
| `mix.py` | Score at −16.5 LUFS ducked under the effects at −18 LUFS, limiter, master at −14 LUFS |
| `fetch_samples.py` | Downloads FluidR3_GM notes (MIDI.js soundfonts, CC BY 3.0) into `samples/*.npz` |
| `run_render.py` | 4-process chunked render → `out/<asset>/video_noaudio.mp4` |
| `finalize.py` | SFX + score + mix, then either copy an encoded picture (`--reuse-video`) or two-pass x264 under ~95 MB |
| `cover.py` | 1280×720 YouTube thumbnail |
| `youtube_meta.py` | Upload sheet: title, description with chapters, tags |
| `prepare_data.py` | Builds `data/eth.csv`, `data/sol.csv` from the raw downloads |
| `fetch_binance.py` | Downloads Binance daily klines from the public `data.binance.vision` S3 bucket |
| `data/` | The exact daily-close series used for the videos |

## Data

- ETH: Coin Metrics `PriceUSD` (github.com/coinmetrics/data, `csv/eth.csv`) from 2015-08-08 to 2026-05-23,
  then Binance ETH/USDT daily closes to 2026-10-27.
- SOL: Binance SOL/BUSD daily closes 2020-04-10 … 2020-08-10, then SOL/USDT to 2026-10-27
  (Coin Metrics has no SOL price column).
- Overlap checks: Coin Metrics vs Binance ETH median difference ≈ 0.0% (2023–2026 max 1.9%);
  SOL/BUSD vs SOL/USDT median −0.01%.

## Run

```bash
# python: numpy scipy skia-python pillow pyloudnorm; ffmpeg on PATH
# fonts: Inter + Playfair Display TTFs from npm (@expo-google-fonts/inter, @expo-google-fonts/playfair-display) into ../fonts/
# skia-python needs libEGL.so.1; on hosts without it, build the 3-symbol stub:
#   gcc -shared -fPIC -o libEGL.so.1 egl_stub.c   (see egl_stub.c) and add its folder to LD_LIBRARY_PATH
ASSET=eth python3 common.py                     # number check
ASSET=eth python3 render.py 24.7 99.6           # stills → out/eth/test_frames/
ASSET=eth python3 run_render.py 16              # full render (~12 min on 4 cores)
python3 -I fetch_samples.py ../samples acoustic_grand_piano string_ensemble_1 choir_aahs pad_2_warm timpani \
    pizzicato_strings french_horn taiko_drum celesta   # ~700 MB of decoded notes, not committed
ASSET=eth python3 finalize.py ethereum_2015-2026_16x9.mp4
ASSET=eth python3 cover.py cover.jpg
ASSET=eth python3 youtube_meta.py youtube.md
```

## Music

`music.py` writes an original score for each video (D minor for Ethereum, E minor for Solana).
Checks used instead of listening: sample pitch per MIDI note (FFT), per-bar chroma against the planned
chord (ETH 92/93 bars, SOL 75/75), strong onsets on the 16th-note grid (86–91 %), level inside the
black-swan cuts. Credit for YouTube: instrument samples from the FluidR3_GM SoundFont (CC BY 3.0).
