# Weekly 9-MA cross after a flush + breadth (MMFI) bottom — research (3 Nov 2026)

User idea: for growth stocks/indices, enter when the weekly close crosses above the 9-week MA after QQQ/SPY flushed and MMFI (% of stocks above 50-day) made a local bottom. Tested (1) as bottom catching, (2) as a trading system. Scripts: /home/claude/wk9 (copied to signals-platform/research/weekly-9ma/).

## Data
- Barchart $MMFI blocked (403). Proxy: % of current S&P 1500 members above their 50-day (1,502 stocks, Yahoo, 1990+; survivorship bias: dead stocks missing). research-data branch: research-data/breadth/ (breadth.csv, closes.csv.gz). Proxy lows: Mar 2020 1.6, Jun 2022 4.9, Oct 2022 14, Apr 2025 3.8; mid-Oct 2026 ~19.
- Indices: ^NDX, ^GSPC, ^SOX (1991+); ETFs QQQ/SPY/SOXX for trading.

## Rules tested (defaults, then grid)
- Flush: QQQ (NDX) 10%+ or SPY 7.5%+ below 1y high at some point in the last 8 weeks.
- Breadth bottom: proxy daily low <= 25 in the last 6 weeks and now >= low + 10.
- Trigger: weekly close crosses above its 9-week SMA. Episodes: first signal per correction (NDX 10%, SPX 7.5%, SOX 15%).

## 1) Bottom catching (first signal per correction)
- It is a CONFIRMATION entry: median ~9% above the episode low (SOX ~21%); within 5% of the low ~0-10% of the time; 2/3 come after the low.
- NDX 2010-26: 14 signals / 19 corrections; further fall median -3.8%, worst -23% (2022); 6m +13.5% (all weeks 9.4%); up after 6m 93% (80%). 1991-2009 weaker: 6m +5.7% vs 7.6% base; worst further fall -42% (2001).
- SPX 2010-26: 6m +10.4% vs 6.4% base. SOX 2010-26: 6m +17% vs 13% base (7 signals).
- Breadth filter adds ~nothing for NDX/SPX since 2010 (every 10% flush already took breadth below 25); helps SOX (6m +17% vs +7% for cross+flush) - tiny samples. Results stable across parameters (low 15-35, turn 5-15, lookback 4-13).
- vs our fast-crash plan (QQQ 2007-26): plan 79% within 5% of low, further fall -0.4% median / -15% worst, +10.3% at 3m; setup +6.4% at 3m. The plan is the better bottom tool; the setup is a later, confirmation entry.

## 2) Trading system (weekly, 0.1%/side, cash 0%)
- QQQ 2010-26: setup + exit on weekly close below 9w: 5.5% / -28%, exposure 26%. Hold 52 weeks: 11.0% / -30%. Plain 9w trend: 8.8% / -27%. Buy & hold 18.3% / -35%. Our QQQ system ~9% / -14%.
- SPY 2010-26: setup/9w exit 4.4% / -19%; B&H 13.9% / -34%.
- SOXX: setup + hold 52w 15.0% / -40% (2001-26) vs B&H 13.4% / -69%; 2010-26 16.7% vs 23.0%.
- Verdict: not competitive as a standalone system; the 9-week exit whipsaws.
- Single stocks (S&P 1500 current members, survivorship-biased): 9w cross inside the setup window 2010-26: 6m +12.8%, win 69% vs +5.7% / 60% for crosses outside a flush - but excess vs S&P only +3.4% and beats S&P only 51.5%: the edge is the market rebound, not stock selection. RS leaders did NOT beat laggards after a flush (laggards bounced more).

## Now (2 Nov 2026)
- Flush on (QQQ -10.3%), breadth proxy washed out mid-Oct (~19) and recovered to ~55-60 -> setup armed; trigger needs a weekly close above the 9w MA: QQQ ~$718 (+5.5%), SOXX ~$520 (+15%), SPY ~$764.

Not adopted. Possible use: a display-only "confirmation" flag next to the fast-crash plan (user to decide).
