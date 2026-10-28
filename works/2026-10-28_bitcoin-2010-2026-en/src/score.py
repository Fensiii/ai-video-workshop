"""The score: tempo grid, chords, energy curve and theme statements, all keyed to the video timeline.

120 BPM puts every event on a beat (events sit on multiples of 0.5 s); bars start at 0.5 s so the
chart start (8.5 s) and several peaks (16.5, 80.5, 170.5) land on downbeats. Key: D minor, with a
Picardy D major on the last chord. The main theme climbs A-D-E-F (the bull run) and falls back.
"""
import numpy as np

import btc_common as B

BPM = 120
BEAT = 60.0 / BPM
BAR = 4 * BEAT
T0 = 0.5
DUR = B.NFRAMES / B.FPS


def tb(bar, beat=0.0):
    return T0 + bar * BAR + beat * BEAT


# ----------------------------------------------------------------------------
# harmony
# ----------------------------------------------------------------------------
_PC = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7,
       'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
_QUAL = {'': (0, 4, 7), 'm': (0, 3, 7), 'maj7': (0, 4, 7, 11), 'm9': (0, 3, 7, 14), 'add9': (0, 4, 7, 14),
         'sus2': (0, 2, 7), 'sus4': (0, 5, 7), 'm7': (0, 3, 7, 10)}


def parse_chord(name):
    """'Bb/D' -> (root pc, pitch classes, bass pc)"""
    body, _, bass = name.partition('/')
    root = body[:2] if len(body) > 1 and body[1] in '#b' else body[:1]
    q = body[len(root):]
    r = _PC[root]
    pcs = tuple(sorted({(r + i) % 12 for i in _QUAL[q]}))
    return r, pcs, _PC[bass] if bass else r


CHORDS = [  # (time, chord) - a chord lasts until the next entry
    # intro: title card, preview line, "It all started at $0.0858"
    (0.0, 'Dm9'), (tb(1), 'Bbmaj7'), (tb(2), 'Fadd9'), (tb(3), 'C'),
    # 2010-2012 The Geek Experiment
    (tb(4), 'Dm'), (tb(5), 'Bb'), (tb(6), 'F'), (tb(7), 'C'),
    (tb(8), 'F'), (tb(9), 'C'), (19.5, 'Gm'), (tb(10), 'Bb'), (tb(11), 'Asus4'), (tb(11, 1), 'A'),
    (23.5, 'Dm'), (tb(12), 'Dm9'), (tb(13), 'Bb'), (tb(14), 'Csus2'), (tb(14, 2), 'C'),
    # 2013-2015 The Wild West
    (tb(15), 'Dm'), (tb(16), 'Bb'), (tb(17), 'F'), (36.0, 'Gm'), (tb(19), 'A'),
    (tb(20), 'Dm'), (tb(21), 'Bb'), (tb(22), 'F'), (tb(23), 'C'),
    (tb(24), 'Bb'), (tb(25), 'Gm'), (tb(26), 'Dm'), (tb(27), 'A'), (55.5, 'Dm'),
    (tb(28), 'Bb'), (tb(29), 'Gm'), (59.5, 'F'), (tb(30), 'C'),
    # 2016-2018 ICO Mania
    (tb(31), 'Dm'), (tb(32), 'Bb'), (tb(33), 'Gm'), (tb(34), 'C'), (tb(35), 'F'), (tb(36), 'C'),
    (tb(37), 'Dm'), (75.0, 'Gm'), (tb(38), 'Bb'), (tb(39), 'C'),
    (tb(40), 'Dm'), (tb(41), 'Bb'), (tb(42), 'Gm'), (tb(42, 2), 'A'), (tb(43), 'Dm'),
    # 2019-2020 Pandemic & Halving
    (tb(44), 'Dm'), (tb(45), 'Bb'), (tb(46), 'Gm'), (tb(47), 'A'), (96.0, 'Dm'),
    (99.5, 'Bb'), (tb(50), 'F'), (tb(50, 2), 'C'),
    # 2020-2021 Institutions Arrive
    (tb(51), 'Dm'), (tb(52), 'Bb'), (tb(53), 'F'), (tb(54), 'C'),
    (tb(55), 'Dm'), (tb(56), 'Bb'), (tb(57), 'F'), (tb(58), 'C'), (118.0, 'Gm'), (tb(59, 2), 'A'),
    (tb(60), 'Dm'), (tb(61), 'Bb'), (tb(62), 'F'), (tb(63), 'C'),
    # 2022-2023 Crypto Winter
    (tb(64), 'Dm'), (tb(65), 'Bb'), (tb(66), 'Gm'), (tb(67), 'A'), (tb(68), 'Dm'),
    (tb(69), 'Bb'), (tb(70), 'Gm'), (tb(70, 3), 'C'),
    # 2023-2024 The ETF Era
    (tb(71), 'F'), (tb(72), 'C'), (tb(73), 'Dm'), (tb(74), 'Bb'),
    (tb(75), 'F'), (tb(76), 'C'), (tb(77), 'Dm'), (tb(78), 'Bb'), (tb(79), 'C'),
    # 2025-2026 Strategic Reserve
    (tb(80), 'Dm'), (tb(81), 'Bb'), (tb(82), 'F'), (tb(83), 'C'),
    (tb(84), 'Dm'), (tb(85), 'Bb'), (tb(86), 'F'), (173.5, 'Gm'), (tb(88), 'A'),
    # ending: questions, pull-out, summary, tagline
    (tb(89), 'Dm'), (tb(91), 'Bb'), (tb(92), 'Gm'), (tb(93), 'Asus4'), (tb(93, 2), 'A'),
    (tb(94), 'Bb'), (tb(94, 2), 'C'), (tb(95), 'D'),
]
CHORD_T = np.array([c[0] for c in CHORDS])


