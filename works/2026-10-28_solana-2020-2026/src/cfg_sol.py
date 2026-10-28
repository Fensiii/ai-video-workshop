"""Solana 2020-2026: data, story beats and on-screen copy (English)."""

NAME = 'Solana'
DATA_CSV = 'sol.csv'

T_END = 135.0            # head reaches the final data day

# HUD
HUD_LINE1 = 'SOLANA · SOL / USD'
HUD_LINE2 = 'Solana vs. US Dollar'

# kinds: genesis / peak / high / rally / crash / crisis / bottom / info / tech
# (t, date, kind, category, title, value, [desc lines], tag, short chart label)
# every value is checked against the price series by `python3 common.py`
EVENTS_RAW = [
    (8.5, '2020-04-10', 'genesis', 'LAUNCH', 'Trading Begins', '$0.95',
     ['Mainnet Beta launched March 16, 2020', 'CoinList auction price: $0.22'], 'MAINNET BETA', '2020 Launch'),
    (15.5, '2020-05-11', 'bottom', 'BOTTOM', 'All-Time Low', '−45.4%',
     ['2020.05.11 · $0.52', 'The lowest close on record'], '', '2020 Low'),
    (22.5, '2020-08-31', 'peak', 'PEAK', 'The First Rally', '$4.74',
     ['FTX’s Serum DEX goes live on Solana', '9× from the May low'], 'SERUM', 'Serum Rally'),
    (27.0, '2020-12-23', 'bottom', 'BOTTOM', 'Round Trip', '−74.7%',
     ['2020.12.23 · $1.20', 'Most of the rally erased'], '', '2020 Dip'),
    (35.0, '2021-05-19', 'crash', 'CRASH', 'The May 19 Crash', '−37.5%',
     ['China reiterates its crypto ban', 'From $55.98 to $34.99 in a day'], '', 'May 19'),
    (38.5, '2021-06-09', 'info', 'FUNDING', '$314M Token Sale', '',
     ['Led by a16z and Polychain Capital', 'Venture money bets big on Solana'], 'A16Z', 'a16z Raise'),
    (45.5, '2021-09-14', 'crisis', 'OUTAGE', '17-Hour Outage', '',
     ['Bot spam during a token sale halts the chain', 'Validators coordinate a restart'], 'DOWNTIME', 'Outage'),
    (51.5, '2021-11-06', 'peak', 'PEAK', 'Bull Market Peak', '$258.44',
     ['500× from the 2020 low', 'Market cap near $78 billion'], '', '2021 Peak'),
    (56.5, '2022-02-02', 'crisis', 'HACK', 'Wormhole Hack', '',
     ['120,000 wETH stolen from the bridge', 'Jump Crypto covers the ~$320M loss'], 'WORMHOLE', 'Wormhole'),
    (60.0, '2022-05-11', 'crash', 'CRASH', 'Terra Collapses', '−40.8%',
     ['UST breaks its peg, LUNA goes to zero', 'SOL −40.8% in four days'], 'LUNA', 'LUNA'),
    (65.0, '2022-11-09', 'crash', 'CRASH', 'FTX Collapses', '−52.5%',
     ['SBF’s empire was Solana’s biggest backer', 'Worst day ever: −42.2% on Nov 9'], 'FTX', 'FTX'),
    (68.5, '2022-12-29', 'bottom', 'BOTTOM', 'Rock Bottom', '−96.3%',
     ['2022.12.29 · $9.64', 'From $258 to under $10'], '', '2022 Low'),
    (71.5, '2023-01-14', 'rally', 'RALLY', 'The BONK Rebound', '+151.5%',
     ['A dog-coin airdrop revives the ecosystem', '+151% in 16 days'], 'BONK', 'BONK'),
    (75.5, '2023-06-10', 'crisis', 'REGULATION', 'SEC: “A Security”', '−28.5%',
     ['SEC lawsuits list SOL as a security', 'Robinhood delists SOL'], 'SEC', 'SEC Suits'),
    (80.5, '2023-12-25', 'rally', 'RALLY', 'The Comeback', '+1,154%',
     ['Jito airdrop and a DeFi revival', '12.5× from the FTX-crash low'], 'JITO', 'Comeback'),
    (84.5, '2024-03-17', 'tech', 'MEMECOINS', 'Memecoin Mania', '',
     ['pump.fun, BOME and WIF frenzy', 'First close above $200 since 2021'], 'PUMP.FUN', 'Memecoins'),
    (88.0, '2024-06-27', 'info', 'ETF', 'First SOL ETF Filing', '+9.4%',
     ['VanEck files for a spot Solana ETF', 'SOL jumps 9.4% on the day'], 'VANECK', 'ETF Filing'),
    (92.0, '2024-11-06', 'rally', 'RALLY', 'US Election', '+12.0%',
     ['Markets bet on crypto-friendly policy', 'Up 54% by November 22'], 'ELECTION', 'Election'),
    (96.0, '2025-01-18', 'peak', 'NEW HIGH', 'TRUMP Memecoin', '$261.97',
     ['Trump launches a memecoin on Solana', 'Record close: +19.3% in a day'], '$TRUMP', '2025 ATH'),
    (99.5, '2025-03-02', 'rally', 'POLICY', 'US Crypto Reserve', '+24.4%',
     ['Trump names SOL for a strategic reserve', 'Next day: −20.5%'], 'USA', 'Reserve'),
    (102.5, '2025-04-08', 'bottom', 'BOTTOM', 'Tariff Shock', '−59.8%',
     ['“Liberation Day” tariffs hit risk assets', '2025.04.08 · $105.40'], 'TARIFFS', 'Tariffs'),
    (106.0, '2025-07-02', 'info', 'ETF', 'First Staking ETF', '',
     ['REX-Osprey SSK debuts in the US', 'SOL and staking rewards in one ticker'], 'SSK', 'SSK ETF'),
    (109.5, '2025-09-08', 'info', 'TREASURY', 'Corporate Treasuries', '',
     ['Forward Industries raises $1.65B to buy SOL', 'Validators back the Alpenglow upgrade'], 'FORWARD', 'Treasuries'),
    (112.5, '2025-10-10', 'crash', 'CRASH', 'Record Liquidations', '−14.7%',
     ['Trump threatens 100% tariffs on China', '$19B+ of leveraged bets wiped out'], '', '10/10'),
    (115.5, '2025-10-28', 'info', 'ETF', 'Spot SOL ETFs Launch', '',
     ['Bitwise’s BSOL debuts on the NYSE', '$55M traded on day one'], 'BSOL', 'BSOL'),
    (120.0, '2026-02-05', 'crash', 'CRASH', 'Panic Sell-Off', '−14.9%',
     ['Bitcoin closes at $63,495', 'SOL closes at $78.35'], '', 'Feb Crash'),
    (124.5, '2026-06-06', 'bottom', 'BOTTOM', 'Bear Market Low', '−76.3%',
     ['Lowest close since December 2023', '2026.06.06 · $62.20'], '', '2026 Low'),
    (128.5, '2026-08-19', 'rally', 'RALLY', 'White House Summit', '+10.8%',
     ['Trump urges Congress to pass the CLARITY Act', 'SOL +24% in five days'], 'CLARITY ACT', 'WH Summit'),
    (132.5, '2026-10-21', 'tech', 'UPGRADE', 'Alpenglow Goes Live', '',
     ['New consensus replaces TowerBFT', 'Target finality: ~150 ms (from ~12.8 s)'], 'ALPENGLOW', 'Alpenglow'),
]

