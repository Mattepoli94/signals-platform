"""Emergency plan (Nov 2026): track QQQ and SOXX against the exit framework and say what it calls for now.

The framework (see research/emergency-exit-plan.md):
  start 70 high beta / 30 large cap / 0 cash
  Tranche 1 at Target 1 (SOXX ~149 or QQQ 690): sell 35 high beta            -> 35/30/35
  19 Nov checkpoint (session 10 after the 5 Nov low): strong = SOXX >= 142.5 or QQQ >= 687
      strong     -> Tranche 2 order at SOXX ~157 / QQQ 707, 5% trailing stop from the highest close since 19 Nov, deadline 4 Dec
      not strong -> sell Tranche 2 on the next up day, by 30 Nov at the latest     -> 15/30/55
  Warning: close below the low (SOXX 131.90 / QQQ 618) -> finish any tranche not yet sold
  Jump ship: SOXX close < 120 -> sell 10 high beta; QQQ weekly close < 585 -> sell 15 large cap -> 5/15/80
  We're back: 10 closes in a row above the 200-day on both -> stop selling
"""
from __future__ import annotations

import json
from datetime import date

import pandas as pd

from . import STATE
from . import data as D

LOW_DATE = '2026-11-05'
CHECK_DATE = '2026-11-19'
T2_DEADLINE_WEAK = '2026-11-30'
T2_DEADLINE_STRONG = '2026-12-04'

LEVELS = {
    'SOXX': {'low': 131.90, 't1': 149.0, 't2': 157.0, 'strong': 142.5, 'weak': 138.5, 'warn': 131.90, 'jump': 120.0,
             'high': 218.19},
    'QQQ': {'low': 647.05, 't1': 690.0, 't2': 707.0, 'strong': 687.0, 'weak': 666.0, 'warn': 618.0, 'jump': 585.0,
            'high': 759.66},
}

_FUT = ['2026-11-09', '2026-11-10', '2026-11-11', '2026-11-12', '2026-11-13', '2026-11-16', '2026-11-17', '2026-11-18',
        '2026-11-19', '2026-11-20', '2026-11-23', '2026-11-24', '2026-11-25', '2026-11-27', '2026-11-30', '2026-12-01',
        '2026-12-02', '2026-12-03', '2026-12-04', '2026-12-07', '2026-12-08', '2026-12-09', '2026-12-10', '2026-12-11',
        '2026-12-14', '2026-12-15', '2026-12-16', '2026-12-17', '2026-12-18']
PATHS = {
    'SOXX': {
        'bounce': [135.5, 134.8, 137.5, 140.5, 142.5, 144, 145, 149.5, 150.5, 152, 154, 155.5, 157, 156, 155, 153, 151, 149,
                   148, 147, 149, 150, 148, 146, 145, 147, 148, 146, 144],
        'failure': [134, 133, 136, 139.5, 140.2, 138, 137, 133, 131, 129, 130.5, 132, 131, 129, 127, 125, 126.5, 124, 122,
                    123, 121, 119.5, 121, 120, 118.5, 117, 119, 118, 117],
    },
    'QQQ': {
        'bounce': [654, 652, 660, 668, 672, 676, 680, 690, 692, 695, 700, 704, 707, 705, 703, 700, 697, 695, 693, 692, 695,
                   697, 694, 690, 688, 691, 693, 690, 687],
        'failure': [653, 650, 657, 662, 664.5, 660, 657, 648, 643, 638, 641, 644, 641, 636, 630, 625, 628, 622, 617, 620,
                    612, 606, 610, 604, 598, 592, 596, 590, 586],
    },
}
START_ALLOC = (70, 30, 0)  # high beta, large cap, cash (% of portfolio)


def _closes(key: str) -> pd.Series:
    df = D.load(key)
    c = df['close'].dropna() if len(df) else pd.Series(dtype=float)
    live = (D.load_live().get('bars') or {}).get(key)
    if live and (len(c) == 0 or pd.Timestamp(live['date']) > c.index[-1]):
        c = pd.concat([c, pd.Series([float(live['close'])], index=[pd.Timestamp(live['date'])])])
    return c


