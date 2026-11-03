"""Manual trading: your discretionary systems, risk rules and trade journal.

Trades live in config/portfolio.yaml under `manual.trades` (written by the Manual trading page).
Everything below is computed from them on every run: risk, reward-to-risk, time in the trade,
realised P&L in GBP, R multiples, and statistics per system.
"""
from __future__ import annotations

import uuid
from datetime import date

import numpy as np
import pandas as pd

SYSTEMS = {
    '1': {'name': 'Box system: early entry', 'short': 'Box', 'side': 'long',
          'idea': 'Enter early inside a consolidation box after a mark-up, before the next leg up.',
          'rules': [
              'Indices trending (not consolidating), or indices reclaiming the 9-week MA after a flush and a breadth washout',
              'A previous mark-up, then a consolidation before the next leg up',
              'No more than 1 push so far: not 2 higher highs and higher lows on the monthly chart (wicks count), as moves usually come in 2 pushes',
              'A fake breakdown (liquidity grab) raises the odds',
              'A leader: one of the strongest names in one of the strongest sectors',
              'Fundamentals add confluence: earnings, forecasts, profit, balance sheet, insider buying',
              'Above all the MAs, with the MAs curling up',
              'Squeeze Pro on the weekly shows a red or yellow (consolidation) squeeze',
              'Variation B: an undercut of the box that closes back inside on strong volume is a valid early entry',
          ]},
    '2': {'name': 'Breakout trading', 'short': 'Breakout', 'side': 'long',
          'idea': 'Buy the break of the box when the market is trending; get out fast if the break fails.',
          'rules': [
              'Indices trending and not chopping',
              'A leader with strong fundamentals',
              'Stop at the first resistance or MA inside the box',
              'The break has momentum and follow-through',
              'An indecision candle or a failed breakout usually sends price back to the origin of the move: exit quickly',
          ]},
    '3': {'name': 'Mean reversion', 'short': 'Mean rev.', 'side': 'long',
          'idea': 'Buy the first retest of an extreme value zone, with a tight stop, targeting a 50% retracement.',
          'rules': [
              'Volatile stock, preferably with strong fundamentals',
              'Levels and value zones marked on the 1-hour or daily chart',
              'Early entry at an imbalance block in the extreme zone (value-area high or low)',
              'First retest only, closing back within the swing low: that is where the reaction is strongest',
              'Tight stop: 1.2× beyond the swing-low wick',
              'Add to the position on a break of structure on a smaller timeframe',
              'Target a 50% retracement or a key level (POC, MAs, resistance)',
          ]},
    '4': {'name': 'Trend following: long', 'short': 'Trend long', 'side': 'long',
          'idea': 'Ride an uptrend; enter on a pullback to a moving average.',
          'rules': [
              'Uptrend in place; stop on a close below the slow MA or a market-structure break (MSB)',
              'Low-risk entry on a retest of the fast or slow MA',
          ]},
    '5': {'name': 'Trend following: short', 'short': 'Trend short', 'side': 'short',
          'idea': 'Ride a downtrend; enter short on a rally to a moving average.',
          'rules': [
              'Downtrend in place; stop on a close above the slow MA or a market-structure break (MSB)',
              'Low-risk entry on a retest of the fast or slow MA',
          ]},
}

DEFAULTS = {'capital': 857.0, 'target_share_pct': 30.0, 'risk_pct': 0.5, 'risk_base': 'portfolio',
            'max_open': 5, 'max_per_system': 3}


def settings(cfg: dict) -> dict:
    m = cfg.get('manual') or {}
    out = {**DEFAULTS, **{k: v for k, v in m.items() if k != 'trades'}}
    out['trades'] = m.get('trades') or []
    return out


# ----------------------------------------------------------------------------- money
def _fx(fx: pd.Series | None, d: str) -> float:
    if fx is None or not len(fx):
        return 1.3
    s = fx[fx.index <= pd.Timestamp(d)]
    return float(s.iloc[-1] if len(s) else fx.iloc[0])


def to_gbp(amount: float, ccy: str, fx_rate: float) -> float:
    """Converts an amount in the trade's price currency to GBP."""
    if ccy == 'USD':
        return amount / fx_rate
    if ccy == 'GBX':
        return amount / 100.0
    return amount