def chord_at(t):
    i = int(np.searchsorted(CHORD_T, t, side='right')) - 1
    return CHORDS[max(i, 0)][1]


def chord_segments():
    out = []
    for i, (t, name) in enumerate(CHORDS):
        t1 = CHORDS[i + 1][0] if i + 1 < len(CHORDS) else DUR
        out.append((t, t1, name))
    return out


def chord_tones_at(t, lo, hi):
    """all chord tones (midi) of the chord sounding at t, within [lo, hi]"""
    _, pcs, _ = parse_chord(chord_at(t))
    return [m for m in range(lo, hi + 1) if m % 12 in pcs]


# ----------------------------------------------------------------------------
# energy: drives the arrangement (which layers play, how hard). Crashes cut it instantly.
# ----------------------------------------------------------------------------
ENERGY = [
    (0.0, 0.12), (7.0, 0.22), (8.5, 0.34), (13.0, 0.42), (16.5, 0.62), (19.45, 0.56), (19.5, 0.26),
    (23.5, 0.16), (27.0, 0.3), (30.3, 0.5), (32.5, 0.58), (35.95, 0.64), (36.0, 0.36), (38.5, 0.52),
    (42.5, 0.74), (45.5, 0.96), (48.5, 0.76), (50.45, 0.66), (50.5, 0.28), (55.5, 0.14), (59.5, 0.34),
    (62.2, 0.48), (66.45, 0.56), (66.5, 0.46), (70.5, 0.7), (74.95, 0.78), (75.0, 0.5), (78.5, 0.84),
    (80.5, 1.0), (82.5, 0.92), (84.5, 0.5), (86.5, 0.2), (88.5, 0.36), (94.5, 0.56), (95.95, 0.62),
    (96.0, 0.08), (99.45, 0.14), (99.5, 0.34), (102.2, 0.56), (108.0, 0.72), (111.5, 0.8), (114.5, 0.86),
    (117.95, 0.86), (118.0, 0.5), (120.5, 0.76), (125.0, 1.0), (126.5, 0.86), (127.4, 0.62), (128.5, 0.3),
    (133.5, 0.22), (137.45, 0.24), (137.5, 0.1), (141.0, 0.18), (142.0, 0.34), (146.0, 0.5), (149.0, 0.66),
    (152.0, 0.68), (155.5, 0.8), (157.6, 0.92), (160.5, 0.86), (163.95, 0.86), (164.0, 0.6), (166.5, 0.82),
    (170.5, 1.0), (173.45, 0.95), (173.5, 0.32), (176.5, 0.24), (179.0, 0.16), (183.0, 0.22),
    (188.5, 0.86), (189.5, 0.92), (190.5, 0.8), (DUR, 0.55),
]
_ET = np.array([e[0] for e in ENERGY])
_EV = np.array([e[1] for e in ENERGY])


def energy(t):
    return float(np.interp(t, _ET, _EV))


# ----------------------------------------------------------------------------
# theme statements: (start time, instrument, [(beat offset, beats, midi, vel)])
# 'horn' lines are carried by the cello section with horns doubling (the horn samples skip C4-D5);
# violin lines stay at or below F6 (the highest violin sample is D6)
# ----------------------------------------------------------------------------
A4, Bb4, C5, Cs5, D5, E5, F5, Fs5, G5, A5 = 69, 70, 72, 73, 74, 76, 77, 78, 79, 81
THEME = [(0, 1, A4), (1, 2, D5), (3, 1, E5), (4, 3, F5), (7, 1, E5), (8, 2, D5), (10, 2, C5), (12, 4, E5)]


def phrase(notes, transpose=0, vel=0.7):
    return [(b, d, m + transpose, vel) for b, d, m in notes]


