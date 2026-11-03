"""Bottom signals (display only): QQQ fast-crash two-step buy plan and the bear-market washout.

Research and backtests: research/bottom-signals.md. Nothing here changes any order.

Fast crash (QQQ, adjusted daily closes and volume)
  Window: QQQ falls 8%+ within 15 sessions, starting within 4% of its 1-year high; the window lasts 40 sessions.
  Override (skip the plan): rate/inflation pressure on, or the late-cycle radar red (3+ signs), on the buy-1 day.
  Buy 1: first close in the window at least 10.8% below the 1-year high.
  Buy 2 (same amount): first later close below the buy-1 price, within 40 sessions, with 3+ of 6 capitulation
  groups on (each group stays on for 10 sessions):
    stretch       drawdown or 15-day return <= -2.5 x one-year daily volatility (scaled)
    capitulation  volume >= 1.8x its 50-day average on a down 2%+ day (in the last 3 sessions)
    options fear  Cboe total or equity put/call (5-day mean) in the top 10% of the last year
    vol panic     VXN in the top 10% of the last year, or VIX9D/VIX >= 1.05
    dealer gamma  SqueezeMetrics GEX below zero
    oversold      RSI(14) <= 30 or RSI(2) <= 5
Bear washout (S&P 500 and QQQ; QQQ thresholds x1.35)
  In a bear state (15% / 20.25% below the 1-year high), signal when the index is 30% / 40.5% below its high,
  or 20% / 27% below its 200-day average, or VIX >= 35. One signal per 126 sessions.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .radar import _on, _price, _read, late_cycle

PERF = {
    'fast': {
        'predicts': 'Where to buy in a QQQ fast crash (down 8%+ in 3 weeks from near its high), in two steps',
        'headline': [('79%', 'of buys within 5% of the crash low (one fixed buy: 62%)'),
                     ('−0.4%', 'median further fall after buying (worst −15%)'),
                     ('+10.3%', 'average return 3 months later (+18.0% after 6)'),
                     ('24 days', 'median time until back above the entry price for good')],
        'detail': [('Tested', '19 QQQ fast crashes 2007–2026: 14 bought, 2 skipped by the override, 3 never fell 10.8%'),
                   ('By era', '2007–15: 71% within 5% of low, +10.2% at 3 months · 2016–26: 86%, +10.5%'),
                   ('Override', 'Skipped Jan 2022 (−22% further) and Mar 2025 (bear washout bought Apr 2025). 1990–2026: traps 30% → 21%'),
                   ('Up after 3 months', '86% of buys')],
        'caveat': 'Small sample (14 buys). 10.8% is an entry into the crash, not the low: the typical QQQ fast-crash low is about 16% below the high.',
    },
    'washout': {
        'predicts': 'A capitulation low in a bear market (S&P 500 down 15%+ or QQQ 20%+)',
        'headline': [('−1.8%', 'median further fall after an S&P signal, 2010–2026'),
                     ('+25%', 'average S&P return 6 months later (QQQ +42%)'),
                     ('7 of 7', 'S&P and QQQ signals since 2010 up 6 months later'),
                     ('91%', 'S&P signals before 2010 up 6 months later (11 signals)')],
        'detail': [('S&P since 2010', 'Aug 2011, Dec 2018, Mar 2020, Apr 2025: 75% within 5% of the low; worst further fall −19% (2020)'),
                   ('QQQ since 2010', 'Dec 2018, Mar 2020, Apr 2025: all within 4% of the low'),
                   ('Before 2010', 'S&P 1962–2009: −3.8% median further fall, +12% at 6 months. QQQ 1987–2009: failed in the dot-com bust (−60%)'),
                   ('Missed', 'The October 2022 low: a slow, rate-driven bear market with no washout')],
        'caveat': 'Few signals. In a secular bear market (2000–02) a washout can come far too early.',
    },
}


# ----------------------------------------------------------------------------- helpers
def _tp(s, n=252, mp=120):
    return s.rolling(n, min_periods=mp).apply(lambda w: (w[:-1] < w[-1]).mean(), raw=True)


def _rsi(c, n):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


def _windows(c, fall=0.08, n=15, near=0.04, win=40):
    """Start index of each fast-crash window, using only data up to the last close."""
    a = c.values
    hi = c.rolling(252, min_periods=200).max().values
    out, i = [], 0
    while i < len(a) - 1:
        fut = a[i + 1:i + 1 + n]
        if hi[i] == hi[i] and a[i] / hi[i] - 1 >= -near and len(fut) and fut.min() / a[i] - 1 <= -fall:
            out.append(i)
            i += win
        else:
            i += 1
    return out


def qqq_groups() -> pd.DataFrame:
    c = _price('QQQ', 'adj_close').dropna()
    v = _price('QQQ', 'volume').reindex(c.index)
    idx = c.index
    X = pd.DataFrame(index=idx)
    r = np.log(c).diff()
    sig = r.rolling(252, min_periods=120).std()
    hi = c.rolling(252, min_periods=200).max()
    X['close'] = c
    X['dd'] = c / hi - 1
    X['z15'] = np.log(c / c.shift(15)) / (sig * np.sqrt(15))
    X['dd_z'] = np.log(c / hi) / (sig * np.sqrt(20))
    va = v.rolling(50).mean()
    X['volx'] = v / va
    X['ret'] = c.pct_change()
    X['capit3'] = ((X['volx'] >= 1.8) & (X['ret'] <= -0.02)).astype(float).rolling(3, min_periods=1).max().where(va.notna())
    X['rsi14'], X['rsi2'] = _rsi(c, 14), _rsi(c, 2)
    vix, vxn, vix9 = (_on(_read(f'cboe_{s}', 'close'), idx, stale_days=10) for s in ('VIX', 'VXN', 'VIX9D'))
    X['vxn'], X['vxn_pct'], X['vix9_ratio'] = vxn, _tp(vxn), vix9 / vix
    pc = _read('putcall_total')
    X['pct_pct'] = _tp(_on(pc['total_pc'], idx, stale_days=10).rolling(5).mean())
    X['pce_pct'] = _tp(_on(pc['equity_pc'], idx, stale_days=10).rolling(5).mean()) if 'equity_pc' in pc else np.nan
    sq = _read('squeeze')
    X['gex'] = _on(sq['gex'], idx, stale_days=10) if len(sq) else np.nan
    f = lambda cond, src: cond.astype(float).where(src.notna()).fillna(0)  # noqa: E731
    m10 = lambda s: s.rolling(10, min_periods=1).max()                     # noqa: E731
    any_ = lambda *s: pd.concat(s, axis=1).max(axis=1)                     # noqa: E731
    G = pd.DataFrame(index=idx)
    G['stretch'] = m10(any_(f(X.dd_z <= -2.5, X.dd_z), f(X.z15 <= -2.5, X.z15)))
    G['capitulation'] = m10(f(X.capit3 == 1, X.capit3))
    G['options_fear'] = m10(any_(f(X.pct_pct >= 0.9, X.pct_pct), f(X.pce_pct >= 0.9, X.pce_pct)))
    G['vol_panic'] = m10(any_(f(X.vxn_pct >= 0.9, X.vxn_pct), f(X.vix9_ratio >= 1.05, X.vix9_ratio)))
    G['dealer_gamma'] = m10(f(X.gex < 0, X.gex))
    G['oversold'] = m10(any_(f(X.rsi14 <= 30, X.rsi14), f(X.rsi2 <= 5, X.rsi2)))
    return X.join(G)


def fast_crash_plan():
    """All fast-crash windows with buy-1 / buy-2 / override outcomes, plus the full feature table."""
    X = qqq_groups()
    c, a, idx = X['close'], X['close'].values, X.index
    L = late_cycle()
    L = L.reindex(L.index.union(idx)).ffill().reindex(idx)
    ovr = (L['pressure'] == 1) | (L['score'] >= 3)
    cnt = X[['stretch', 'capitulation', 'options_fear', 'vol_panic', 'dealer_gamma', 'oversold']].sum(axis=1)
    plans = []
    for s in _windows(c):
        p = {'start': idx[s], 'end_i': min(s + 40, len(a) - 1), 'buy1': None, 'buy2': None, 'skipped': False}
        i = next((k for k in range(s, min(s + 41, len(a))) if X['dd'].iloc[k] <= -0.108), None)
        if i is not None:
            p['buy1'] = idx[i]
            p['buy1_px'] = float(a[i])
            p['skipped'] = bool(ovr.iloc[i])
            if not p['skipped']:
                j = next((k for k in range(i + 1, min(i + 41, len(a))) if cnt.iloc[k] >= 3 and a[k] < a[i]), None)
                if j is not None:
                    p['buy2'] = idx[j]
        plans.append(p)
    return X, L, ovr, cnt, plans


def washout_signals(c: pd.Series, vix: pd.Series, scale=1.0, VB=35, cool=126):
    hi = c.rolling(252, min_periods=200).max()
    dd = c / hi - 1
    s200 = c.rolling(200).mean()
    state = dd <= -0.15 * scale
    cond = ((dd <= -0.30 * scale) | (c / s200 <= 1 - 0.20 * scale) | (vix >= VB)) & state
    sig, last = [], -10 ** 9
    for i in np.where(cond.fillna(False).values)[0]:
        if i - last >= cool:
            sig.append(i)
            last = i
    return sig, dd, s200, state


# ----------------------------------------------------------------------------- panels
def _sign(label, on, value, trigger, explain):
    ok = None if on is None or (isinstance(on, float) and np.isnan(on)) else bool(on)
    return {'label': label, 'on': ok, 'value': value, 'trigger': trigger, 'explain': explain}


def _pct(x, signed=True):
    return '—' if x is None or x != x else (f'{x * 100:+.1f}%' if signed else f'{x * 100:.1f}%')


def fast_panel() -> dict:
    X, L, ovr, cnt, plans = fast_crash_plan()
    t = len(X) - 1
    x = X.iloc[-1]
    asof = X.index[-1]
    act = next((p for p in reversed(plans) if X.index.get_loc(p['start']) <= t <= X.index.get_loc(p['start']) + 40), None)
    groups = [('Stretch', 'stretch', 'Fall of 2.5+ volatility units', f"{x['dd_z']:.1f}σ drawdown · {x['z15']:.1f}σ in 15 days" if x['dd_z'] == x['dd_z'] else '—'),
              ('Capitulation volume', 'capitulation', 'Volume 1.8× normal on a −2% day', f"volume {x['volx']:.1f}× today" if x['volx'] == x['volx'] else '—'),
              ('Options fear', 'options_fear', 'Put/call in top 10% of the year', f"total pct {x['pct_pct'] * 100:.0f} · equity pct {x['pce_pct'] * 100:.0f}" if x['pct_pct'] == x['pct_pct'] else '—'),
              ('Volatility panic', 'vol_panic', 'VXN top 10%, or VIX9D above VIX', f"VXN {x['vxn']:.1f} (pct {x['vxn_pct'] * 100:.0f}) · VIX9D/VIX {x['vix9_ratio']:.2f}" if x['vxn'] == x['vxn'] else '—'),
              ('Dealers short gamma', 'dealer_gamma', 'GEX below zero', f"GEX {x['gex'] / 1e9:+.1f}bn" if x['gex'] == x['gex'] else '—'),
              ('Oversold', 'oversold', 'RSI(14) ≤ 30 or RSI(2) ≤ 5', f"RSI14 {x['rsi14']:.0f} · RSI2 {x['rsi2']:.0f}")]
    n_on = int(cnt.iloc[-1])
    pressure, late = L['pressure'].iloc[-1], L['score'].iloc[-1]
    override_now = bool(ovr.iloc[-1])
    if act is None:
        level, tone = 'IDLE', 'grey'
        summary = f"No fast crash under way: QQQ is {abs(x['dd']) * 100:.1f}% below its 1-year high. The plan starts when QQQ falls 8%+ within 3 weeks from near its high."
    elif act['buy1'] is None:
        level, tone = ('SKIP', 'red') if override_now else ('WATCH', 'amber')
        start = act['start'].strftime('%d %b')
        if override_now:
            summary = f"Fast crash under way since {start}, but the override is on (rate/inflation pressure or late-cycle red): leave this fall to the bear-market washout."
        else:
            summary = (f"Fast crash under way since {start}. Buy 1 triggers at a close 10.8% below the 1-year high "
                       f"(QQQ is {abs(x['dd']) * 100:.1f}% below). Override is off.")
    elif act['skipped']:
        level, tone = 'SKIP', 'red'
        summary = f"Buy 1 level was reached on {act['buy1']:%d %b}, but the override was on: no fast-crash buy. Watch the bear-market washout."
    elif act['buy2'] is None:
        level, tone = 'BUY 1', 'green'
        summary = (f"Buy 1 triggered on {act['buy1']:%d %b} at ${act['buy1_px']:.2f} (adjusted). Buy 2 (same amount) comes on a lower close "
                   f"with 3+ capitulation groups on: {n_on} of 6 on now.")
    else:
        level, tone = 'BUY 2', 'green'
        summary = f"Both buys done: buy 1 on {act['buy1']:%d %b}, buy 2 on {act['buy2']:%d %b}."
    signs = [
        _sign('Fast crash under way', act is not None, f"since {act['start']:%d %b %Y}" if act else 'no', 'QQQ −8% within 15 sessions from near its high', 'The plan only runs inside a fast crash (40 sessions).'),
        _sign('Override: rate/inflation pressure', pressure == 1, 'on' if pressure == 1 else 'off', '10y +1.5 pt in a year, or CPI > 4% and rising', 'Rate-driven falls tend to keep going (1990, 2022). When on, skip the plan.'),
        _sign('Override: late-cycle radar red', late >= 3, f"{int(late)} of 5 signs" if late == late else '—', '3+ late-cycle signs', 'Valuation-driven tops (2000). When on, skip the plan.'),
        _sign('Buy 1: depth reached', x['dd'] <= -0.108, f"{x['dd'] * 100:.1f}% from 1-year high", '10.8% below the 1-year high', 'An entry into the crash; the typical low is ~16% below the high.'),
    ] + [_sign(f'Buy 2 group: {lab}', x[k] == 1, val, trig, 'Counts for 10 sessions after it fires.') for lab, k, trig, val in groups]
    return {'key': 'fast', 'title': 'Fast-crash bottom plan', 'market': 'QQQ', 'horizon': 'the crash low',
            'asof': asof.strftime('%Y-%m-%d'), 'level': level, 'tone': tone, 'score': float(n_on), 'of': 6,
            'rule': 'Buy 1 at −10.8% from the high · Buy 2 on a lower close with 3+ of 6 capitulation groups · skipped when the override is on',
            'summary': summary, 'context': f"Override now: {'ON' if override_now else 'off'} · capitulation groups on now: {n_on} of 6",
            'signs': signs, 'perf': PERF['fast'], 'amber': 3, 'red': 6,
            'hist': [[d.strftime('%Y-%m-%d'), float(v)] for d, v in cnt[cnt.index >= cnt.index[-1] - pd.DateOffset(years=3)].items()],
            'history': [{'start': p['start'].strftime('%Y-%m-%d'), 'buy1': p['buy1'].strftime('%Y-%m-%d') if p['buy1'] is not None else None,
                         'buy2': p['buy2'].strftime('%Y-%m-%d') if p['buy2'] is not None else None, 'skipped': p['skipped'],
                         'active': act is not None and p['start'] == act['start']}
                        for p in plans if p['start'].year >= 2007]}


def washout_panel() -> dict:
    out_signs, levels, notes, last_sig = [], [], [], {}
    vix_all = _read('cboe_VIX', 'close')
    for name, series, scale in (('S&P 500', _read('yahoo_GSPC', 'close').dropna(), 1.0), ('QQQ', _price('QQQ', 'close').dropna(), 1.35)):
        c = series[series.index >= '1990-01-01']
        vix = _on(vix_all, c.index, stale_days=10)
        sig, dd, s200, state = washout_signals(c, vix, scale)
        x_dd, x_200, x_v = dd.iloc[-1], c.iloc[-1] / s200.iloc[-1] - 1, vix.iloc[-1]
        recent = [c.index[i] for i in sig if i >= len(c) - 10]
        last_sig[name] = c.index[sig[-1]].strftime('%Y-%m-%d') if sig else None
        if recent:
            levels.append('BUY')
        elif state.iloc[-1]:
            levels.append('WAIT')
        out_signs.append(_sign(f'{name}: bear state', bool(state.iloc[-1]), f"{x_dd * 100:.1f}% from 1-year high", f"{15 * scale:.1f}%+ below the high", ''))
        out_signs.append(_sign(f'{name}: washout', bool(recent), f"{x_dd * 100:.1f}% · {x_200 * 100:+.1f}% vs 200-day · VIX {x_v:.1f}",
                               f"{30 * scale:.1f}% below high, or {20 * scale:.0f}% below 200-day, or VIX ≥ 35", f"Last signal: {last_sig[name] or 'none since 1990'}"))
    if 'BUY' in levels:
        level, tone, summary = 'BUY', 'green', 'Washout signal in the last 10 sessions: historically one of the best times to buy in a bear market.'
    elif 'WAIT' in levels:
        level, tone, summary = 'WAIT', 'amber', 'In a bear-market state but no washout yet: wait for capitulation (deep fall, stretch below the 200-day, or VIX ≥ 35).'
    else:
        level, tone, summary = 'IDLE', 'grey', 'No bear market: neither the S&P 500 (15%+) nor QQQ (20%+) is in a bear state.'
    return {'key': 'washout', 'title': 'Bear-market washout', 'market': 'S&P 500 and QQQ', 'horizon': 'the bear-market low',
            'asof': _read('yahoo_GSPC', 'close').index[-1].strftime('%Y-%m-%d'), 'level': level, 'tone': tone, 'score': None, 'of': None,
            'rule': 'In a bear state, buy on a washout: 30% below the high, 20% below the 200-day, or VIX ≥ 35 (QQQ thresholds ×1.35)',
            'summary': summary, 'context': f"Last signals: S&P {last_sig.get('S&P 500') or '—'} · QQQ {last_sig.get('QQQ') or '—'}",
            'signs': out_signs, 'perf': PERF['washout'], 'hist': []}


def compute() -> list:
    out = []
    for fn, key, title in ((fast_panel, 'fast', 'Fast-crash bottom plan'), (washout_panel, 'washout', 'Bear-market washout')):
        try:
            out.append(fn())
        except Exception as e:  # noqa: BLE001
            out.append({'key': key, 'title': title, 'error': str(e)[:200], 'perf': PERF[key], 'signs': []})
    return out
