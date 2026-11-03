# Risk radar (v1, live from 3 November 2026)

Three early-warning flags, shown on the **Risk radar** page. They are display only: no order on the platform depends on them. The trading systems already step out of falling markets through their own trend rules, and every test of "sell when the flag is on" lowered returns (section 6).

The radar answers one question: **is the market set up for trouble before the trouble starts?** Indicators that only light up once prices are already falling were tested and dropped.

| Radar | Market | Predicts | Main result |
|---|---|---|---|
| **Late cycle** | S&P 500 / whole market | A bear market (fall of 19%+) starting within ~12 months | 2+ signs: **2.0× the odds**, both in the years used to choose it and in the years after |
| **Nasdaq crash risk** | Nasdaq-100, near its high | A fall of 8%+ within 3 weeks | 2+ families: **1.9× the odds**; stricter estimate ~1.4× |
| **BTC leverage** | Bitcoin | A fall of 15%+ within 10 days | 2+ signs: **3.4× the odds**; 1 sign: 1.7× |

**How to read "2.0× the odds".** On the days the flag was on, the bad outcome followed about twice as often as on an average day in the same conditions. It is a tilt in the odds, not a forecast. Most "on" days are still followed by no crash.

---

## 1. Late-cycle radar

### Rules

Checked daily on S&P 500 data. One point per sign:

| Sign | On when | Source |
|---|---|---|
| Yield curve flat | 10-year Treasury yield minus 3-month T-bill yield below +0.50 pt | Yahoo ^TNX, ^IRX |
| Valuation stretched | Shiller CAPE above the 90th percentile of all monthly CAPE readings since 1953 up to that month | multpl.com (Shiller data) |
| Overextended rally | S&P 500 up 50% or more over 504 sessions (~2 years) | Yahoo ^GSPC |
| Rate or inflation pressure | 10-year yield up 1.5 pt or more in 252 sessions, **or** CPI inflation above 4% and higher than 6 months earlier | Yahoo, multpl.com |
| Leverage surge | FINRA margin debt up 30% or more year on year | FINRA |

**Amber at 2 signs, red at 3.** Monthly data is used only from the date it would have been published (CAPE at month end, CPI mid next month, margin debt ~3 weeks after month end).

### How it was tested

- **Events:** every S&P 500 peak at a 1-year high followed by a fall of 19% or more: 1957, 1961, 1966, 1969, 1973, 1980, 1987, 1990, 1998, 2000, 2007, 2011, 2018, 2020, 2022 (15 peaks).
- **Days scored:** only days when the S&P was within 5% of its 1-year high, since an early warning is only useful then. A day counts as "positive" if a bear-market peak followed within 252 sessions. About 25–28% of such days were positive.
- **Split:** signs chosen on **1955–1994**, then checked unchanged on **1995–2026**.
- **Data:** S&P 500 from 1953, yields from 1962, Shiller CAPE and CPI, FINRA margin debt from 1997, plus about 25 other candidate signs (section 5).

### Results

**Single signs** (odds multiplier when on: 1955–94 / 1995–2026):

| Sign | 1955–94 | 1995–2026 |
|---|---|---|
| Yield curve flat (< 0.5 pt) | 2.1× | 1.3× |
| Yield curve inverted at some point in the last 18 months | 1.2× | 1.6× |
| CAPE in the top 10% of history | 1.5× | 1.8× |
| S&P +50% in 2 years | 1.4× | 1.9× |
| 10-year yield +1.5 pt in a year | 1.8× | 1.8× |
| CPI > 4% and rising | 1.5× | 2.1× |
| Margin debt +30% y/y (data from 1997) | – | 1.9× (5 of 7 peaks) |

**Combined (the radar):**

