"""Trading system #1: QQQ regime system with the dollar (UUP) add-on. Spec v1.0.

All signals on daily adjusted closes; every order is market-on-close the same day.
  Regime  Trending = close > SMA50 AND SMA50 > SMA50 ten sessions earlier.
  Trend leg  50% QQQ while Trending.
  Dip leg (new entries only when NOT Trending)
     above SMA200 -> 100% on close < lower BB(20,2)  OR 3 lower closes in a row  OR RSI(2) < 10
     at/below SMA200 -> 50% on close < lower BB(20,2) OR RSI(2) < 5
     exits: RSI(2) > 70, close <= entry x 0.97, the 10th session after entry, or regime turns Trending.
  QQQ weight = trend + dip x (1 - trend).
  Dollar add-on  UUP weight = 0.5 x (1 - QQQ weight) while UUP is Trending (same definition).
  Risk flag (display only): W1 3m T-bill +0.5 pt over 126 sessions, W2 dollar index +5% over 126
  sessions, W3 two or more of QQQ/TLT/GLD below their 200-day SMA.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..calendar import add_trading_days
from ..indicators import is_trending, lower_bollinger, sma, wilder_rsi
from .base import Strategy, check, fmt_pct, fmt_usd

SPEC_URL = 'https://claude.ai/artifact/Kjtfn4jJ1JdCrynU9ubXvc'


class QQQRegime(Strategy):
    def __init__(self):
        super().__init__(
            key='qqq_regime', name='QQQ regime system + dollar add-on', kind='weights', page='trading',
            assets=('QQQ', 'UUP'), inputs=('QQQ', 'UUP', 'TLT', 'GLD', 'IRX', 'DXY'), calendar_asset='QQQ',
            band=1.0,   # trades only when the rules change the target (weights are discrete)
            params=dict(stop=0.03, max_days=10, rsi_exit=70, rsi_in_above=10, rsi_in_below=5, uup_share=0.5),
            paper='research/qqq-regime-system.html', timing='Checks at the US close (16:00 New York). Orders are market-on-close: place them before the cut-off on the Today page (5 minutes before the close).',
            tested={'cagr': 0.104, 'maxdd': -0.153, 'period': '2000-2024', 'holdout_cagr': 0.085})

    # ------------------------------------------------------------------ signals
    def compute(self, data: dict) -> pd.DataFrame:
        p = self.params
        c = data['QQQ']['adj_close'].dropna()
        t = pd.DataFrame(index=c.index)
        t['close'] = c
        t['raw_close'] = data['QQQ']['close'].reindex(c.index)
        t['s20'], t['s50'], t['s200'] = sma(c, 20), sma(c, 50), sma(c, 200)
        t['s50_prev10'] = t['s50'].shift(10)
        t['lbb'] = lower_bollinger(c)
        t['rsi2'] = wilder_rsi(c)
        t['down_run'] = _down_run(c)
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
                if cc[i] <= entry * (1 - p['stop']): why.append('stop: close at or below entry -3%')
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
        t['w_QQQ'] = trend_w + dip_w * (1 - trend_w)
        # trend-leg events
        tw = pd.Series(trend_w, index=c.index)
        t['event_trend'] = np.where((tw > 0) & (tw.shift(1, fill_value=0) == 0), 'Trend leg on (regime turned Trending)',
                                    np.where((tw == 0) & (tw.shift(1, fill_value=0) > 0), 'Trend leg off (regime no longer Trending)', ''))

        # dollar add-on
        if 'UUP' in data and len(data['UUP']):
            u = data['UUP']['adj_close'].dropna()
            us50 = sma(u, 50)
            t['uup_close'] = u.reindex(c.index)
            t['uup_s50'] = us50.reindex(c.index)
            t['uup_s50_prev10'] = us50.shift(10).reindex(c.index)
            t['uup_trending'] = is_trending(u).reindex(c.index).fillna(False).astype(bool)
        else:
            t['uup_close'] = t['uup_s50'] = t['uup_s50_prev10'] = np.nan
            t['uup_trending'] = False
        t['w_UUP'] = np.where(t['uup_trending'], p['uup_share'] * (1 - t['w_QQQ']), 0.0)
        t['state'] = t['w_QQQ'].round(4).astype(str) + '|' + t['w_UUP'].round(4).astype(str)

        # risk flag (display only)
        irx = _align(data.get('IRX'), c.index)
        dxy = _align(data.get('DXY'), c.index)
        t['irx'] = irx
        t['w1_val'] = irx - irx.shift(126)
        t['dxy'] = dxy
        t['w2_val'] = (dxy / dxy.shift(126) - 1) * 100
        below_n = (c < t['s200']).astype(int)
        names = []
        for k in ('TLT', 'GLD'):
            s = _align(data.get(k), c.index)
            b = (s < sma(s, 200)).fillna(False)
            t[f'{k.lower()}_below'] = b
            below_n = below_n + b.astype(int)
        t['qqq_below'] = c < t['s200']
        t['w3_val'] = below_n
        t['W1'], t['W2'], t['W3'] = t['w1_val'] > 0.5, t['w2_val'] > 5, t['w3_val'] >= 2
        t['risk_score'] = t[['W1', 'W2', 'W3']].sum(axis=1)
        t['risk_level'] = t['risk_score'].map({0: 'GREEN', 1: 'AMBER'}).fillna('RED')
        return t

    # ------------------------------------------------------------------ dashboard
    def status(self, t: pd.DataFrame, pot: dict | None = None, provisional: bool = False) -> dict:
        x, prev = t.iloc[-1], t.iloc[-2]
        d = t.index[-1]
        w, w_prev = x['w_QQQ'], prev['w_QQQ']
        u, u_prev = x['w_UUP'], prev['w_UUP']
        p = self.params

        # action
        if w > w_prev:
            action, sub = 'BUY', f'QQQ to {w:.0%} at the close'
        elif w < w_prev:
            action, sub = ('SELL', 'QQQ to 0% at the close') if w == 0 else ('REDUCE', f'QQQ to {w:.0%} at the close')
        elif w > 0:
            action, sub = 'HOLD', f'QQQ {w:.0%}'
        else:
            action, sub = 'FLAT', 'no QQQ position'
        if u != u_prev and action in ('HOLD', 'FLAT'):
            action, sub = ('BUY', f'UUP to {u:.0%}') if u > u_prev else ('SELL', f'UUP to {u:.0%}')

        dip_open = x['w_dip'] > 0
        entry = x['dip_entry']
        stop = x['dip_stop']
        exit_date = add_trading_days(x['dip_entry_date'], p['max_days']) if dip_open else None

        # plain-English summary
        reg = x['regime']
        if x['event_in']:
            plain = (f"{x['event_in']}. Buy at the {d:%d %b} close (reference ${x['close']:,.2f}); "
                     f"stop on a close at or below ${stop:,.2f}; time exit {exit_date:%d %b}.")
        elif x['event_out']:
            plain = f"Dip trade closed: {x['event_out']}. Sell the dip position at the {d:%d %b} close."
        elif x['event_trend']:
            plain = f"{x['event_trend']}. Trade at the {d:%d %b} close so QQQ is {w:.0%} of the pot."
        elif dip_open:
            plain = (f"Dip trade open since {x['dip_entry_date']:%d %b} (day {int(x['dip_days'])} of 10). "
                     f"Hold. Exit on RSI(2) above 70, a close at or below ${stop:,.2f}, or the {exit_date:%d %b} close.")
        elif x['trending']:
            plain = 'Regime is Trending: hold the 50% trend leg. Dip entries are paused while Trending.'
        else:
            plain = f'Regime: {reg}. No dip signal today; stay in cash (plus the dollar add-on when UUP trends).'

        tone_reg = {'Trending': 'green', 'Range above 200-day': 'blue', 'Below 200-day': 'red'}[reg]
        lvl = x['risk_level']
        groups = [
            {'title': '1 · Regime', 'note': 'decides which leg is live', 'rows': [
                check('Close above 50-day average', fmt_usd(x['close']), f"above {fmt_usd(x['s50'])}", x['close'] > x['s50']),
                check('50-day average rising (vs 10 sessions ago)', fmt_usd(x['s50']), f"above {fmt_usd(x['s50_prev10'])}", x['s50'] > x['s50_prev10']),
                check('Close above 200-day average', fmt_usd(x['close']), f"above {fmt_usd(x['s200'])}", x['above200']),
            ]},
        ]
        if x['above200']:
            dip_rows = [
                check('RSI(2) below 10', f"{x['rsi2']:.2f}", 'below 10', x['rsi2'] < 10),
                check('Close below lower Bollinger band (20, 2)', fmt_usd(x['close']), f"below {fmt_usd(x['lbb'])}", x['close'] < x['lbb']),
                check('3 lower closes in a row', f"{int(x['down_run'])}", '3', x['down_run'] >= 3),
            ]
            title = '2 · Dip entry, above 200-day → 100%'
        else:
            dip_rows = [
                check('RSI(2) below 5', f"{x['rsi2']:.2f}", 'below 5', x['rsi2'] < 5),
                check('Close below lower Bollinger band (20, 2)', fmt_usd(x['close']), f"below {fmt_usd(x['lbb'])}", x['close'] < x['lbb']),
            ]
            title = '2 · Dip entry, below 200-day → 50%'
        groups.append({'title': title, 'note': 'any one fires (only when not Trending)', 'rows': dip_rows})
        if dip_open:
            groups.append({'title': '3 · Open dip trade: exits', 'note': 'any one closes it', 'rows': [
                check('RSI(2) above 70', f"{x['rsi2']:.2f}", 'above 70', x['rsi2'] > 70),
                check('Stop: close at or below entry − 3%', fmt_usd(x['close']), f"at/below {fmt_usd(stop)}", x['close'] <= stop),
                check('Time exit: 10th session', f"day {int(x['dip_days'])}", f"{exit_date:%d %b}", x['dip_days'] >= 10),
            ]})
        groups.append({'title': f'{len(groups) + 1} · Dollar add-on (UUP)', 'note': '0.5 × the share not in QQQ', 'rows': [
            check('UUP above its 50-day average', fmt_usd(x['uup_close']), f"above {fmt_usd(x['uup_s50'])}", x['uup_close'] > x['uup_s50']),
            check('UUP 50-day average rising', fmt_usd(x['uup_s50']), f"above {fmt_usd(x['uup_s50_prev10'])}", x['uup_s50'] > x['uup_s50_prev10']),
            check('Room for the add-on (QQQ below 100%)', f'{w:.0%}', 'below 100%', w < 1),
        ]})

        orders = []
        if dip_open:
            orders.append({'kind': 'ENTRY', 'tone': 'green', 'text': f"Dip entry {x['dip_entry_date']:%d %b} at ${entry:,.2f} (market-on-close)."})
            orders.append({'kind': 'STOP LOSS', 'tone': 'red', 'text': f'Sell at the close if QQQ closes at or below ${stop:,.2f} (entry − 3%).'})
            orders.append({'kind': 'TAKE PROFIT', 'tone': 'blue', 'text': 'Sell at the close when RSI(2) closes above 70.'})
            orders.append({'kind': 'TIME / REGIME EXIT', 'tone': 'grey', 'text': f'Sell at the {exit_date:%d %b} close (10th session), or earlier if the regime turns Trending.'})
        else:
            orders.append({'kind': 'NEXT ENTRY', 'tone': 'green', 'text': (
                'Paused while Trending (trend leg holds 50%).' if x['trending'] else
                (f"Buy 100% at the close on RSI(2) below 10, a close below ${x['lbb']:,.2f}, or 3 lower closes." if x['above200']
                 else f"Buy 50% at the close on RSI(2) below 5 or a close below ${x['lbb']:,.2f}."))})
            orders.append({'kind': 'STOP LOSS', 'tone': 'red', 'text': 'Set on entry: a close at or below entry − 3%.'})
            if x['trending']:
                orders.append({'kind': 'TREND EXIT', 'tone': 'grey', 'text': f"Sell the trend leg at the close when the regime stops Trending (close below ${x['s50']:,.2f} or a falling 50-day)."})
        orders.append({'kind': 'DOLLAR ADD-ON', 'tone': 'blue', 'text': f'UUP target {u:.0%} of the pot ' + ('(UUP trending).' if x['uup_trending'] else '(UUP not trending).')})

        below = [k for k, b in (('QQQ', x['qqq_below']), ('TLT', x['tlt_below']), ('GLD', x['gld_below'])) if b]
        extra = [
            {'label': 'W1 · 3-month T-bill +0.5 pt over 6 months', 'value': f"{x['w1_val']:+.2f} pt" if pd.notna(x['w1_val']) else '—', 'tone': 'amber' if x['W1'] else ''},
            {'label': 'W2 · dollar index +5% over 6 months', 'value': fmt_pct(x['w2_val'], 2), 'tone': 'amber' if x['W2'] else ''},
            {'label': 'W3 · 2+ of QQQ/TLT/GLD below 200-day', 'value': ', '.join(below) or 'none', 'tone': 'amber' if x['W3'] else ''},
        ]
        return {
            'key': self.key, 'name': self.name, 'asof': d.strftime('%Y-%m-%d'), 'provisional': provisional,
            'kicker': 'System #1 · QQQ daily · orders at the close',
            'action': action, 'action_sub': sub, 'plain': plain,
            'pills': [{'text': f'Regime: {reg}', 'tone': tone_reg},
                      {'text': f"Risk flag: {lvl} ({int(x['risk_score'])} of 3)", 'tone': {'GREEN': 'green', 'AMBER': 'amber', 'RED': 'red'}[lvl]}],
            'groups': groups, 'orders': orders,
            'extra_title': 'Risk flag · display only, does not change orders', 'extra': extra,
            'extra_note': '2+ warnings marked years like 2015 and 2022. One warning: stay alert.',
            'targets': {'QQQ': float(w), 'UUP': float(u)}, 'prev_targets': {'QQQ': float(w_prev), 'UUP': float(u_prev)},
            'levels': {'close': float(x['close']), 'stop': None if pd.isna(stop) else float(stop),
                       'entry': None if pd.isna(entry) else float(entry),
                       'exit_date': exit_date.strftime('%Y-%m-%d') if exit_date is not None else None,
                       'risk_level': lvl},
            'paper': self.paper, 'timing': self.timing,
        }


def _down_run(c: pd.Series) -> pd.Series:
    dn = (c < c.shift(1)).astype(int)
    return dn.groupby((dn == 0).cumsum()).cumsum()


def _align(df, idx):
    if df is None or len(df) == 0:
        return pd.Series(np.nan, index=idx)
    s = df['adj_close'].dropna()
    return s.reindex(s.index.union(idx)).ffill().reindex(idx)
