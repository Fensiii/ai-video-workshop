"""Ethereum 2015-2026: data, story beats and on-screen copy (English)."""

NAME = 'Ethereum'
DATA_CSV = 'eth.csv'

T_END = 174.0            # head reaches the final data day

# HUD
HUD_LINE1 = 'ETHEREUM · ETH / USD'
HUD_LINE2 = 'Ether vs. US Dollar'

# kinds: genesis / peak / high / rally / crash / crisis / bottom / info / tech
# (t, date, kind, category, title, value, [desc lines], tag, short chart label)
# every value is checked against the price series by `python3 common.py`
EVENTS_RAW = [
    (8.5, '2015-08-08', 'genesis', 'LAUNCH', 'Trading Begins', '$1.20',
     ['Frontier mainnet went live on July 30, 2015', '2014 crowdsale price: about $0.31'], 'FRONTIER', '2015 Launch'),
    (16.0, '2015-10-21', 'bottom', 'BOTTOM', 'All-Time Low', '−77.7%',
     ['2015.10.21 · $0.42', 'The lowest close on record'], '', '2015 Low'),
    (24.0, '2016-06-17', 'crisis', 'HACK', 'The DAO Hack', '−45.7%',
     ['Attacker drains 3.6M ETH from The DAO', 'Two days: $20.73 → $11.26'], 'THE DAO', 'DAO Hack'),
    (27.5, '2016-07-20', 'tech', 'HARD FORK', 'The DAO Fork', '',
     ['Stolen funds moved to a refund contract', 'The old chain lives on as Ethereum Classic'], 'ETC SPLIT', 'DAO Fork'),
    (32.5, '2017-02-28', 'info', 'ADOPTION', 'Enterprise Alliance', '',
     ['JPMorgan, Microsoft, Intel and ~30 firms', 'launch the Enterprise Ethereum Alliance'], 'EEA', 'EEA'),
    (39.0, '2017-06-12', 'peak', 'PEAK', 'ICO Fever', '$389.19',
     ['Bancor’s ICO raises $153M in under 3 hours', 'Up 47× since New Year’s Day'], 'BANCOR', 'ICO Fever'),
    (43.0, '2017-09-04', 'crisis', 'CRISIS', 'China Bans ICOs', '−42.5%',
     ['Beijing outlaws token sales', 'ETH falls 42.5% in two weeks'], 'CHINA', 'ICO Ban'),
    (47.0, '2017-12-04', 'tech', 'CONGESTION', 'CryptoKitties', '',
     ['A cat-collecting game clogs the network', 'Over 10% of all Ethereum transactions'], 'NFT', 'CryptoKitties'),
    (52.0, '2018-01-13', 'peak', 'PEAK', 'ICO Bubble Peak', '$1,380.14',
     ['Up ~169× since January 2017', 'Next: a 94% crash'], '', '2018 Peak'),
    (57.5, '2018-12-15', 'bottom', 'BOTTOM', 'Capitulation', '−94.0%',
     ['2018.12.15 · $82.83', '11 months of decline'], '', '2018 Low'),
    (61.0, '2019-02-28', 'tech', 'UPGRADE', 'Constantinople', '',
     ['Block reward cut from 3 to 2 ETH', 'Delayed once over a security bug'], 'ISSUANCE', 'Constantinople'),
    (66.5, '2020-03-12', 'crash', 'CRASH', 'Black Thursday', '−43.2%',
     ['COVID panic: ETH’s worst day on record', 'MakerDAO vaults liquidated for $0 bids'], 'COVID-19', 'Black Thursday'),
    (70.5, '2020-06-15', 'tech', 'DEFI', 'DeFi Summer', '',
     ['Compound’s COMP token sparks yield farming', 'Uniswap, Aave and Maker take off'], 'COMPOUND', 'DeFi Summer'),
    (74.5, '2020-12-01', 'tech', 'UPGRADE', 'Beacon Chain', '',
     ['The proof-of-stake chain goes live', 'Stakers lock 32 ETH per validator'], 'STAKING', 'Beacon Chain'),
    (77.5, '2021-01-19', 'high', 'NEW HIGH', 'Record Broken', '$1,386.09',
     ['First close above the 2018 peak', 'Three years and six days later'], '', '2021 New High'),
    (80.0, '2021-02-08', 'info', 'WALL STREET', 'CME Ether Futures', '',
     ['Regulated ETH futures go live in Chicago', 'ETH closes at $1,743.54'], 'CME', 'CME Futures'),
    (82.5, '2021-03-11', 'tech', 'NFT', 'Beeple’s $69M NFT', '',
     ['Christie’s sells a digital artwork for $69.3M', 'NFT mania goes mainstream'], 'CHRISTIE’S', 'Beeple'),
    (91.0, '2021-05-19', 'crash', 'CRASH', 'The May 19 Crash', '−24.7%',
     ['China reiterates its crypto ban', '−57% from the May high by July 20'], '', 'May 19'),
    (95.0, '2021-08-05', 'tech', 'UPGRADE', 'London Upgrade', '',
     ['EIP-1559 burns part of every fee', 'ETH supply growth slows sharply'], 'EIP-1559', 'London'),
    (99.0, '2021-11-08', 'peak', 'PEAK', 'Bull Market Peak', '$4,811.16',
     ['Up 58× from the 2018 low', 'Next: a 79% crash'], '', '2021 Peak'),
    (104.0, '2022-05-09', 'crash', 'CRASH', 'Terra Collapses', '−22.3%',
     ['UST stablecoin loses its dollar peg', 'About $40B wiped out within days'], 'LUNA', 'LUNA'),
    (107.5, '2022-06-18', 'bottom', 'BOTTOM', 'Below $1,000', '−79.4%',
     ['Celsius freezes withdrawals, 3AC collapses', '2022.06.18 · $992.79'], 'CELSIUS', '2022 Low'),
    (111.5, '2022-09-15', 'tech', 'UPGRADE', 'The Merge', '',
     ['Ethereum switches to proof-of-stake', 'Energy use falls by ~99.95%'], 'PROOF OF STAKE', 'The Merge'),
    (115.0, '2022-11-09', 'crisis', 'CRISIS', 'FTX Collapses', '−17.9%',
     ['A top crypto exchange halts withdrawals', 'ETH sinks to $1,093'], 'FTX', 'FTX'),
    (120.0, '2023-04-12', 'tech', 'UPGRADE', 'Shapella', '',
     ['Staked ETH can finally be withdrawn', 'ETH back above $2,000 the next day'], 'WITHDRAWALS', 'Shapella'),
    (125.0, '2024-03-13', 'tech', 'UPGRADE', 'Dencun', '',
     ['“Blobs” slash layer-2 fees', 'ETH topped $4,000 two days earlier'], 'EIP-4844', 'Dencun'),
    (129.0, '2024-05-23', 'info', 'ETF', 'Spot ETH ETFs Approved', '',
     ['The SEC approves spot Ether ETF listings', 'Trading starts July 23, 2024'], 'SEC', 'ETF Approval'),
    (132.5, '2024-08-05', 'crash', 'CRASH', 'Yen Carry Unwind', '−24.0%',
     ['Japan’s market crash spills into crypto', 'ETH −24% in four days'], 'JAPAN', 'Yen Unwind'),
    (137.0, '2025-02-21', 'crisis', 'HACK', 'The Bybit Hack', '',
     ['~$1.5B in ETH stolen: the largest crypto hack', 'FBI blames North Korea’s Lazarus Group'], 'BYBIT', 'Bybit Hack'),
    (140.5, '2025-04-08', 'bottom', 'BOTTOM', 'Tariff Shock', '−63.2%',
     ['“Liberation Day” tariffs hit risk assets', 'Lowest close since March 2023'], 'TARIFFS', 'Tariffs'),
    (143.5, '2025-05-07', 'tech', 'UPGRADE', 'Pectra', '',
     ['Smart accounts (EIP-7702), bigger validators', 'ETH +20.9% the next day'], 'EIP-7702', 'Pectra'),
    (147.0, '2025-07-18', 'info', 'POLICY', 'GENIUS Act Signed', '',
     ['First US federal law for stablecoins', 'Public companies race to stockpile ETH'], 'STABLECOINS', 'GENIUS Act'),
    (150.5, '2025-08-22', 'peak', 'NEW HIGH', 'All-Time High', '$4,831.10',
     ['Powell signals rate cuts at Jackson Hole', 'First record close since Nov 2021'], '', '2025 ATH'),
    (154.5, '2025-10-10', 'crash', 'CRASH', 'Record Liquidations', '−11.5%',
     ['Trump threatens 100% tariffs on China', '$19B+ of leveraged bets wiped out'], '', '10/10'),
    (158.0, '2025-12-03', 'tech', 'UPGRADE', 'Fusaka', '',
     ['PeerDAS: nodes check data by sampling', 'Paves the way for more blob space'], 'PEERDAS', 'Fusaka'),
    (162.0, '2026-02-05', 'crash', 'CRASH', 'Panic Sell-Off', '−13.8%',
     ['Bitcoin closes at $63,495', 'ETH closes at $1,850'], '', 'Feb Crash'),
    (167.0, '2026-06-25', 'bottom', 'BOTTOM', 'Bear Market Low', '−67.5%',
     ['Billions pulled from spot ETH ETFs', '2026.06.25 · $1,567.84'], 'ETF OUTFLOWS', '2026 Low'),
    (171.0, '2026-08-19', 'rally', 'RALLY', 'White House Summit', '+17.5%',
     ['Trump urges Congress to pass the CLARITY Act', 'Biggest daily gain since May 2025'], 'CLARITY ACT', 'WH Summit'),
]

