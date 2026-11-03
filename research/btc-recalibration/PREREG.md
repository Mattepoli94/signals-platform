# BTC recalibration — pre-registered design (written 2026-11-03 01:50 UTC, before any test is run)

Goal: re-fit the BTC long/flat system on training years only and judge it once on held-out years,
with the same discipline as the QQQ system.

Honest caveat: every year 2012–2026 was already looked at in the earlier BTC research, so the holdout
is clean only against this new search, not against my prior knowledge. To limit that, the search space,
the selection rules and the adoption rule are fixed below before any result is seen.

## Data and simulation
- Price: Coin Metrics daily BTC/USD (00:00 UTC close), 2011-01 → 2026-10-31. Signals point-in-time.
- Position decided at close t, held to close t+1. Long/flat, weight 0–1. Cost 10 bp per unit traded.
  Idle cash earns the 3-month T-bill. Returns measured in USD.
- 2011 is excluded from training and holdout (illiquid, Mt Gox era); used for indicator warm-up only.

## Holdout years (stratified random)
- Pool: calendar years 2012–2026 (2026 = Jan–Oct). Rank by BTC buy-and-hold return; split into
  terciles (bear / middle / bull, 5 years each). Draw ONE year from each tercile with
  numpy.random.default_rng(20261103). Those 3 years are the holdout; the other 12 train.
- Holdout results are computed ONCE, after the final system is fixed.

## Search space (training years only)
Stage 1 — trend core (full size, no filters), 26 rules:
- momentum: close > close n days ago, n ∈ {10, 20, 30, 50, 100, 150, 200}
- close > EMA n, n ∈ {20, 30, 50, 75, 100, 150, 200}
- close > SMA n, n ∈ {20, 30, 50, 75, 100, 150, 200}
- EMA cross fast/slow: (10,30), (20,50), (20,100), (50,200)
- blends: momentum vote 10/20/50 (graded); the v1 five-signal blend (graded)
Stage 2 — volatility sizing: x min(1, target / 30-day realised vol), target ∈ {none, 60%, 80%, 100%, 120%}
Stage 3 — halving window (flat a..b days after each halving): none, or a ∈ {365, 450, 545, 640} × b ∈ {730, 820, 910, 1000}

## Selection rules
- Objective: training Calmar (CAGR / |MaxDD|) on concatenated training-year returns.
- Stage 1: choose the FAMILY with the best median Calmar across its lengths (blends count as a family
  of their own); within it, choose the length with the best 3-point neighbourhood average (plateau
  centre), not the single best point.
- Stage 2: keep vol sizing only if it improves BOTH training Calmar and training MaxDD; choose the
  plateau centre among targets.
- Stage 3: keep the halving window only if it raises training Calmar by ≥ 20% AND does not lower
  Calmar in any of the training halving cycles (2012-11→2016-07, 2016-07→2020-05, 2020-05→2024-04,
  2024-04→2026-10) in which it is active; choose the plateau centre of the (a, b) grid.
- Ties within 10% of Calmar → choose the simpler rule.

## Adoption rule (decided now)
- Adopt the new system if, on the holdout years, it has positive CAGR and a smaller MaxDD than
  buy-and-hold, AND its holdout Calmar is not more than 50% below its training Calmar.
- Otherwise: report the failure, keep the simplest trend core with no extra filters, and size the
  BTC pot expectation from the holdout, not the training, figures.
- In both cases the platform's "expected" cone will use the full 2012–2026 backtest of the adopted
  rules (training + holdout), not the training years alone.
