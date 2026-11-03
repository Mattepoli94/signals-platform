"""QQQ value-zone accumulation plan (PAC v3).

Contributions wait in cash. On a daily close inside either value zone, buy `frac` (50%) of the cash
at the close, at most once every 10 trading days. Never sells.
  Trend zone     z in (-1, 0]  AND close > 20-day SMA, where z = residual of log(close) from a
                 straight line over the last 1,260 sessions (5 years), in residual standard deviations.
  200-week zone  close 0-15% above its 1,000-day SMA AND close > 50-day SMA.
  Safety cap     on the first trading day of a month, cash above 24 x the monthly top-up is invested.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..indicators import sma, trend_z
from .base import Strategy, check, fmt_usd


class QQQValue(Strategy):
    def __init__(self):
        super().__init__(
            key='qqq_value', name='QQQ value plan', kind='accumulate', page='investing',
            assets=('QQQ',), inputs=('QQQ',), calendar_asset='QQQ',
            params=dict(frac=0.5, cooldown=10, cap_months=24, z_window=1260),
            paper='research/qqq-value-plan.html',
            timing='Checks at the US close (16:00 New York). Buys are market-on-close: place them before the cut-off on the Today page (5 minutes before the close).',
            tested={'note': 'Median 10-year plan from 2000: account drawdown -34% vs -49% for monthly buying; wealth -5.4%.'})

    def compute(self, data: dict) -> pd.DataFrame:
        c = data['QQQ']['adj_close'].dropna()
        t = pd.DataFrame(index=c.index)
        t['close'] = c
        t['s20'], t['s50'], t['s1000'] = sma(c, 20), sma(c, 50), sma(c, 1000)
        t['z'] = trend_z(c, self.params['z_window'])
        t['vs200w'] = (c / t['s1000'] - 1) * 100
        # trend line level (z = 0) and the -1 sd line, for display
        t['trend_zone'] = (t['z'] > -1) & (t['z'] <= 0) & (c > t['s20'])
        t['w200_zone'] = (t['vs200w'] > 0) & (t['vs200w'] <= 15) & (c > t['s50'])
        t['zone'] = t['trend_zone'] | t['w200_zone']
        t['trend_line'] = _trend_line(c, self.params['z_window'])
        return t

    def status(self, t: pd.DataFrame, pot: dict | None = None, provisional: bool = False) -> dict:
        x = t.iloc[-1]
        d = t.index[-1]
        cash = (pot or {}).get('cash', np.nan)
        frac = self.params['frac']
        cool_left = (pot or {}).get('cooldown_left', 0)
        tz_ok = (x['z'] > -1) and (x['z'] <= 0)
        w2_ok = (x['vs200w'] > 0) and (x['vs200w'] <= 15)
        n_tz = int(tz_ok) + int(x['close'] > x['s20'])
        n_w2 = int(w2_ok) + int(x['close'] > x['s50'])
        would = cash * frac if pd.notna(cash) else np.nan

        if x['zone'] and cool_left <= 0:
            action, sub = 'BUY', f'50% of cash at the close'
            plain = (f"QQQ closed inside a value zone ({'trend zone' if x['trend_zone'] else '200-week zone'}). "
                     f"Buy {'£{:,.0f}'.format(would) if pd.notna(would) else '50% of the cash'} of QQQ at the {d:%d %b} close.")
        elif x['zone']:
            action, sub = 'WAIT', f'cooldown: {cool_left} more sessions'
            plain = f'QQQ is in a value zone, but the last buy was less than 10 sessions ago. Next buy allowed in {cool_left} sessions.'
        elif tz_ok:
            action, sub = 'WAIT', f"needs a close above {fmt_usd(x['s20'])}"
            plain = (f"Trend zone reached (z {x['z']:.2f}). Waiting for price to turn up: a close above the 20-day average "
                     f"({fmt_usd(x['s20'])}). That close triggers a buy of half the cash.")
        elif x['z'] <= -1:
            action, sub = 'WAIT', 'below the trend zone'
            plain = (f"QQQ is more than 1 sd below its 5-year trend (z {x['z']:.2f}): falling-knife territory. "
                     'The plan waits for the 200-week zone or a recovery into the trend zone.')
        else:
            action, sub = 'WAIT', 'above value zones'
            plain = (f"QQQ is above its 5-year trend line (z {x['z']:+.2f}) and {x['vs200w']:.0f}% above its 200-week average. "
                     'Cash keeps building until price comes back to value.')

        groups = [
            {'title': 'Trend zone', 'note': f'{n_tz} of 2 met', 'met': n_tz == 2, 'rows': [
                check('Price vs 5-year trend line (z-score)', f"{x['z']:+.2f}", 'between −1 and 0', tz_ok),
                check('Close above 20-day average', fmt_usd(x['close']), f"above {fmt_usd(x['s20'])}", x['close'] > x['s20']),
            ]},
            {'title': '200-week zone', 'note': f'{n_w2} of 2 met', 'met': n_w2 == 2, 'rows': [
                check('Price above 200-week (1,000-day) average', f"{x['vs200w']:+.1f}%", '0% to +15%', w2_ok),
                check('Close above 50-day average', fmt_usd(x['close']), f"above {fmt_usd(x['s50'])}", x['close'] > x['s50']),
            ]},
        ]
        return {
            'key': self.key, 'name': self.name, 'asof': d.strftime('%Y-%m-%d'), 'provisional': provisional,
            'action': action, 'action_sub': sub, 'plain': plain, 'groups': groups,
            'would_buy': None if pd.isna(would) else float(would),
            'levels': {'close': float(x['close']), 'z': float(x['z']), 'trend_line': float(x['trend_line']),
                       's20': float(x['s20']), 's50': float(x['s50']), 's1000': float(x['s1000']),
                       'zone_top_200w': float(x['s1000'] * 1.15)},
            'targets': {}, 'paper': self.paper, 'timing': self.timing,
        }


def _trend_line(c: pd.Series, n: int) -> pd.Series:
    """Fitted value of the trailing 5-year log-linear trend at each date (the z = 0 level)."""
    y = np.log(c.values.astype(float))
    out = np.full(len(y), np.nan)
    if len(y) <= n:
        return pd.Series(out, index=c.index)
    t = np.arange(n + 1, dtype=float)
    tt = t - t.mean(); den = (tt ** 2).sum()
    for i in range(max(n, len(y) - 400), len(y)):      # recent 400 sessions are enough for charts
        yy = y[i - n:i + 1]
        b = (tt * (yy - yy.mean())).sum() / den
        out[i] = np.exp(yy.mean() + b * (t[-1] - t.mean()))
    return pd.Series(out, index=c.index)
