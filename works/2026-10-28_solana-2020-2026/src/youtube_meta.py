"""YouTube upload sheet (title, description with chapters, tags) generated from the same timeline.

ASSET=eth python3 youtube_meta.py OUT.md
"""
import sys

import common as B

META = {
    'eth': dict(
        title='Ethereum Price History 2015–2026 | 11 Years in 3 Minutes (Every Crash & Record)',
        hook=('From $1.20 in August 2015 to a $4,831 record close in 2025, Ethereum lived through '
              'The DAO hack, a 94% crypto winter, Black Thursday and the FTX collapse, and rebuilt itself '
              'with The Merge. Every key moment of ETH’s first eleven years, animated on its real daily '
              'closing price.'),
        tags=['ethereum', 'eth', 'ethereum price history', 'ethereum price', 'eth price', 'ether',
              'crypto', 'cryptocurrency', 'crypto history', 'ethereum chart', 'the merge', 'defi',
              'nft', 'ico', 'crypto crash', 'bull market', 'bear market', 'spot ethereum etf',
              'data visualization', 'price animation'],
        hashtags='#Ethereum #ETH #Crypto',
    ),
    'sol': dict(
        title='Solana Price History 2020–2026 | The −96% Comeback in 2.5 Minutes',
        hook=('Solana launched in the middle of the COVID crash, ran 500× to $258, then crashed 96% '
              'through the 2022 bear market and the FTX collapse, and came back to a record close in 2025. '
              'Every key moment of SOL’s first six years, animated on its real daily closing price.'),
        tags=['solana', 'sol', 'solana price history', 'solana price', 'sol price', 'crypto',
              'cryptocurrency', 'crypto history', 'solana chart', 'ftx collapse', 'memecoins',
              'bonk', 'trump coin', 'solana etf', 'alpenglow', 'crypto crash', 'bull market',
              'bear market', 'data visualization', 'price animation'],
        hashtags='#Solana #SOL #Crypto',
    ),
}


def ts(t):
    t = int(t)
    return f'{t // 60}:{t % 60:02d}'


def main():
    m = META[B.ASSET]
    chapters = [(0.0, 'Intro')]
    for t, label, title in B.ERA_T:
        chapters.append((t, f'{label.replace(" — ", "–")} {title}'))
    chapters.append((B.T_END, 'The big picture'))
    p0, p1 = B.PRICE[0], B.PRICE[-1]
    src = B.CFG.END_SOURCE.split('|')[0].strip()
    lines = [
        f'# YouTube upload sheet — {B.CFG.NAME}',
        '',
        f'- File: 1920×1080, {B.FPS} fps, {ts(B.DURATION)} long, sound effects only (no music, no voice-over)',
        f'- Data: {B.DATES[0]} → {B.DATES[-1]}, ${p0:,.2f} → ${p1:,.2f}',
        '- Thumbnail: `cover.jpg` (1280×720)',
        '',
        '## Title',
        '',
        m['title'],
        '',
        '## Description',
        '',
        m['hook'],
        '',
        'Chapters',
    ]
    lines += [f'{ts(t)} {name}' for t, name in chapters]
    lines += [
        '',
        f'{src}.',
        'Prices are daily closes in UTC; intraday highs and lows were higher or lower.',
        'This video is a historical review only and is not financial advice.',
        '',
        m['hashtags'],
        '',
        '## Tags',
        '',
        ', '.join(m['tags']),
        '',
    ]
    open(sys.argv[1], 'w').write('\n'.join(lines))
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
