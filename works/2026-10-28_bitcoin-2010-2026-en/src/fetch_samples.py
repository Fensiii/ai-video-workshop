"""Download the instrument samples used by music.py into ../samples/ (about 600 MB, git-ignored).

Sources (both reachable through raw.githubusercontent.com from the cloud container):
  * VS Chamber Orchestra Community Edition (sgossner/VSCO-2-CE, SFZ branch) - CC0
  * Salamander Grand Piano V3 by Alexander Holm (sfzinstruments/SalamanderGrandPiano) - CC BY 3.0
"""
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(ROOT, 'samples')
MANIFEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'samples_manifest.tsv')


def fetch(line):
    url, rel = line.rstrip('\n').split('\t')
    out = os.path.join(DEST, rel)
    if os.path.exists(out) and os.path.getsize(out) > 4096:
        return 0
    os.makedirs(os.path.dirname(out), exist_ok=True)
    subprocess.run(['curl', '-sS', '--retry', '3', '-o', out, url], check=True)
    return 1


if __name__ == '__main__':
    lines = [ln for ln in open(MANIFEST) if ln.strip()]
    with ThreadPoolExecutor(12) as ex:
        n = sum(ex.map(fetch, lines))
    print(f'{n} downloaded, {len(lines)} in manifest')
