# Nasdaq-100 value-zone accumulation plan (v1.2)

A monthly savings plan (a *piano di accumulo*) that buys QQQ only at value, instead of on a fixed date. It complements trading system #1: it buys in the conditions where the trading system is usually flat.

## Idea

Plain monthly buying (DCA) is hard to beat on wealth, but it buys tops as readily as bottoms, and the account can spend years below the money put in. This plan keeps contributions in cash (earning interest) and invests them when QQQ comes back to levels that have historically been good value, after price has started to turn up. You give up some wealth in strong bull markets in exchange for much smaller drawdowns.

## Rules (daily adjusted closes; buys at the close; never sells)

1. Every contribution goes into the pot's cash.
2. **Trend zone.** Fit a straight line to log(close) over the last 1,260 sessions (5 years). *z* is today's distance from the line in standard deviations of the fit's residuals. Zone = −1 < z ≤ 0 **and** close above the 20-day SMA.
3. **200-week zone.** Close 0–15% above the 1,000-day SMA **and** close above the 50-day SMA.
4. On a close in either zone, buy **50% of the cash** at the close. At most one buy every 10 trading days.
5. **Safety cap.** On the first trading day of a month, if cash is above 24 × the monthly contribution, invest the excess.
6. **Fast-crash buys (v1.2).** In a QQQ fast crash (down 8%+ within 15 sessions from near its 1-year high), use the Risk radar's fast-crash plan:
    - **Buy 1:** at the first close 10.8% below the 1-year high, invest **50% of the cash**.
    - **Buy 2:** at a later, lower close with 3+ of 6 capitulation groups on, invest **all the cash**.
    - Both are skipped when the override is on (rate/inflation pressure, or the late-cycle radar red). They ignore the 10-day cooldown.
    - Full rules: [Bottom signals](bottom-signals.html).

Price below the trend zone (z ≤ −1) is not bought. Deep levels behaved like falling knives in secular bear markets (2000–2002).

## Results of the zones alone (v1.1; rolling plans, $1,000 a month, cash at the T-bill rate)

| Plans | Wealth vs monthly DCA (median) | Account drawdown (median) | Below money in (median / worst) |
|---|---|---|---|
| 10 years, starts 2000+ | −5.4% | −34% vs −49% | −19% / −37% vs −29% / −56% |
| 10 years, starts 1986–99 | −0.2% | — | −3% / −24% vs −23% / −57% |
| 20 years | −3% to +1% | — | — |

Level study: after a trend-zone close, QQQ returned +39% over the next year in 1990–2005 and +23% in 2006–25 (loss in 1% and 11% of cases). After a 200-week-zone close: +26% and +23%.

## v1.2: what the fast-crash buys add

10-year plans, $1,000 a month, started every month 2000–2016, cash at the T-bill rate.

| Version | Wealth vs DCA (starts 2000–08 / 2009–16) | Account drawdown, median | Worst time below money in |
|---|---|---|---|
| Monthly DCA | – | −44% / −30% | −56% / −14% |
| v1.1 zones only | −4.3% / −6.2% | −42% / −28% | −37% / −10% |
| **v1.2 zones + fast-crash buys** | **−0.6% / −1.4%** | −42% / −29% | **−37% / −9%** |
| v1.2 + bear washout buys (not adopted) | +0.8% / −1.2% | −43% / −29% | −48% / −9% |

- The zones rarely buy during a crash: they need the price back above its 20- or 50-day average. So cash builds up exactly when the fast-crash buys fire, and no separate reserve is needed.
- **A dedicated crash reserve was tested and not adopted.** Setting aside 10–30% of each contribution cost 0.7–2.5 points of wealth versus DCA, and only trimmed drawdowns because more money sat uninvested.
- **The bear washout was left out.** It added little, and in the dot-com years it deepened the worst time below money put in from −37% to −48%.
- **The trading system does not use these buys.** By the user's choice, it keeps its lower drawdown.
- **Caveat:** the fast-crash plan was designed on the 2007–26 crashes. 1999–2006 gives only partly independent evidence.

## What to expect

- Long stretches with no buys in strong markets. Cash can build up for many months; that is the plan working, not a fault.
- Over 10–20 years, wealth roughly equal to or a little below monthly buying, with much shallower drawdowns.
- Fit with trading system #1: on zone-buy days the trading system was flat or half-invested 97% of the time.
- The rules are QQQ-specific: on SPY the zones gave no edge in 1998–2009.

## UK implementation (v1.1)

The zones are still judged on QQQ at the US close: the rules were validated on that series, and they move slowly. A buy is placed in **EQQQ** (pence, ISA) at the next London close. That is one session later than in the research, which matters little for a plan that buys a few times a year, and it avoids any currency fee. The cut-off is 16:25 UK. The site shows a buy as due the evening before (after the US close), and again in the ~16:05 live preview.

## On this platform

- Your initial capital and every top-up go into the pot's cash on their date. The monthly top-up setting adds money automatically on the first trading day of each month and enables the safety cap.
- The Investing page shows each zone condition live, what a buy would invest (50% of cash), and the plan against QQQ buy-and-hold with the same deposits.
