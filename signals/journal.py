"""Signal journal: a permanent record of every order the systems suggested (state/journal.json).

Unlike the pot ledger (rebuilt from scratch on every run), entries here are written once, the first
time a suggestion is seen, and never rewritten: so the journal shows what the site told you at the
time, even if settings change later. Each entry then gets a status:
  preview    seen in the ~16:05 pre-close preview, not yet confirmed by the close
  confirmed  the system traded at the close (the pot's model trade)
  cancelled  previewed, but the close did not confirm it
  superseded a confirmed suggestion that no longer appears after a settings change (e.g. capital)
Your real execution (recorded fill) is shown next to each entry.
"""
from __future__ import annotations

import json
from datetime import datetime

from . import STATE

PATH = STATE / 'journal.json'


def load() -> dict:
    try:
        return json.loads(PATH.read_text()) if PATH.exists() else {}
    except json.JSONDecodeError:
        return {}


def update(snap: dict, now: datetime) -> list:
    j = load()
    stamp = now.strftime('%Y-%m-%d %H:%M UTC')
    fills = {f['trade_id']: f for f in snap['config'].get('fills', [])}
    live_ids = set()
    for p in snap['pots'].values():
        # confirmed model trades (the whole replay, so the journal starts complete)
        for t in p['trades']:
            live_ids.add(t['id'])
            e = j.get(t['id'])
            if e is None:
                j[t['id']] = e = {
                    'id': t['id'], 'date': t['date'], 'pot': p['key'], 'pot_name': p['name'], 'system': p['strategy_name'],
                    'side': t['side'], 'asset': t['asset'], 'ccy': t.get('ccy'), 'gbp': t['gbp'], 'units': t['units'],
                    'price': t['price'], 'reason': t['reason'], 'first_seen': stamp,
                    'stop': t.get('stop'),
                    'status': 'confirmed'}
            elif e['status'] in ('preview', 'cancelled', 'superseded'):
                e.update({'status': 'confirmed', 'gbp': t['gbp'], 'units': t['units'], 'price': t['price'], 'reason': t['reason'],
                          'confirmed_at': stamp})
        # pre-close previews (before the London close)
        prov = p.get('status_provisional')
        if prov:
            day = now.strftime('%Y-%m-%d')
            for o in p.get('preview_provisional', []):
                tid = f"{p['key']}-{day}-{o['asset']}-{o['side']}"
                if tid not in j:
                    j[tid] = {'id': tid, 'date': day, 'pot': p['key'], 'pot_name': p['name'], 'system': p['strategy_name'],
                              'side': o['side'], 'asset': o['asset'], 'ccy': o.get('ccy'), 'gbp': o['gbp'], 'units': o.get('units'),
                              'price': o.get('price'), 'reason': prov.get('plain', '')[:200], 'first_seen': stamp,
                              'stop': prov['levels'].get('stop'), 'status': 'preview'}
    latest = {p['key']: p['latest_date'] for p in snap['pots'].values()}
    for tid, e in j.items():
        if e['status'] == 'preview' and e['date'] <= latest.get(e['pot'], '') and tid not in live_ids:
            e['status'] = 'cancelled'
        elif e['status'] == 'confirmed' and tid not in live_ids and e['date'] >= snap['config']['start_date']:
            e['status'] = 'superseded'
        elif e['status'] == 'confirmed' and e['date'] < snap['config']['start_date']:
            e['status'] = 'superseded'
        f = fills.get(tid)
        e['fill'] = {k: f.get(k) for k in ('price', 'fx', 'fee_gbp', 'units')} if f else None
    STATE.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(j, indent=1, sort_keys=True))
    return sorted(j.values(), key=lambda e: (e['date'], e['id']), reverse=True)
