"""Settings file (config/portfolio.yaml) and the edit operations the website sends."""
from __future__ import annotations

import copy
import uuid
from datetime import date

import yaml

from . import CONFIG

HEADER = """# Poli's Hedge Fund: your settings.
# Edit this file directly, or use the Settings and Portfolio pages (they write here for you).
# All money is in GBP. EQQQ is priced in pence; BTC in USD, converted with the GBP/USD close of the day.
# Pots follow their systems from the first close on or after start_date.
# manual: Manual trading settings and your logged trades (written by the Manual trading page).
# topups: one-off deposits. fills: your real executions (price in the asset's own unit: pence for EQQQ,
# USD for BTC, the GBP/USD rate for USD cash; optional fx, fee_gbp, units).

"""

POT_FIELDS = {'initial_capital': float, 'monthly_topup': float, 'fee_pct': float, 'fx_fee_pct': float, 'cash_rate_pct': float, 'name': str}


def load() -> dict:
    cfg = yaml.safe_load(CONFIG.read_text()) or {}
    cfg.setdefault('topups', [])
    cfg.setdefault('fills', [])
    cfg.setdefault('alerts', {})
    cfg['topups'] = cfg['topups'] or []
    cfg['fills'] = cfg['fills'] or []
    cfg['start_date'] = str(cfg.get('start_date'))
    return cfg


def save(cfg: dict):
    out = copy.deepcopy(cfg)
    CONFIG.write_text(HEADER + yaml.safe_dump(out, sort_keys=False, allow_unicode=True, width=120))


def _money(x) -> float:
    v = float(str(x).replace('£', '').replace(',', '').strip())
    if v != v or abs(v) > 1e9:
        raise ValueError('amount out of range')
    return round(v, 2)


def _date(x) -> str:
    return date.fromisoformat(str(x)[:10]).isoformat()


def apply(op: dict) -> str:
    """Applies one edit. Returns a short description. Raises ValueError on bad input."""
    cfg = load()
    kind = op.get('op')
    pots = cfg['pots']
    if kind == 'set_pot':
        pot = op['pot']
        if pot not in pots:
            raise ValueError(f'unknown pot {pot}')
        changed = []
        for f, typ in POT_FIELDS.items():
            if f in op and op[f] not in (None, ''):
                pots[pot][f] = _money(op[f]) if typ is float else str(op[f])[:60]
                changed.append(f)
        msg = f'{pot}: updated {", ".join(changed)}'
    elif kind == 'add_topup':
        pot = op['pot']
        if pot not in pots:
            raise ValueError(f'unknown pot {pot}')
        amt = _money(op['amount'])
        t = {'id': 't' + uuid.uuid4().hex[:6], 'pot': pot, 'date': _date(op.get('date') or date.today()),
             'amount': amt, 'note': str(op.get('note', ''))[:80]}
        cfg['topups'].append(t)
        msg = f"top-up £{amt:,.2f} to {pot} on {t['date']}"
    elif kind == 'delete_topup':
        n = len(cfg['topups'])
        cfg['topups'] = [t for t in cfg['topups'] if t.get('id') != op['id']]
        if len(cfg['topups']) == n:
            raise ValueError('top-up not found')
        msg = f"deleted top-up {op['id']}"
    elif kind == 'set_fill':
        tid = str(op['trade_id'])
        f = {'trade_id': tid}
        for k in ('price', 'fx', 'fee_gbp', 'units'):
            if op.get(k) not in (None, ''):
                f[k] = float(op[k])
        cfg['fills'] = [x for x in cfg['fills'] if x.get('trade_id') != tid] + [f]
        msg = f'recorded fill for {tid}'
    elif kind == 'delete_fill':
        cfg['fills'] = [x for x in cfg['fills'] if x.get('trade_id') != op['trade_id']]
        msg = f"removed fill for {op['trade_id']}"
    elif kind == 'set_start':
        cfg['start_date'] = _date(op['start_date'])
        msg = f"start date {cfg['start_date']}"
    elif kind == 'set_alerts':
        for k in ('email_enabled', 'daily_summary', 'preclose_warning'):
            if k in op:
                cfg['alerts'][k] = bool(op[k]) if not isinstance(op[k], str) else op[k].lower() in ('1', 'true', 'yes', 'on')
        msg = 'alert settings updated'
    elif str(kind).startswith('manual_'):
        from . import manual
        msg = manual.apply(cfg, op, _date)
    else:
        raise ValueError(f'unknown operation {kind}')
    save(cfg)
    return msg
