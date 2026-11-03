"""BTC cycle trend system v2 (spot, long or flat). Daily close = 00:00 UTC.

Rules (crystallised 3 Nov 2026; research/btc-trend.md):
  1. Trend    in the market while the 30-day EMA of daily closes is above the 50-day EMA;
              out while it is below (buy / sell at the daily close on the cross).
  2. Bear     flat from day 541 to day 900 after each halving (no position, no entries).
  3. Size     100% of the BTC pot, except 50% when
                - ADX(14) on daily highs/lows/closes is below 25 (no trend strength), or
                - it is day 1,081 to 1,260 after the halving (mid-cycle chop phase).
  Target BTC weight = trend (0/1) x size (1 or 0.5), 0 inside the bear window. The rest stays in cash.
  No stop loss, no profit target: the cross, the bear window and the size rules are the only exits.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..indicators import ema
from .base import Strategy, check, fmt_pct, fmt_usd

HALVINGS = [pd.Timestamp(d) for d in ('2012-11-28', '2016-07-09', '2020-05-11', '2024-04-20')]
NEXT_HALVING_EST = pd.Timestamp('2028-04-15')


def adx(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    """Wilder's ADX (smoothing alpha = 1/n)."""
    up, dn = high.diff(), -low.diff()
    pdm = up.where((up > dn) & (up > 0), 0.0)
    ndm = dn.where((dn > up) & (dn > 0), 0.0)
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / n, adjust=False).mean()
    pdi = 100 * pdm.ewm(alpha=1 / n, adjust=False).mean() / atr
    ndi = 100 * ndm.ewm(alpha=1 / n, adjust=False).mean() / atr
    dx = 100 * (pdi - ndi).abs() / (pdi + ndi)
    return dx.ewm(alpha=1 / n, adjust=False).mean()


def _days_since_halving(idx: pd.DatetimeIndex) -> np.ndarray:
    out = np.full(len(idx), np.nan)
    for h in HALVINGS:
        m = idx >= h
        out[m] = (idx[m] - h).days
    return out


