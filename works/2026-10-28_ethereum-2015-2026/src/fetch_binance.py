"""Download Binance public daily klines from the data.binance.vision S3 bucket.

Monthly zips cover finished months; daily zips fill in the current month.
Usage: python3 fetch_binance.py OUT_DIR SYMBOL [SYMBOL ...]
"""
import concurrent.futures as cf
import io
import os
import re
import sys
import time
import urllib.request
import zipfile

BASE = 'https://s3-ap-northeast-1.amazonaws.com/data.binance.vision'


def get(url):
    for k in range(6):
        try:
            return urllib.request.urlopen(url, timeout=60).read()
        except Exception as e:  # transient proxy/TLS hiccups
            print('retry', k, url[-70:], e, flush=True)
            time.sleep(2 ** k)
    raise RuntimeError(url)


def ls(prefix):
    keys, marker = [], ''
    while True:
        x = get(f'{BASE}?prefix={prefix}&marker={marker}').decode()
        ks = re.findall(r'<Key>([^<]+)</Key>', x)
        keys += ks
        if '<IsTruncated>true</IsTruncated>' not in x or not ks:
            break
        marker = ks[-1]
    return [k for k in keys if k.endswith('.zip')]


def rows_of(key):
    z = zipfile.ZipFile(io.BytesIO(get(f'{BASE}/{key}')))
    out = []
    for name in z.namelist():
        for line in z.read(name).decode().splitlines():
            p = line.split(',')
            if p[0].isdigit():
                out.append(p)
    return out


def main():
    out_dir = sys.argv[1]
    for sym in sys.argv[2:]:
        monthly = ls(f'data/spot/monthly/klines/{sym}/1d/')
        last_month = max(re.search(r'(\d{4}-\d{2})\.zip$', k).group(1) for k in monthly) if monthly else '0000-00'
        daily = [k for k in ls(f'data/spot/daily/klines/{sym}/1d/')
                 if re.search(r'(\d{4}-\d{2})-\d{2}\.zip$', k).group(1) > last_month]
        print(sym, 'monthly', len(monthly), 'last', last_month, 'extra daily', len(daily), flush=True)
        rows = {}
        with cf.ThreadPoolExecutor(8) as ex:
            for part in ex.map(rows_of, monthly + daily):
                for p in part:
                    ot = int(p[0])
                    if ot > 1e14:  # files from 2025 on use microseconds
                        ot //= 1000
                    rows[ot] = p
        with open(os.path.join(out_dir, f'{sym}_1d.csv'), 'w') as f:
            f.write('open_time_ms,open,high,low,close,volume,close_time,quote_volume,trades\n')
            for ot in sorted(rows):
                p = rows[ot]
                f.write(f'{ot},{p[1]},{p[2]},{p[3]},{p[4]},{p[5]},{p[6]},{p[7]},{p[8]}\n')
        print(sym, 'rows', len(rows), flush=True)


if __name__ == '__main__':
    main()
