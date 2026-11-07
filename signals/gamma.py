"""Gamma levels for the S&P 500 and Nasdaq-100, from Cboe's free delayed option chains.

Once a day after the US close (when open interest has been updated) this downloads the option
chains for SPX + SPY and NDX + QQQ, recomputes each option's gamma (Black-Scholes, Cboe's implied
volatility), and estimates dealer gamma exposure (GEX) with the common public convention: dealers
long calls / short puts, so calls add gamma and puts subtract it. From that it derives:

  call wall   the strike above the price with the largest call gamma   (resistance in a calm market)
  put wall    the strike below the price with the largest put gamma    (support in a calm market)
  gamma flip  the price where total gamma changes sign                 (above: calmer; below: moves extend)
  key strikes the largest positive and negative net-gamma strikes nearby

Two windows: "near" = expiries up to the next monthly expiry (what moves prices day to day) and
"3 months" (the bigger positions). Levels are given in index points and as futures/CFD equivalents.

These are estimates: providers use different assumptions about who holds the options, so levels
and especially the GEX sign differ between sources. Every day's levels are logged and scored on
what the index did next (state/gamma_log.json), so the page shows how well they actually worked.
"""
from __future__ import annotations

import json
import math
import re
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import requests

from . import DATA, STATE

DIR = DATA / 'gamma'
LOG = STATE / 'gamma_log.json'
CBOE = 'https://cdn.cboe.com/api/global/delayed_quotes/options/{}.json'
UA = {'User-Agent': 'Mozilla/5.0 (compatible; signals-platform)'}
PAT = re.compile(r'^([A-Z]+)(\d{6})([CP])(\d{8})$')
INDICES = {
    'spx': {'name': 'S&P 500', 'cfd': 'US 500', 'chains': ['_SPX', 'SPY'], 'yahoo': '^GSPC', 'fut': 'ES=F', 'bucket': 25},
    'ndx': {'name': 'Nasdaq-100', 'cfd': 'US Tech 100', 'chains': ['_NDX', 'QQQ'], 'yahoo': '^NDX', 'fut': 'NQ=F', 'bucket': 100},
    'qqq': {'name': 'QQQ', 'cfd': 'QQQ', 'chains': ['QQQ'], 'yahoo': 'QQQ', 'fut': None, 'bucket': 5},
}


# ----------------------------------------------------------------------------- maths
def _pdf(x):
    return np.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def bs_gamma(S, K, T, iv, r=0.04):
    T = np.maximum(T, 1 / 365 / 24)
    iv = np.maximum(iv, 0.01)
    d1 = (np.log(S / K) + (r + 0.5 * iv * iv) * T) / (iv * np.sqrt(T))
    return _pdf(d1) / (S * iv * np.sqrt(T))


def third_friday(y, m):
    d = datetime(y, m, 15)
    return d + timedelta(days=(4 - d.weekday()) % 7)


def next_monthly(now: datetime) -> pd.Timestamp:
    y, m = now.year, now.month
    for _ in range(3):
        tf = third_friday(y, m)
        if tf.date() >= (now + timedelta(days=2)).date():
            return pd.Timestamp(tf) + pd.Timedelta(hours=16)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return pd.Timestamp(now) + pd.Timedelta(days=30)


def parse_chain(raw: dict) -> tuple[float, str, pd.DataFrame]:
    d = raw['data']
    rows = []
    for o in d.get('options', []):
        m = PAT.match(o.get('option', ''))
        oi = o.get('open_interest') or 0
        if not m or oi <= 0:
            continue
        _, ymd, cp, k = m.groups()
        exp = pd.Timestamp(datetime.strptime(ymd, '%y%m%d')) + pd.Timedelta(hours=16)
        rows.append((exp, cp, int(k) / 1000, float(oi), float(o.get('iv') or 0)))
    df = pd.DataFrame(rows, columns=['exp', 'cp', 'K', 'oi', 'iv'])
    return float(d['current_price']), str(d.get('last_trade_time') or ''), df


def _prep(df, S, now, until, band=0.25):
    d = df[(df.iv > 0.01) & (df.iv < 3) & (df.K > S * (1 - band)) & (df.K < S * (1 + band))].copy()
    d['T'] = (d.exp - pd.Timestamp(now).tz_localize(None)).dt.total_seconds() / (365 * 24 * 3600)
    d = d[(d['T'] > 0) & (d.exp <= until)]
    d['sign'] = np.where(d.cp == 'C', 1.0, -1.0)
    return d