BLACK_SWANS = {'2021-05-19', '2022-05-11', '2022-11-09', '2025-10-10', '2026-02-05'}
SHAKE = {
    '2021-05-19': 20, '2021-09-14': 10, '2022-02-02': 10, '2022-05-11': 16, '2022-11-09': 26,
    '2022-12-29': 8, '2023-06-10': 12, '2025-04-08': 10, '2025-10-10': 18, '2026-02-05': 18,
    '2026-06-06': 8,
}
BRACKETS = {
    '2020-05-11': ('2020-04-10', '2020-05-11'),
    '2020-12-23': ('2020-08-31', '2020-12-23'),
    '2021-05-19': ('2021-05-18', '2021-05-19'),
    '2022-05-11': ('2022-05-08', '2022-05-12'),
    '2022-11-09': ('2022-11-07', '2022-11-09'),
    '2022-12-29': ('2021-11-06', '2022-12-29'),
    '2023-01-14': ('2022-12-29', '2023-01-14'),
    '2023-06-10': ('2023-06-04', '2023-06-10'),
    '2023-12-25': ('2022-12-29', '2023-12-25'),
    '2024-06-27': ('2024-06-26', '2024-06-27'),
    '2024-11-06': ('2024-11-05', '2024-11-06'),
    '2025-03-02': ('2025-03-01', '2025-03-02'),
    '2025-04-08': ('2025-01-18', '2025-04-08'),
    '2025-10-10': ('2025-10-09', '2025-10-10'),
    '2026-02-05': ('2026-02-04', '2026-02-05'),
    '2026-06-06': ('2025-01-18', '2026-06-06'),
    '2026-08-19': ('2026-08-18', '2026-08-19'),
}

MILESTONES = [(1, 19.0), (10, 31.0), (100, 42.0), (200, 48.5)]

ERAS = [
    ('2020-04-10', '2020', 'Born in a Crash'),
    ('2021-01-01', '2021', 'Solana Summer'),
    ('2022-01-01', '2022', 'The Fall'),
    ('2023-01-01', '2023', 'Back from the Dead'),
    ('2024-01-01', '2024', 'Memecoin Season'),
    ('2025-01-01', '2025', 'The ETF Era'),
    ('2026-01-01', '2026', 'Winter Returns'),
]

MM_RANGE = (0.4, 330.0)
MM_YEARS = [2021, 2022, 2023, 2024, 2025, 2026]

INTRO_KICKER = 'SOLANA  ·  2020 — 2026'
INTRO_TITLE = 'SOLANA'
INTRO_SUB = 'A 96% crash — and a full comeback'
INTRO_START = ('It all began at', '$0.95')
GLINT_DATES = ['2020-05-11', '2020-08-31', '2020-12-23', '2021-11-06', '2022-12-29', '2025-01-18', '2026-06-06']

END_QUESTIONS = ['Another comeback', 'Or a longer winter']
OV_LABELS = [
    ('2020-04-10', '2020 Launch', 'gold', True),
    ('2020-08-31', '2020 Serum Rally', 'gold', True),
    ('2020-12-23', '2020 −75%', 'down', False),
    ('2021-11-06', '2021 Peak', 'gold', True),
    ('2022-12-29', '2022 FTX Low −96%', 'down', False),
    ('2024-03-17', '2024 Memecoins', 'purple', True),
    ('2025-01-18', '2025 ATH', 'gold', True),
    ('2026-06-06', '2026 Low −76%', 'down', False),
]
END_SUMMARY_MULT = '≈ 107×'
END_SLOGAN = 'Left for dead. Never gone.'
END_SOURCE = ('Data: Binance SOL/BUSD (2020) and SOL/USDT daily closes (UTC)'
              '   |   Historical review only — not financial advice')
