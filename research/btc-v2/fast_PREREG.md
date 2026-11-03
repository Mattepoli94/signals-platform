# BTC faster trend + cycle window — v3 design (2026-11-03 10:05 UTC, before tests)
User brief: worst fall of -67% is unacceptable; faster trend following with more in/out, SMA and EMA,
daily and weekly, crossover entries and close-below-slow-MA exits, coupled with the cycle window.
- Same data, costs (0.40%/side), holdout years (2012, 2016, 2018) and walk-forward reporting as v2.
- Grid: timeframe {daily, weekly, weekly MAs with daily exits} x MA type {SMA, EMA} x entry {fast>slow cross,
  close>fast MA} x exit {fast<slow, close<slow MA, close<fast MA} x (fast, slow) pairs
  daily (10,20,30,50) x (50,100,150,200); weekly (5,10,13,20) x (20,30,40,50).
- Cycle window: fixed knowledge window, flat from day 540 to 900 after each halving (also shown without).
- Selection on training years only: highest training Calmar among rules whose 4 nearest (fast/slow) neighbours
  average within 15% of it (plateau), with training MaxDD reported both with and without the April 2013 crash.
- Target stated by user: much smaller drawdown than -67%. Adoption: holdout Calmar >= 50% of training,
  holdout and 2016-26 worst fall clearly better than v2-D, and Calmar 2016-26 above buy & hold.
- ~400 variants are tested: expect in-sample optimism; judge on holdout + 2016-26 consistency.
