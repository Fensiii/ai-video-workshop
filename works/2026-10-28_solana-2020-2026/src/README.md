# Crypto price-history videos (English) — generator

One codebase renders both videos; pick the asset with `ASSET=eth` or `ASSET=sol`.
Derived from the Bitcoin 2010–2026 video (`works/2026-10-17_bitcoin-2010-2026/src/`).

| File | Role |
|---|---|
| `cfg_eth.py`, `cfg_sol.py` | Story and copy per asset: events, milestones, eras, HUD/intro/ending text, shake/zoom tuning |
| `common.py` | Data loading, time mapping (events + milestones are anchors), camera precompute; `python3 common.py` checks every on-screen number against the price series |
| `render.py` | skia frame renderer (English fonts, green-up / red-down palette) |
| `audio.py` | Synthesised sound effects only (no music, no voice) |
| `run_render.py` | 4-process chunked render → `out/<asset>/video_noaudio.mp4` |
| `finalize.py` | SFX → −14 LUFS check → two-pass x264 under ~95 MB with AAC audio |
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
# fonts: Inter + Playfair Display TTFs from npm (@expo-google-fonts/inter, @expo-google-fonts/playfair-display) into ../fonts/
# skia-python needs libEGL.so.1; on hosts without it, build the 3-symbol stub:
#   gcc -shared -fPIC -o libEGL.so.1 egl_stub.c   (see egl_stub.c) and add its folder to LD_LIBRARY_PATH
ASSET=eth python3 common.py                     # number check
ASSET=eth python3 render.py 24.7 99.6           # stills → out/eth/test_frames/
ASSET=eth python3 run_render.py 16              # full render (~12 min on 4 cores)
ASSET=eth python3 finalize.py ethereum_2015-2026_16x9.mp4
ASSET=eth python3 cover.py cover.jpg
ASSET=eth python3 youtube_meta.py youtube.md
```
