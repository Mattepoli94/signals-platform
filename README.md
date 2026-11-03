# Poli's Hedge Fund

A personal trading and investing dashboard (repository `signals-platform`, Python package `signals`). It runs three research-tested systems, tracks a GBP pot for each, shows early-warning and bottom signals, and publishes everything on Vercel. Email alerts are built in but switched off for now. It sends signals only: no orders go to any broker.

Live rules (v2.0 platform): Nasdaq trading system v1.1 · Nasdaq value plan v1.2 · BTC cycle trend system v2 · Risk radar v1 · Bottom signals v1. Every rule change is logged on the Research page.

| Page | What it shows |
|---|---|
| **Today** | The action for each pot (BUY / SELL / HOLD / WAIT) with stops and exit dates, the order cut-off time, radar and bottom-signal pills, fills waiting to be recorded, total P&L, recent signals and the daily routine |
| **Investing** | The Nasdaq-100 value plan (buys EQQQ): live checklist for both value zones and the fast-crash buys, what a buy would invest, the pot's P&L, the plan vs QQQ buy & hold with the same deposits, and a QQQ chart with value levels |
| **Trading** | The Nasdaq-100 regime system (EQQQ + dollar add-on) and the BTC cycle trend system. Under each system, a *Live vs expected* chart: the pot's return against the 80% range its backtest produced over the same number of sessions, with EQQQ/BTC as a grey line and flags when return or drawdown leave the backtest range. Also: every rule with its live value, entry/stop/take-profit/time exits, each pot and its chart, trades, signal history, and live-vs-backtest health |
| **Risk radar** | Three predictive warning flags (late cycle, Nasdaq crash risk, BTC leverage) and two bottom signals (QQQ fast-crash plan, bear-market washout), each with its backtested track record and a live track record from 2 Nov 2026. Display only |
| **Journal** | Every order the systems suggested, written once when first shown (preview at 16:05, then confirmed or cancelled by the close), with your real fill next to it, and the system's ideal result against yours (execution decay) |
| **Portfolio** | All pots, top-ups, deposit history and every trade by pot (fills can be recorded here too) |
| **Research** | One paper per system with the exact rules and test results |
| **Settings** | Initial capital, monthly top-up, fees and cash interest per pot, start date, status of every data feed (systems and radar) and CSV upload |

## How it works

```
GitHub Actions (free, on a schedule)
  └─ download prices (Yahoo)  →  data/prices/*.csv
  └─ radar inputs (Cboe, SqueezeMetrics, FINRA, multpl, Yahoo, Deribit, CFTC)  →  data/radar/*.csv   [US and BTC runs]
  └─ compute signals (signals/strategies/*)            same code as the research
  └─ replay each pot from its start date (signals/ledger.py), with and without your fills
  └─ risk radar + bottom signals (signals/radar.py, signals/bottoms.py); live track record (signals/radar_track.py)
  └─ signal journal (signals/journal.py)
  └─ email alerts (ready, switched off for now)
  └─ build the website (site/ → public/)  →  Vercel serves public/
```

The pots are **rebuilt from scratch on every run** from three inputs: the prices, the system's rules and your settings in `config/portfolio.yaml` (capital, top-ups, recorded fills). So when the systems buy or sell, receive dividends or earn interest, or when you add a top-up, every pot updates by itself.

### Pots

| Pot | System | Default capital |
|---|---|---|
| `qqq_value` | Nasdaq-100 value plan: zones on QQQ, buys EQQQ in your **ISA** | £1,000 |
| `qqq_trading` | Nasdaq-100 regime system on EQQQ (**ISA**) + USD cash add-on (**Invest** account) | £500 |
| `btc_trend` | BTC cycle trend system (v2) | £500 |

- **Initial capital** is deposited at the start date (`start_date`, default 3 Nov 2026). At its first close, each pot joins its system's current position.
- **Top-ups** go into a pot's cash at the close of their date (Portfolio page, or the box on each pot). An optional **monthly top-up** per pot is added on the first trading day of each month.
- **Trades** happen at the close. EQQQ is priced in pence, so it needs no conversion. USD cash and BTC are valued with that day's GBP/USD.
- **Fees** (editable in Settings): 0.05% on EQQQ trades (the spread; no FX fee in pence); 0.15% on each GBP↔USD conversion for the dollar add-on (Trading 212); 0.40% for BTC (Kraken Pro limit orders).
- **Dividends:** EQQQ's small dividends are not in Yahoo's price series, so the pots slightly understate them. **Interest on cash** is optional (Settings).
- **Your real fills.** Each model trade has an id. Record your real price (and optionally the GBP/USD rate and fee) in the Journal, and the pot is re-valued with it. The Journal also keeps the ideal pot (model fills) so you can see execution decay.

## Schedule (all automatic)

| When (UK time) | Run | Email (when switched on) |
|---|---|---|
| ~16:05 | London pre-close preview on the live EQQQ price | "ACTION before 16:25" if an EQQQ or USD order is likely, or a value-plan buy is due |
| ~16:55 (and a backup run an hour later) | After the London close | Confirmed EQQQ / USD trades |
| ~21:20 (and 22:20 backup) | After the US close | Value-plan buy for the next London close; daily summary |
| ~00:20 | After the BTC daily close | New BTC trades |
| On every push of code or settings | Full run | — |