# black swans: strongest push-in, white flash
BLACK_SWANS = {'2016-06-17', '2020-03-12', '2021-05-19', '2022-11-09', '2025-10-10', '2026-02-05'}
SHAKE = {
    '2016-06-17': 18, '2017-09-04': 12, '2020-03-12': 26, '2021-05-19': 18, '2022-05-09': 14,
    '2022-06-18': 10, '2022-11-09': 16, '2024-08-05': 14, '2025-02-21': 10, '2025-04-08': 10,
    '2025-10-10': 18, '2026-02-05': 18, '2026-06-25': 8,
}
# measurement arrows: event date -> (from date, to date)
BRACKETS = {
    '2015-10-21': ('2015-08-13', '2015-10-21'),
    '2016-06-17': ('2016-06-16', '2016-06-18'),
    '2017-09-04': ('2017-09-01', '2017-09-14'),
    '2018-12-15': ('2018-01-13', '2018-12-15'),
    '2020-03-12': ('2020-03-11', '2020-03-12'),
    '2021-05-19': ('2021-05-18', '2021-05-19'),
    '2022-05-09': ('2022-05-08', '2022-05-12'),
    '2022-06-18': ('2021-11-08', '2022-06-18'),
    '2022-11-09': ('2022-11-08', '2022-11-09'),
    '2024-08-05': ('2024-08-01', '2024-08-05'),
    '2025-04-08': ('2024-12-16', '2025-04-08'),
    '2025-10-10': ('2025-10-09', '2025-10-10'),
    '2026-02-05': ('2026-02-04', '2026-02-05'),
    '2026-06-25': ('2025-08-22', '2026-06-25'),
    '2026-08-19': ('2026-08-18', '2026-08-19'),
}

