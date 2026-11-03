"""One run = refresh data -> signals -> pot ledgers -> snapshot -> alerts -> website.

Modes
  close     after the US close (and fine at any time): confirmed signals, ledgers, daily summary email.
  preclose  ~25 min before the US close: previews today's QQQ orders on the live price and emails
            them so you can place market-on-close orders in time.
  btc       after 00:00 UTC: confirmed BTC signal and email if the BTC pot trades.
  build     no download and no email: recompute and rebuild the site (after editing settings).
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import STATE, __version__
from . import alerts as A
from . import config as C
from . import data as D
from .assets import ASSETS
from .ledger import order_preview, run_pot
from .strategies import STRATEGIES

BENCH = {'qqq_regime': 'QQQ', 'qqq_value': 'QQQ', 'btc_trend': 'BTC'}


def _clean(o):
    """JSON-safe: NaN -> None, numpy -> python, timestamps -> str."""
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if (o is None or math.isnan(o) or math.isinf(o)) else round(float(o), 6)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp, datetime)):
        return o.strftime('%Y-%m-%d')
    return o


def _with_live(data: dict, live: dict) -> tuple[dict, bool]:
    """Copy of data with forming bars appended (used for the pre-close preview)."""
    out, added = dict(data), False
    for k, bar in (live.get('bars') or {}).items():
        if k in out and len(out[k]):
            d = pd.Timestamp(bar['date'])
            if d > out[k].index[-1]:
                row = pd.DataFrame({'open': bar['close'], 'high': bar['close'], 'low': bar['close'], 'close': bar['close'],
                                    'adj_close': bar['close'], 'volume': np.nan}, index=pd.DatetimeIndex([d], name='date'))
                out[k] = pd.concat([out[k], row])
                added = True
    return out, added


def _history(key: str, t: pd.DataFrame, n: int = 120) -> list:
    """Recent signal events for the strategy page."""
    x = t.tail(n)
    ev = []
    if key == 'qqq_regime':
        for d, r in x.iterrows():
            for col, kind in (('event_in', 'BUY'), ('event_out', 'SELL'), ('event_trend', 'TREND')):
                if r[col]:
                    ev.append({'date': d, 'kind': kind if kind != 'TREND' else ('BUY' if 'on' in r[col] else 'SELL'),
                               'text': r[col], 'price': r['raw_close']})
    elif key == 'btc_trend':
        prev = None
        for d, r in x.iterrows():
            if prev is not None and r['state'] != prev['state']:
                up = r['w_BTC'] > prev['w_BTC']
                ev.append({'date': d, 'kind': 'BUY' if up else 'SELL',
                           'text': f"Score {prev['score']:.1f} → {r['score']:.1f}" + (' · halving window' if r['halving_window'] else '') +
                                   f" · target {r['w_BTC']:.0%}", 'price': r['close']})
            prev = r
    elif key == 'qqq_value':
        z = x['zone'] & ~x['zone'].shift(1, fill_value=False)
        for d, r in x[z].iterrows():
            ev.append({'date': d, 'kind': 'ZONE', 'text': 'Entered ' + ('trend zone' if r['trend_zone'] else '200-week zone'), 'price': r['close']})
    return list(reversed(ev))[:25]


def compute(cfg: dict, now: datetime, mode: str) -> tuple[dict, dict]:
    keys = sorted({k for s in STRATEGIES.values() for k in s.inputs} | {'GBPUSD'})
    data = {k: D.load(k) for k in keys}
    if data['GBPUSD'].empty:
        raise RuntimeError('No GBP/USD data yet: run a refresh (internet needed) or upload GBPUSD.csv.')
    live = D.load_live()
    data_live, has_live = _with_live(data, live)
    fx = data['GBPUSD']['close']
    fx_now = float(fx.iloc[-1])
    if 'GBPUSD' in (live.get('bars') or {}):
        fx_now = float(live['bars']['GBPUSD']['close'])

    tables, prov_tables = {}, {}
    for k, s in STRATEGIES.items():
        tables[k] = s.compute(data)
        if has_live and data_live[s.calendar_asset].index[-1] > data[s.calendar_asset].index[-1]:
            prov_tables[k] = s.compute(data_live)

    pots_out, pot_objs = {}, {}
    for pk, pc in cfg['pots'].items():
        s = STRATEGIES[pc['strategy']]
        res = run_pot(pk, pc, s, tables[s.key], {a: data[a] for a in set(s.assets) | {BENCH[s.key]}}, fx,
                      cfg['start_date'], cfg['topups'], cfg['fills'], BENCH[s.key])
        pot_objs[pk] = res
        pot_info = {'cash': res.cash, 'cooldown_left': res.cooldown_left, 'weights': res.weights}
        st = s.status(tables[s.key], pot_info)
        prov = s.status(prov_tables[s.key], pot_info, provisional=True) if s.key in prov_tables else None
        last_px = {a: float(data[a]['close'].iloc[-1]) for a in s.assets}
        joining = not res.started
        preview_final = order_preview(res, s, st, float(fx.iloc[-1]), last_px, joining=joining)
        live_px = {a: float(data_live[a]['close'].iloc[-1]) for a in s.assets}
        preview_prov = order_preview(res, s, prov, fx_now, live_px, joining=joining) if prov else []
        latest_date = tables[s.key].index[-1].strftime('%Y-%m-%d')
        curve = res.curve
        pnl = res.equity - res.deposits
        unreal = sum(p['unrealised'] for p in res.positions.values())
        pots_out[pk] = {
            'key': pk, 'name': pc.get('name', pk), 'strategy': s.key, 'strategy_name': s.name, 'page': pc.get('page', s.page),
            'kind': s.kind, 'cfg': pc, 'started': res.started, 'start': res.start, 'cash': res.cash, 'deposits': res.deposits,
            'equity': res.equity, 'pnl': pnl, 'pnl_pct': pnl / res.deposits if res.deposits else 0.0,
            'realised': res.realised, 'unrealised': unreal, 'dividends': res.dividends, 'interest': res.interest, 'fees': res.fees,
            'bench_asset': BENCH[s.key], 'bench_equity': res.bench_equity,
            'bench_pnl_pct': (res.bench_equity / res.deposits - 1) if res.deposits else 0.0,
            'positions': res.positions, 'weights': res.weights, 'trades': list(reversed(res.trades)),
            'trades_latest': [t for t in res.trades if t['date'] == latest_date],
            'deposits_log': list(reversed(res.deposits_log)), 'metrics': res.metrics,
            'curve': [[d.strftime('%Y-%m-%d'), r['equity'], r['deposits'], r['bench']] for d, r in curve.iterrows()] if len(curve) else [],
            'cooldown_left': res.cooldown_left, 'last_buy': res.last_buy,
            'status': st, 'status_provisional': prov, 'preview': preview_final, 'preview_provisional': preview_prov,
            'tested': s.tested, 'latest_date': latest_date,
        }

    strategies_out = {k: {'key': k, 'name': s.name, 'kind': s.kind, 'paper': s.paper, 'timing': s.timing,
                          'history': _history(k, tables[k]), 'asof': tables[k].index[-1].strftime('%Y-%m-%d')}
                      for k, s in STRATEGIES.items()}
    # chart data for the value page: QQQ close vs trend line and zones, last ~2 years
    vt = tables['qqq_value'].tail(500)
    strategies_out['qqq_value']['chart'] = [[d.strftime('%Y-%m-%d'), r['close'], r['trend_line'], r['s1000'], bool(r['zone'])]
                                            for d, r in vt.iterrows()]

    # at-the-close order cut-off (15:55 New York) for the next US session, in UK time
    ny = now.astimezone(D.NY)
    nxt = ny.date() if (ny.weekday() < 5 and ny.hour < 16) else (pd.Timestamp(ny.date()) + pd.offsets.BDay(1)).date()
    moc = datetime(nxt.year, nxt.month, nxt.day, 15, 55, tzinfo=D.NY).astimezone(D.LDN)  # 15:55 New York: last safe minute for an at-the-close order
    tot_eq = sum(p['equity'] for p in pots_out.values())
    tot_dep = sum(p['deposits'] for p in pots_out.values())
    snap = {
        'version': __version__, 'mode': mode,
        'generated_utc': now.strftime('%Y-%m-%d %H:%M'),
        'generated_london': now.astimezone(D.LDN).strftime('%a %d %b %Y, %H:%M'),
        'moc_deadline_uk': moc.strftime('%H:%M'), 'moc_day': moc.strftime('%a %d %b'),
        'fx': {'gbpusd': fx_now, 'date': fx.index[-1].strftime('%Y-%m-%d')},
        'live': {'fetched_utc': live.get('fetched_utc'), 'has_live': has_live,
                 'bars': live.get('bars') or {}},
        'freshness': D.freshness(now),
        'strategies': strategies_out, 'pots': pots_out,
        'totals': {'equity': tot_eq, 'deposits': tot_dep, 'pnl': tot_eq - tot_dep, 'pnl_pct': (tot_eq / tot_dep - 1) if tot_dep else 0.0,
                   'cash': sum(p['cash'] for p in pots_out.values())},
        'config': {'start_date': cfg['start_date'], 'topups': cfg['topups'], 'fills': cfg['fills'], 'alerts': cfg.get('alerts', {}),
                   'pots': cfg['pots']},
        'assets': [{'key': a.key, 'name': a.name, 'symbol': a.symbol, 'source': a.source} for a in ASSETS.values()],
        'email_configured': A.configured(),
    }
    return _clean(snap), tables


# ----------------------------------------------------------------------------- alerts
def _fmt_order(o, pot_name):
    u = f" (~{o['units']:.4f} units at ${o['price']:,.2f})" if o.get('units') and o.get('price') else ''
    return f"{o['side']} {o['asset']} £{o['gbp']:,.0f}{u} · {pot_name}"


def alerts_for(snap: dict, mode: str, now: datetime) -> list:
    """Returns [(id, subject, lines)] still to send."""
    cfg_a = snap['config'].get('alerts', {})
    if not cfg_a.get('email_enabled', True):
        return []
    out = []
    pots = snap['pots']
    if mode == 'preclose' and cfg_a.get('preclose_warning', True):
        lines, ids = [], []
        for p in pots.values():
            if p['bench_asset'] != 'QQQ' or not p['status_provisional']:
                continue
            for o in p['preview_provisional']:
                ids.append(f"pre-{p['status_provisional']['asof']}-{p['key']}-{o['asset']}-{o['side']}")
                lines.append(_fmt_order(o, p['name']) + ' — market-on-close')
        if lines and not all(A.already_sent(i) for i in ids):
            asof = next(p['status_provisional']['asof'] for p in pots.values() if p['status_provisional'])
            out.append((ids, f'ACTION before the US close · {len(lines)} QQQ order(s) likely today',
                        ['Based on the live price ~25 minutes before the close. Place market-on-close orders now:'] + lines +
                        ['', 'If the close moves the other way the signal can still change; the post-close email confirms.', f'Session {asof}.']))
    if mode in ('close', 'btc'):
        want = ('BTC',) if mode == 'btc' else ('QQQ', 'BTC')
        lines, ids = [], []
        for p in pots.values():
            if p['bench_asset'] not in want:
                continue
            for t in p['trades_latest']:
                if not A.already_sent('trade-' + t['id']):
                    ids.append('trade-' + t['id'])
                    lines.append(f"{t['side']} {t['asset']} £{t['gbp']:,.0f} at ${t['price']:,.2f} on {t['date']} · {p['name']} — {t['reason']}")
        if lines:
            when = 'at the close' if mode == 'close' else 'at 00:00 UTC'
            out.append((ids, f"Signal · {lines[0].split(' · ')[0]}" + (f' (+{len(lines) - 1} more)' if len(lines) > 1 else ''),
                        [f'New system trades {when}:'] + lines +
                        ['', 'QQQ orders are market-on-close; if you missed the close, the research assumes the close price, so trade as early as possible next session.']))
    if mode == 'close' and cfg_a.get('daily_summary', True):
        us = pots.get('qqq_trading') or next(iter(pots.values()))
        sid = f"summary-{us['latest_date']}"
        if not A.already_sent(sid):
            lines = [f"{p['name']}: {p['status']['action']} — {p['status']['action_sub']} · value £{p['equity']:,.0f} ({p['pnl_pct']:+.1%})"
                     for p in pots.values()]
            stale = [f"{r['key']} last {r['last']}" for r in snap['freshness'] if r['status'] != 'ok']
            if stale:
                lines += ['', 'Data warning: ' + ', '.join(stale)]
            out.append(([sid], f"Daily summary · {us['latest_date']} · total £{snap['totals']['equity']:,.0f}", lines))
    return out


def _email_html(subject: str, lines: list) -> str:
    body = ''.join(f'<p style="margin:0 0 8px">{l}</p>' if l else '<br>' for l in lines)
    return (f'<div style="font-family:Arial,sans-serif;font-size:15px;color:#0B1220;max-width:640px">'
            f'<div style="background:#0B1220;color:#fff;padding:12px 16px;font-weight:bold">Signals</div>'
            f'<div style="padding:16px;border:1px solid #D5DBE5;border-top:0"><h2 style="font-size:18px;margin:0 0 12px">{subject}</h2>{body}'
            f'<p style="color:#475467;font-size:12px;margin-top:16px">Signals only. Check the dashboard before acting.</p></div></div>')


def send_alerts(snap: dict, mode: str, now: datetime) -> list:
    sent = []
    for ids, subject, lines in alerts_for(snap, mode, now):
        try:
            r = A.send(subject, _email_html(subject, lines), '\n'.join(lines))
            A.mark_sent(ids, now.strftime('%Y-%m-%d %H:%M'))
            sent.append({'subject': subject, 'result': r})
        except Exception as e:  # noqa: BLE001
            sent.append({'subject': subject, 'result': f'failed: {e}'})
    return sent


# ----------------------------------------------------------------------------- entry point
def in_preclose_window(now: datetime) -> bool:
    ny = now.astimezone(D.NY)
    return ny.weekday() < 5 and (15 * 60) <= ny.hour * 60 + ny.minute <= (15 * 60 + 58)


def run(mode: str = 'close', fetch: bool = True, email: bool = True, build: bool = True, force: bool = False,
        now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    if mode == 'preclose' and not force and not in_preclose_window(now):
        return {'skipped': f'outside the pre-close window (New York time {now.astimezone(D.NY):%H:%M})'}
    report = {}
    if fetch and mode != 'build':
        report['refresh'] = D.refresh(now=now)
    report['uploads'] = D.import_uploads()
    cfg = C.load()
    snap, _ = compute(cfg, now, mode)
    snap['refresh'] = report.get('refresh')
    STATE.mkdir(parents=True, exist_ok=True)
    report['alerts'] = send_alerts(snap, mode, now) if (email and mode != 'build') else []
    snap['last_alerts'] = report['alerts']
    (STATE / 'snapshot.json').write_text(json.dumps(snap, indent=1))
    if build:
        from .web.build import build as build_site
        report['site'] = str(build_site(snap))
    return report
