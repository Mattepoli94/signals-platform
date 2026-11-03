# Bottom signals (v1, live from 3 November 2026)

Two buy-side signals, shown on the **Risk radar** page under *Bottom signals*. They are display only: they say when history favoured buying into a fall, and no order depends on them.

| Signal | Market | Use |
|---|---|---|
| **Fast-crash bottom plan** | QQQ | A sudden fall from near the high: buy in two steps, unless the override says this fall may become a bear market |
| **Bear-market washout** | S&P 500 and QQQ | A deep, prolonged fall: buy on capitulation |

---

## 1. Fast-crash bottom plan (QQQ)

### Rules

1. **Fast crash:** QQQ falls 8% or more within 15 sessions, starting within 4% of its 1-year high. The plan runs for the next 40 sessions.
2. **Override:** on the buy-1 day, skip the plan if either of these is on. The fall is then left to the bear-market washout.
   - **rate/inflation pressure:** the 10-year yield is up 1.5 points or more in a year, or CPI inflation is above 4% and higher than 6 months earlier;
   - **late-cycle radar red:** 3 or more of its 5 signs.
3. **Buy 1:** the first close at least **10.8% below the 1-year high**.
4. **Buy 2 (same amount):** the first later close **below the buy-1 price**, within 40 sessions, with **3 or more of these 6 capitulation groups on**. Each group stays on for 10 sessions after it fires.

| Group | On when | Data |
|---|---|---|
| Stretch | Drawdown, or the 15-day fall, of 2.5+ times one-year daily volatility (scaled) | QQQ |
| Capitulation volume | Volume at least 1.8× its 50-day average on a down day of 2%+ (last 3 sessions) | QQQ |
| Options fear | Cboe total or equity put/call (5-day mean) in the top 10% of the last year | Cboe |
| Volatility panic | Nasdaq VIX (VXN) in the top 10% of the last year, or VIX9D/VIX ≥ 1.05 | Cboe |
| Dealers short gamma | Dealer gamma exposure (GEX) below zero | SqueezeMetrics |
| Oversold | RSI(14) ≤ 30 or RSI(2) ≤ 5 | QQQ |

### Where 10.8% comes from

10.8% is the S&P 500's best fast-crash depth (8%) scaled by the Nasdaq's higher volatility (×1.35). It was not fitted on QQQ.

QQQ fast-crash lows from 1990 to 2026 (42 crashes):
- **median 15.7% below the high**; the middle half fell between 12.6% and 18.1%;
- **93% went deeper than 10.8%.**

So buy 1 means "you're now in the crash", typically 5–6% above the eventual low. Buy 2 is there to catch more of the remaining fall.

QQQ depth sensitivity:
- **−9%:** too early.
- **−10.8% and −12%:** about equally good.
- **−15%:** misses most crashes.

### Results: QQQ, 19 fast crashes 2007–2026

| | One buy at −10.8% | **Plan (two buys + override)** |
|---|---|---|
| Buys | 16 | **14** (2 skipped) |
| Second buy used | – | 9 |
| Average entry above the crash low | +4.5% | **+2.9%** |
| Entries within 5% of the low | 62% | **79%** |
| Further fall in the next 3 months (median / worst) | −1.6% / −18% | **−0.4% / −15%** |
| Days below the entry price over the next year (median) | 5 | 5 |
| Days until back above entry for good (median) | 37 | **24** |
| Return after 1 / 3 / 6 months | +2.9% / +8.9% / +15.6% | **+4.9% / +10.3% / +18.0%** |
| Up after 3 months | 81% | **86%** |

**By era:**
- **2007–15:** 7 buys, 71% within 5% of the low, +10.2% after 3 months.
- **2016–26:** 7 buys, 86% within 5% of the low, +10.5% after 3 months.

**Skipped by the override:**
- **January 2022:** QQQ fell another 22% (a rate-driven bear market).
- **March 2025:** the bear washout bought this fall on 4 April 2025, near the low.

**What the override adds over a longer history** (QQQ 1990–2026, fast-crash buys plus washouts):

| Override | Fast-crash buys skipped | Buys that fell 10%+ more | Return after 6 / 12 months | Worst 12 months |
|---|---|---|---|---|
| None | 0 | 30% | +17.8% / +27.0% | −66% |
| Rate/inflation pressure | 3 | 27% | +19.0% / +29.6% | −66% |
| Late-cycle red | 4 | 25% | +17.8% / +29.3% | −42% |
| **Either (live rule)** | 6 | **21%** | **+19.0% / +30.6%** | **−42%** |

### How each second-buy trigger scored on its own (2007–2026)

The score is the 3-month return minus the median further fall; higher is better.

| Second-buy trigger | Times it fired | Score 2007–15 / 2016–26 |
|---|---|---|
| Put/call heavy (total or equity) | 9 | 8.2 / 8.0 |
| **3+ of 6 groups (live)** | 12 | **8.5 / 8.1** |
| Dealers short gamma | 8 | 8.2 / 7.9 |
| Nasdaq VIX / short-term panic | 8–9 | 8.2 / 7.5 |
| Capitulation volume alone | 7 | 7.6 / 7.5 |
| CFTC futures positioning (dropped) | 4–5 | 7.7 / 7.1 |
| No second buy | – | 7.6 / 6.9 |

