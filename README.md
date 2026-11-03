# Signals platform

A personal trading and investing dashboard that runs three research-tested systems, tracks a GBP pot for each, and emails you when a signal fires. It sends signals only: no orders go to any broker.

| Page | What it shows |
|---|---|
| **Today** | The action for each pot (BUY / SELL / HOLD / WAIT) with stops and exit dates, the order cut-off time, total P&L and recent signals |
| **Investing** | The QQQ value plan: live checklist for both value zones, what a buy would invest, the pot's P&L, the plan vs QQQ buy & hold with the same deposits, and a QQQ chart with value levels |
| **Trading** | The QQQ regime system (+ dollar add-on) and the BTC trend blend: every rule with its live value, entry/stop/take-profit/time exits, the risk flag, each pot and its chart, trades, signal history, and live-vs-backtest health |
| **Portfolio** | All pots, total value chart, top-ups, deposit history and the trade journal (record your real fills) |
| **Research** | One paper per system with the exact rules and test results |
| **Settings** | Initial capital, monthly top-up, fees and cash interest per pot, start date, email alerts, data status and CSV upload |

## How it works

```
GitHub Actions (free, on a schedule)
  └─ download prices (Yahoo, FRED)  →  data/prices/*.csv
  └─ compute signals (signals/strategies/*)            same code as the research
  └─ replay each pot from its start date (signals/ledger.py)
  └─ email alerts (only once per signal)
  └─ build the website (site/)  →  GitHub Pages, or run it on your computer
```

The pots are **rebuilt from scratch on every run** from three inputs: the prices, the system's rules and your settings in `config/portfolio.yaml` (capital, top-ups, recorded fills). So when the systems buy or sell, receive dividends or earn interest, or when you add a top-up, every pot updates by itself.

### Pots

| Pot | System | Default capital |
|---|---|---|
| `qqq_value` | QQQ value plan | £1,000 |
| `qqq_trading` | QQQ regime system + dollar add-on | £500 |
| `btc_trend` | BTC trend blend | £500 |

- **Initial capital** is deposited at the start date (`start_date`, default 3 Nov 2026). At its first close, each pot joins its system's current position.
- **Top-ups** go into a pot's cash at the close of their date (Portfolio page, or the box on each pot). An optional **monthly top-up** per pot is added on the first trading day of each month.
- **Trades** happen at the close, in USD, converted at that day's GBP/USD. The **fee** per trade defaults to 0.15% for QQQ (the Trading 212 FX fee) and 0.10% for BTC. Change both in Settings.
- **Dividends** (QQQ, UUP) are credited after 15% US withholding tax. **Interest on cash** is optional (Settings).
- **Your real fills.** Each model trade has an id. Record your real price (and optionally the GBP/USD rate and fee) in the trade journal, and the pot is re-valued with it.

## Schedule (all automatic)

| When (UK time) | Run | Email |
|---|---|---|
| ~20:25 (19:25 in the few weeks when US/UK clocks differ) | Pre-close preview on the live QQQ price | "ACTION before the US close" if a QQQ order is likely |
| ~21:20 and 22:20 (backup) | After the US close | New confirmed trades, plus the daily summary |
| ~00:20 | After the BTC daily close | New BTC trades |

GitHub can start scheduled runs 5–30 minutes late at busy times. If the pre-close email has not arrived by the cut-off shown on the Today page, open the site and press **Refresh data**.

## One-time setup (about 10 minutes)

