# BTC trend blend (v1.0)

Trading system #2. Spot Bitcoin, long or flat. Built from scratch for BTC rather than adapted from the QQQ system.

## Idea

Bitcoin trends strongly in both directions, and its four-year halving cycle has produced deep bear markets roughly 1.5–2.5 years after each halving. The system holds BTC in proportion to how many trend signals agree. It cuts size when volatility is extreme, and stays out during the post-halving bear window.

## Rules (daily close at 00:00 UTC, BTC/USD)

1. **Score** = average of five 0/1 signals:
   - close above the close 10 days ago;
   - close above the close 20 days ago;
   - close above the close 50 days ago;
   - close above the 50-day EMA;
   - 10-day EMA above the 30-day EMA.

   The score can be 0, 0.2, 0.4, 0.6, 0.8 or 1.
2. **Volatility sizing.** Multiply by min(1, 80% ÷ 30-day realised volatility). Volatility is the standard deviation of daily log returns over 30 days × √365.
3. **Halving window.** Hold nothing from day 545 to day 910 after each halving: 28 Nov 2012, 9 Jul 2016, 11 May 2020 and 20 Apr 2024. The next halving is expected around April 2028, so the next window runs about October 2029 to October 2030.
4. **Target weight** = score × volatility factor (0 inside the window). The rest of the pot stays in cash.

On the platform, the pot trades to the target when the score or the window changes, or when the holding drifts more than 10 points from target. EMAs use the standard recursive formula (span n).

## Results (10 bp costs, cash at the T-bill rate)

| Period | CAGR | Max drawdown | Calmar | BTC buy & hold |
|---|---|---|---|---|
| Training 2015–2024 | 105% | −30% | 3.46 | 77% / −84% / 0.92 |
| Early check 2011–2014 | 301% | −42% | — | drawdown −93% |
| 2025–Oct 2026 (seen during research, not independent) | −1% total | −17% | — | −17% total, −53% drawdown |

Calmar by era: 2015–17 6.3, 2018–20 3.4, 2021–24 2.1. About 49% invested on average.

## Filters tested

- **Halving window:** kept. It lifted Calmar from 1.55 to 3.43 and cut the worst drawdown from −54% to −33%.
- **Volatility sizing:** kept as crash insurance. Little change in 2015–24, but it cut the 2011–14 drawdown from −70% to −42%.
- **Dropped:** dollar-strength, Fed-liquidity, credit and overheating filters. Each made results worse or added nothing. Dollar and liquidity are shown on the dashboard as context only.
- **Which moving average** mattered much less than the halving window and volatility sizing. Almost any sensible trend rule inside that wrapper scored Calmar 2.2–3.5.

## What to expect

- About 180 variants were tested in total, so the training figures are optimistic. Expect less in live trading.
- Many small adjustments: each change in score moves the target by 20 points. With a 0.10% fee that is a real but small cost.
- Long flat periods inside the halving window, even if the price rises.
- The research used Coin Metrics closes. Live signals use Yahoo's BTC-USD close at 00:00 UTC; the two sources occasionally differ by a day's signal.

## Re-test, 3 November 2026: failed out of sample

After the live-vs-expected chart showed the pot far below its expected range, the system was re-fitted from scratch with the QQQ discipline. The design was written down before any test ran (`research/btc-recalibration/PREREG.md` in this repo).

**Holdout.** The years 2012–2026 were ranked by BTC's return and split into thirds (bear, middle, bull). One year was drawn at random from each third (seed 20261103): **2018, 2016 and 2012**. The other 12 years were used for fitting.

**Search on the training years only.** The search ran in stages, with the selection rules fixed in advance:

1. Trend rule. From 26 candidates, the simplest family within 10% of the best was kept, and the centre of its best range of lengths was chosen: close above the 100-day EMA.
2. Volatility sizing at a 100% target. It was kept because it improved both Calmar and drawdown.
3. Halving window. It was **dropped**: its best setting improved training Calmar by only 9%, below the 20% bar set in advance.

**Result.** Training: 128% a year, worst fall −52%. Holdout years: **8% a year, worst fall −57%**. In 2018 it lost 49%: BTC crossed its 100-day EMA 25 times that year. That fails the adoption rule, which required holdout Calmar of at least half the training figure (0.14 against a required 1.25).

**Walk-forward check of the whole procedure.** For each year from 2016 to 2026, the same selection stages were re-run on the years before it, and that year was traded out of sample:

| 2016–Oct 2026, out of sample | Yearly return | Worst fall | Calmar |
|---|---|---|---|
| Walk-forward trend system | 37% | −64% | 0.57 |
| Holding BTC | 61% | −84% | 0.73 |
| v1 system (the rules on this page; in-sample, for reference) | 83% | −30% | 2.75 |

The trend rule chosen changed from year to year, which is a sign of no stable edge. The v1 system's halving window would have saved 2018 (+12% against −72%), but the evidence for the window rests on only four halving cycles. When it was fitted only on the years before each test year, it did not hold up as a reliable improvement.

**Conclusion.** No version of the BTC trend system has a validated edge over simply holding BTC. Out of sample, trend timing cut the worst fall by about 20 points but gave up about 40% of the return. The gap between the v1 backtest (Calmar 2.75) and the walk-forward result (0.57) is the in-sample optimism the live chart exposed.

**On the platform.** The BTC pot keeps following the v1 rules as a **paper-only** track and is labelled as such. The rules were not swapped for a variant picked after seeing the holdout, because that would bring the bias straight back. The choice of what to do with BTC money is open; see the options in the project notes.