def _track(key: str, c: pd.Series) -> dict:
    L = LEVELS[key]
    since = c.loc[LOW_DATE:]
    last_d, last = c.index[-1], float(c.iloc[-1])
    post = c.loc[pd.Timestamp(LOW_DATE) + pd.Timedelta(days=1):]
    session = len(post)
    s200 = c.rolling(200).mean()
    above200 = (c > s200)
    streak = 0
    for v in reversed(above200.tolist()):
        if not v:
            break
        streak += 1
    hit = lambda lvl: next((d.strftime('%Y-%m-%d') for d, v in post.items() if v >= lvl), None)  # noqa: E731
    new_low = next((d.strftime('%Y-%m-%d') for d, v in post.items() if v < L['warn']), None)
    if key == 'SOXX':
        jump = next((d.strftime('%Y-%m-%d') for d, v in post.items() if v < L['jump']), None)
    else:
        w = post.groupby(post.index.to_period('W-FRI')).last()
        done_weeks = w[[p.end_time.normalize() <= last_d.normalize() for p in w.index]]
        jump = next((p.end_time.strftime('%Y-%m-%d') for p, v in done_weeks.items() if v < L['jump']), None)
    exp_date = last_d.strftime('%Y-%m-%d')
    exp = {n: dict(zip(_FUT, PATHS[key][n])).get(exp_date) for n in ('bounce', 'failure')}
    if exp['bounce'] and exp['failure']:
        db, df_ = last / exp['bounce'] - 1, last / exp['failure'] - 1
        if last >= exp['bounce']:
            tracking = 'Ahead of the bounce path'
        elif last <= exp['failure']:
            tracking = 'On or below the failure path'
        else:
            tracking = 'Closer to the bounce path' if abs(db) < abs(df_) else 'Closer to the failure path'
    else:
        db = df_ = None
        tracking = 'Before the projection starts' if exp_date < _FUT[0] else 'Past the projection window'
    check_close = float(c.loc[:CHECK_DATE].iloc[-1]) if last_d >= pd.Timestamp(CHECK_DATE) else None
    return {
        'key': key, 'date': exp_date, 'close': last, 'session': session,
        'from_low': last / L['low'] - 1, 'from_high': last / L['high'] - 1,
        'max_since_low': float(since.max()), 'max_from_low': float(since.max()) / L['low'] - 1,
        't1_hit': hit(L['t1']), 't2_hit': hit(L['t2']), 'new_low': new_low, 'jump': jump,
        'sma200': float(s200.iloc[-1]), 'above200_streak': streak,
        'exp_bounce': exp['bounce'], 'exp_failure': exp['failure'], 'dev_bounce': db, 'dev_failure': df_,
        'tracking': tracking, 'check_close': check_close, 'levels': L,
        'band_now': 'strong' if last >= L['strong'] else ('weak' if last <= L['weak'] else 'in between'),
        'chart_actual': [(d.strftime('%Y-%m-%d'), float(v)) for d, v in c.loc['2026-09-15':].items()],
        'chart_bounce': [('2026-11-06', 136.53 if key == 'SOXX' else 656.10)] + list(zip(_FUT, PATHS[key]['bounce'])),
        'chart_failure': [('2026-11-06', 136.53 if key == 'SOXX' else 656.10)] + list(zip(_FUT, PATHS[key]['failure'])),
    }


