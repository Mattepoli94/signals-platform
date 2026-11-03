"""BTC trend blend (spot, long or flat). Daily close = 00:00 UTC.
  Score   average of five 0/1 signals: close > close 10 / 20 / 50 days ago, close > 50-day EMA,
          10-day EMA > 30-day EMA.
  Sizing  x min(1, 80% / 30-day realised volatility)   (log returns, x sqrt(365)).
  Window  flat from day 545 to day 910 after each halving.
  Target  BTC weight = score x vol factor (0 inside the window). The rest stays in cash.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..indicators import ema, realised_vol
from .base import Strategy, check, fmt_pct, fmt_usd

HALVINGS = [pd.Timestamp(d) for d in ('2012-11-28', '2016-07-09', '2020-05-11', '2024-04-20')]
NEXT_HALVING_EST = pd.Timestamp('2028-04-15')


class BTCTrend(Strategy):
    def __init__(self):
        super().__init__(
            key='btc_trend', name='BTC trend blend', kind='weights', page='trading',
            assets=('BTC',), inputs=('BTC', 'DXY', 'NETLIQ'), calendar_asset='BTC', band=0.10,
            params=dict(vol_target=0.80, win_start=545, win_end=910),
            paper='research/btc-trend.html',
            timing='Checks at the daily close, 00:00 UTC. Trade soon after (the research assumes the close price).',
            tested={'cagr': 1.05, 'maxdd': -0.30, 'period': '2015-2024 (training; ~180 variants tried: optimistic)'})

    def compute(self, data: dict) -> pd.DataFrame:
        P = data['BTC']['close'].dropna()
        p = self.params
        t = pd.DataFrame(index=P.index)
        t['close'] = P
        for n in (10, 20, 50):
            t[f'c{n}'] = P.shift(n)
            t[f'sig_m{n}'] = (P > P.shift(n)).astype(float)
        t['ema10'], t['ema30'], t['ema50'] = ema(P, 10), ema(P, 30), ema(P, 50)
        t['sig_ema50'] = (P > t['ema50']).astype(float)
        t['sig_cross'] = (t['ema10'] > t['ema30']).astype(float)
        sigs = ['sig_m10', 'sig_m20', 'sig_m50', 'sig_ema50', 'sig_cross']
        t['score'] = t[sigs].mean(axis=1)
        t['vol30'] = realised_vol(P, 30, 365)
        t['vol_factor'] = (p['vol_target'] / t['vol30']).clip(upper=1).fillna(1.0)
        t['days_since_halving'] = _days_since_halving(P.index)
        t['halving_window'] = (t['days_since_halving'] > p['win_start']) & (t['days_since_halving'] <= p['win_end'])
        t['w_BTC'] = np.where(t['halving_window'], 0.0, t['score'] * t['vol_factor'])
        t['state'] = t['score'].round(2).astype(str) + '|' + t['halving_window'].astype(str)
        prev_score, prev_win = t['score'].shift(1), t['halving_window'].shift(1, fill_value=False)
        t['event'] = np.where(t['halving_window'] & ~prev_win, 'Halving window opened: go flat',
                     np.where(~t['halving_window'] & prev_win, 'Halving window closed',
                     np.where(t['score'] != prev_score, 'Score ' + prev_score.round(1).astype(str) + ' → ' + t['score'].round(1).astype(str), '')))
        # context, display only
        for k, n, col in (('DXY', 182, 'dxy_6m'), ('NETLIQ', 91, 'netliq_3m')):
            df = data.get(k)
            if df is not None and len(df):
                s = df['adj_close'].dropna()
                s.index = s.index + pd.Timedelta(days=1)          # known the day after
                s = s.reindex(s.index.union(P.index)).ffill().reindex(P.index)
                t[col] = (s / s.shift(n) - 1) * 100
            else:
                t[col] = np.nan
        return t

    def status(self, t: pd.DataFrame, pot: dict | None = None, provisional: bool = False) -> dict:
        x, prev = t.iloc[-1], t.iloc[-2]
        d = t.index[-1]
        w, w_prev = float(x['w_BTC']), float(prev['w_BTC'])
        n_on = int(round(x['score'] * 5))
        held = (pot or {}).get('weights', {}).get('BTC')
        if x['state'] != prev['state'] and w > w_prev:
            action, sub = 'BUY', f'BTC to {w:.0%}'
        elif x['state'] != prev['state'] and w < w_prev:
            action, sub = ('SELL', 'BTC to 0%') if w == 0 else ('REDUCE', f'BTC to {w:.0%}')
        elif w > 0:
            action, sub = 'HOLD', f'target {w:.0%} of the pot'
        else:
            action, sub = 'FLAT', 'in cash'
        if held is not None and action in ('HOLD', 'FLAT') and abs(held - w) > self.band:
            action, sub = ('BUY' if w > held else 'REDUCE'), f'rebalance {held:.0%} → {w:.0%}'

        hs = int(x['days_since_halving'])
        last_h = max(h for h in HALVINGS if h <= d)
        win_start = last_h + pd.Timedelta(days=self.params['win_start'] + 1)
        win_end = last_h + pd.Timedelta(days=self.params['win_end'])
        nxt_start = NEXT_HALVING_EST + pd.Timedelta(days=self.params['win_start'] + 1)
        if x['halving_window']:
            win_txt = f'inside (day {hs}) until {win_end:%d %b %Y}'
        elif d < win_start:
            win_txt = f'opens {win_start:%d %b %Y} (day {hs} now)'
        else:
            win_txt = f'clear (day {hs}); next ~{nxt_start:%b %Y}'

        if x['halving_window']:
            plain = f'Post-halving bear window (day {hs} of 545–910): the system is flat until {win_end:%d %b %Y}, whatever the trend says.'
        else:
            plain = (f"{n_on} of 5 trend signals are positive, so the score is {x['score']:.1f}. "
                     f"Volatility is {x['vol30']:.1%}" + (', so no size cut' if x['vol_factor'] >= 1 else f", so size × {x['vol_factor']:.2f}") +
                     f". Target {w:.0%} of the pot." + (' A score of 0 means fully in cash.' if w > 0 else ''))
        rows = [
            check('Close above close 10 days ago', fmt_usd(x['close'], 0), f"above {fmt_usd(x['c10'], 0)}", x['sig_m10'] > 0),
            check('Close above close 20 days ago', fmt_usd(x['close'], 0), f"above {fmt_usd(x['c20'], 0)}", x['sig_m20'] > 0),
            check('Close above close 50 days ago', fmt_usd(x['close'], 0), f"above {fmt_usd(x['c50'], 0)}", x['sig_m50'] > 0),
            check('Close above 50-day EMA', fmt_usd(x['close'], 0), f"above {fmt_usd(x['ema50'], 0)}", x['sig_ema50'] > 0),
            check('10-day EMA above 30-day EMA', fmt_usd(x['ema10'], 0), f"above {fmt_usd(x['ema30'], 0)}", x['sig_cross'] > 0),
        ]
        groups = [
            {'title': '1 · Trend signals', 'note': 'each adds 20%', 'rows': rows},
            {'title': '2 · Sizing and calendar', 'note': 'applied to the score', 'rows': [
                check('30-day volatility at or below 80%', f"{x['vol30']:.1%}", f"size × {x['vol_factor']:.2f}", x['vol_factor'] >= 1),
                check('Outside post-halving window (day 545–910)', f'day {hs}', 'outside window', not x['halving_window']),
            ]},
        ]
        orders = [
            {'kind': 'TARGET', 'tone': 'blue', 'text': f'Hold BTC at {w:.0%} of the pot. Trade when the score or window changes, or when the holding drifts more than 10 pts from target.'},
            {'kind': 'ADD', 'tone': 'green', 'text': 'Each extra positive signal adds 20% (× the volatility factor), up to 100%.'},
            {'kind': 'EXIT', 'tone': 'red', 'text': f'Go to cash when the score reaches 0, or when the next halving window opens (~{nxt_start:%b %Y}).'},
            {'kind': 'NO FIXED STOP', 'tone': 'grey', 'text': 'Risk is controlled by the signals and volatility sizing, as tested.'},
        ]
        extra = [
            {'label': 'Dollar index, 6-month change', 'value': fmt_pct(x['dxy_6m']), 'tone': ''},
            {'label': 'Fed net liquidity, 3-month change', 'value': fmt_pct(x['netliq_3m']), 'tone': ''},
            {'label': 'Next halving (est.)', 'value': f'{NEXT_HALVING_EST:%b %Y}', 'tone': ''},
        ]
        return {
            'key': self.key, 'name': self.name, 'asof': d.strftime('%Y-%m-%d'), 'provisional': provisional,
            'kicker': 'System #2 · BTC spot daily · checks at 00:00 UTC',
            'action': action, 'action_sub': sub, 'plain': plain,
            'pills': [{'text': f"Score {x['score']:.1f} ({n_on} of 5)", 'tone': 'blue'},
                      {'text': f'Halving window: {win_txt}', 'tone': 'red' if x['halving_window'] else 'green'}],
            'groups': groups, 'orders': orders,
            'extra_title': 'Context · display only', 'extra': extra,
            'extra_note': 'Tested as position filters and dropped: they did not improve results.',
            'targets': {'BTC': w}, 'prev_targets': {'BTC': w_prev},
            'levels': {'close': float(x['close']), 'score': float(x['score']), 'vol30': float(x['vol30'])},
            'paper': self.paper, 'timing': self.timing,
        }


def _days_since_halving(idx: pd.DatetimeIndex) -> np.ndarray:
    out = np.full(len(idx), np.nan)
    for h in HALVINGS:
        m = idx >= h
        out[m] = (idx[m] - h).days
    return out