GitHub can start scheduled runs 5–30 minutes late at busy times. If the site has not updated by 16:15, press **Refresh data**. Every run writes `state/last_run.json`; a failed run writes `state/last_error.log`.

## Hosting on Vercel (free Hobby plan)

GitHub Actions builds the website on every run and commits it to `public/`. Vercel serves that folder as a static site; `vercel.json` disables any build step. Every push (about 8 a day) triggers a new deployment, well within the Hobby limit.

One-time setup (about 3 minutes):

1. [vercel.com/new](https://vercel.com/new) → **Continue with GitHub** → import **signals-platform**. If it isn't listed, use *Adjust GitHub App Permissions* to give Vercel access to the repo.
2. Framework preset: **Other**. Leave the build and output settings as they are (`vercel.json` sets them) → **Deploy**.
3. **Recommended: password.** Project → Settings → Environment Variables → add `SITE_PASSWORD` (and optionally `SITE_USER`, default `me`) → redeploy. `middleware.js` then asks for that login. Without it, anyone with the link can see your pots. Alternatively, turn on Vercel Authentication for all deployments under Settings → Deployment Protection.
4. **Edit from the website** (top-ups, capital, fills). Open Settings on the site and paste a [fine-grained GitHub token](https://github.com/settings/personal-access-tokens/new) limited to this repository, with *Contents: read and write* and *Actions: read and write*. The token is stored only in that browser. Edits run the *manage* workflow, which rebuilds the site; Vercel republishes it in about 2–3 minutes.

## Other ways to run it

- **On your computer.** Install Python 3.11+, then run:
  ```
  git clone https://github.com/Mattepoli94/signals-platform && cd signals-platform
  pip install -r requirements.txt
  python -m signals run --mode us --no-email   # download data + build
  python -m signals serve                      # opens http://localhost:8000
  ```
  Edits save straight to `config/portfolio.yaml`. Commit and push them so the scheduled runs use them.
- **Runs.** They happen on the schedule and on every push of code or settings. You can also start one from Actions → *Signals (scheduled)* → **Run workflow**. GitHub Actions needs *Read and write permissions* (Settings → Actions → General); it is already working on this repo.

## Email alerts (later)

The code is ready but switched off (`alerts.email_enabled: false`). To turn it on, add these repository secrets: `SMTP_HOST` (e.g. `smtp.gmail.com`), `SMTP_PORT` (`587`), `SMTP_USER`, `SMTP_PASSWORD` (a Gmail app password) and `ALERT_TO`. Then set `email_enabled: true`.

## Command line

```
python -m signals run --mode preclose|close|us|btc|build [--no-fetch] [--no-email] [--force]
python -m signals op '{"op":"add_topup","pot":"qqq_value","amount":500,"date":"2026-12-01","note":"Dec"}'
python -m signals op '{"op":"set_pot","pot":"btc_trend","initial_capital":750}'
python -m signals op '{"op":"set_fill","trade_id":"qqq_trading-2026-11-03-QQQ-BUY","price":691.20,"fx":1.305}'
python -m signals import QQQ ~/Downloads/QQQ.csv
python -m signals serve
pytest -q
```

## Data

Data is free and daily. System prices come from Yahoo Finance (EQQQ.L, QQQ, UUP, BTC-USD, GBPUSD=X). Yahoo's London ETF history has bad prints, such as whole weeks quoted in US cents. EQQQ is repaired against QQQ ÷ GBP/USD whenever it is loaded. If Yahoo fails, GBP/USD falls back to FRED (FRED is often unreachable from GitHub's runners, so upload a CSV if both fail). The radar inputs are listed in Settings → Data with their latest date. Any system price feed can be replaced by uploading a CSV (Settings → Data). Yahoo, Investing.com, Nasdaq.com and FRED exports are accepted. Only completed daily closes are stored; a bar still forming is used only for the pre-close preview. To move to a paid live feed later, add a fetcher in `signals/data.py`.

## Extending

- **New market:** add an `Asset` in `signals/assets.py`.
- **New strategy:** subclass `Strategy` (`signals/strategies/base.py`), implement `compute()` (daily table with `w_<ASSET>` + `state`, or `zone` for accumulation) and `status()` (checklist, action, orders). Register it in `signals/strategies/__init__.py` and add a pot that uses it in `config/portfolio.yaml`. The ledger, alerts and pages pick it up.

## Important

- **Display-only signals.** The Risk radar and bottom signals never change the trading system's orders. The value plan does use the fast-crash buys (v1.2).
- **Fees and the UK route (v1.1).** The Nasdaq system trades its pot about 15–22 times a year. Trading 212's 0.15% currency fee would cost several percent a year on USD-quoted funds, so v1.1 trades EQQQ (pence) in the ISA at the London close, with no FX fee. Tested 2010–2024: 9.0% a year, worst drawdown −14.1% (with the dollar add-on, cash 0%). QQQ and UUP are used only as signals.
- **Timing.** Yahoo's London prices can be about 15 minutes delayed. The 16:05 preview uses them; the 16:55 run confirms with the official close.
- **Data source.** The rules were validated on adjusted closes. Yahoo data is unofficial and can occasionally be wrong or late, so the freshness bar flags stale feeds.
- Backtested results do not guarantee future results. This is not financial advice.
