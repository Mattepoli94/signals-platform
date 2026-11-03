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

## 3) Swing-trading version (3 Nov, /home/claude/wk9/swing.py, run6.py, run7.py)
Exits on daily closes: stop / target / time; 0.2% round trip; one position at a time; grid stop 5/8/12%, target 8/15/25%, max 20/40/60 days (27 settings). Default shown: 8% / 15% / 40 days.
- Entries: (a) weekly setup cross; (b) **daily close crosses above the 9-day EMA while the weekly setup is armed** (flush in last 8 weeks + breadth bottom); baselines: any weekly 9w cross, every week.
- QQQ per trade, (b): 1999-2009 18 trades, 78% win, +6.2% avg, PF 4.3; 2010-26 21 trades, 67% win, +4.1%, PF 3.0, ~34 days. Every week baseline: -0.1% / +2.2%. (a) setup: +4.3% / +3.7%. Positive in both eras for all 27 settings (b).
- SPY (b): +3.5% / +4.7% per trade (86% win 2010+). SOXX (b): +5.1% / +5.0%.
- Alone it is low frequency (~1.2-1.9 trades a year, ~20% exposure): ~5-10% a year.
- Single stocks (S&P 1500, survivorship-biased): (b) +2.7% per trade vs +1.1-1.4% unarmed, but vs S&P only +0.6-1.1%; weekly cross in setup vs S&P ~0. Stock picking adds nothing: trade the index.
- **As an overlay on the QQQ trading system** (QQQ US close, cash 0%, +50% QQQ while a swing trade is open, capped at 100%): 2000-09 9.8% / -17.3% -> 14.2% / -19.2%; 2010-26 7.6% / -14.1% -> 9.9% / -14.9%. All 27 exit settings add CAGR in both eras (+3.1 to +6.4 pt; +0.5 to +3.0 pt), worst fall 0 to 4.6 pt deeper. One-day lag (EQQQ next London close): 12.2% / -20.5% and 9.8% / -15.9%. The system is only 28% invested on average during these trades (38% overall).
- Caveats: ~39 trades total; clustered in ~20 corrections; idea proposed by the user after seeing markets (partly in-sample); breadth proxy survivorship-biased. Not adopted - user to decide.
