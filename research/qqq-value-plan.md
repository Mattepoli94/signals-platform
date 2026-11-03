# QQQ value-zone accumulation plan (v1.0)

A monthly savings plan (a *piano di accumulo*) that buys QQQ only at value, instead of on a fixed date. It complements trading system #1: it buys in the conditions where the trading system is usually flat.

## Idea

Plain monthly buying (DCA) is hard to beat on wealth, but it buys tops as readily as bottoms, and the account can spend years below the money put in. This plan keeps contributions in cash (earning interest) and invests them when QQQ comes back to levels that have historically been good value, after price has started to turn up. You give up some wealth in strong bull markets in exchange for much smaller drawdowns.

## Rules (daily adjusted closes; buys at the close; never sells)

1. Every contribution goes into the pot's cash.
2. **Trend zone.** Fit a straight line to log(close) over the last 1,260 sessions (5 years). *z* is today's distance from the line in standard deviations of the fit's residuals. Zone = −1 < z ≤ 0 **and** close above the 20-day SMA.
3. **200-week zone.** Close 0–15% above the 1,000-day SMA **and** close above the 50-day SMA.
4. On a close in either zone, buy **50% of the cash** at the close. At most one buy every 10 trading days.
5. **Safety cap.** On the first trading day of a month, if cash is above 24 × the monthly contribution, invest the excess.

Price below the trend zone (z ≤ −1) is not bought. Deep levels behaved like falling knives in secular bear markets (2000–2002).

## Results (rolling plans, $1,000 a month, cash at the T-bill rate)

| Plans | Wealth vs monthly DCA (median) | Account drawdown (median) | Below money in (median / worst) |
|---|---|---|---|
| 10 years, starts 2000+ | −5.4% | −34% vs −49% | −19% / −37% vs −29% / −56% |
| 10 years, starts 1986–99 | −0.2% | — | −3% / −24% vs −23% / −57% |
| 20 years | −3% to +1% | — | — |

Level study: after a trend-zone close, QQQ returned +39% over the next year in 1990–2005 and +23% in 2006–25 (loss in 1% and 11% of cases). After a 200-week-zone close: +26% and +23%.

## What to expect

- Long stretches with no buys in strong markets. Cash can build up for many months; that is the plan working, not a fault.
- Over 10–20 years, wealth roughly equal to or a little below monthly buying, with much shallower drawdowns.
- Fit with trading system #1: on zone-buy days the trading system was flat or half-invested 97% of the time.
- The rules are QQQ-specific: on SPY the zones gave no edge in 1998–2009.

## On this platform

- Your initial capital and every top-up go into the pot's cash on their date. The monthly top-up setting adds money automatically on the first trading day of each month and enables the safety cap.
- The Investing page shows each zone condition live, what a buy would invest (50% of cash), and the plan against QQQ buy-and-hold with the same deposits.