| Version | Period | Time on (near-high days) | Odds multiplier | Peaks flagged in the 6 months before |
|---|---|---|---|---|
| 4 signs (no margin debt), 2+ on | 1955–94 | 17% | **1.97×** | 4 of 7 |
| 4 signs (no margin debt), 2+ on | 1995–2026 | 24% | **2.00×** | 4 of 7 |
| 5 signs (with margin debt), 2+ on | 1995–2026 | 25% | **2.19×** | 6 of 7 |
| 5 signs, 3+ on | 1995–2026 | 11% | 2.06× | 3 of 7 |
| 4 signs, 1+ on | 1955–2026 | 47–61% | ~1.5× | 13 of 14 |

**Lead time.** When it fired, the first 2-sign warning came:

| First warning | Peak |
|---|---|
| Feb 1965 | Feb 1966 |
| Apr 1968 | May 1969 |
| Nov 1979 | Nov 1980 |
| Aug 1987 | Aug 1987 (2 weeks) |
| Jul 1989 | Jul 1990 |
| Jul 1997 | Jul 1998 |
| Mar 1999 | Mar 2000 |
| Jan 2018 | Sep 2018 |
| Mar 2019 | Feb 2020 |
| Jan 2021 | Jan 2022 |

**Missed:** 1961, 1973, 2007 (a credit-driven top), 2011.

### Signs that failed

These were tested and failed in one or both periods:
- **Fed hiking** (T-bill +1.5 pt in a year): 0.75× then 0.0×.
- **Low VIX** (complacency).
- **Strong dollar.**
- **Earnings yield below the 10-year yield.**
- **Momentum fading at highs.**
- **Small caps, transports or credit lagging the index:** on so often that they carried no information (~1.0×).

---

## 2. Nasdaq crash-risk radar

### Rules

Checked daily, and **active only while QQQ is within 4% of its 1-year high**. Otherwise it shows *Idle*. One point per family:

| Family | On when | Source |
|---|---|---|
| Narrow market | Equal-weight Nasdaq-100 (QQEW) lagging QQQ by 3%+ over 63 sessions while near the high, **or** the Cboe S&P 500 Dispersion Index (DSPX, 5-day mean) in the top 10% of the last 2 years | Yahoo, Cboe |
| Options complacency | Cboe total put/call ratio (10-day mean) in the bottom 10% of the last 2 years | Cboe |
| Nasdaq fear premium | Nasdaq VIX ÷ S&P VIX (VXN/VIX, 5-day mean) in the top 10% of the last 2 years | Cboe |
| Leverage surge | FINRA margin debt up 30%+ year on year | FINRA |

**Amber at 2 families, red at 3.** "Top/bottom 10% of the last 2 years" compares today with the previous 503 sessions only, so nothing is fitted and nothing looks ahead.

### How it was tested

- **Events:** the Nasdaq-100 falling 8% or more within 15 sessions, starting within 4% of its 1-year high: 21 events, 2007–2026.
  - 2007 Oct; 2010 Jan, Apr; 2011 Jul, Nov; 2012 Apr; 2015 Jul, Dec; 2018 Jan, Mar, Sep; 2019 May; 2020 Feb, Aug, Oct; 2021 Feb, Dec; 2024 Jul; 2025 Feb; 2026 Jul, Oct.
- **Base rate:** 5.1% of near-high days were followed by such a fall.
- **All years are test years.** The market's mechanics have changed (options volume, zero-day options, passive flows), so instead of one early training period every sign was scored in five separate blocks: 2006–10, 2011–15, 2016–19, 2020–22, 2023–26. A sign was kept only if it helped in most blocks.
- **Stricter check:** the selection was repeated five times, each time choosing on four blocks and testing on the fifth.

### Results

**Single signs** (odds multiplier by block; "–" = no events or too few days on):

