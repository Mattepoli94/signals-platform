"""Pot ledger: replays each pot day by day from its start date, following its strategy.

The ledger is rebuilt from scratch on every run from three inputs: stored prices, the strategy's
signal table and your settings (initial capital, monthly and one-off top-ups, recorded fills).
So editing a top-up or a fill always gives a consistent history.

Conventions
  * Pots are in GBP. Assets trade in USD at the day's (unadjusted) close, converted at that day's
    GBP/USD close. Fees are `fee_pct` of the trade value (Trading 212 charges 0.15% FX on USD assets).
  * Dividends: on an ex-date the pot is credited the dividend implied by the adjusted-close series,
    minus 15% US withholding tax (W-8BEN rate).
  * Cash earns `cash_rate_pct` a year, accrued daily.
  * Model trades have ids like  qqq_trading-2026-11-03-QQQ-BUY. Recording a fill with that id
    re-prices the trade at your real execution.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .assets import currency

WHT = 0.15


def gbp_series(a: str, df: pd.DataFrame, fx: pd.Series, cal: pd.DatetimeIndex) -> tuple:
    """(GBP price per unit, native price for display) on the pot calendar."""
    nat = df['close'].reindex(df.index.union(cal)).ffill().reindex(cal)
    f = _fx_on(fx, cal)
    ccy = currency(a)
    if ccy == 'GBX':
        return nat / 100.0, nat
    if ccy == 'USDCASH':                      # df is GBP/USD; one unit = one US dollar
        return 1.0 / nat, nat
    if ccy in ('GBP',):
        return nat, nat
    return nat / f, nat                       # USD-quoted


def native_to_gbp(a: str, price: float, fxrate: float) -> float:
    ccy = currency(a)
    if ccy == 'GBX':
        return price / 100.0
    if ccy == 'USDCASH':
        return 1.0 / price
    if ccy == 'GBP':
        return price
    return price / fxrate


@dataclass
class PotResult:
    key: str
    name: str
    strategy: str
    started: bool
    start: str
    curve: pd.DataFrame
    trades: list
    positions: dict
    cash: float
    deposits: float
    equity: float
    realised: float
    dividends: float
    interest: float
    fees: float
    weights: dict
    bench_equity: float
    cooldown_left: int = 0
    last_buy: str | None = None
    metrics: dict = field(default_factory=dict)
    deposits_log: list = field(default_factory=list)


def _fx_on(fx: pd.Series, idx: pd.DatetimeIndex) -> pd.Series:
    s = fx.dropna()
    return s.reindex(s.index.union(idx)).ffill().bfill().reindex(idx)


def _dividends(df: pd.DataFrame) -> pd.Series:
    """Cash dividend per share on each ex-date, implied by the adjusted/raw close ratio."""
    k = (df['adj_close'] / df['close']).replace([np.inf, -np.inf], np.nan).ffill()
    jump = k / k.shift(1)                         # >1 on an ex-date
    div = df['close'].shift(1) * (1 - 1 / jump)
    return div.where(jump > 1 + 1e-5, 0.0).fillna(0.0)


def run_pot(key: str, cfg: dict, strategy, table: pd.DataFrame, prices: dict, fx: pd.Series,
            start_date: str, topups: list, fills: list, bench_asset: str) -> PotResult:
    start = pd.Timestamp(start_date)
    cal = table.index[table.index >= start]
    name = cfg.get('name', key)
    init = float(cfg.get('initial_capital', 0) or 0)
    monthly = float(cfg.get('monthly_topup', 0) or 0)
    fee_main = float(cfg.get('fee_pct', 0) or 0) / 100
    fee_fx = float(cfg.get('fx_fee_pct', 0.15) if cfg.get('fx_fee_pct') is not None else 0.15) / 100
    fee_of = lambda a: fee_fx if currency(a) == 'USDCASH' else fee_main
    fee = fee_main
    rate = float(cfg.get('cash_rate_pct', 0) or 0) / 100
    my_topups = sorted([t for t in topups if t.get('pot') == key], key=lambda t: str(t['date']))
    fill_map = {f['trade_id']: f for f in fills if f.get('trade_id', '').startswith(key + '-')}

    if len(cal) == 0:
        extra = sum(float(t['amount']) for t in my_topups)
        return PotResult(key, name, strategy.key, False, start.strftime('%Y-%m-%d'), pd.DataFrame(), [], {}, init + extra,
                         init + extra, init + extra, 0.0, 0.0, 0.0, 0.0, {}, init + extra,
                         deposits_log=[{'date': start.strftime('%Y-%m-%d'), 'amount': init, 'kind': 'initial'}] +
                                      [{'date': str(t['date']), 'amount': float(t['amount']), 'kind': 'top-up', 'note': t.get('note', ''), 'id': t.get('id')} for t in my_topups])

    assets = list(strategy.assets)
    fxs = _fx_on(fx, cal)
    px, nat = {}, {}
    for a in assets:
        px[a], nat[a] = gbp_series(a, prices[a], fx, cal)
    # dividends per unit in GBP (US withholding only on US-listed funds)
    divs = {}
    for a in assets:
        dv = _dividends(prices[a]).reindex(cal).fillna(0.0)
        divs[a] = (dv / 100.0) if currency(a) == 'GBX' else ((dv / fxs) * (1 - WHT) if currency(a) == 'USD' else dv * 0)
    bpx, _ = gbp_series(bench_asset, prices[bench_asset], fx, cal)
    bdv = _dividends(prices[bench_asset]).reindex(cal).fillna(0.0)
    bdiv = (bdv / 100.0) if currency(bench_asset) == 'GBX' else (bdv / fxs) * (1 - WHT)

    cash, units = 0.0, {a: 0.0 for a in assets}
    cost = {a: 0.0 for a in assets}                  # GBP cost basis incl. fees (average cost)
    b_units, b_cash = 0.0, 0.0
    deposits = realised = dividends = interest = fees = 0.0
    nav_units, nav = 0.0, 1.0
    trades, rows, dep_log = [], [], []
    last_buy_i, prev_d = -10 ** 9, None
    pending = list(my_topups)
    first_month_seen = cal[0].to_period('M')
    params = strategy.params

    def deposit(amount, d, kind, note='', tid=None):
        nonlocal cash, deposits, nav_units, b_cash
        if amount == 0:
            return
        eq_before = cash + sum(units[a] * px[a][d] for a in assets)
        nav_units += amount / (eq_before / nav_units if nav_units > 0 and eq_before > 0 else 1.0)
        cash += amount; deposits += amount; b_cash += amount
        dep_log.append({'date': d.strftime('%Y-%m-%d'), 'amount': round(amount, 2), 'kind': kind, 'note': note, 'id': tid})

    def trade(d, a, side, gbp=None, qty=None, reason=''):
        nonlocal cash, realised, fees
        tid = f"{key}-{d:%Y-%m-%d}-{a}-{side}"
        f = fill_map.get(tid, {})
        price = float(f.get('price') or nat[a][d])          # native: pence, USD, or GBP/USD for USD cash
        rate_fx = float(f.get('fx') or fxs[d])
        unit_gbp = native_to_gbp(a, price, rate_fx)
        fee = fee_of(a)
        if side == 'BUY':
            gbp = min(gbp, cash)
            if gbp <= 0.01:
                return
            fee_gbp = float(f['fee_gbp']) if f.get('fee_gbp') not in (None, '') else gbp * fee
            q = (gbp - fee_gbp) / unit_gbp
            if f.get('units'):
                q = float(f['units'])
            units[a] += q; cost[a] += gbp; cash -= gbp; fees += fee_gbp
            pnl = None
        else:
            q = min(qty, units[a])
            if q <= 0:
                return
            gross = q * unit_gbp
            fee_gbp = float(f['fee_gbp']) if f.get('fee_gbp') not in (None, '') else gross * fee
            basis = cost[a] * q / units[a] if units[a] > 0 else 0.0
            pnl = gross - fee_gbp - basis
            units[a] -= q; cost[a] -= basis; cash += gross - fee_gbp; fees += fee_gbp; realised += pnl
            if units[a] < 1e-12:
                units[a], cost[a] = 0.0, 0.0
            gbp = gross
        trades.append({'id': tid, 'date': d.strftime('%Y-%m-%d'), 'asset': a, 'side': side, 'units': q,
                       'price': price, 'ccy': currency(a), 'unit_gbp': unit_gbp, 'fx': rate_fx, 'gbp': round(gbp, 2), 'fee': round(fee_gbp, 2),
                       'pnl': None if pnl is None else round(pnl, 2), 'reason': reason, 'filled': bool(f)})

    for i, d in enumerate(cal):
        # 1) interest on cash since the previous close
        if prev_d is not None and rate > 0 and cash > 0:
            r = cash * ((1 + rate) ** ((d - prev_d).days / 365) - 1)
            cash += r; interest += r
        # 2) dividends (ex-date)
        for a in assets:
            if units[a] > 0 and divs[a][d] > 0:
                inc = units[a] * divs[a][d]
                cash += inc; dividends += inc
        if b_units > 0 and bdiv[d] > 0:
            b_cash += b_units * bdiv[d]
        # 3) deposits
        if i == 0:
            deposit(init, d, 'initial')
        elif monthly > 0 and d.to_period('M') != cal[i - 1].to_period('M') and d.to_period('M') != first_month_seen:
            deposit(monthly, d, 'monthly')
        while pending and pd.Timestamp(pending[0]['date']) <= d:
            t = pending.pop(0)
            deposit(float(t['amount']), d, 'top-up', t.get('note', ''), t.get('id'))

        row = table.loc[d]
        eq = cash + sum(units[a] * px[a][d] for a in assets)
        # 4) strategy orders at the close
        if strategy.kind == 'weights':
            changed = i == 0 or row['state'] != table['state'].shift(1).loc[d]
            reason = ' / '.join(x for x in (row.get('event_in', ''), row.get('event_out', ''), row.get('event_trend', ''), row.get('event', '')) if isinstance(x, str) and x) \
                or ('start: join the current position' if i == 0 else 'rule change')
            plan = []
            for a in assets:
                tgt = float(row[f'w_{a}'])
                cur_v = units[a] * px[a][d]
                cur_w = cur_v / eq if eq > 0 else 0.0
                if (changed and abs(tgt - cur_w) > 0.005) or abs(tgt - cur_w) > strategy.band or (tgt == 0 and units[a] > 0):
                    plan.append((a, tgt, cur_v))
            for a, tgt, cur_v in plan:                      # sells first
                if tgt * eq < cur_v:
                    q = units[a] if tgt == 0 else (cur_v - tgt * eq) / px[a][d]
                    trade(d, a, 'SELL', qty=q, reason=reason if changed else 'rebalance (drift)')
            for a, tgt, cur_v in plan:
                if tgt * eq > cur_v:
                    trade(d, a, 'BUY', gbp=(tgt * eq - cur_v), reason=reason if changed else 'rebalance (drift)')
        else:  # accumulate
            a = assets[0]
            amt = 0.0
            why = ''
            if bool(row['zone']) and i - last_buy_i >= params['cooldown']:
                amt = cash * params['frac']
                why = 'value zone: ' + ('trend zone' if row['trend_zone'] else '200-week zone')
                last_buy_i = i
            first_of_month = i > 0 and d.to_period('M') != cal[i - 1].to_period('M')
            if monthly > 0 and first_of_month and cash - amt > params['cap_months'] * monthly:
                amt = cash - params['cap_months'] * monthly
                why = (why + ' + ' if why else '') + 'safety cap (cash above 24 months of top-ups)'
            if amt > 0.01:
                trade(d, a, 'BUY', gbp=amt, reason=why)

        # 5) benchmark: everything bought at once, held
        if b_cash > 0.01:
            b_units += (b_cash * (1 - fee_main)) / bpx[d]; b_cash = 0.0

        vals = {a: units[a] * px[a][d] for a in assets}
        eq = cash + sum(vals.values())
        nav = eq / nav_units if nav_units > 0 else 1.0
        rows.append({'date': d, 'cash': cash, **{f'v_{a}': v for a, v in vals.items()}, 'equity': eq,
                     'deposits': deposits, 'nav': nav, 'bench': b_units * bpx[d] + b_cash, 'fx': fxs[d]})
        prev_d = d

    curve = pd.DataFrame(rows).set_index('date')
    d = cal[-1]
    positions = {}
    for a in assets:
        if units[a] > 0:
            v = units[a] * px[a][d]
            positions[a] = {'units': units[a], 'price': float(nat[a][d]), 'ccy': currency(a), 'unit_gbp': float(px[a][d]),
                            'value': v, 'cost': cost[a],
                            'unrealised': v - cost[a], 'unrealised_pct': (v / cost[a] - 1) if cost[a] else 0.0}
    eq = float(curve['equity'].iloc[-1])
    weights = {a: (positions[a]['value'] / eq if a in positions and eq > 0 else 0.0) for a in assets}
    cool_left = max(0, params.get('cooldown', 0) - (len(cal) - 1 - last_buy_i)) if strategy.kind == 'accumulate' and last_buy_i >= 0 else 0
    res = PotResult(key, name, strategy.key, True, cal[0].strftime('%Y-%m-%d'), curve, trades, positions, cash, deposits, eq,
                    realised, dividends, interest, fees, weights, float(curve['bench'].iloc[-1]), cool_left,
                    next((t['date'] for t in reversed(trades) if t['side'] == 'BUY'), None), deposits_log=dep_log)
    res.metrics = metrics(curve, trades)
    return res


def metrics(curve: pd.DataFrame, trades: list) -> dict:
    if curve.empty:
        return {}
    nav = curve['nav']
    dd = nav / nav.cummax() - 1
    days = max((curve.index[-1] - curve.index[0]).days, 1)
    total = nav.iloc[-1] - 1
    cagr = (nav.iloc[-1] ** (365 / days) - 1) if days >= 90 else None
    sells = [t for t in trades if t['side'] == 'SELL' and t['pnl'] is not None]
    wins = [t for t in sells if t['pnl'] > 0]
    return {'twr_total': float(total), 'cagr': None if cagr is None else float(cagr), 'maxdd': float(dd.min()),
            'days': int(days), 'trades': len(trades), 'sells': len(sells),
            'win_rate': (len(wins) / len(sells)) if sells else None}


def order_preview(pot: PotResult, strategy, status: dict, fx: float, prices: dict, joining: bool = False) -> list:
    """Orders the pot would place at the close described by `status` (provisional or final).
    prices: {asset: native price} (pence, USD, or GBP/USD for USD cash).
    `joining` = the pot has not started yet and will join the current position at its first close."""
    out = []

    def row(a, side, gbp, tgt):
        px = prices.get(a)
        unit = native_to_gbp(a, px, fx) if px else None
        return {'asset': a, 'side': side, 'gbp': abs(gbp), 'units': abs(gbp) / unit if unit else None,
                'price': px, 'ccy': currency(a), 'target': tgt}

    if strategy.kind == 'weights':
        eq = pot.equity
        for a, tgt in (status.get('targets') or {}).items():
            cur = pot.weights.get(a, 0.0)
            prev_tgt = (status.get('prev_targets') or {}).get(a, cur)
            changed = joining or tgt != prev_tgt
            if (changed and abs(tgt - cur) > 0.005) or abs(tgt - cur) > strategy.band or (tgt == 0 and cur > 0):
                gbp = (tgt - cur) * eq
                out.append(row(a, 'BUY' if gbp > 0 else 'SELL', gbp, tgt))
    else:
        if status['action'] == 'BUY' and status.get('would_buy'):
            out.append(row(strategy.assets[0], 'BUY', status['would_buy'], None))
    return out
