"""Trading system #1, UK implementation (v1.1): Nasdaq-100 regime system on EQQQ + US dollar add-on.

Signals and trades at the LONDON close (16:30 UK) on Invesco EQQQ Nasdaq-100 UCITS ETF (LSE, pence),
held in the ISA: no currency conversion, so no FX fee. Rules are the v1.0 research rules, unchanged:
  Regime  Trending = close > SMA50 AND SMA50 > SMA50 ten sessions earlier.
  Trend leg  50% while Trending.
  Dip leg (new entries only when NOT Trending)
     above SMA200 -> 100% on close < lower BB(20,2)  OR 3 lower closes in a row  OR RSI(2) < 10
     at/below SMA200 -> 50% on close < lower BB(20,2) OR RSI(2) < 5
     exits: RSI(2) > 70, close <= entry x 0.97, the 10th session after entry, or regime turns Trending.
  EQQQ weight = trend + dip x (1 - trend).
  Dollar add-on  USD cash (Invest account) = 0.5 x (1 - EQQQ weight) while UUP is Trending, judged at
  the latest US close before the London close. Each switch converts GBP<->USD (0.15% fee).
  The old 3-point risk flag (W1-W3) was retired on 3 Nov 2026: the Risk radar page replaces it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..calendar import add_trading_days
from ..indicators import is_trending, lower_bollinger, sma, wilder_rsi
from .base import Strategy, check, fmt_pct

SPEC_URL = 'https://claude.ai/artifact/Kjtfn4jJ1JdCrynU9ubXvc'


def fmt_p(x):
    """Pence -> pounds."""
    return '—' if x is None or pd.isna(x) else f'£{x / 100:,.2f}'


def fmt_usd(x):
    return '—' if x is None or pd.isna(x) else f'${x:,.2f}'


def regime_core(c: pd.Series, p: dict) -> pd.DataFrame:
    """The v1.0 rules on any daily close series."""
    t = pd.DataFrame(index=c.index)
    t['close'] = c
    t['s20'], t['s50'], t['s200'] = sma(c, 20), sma(c, 50), sma(c, 200)
    t['s50_prev10'] = t['s50'].shift(10)
    t['lbb'] = lower_bollinger(c)
    t['rsi2'] = wilder_rsi(c)
    dn = (c < c.shift(1)).astype(int)
    t['down_run'] = dn.groupby((dn == 0).cumsum()).cumsum()
    trend = is_trending(c).values
    above = (c > t['s200']).values
    below = ((c <= t['s200']) & t['s200'].notna()).values
    lbb = (c < t['lbb']).values
    down3 = (t['down_run'] >= 3).values
    r, cc = t['rsi2'].values, c.values
    n = len(c)
    trend_w, dip_w = np.zeros(n), np.zeros(n)
    entry_px = np.full(n, np.nan); entry_i = np.full(n, -1); days_in = np.zeros(n, int)
    ev_in = np.array([''] * n, dtype=object); ev_out = np.array([''] * n, dtype=object)
    dip_open, dip_sz, days, entry, e_i = False, 0.0, 0, np.nan, -1
    for i in range(n):
        tp = 0.5 if trend[i] else 0.0
        if dip_open:
            days += 1
            why = []
            if r[i] > p['rsi_exit']: why.append('RSI(2) above 70')
            if cc[i] <= entry * (1 - p['stop']): why.append('stop: close at or below entry −3%')
            if days >= p['max_days']: why.append('10th session (time exit)')
            if trend[i]: why.append('regime turned Trending')
            if why:
                dip_open, dip_sz = False, 0.0
                ev_out[i] = '; '.join(why)
        elif not trend[i]:
            if above[i] and (lbb[i] or down3[i] or r[i] < p['rsi_in_above']):
                why = [w for w, ok in (('close below lower Bollinger band', lbb[i]), ('3 lower closes', down3[i]),
                                       ('RSI(2) below 10', r[i] < p['rsi_in_above'])) if ok]
                dip_open, dip_sz, days, entry, e_i = True, 1.0, 0, cc[i], i
                ev_in[i] = 'Dip entry 100% (above 200-day): ' + ', '.join(why)
            elif below[i] and (lbb[i] or r[i] < p['rsi_in_below']):
                why = [w for w, ok in (('close below lower Bollinger band', lbb[i]), ('RSI(2) below 5', r[i] < p['rsi_in_below'])) if ok]
                dip_open, dip_sz, days, entry, e_i = True, 0.5, 0, cc[i], i
                ev_in[i] = 'Dip entry 50% (below 200-day): ' + ', '.join(why)
        trend_w[i], dip_w[i] = tp, dip_sz
        if dip_open:
            entry_px[i], entry_i[i], days_in[i] = entry, e_i, days
    t['trending'] = trend
    t['above200'] = above
    t['regime'] = np.where(trend, 'Trending', np.where(above, 'Range above 200-day', 'Below 200-day'))
    t['w_trend'], t['w_dip'] = trend_w, dip_w
    t['dip_entry'] = entry_px
    t['dip_entry_date'] = [c.index[j] if j >= 0 else pd.NaT for j in entry_i]
    t['dip_days'] = days_in
    t['dip_stop'] = t['dip_entry'] * (1 - p['stop'])
    t['event_in'], t['event_out'] = ev_in, ev_out
    t['w_core'] = trend_w + dip_w * (1 - trend_w)
    tw = pd.Series(trend_w, index=c.index)
    t['event_trend'] = np.where((tw > 0) & (tw.shift(1, fill_value=0) == 0), 'Trend leg on (regime turned Trending)',
                                np.where((tw == 0) & (tw.shift(1, fill_value=0) > 0), 'Trend leg off (regime no longer Trending)', ''))
    return t


def lag_to(s: pd.Series, idx: pd.DatetimeIndex) -> pd.Series:
    """Value known at each London date from a US-close series: the latest US date strictly before it."""
    s = s.copy()
    s.index = s.index + pd.Timedelta(days=1)
    return s.reindex(s.index.union(idx)).ffill().reindex(idx)


def _align(df, idx):
    if df is None or len(df) == 0:
        return pd.Series(np.nan, index=idx)
    s = df['adj_close'].dropna()
    return s.reindex(s.index.union(idx)).ffill().reindex(idx)


class QQQRegime(Strategy):
    def __init__(self):
        super().__init__(
            key='qqq_regime', name='Nasdaq-100 regime system + dollar add-on', kind='weights', page='trading',
            assets=('EQQQ', 'USD'), inputs=('EQQQ', 'QQQ', 'UUP', 'GBPUSD'), calendar_asset='EQQQ',
            band=1.0,   # trades only when the rules change the target (weights are discrete)
            params=dict(stop=0.03, max_days=10, rsi_exit=70, rsi_in_above=10, rsi_in_below=5, usd_share=0.5),
            paper='research/qqq-regime-system.html',
            timing='Signals on EQQQ at the London close (16:30 UK). Place orders before 16:25 UK using the ~16:05 preview email.',
            tested={'cagr': 0.090, 'maxdd': -0.141, 'period': '2010-2024, EQQQ at the London close, dollar add-on, cash 0%'})

    def compute(self, data: dict) -> pd.DataFrame:
        p = self.params
        eq = data['EQQQ']
        c = eq['adj_close'].dropna()
        t = regime_core(c, p)
        t['raw_close'] = eq['close'].reindex(c.index)
        t['w_EQQQ'] = t['w_core']

        # dollar add-on: UUP trend at the latest US close before this London close
        idx = c.index
        if 'UUP' in data and len(data['UUP']):
            u = data['UUP']['adj_close'].dropna()
            us50 = sma(u, 50)
            t['uup_close'] = lag_to(u, idx)
            t['uup_s50'] = lag_to(us50, idx)
            t['uup_s50_prev10'] = lag_to(us50.shift(10), idx)
            t['uup_trending'] = lag_to(is_trending(u).astype(float), idx).fillna(0).astype(bool)
            t['uup_date'] = lag_to(pd.Series(u.index, index=u.index), idx)
        else:
            t['uup_close'] = t['uup_s50'] = t['uup_s50_prev10'] = np.nan
            t['uup_trending'] = False
            t['uup_date'] = pd.NaT
        t['w_USD'] = np.where(t['uup_trending'], p['usd_share'] * (1 - t['w_EQQQ']), 0.0)
        t['state'] = t['w_EQQQ'].round(4).astype(str) + '|' + t['w_USD'].round(4).astype(str)

        return t

    def status(self, t: pd.DataFrame, pot: dict | None = None, provisional: bool = False) -> dict:
        x, prev = t.iloc[-1], t.iloc[-2]
        d = t.index[-1]
        w, w_prev = x['w_EQQQ'], prev['w_EQQQ']
        u, u_prev = x['w_USD'], prev['w_USD']
        p = self.params
        if w > w_prev:
            action, sub = 'BUY', f'EQQQ to {w:.0%} at the London close'
        elif w < w_prev:
            action, sub = ('SELL', 'EQQQ to 0% at the London close') if w == 0 else ('REDUCE', f'EQQQ to {w:.0%} at the London close')
        elif w > 0:
            action, sub = 'HOLD', f'EQQQ {w:.0%}'
        else:
            action, sub = 'FLAT', 'no EQQQ position'
        if u != u_prev and action in ('HOLD', 'FLAT'):
            action, sub = ('BUY', f'USD cash to {u:.0%}') if u > u_prev else ('SELL', f'USD cash to {u:.0%}')

        dip_open = x['w_dip'] > 0
        entry, stop = x['dip_entry'], x['dip_stop']
        exit_date = add_trading_days(x['dip_entry_date'], p['max_days'], 'lse') if dip_open else None
        reg = x['regime']
        when = 'today\'s London close' if provisional else f'the {d:%d %b} London close'
        if x['event_in']:
            plain = (f"{x['event_in']}. Buy EQQQ at {when} (reference {fmt_p(x['close'])}); "
                     f"stop on a close at or below {fmt_p(stop)}; time exit {exit_date:%d %b}.")
        elif x['event_out']:
            plain = f"Dip trade closed: {x['event_out']}. Sell the dip position at {when}."
        elif x['event_trend']:
            plain = f"{x['event_trend']}. Trade at {when} so EQQQ is {w:.0%} of the pot."
        elif dip_open:
            plain = (f"Dip trade open since {x['dip_entry_date']:%d %b} (day {int(x['dip_days'])} of 10). Hold. "
                     f"Exit on RSI(2) above 70, a close at or below {fmt_p(stop)}, or the {exit_date:%d %b} close.")
        elif x['trending']:
            plain = 'Regime is Trending: hold the 50% trend leg. Dip entries are paused while Trending.'
        else:
            plain = f'Regime: {reg}. No dip signal; stay in cash (plus USD cash when the dollar trends).'

        groups = [
            {'title': '1 · Regime (EQQQ, London closes)', 'note': 'decides which leg is live', 'rows': [
                check('Close above 50-day average', fmt_p(x['close']), f"above {fmt_p(x['s50'])}", x['close'] > x['s50']),
                check('50-day average rising (vs 10 sessions ago)', fmt_p(x['s50']), f"above {fmt_p(x['s50_prev10'])}", x['s50'] > x['s50_prev10']),
                check('Close above 200-day average', fmt_p(x['close']), f"above {fmt_p(x['s200'])}", x['above200']),
            ]},
        ]
        if x['above200']:
            groups.append({'title': '2 · Dip entry, above 200-day → 100%', 'note': 'any one fires (only when not Trending)', 'rows': [
                check('RSI(2) below 10', f"{x['rsi2']:.2f}", 'below 10', x['rsi2'] < 10),
                check('Close below lower Bollinger band (20, 2)', fmt_p(x['close']), f"below {fmt_p(x['lbb'])}", x['close'] < x['lbb']),
                check('3 lower closes in a row', f"{int(x['down_run'])}", '3', x['down_run'] >= 3)]})
        else:
            groups.append({'title': '2 · Dip entry, below 200-day → 50%', 'note': 'any one fires (only when not Trending)', 'rows': [
                check('RSI(2) below 5', f"{x['rsi2']:.2f}", 'below 5', x['rsi2'] < 5),
                check('Close below lower Bollinger band (20, 2)', fmt_p(x['close']), f"below {fmt_p(x['lbb'])}", x['close'] < x['lbb'])]})
        if dip_open:
            groups.append({'title': '3 · Open dip trade: exits', 'note': 'any one closes it', 'rows': [
                check('RSI(2) above 70', f"{x['rsi2']:.2f}", 'above 70', x['rsi2'] > 70),
                check('Stop: close at or below entry − 3%', fmt_p(x['close']), f"at/below {fmt_p(stop)}", x['close'] <= stop),
                check('Time exit: 10th session', f"day {int(x['dip_days'])}", f"{exit_date:%d %b}", x['dip_days'] >= 10)]})
        ud = x['uup_date']
        groups.append({'title': f'{len(groups) + 1} · Dollar add-on (USD cash, Invest)', 'note': f"UUP at the {pd.Timestamp(ud):%d %b} US close" if pd.notna(ud) else '', 'rows': [
            check('UUP above its 50-day average', fmt_usd(x['uup_close']), f"above {fmt_usd(x['uup_s50'])}", x['uup_close'] > x['uup_s50']),
            check('UUP 50-day average rising', fmt_usd(x['uup_s50']), f"above {fmt_usd(x['uup_s50_prev10'])}", x['uup_s50'] > x['uup_s50_prev10']),
            check('Room for the add-on (EQQQ below 100%)', f'{w:.0%}', 'below 100%', w < 1)]})

        orders = []
        if dip_open:
            orders += [
                {'kind': 'ENTRY', 'tone': 'green', 'text': f"Dip entry {x['dip_entry_date']:%d %b} at {fmt_p(entry)} (ISA, London close)."},
                {'kind': 'STOP LOSS', 'tone': 'red', 'text': f'Sell at the London close if EQQQ closes at or below {fmt_p(stop)} (entry − 3%).'},
                {'kind': 'TAKE PROFIT', 'tone': 'blue', 'text': 'Sell at the London close when RSI(2) closes above 70.'},
                {'kind': 'TIME / REGIME EXIT', 'tone': 'grey', 'text': f'Sell at the {exit_date:%d %b} London close (10th session), or earlier if the regime turns Trending.'}]
        else:
            orders.append({'kind': 'NEXT ENTRY', 'tone': 'green', 'text': (
                'Paused while Trending (trend leg holds 50%).' if x['trending'] else
                (f"Buy 100% at the London close on RSI(2) below 10, a close below {fmt_p(x['lbb'])}, or 3 lower closes." if x['above200']
                 else f"Buy 50% at the London close on RSI(2) below 5 or a close below {fmt_p(x['lbb'])}."))})
            orders.append({'kind': 'STOP LOSS', 'tone': 'red', 'text': 'Set on entry: a London close at or below entry − 3%.'})
            if x['trending']:
                orders.append({'kind': 'TREND EXIT', 'tone': 'grey', 'text': f"Sell the trend leg at the London close when the regime stops Trending (close below {fmt_p(x['s50'])} or a falling 50-day)."})
        orders.append({'kind': 'DOLLAR ADD-ON', 'tone': 'blue', 'text': f'USD cash target {u:.0%} of the pot in your Invest account ' +
                       ('(UUP trending). ' if x['uup_trending'] else '(UUP not trending). ') + 'Each switch is a GBP↔USD conversion (0.15%).'})
        return {
            'key': self.key, 'name': self.name, 'asof': d.strftime('%Y-%m-%d'), 'provisional': provisional,
            'kicker': 'System #1 · EQQQ (ISA) daily · orders at the London close',
            'action': action, 'action_sub': sub, 'plain': plain,
            'pills': [{'text': f'Regime: {reg}', 'tone': {'Trending': 'green', 'Range above 200-day': 'blue', 'Below 200-day': 'red'}[reg]},
                      ],
            'groups': groups, 'orders': orders,
            'extra_title': None, 'extra': [], 'extra_note': None,
            'targets': {'EQQQ': float(w), 'USD': float(u)}, 'prev_targets': {'EQQQ': float(w_prev), 'USD': float(u_prev)},
            'levels': {'close': float(x['raw_close']), 'close_fmt': fmt_p(x['raw_close']),
                       'stop': None if pd.isna(stop) else float(stop), 'stop_fmt': fmt_p(stop) if pd.notna(stop) else None,
                       'entry': None if pd.isna(entry) else float(entry),
                       'exit_date': exit_date.strftime('%Y-%m-%d') if exit_date is not None else None},
            'paper': self.paper, 'timing': self.timing,
        }