# round-number "first close above" moments; each one is also a time anchor (t)
MILESTONES = [(10, 19.5), (100, 36.0), (1000, 49.5), (2000, 85.5), (4000, 88.5)]

ERAS = [  # (start date, label, title)
    ('2015-08-08', '2015 — 2016', 'Frontier Days'),
    ('2017-01-01', '2017 — 2018', 'ICO Mania'),
    ('2018-03-01', '2018 — 2019', 'Crypto Winter'),
    ('2020-04-01', '2020 — 2021', 'DeFi & NFT Boom'),
    ('2022-01-01', '2022 — 2023', 'Contagion'),
    ('2024-01-01', '2024 — 2025', 'Wall Street Arrives'),
    ('2025-09-01', '2025 — 2026', 'Boom & Bust'),
]

# minimap
MM_RANGE = (0.3, 7000.0)
MM_YEARS = [2016, 2018, 2020, 2022, 2024, 2026]

# intro
INTRO_KICKER = 'ETHEREUM  ·  2015 — 2026'
INTRO_TITLE = 'ETHEREUM'
INTRO_SUB = 'Eleven years of code, crashes and comebacks'
INTRO_START = ('It all began at', '$1.20')
GLINT_DATES = ['2015-10-21', '2016-06-16', '2018-01-13', '2018-12-15', '2020-03-12',
               '2021-11-08', '2022-06-18', '2025-08-22', '2026-06-25']

# ending
END_QUESTIONS = ['The bottom is in', 'Or another winter']
OV_LABELS = [  # (date, text, colour key, above)
    ('2015-08-08', '2015 Launch', 'gold', True),
    ('2015-10-21', '2015 Low $0.42', 'down', False),
    ('2016-06-16', '2016 DAO Hack', 'down', True),
    ('2018-01-13', '2018 ICO Peak', 'gold', True),
    ('2018-12-15', '2018 Low −94%', 'down', False),
    ('2020-03-12', '2020 COVID Crash', 'down', False),
    ('2021-11-08', '2021 Peak', 'gold', True),
    ('2022-06-18', '2022 Low −79%', 'down', False),
    ('2024-03-11', '2024 ETF Year', 'blue', True),
    ('2025-08-22', '2025 ATH', 'gold', True),
    ('2026-06-25', '2026 Low −68%', 'down', False),
]
END_SUMMARY_MULT = '≈ 1,959×'
END_SLOGAN = 'Every crash looked like the end.'
END_SOURCE = ('Data: Coin Metrics ETH/USD to 2026-05-23, then Binance ETH/USDT · daily closes (UTC)'
              '   |   Historical review only — not financial advice')
