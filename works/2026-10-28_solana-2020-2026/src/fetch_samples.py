"""Download FluidR3_GM instrument notes (MIDI.js pre-rendered, CC BY 3.0) and decode them to numpy.

python3 -I fetch_samples.py OUT_DIR instrument [instrument ...]
Writes OUT_DIR/<instrument>.npz with one float32 stereo array per MIDI note number (48 kHz).
"""
import base64
import io
import os
import re
import subprocess
import sys
import urllib.request

import numpy as np

URL = 'https://raw.githubusercontent.com/gleitz/midi-js-soundfonts/gh-pages/FluidR3_GM/{}-mp3.js'
NOTE_RE = re.compile(r'"([A-G]b?)(-?\d)"\s*:\s*"data:audio/mp3;base64,([A-Za-z0-9+/=]+)"')
PC = {'C': 0, 'Db': 1, 'D': 2, 'Eb': 3, 'E': 4, 'F': 5, 'Gb': 6, 'G': 7, 'Ab': 8, 'A': 9, 'Bb': 10, 'B': 11}
SR = 48000


def decode_mp3(data):
    p = subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-f', 'mp3', '-i', 'pipe:0',
                        '-ac', '2', '-ar', str(SR), '-f', 'f32le', 'pipe:1'],
                       input=data, capture_output=True, check=True)
    return np.frombuffer(p.stdout, np.float32).reshape(-1, 2).copy()


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for ins in sys.argv[2:]:
        path = os.path.join(out, f'{ins}.npz')
        if os.path.exists(path):
            print('have', ins)
            continue
        js = urllib.request.urlopen(URL.format(ins), timeout=120).read().decode()
        notes = {}
        for name, octave, b64 in NOTE_RE.findall(js):
            midi = 12 * (int(octave) + 1) + PC[name]
            notes[f'n{midi}'] = decode_mp3(base64.b64decode(b64))
        lens = [v.shape[0] / SR for v in notes.values()]
        np.savez_compressed(path, **notes)
        print(ins, len(notes), 'notes', f'{min(lens):.2f}-{max(lens):.2f}s', flush=True)


if __name__ == '__main__':
    main()