def levels_for(key: str, chains: dict, now: datetime, until: pd.Timestamp) -> dict:
    """chains: {chain_symbol: (spot, last_time, df)}. Index chain first; ETF scaled to index points."""
    spec = INDICES[key]
    idx_sym = spec['chains'][0]
    S_idx, asof, _ = chains[idx_sym]
    parts = []
    for sym in spec['chains']:
        if sym not in chains:
            continue
        S, _, df = chains[sym]
        c = S_idx / S                                   # index points per ETF point
        d = _prep(df, S, now, until)
        if d.empty:
            continue
        parts.append((sym, S, c, d))
    if not parts:
        raise ValueError(f'{key}: no option data')

    def total(x_idx):                                    # total dollar gamma per 1% move at a hypothetical index level
        t = 0.0
        for _, S, c, d in parts:
            x = x_idx / c
            g = bs_gamma(x, d.K.values, d['T'].values, d.iv.values)
            t += float((d.sign.values * g * d.oi.values * 100 * x * x * 0.01).sum())
        return t

    prof = []
    for _, S, c, d in parts:
        g = bs_gamma(S, d.K.values, d['T'].values, d.iv.values)
        gex = d.sign.values * g * d.oi.values * 100 * S * S * 0.01
        b = spec['bucket']
        prof.append(pd.DataFrame({'K': np.round(d.K.values * c / b) * b, 'cp': d.cp.values, 'gex': gex}))
    P = pd.concat(prof).groupby(['K', 'cp'])['gex'].sum().unstack(fill_value=0.0)
    for col in ('C', 'P'):
        if col not in P:
            P[col] = 0.0
    P['net'] = P['C'] + P['P']
    near = P[(P.index > S_idx * 0.88) & (P.index < S_idx * 1.12)]
    above, below = near[near.index > S_idx], near[near.index < S_idx]
    call_wall = float(above['C'].idxmax()) if len(above) else None
    put_wall = float(below['P'].idxmin()) if len(below) else None
    grid = np.linspace(S_idx * 0.9, S_idx * 1.1, 81)
    tot = np.array([total(x) for x in grid])
    flip = None
    for i in range(len(grid) - 1):
        if np.sign(tot[i]) != np.sign(tot[i + 1]):
            x = grid[i] - tot[i] * (grid[i + 1] - grid[i]) / (tot[i + 1] - tot[i])
            if flip is None or abs(x - S_idx) < abs(flip - S_idx):
                flip = float(x)
    g_now = total(S_idx)
    window = near[(near.index > S_idx * 0.95) & (near.index < S_idx * 1.05)]
    return {
        'spot': S_idx, 'asof': asof, 'gex_bn': g_now / 1e9,
        'call_wall': call_wall, 'put_wall': put_wall, 'flip': flip,
        'pos_strikes': [float(k) for k in window['net'].nlargest(3).index if window.loc[k, 'net'] > 0],
        'neg_strikes': [float(k) for k in window['net'].nsmallest(3).index if window.loc[k, 'net'] < 0],
        'profile': [[float(k), float(v) / 1e9] for k, v in window['net'].items()],
        'regime': ('negative' if flip is not None and S_idx < flip else 'positive') if g_now != 0 else 'flat',
        'n_options': int(sum(len(p[3]) for p in parts)),
    }


# ----------------------------------------------------------------------------- fetch (after the US close)
def _futures_offset(spec) -> dict:
    from .data import fetch_yahoo
    out = {}
    if not spec.get('fut'):
        return out
    try:
        f = fetch_yahoo(spec['fut'], (datetime.now(timezone.utc) - timedelta(days=10)).strftime('%Y-%m-%d'))['close']
        i = fetch_yahoo(spec['yahoo'], (datetime.now(timezone.utc) - timedelta(days=10)).strftime('%Y-%m-%d'))['close']
        j = f.index.intersection(i.index)
        if len(j):
            out = {'fut_last': float(f.iloc[-1]), 'idx_close': float(i.loc[j[-1]]), 'offset': float(f.loc[j[-1]] - i.loc[j[-1]]), 'asof': j[-1].strftime('%Y-%m-%d')}
    except Exception as e:  # noqa: BLE001
        out = {'error': str(e)[:120]}
    return out


