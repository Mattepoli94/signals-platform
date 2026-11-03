"""Nasdaq-100 value-zone accumulation plan (PAC v3), UK implementation (v1.1).

Zones are judged on QQQ at the US close (the research series). Buys are made in EQQQ (ISA, pence)
at the next London close, so no currency conversion is needed. Never sells.
  Trend zone     z in (-1, 0]  AND close > 20-day SMA, where z = residual of log(close) from a
                 straight line over the last 1,260 sessions (5 years), in residual standard deviations.
  200-week zone  close 0-15% above its 1,000-day SMA AND close > 50-day SMA.
  Buy            50% of the cash, at most once every 10 trading days.
  Safety cap     on the first trading day of a month, cash above 24 x the monthly top-up is invested.
  Fast-crash buys (v1.2, from signals/bottoms.py, same rules as the Risk radar plan; skipped when the
                 override is on): buy 1 = 50% of the cash, buy 2 = all of the cash. They ignore the cooldown.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..calendar import add_trading_days
from ..indicators import sma, trend_z
from .base import Strategy, check, fmt_usd
from .qqq_regime import lag_to


class QQQValue(Strategy):
    def __init__(self):
        super().__init__(
            key='qqq_value', name='Nasdaq-100 value plan', kind='accumulate', page='investing',
            assets=('EQQQ',), inputs=('QQQ', 'EQQQ', 'GBPUSD'), calendar_asset='EQQQ',
            params=dict(frac=0.5, cooldown=10, cap_months=24, z_window=1260),
            paper='research/qqq-value-plan.html',
            timing='Zones are checked at the US close (QQQ). A buy is placed in EQQQ at the next London close (order before 16:25 UK).',
            tested={'note': 'v1.2: 10-year plans from 2000: wealth vs monthly buying -0.6% (starts 2000-08) / -1.4% (2009-16), account drawdown -42% / -29% vs -44% / -30%.'})
        self.us = None

    def compute_us(self, data: dict) -> pd.DataFrame:
        c = data['QQQ']['adj_close'].dropna()
        t = pd.DataFrame(index=c.index)
        t['close'] = c
        t['s20'], t['s50'], t['s1000'] = sma(c, 20), sma(c, 50), sma(c, 1000)
        t['z'] = trend_z(c, self.params['z_window'])
        t['vs200w'] = (c / t['s1000'] - 1) * 100
        t['trend_zone'] = (t['z'] > -1) & (t['z'] <= 0) & (c > t['s20'])
        t['w200_zone'] = (t['vs200w'] > 0) & (t['vs200w'] <= 15) & (c > t['s50'])
        t['zone'] = t['trend_zone'] | t['w200_zone']
        t['trend_line'] = _trend_line(c, self.params['z_window'])
        t['fast_b1'] = False
        t['fast_b2'] = False
        self.fast = None
        try:
            from .. import bottoms
            X, L, ovr, cnt, plans = bottoms.fast_crash_plan()
            for p in plans:
                if p['skipped']:
                    continue
                if p['buy1'] is not None and p['buy1'] in t.index:
                    t.loc[p['buy1'], 'fast_b1'] = True
                if p['buy2'] is not None and p['buy2'] in t.index:
                    t.loc[p['buy2'], 'fast_b2'] = True
            panel = bottoms.fast_panel()
            self.fast = {'level': panel['level'], 'summary': panel['summary'], 'signs': panel['signs'][:4],
                         'groups_on': int(panel['score']) if panel.get('score') == panel.get('score') else None}
        except Exception as e:  # noqa: BLE001  (radar data missing: plan runs without fast-crash buys)
            self.fast = {'level': 'NO DATA', 'summary': f'Fast-crash data unavailable: {e}'[:200], 'signs': [], 'groups_on': None}
        return t

    def compute(self, data: dict) -> pd.DataFrame:
        us = self.compute_us(data)
        self.us = us
        eq = data['EQQQ']
        idx = eq['close'].dropna().index
        t = pd.DataFrame(index=idx)
        t['close'] = eq['close'].reindex(idx)              # EQQQ, pence (trade price)
        for col in ('trend_zone', 'w200_zone', 'zone'):
            t[col] = lag_to(us[col].astype(float), idx).fillna(0).astype(bool)
        for col in ('fast_b1', 'fast_b2'):                   # one-off events: first London session after the US close
            t[col] = False
            for d in us.index[us[col].astype(bool)]:
                nxt = idx[idx > d]
                if len(nxt):
                    t.loc[nxt[0], col] = True
        t['us_date'] = lag_to(pd.Series(us.index, index=us.index), idx)
        t.attrs['us'], t.attrs['fast'] = us, self.fast   # kept with the table: a later live compute must not overwrite it
        return t

    def status(self, t: pd.DataFrame, pot: dict | None = None, provisional: bool = False) -> dict:
        us = t.attrs.get('us', self.us)
        x = us.iloc[-1]
        d = us.index[-1]
        next_lse = add_trading_days(max(d, t.index[-1]), 1, 'lse') if d >= t.index[-1] else t.index[-1]
        cash = (pot or {}).get('cash', np.nan)
        frac = self.params['frac']
        cool_left = (pot or {}).get('cooldown_left', 0)
        tz_ok = (x['z'] > -1) and (x['z'] <= 0)
        w2_ok = (x['vs200w'] > 0) and (x['vs200w'] <= 15)
        n_tz = int(tz_ok) + int(x['close'] > x['s20'])
        n_w2 = int(w2_ok) + int(x['close'] > x['s50'])
        would = cash * frac if pd.notna(cash) else np.nan
        when = f'the {next_lse:%a %d %b} London close'
        fast = t.attrs.get('fast', self.fast) or {}
        if bool(x.get('fast_b2', False)):
            action, sub = 'BUY', f'fast-crash buy 2: all cash in EQQQ at {next_lse:%d %b} London close'
            plain = (f"Fast-crash buy 2 on {d:%d %b}: QQQ made a lower close with 3+ capitulation groups on. "
                     f"Invest all the cash ({'£{:,.0f}'.format(cash) if pd.notna(cash) else 'all cash'}) in EQQQ at {when}.")
        elif bool(x.get('fast_b1', False)):
            action, sub = 'BUY', f'fast-crash buy 1: 50% of cash in EQQQ at {next_lse:%d %b} London close'
            plain = (f"Fast-crash buy 1 on {d:%d %b}: QQQ closed 10.8% below its 1-year high during a fast crash, and the override is off. "
                     f"Buy {'£{:,.0f}'.format(would) if pd.notna(would) else '50% of the cash'} of EQQQ at {when}.")
        elif x['zone'] and cool_left <= 1:
            action, sub = 'BUY', f'50% of cash in EQQQ at {next_lse:%d %b} London close'
            plain = (f"QQQ closed inside a value zone on {d:%d %b} ({'trend zone' if x['trend_zone'] else '200-week zone'}). "
                     f"Buy {'£{:,.0f}'.format(would) if pd.notna(would) else '50% of the cash'} of EQQQ in your ISA at {when}.")
        elif x['zone']:
            action, sub = 'WAIT', f'cooldown: {cool_left} more sessions'
            plain = f'QQQ is in a value zone, but the last buy was less than 10 sessions ago. Next buy allowed in {cool_left} sessions.'
        elif tz_ok:
            action, sub = 'WAIT', f"needs a QQQ close above {fmt_usd(x['s20'])}"
            plain = (f"Trend zone reached (z {x['z']:.2f}). Waiting for QQQ to turn up: a US close above its 20-day average "
                     f"({fmt_usd(x['s20'])}). The next London close after that, half the cash goes into EQQQ.")
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
                check('QQQ vs 5-year trend line (z-score)', f"{x['z']:+.2f}", 'between −1 and 0', tz_ok),
                check('QQQ close above 20-day average', fmt_usd(x['close']), f"above {fmt_usd(x['s20'])}", x['close'] > x['s20'])]},
            {'title': '200-week zone', 'note': f'{n_w2} of 2 met', 'met': n_w2 == 2, 'rows': [
                check('QQQ above 200-week (1,000-day) average', f"{x['vs200w']:+.1f}%", '0% to +15%', w2_ok),
                check('QQQ close above 50-day average', fmt_usd(x['close']), f"above {fmt_usd(x['s50'])}", x['close'] > x['s50'])]},
        ]
        if fast.get('level') in ('WATCH', 'BUY 1', 'SKIP'):
            plain += ' Fast-crash plan: ' + fast['summary'][0].lower() + fast['summary'][1:]
        groups.append({'title': 'Fast-crash buys (v1.2)', 'note': f"plan {fast.get('level', '—')}", 'met': fast.get('level') in ('BUY 1', 'BUY 2'),
                       'rows': [check(sg['label'], sg['value'], sg['trigger'], sg['on']) for sg in fast.get('signs', [])] +
                               ([check('Capitulation groups on (buy 2 needs 3 and a lower close)', f"{fast['groups_on']} of 6", '3 or more',
                                       (fast['groups_on'] or 0) >= 3)] if fast.get('groups_on') is not None else [])})
        eq_px = float(t['close'].iloc[-1])
        return {
            'key': self.key, 'name': self.name, 'asof': d.strftime('%Y-%m-%d'), 'provisional': provisional,
            'action': action, 'action_sub': sub, 'plain': plain, 'groups': groups,
            'would_buy': None if pd.isna(would) else float(would), 'executes': next_lse.strftime('%Y-%m-%d'),
            'levels': {'close': float(x['close']), 'z': float(x['z']), 'trend_line': float(x['trend_line']),
                       's20': float(x['s20']), 's50': float(x['s50']), 's1000': float(x['s1000']),
                       'zone_top_200w': float(x['s1000'] * 1.15), 'eqqq': eq_px},
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
    for i in range(max(n, len(y) - 520), len(y)):
        yy = y[i - n:i + 1]
        b = (tt * (yy - yy.mean())).sum() / den
        out[i] = np.exp(yy.mean() + b * (t[-1] - t.mean()))
    return pd.Series(out, index=c.index)
