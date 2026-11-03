"""One run = refresh data -> signals -> pot ledgers -> snapshot -> alerts -> website.

Modes (UK time)
  preclose  ~16:05: previews today's EQQQ orders on the live London price (and any value-plan buy due
            today) and emails them so you can trade before the London close.
  close     ~16:55: after the London close: confirmed EQQQ / USD trades for the pots.
  us        ~21:20: after the US close: value zones, dollar trend, risk flag, daily summary email.
  btc       ~00:20: after the BTC daily close: confirmed BTC signal and email if the BTC pot trades.
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

BENCH = {'qqq_regime': 'EQQQ', 'qqq_value': 'EQQQ', 'btc_trend': 'BTC'}


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
                    ev.append({'date': d, 'kind': kind if kind != 'TREND' else ('BUY' if r[col].startswith('Trend leg on') else 'SELL'),
                               'text': r[col], 'price': r['raw_close'], 'price_fmt': f"£{r['raw_close'] / 100:,.2f}"})
    elif key == 'btc_trend':
        prev = None
        for d, r in x.iterrows():
            if prev is not None and r['w_BTC'] != prev['w_BTC']:
                up = r['w_BTC'] > prev['w_BTC']
                ev.append({'date': d, 'kind': 'BUY' if up else 'SELL',
                           'text': f"{r['event']} · target {r['w_BTC']:.0%}", 'price': r['close'], 'price_fmt': f"${r['close']:,.0f}"})
            prev = r
    elif key == 'qqq_value':
        z = x['zone'] & ~x['zone'].shift(1, fill_value=False)
        for d, r in x[z].iterrows():
            ev.append({'date': d, 'kind': 'ZONE', 'text': 'QQQ entered the ' + ('trend zone' if r['trend_zone'] else '200-week zone'),
                       'price': r['close'], 'price_fmt': f"${r['close']:,.2f}"})
        for col, txt in (('fast_b1', 'Fast-crash buy 1 (50% of cash)'), ('fast_b2', 'Fast-crash buy 2 (all cash)')):
            if col in x:
                for d, r in x[x[col].astype(bool)].iterrows():
                    ev.append({'date': d, 'kind': 'BUY', 'text': txt, 'price': r['close'], 'price_fmt': f"${r['close']:,.2f}"})
        ev.sort(key=lambda e: e['date'])
    return list(reversed(ev))[:25]


def compute(cfg: dict, now: datetime, mode: str) -> tuple[dict, dict]:
    keys = sorted({k for s in STRATEGIES.values() for k in s.inputs} | {'GBPUSD'})
    data = D.load_all(keys)
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
        px_src = {a: (data['GBPUSD'] if a == 'USD' else data[a]) for a in set(s.assets) | {BENCH[s.key]}}
        res = run_pot(pk, pc, s, tables[s.key], px_src, fx,
                      cfg['start_date'], cfg['topups'], cfg['fills'], BENCH[s.key])
        pot_objs[pk] = res
        # ideal run: the same signals filled exactly at the model price and fee (no recorded fills)
        has_fills = any(str(f.get('trade_id', '')).startswith(pk + '-') for f in cfg['fills'])
        ideal = run_pot(pk, pc, s, tables[s.key], px_src, fx, cfg['start_date'], cfg['topups'], [], BENCH[s.key]) if has_fills else res
        ideal_out = {'equity': ideal.equity, 'pnl': ideal.equity - ideal.deposits, 'realised': ideal.realised, 'fees': ideal.fees,
                     'trades': {t['id']: {k: t[k] for k in ('price', 'pnl', 'fee', 'gbp', 'units', 'unit_gbp')} for t in ideal.trades}}
        pot_info = {'cash': res.cash, 'cooldown_left': res.cooldown_left, 'weights': res.weights}
        st = s.status(tables[s.key], pot_info)
        prov = s.status(prov_tables[s.key], pot_info, provisional=True) if s.key in prov_tables else None
        last_px = {a: float(px_src[a]['close'].iloc[-1]) for a in s.assets}
        joining = not res.started
        preview_final = order_preview(res, s, st, float(fx.iloc[-1]), last_px, joining=joining)
        live_px = {a: float((data_live['GBPUSD'] if a == 'USD' else data_live[a])['close'].iloc[-1]) for a in s.assets}
        preview_prov = order_preview(res, s, prov, fx_now, live_px, joining=joining) if prov else []
        latest_date = tables[s.key].index[-1].strftime('%Y-%m-%d')
        curve = res.curve
        pnl = res.equity - res.deposits
        unreal = sum(p['unrealised'] for p in res.positions.values())
        if s.key == 'qqq_regime':
            tb = tables[s.key]
            for tr in res.trades:
                ds = pd.Timestamp(tr['date'])
                if tr['asset'] == 'EQQQ' and tr['side'] == 'BUY' and ds in tb.index and pd.notna(tb.at[ds, 'dip_stop']) and tb.at[ds, 'w_dip'] > 0:
                    tr['stop'] = float(tb.at[ds, 'dip_stop'])
        expect = {}
        if s.kind == 'weights':
            from .expect import expectation
            from .assets import ASSETS as _A
            try:
                expect = expectation(pk, s, tables[s.key], data, pc, res.curve, res.start, _A[s.calendar_asset].calendar)
            except Exception as e:  # noqa: BLE001 - never block the run
                expect = {'error': str(e)[:200]}
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
            'tested': s.tested, 'latest_date': latest_date, 'expect': expect, 'ideal': ideal_out,
        }

    strategies_out = {k: {'key': k, 'name': s.name, 'kind': s.kind, 'paper': s.paper, 'timing': s.timing,
                          'history': _history(k, STRATEGIES[k].compute_us(data) if k == 'qqq_value' else tables[k]), 'asof': tables[k].index[-1].strftime('%Y-%m-%d')}
                      for k, s in STRATEGIES.items()}
    # chart data for the value page: QQQ close vs trend line and zones, last ~2 years
    vt = STRATEGIES['qqq_value'].compute_us(data).tail(500)
    strategies_out['qqq_value']['chart'] = [[d.strftime('%Y-%m-%d'), r['close'], r['trend_line'], r['s1000'], bool(r['zone'])]
                                            for d, r in vt.iterrows()]

    # order cut-off: 16:25 London on the next LSE session (the close auction starts at 16:30)
    from .calendar import add_trading_days
    ldn = now.astimezone(D.LDN)
    today = pd.Timestamp(ldn.date())
    is_session = add_trading_days(today - pd.Timedelta(days=1), 1, 'lse') == today
    nxt = today if (is_session and (ldn.hour, ldn.minute) < (16, 25)) else add_trading_days(today, 1, 'lse')
    moc = datetime(nxt.year, nxt.month, nxt.day, 16, 25, tzinfo=D.LDN)
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
    from .assets import account
    if o['ccy'] == 'GBX':
        u = f" (~{o['units']:.2f} shares at £{o['price'] / 100:,.2f})" if o.get('units') else ''
    elif o['ccy'] == 'USDCASH':
        u = f" (~${o['units']:,.0f} at {o['price']:.4f})" if o.get('units') else ''
        return f"{'Convert GBP→USD' if o['side'] == 'BUY' else 'Convert USD→GBP'} £{o['gbp']:,.0f}{u} · {account('USD')} · {pot_name}"
    else:
        u = f" (~{o['units']:.4f} units at ${o['price']:,.2f})" if o.get('units') and o.get('price') else ''
    return f"{o['side']} {o['asset']} £{o['gbp']:,.0f}{u} · {account(o['asset'])} · {pot_name}"


def _fmt_trade(t, pot_name):
    if t.get('ccy') == 'GBX':
        px = f"£{t['price'] / 100:,.2f}"
    elif t.get('ccy') == 'USDCASH':
        px = f"GBP/USD {t['price']:.4f}"
    else:
        px = f"${t['price']:,.2f}"
    return f"{t['side']} {t['asset']} £{t['gbp']:,.0f} at {px} on {t['date']} · {pot_name} — {t['reason']}"


def alerts_for(snap: dict, mode: str, now: datetime) -> list:
    """Returns [(ids, subject, lines)] still to send."""
    cfg_a = snap['config'].get('alerts', {})
    if not cfg_a.get('email_enabled', True):
        return []
    out = []
    pots = snap['pots']
    today = now.astimezone(D.LDN).strftime('%Y-%m-%d')
    if mode == 'preclose' and cfg_a.get('preclose_warning', True):
        lines, ids = [], []
        for p in pots.values():
            if p['bench_asset'] != 'EQQQ':
                continue
            if p['kind'] == 'weights' and p['status_provisional']:
                for o in p['preview_provisional']:
                    ids.append(f"pre-{today}-{p['key']}-{o['asset']}-{o['side']}")
                    lines.append(_fmt_order(o, p['name']))
            if p['kind'] == 'accumulate' and p['status']['action'] == 'BUY' and p['status'].get('executes') == today:
                for o in p['preview']:
                    ids.append(f"pre-{today}-{p['key']}-{o['asset']}-{o['side']}")
                    lines.append(_fmt_order(o, p['name']) + ' (value zone at the last US close)')
        if lines and not all(A.already_sent(i) for i in ids):
            out.append((ids, f"ACTION before 16:25 · {len(lines)} order(s) likely at today's London close",
                        ['Based on the live London price ~25 minutes before the close. Place these now:'] + lines +
                        ['', 'If the price moves a lot before 16:30 the signal can change; the 16:55 email confirms.']))
    if mode in ('close', 'btc'):
        want = ('BTC',) if mode == 'btc' else ('EQQQ',)
        lines, ids = [], []
        for p in pots.values():
            if p['bench_asset'] not in want:
                continue
            for t in p['trades_latest']:
                if not A.already_sent('trade-' + t['id']):
                    ids.append('trade-' + t['id'])
                    lines.append(_fmt_trade(t, p['name']))
        if lines:
            when = 'at the London close' if mode == 'close' else 'at 00:00 UTC'
            out.append((ids, f"Signal · {lines[0].split(' · ')[0]}" + (f' (+{len(lines) - 1} more)' if len(lines) > 1 else ''),
                        [f'New system trades {when}:'] + lines +
                        ['', 'If you missed the close, trade as early as possible in the next session and record your real fill in the journal.']))
    if mode == 'us':
        v = next((p for p in pots.values() if p['kind'] == 'accumulate'), None)
        if v and v['status']['action'] == 'BUY':
            vid = f"value-{v['status']['executes']}"
            if not A.already_sent(vid):
                lines = [f"{v['name']}: {v['status']['plain']}"] + [_fmt_order(o, v['name']) for o in v['preview']]
                out.append(([vid], f"Value plan · BUY EQQQ at the {v['status']['executes']} London close", lines))
    if mode == 'us' and cfg_a.get('daily_summary', True):
        sid = f"summary-{today}"
        if not A.already_sent(sid):
            lines = [f"{p['name']}: {p['status']['action']} — {p['status']['action_sub']} · value £{p['equity']:,.0f} ({p['pnl_pct']:+.1%})"
                     for p in pots.values()]
            stale = [f"{r['key']} last {r['last']}" for r in snap['freshness'] if r['status'] != 'ok']
            if stale:
                lines += ['', 'Data warning: ' + ', '.join(stale)]
            out.append(([sid], f"Daily summary · {today} · total £{snap['totals']['equity']:,.0f}", lines))
    return out


def _email_html(subject: str, lines: list) -> str:
    body = ''.join(f'<p style="margin:0 0 8px">{l}</p>' if l else '<br>' for l in lines)
    return (f'<div style="font-family:Arial,sans-serif;font-size:15px;color:#0B1220;max-width:640px">'
            f'<div style="background:#0B1220;color:#fff;padding:12px 16px;font-weight:bold">&#9760; Poli&#39;s Hedge Fund</div>'
            f'<div style="padding:16px;border:1px solid #D5DBE5;border-top:0"><h2 style="font-size:18px;margin:0 0 12px">{subject}</h2>{body}'
            f'<p style="color:#475467;font-size:12px;margin-top:16px">Signals only: no orders are sent. Check the dashboard before acting.</p></div></div>')


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
    ldn = now.astimezone(D.LDN)
    return ldn.weekday() < 5 and (15 * 60 + 50) <= ldn.hour * 60 + ldn.minute <= (16 * 60 + 22)


def run(mode: str = 'us', fetch: bool = True, email: bool = True, build: bool = True, force: bool = False,
        now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    if mode == 'preclose' and not force and not in_preclose_window(now):
        return {'skipped': f'outside the pre-close window (London time {now.astimezone(D.LDN):%H:%M})'}
    report = {}
    if fetch and mode != 'build':
        report['refresh'] = D.refresh(now=now)
    report['uploads'] = D.import_uploads()
    cfg = C.load()
    snap, _ = compute(cfg, now, mode)
    snap['refresh'] = report.get('refresh')
    from . import radar as R
    if fetch and mode in ('us', 'btc'):
        report['radar_fetch'] = R.fetch(now)
    try:
        snap['radar'] = _clean(R.compute())
        snap['radar']['fetch'] = report.get('radar_fetch')
        snap['radar']['feeds'] = R.feeds()
    except Exception as e:  # noqa: BLE001
        snap['radar'] = {'error': str(e)[:300], 'panels': []}
    from .journal import update as journal_update, summary as journal_summary
    snap['journal'] = journal_update(snap, now)
    snap['journal_summary'] = journal_summary(snap['journal'], snap['pots'])
    try:
        from . import radar_track
        radar_track.update(snap.get('radar') or {}, now)
    except Exception as e:  # noqa: BLE001 - tracking must never block the run
        (snap.get('radar') or {})['track_error'] = str(e)[:200]
    STATE.mkdir(parents=True, exist_ok=True)
    report['alerts'] = send_alerts(snap, mode, now) if (email and mode != 'build') else []
    snap['last_alerts'] = report['alerts']
    (STATE / 'snapshot.json').write_text(json.dumps(snap, indent=1))
    if build:
        from .web.build import build as build_site
        report['site'] = str(build_site(snap))
    return report