def _ohlc(spec, days=400) -> pd.DataFrame:
    from .data import fetch_yahoo
    d = fetch_yahoo(spec['yahoo'], (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%d'))
    return d[['open', 'high', 'low', 'close']]


def fetch(now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    DIR.mkdir(parents=True, exist_ok=True)
    rep, chains = {}, {}
    for sym in dict.fromkeys(c for spec in INDICES.values() for c in spec['chains']):
        try:
            r = requests.get(CBOE.format(sym), headers=UA, timeout=90)
            r.raise_for_status()
            chains[sym] = parse_chain(r.json())
            rep[sym] = f'ok ({len(chains[sym][2])} options)'
        except Exception as e:  # noqa: BLE001
            rep[sym] = f'failed: {str(e)[:100]}'
    until_near = next_monthly(now)
    latest = {'computed': now.strftime('%Y-%m-%d %H:%M UTC'), 'near_expiry': until_near.strftime('%Y-%m-%d'), 'indices': {}}
    for key, spec in INDICES.items():
        try:
            near = levels_for(key, chains, now, until_near)
            far = levels_for(key, chains, now, pd.Timestamp(now).tz_localize(None) + pd.Timedelta(days=95))
            near.pop('n_options', None)
            far = {k: far[k] for k in ('call_wall', 'put_wall', 'flip', 'gex_bn', 'regime')}
            latest['indices'][key] = {'name': spec['name'], 'cfd': spec['cfd'], 'near': near, 'quarter': far, 'futures': _futures_offset(spec)}
            try:
                _ohlc(spec).to_csv(DIR / f'{key}_ohlc.csv', date_format='%Y-%m-%d')
            except Exception as e:  # noqa: BLE001
                rep[f'{key} prices'] = f'failed: {str(e)[:80]}'
        except Exception as e:  # noqa: BLE001
            latest['indices'][key] = {'name': spec['name'], 'error': str(e)[:200]}
    (DIR / 'latest.json').write_text(json.dumps(latest, indent=1))
    _log(latest)
    return rep


# ----------------------------------------------------------------------------- live record
def _log(latest: dict) -> None:
    log = json.loads(LOG.read_text()) if LOG.exists() else []
    for key, v in latest.get('indices', {}).items():
        n = v.get('near') or {}
        if not n or not n.get('asof'):
            continue
        day = n['asof'][:10]
        if any(e['index'] == key and e['date'] == day for e in log):
            continue                                     # write once per data date
        log.append({'index': key, 'date': day, 'spot': n['spot'], 'call_wall': n['call_wall'], 'put_wall': n['put_wall'],
                    'flip': n['flip'], 'regime': n['regime'], 'gex_bn': n['gex_bn']})
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(json.dumps(log, indent=1))


def score(log: list, ohlc: dict) -> dict:
    """Next-session outcome of each logged level: touched? held (closed back on the right side) or broke?"""
    out = {}
    for key in INDICES:
        px = ohlc.get(key)
        rows = [e for e in log if e['index'] == key]
        st = {'days': 0, 'cw_touch': 0, 'cw_held': 0, 'pw_touch': 0, 'pw_held': 0, 'range_neg': [], 'range_pos': [], 'recent': []}
        if px is None or px.empty:
            st.update({'avg_range_neg': None, 'avg_range_pos': None, 'n_neg': 0, 'n_pos': 0})
            st.pop('range_neg'); st.pop('range_pos')
            out[key] = st
            continue
        for e in rows:
            nxt = px[px.index > pd.Timestamp(e['date'])]
            if nxt.empty:
                continue
            b = nxt.iloc[0]
            st['days'] += 1
            res = {'date': e['date'], 'next': nxt.index[0].strftime('%Y-%m-%d'), 'call_wall': e['call_wall'], 'put_wall': e['put_wall'],
                   'high': float(b.high), 'low': float(b.low), 'close': float(b.close), 'regime': e['regime']}
            if e.get('call_wall') and b.high >= e['call_wall']:
                st['cw_touch'] += 1
                held = b.close < e['call_wall']
                st['cw_held'] += held
                res['cw'] = 'held' if held else 'broke'
            if e.get('put_wall') and b.low <= e['put_wall']:
                st['pw_touch'] += 1
                held = b.close > e['put_wall']
                st['pw_held'] += held
                res['pw'] = 'held' if held else 'broke'
            rng = float((b.high - b.low) / e['spot'] * 100)
            (st['range_neg'] if e['regime'] == 'negative' else st['range_pos']).append(rng)
            st['recent'].append(res)
        st['avg_range_neg'] = float(np.mean(st['range_neg'])) if st['range_neg'] else None
        st['avg_range_pos'] = float(np.mean(st['range_pos'])) if st['range_pos'] else None
        st['n_neg'], st['n_pos'] = len(st['range_neg']), len(st['range_pos'])
        st.pop('range_neg'); st.pop('range_pos')
        st['recent'] = list(reversed(st['recent']))[:10]
        out[key] = st
    return out


def compute() -> dict:
    p = DIR / 'latest.json'
    if not p.exists():
        return {'error': 'no gamma data yet (computed after each US close)'}
    latest = json.loads(p.read_text())
    log = json.loads(LOG.read_text()) if LOG.exists() else []
    ohlc = {}
    for key in INDICES:
        f = DIR / f'{key}_ohlc.csv'
        if f.exists():
            ohlc[key] = pd.read_csv(f, index_col=0, parse_dates=True)
    latest['track'] = score(log, ohlc)
    latest['since'] = min((e['date'] for e in log), default=None)
    for key, v in latest.get('indices', {}).items():
        fut = (v.get('futures') or {}).get('offset')
        if fut is not None and v.get('near'):
            n = v['near']
            v['cfd_levels'] = {k: (n[k] + fut if n.get(k) else None) for k in ('call_wall', 'put_wall', 'flip')}
    return latest