def _sign(t):
    return -1.0 if t.get('side') == 'short' else 1.0


def trade_view(t: dict, fx: pd.Series | None, today: str) -> dict:
    """Everything the page shows for one trade."""
    s, ccy = _sign(t), t.get('ccy', 'USD')
    fills = [{'date': t['opened'], 'price': float(t['entry']), 'units': float(t['units'])}] + list(t.get('adds') or [])
    units = sum(f['units'] for f in fills)
    avg = sum(f['price'] * f['units'] for f in fills) / units if units else float(t['entry'])
    entry, stop, tgt = float(t['entry']), float(t['stop']), (float(t['target']) if t.get('target') not in (None, '') else None)
    init_stop = float(t.get('initial_stop', stop))
    fx_in = _fx(fx, t['opened'])
    risk_unit = abs(entry - init_stop)
    risk_gbp = to_gbp(risk_unit * float(t['units']), ccy, fx_in)        # initial risk on the first fill
    for a in t.get('adds') or []:                                         # adds carry their own risk to the stop at the time
        risk_gbp += to_gbp(abs(float(a['price']) - float(a.get('stop', stop))) * float(a['units']), ccy, _fx(fx, a['date']))
    rr = (abs(tgt - entry) / risk_unit) if (tgt is not None and risk_unit > 0) else None
    open_risk_gbp = max(0.0, to_gbp(s * (avg - stop) * units, ccy, fx_in))   # what is still at risk to the current stop
    closed = t.get('status') == 'closed'
    end = t.get('closed') if closed else today
    days = (pd.Timestamp(end) - pd.Timestamp(t['opened'])).days
    fees = float(t.get('fees_gbp') or 0) + float(t.get('exit_fees_gbp') or 0)
    out = {**t, 'system_name': SYSTEMS.get(str(t['system']), {}).get('short', str(t['system'])),
           'units_total': units, 'avg_entry': avg, 'risk_unit': risk_unit, 'risk_gbp': risk_gbp, 'rr_planned': rr,
           'open_risk_gbp': 0.0 if closed else open_risk_gbp, 'days': days, 'fees_total': fees,
           'position_gbp': to_gbp(avg * units, ccy, fx_in), 'checks_n': len(t.get('checks') or []),
           'rules_n': len(SYSTEMS.get(str(t['system']), {}).get('rules', []))}
    if closed:
        fx_out = _fx(fx, t['closed'])
        pnl_ccy = s * (float(t['exit']) - avg) * units
        pnl_gbp = to_gbp(pnl_ccy, ccy, fx_out) - fees
        out.update({'pnl_gbp': pnl_gbp, 'r_multiple': pnl_gbp / risk_gbp if risk_gbp > 0 else None,
                    'ret_pct': s * (float(t['exit']) / avg - 1), 'win': pnl_gbp > 0})
    return out


def _stats(rows: list) -> dict:
    closed = [r for r in rows if r.get('status') == 'closed']
    rs = [r['r_multiple'] for r in closed if r.get('r_multiple') is not None]
    pnl = [r['pnl_gbp'] for r in closed]
    wins = [p for p in pnl if p > 0]
    losses = [p for p in pnl if p <= 0]
    streak = best = 0
    for p in sorted(closed, key=lambda r: r['closed']):
        streak = streak + 1 if p['pnl_gbp'] <= 0 else 0
        best = max(best, streak)
    rr = [r['rr_planned'] for r in rows if r.get('rr_planned') is not None]
    return {'trades': len(closed), 'open': len(rows) - len(closed),
            'win_rate': len(wins) / len(closed) if closed else None,
            'avg_r': float(np.mean(rs)) if rs else None, 'total_r': float(np.sum(rs)) if rs else 0.0,
            'pnl': float(np.sum(pnl)) if pnl else 0.0,
            'avg_win': float(np.mean(wins)) if wins else None, 'avg_loss': float(np.mean(losses)) if losses else None,
            'profit_factor': (sum(wins) / -sum(losses)) if losses and sum(losses) < 0 else None,
            'avg_days': float(np.mean([r['days'] for r in closed])) if closed else None,
            'avg_rr_planned': float(np.mean(rr)) if rr else None, 'max_losing_streak': best,
            'avg_checks': float(np.mean([r['checks_n'] / r['rules_n'] for r in rows if r['rules_n']])) if rows else None}