class BTCTrend(Strategy):
    def __init__(self):
        super().__init__(
            key='btc_trend', name='BTC cycle trend system', kind='weights', page='trading',
            assets=('BTC',), inputs=('BTC',), calendar_asset='BTC', band=1.0,
            params=dict(fast=30, slow=50, bear=(540, 900), chop=(1080, 1260), adx_n=14, adx_min=25, reduced=0.5),
            paper='research/btc-trend.html',
            timing='Checks at the daily close, 00:00 UTC. Trade soon after with a limit order (Kraken Pro) or at the next session (ETF).',
            tested={'cagr': 0.83, 'maxdd': -0.34, 'period': '2016-Oct 2026 (selected after extensive testing: expect less)'})

    def compute(self, data: dict) -> pd.DataFrame:
        df = data['BTC']
        P = df['close'].dropna()
        p = self.params
        t = pd.DataFrame(index=P.index)
        t['close'] = P
        t['ema_fast'], t['ema_slow'] = ema(P, p['fast']), ema(P, p['slow'])
        t['trend'] = (t['ema_fast'] > t['ema_slow'])
        h = df['high'].reindex(P.index).fillna(P)
        lo = df['low'].reindex(P.index).fillna(P)
        t['adx'] = adx(h, lo, P, p['adx_n'])
        d = pd.Series(_days_since_halving(P.index), index=P.index)
        t['days_since_halving'] = d
        t['bear_window'] = (d > p['bear'][0]) & (d <= p['bear'][1])
        t['chop_window'] = (d > p['chop'][0]) & (d <= p['chop'][1])
        t['weak_trend'] = (t['adx'] < p['adx_min']).fillna(False)
        t['size'] = np.where(t['weak_trend'] | t['chop_window'], p['reduced'], 1.0)
        t['w_BTC'] = np.where(t['bear_window'], 0.0, t['trend'].astype(float) * t['size'])
        t['state'] = t['w_BTC'].round(3).astype(str)
        prev = t.shift(1)
        ev = []
        for i, (dt, r) in enumerate(t.iterrows()):
            if i == 0 or r['w_BTC'] == prev['w_BTC'].iloc[i]:
                ev.append('')
                continue
            pr = prev.iloc[i]
            if r['bear_window'] and not pr['bear_window']:
                ev.append('Bear window opened (day 541 after the halving): go flat')
            elif pr['bear_window'] and not r['bear_window']:
                ev.append('Bear window closed' + (': 30-day EMA above 50-day, buy' if r['trend'] else ''))
            elif r['trend'] != pr['trend']:
                ev.append('30-day EMA crossed ' + ('above' if r['trend'] else 'below') + ' the 50-day EMA')
            else:
                why = []
                if r['weak_trend'] != pr['weak_trend']:
                    why.append(f"ADX {'fell below' if r['weak_trend'] else 'rose above'} 25")
                if r['chop_window'] != pr['chop_window']:
                    why.append('mid-cycle chop phase ' + ('started' if r['chop_window'] else 'ended'))
                ev.append('Size ' + ('halved' if r['size'] < pr['size'] else 'back to full') + (': ' + ', '.join(why) if why else ''))
        t['event'] = ev
        return t

    def status(self, t: pd.DataFrame, pot: dict | None = None, provisional: bool = False) -> dict:
        x, prev = t.iloc[-1], t.iloc[-2]
        d = t.index[-1]
        p = self.params
        w, w_prev = float(x['w_BTC']), float(prev['w_BTC'])
        if w > w_prev:
            action, sub = 'BUY', f'BTC to {w:.0%} of the pot'
        elif w < w_prev:
            action, sub = ('SELL', 'BTC to 0%') if w == 0 else ('REDUCE', f'BTC to {w:.0%}')
        elif w > 0:
            action, sub = 'HOLD', f'BTC {w:.0%} of the pot'
        else:
            action, sub = 'FLAT', 'in cash'

        hs = int(x['days_since_halving'])
        last_h = max(h for h in HALVINGS if h <= d)
        bear_s, bear_e = last_h + pd.Timedelta(days=p['bear'][0] + 1), last_h + pd.Timedelta(days=p['bear'][1])
        chop_s, chop_e = last_h + pd.Timedelta(days=p['chop'][0] + 1), last_h + pd.Timedelta(days=p['chop'][1])
        nxt_bear = NEXT_HALVING_EST + pd.Timedelta(days=p['bear'][0] + 1)
        if x['bear_window']:
            phase = f'Bear window (day {hs}): flat until {bear_e:%d %b %Y}'
            tone = 'red'
        elif x['chop_window']:
            phase = f'Mid-cycle chop (day {hs}): half size until {chop_e:%d %b %Y}'
            tone = 'amber'
        elif d < bear_s:
            phase = f'Bull phase (day {hs}): bear window opens {bear_s:%d %b %Y}'
            tone = 'green'
        elif d < chop_s:
            phase = f'Recovery (day {hs}): chop phase {chop_s:%b %Y} – {chop_e:%b %Y}'
            tone = 'green'
        else:
            phase = f'Pre-halving (day {hs}): next bear window ~{nxt_bear:%b %Y}'
            tone = 'green'

        gap = (x['ema_fast'] / x['ema_slow'] - 1) * 100
        if x['bear_window']:
            plain = f'Post-halving bear window: the system is out of BTC until {bear_e:%d %b %Y}, whatever the trend says.'
        elif not x['trend']:
            plain = (f"The 30-day EMA ({fmt_usd(x['ema_fast'], 0)}) is below the 50-day EMA ({fmt_usd(x['ema_slow'], 0)}): no trend, stay in cash. "
                     'Buy at the close when the 30-day crosses back above.')
        else:
            why = []
            if x['weak_trend']:
                why.append(f"ADX is {x['adx']:.0f}, below 25 (weak trend)")
            if x['chop_window']:
                why.append('it is the mid-cycle chop phase')
            plain = (f"Uptrend: the 30-day EMA is {gap:+.1f}% above the 50-day. Hold {w:.0%} of the pot" +
                     (f": half size because {' and '.join(why)}." if why else ' (full size).') +
                     f" Sell at the close if the 30-day EMA crosses below the 50-day ({fmt_usd(x['ema_slow'], 0)} now).")
        groups = [
            {'title': '1 · Trend', 'note': 'in when the 30-day EMA is above the 50-day', 'rows': [
                check('30-day EMA above 50-day EMA', fmt_usd(x['ema_fast'], 0), f"above {fmt_usd(x['ema_slow'], 0)}", x['trend']),
                check('Gap between the averages', f'{gap:+.1f}%', 'positive = in', None),
            ]},
            {'title': '2 · Halving cycle', 'note': f'day {hs} since the {last_h:%b %Y} halving', 'rows': [
                check('Outside the bear window (day 541–900)', f'day {hs}', 'outside', not x['bear_window']),
                check('Outside the mid-cycle chop phase (day 1,081–1,260)', f'day {hs}', 'outside = full size', not x['chop_window']),
            ]},
            {'title': '3 · Size', 'note': '100%, or 50% when the trend is weak', 'rows': [
                check('ADX(14) at or above 25 (trend has strength)', f"{x['adx']:.1f}", 'at/above 25 = full size', not x['weak_trend']),
                check('Position size', f"{x['size']:.0%}", '100% or 50%', None),
            ]},
        ]
        orders = [
            {'kind': 'ENTRY', 'tone': 'green', 'text': 'Buy at the daily close when the 30-day EMA crosses above the 50-day EMA (outside the bear window).'},
            {'kind': 'EXIT', 'tone': 'red', 'text': f"Sell everything at the close when the 30-day EMA crosses below the 50-day, or when the bear window opens (next ~{nxt_bear:%b %Y})."},
            {'kind': 'SIZE', 'tone': 'blue', 'text': 'Hold 100% of the pot, or 50% while ADX(14) is below 25 or during the mid-cycle chop phase. Rebalance at the close when the size changes.'},
            {'kind': 'NO FIXED STOP', 'tone': 'grey', 'text': 'No stop loss or profit target: the cross, the bear window and the size rules are the only exits.'},
        ]
        extra = [
            {'label': 'Next halving (est.)', 'value': f'{NEXT_HALVING_EST:%b %Y}', 'tone': ''},
            {'label': 'Next bear window (flat)', 'value': f'from ~{nxt_bear:%b %Y}', 'tone': ''},
            {'label': 'Leverage warning', 'value': 'see Risk radar', 'tone': ''},
        ]
        return {
            'key': self.key, 'name': self.name, 'asof': d.strftime('%Y-%m-%d'), 'provisional': provisional,
            'kicker': 'System #2 · BTC spot daily · checks at 00:00 UTC',
            'action': action, 'action_sub': sub, 'plain': plain,
            'pills': [{'text': 'Trend: ' + ('up' if x['trend'] else 'down'), 'tone': 'green' if x['trend'] else 'grey'},
                      {'text': phase, 'tone': tone},
                      {'text': f"ADX {x['adx']:.0f} · size {x['size']:.0%}", 'tone': 'blue' if not x['weak_trend'] else 'amber'}],
            'groups': groups, 'orders': orders,
            'extra_title': 'Calendar · display only', 'extra': extra,
            'extra_note': 'Dollar and Fed-liquidity filters were tested in v1 and dropped, so they are no longer shown.',
            'targets': {'BTC': w}, 'prev_targets': {'BTC': w_prev},
            'levels': {'close': float(x['close']), 'ema_fast': float(x['ema_fast']), 'ema_slow': float(x['ema_slow']),
                       'adx': float(x['adx']), 'size': float(x['size'])},
            'paper': self.paper, 'timing': self.timing,
        }