### What did not work

**As the first buy**, every dynamic signal fired too early in the fall. That covers volume capitulation, put/call, VXN, gamma, positioning and RSI. So do these 12 price patterns:
- hammer;
- volume climax;
- engulfing;
- key reversal;
- gap reversal;
- exhaustion;
- swing turn;
- RSI(2);
- divergence;
- ATR stretch;
- thrust;
- Bollinger re-entry.

A depth tied to implied volatility helped in 2007–15 but hurt in 2016–26.

The **2.5-sigma Bollinger band re-entry** was the best first-entry pattern: 8 of 23 crashes, +14% after 3 months, consistent in both eras. But it is rare and sensitive to its settings, so it is not used.

**SOXX:** see section 3. It is studied as a flag only and is not on the platform.

---

## 2. Bear-market washout (S&P 500 and QQQ)

### Rules

In a bear state (S&P 500 15%+ below its 1-year high; QQQ 20.25%+), a **washout** fires on the first close with any of:
- 30% below the high (QQQ 40.5%);
- 20% below the 200-day average (QQQ 27%);
- VIX at 35 or above.

One signal per 126 sessions.

### Results

| | S&P 2010–2026 | S&P 1962–2009 | QQQ 2010–2026 | QQQ 1987–2009 |
|---|---|---|---|---|
| Signals | 4 | 11 | 3 | 10 |
| Further fall after the signal (median / worst) | **−1.8% / −19%** | −3.8% / −41% | **−1.8% / −4%** | −19% / −60% |
| Within 5% of the final low | 75% | 64% | 100% | 40% |
| Days below the entry price over the next year (median) | 2 | 6 | 1 | 126 |
| Return after 3 / 6 / 12 months | +18% / +25% / +34% | +5% / +12% / +22% | +29% / +42% / +56% | −2% / +11% / +21% |
| Up after 6 months | 100% | 91% | 100% | 50% |

Signals since 2010:
- **S&P:** Aug 2011, Dec 2018, Mar 2020, Apr 2025.
- **QQQ:** Dec 2018, Mar 2020, Apr 2025.

The QQQ failures before 2010 were the dot-com bust: a secular bear market of −83%. **It missed the October 2022 low:** a slow, rate-driven bear market with no washout. The fast-crash override keeps the plan out of that kind of decline as well.

Rejected alternatives:
- **A "thrust" after the washout** (+5–7% in 10–15 days): later and worse.
- **First VIX ≥ 30 or capitulation volume:** too early.

---

## 3. SOXX fast-crash study (flag only, 3 Nov 2026)

SOXX (semiconductors) has been the market's growth leader, so the same framework was tested on it. SOXX moves about 1.44× as much as QQQ each day.

**Inputs:** the capitulation groups use SOXX's own price and volume (stretch; capitulation volume on a 2.9%+ down day; oversold), plus the market-wide groups (put/call, VXN/VIX9D, dealer gamma). The override is the same.

**Two versions:**

| | A: fall from the 1-year high | **B: fall from the 3-month high (preferred)** |
|---|---|---|
| Crash definition | −11.5% in 15 sessions, from near the 1-year high | the same fall, from near the 3-month high |
| Crashes 2007–2026 | 16 (only 4 before 2016) | 25 |
| Buys (skipped by the override) | 14 (2) | 20 (5) |
| Buy 1 depth | −12% from the high | −12% from the window's high |
| Entries within 5% of the low | 71% | 70% |
| Further fall (median / worst) | −1.6% / −19% | −1.7% / −19% |
| Return after 3 / 6 months | +16.1% / +24.8% | **+18.3% / +27.2%** |
| Up after 3 months | 93% | **95%** (2016–26: 100%) |
| Days until back above entry (median) | ~104 | **~29** |

- Version A misses second-leg crashes that start below the 1-year high, such as October 2026 (SOXX went from −10% to −28%).
- Version B was chosen after seeing A, so it is partly in-sample.
- A depth scaled by volatility (−15% or more) missed half the crashes.

**Now (3 Nov 2026):** under version B, a crash started on 30 Sep. Buy 1 came on 15 Oct and buy 2 on 22 Oct. SOXX was about 8% below the averaged entry; the low is not yet known.

**Status:** research only. If added, it would be a display-only flag on the Risk radar, not part of any system.

---

## 4. Method and limits

- **Data:** QQQ and S&P 500 daily prices and volume (Yahoo); Cboe put/call ratios (archive to 2019 plus daily reports); Cboe VIX, VIX9D and VXN; SqueezeMetrics GEX; and the platform's late-cycle radar for the override.
- **Thresholds:** fixed, or measured against each indicator's own past year, using only data known on the day.
- **Eras:** results are shown separately for older years and the options-heavy era.
- **Samples are small:** 19 QQQ fast crashes and a handful of bear markets. Treat the numbers as a tilt in the odds, not a guarantee.
- **Scripts:** research/bottom-signals/ (copies). Platform code: signals/bottoms.py, which reproduces the research buy dates exactly.
