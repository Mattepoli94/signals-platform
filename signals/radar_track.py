"""Live track record of the Risk radar and the bottom signals, kept from 3 November 2026 onwards.

Every run stores the published level of each panel in state/radar_log.json, keyed by the data date
(written once per date: what the site showed at the time). Outcomes are then scored against prices as
they arrive:

  late     warning = AMBER/RED. Hit if the S&P 500 falls 19%+ from its highest close since the warning
           began, within 378 sessions (about 18 months). False alarm if not.
  ndx      warning = AMBER/RED. Hit if, from any warning day, QQQ closes 8%+ lower within 15 sessions.
  btc      warning = AMBER/RED. Hit if, from any warning day, BTC closes 15%+ lower within 10 days.
  fast     signal = BUY 1 / BUY 2 days (fast-crash plan). Scored by the return 1 and 3 months after the
           first buy day and the further fall after it; "worked" = higher 3 months later.
  washout  signal = BUY. Same scoring at 3 and 6 months.
Missed events (risk panels only): an event of the same kind that started on a day when the panel was not
warning (and had not warned in the lead window before it).
"""
from __future__ import annotations

import json
from datetime import datetime

import numpy as np
import pandas as pd

from . import STATE
from .radar import _price, _read

PATH = STATE / 'radar_log.json'
START = '2026-11-02'
WARN = {'late': ('AMBER', 'RED'), 'ndx': ('AMBER', 'RED'), 'btc': ('AMBER', 'RED'),
        'fast': ('BUY 1', 'BUY 2'), 'washout': ('BUY',)}
RULES = {
    'late': dict(series='spx', horizon=378, kind='bear', thr=0.19, lead=252,
                 what='S&P 500 falls 19%+ within ~18 months of the warning'),
    'ndx': dict(series='qqq', horizon=15, kind='fall', thr=0.08, lead=20, what='QQQ falls 8%+ within 3 weeks of a warning day'),
    'btc': dict(series='btc', horizon=10, kind='fall', thr=0.15, lead=10, what='BTC falls 15%+ within 10 days of a warning day'),
    'fast': dict(series='qqq', horizon=63, kind='buy', what='QQQ higher 3 months after the first buy'),
    'washout': dict(series='spx', horizon=126, kind='buy', what='S&P 500 higher 6 months after the signal'),
}


def load() -> dict:
    try:
        return json.loads(PATH.read_text()) if PATH.exists() else {}
    except json.JSONDecodeError:
        return {}


def _series():
    return {'spx': _read('yahoo_GSPC', 'close').dropna(), 'qqq': _price('QQQ', 'adj_close').dropna(),
            'btc': _price('BTC', 'close').dropna()}


def _episodes(days: list[str]) -> list[list[str]]:
    """Group warning dates into episodes (gaps of more than 7 calendar days start a new one)."""
    eps = []
    for d in sorted(days):
        if eps and (pd.Timestamp(d) - pd.Timestamp(eps[-1][-1])).days <= 7:
            eps[-1].append(d)
        else:
            eps.append([d])
    return eps


def score(log: dict, px: dict) -> dict:
    out = {}
    for key, r in RULES.items():
        rows = {d: v[key] for d, v in log.items() if key in v}
        if not rows:
            out[key] = {'since': START, 'what': r['what'], 'days': 0, 'episodes': [], 'n': 0}
            continue
        c = px[r['series']]
        warn_days = [d for d, v in rows.items() if v.get('level') in WARN[key]]
        eps = []
        for ep in _episodes(warn_days):
            s0 = pd.Timestamp(ep[0])
            fut = c[c.index > s0]
            e = {'start': ep[0], 'end': ep[-1], 'days': len(ep)}
            if r['kind'] == 'bear':
                win = c[(c.index >= s0)].iloc[:r['horizon'] + 1]
                ddmax = float((win / win.cummax() - 1).min()) if len(win) else 0.0
                e['outcome'] = ('hit' if ddmax <= -r['thr'] else ('false alarm' if len(win) > r['horizon'] else 'pending'))
                e['detail'] = f'worst fall so far {ddmax * 100:.1f}%'
            elif r['kind'] == 'fall':
                worst, resolved = 0.0, True
                for d in ep:
                    t = pd.Timestamp(d)
                    if t not in c.index:
                        continue
                    nxt = c[c.index > t].iloc[:r['horizon']]
                    if len(nxt):
                        worst = min(worst, float(nxt.min() / c.loc[t] - 1))
                    resolved &= len(nxt) >= r['horizon']
                e['outcome'] = 'hit' if worst <= -r['thr'] else ('false alarm' if resolved else 'pending')
                e['detail'] = f'worst fall within {r["horizon"]} sessions {worst * 100:.1f}%'
            else:   # buy signals
                t = pd.Timestamp(ep[0])
                base = c[c.index <= t]
                if len(base) == 0:
                    continue
                p0 = float(base.iloc[-1])
                nxt = fut.iloc[:r['horizon']]
                ret = float(nxt.iloc[-1] / p0 - 1) if len(nxt) else None
                worst = float(min(0, nxt.min() / p0 - 1)) if len(nxt) else 0.0
                e['outcome'] = ('pending' if len(nxt) < r['horizon'] else ('worked' if ret > 0 else 'failed'))
                e['detail'] = (f'{len(nxt)} sessions: {ret * 100:+.1f}%, further fall {worst * 100:.1f}%' if ret is not None else 'just issued')
            eps.append(e)
        res = {'since': START, 'what': r['what'], 'days': len(rows), 'warn_days': len(warn_days), 'episodes': eps, 'n': len(eps),
               'hits': sum(e['outcome'] in ('hit', 'worked') for e in eps),
               'false': sum(e['outcome'] in ('false alarm', 'failed') for e in eps),
               'pending': sum(e['outcome'] == 'pending' for e in eps)}
        # missed events: event starts on logged days with no warning in the lead window
        if r['kind'] in ('fall', 'bear'):
            logged = sorted(rows)
            missed = []
            for d in logged:
                t = pd.Timestamp(d)
                if t not in c.index:
                    continue
                nxt = c[c.index > t].iloc[:r['horizon'] if r['kind'] == 'fall' else 252]
                if not len(nxt):
                    continue
                hit = (nxt.min() / c.loc[t] - 1) <= -r['thr']
                lead = [x for x in warn_days if t - pd.Timedelta(days=int(r['lead'] * 1.5)) <= pd.Timestamp(x) <= t]
                if hit and not lead and not (missed and (t - pd.Timestamp(missed[-1])).days <= 30):
                    missed.append(d)
            res['missed'] = missed
        out[key] = res
    return out


def update(radar: dict, now: datetime) -> dict:
    log = load()
    for p in (radar.get('panels') or []) + (radar.get('bottoms') or []):
        if not p.get('asof') or p.get('error') or p['asof'] < START:
            continue
        day = log.setdefault(p['asof'], {})
        day.setdefault(p['key'], {'level': p.get('level'), 'score': p.get('score'), 'seen': now.strftime('%Y-%m-%d %H:%M UTC')})
    STATE.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(log, indent=1, sort_keys=True))
    track = score(log, _series())
    for p in (radar.get('panels') or []) + (radar.get('bottoms') or []):
        p['live'] = track.get(p['key'])
    radar['track_since'] = START
    return track