def _decide(s: dict, q: dict, today: str) -> dict:
    """Walk the framework and return the steps with their state and the action it calls for now."""
    hb, lc, cash = START_ALLOC
    steps, actions = [], []
    session = max(s['session'], q['session'])
    t1 = s['t1_hit'] or q['t1_hit']
    warn = s['new_low'] or q['new_low']
    t2 = s['t2_hit'] or q['t2_hit']
    checked = s['check_close'] is not None
    strong = None
    if checked:
        strong = s['check_close'] >= s['levels']['strong'] or q['check_close'] >= q['levels']['strong']
        weak = s['check_close'] <= s['levels']['weak'] and q['check_close'] <= q['levels']['weak']

    # Tranche 1
    if t1:
        st1 = ('done', f"Target 1 reached on {t1}: sell 35 of high beta")
    elif warn:
        st1 = ('act', f"New low on {warn}: the bounce failed for now. Sell tranche 1 (35 of high beta) on the next up day")
    elif session >= 10:
        st1 = ('act', 'No Target 1 by session 10: the bounce is failing. Sell tranche 1 (35 of high beta) on the next up day')
    else:
        st1 = ('wait', f"Waiting for SOXX ~149 or QQQ 690 (session {session} of 10). Typical bounces reach it by session 3–9")
    steps.append({'id': 't1', 'name': 'Tranche 1 · Target 1', 'state': st1[0], 'text': st1[1]})
    if st1[0] in ('done', 'act'):
        hb -= 35
        cash += 35

    # Checkpoint
    if checked:
        band = 'strong' if strong else ('weak' if weak else 'in between')
        stc = ('done', f"19 Nov close: SOXX {s['check_close']:.2f}, QQQ {q['check_close']:.2f} → {band}")
    else:
        band = None
        stc = ('wait', f"19 Nov close decides tranche 2. Right now: SOXX {s['band_now']}, QQQ {q['band_now']} "
                       f"(strong = SOXX ≥142.5 or QQQ ≥687)")
    steps.append({'id': 'check', 'name': '19 Nov checkpoint', 'state': stc[0], 'text': stc[1]})

    # Tranche 2
    if t2:
        st2 = ('done', f"Target 2 reached on {t2}: sell 20 of high beta")
    elif warn and t1:
        st2 = ('act', f"New low on {warn}: finish selling — tranche 2 (20 of high beta) on the next up day")
    elif checked and not strong:
        late = today > T2_DEADLINE_WEAK
        st2 = ('act', 'Checkpoint not strong: Target 2 is unlikely (0 of 10 past cases). Sell tranche 2 (20 of high beta) '
                      + ('now — the 30 Nov deadline has passed' if late else 'on the next up day, by 30 Nov'))
    elif checked and strong:
        if today > T2_DEADLINE_STRONG:
            st2 = ('act', 'Strong path but no Target 2 by 4 Dec: sell tranche 2 at market')
        else:
            st2 = ('wait', 'Strong bounce: keep the tranche 2 order at SOXX ~157 / QQQ 707, with a stop 5% below the highest close since 19 Nov; deadline 4 Dec')
    else:
        st2 = ('wait', 'Waits for the 19 Nov checkpoint (or Target 2 if it comes first)')
    steps.append({'id': 't2', 'name': 'Tranche 2 · Target 2', 'state': st2[0], 'text': st2[1]})
    if st2[0] in ('done', 'act'):
        hb -= 20
        cash += 20

    # Warning
    steps.append({'id': 'warn', 'name': 'Warning · new low', 'state': 'act' if warn else 'ok',
                  'text': (f"Triggered {warn}: close below SOXX 131.90 or QQQ 618" if warn else
                           'Not triggered: SOXX above 131.90 and QQQ above 618')})

    # Jump ship
    js = []
    if s['jump']:
        js.append(f"SOXX closed below 120 on {s['jump']}: sell 10 of high beta")
        hb -= min(10, hb)
        cash += 10
    if q['jump']:
        js.append(f"QQQ weekly close below 585 ({q['jump']}): sell 15 of large cap")
        lc -= 15
        cash += 15
    steps.append({'id': 'jump', 'name': 'Jump ship', 'state': 'act' if js else 'ok',
                  'text': '; '.join(js) if js else 'Not triggered: SOXX above 120 and QQQ weekly close above 585'})

    back = s['above200_streak'] >= 10 and q['above200_streak'] >= 10
    steps.append({'id': 'back', 'name': "We're back", 'state': 'done' if back else 'ok',
                  'text': ('Both have held above their 200-day for 10 closes: stop selling, hold what is left' if back else
                           f"Not yet: SOXX {s['above200_streak']} and QQQ {q['above200_streak']} closes in a row above the 200-day (need 10 each)")})

    act = [x for x in steps if x['state'] == 'act']
    if back and not js:
        headline, tone = "We're back: stop selling and hold", 'ok'
    elif js:
        headline, tone = 'Jump ship triggered: cut to the stop allocation', 'bad'
    elif act:
        headline, tone = act[0]['text'], 'warn'
    elif t1 and not t2:
        headline, tone = 'Tranche 1 done. Waiting for the 19 Nov checkpoint / Target 2', 'info'
    else:
        headline, tone = 'Hold: no sale yet. Let the bounce come to Target 1', 'info'
    if s['tracking'].startswith(('On or below the failure', 'Closer to the failure')) and tone == 'info':
        tone = 'warn'
    return {'steps': steps, 'headline': headline, 'tone': tone, 'alloc': {'high_beta': hb, 'large_cap': lc, 'cash': cash},
            'session': session, 'band': band}


def _log(rec: dict):
    p = STATE / 'emergency_log.json'
    log = json.loads(p.read_text()) if p.exists() else []
    log = [r for r in log if r['date'] != rec['date']] + [rec]
    STATE.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(log[-120:], indent=1))
    return log


def compute(today: str | None = None) -> dict:
    today = today or date.today().isoformat()
    s, q = _track('SOXX', _closes('SOXX')), _track('QQQ', _closes('QQQ'))
    dec = _decide(s, q, today)
    log = _log({'date': max(s['date'], q['date']), 'soxx': round(s['close'], 2), 'qqq': round(q['close'], 2),
                'session': dec['session'], 'tracking': s['tracking'], 'headline': dec['headline'],
                'alloc': f"{dec['alloc']['high_beta']} · {dec['alloc']['large_cap']} · {dec['alloc']['cash']}"})
    return {'soxx': s, 'qqq': q, **dec, 'log': list(reversed(log))[:30], 'asof': max(s['date'], q['date'])}