MELODY = [
    # intro, solo piano: the theme, quietly
    (tb(0), 'piano', phrase(THEME, 0, 0.42)),
    # geek years: music-box glockenspiel an octave up
    (tb(4), 'glock', phrase(THEME, 12, 0.5)),
    # 2013 peak: horns, the top note lands on 45.5
    (tb(20), 'horn', phrase([(0, 1, A4), (1, 2, D5), (3, 1, E5), (4, 3, F5), (7, 1, E5), (8, 2, F5), (10, 2, A5),
                             (12, 2, G5), (14, 2, E5)], -12, 0.78)),
    (tb(20), 'violin', phrase([(0, 1, A4), (1, 2, D5), (3, 1, E5), (4, 3, F5), (7, 1, E5), (8, 2, F5), (10, 2, A5),
                               (12, 4, G5)], 0, 0.7)),
    # 2017 peak: theme on violins + horns, then it breaks off
    (tb(40), 'horn', phrase([(0, 1, A4), (1, 2, D5), (3, 1, E5), (4, 4, F5)], -12, 0.9)),
    (tb(40), 'violin', phrase([(0, 1, A4), (1, 2, D5), (3, 1, E5), (4, 3, F5), (7, 1, E5), (8, 2, D5), (10, 1, Bb4),
                               (11, 1, A4)], 12, 0.85)),
    # winter: lonely piano
    (tb(64), 'piano', phrase([(0, 2, A4), (2, 2, F5), (4, 3, D5), (8, 2, Bb4), (10, 2, D5), (12, 4, Cs5)], 0, 0.4)),
    # 2020-2021: full theme, peak note on 125.0
    (tb(60), 'horn', phrase([(0, 1, A4), (1, 2, D5), (3, 1, E5), (4, 3, F5), (7, 1, E5), (8, 1, F5), (9, 3, A5),
                             (12, 2, G5), (14, 2, E5)], -12, 0.95)),
    (tb(60), 'violin', phrase([(0, 1, A4), (1, 2, D5), (3, 1, E5), (4, 3, F5), (7, 1, E5), (8, 1, F5), (9, 3, A5),
                               (12, 2, G5), (14, 2, E5)], 0, 0.9)),
    # ETF era: hope returns on the piano
    (tb(71), 'piano', phrase([(0, 1, C5), (1, 2, F5), (3, 1, G5), (4, 4, E5), (8, 1, D5), (9, 2, F5), (11, 1, A5),
                              (12, 4, F5)], 0, 0.5)),
    # 2025: the theme in horns, then the final climax on 170.5
    (tb(80), 'horn', phrase(THEME, -12, 0.85)),
    (tb(80), 'violin', phrase(THEME, 0, 0.75)),
    (tb(84), 'violin', phrase([(0, 1, A4), (1, 2, D5), (3, 1, E5), (4, 4, F5), (8, 2, A5)], 0, 0.95)),
    (tb(84), 'horn', phrase([(0, 1, A4), (1, 2, D5), (3, 1, E5), (4, 4, F5), (8, 2, A5)], -12, 1.0)),
    # questions: two piano notes hanging in the air
    (tb(89), 'piano', phrase([(1, 3, A4), (5, 3, E5)], 0, 0.36)),
    # ending: the theme turns major (F -> F#) as the tagline appears
    (tb(94), 'piano', phrase([(0, 1, D5), (1, 1, F5), (2, 2, E5), (4, 7, Fs5)], 0, 0.55)),
    (tb(94), 'violin', phrase([(0, 1, D5), (1, 1, F5), (2, 2, E5), (4, 7, Fs5)], 0, 0.62)),
]

# ----------------------------------------------------------------------------
# accents taken from the video's events
# ----------------------------------------------------------------------------


def accents():
    """(time, kind, strength): kind in peak / crash / swan / bottom / tech / adopt / milestone / era"""
    out = []
    for ev in B.EVENTS:
        if ev.cat == '开端':
            continue
        if ev.date in B.BLACK_SWANS:
            kind = 'swan'
        elif ev.cat in ('顶点', '新高', '暴涨', '大选'):
            kind = 'peak'
        elif ev.cat in ('危机', '暴跌'):
            kind = 'crash'
        elif ev.cat == '谷底':
            kind = 'bottom'
        elif ev.cat in ('减半', '科技', '上线'):
            kind = 'tech'
        else:
            kind = 'adopt'
        out.append((ev.t, kind, 1.0 if ev.cat == '顶点' or kind == 'swan' else 0.75))
    for lv, fd, tm in B.MILESTONE_T:
        out.append((float(tm), 'milestone', 0.8))
    for te, label, title in B.ERA_T[1:]:
        out.append((float(te), 'era', 0.7))
    return sorted(out)


# swells (cymbal roll + timpani roll) that crest exactly on these moments
SWELLS = [16.5, 45.5, 80.5, 125.0, float(B.MILESTONE_T[-1][2]), 170.5, 189.5]
