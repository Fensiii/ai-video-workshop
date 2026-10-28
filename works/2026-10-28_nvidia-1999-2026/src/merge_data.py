"""Build data/nvda_daily.csv from two public Yahoo Finance mirrors on GitHub.

The cloud session cannot reach Yahoo/Stooq directly, so the series is stitched from:
  1999-01-22 .. 2024-06-18  github.com/debjit-mandal/NVIDIA-Stock-Analysis  data/NVDA.csv  ("Close", 6 decimals)
  2024-06-19 .. latest      github.com/yennanliu/finance_data  data/prices/nvda.csv  ("close", refreshed nightly)
Both are split-adjusted (six splits, 480:1 in total) and not dividend-adjusted.
Over their 1,922-day overlap (2016-10-27 .. 2024-06-18) they agree to within $0.005.

    python3 merge_data.py OLD.csv NEW.csv
"""
import csv
import datetime as dt
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'nvda_daily.csv')


def load(fn, col):
    out = {}
    for r in csv.DictReader(open(fn)):
        v = r[col]
        if v and v != 'null':
            out[dt.date.fromisoformat((r.get('Date') or r.get('date'))[:10])] = float(v)
    return out


def main(old_fn, new_fn):
    old = load(old_fn, 'Close')
    new = load(new_fn, 'close')
    common = sorted(set(old) & set(new))
    worst = max(abs(old[d] - new[d]) for d in common)
    assert worst < 0.0051, f'sources disagree by {worst}'
    cut = max(old)
    rows = sorted(old.items()) + sorted((d, c) for d, c in new.items() if d > cut)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['date', 'close'])
        for d, c in rows:
            w.writerow([d.isoformat(), f'{c:.6f}'.rstrip('0').rstrip('.')])
    print(f'{len(rows)} rows {rows[0][0]} .. {rows[-1][0]}  overlap {len(common)} days, max diff {worst:.4f} -> {OUT}')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