def compute(cfg: dict, systems_equity: float, fx: pd.Series | None, today: str) -> dict:
    """The Manual trading snapshot."""
    m = settings(cfg)
    rows = [trade_view(t, fx, today) for t in m['trades']]
    realised = sum(r.get('pnl_gbp', 0.0) for r in rows if r.get('status') == 'closed')
    equity = float(m['capital']) + realised
    total = systems_equity + equity
    base = total if m['risk_base'] == 'portfolio' else equity
    budget = base * float(m['risk_pct']) / 100.0
    open_rows = [r for r in rows if r.get('status') != 'closed']
    by_sys = {}
    for k, sd in SYSTEMS.items():
        rr = [r for r in rows if str(r['system']) == k]
        by_sys[k] = {**_stats(rr), 'name': sd['name'], 'short': sd['short'],
                     'open_now': sum(1 for r in open_rows if str(r['system']) == k)}
    closed = sorted([r for r in rows if r.get('status') == 'closed'], key=lambda r: r['closed'])
    curve, run = [], float(m['capital'])
    for r in closed:
        run += r['pnl_gbp']
        curve.append([r['closed'], run])
    return {
        'settings': {k: v for k, v in m.items() if k != 'trades'},
        'systems': SYSTEMS, 'by_system': by_sys, 'overall': _stats(rows),
        'open': sorted(open_rows, key=lambda r: r['opened'], reverse=True),
        'closed': list(reversed(closed)),
        'equity': equity, 'realised': realised, 'total_portfolio': total,
        'share_pct': equity / total * 100 if total else None,
        'risk_budget_gbp': budget, 'risk_base_gbp': base,
        'open_risk_gbp': sum(r['open_risk_gbp'] for r in open_rows),
        'open_count': len(open_rows), 'curve': curve,
        'fx_now': _fx(fx, today),
    }


# ----------------------------------------------------------------------------- edits (called from config.apply)
def _num(x, name):
    try:
        v = float(str(x).replace(',', '').replace('£', '').replace('$', '').strip())
    except Exception:  # noqa: BLE001
        raise ValueError(f'{name}: not a number')
    if not np.isfinite(v) or v < 0 or v > 1e8:
        raise ValueError(f'{name}: out of range')
    return v


def _risk_budget_now(cfg: dict) -> float | None:
    """Risk budget from the latest snapshot (systems equity) and the manual pot."""
    try:
        import json
        from . import STATE
        snap = json.loads((STATE / 'snapshot.json').read_text())
        mm = snap.get('manual') or {}
        return float(mm.get('risk_budget_gbp')) if mm.get('risk_budget_gbp') else None
    except Exception:  # noqa: BLE001
        return None


