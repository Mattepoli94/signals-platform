# Portfolio decisions and rejected ideas (3 November 2026)

This page records what was tested around the three systems and **not** adopted, so the same ideas are not re-tested by accident. Nothing here runs on the platform.

## 1. The three pots together

Platform rules and fees (EQQQ 0.05%, GBP↔USD 0.15%, BTC 0.40%), in GBP, June 2015 – October 2026.

- The Nasdaq trading system and the BTC system are almost uncorrelated: daily returns 0.06, weekly 0.12. Both were more than 10% down on only 2% of days, about what chance would give.
- **Alone:** Nasdaq trading 8.6% a year, worst fall −13.3%. BTC system 84.9% a year, worst fall −33.6%.
- **Mixed and rebalanced monthly:** 50/50 gives 45% a year with a −22% worst fall. 80/20 (Nasdaq/BTC) gives 23% and −14%.
- The worst combined fall was December 2017 – March 2018, driven by BTC.

### Rebalancing between pots: not adopted (for now)

| Method (50/50, costs included) | Yearly return | Worst fall | Trades a year |
|---|---|---|---|
| Never | 74% | −33% | 0 |
| Yearly | 53% | −31% | 1 |
| Quarterly | 49% | −26.5% | 4 |
| Monthly | 45% | −22% | 12 |
| Drift band: rebalance when BTC's share is 10+ points off target | 46% | −18.8% | 1.4 |

- Any rebalancing roughly halves the worst fall. That held in every sub-period and in 34 rolling 3-year windows.
- The differences between methods are mostly noise: the monthly result moves between −18% and −24% depending on the day of the month.
- **Decision:** no rebalancing for now. If it is added later, the 10-point drift band is the cheapest version.

### Replay: £10,000 in each pot from 1 January 2021

This used the platform's own ledger and fees, cash at 0%, no rebalancing and no taxes, up to 2 November 2026.

| Pot | End value | Yearly return | Worst fall | Buy & hold |
|---|---|---|---|---|
| Value plan v1.1 (zones only) | £19,785 | 12.4% | −24.2% | EQQQ £22,707 |
| Value plan v1.2 (with fast-crash buys) | £21,467 | 14.0% | −24.2% | EQQQ £22,707 |
| Nasdaq trading system | £17,670 | 10.3% | −10.5% | EQQQ £22,707 |
| BTC cycle trend system | £52,504 | 32.8% | −26.3% | BTC £26,557 |

- **Total (v1.1):** £89,958 from £30,000, with a −15.0% worst fall for the total. Buy and hold of the same three would have made £72,101, with a −48.2% worst fall.
- **Not included:**
  - interest on idle cash (about +£5–6k);
  - EQQQ dividends (about 0.5% a year);
  - capital gains tax on BTC held outside the ISA.
- **All of 2021–26 is in-sample** for the systems' design.

## 2. Gold trend system: not adopted

The system was designed from scratch on GLD 2006–2026, with 51 randomly held-out months.
- **Rules tried:** 37 core rules (trend, momentum, OBV, VWAP, volume profile, CMF, dip-buying), then filters and sizing.
- **Chosen:** a 50% EMA 50/150 trend leg plus an RSI(2) dip leg.

**Results:**
- **Held-out months:** 9.6% a year with a −9.3% worst fall, against buy and hold at 13.5% and −26%.
- **Walk-forward 2012–26:** only 3.5% a year with −25%, barely ahead of buy and hold on a risk-adjusted basis.
- **UK version on SGLN:** 5.5% a year with −15.6%.

Volume indicators did not help.

**Decision:** too little return for the effort. A cash ISA at about 4–5% gives similar returns without the drawdown risk.

## 3. Diversifiers for bad months: not adopted

45 ETFs were screened in GBP over July 2015 – October 2026. Each was judged on how it did in the systems' worst third of months.

- **Defensive sectors, value, low-volatility, quality and dividend funds do not help.** They are still equities, with a correlation of +0.25 to +0.40 to the systems, and they lost 0.4–0.8% a month in the systems' bad months.
- **Bonds and the dollar:** close to zero correlation, but they also lost in bad months. TLT fell 23% in 2022.
- **What did help:**

  | Asset | Gain in the systems' bad months | Long-run return | Worst fall |
  |---|---|---|---|
  | Gold | +0.7% a month | 12.3% a year | −27% |
  | Energy | +0.8% a month | 11.4% a year | −64% |
  | Broad commodities | +0.6% a month | 8.8% a year | −39% |
  | Managed futures (2022) | +36–39% | – | – |

  2022 dominates these results.
- **Decision:** "not enough alpha". Stick to the three systems.

## 4. Other ideas tested elsewhere

- **The old 3-point risk flag and stress gauges:** see [Risk radar](risk-radar.html), section 4.
- **The fast-crash plan:**
  - in the trading system: not adopted (more drawdown);
  - a separate crash reserve in the value plan: not adopted;
  - the bear washout in the value plan: not adopted.

  See [Bottom signals](bottom-signals.html) and [Value plan](qqq-value-plan.html).
- **The BTC trend blend (v1):** retired after failing its re-test. See [BTC cycle trend system](btc-trend.html).
