"""Expected path of a trading pot, from the system's own backtest.

The backtest uses the same signal table the live pot follows, over the years BEFORE the pot's
start date (2010+ for the Nasdaq system, 2015+ for BTC), with the pot's fees. For every holding
period h (sessions since the start) we take every historical start day and measure the return
over the next h sessions: the 10th / 50th / 90th percentiles form the expected cone. The pot's
actual return and drawdown are then compared with that distribution and flagged when outside it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .calendar import add_trading_days

BT_START = {'qqq_regime': '2010-01-01', 'btc_trend': '2015-01-01'}
AHEAD = 63          # sessions of cone drawn beyond today


def _ffill_on(s: pd.Series, idx) -> pd.Series:
    s = s.dropna()
    return s.reindex(s.index.union(idx)).ffill().reindex(idx)


def backtest_returns(strategy, table: pd.DataFrame, data: dict, cfg: dict) -> tuple[pd.Series, pd.Series]:
    """Daily GBP returns of the strategy and of its underlying, on the strategy calendar."""
    idx = table.index
    fx = _ffill_on(data['GBPUSD']['close'], idx)
    fee_main = float(cfg.get('fee_pct', 0) or 0) / 100
    fee_fx = float(cfg.get('fx_fee_pct', 0.15) if cfg.get('fx_fee_pct') is not None else 0.15) / 100
    rate = float(cfg.get('cash_rate_pct', 0) or 0) / 100
    rets, invested = pd.Series(0.0, index=idx), pd.Series(0.0, index=idx)
    under = None
    for a in strategy.assets:
        w = table[f'w_{a}'].astype(float)
        if a == 'USD':
            r = (1 / fx).pct_change().fillna(0)
            fee = fee_fx
        elif a == 'EQQQ':
            r = _ffill_on(data['EQQQ']['close'], idx).pct_change().fillna(0)
            fee = fee_main
            under = r
        else:                               # USD-quoted (BTC)
            r = (_ffill_on(data[a]['close'], idx) / fx).pct_change().fillna(0)
            fee = fee_main
            under = r
        rets += w.shift(1).fillna(0) * r - fee * w.diff().abs().fillna(0)
        invested += w
    days = pd.Series(idx, index=idx).diff().dt.days.fillna(1)
    rets += (1 - invested.shift(1).fillna(0)).clip(lower=0) * ((1 + rate) ** (days / 365) - 1)
    return rets, under


def _cum_quantiles(logr: np.ndarray, hs, q=(2.5, 10, 50, 90)) -> dict:
    cs = np.concatenate([[0.0], np.cumsum(logr)])
    out = {}
    for h in hs:
        if h <= 0 or h >= len(cs):
            continue
        v = cs[h:] - cs[:-h]
        out[h] = np.percentile(v, q)
    return out


def _window_dd(logr: np.ndarray, h: int) -> np.ndarray:
    """Max drawdown of every h-session window (as a negative fraction)."""
    cs = np.concatenate([[0.0], np.cumsum(logr)])
    n = len(cs) - h
    if n <= 0:
        return np.array([0.0])
    step = max(1, n // 1500)
    out = []
    for i in range(0, n, step):
        seg = cs[i:i + h + 1] - cs[i]
        out.append(np.exp((seg - np.maximum.accumulate(seg)).min()) - 1)
    return np.array(out)


def expectation(pot_key: str, strategy, table: pd.DataFrame, data: dict, cfg: dict, curve: pd.DataFrame,
                start: str, cal: str) -> dict:
    rets, under = backtest_returns(strategy, table, data, cfg)
    start_ts = pd.Timestamp(start)
    bt = rets[(rets.index >= BT_START.get(strategy.key, '2010-01-01')) & (rets.index < start_ts)]
    logr = np.log1p(bt.values)
    if len(logr) < 260:
        return {}
    years = len(bt) / (365 if cal == 'crypto' else 252)
    eq = np.exp(np.cumsum(logr))
    bt_cagr = eq[-1] ** (1 / years) - 1
    bt_maxdd = (eq / np.maximum.accumulate(eq) - 1).min()

    live_dates = list(curve.index) if len(curve) else []
    n_live = max(len(live_dates) - 1, 0)
    H = n_live + AHEAD
    q = _cum_quantiles(logr, range(1, H + 1))
    # dates for the cone: live dates, then projected sessions
    d0 = live_dates[0] if live_dates else pd.Timestamp(start)
    dates = list(live_dates) if live_dates else [d0]
    while len(dates) < H + 1:
        dates.append(dates[-1] + pd.Timedelta(days=1) if cal == 'crypto' else add_trading_days(dates[-1], 1, 'lse'))
    cone = [[dates[0].strftime('%Y-%m-%d'), 0.0, 0.0, 0.0]]
    for h in range(1, H + 1):
        if h in q:
            _, lo, md, hi = (np.exp(q[h]) - 1) * 100
            cone.append([dates[h].strftime('%Y-%m-%d'), lo, md, hi])

    live, flags = [], []
    out = {'bt_period': f"{bt.index[0]:%b %Y} – {bt.index[-1]:%b %Y}", 'bt_cagr': float(bt_cagr), 'bt_maxdd': float(bt_maxdd),
           'cone': cone, 'live': live, 'flags': flags, 'sessions': n_live}
    if len(curve) >= 2:
        nav = curve['nav'] / curve['nav'].iloc[0]
        u = (1 + under.reindex(curve.index).fillna(0)).cumprod()
        u = u / u.iloc[0]
        live += [[d.strftime('%Y-%m-%d'), (n - 1) * 100, (v - 1) * 100] for d, n, v in zip(curve.index, nav, u)]
        h = n_live
        ret = float(nav.iloc[-1] - 1)
        dd = float((nav / nav.cummax() - 1).min())
        und_ret = float(u.iloc[-1] - 1)
        out.update({'live_ret': ret, 'live_dd': dd, 'under_ret': und_ret})
        if h in q:
            p2, lo, md, hi = np.exp(q[h]) - 1
            out.update({'exp_lo': float(lo), 'exp_med': float(md), 'exp_hi': float(hi)})
            if ret < p2:
                flags.append({'tone': 'red', 'text': f'Return {ret:+.1%} is below 97.5% of backtest outcomes after {h} sessions.'})
            elif ret < lo:
                flags.append({'tone': 'amber', 'text': f'Return {ret:+.1%} is below the expected range ({lo:+.1%} to {hi:+.1%}) after {h} sessions.'})
            elif ret > hi:
                flags.append({'tone': 'blue', 'text': f'Return {ret:+.1%} is above the expected range ({lo:+.1%} to {hi:+.1%}): good, but check the fills.'})
        wdd = _window_dd(logr, max(h, 5))
        typ_worst = float(np.percentile(wdd, 10))
        out['exp_dd'] = typ_worst
        if dd < bt_maxdd:
            flags.append({'tone': 'red', 'text': f'Drawdown {dd:.1%} is worse than the worst in the backtest ({bt_maxdd:.1%}). Review before trading on.'})
        elif dd < typ_worst:
            flags.append({'tone': 'amber', 'text': f'Drawdown {dd:.1%} is worse than 90% of backtest periods of the same length ({typ_worst:.1%}).'})
        if not flags:
            flags.append({'tone': 'green', 'text': f'In line with the backtest after {h} sessions.'})
    return out
