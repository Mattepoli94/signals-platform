# Nasdaq-100 regime system + dollar add-on (v1.1, UK implementation)

Trading system #1. Long-only on the Nasdaq-100, with the US dollar as the only add-on. Since v1.1 it is traded in **EQQQ** (Invesco EQQQ Nasdaq-100 UCITS ETF, London, priced in pence) inside the ISA, at the **London close**. The dollar add-on is held as **USD cash in the Trading 212 Invest account**. The rules themselves are unchanged from v1.0. The full build specification, with every test, is in the [Build Spec v1.0](https://claude.ai/artifact/Kjtfn4jJ1JdCrynU9ubXvc). This page is the short version the platform runs.

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

## Original research results (QQQ at the US close, 3 bp costs, cash at the T-bill rate)

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
- **Costs matter.** See v1.1 below: trading a pence-priced ETF in the ISA removes the 0.15% FX fee from the Nasdaq trades.
- The rules work on QQQ, not on SPY: the same rules on SPY gave about half the return.

## v1.1: UK implementation (3 Nov 2026)

**Why it changed.** The fee is charged on the value of every trade, and this system trades a lot. The Nasdaq legs alone trade about 15–22 times the pot each year. The dollar add-on mirrors every Nasdaq change, so the total is about 35 times the pot a year. A 0.15% currency fee therefore costs about 5% a year, while the average dip trade only earns +0.7% to +1.0%. Trading 212 charges the fee only when it converts currency. EQQQ is priced in pence, so buying it from GBP in the ISA has no FX fee; the cost is just the bid/ask spread.

**What runs now**

- The same rules, applied to EQQQ's own daily closes at the London close (16:30 UK). A preview email goes out at ~16:05 with the live London price; place orders before 16:25.
- Dollar add-on: USD cash = 0.5 × (1 − EQQQ weight) while UUP trends. UUP is judged at the latest US close before the London close. Each switch is a GBP↔USD conversion at 0.15%.
- Risk flag: unchanged. It uses US data from the latest US close.

**Test** (EQQQ 2010–Oct 2026, in GBP, rules not re-tuned, cash earning 0%). Yahoo's EQQQ history had bad prints, including weeks quoted in US cents. They were repaired against QQQ ÷ GBP/USD, and the platform does the same live.

| Variant | 2010–24 CAGR / max drawdown | 2025–Oct 2026 |
|---|---|---|
| Research reference: QQQ at the US close, 3 bp | 9.4% / −14.1% | 5.7% / −16.2% |
| Same with Trading 212's 0.15% FX fee | 7.4% / −16.5% | 3.0% |
| **EQQQ, signal and trade at the London close, 5 bp** | **7.7% / −13.8%** | **11.0% / −9.5%** |
| … plus the dollar add-on (USD cash, 0.15% per switch) | **9.0% / −14.1%** | 10.4% / −9.8% |
| EQQQ, signal at the London close, trade at the next London open, 5 bp | 8.0% / −14.2% | 12.8% / −6.5% |
| Same at a 10 bp spread at the open | 7.1% / −14.9% | 11.8% |
| QQQ US-close signal, trade EQQQ at the next London open | 6.9% / −18.3% | 2.1% |
| EQQQ buy & hold | 19.5% / −28.2% | 13.0% / −24.2% |

EQQQ dip trades: 9.2 a year, 75.5% winners, average +0.64%, worst −5.8%. Computing the signals on EQQQ converted to USD did worse (6.7%). So did timing the dollar with its own trend against the pound (7.3%) instead of UUP's.

## Execution notes

- Signals use the London close, so orders go in just before it: the preview email arrives at ~16:05 and the cut-off is 16:25 UK. Yahoo's London prices can be about 15 minutes delayed.
- If an order is missed, trade as early as possible next session. Record the real fill (in pence) in the trade journal so the pot reflects it.
- EQQQ pays small dividends (about 0.3–0.5% a year). They are not in the price series, so the pot slightly understates the return. CNX1 (iShares, accumulating) tracks the same index if you prefer.
