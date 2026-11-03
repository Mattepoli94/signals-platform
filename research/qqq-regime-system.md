# QQQ regime trading system + dollar add-on (v1.0)

Trading system #1. Long-only on QQQ, with the US dollar (UUP) as the only add-on. The full build specification, with every test, is in the [Build Spec v1.0](https://claude.ai/artifact/Kjtfn4jJ1JdCrynU9ubXvc). This page is the short version the platform runs.

## Idea

QQQ behaves differently in different regimes. When it trends, holding it pays. When it is not trending, short sell-offs tend to snap back within days. The system holds half a position in trends and buys short dips when there is no trend, with a tight stop and a time limit. Money that is not in QQQ can sit in the dollar when the dollar trends, because dollar strength has often lined up with equity stress.

## Rules (daily adjusted closes; every order at the close of the same day)

**Regime.** *Trending* = close above its 50-day SMA **and** the 50-day SMA higher than 10 sessions earlier. Otherwise *Range above 200-day* (close above the 200-day SMA) or *Below 200-day*.

**Trend leg.** 50% of the pot in QQQ while Trending.

**Dip leg.** New entries only when not Trending.

| Regime | Entry (any one) | Size |
|---|---|---|
| Above 200-day | close below lower Bollinger band (20, 2) · 3 lower closes in a row · RSI(2) below 10 | 100% |
| Below 200-day | close below lower Bollinger band (20, 2) · RSI(2) below 5 | 50% |

Exit the dip trade at the close on the first of these:

- RSI(2) closes above 70 (take profit);
- close at or below entry × 0.97 (stop loss);
- the 10th session after entry (time exit);
- the regime turns Trending (the trend leg then holds 50%).

**QQQ weight** = trend + dip × (1 − trend).

**Dollar add-on.** UUP weight = 0.5 × (1 − QQQ weight) while UUP is Trending (same definition as QQQ). Otherwise 0.

**Risk flag (display only).** One point each for:

- W1: 3-month T-bill yield up more than 0.5 pt over 126 sessions;
- W2: dollar index up more than 5% over 126 sessions;
- W3: two or more of QQQ, TLT and GLD below their 200-day SMA.

0 = green, 1 = amber, 2+ = red. The flag does not change orders: acting on it did not help in tests.

Indicators: SMA = simple average of adjusted closes. RSI(2) uses Wilder smoothing. Bollinger uses the sample standard deviation.

## Results (3 bp costs, cash at the T-bill rate)

| Period | CAGR | Max drawdown | QQQ buy & hold |
|---|---|---|---|
| 2000–2024 (training with held-out years) | 10.4% | −15.3% | — |
| Held-out years only | 4.9% | −13.8% | — |
| Final holdout 2025–Oct 2026 (run once) | 8.5% | −13.5% | 20.9% |

Bear markets, peak to trough: 2000–02 +40% vs −83%; 2008 +0.2% vs −53%; 2018 Q4 −3.8% vs −23%; 2020 −8.5% vs −29%; 2022 +2.5% vs −35%; 2025 −14.0% vs −23%.

## What to expect

- Far smaller drawdowns than holding QQQ. Much lower returns in strong bull markets: since 2009 the system behaves like roughly 40% QQQ and 60% cash.
- About 9 dip trades a year (2000–2024), most lasting a few days. 71% of them were winners, with an average gain of +1.0% per trade. The stop normally limits a loss to about −3%, but gaps made the worst trade −8.4%.
- On top of the dip trades come trend-leg switches and dollar add-on switches: in 2025–26 the pot made about 70 trades a year in total.
- **Costs matter.** The research used 3 bp per trade. Trading 212 charges 0.15% FX on each USD trade from a GBP account. Replaying January 2025 to October 2026 with that fee cut the result from +11.7% to +2.0%. The pot on this platform includes your real fee.
- The rules work on QQQ, not on SPY: the same rules on SPY gave about half the return.

## Execution notes

- Signals use the close, so orders must be placed just before the close (by 15:55 New York). The platform emails a preview ~25 minutes before the close, using the live price.
- If an order is missed, trade as early as possible next session. Record the real fill in the trade journal so the pot reflects it.
- UK investors usually cannot buy US-listed ETFs (QQQ, UUP) in a normal account because of PRIIPs rules. Common routes are a CFD account on QQQ, or a UCITS Nasdaq-100 ETF (it trades in London hours, so it cannot be bought at the US close). Each route changes timing, costs and tax. The pot here is valued on QQQ prices.