1. **Let the workflows save data.** Repository → Settings → Actions → General → *Workflow permissions* → **Read and write permissions** → Save.
2. **Email alerts** (Gmail example). Create an [app password](https://myaccount.google.com/apppasswords) (it needs 2-step verification). Then go to Repository → Settings → Secrets and variables → Actions → *New repository secret* and add:
   - `SMTP_HOST` = `smtp.gmail.com`
   - `SMTP_PORT` = `587`
   - `SMTP_USER` = your Gmail address
   - `SMTP_PASSWORD` = the app password
   - `ALERT_TO` = where alerts should go
   - optional: `ALERT_FROM`
3. **First run.** Actions → *Signals (scheduled)* → **Run workflow** → mode `close`. This downloads all the data (including GBP/USD, which is not in the repo yet) and builds the site.
4. **See the website.** Pick one:
   - **GitHub Pages (hosted, phone-friendly).** Repository → Settings → Pages → *Source*: **GitHub Actions**. On a free GitHub plan this needs the repository to be **public**. GitHub Pro allows it on a private repo. The site is then at `https://<you>.github.io/signals-platform/`. To edit from the hosted site, open Settings on the site and paste a [fine-grained token](https://github.com/settings/personal-access-tokens/new) limited to this repository, with *Contents: read and write* and *Actions: read and write*. The token is stored only in that browser.
   - **On your computer.** Install Python 3.11+, then run:
     ```
     git clone https://github.com/Mattepoli94/signals-platform && cd signals-platform
     pip install -r requirements.txt
     python -m signals run --mode close --no-email   # download data + build
     python -m signals serve                         # opens http://localhost:8000
     ```
     Edits save straight to `config/portfolio.yaml`. Commit and push them so the scheduled runs use them.
   - **Quick look.** Every run uploads the built site as an artifact (Actions → latest run → *site*). Download it and open `index.html`.

## Command line

```
python -m signals run --mode close|preclose|btc|build [--no-fetch] [--no-email] [--force]
python -m signals op '{"op":"add_topup","pot":"qqq_value","amount":500,"date":"2026-12-01","note":"Dec"}'
python -m signals op '{"op":"set_pot","pot":"btc_trend","initial_capital":750}'
python -m signals op '{"op":"set_fill","trade_id":"qqq_trading-2026-11-03-QQQ-BUY","price":691.20,"fx":1.305}'
python -m signals import QQQ ~/Downloads/QQQ.csv
python -m signals serve
pytest -q
```

## Data

Data is free and daily. Prices come from Yahoo Finance (QQQ, UUP, BTC-USD, TLT, GLD, ^IRX, DX-Y.NYB, GBPUSD=X). Fed net liquidity (WALCL − WTREGEN − RRPONTSYD) comes from FRED. If Yahoo fails, GBP/USD and the T-bill fall back to FRED. Any feed can be replaced by uploading a CSV (Settings → Data). Yahoo, Investing.com, Nasdaq.com and FRED exports are accepted. Only completed daily closes are stored; a bar still forming is used only for the pre-close preview. To move to a paid live feed later, add a fetcher in `signals/data.py`.

## Extending

- **New market:** add an `Asset` in `signals/assets.py`.
- **New strategy:** subclass `Strategy` (`signals/strategies/base.py`), implement `compute()` (daily table with `w_<ASSET>` + `state`, or `zone` for accumulation) and `status()` (checklist, action, orders). Register it in `signals/strategies/__init__.py` and add a pot that uses it in `config/portfolio.yaml`. The ledger, alerts and pages pick it up.

## Important

- **Fees.** The QQQ system trades often (about 70 trades a year including the dollar add-on). The research assumed 3 bp per trade. At Trading 212's 0.15% FX fee, replaying Jan 2025 – Oct 2026 gives +2.0% instead of +11.7%. The pot shows this honestly. Consider a USD-denominated account or a cheaper route before going live.
- **US ETFs for UK investors.** QQQ and UUP are US-listed and usually not available to UK retail accounts (PRIIPs). Options include a CFD account or a UCITS Nasdaq-100 ETF. A UCITS ETF trades in London hours, so it cannot be bought at the US close, which changes the system. The pots are valued on QQQ/UUP prices.
- **Data source.** The rules were validated on adjusted closes. Yahoo data is unofficial and can occasionally be wrong or late, so the freshness bar flags stale feeds.
- Backtested results do not guarantee future results. This is not financial advice.
