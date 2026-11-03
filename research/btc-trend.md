# BTC cycle trend system (v2, live from 3 November 2026)

Trading system #2. Spot Bitcoin, long or flat, checked once a day at the 00:00 UTC close. It replaces the v1 "trend blend", which failed its out-of-sample re-test (see the history at the end).

## Idea

Bitcoin moves in long trends, and so far its four-year halving cycle has produced a deep bear market roughly 18 to 30 months after each halving. The system:

- follows the trend with a fast pair of daily moving averages;
- stays out of the market during the post-halving bear window;
- halves its size when the trend is weak, or during the mid-cycle chop phase.

## Rules

Every day at the 00:00 UTC daily close:

1. **Trend.** Be in the market while the **30-day EMA** of daily closes is above the **50-day EMA**. Buy at the close when it crosses above; sell everything at the close when it crosses below.
2. **Bear window.** From **day 541 to day 900 after each halving**, hold no BTC: sell if invested, and make no new entries. When the window ends, buy at the first close if the 30-day EMA is above the 50-day.
3. **Size.** Hold **100% of the BTC pot**, except **50%** when either:
   - **ADX(14)** is below 25 (Wilder's ADX on daily highs, lows and closes: the trend has no strength), or
   - it is **day 1,081 to 1,260 after the halving** (mid-cycle chop phase).

   Rebalance at the close when the size changes.
4. **No other exits.** No stop loss and no profit target. The cross, the bear window and the size rules are the only exits.

The EMAs are standard exponential moving averages (span 30 and 50) of daily closes. Days are counted from the halvings of 28 Nov 2012, 9 Jul 2016, 11 May 2020 and 20 Apr 2024. The next halving is expected around April 2028.

| Halving | Bear window: flat | Chop phase: half size |
|---|---|---|
| 20 Apr 2024 | 13 Oct 2025 – 7 Oct 2026 | 6 Apr 2027 – 2 Oct 2027 |
| ~Apr 2028 (est.) | ~Oct 2029 – ~Oct 2030 | ~Apr 2031 – ~Oct 2031 |

## How it was tested

- **Data:** Coin Metrics daily BTC/USD, 2012 to October 2026. Daily highs and lows for ADX come from Yahoo and start in late 2014.
- **Positions:** decided at the close and held to the next close. Idle cash earns the 3-month T-bill.
- **Costs:** 0.40% per trade (Kraken Pro limit-order fee), on every change in position, size changes included.
- **Held-out years:** a stratified random draw, one each from the bear, middle and bull thirds of years: **2012, 2016 and 2018**. They were never used to choose rules. With the ADX size rule, 2012 can't be tested (no highs and lows that early), so the held-out figure covers 2016 and 2018.
- **Search:** about 560 trend variants tested on the other years:
  - daily and weekly charts;
  - simple and exponential averages;
  - crossover and close-above entries;
  - crossover, close-below-slow and close-below-fast exits;
  - fast 10–50 days with slow 50–200 days.

  The cycle overlays, chop indicators (ADX, the Choppiness Index, Kaufman's efficiency ratio) and dip-buying legs were tested after that.

## Results (0.40% per trade; buy and hold with no costs)

| Period | Yearly return | Worst fall | Return ÷ worst fall |
|---|---|---|---|
| 2016–Oct 2026 | **83%** | **−34%** | 2.44 |
| Held-out years 2016 + 2018 | 38% | −24% | 1.6 |
| Same rules on Yahoo prices (as live), 2016–Oct 2026 | 84% | −34% | 2.51 |
| Buy & hold, 2016–Oct 2026 | 61% | −84% | 0.73 |

The worst fall is the largest drop of the pot's value (BTC plus cash) from a previous high, on daily closes.

**Year by year** (final rules). Each cell is the year's return / worst fall within that year:

| Year | System | Buy & hold |
|---|---|---|
| 2016 (held out) | +88% / −24% | +129% / −31% |
| 2017 | +796% / −34% | +1,250% / −36% |
| 2018 (held out) | +2% / 0% | −72% / −81% |
| 2019 | +151% / −15% | +88% / −49% |
| 2020 | +171% / −18% | +310% / −52% |
| 2021 | +136% / −26% | +62% / −53% |
| 2022 | −4% / −6% | −65% / −67% |
| 2023 | +62% / −16% | +165% / −20% |
| 2024 | +62% / −23% | +114% / −26% |
| 2025 | +3% / −16% | −6% / −32% |
| 2026 (to Oct) | −1% / −5% | −13% / −40% |

It beats buy and hold in every bear or sideways year and in some bull years (2019, 2021). It lags in strong, steady bull years (2016, 2017, 2020, 2023, 2024), because it enters late and runs at half size while the trend is still weak.

## What each part contributes (2016–Oct 2026)

| Version | Yearly return | Worst fall |
|---|---|---|
| 30/50 crossover only | 67% | −64% |
| + bear window (day 541–900) | 86% | −40% |
| + half size in the chop phase | 91% | −40% |
| + half size when ADX < 25 (final) | 83% | −34% |

## Decisions and rejected ideas

- **Weekly charts:** too slow. A 13/40-week crossover with the bear window had a −67% worst fall from 2019 to 2020.
- **Close-below-slow-average exits:** for 30/50 they gave more whipsaws and were worse (65% / −45%). They do help pairs that are far apart.
- **Trailing stops (15–30%) and volatility sizing:** both made results worse.
- **Narrower "trade only in bull phases" windows:** results jumped around with small changes in the dates. Not adopted.
- **Chop detection inside the chop phase (ADX, Choppiness Index, efficiency ratio):** no better than the calendar alone. ADX below 25 works as a general filter at any time.
- **Dip-buying leg:** only RSI(14) below 30 in a bull market helped, by about 3 points a year from 14 trades in 15 years, and it was fragile to the threshold. Left out.

## What to expect

- **Optimism from heavy testing.** Many variants were tried, so live results will likely be below the backtest. The site's *Live vs expected* chart flags any drift.
- **The cycle window is the biggest dependency.** It rests on four halving cycles. If the next cycle tops later than about 18 months after the halving, the window would sell too late. Starting it at day 580 instead of 540 badly hurt 2018.
- **Trading activity.** About 2 entries a year, plus size changes: roughly 10 order tickets a year in total. At 0.40% a trade that is about 1.5–2% a year in fees, already included above.
- **Lag in strong bull runs.** It catches part of them, not all. Its strength is sitting out bear markets.

## Execution

- **Kraken Pro:** limit orders at 0.40% (market orders cost 0.80%). This matches the 00:00 UTC close exactly.
- **IB1T:** the iShares bitcoin ETP on the London Stock Exchange, 0.25% a year, can be held in an ISA. Its line is priced in dollars, so Trading 212 adds 0.15% per trade. It trades the next session, about a day late, which made no material difference in testing.
- Set the BTC pot's fee in Settings to match the route you use.

## History

- **v1 (2 Nov 2026):** daily five-signal blend, volatility sizing, flat from day 545 to 910. In-sample 105% / −30% over 2015–24. Failed its re-test on 3 Nov 2026: refitted on training years only, it made 8% a year in the held-out years, and 37% / −64% in a year-by-year re-fit over 2016–26, against buy and hold at 61% / −84%.
- **v2 (3 Nov 2026):** this system, rebuilt from scratch. Scripts and outputs are in `research/btc-v2/`; the v1 re-test is in `research/btc-recalibration/`.