| Sign | 06–10 | 11–15 | 16–19 | 20–22 | 23–26 | All years | Events with sign on in the month before |
|---|---|---|---|---|---|---|---|
| Dispersion high (DSPX, from 2014) | – | – | 14.7× | 4.5× | 2.3× | **2.9×** | 5/15 |
| Narrow leadership (QQEW vs QQQ) | 11.4× | 1.6× | 3.1× | 2.4× | 0.5× | **1.8×** | 15/21 |
| Options complacency (low put/call) | 2.3× | 0.0× | 1.8× | 1.3× | 3.1× | **1.65×** | 10/20 |
| Nasdaq fear premium (VXN/VIX) | – | 2.7× | 1.0× | 2.6× | 2.2× | **1.7×** | 5/18 |
| Margin debt +30% y/y | 3.0× | 2.6× | – | 0.4× | 1.5× | **1.75×** | 8/21 |

**Combined (the radar):**

| Families on | 11–15 | 16–19 | 20–22 | 23–26 | All years |
|---|---|---|---|---|---|
| **2 or more** | 1.7× | 4.0× | 1.3× | 1.6× | **1.9×**, on 19% of near-high days |
| 3 or more | – | – | – | 3.7× | 3.9×, on 3% |

- **Also by event:** 2 or more families were on in the 20 sessions before **14 of the 21** fast falls.
- **10% fall within 2 months:** this happened after **19%** of days with 2+ families on, against **10%** normally.
- **Stricter check** (signs chosen without the test block): about **1.4×**. Treat **1.4–1.9×** as the realistic range.
- **Recent example:** the radar showed 2 families (options complacency plus leverage) on **30 September – 2 October 2026**, just before the 6 October peak. The Nasdaq then fell about 10%.

### Signs that failed

These failed when scored across the blocks:
- **Dealer gamma (GEX)** and **dark-pool buying (DIX)**, from SqueezeMetrics. Both worked well in 2016–22 and failed in other years.
- **SKEW.**
- **CFTC futures positioning:** asset managers crowded long, leveraged funds long or short, VIX-futures shorts.
- **Implied correlation.**
- **VVIX/VIX ratio.**
- **Index put/call.**
- **CNN Fear & Greed** (only from 2021).

**Low VIX lowers** the odds of a fast fall: about 0.4×.

---

## 3. BTC leverage radar

### Rules

Checked daily after the 00:00 UTC close. One point per sign:

| Sign | On when | Source |
|---|---|---|
| Funding rate high | Deribit BTC perpetual funding, 7-day mean, above 30% a year | Deribit |
| Hedge funds crowded on CME | Leveraged funds' net CME bitcoin futures position (as a share of open interest) in the bottom 10% of the last 2 years. This is crowded short: the leveraged cash-and-carry trade. | CFTC (weekly, used 4 days after the Tuesday it describes) |
| Fast run-up | BTC up 40%+ in 30 days | Yahoo |

**Amber at 1 sign, red at 2.**

### How it was tested

- **Events:** BTC falling 15% or more within 10 days, starting within 10% of its 60-day high. There were 16 events from 2019 to 2026.
- **Base rate:** 4.0% of such days.
- **Split:** all years are test years. Results are also shown for 2019–22 and 2023–26 separately.

### Results

| Sign | 2019–22 | 2023–26 | All |
|---|---|---|---|
| Funding > 30% a year | 1.7× | 1.6× | **2.9×** |
| Hedge funds crowded short on CME | 1.3× | 3.1× | **2.1×** |
| BTC +40% in 30 days | 1.7× | 1.9× | **2.7×** |
| **1+ sign** | 1.1× | 2.6× | **1.7×**, on 28%, 9 of 16 events |
| **2+ signs** | 1.9× | 2.7× | **3.4×**, on 8%, 4 of 16 events |

- **Before 10 October 2025:** Deribit funding rose from 5% to 20% a year in the week before the $19bn liquidation day. That stayed below the 30% trigger.
- **What changed after 2021:** in 2015–2020, crashes followed parabolic runs (BTC at 2× its 200-day average: 3.4×). Since 2021 that sign has had no power, and leverage and the macro risk mood matter more.

---

## 4. Indicators dropped from the platform

