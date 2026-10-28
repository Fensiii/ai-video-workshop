"""Build the daily close series used by the videos.

ETH: Coin Metrics PriceUSD (2015-08-08 .. its last day), then Binance ETH/USDT daily close.
SOL: Binance SOL/BUSD daily close (2020-04-10 .. 2020-08-10), then Binance SOL/USDT.
Binance closes are taken at 23:59:59 UTC, matching Coin Metrics' end-of-day reference rate.
"""
import csv
import datetime as dt
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, 'data')          # raw downloads (coinmetrics csv, binance/)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


def binance(name):
    out = {}
    for r in csv.DictReader(open(os.path.join(D, 'binance', name))):
        d = dt.datetime.fromtimestamp(int(r['open_time_ms']) / 1000, dt.timezone.utc).date()
        out[d] = float(r['close'])
    return out


def coinmetrics(name):
    out = {}
    for r in csv.DictReader(open(os.path.join(D, name))):
        if r.get('PriceUSD'):
            out[dt.date.fromisoformat(r['time'])] = float(r['PriceUSD'])
    return out


def write(name, parts):
    rows = {}
    for src, series, d0, d1 in parts:
        for d, p in series.items():
            if d0 <= d <= d1:
                rows[d] = (p, src)
    days = sorted(rows)
    assert all((days[i] - days[i - 1]).days == 1 for i in range(1, len(days))), 'gap in series'
    with open(os.path.join(OUT, name), 'w') as f:
        f.write('date,close,source\n')
        for d in days:
            f.write(f'{d.isoformat()},{rows[d][0]:.6f},{rows[d][1]}\n')
    print(name, days[0], days[-1], len(days))


if __name__ == '__main__':
    eth_cm = coinmetrics('eth_cm.csv')
    cm_end = max(eth_cm)
    write('eth.csv', [('coinmetrics', eth_cm, dt.date(2015, 8, 8), cm_end),
                      ('binance', binance('ETHUSDT_1d.csv'), cm_end + dt.timedelta(days=1), dt.date(2100, 1, 1))])
    write('sol.csv', [('binance_busd', binance('SOLBUSD_1d.csv'), dt.date(2020, 4, 10), dt.date(2020, 8, 10)),
                      ('binance_usdt', binance('SOLUSDT_1d.csv'), dt.date(2020, 8, 11), dt.date(2100, 1, 1))])
