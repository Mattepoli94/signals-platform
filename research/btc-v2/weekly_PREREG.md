# BTC weekly trend + cycle system — pre-registration v2 (2026-11-03 10:05 UTC, before any test)

User hypothesis: weekly closes capture the large BTC trends; a slow/fast EMA trend rule paired with
halving-cycle windows (no-buy / sell periods) adds fundamental knowledge to trend following.

## Data, costs
- Coin Metrics daily BTC/USD 2011-01 → 2026-10-31; weekly close = Sunday's daily close (W-SUN).
- Long/flat, weight 0 or 1 (vol sizing tested as a final optional stage). Idle cash earns the 3m T-bill.
- Costs: base case Kraken Pro limit orders, 0.40% per trade side (Tier 1 maker). Sensitivity: 0.80% (taker),
  and an ETF route (0.05% per side + 0.25%/yr holding fee).

## Validation (unchanged from v1, decided before seeing weekly results)
- Holdout years 2012, 2016, 2018 (the stratified random draw from v1; NOT redrawn, to avoid fishing).
- Walk-forward 2016–2026: the selection procedure re-run on the years before each test year.
- Caveat: 2018 is known (from v1) to be the year where cycle windows matter; holdout is clean only against
  this search, not against prior knowledge.

## Search space (training years only)
Trend core on weekly closes:
- EMA cross fast/slow (weeks): fast ∈ {5, 8, 10, 13, 20}, slow ∈ {20, 26, 30, 40, 50}, fast < slow
- close above weekly EMA n, n ∈ {10, 20, 30, 40, 50}
Execution: E1 weekly (act at the weekly close); E2 entries weekly, exits on a DAILY close below the
slow weekly EMA (faster exit).
Cycle overlay (days since halving d):
- C0 none
- C1 flat (sell) when a < d ≤ b
- C2 no new entries when a < d ≤ b (existing positions exit only on the trend rule)
- a ∈ {450, 500, 550}, b ∈ {850, 900, 950}
- K: a fixed knowledge-based window, chosen from the public cycle narrative rather than fitted:
  sell from 18 months after the halving (d = 540) to 30 months (d = 900). Tested as C1 and C2.

## Selection
- Objective: training Calmar on concatenated training years. Plateau rule: choose the centre of the best
  3x3 (EMA grid) / 3x3 (window grid) neighbourhood, not the single best cell.
- Cycle overlay kept if it raises training Calmar by ≥ 20% AND does not lower Calmar in any training
  halving cycle where it is active. The knowledge window K is reported regardless (it is not fitted).
- Ties within 10% → simpler (E1 over E2, C0 over C2 over C1).

## Adoption
- Adopt if holdout CAGR > 0, holdout MaxDD better than buy & hold, holdout Calmar ≥ 50% of training Calmar,
  AND walk-forward Calmar ≥ buy & hold's walk-forward Calmar.