**The old 3-point risk flag on the Nasdaq system** has been retired. Its parts were:
- W1: T-bill +0.5 pt in 6 months;
- W2: dollar +5% in 6 months;
- W3: two of QQQ, TLT or GLD below their 200-day averages.

Its useful part is coincident: it marks markets that are already under stress. It is not predictive, and acting on it never improved results.

**Stress gauges** were also dropped:
- MOVE above 120;
- VIX above VIX3M;
- VVIX above 100;
- credit spreads widening;
- the Nasdaq below its 200-day average.

These raise the odds of a further fast fall by 2–3×, but only once the market is already falling. In October 2026 they turned red when the Nasdaq was already 10% down. After a red stress reading the average return over the next 3 months was the same as any other day, because rebounds are strong too.

## 5. Everything that was tested

- **Macro and rates:**
  - yield curve (inverted, flat, inverted in the last 18 months);
  - Fed hikes;
  - 10-year yield jumps;
  - real T-bill rate;
  - inflation;
  - dollar.
- **Valuation:** CAPE level and percentile; earnings yield vs bonds.
- **Price:** 12-month and 24-month gains; distance from the 200-day average; fading momentum.
- **Internals:**
  - small caps vs large;
  - Dow transports vs industrials;
  - high-yield vs Treasuries;
  - equal-weight vs cap-weight;
  - staples vs discretionary.
- **Volatility:** VIX level and rises at highs; VIX9D/VIX; VIX term structure; VVIX; SKEW; MOVE; VXN/VIX.
- **Options:**
  - Cboe total, equity, index and SPX put/call ratios (2006–2026);
  - dealer gamma (GEX) and dark-pool index (DIX), 2011+;
  - dispersion (DSPX) and implied correlation (COR1M, COR3M).
- **Positioning:** CFTC asset managers and leveraged funds in S&P, Nasdaq and VIX futures (2006–2026); CME bitcoin.
- **Leverage:** FINRA margin debt; Deribit funding.
- **Sentiment:** CNN Fear & Greed.
- **Not available free:** AAII sentiment, NAAIM exposure, Fed (FRED) series and BitMEX funding were blocked or unavailable.

## 6. Acting on the flags: why the radar is display only

Tested on the live systems' signal tables:

- **Nasdaq trading system 2010–2026:**
  - as it is: 8.5% a year, −14.1% worst fall;
  - halving exposure when the macro score was 2+: 8.0% / −14.3%;
  - going to cash: 7.5% / −16.3%.
- **Stopping the Nasdaq dip buys in stressed markets, 2007–2026:**
  - as it is: 9.6% / −13.7%;
  - half-size dips: 8.3% / −12.9%;
  - no dips: 6.9% / −14.4%.

  Dips bought in nervous markets earned more on average (+0.96% a trade vs +0.53%).
- **BTC system 2015–2026:** halving exposure on the macro score took 84.8% / −33.6% down to 83.3% / −34.7%.

The trend rules already exit most of the falls the flags warn about. Selling earlier mostly misses rebounds.

## 7. Limits

- **Few events.** 15 bear markets since 1955, 21 Nasdaq fast falls since 2006 and 16 BTC crashes since 2019. Any multiplier carries wide error bands.
- **Mechanisms change.** Options and positioning signs worked best in 2016–22. Narrow leadership has been near-permanent since 2023 (mega-cap dominance). The radar should be re-scored once a year.
- **Some crashes need a trigger** (a virus, a tariff announcement, a forced unwind) that no indicator can forecast.
- **Data breaks.** Cboe's put/call archive (to 2019) and daily reports (from October 2019) are joined. CAPE comes from multpl.com; the research used Shiller's own file (98% agreement on the flag).

## 8. Data and code

- **Platform module:** `signals/radar.py`. Inputs are stored in `data/radar/` and refreshed after the US close and the BTC close.
- **Research scripts:** `research/risk-radar/` (copies of the analysis scripts).
- **Check against the research:** the platform reproduces the research flags on 98–100% of days.
