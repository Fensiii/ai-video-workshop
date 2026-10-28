"""Build data/nvda_daily.csv (date, close) -- split-adjusted daily closes of NVDA.

Sources, first one that works wins:
  python3 fetch_data.py                 # Yahoo Finance chart API, then Stooq
  python3 fetch_data.py path/to/file    # a CSV downloaded by hand (Yahoo or Stooq format)

Yahoo's "close" is split-adjusted but not dividend-adjusted, which is how
NVDA prices are normally quoted.
"""
import csv
import datetime as dt
import io
import json
import os
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'nvda_daily.csv')
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'}


def _get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode('utf-8')


def from_yahoo():
    p2 = int(time.time()) + 86400
    url = ('https://query1.finance.yahoo.com/v8/finance/chart/NVDA'
           f'?period1=915148800&period2={p2}&interval=1d&events=split')
    js = json.loads(_get(url))['chart']['result'][0]
    ts = js['timestamp']
    closes = js['indicators']['quote'][0]['close']
    rows = []
    for t, c in zip(ts, closes):
        if c is None:
            continue
        d = (dt.datetime.fromtimestamp(t, dt.timezone.utc) - dt.timedelta(hours=5)).date()
        rows.append((d, c))
    return rows, 'Yahoo Finance'


def from_stooq():
    txt = _get('https://stooq.com/q/d/l/?s=nvda.us&i=d')
    return parse_csv(txt), 'Stooq'


def parse_csv(txt):
    rd = csv.DictReader(io.StringIO(txt))
    keys = {k.lower().strip(): k for k in rd.fieldnames}
    kd = keys.get('date')
    kc = keys.get('close')
    rows = []
    for r in rd:
        v = r[kc].strip().replace(',', '').replace('$', '')
        if not v or v.lower() == 'null':
            continue
        ds = r[kd].strip()
        try:
            d = dt.date.fromisoformat(ds[:10])
        except ValueError:
            d = dt.datetime.strptime(ds, '%m/%d/%Y').date()
        rows.append((d, float(v)))
    return rows


def main():
    if len(sys.argv) > 1:
        rows, src = parse_csv(open(sys.argv[1]).read()), os.path.basename(sys.argv[1])
    else:
        rows, src = None, None
        for fn in (from_yahoo, from_stooq):
            try:
                rows, src = fn()
                break
            except Exception as e:  # noqa: BLE001 - try the next source
                print(fn.__name__, 'failed:', e)
        if rows is None:
            sys.exit('no data source reachable')
    rows = sorted(dict(rows).items())
    rows = [(d, c) for d, c in rows if d >= dt.date(1999, 1, 22)]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['date', 'close'])
        for d, c in rows:
            w.writerow([d.isoformat(), f'{c:.6f}'])
    print(f'{src}: {len(rows)} rows {rows[0][0]} .. {rows[-1][0]}  first {rows[0][1]:.4f} last {rows[-1][1]:.2f} -> {OUT}')


if __name__ == '__main__':
    main()