def apply(cfg: dict, op: dict, date_fn) -> str:
    m = cfg.setdefault('manual', {})
    for k, v in DEFAULTS.items():
        m.setdefault(k, v)
    trades = m.setdefault('trades', []) or []
    m['trades'] = trades
    kind = op['op']
    find = lambda: next((t for t in trades if t['id'] == op.get('id')), None)

    if kind == 'manual_settings':
        for k in ('capital', 'target_share_pct', 'risk_pct'):
            if op.get(k) not in (None, ''):
                m[k] = _num(op[k], k)
        for k in ('max_open', 'max_per_system'):
            if op.get(k) not in (None, ''):
                m[k] = int(_num(op[k], k))
        if op.get('risk_base') in ('portfolio', 'manual'):
            m['risk_base'] = op['risk_base']
        return 'manual trading settings updated'

    if kind == 'manual_open':
        sysk = str(op.get('system'))
        if sysk not in SYSTEMS:
            raise ValueError('choose a system')
        open_now = [t for t in trades if t.get('status') != 'closed']
        if len(open_now) >= int(m['max_open']):
            raise ValueError(f"rule: max {m['max_open']} open trades (close one first)")
        if sum(1 for t in open_now if str(t['system']) == sysk) >= int(m['max_per_system']):
            raise ValueError(f"rule: max {m['max_per_system']} open trades per system")
        side = SYSTEMS[sysk]['side'] if op.get('side') not in ('long', 'short') else op['side']
        entry, stop, units = _num(op['entry'], 'entry'), _num(op['stop'], 'stop'), _num(op['units'], 'units')
        target = _num(op['target'], 'target') if op.get('target') not in (None, '') else None
        if units <= 0 or entry <= 0:
            raise ValueError('entry and units must be above zero')
        if (side == 'long' and stop >= entry) or (side == 'short' and stop <= entry):
            raise ValueError('the stop must be below the entry for a long (above for a short)')
        if target is not None and ((side == 'long' and target <= entry) or (side == 'short' and target >= entry)):
            raise ValueError('the target must be above the entry for a long (below for a short)')
        ccy = op.get('ccy') if op.get('ccy') in ('USD', 'GBP', 'GBX') else 'USD'
        budget = _risk_budget_now(cfg)
        if budget and not op.get('over_risk'):
            from .data import load as load_px
            fxs = load_px('GBPUSD')['close'] if ccy == 'USD' else None
            risk = to_gbp(abs(entry - stop) * units, ccy, _fx(fxs, date_fn(op.get('opened') or date.today())))
            if risk > budget * 1.10:
                raise ValueError(f'rule: this trade risks £{risk:,.2f}, above the £{budget:,.2f} budget '
                                 f'({m["risk_pct"]}% per trade). Reduce the size, or tick "allow above budget"')
        checks = sorted(int(k.split('_')[2]) for k, v in op.items()
                        if k.startswith(f'chk_{sysk}_') and v in (True, 'true', 'on', '1', 1))
        t = {'id': 'm' + uuid.uuid4().hex[:6], 'system': sysk, 'ticker': str(op.get('ticker', '')).upper().strip()[:12],
             'side': side, 'ccy': ccy, 'opened': date_fn(op.get('opened') or date.today()),
             'entry': entry, 'stop': stop, 'initial_stop': stop, 'target': target, 'units': units,
             'fees_gbp': _num(op.get('fees_gbp') or 0, 'fees'), 'checks': checks,
             'notes': str(op.get('notes', ''))[:500], 'status': 'open'}
        if not t['ticker']:
            raise ValueError('ticker missing')
        trades.append(t)
        return f"opened {t['ticker']} ({SYSTEMS[sysk]['short']})"

    t = find()
    if t is None:
        raise ValueError('trade not found')
    if kind == 'manual_update':
        if op.get('stop') not in (None, ''):
            t.setdefault('stop_history', []).append({'date': date.today().isoformat(), 'stop': t['stop']})
            t['stop'] = _num(op['stop'], 'stop')
        if op.get('target') not in (None, ''):
            t['target'] = _num(op['target'], 'target')
        if op.get('notes') not in (None, ''):
            t['notes'] = (t.get('notes', '') + '\n' + str(op['notes'])[:300]).strip()
        return f"updated {t['ticker']}"
    if kind == 'manual_add':
        if t.get('status') == 'closed':
            raise ValueError('trade is closed')
        t.setdefault('adds', []).append({'date': date_fn(op.get('date') or date.today()), 'price': _num(op['price'], 'price'),
                                         'units': _num(op['units'], 'units'), 'stop': float(t['stop'])})
        if op.get('fees_gbp'):
            t['fees_gbp'] = float(t.get('fees_gbp') or 0) + _num(op['fees_gbp'], 'fees')
        return f"added to {t['ticker']}"
    if kind == 'manual_close':
        t.update({'status': 'closed', 'closed': date_fn(op.get('closed') or date.today()), 'exit': _num(op['exit'], 'exit price'),
                  'exit_fees_gbp': _num(op.get('exit_fees_gbp') or 0, 'fees'),
                  'exit_reason': str(op.get('exit_reason', 'manual'))[:30]})
        if op.get('notes'):
            t['notes'] = (t.get('notes', '') + '\nExit: ' + str(op['notes'])[:300]).strip()
        if pd.Timestamp(t['closed']) < pd.Timestamp(t['opened']):
            raise ValueError('close date is before the open date')
        return f"closed {t['ticker']}"
    if kind == 'manual_reopen':
        for k in ('closed', 'exit', 'exit_fees_gbp', 'exit_reason'):
            t.pop(k, None)
        t['status'] = 'open'
        return f"reopened {t['ticker']}"
    if kind == 'manual_delete':
        m['trades'] = [x for x in trades if x['id'] != t['id']]
        return f"deleted {t['ticker']}"
    raise ValueError(f'unknown operation {kind}')
