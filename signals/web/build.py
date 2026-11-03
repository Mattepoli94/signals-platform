"""Renders the static website from state/snapshot.json into site/."""
from __future__ import annotations

import json
import os
import shutil
from datetime import date
from pathlib import Path

import markdown
import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .. import RESEARCH, SITE, STATE
from .charts import line_chart

HERE = Path(__file__).parent

PAPERS = [
    {'slug': 'qqq-regime-system', 'kind': 'TRADING · NASDAQ-100', 'version': 'v1.1', 'title': 'Nasdaq-100 regime system + dollar add-on (UK: EQQQ at the London close)',
     'desc': 'Regime detector, 50% trend leg, dip-buying leg, dollar add-on and risk flag. Traded in EQQQ (ISA, no FX fee) at the London close.',
     'stats': [('CAGR 2010–24*', '9.0%'), ('Max drawdown', '−14.1%'), ('QQQ research 2000–24', '10.4%')],
     'period': '*EQQQ at the London close with the dollar add-on, cash 0% · rules fitted on QQQ 1999–2024, not re-tuned',
     'ext': 'https://claude.ai/artifact/Kjtfn4jJ1JdCrynU9ubXvc'},
    {'slug': 'qqq-value-plan', 'kind': 'INVESTING · NASDAQ-100', 'version': 'v1.1', 'title': 'Nasdaq-100 value-zone accumulation plan',
     'desc': 'Contributions wait in cash and buy only in the trend zone or the 200-week zone. Never sells.',
     'stats': [('Account DD vs DCA', '−34% / −49%'), ('Wealth vs DCA', '−5.4%'), ('Horizon', '10 years')],
     'period': 'Median of rolling 10-year plans started 2000 onwards'},
    {'slug': 'btc-trend', 'kind': 'TRADING · BTC', 'version': 'v1 · paper only', 'title': 'BTC trend blend (under review)',
     'desc': 'Failed its out-of-sample re-test on 3 Nov 2026. Kept as a paper track; the paper has the full re-test and walk-forward results.',
     'stats': [('Walk-forward CAGR', '37%'), ('Worst fall', '−64%'), ('Holding BTC', '61% / −84%')],
     'period': 'Out of sample 2016–Oct 2026 (walk-forward). The old 105% / −30% figures were in-sample.'},
]
CHANGELOG = [
    ('2026-11-03', 'BTC trend blend', 'Re-tested with random holdout years (2012, 2016, 2018) and walk-forward: no validated edge over holding BTC. Marked paper only.'),
    ('2026-11-03', 'Nasdaq systems', 'v1.1: traded in EQQQ (London, pence, ISA) at the London close; dollar add-on held as USD cash in the Invest account. Removes the 0.15% FX fee on Nasdaq trades.'),
    ('2026-11-03', 'Platform', 'v1.0 live: signals, pots, top-ups, fills, email alerts.'),
    ('2026-11-02', 'BTC trend blend', 'Adopted. Cycle bag removed; liquidity and dollar filters shown as context only.'),
    ('2026-11-02', 'QQQ value plan', 'Adopted. Static drawdown rungs replaced by the trend and 200-week zones.'),
    ('2026-11-02', 'QQQ regime system', 'v1.0 frozen. Regime turning Trending closes an open dip trade. Gold/TLT hedge dropped; dollar add-on kept.'),
]


# ----------------------------------------------------------------------------- filters
def _num(x):
    return x is not None and x == x


def f_gbp(x, sign=False):
    if not _num(x):
        return '—'
    v = abs(x)
    s = f'£{v:,.0f}' if v >= 10000 else f'£{v:,.2f}'
    if sign:
        return ('+' if x > 0.004 else ('−' if x < -0.004 else '')) + s
    return ('−' if x < -0.004 else '') + s


def f_gbp2(x):
    return '—' if not _num(x) else ('−' if x < 0 else '') + f'£{abs(x):,.2f}'


def f_px(x, ccy='USD'):
    if not _num(x):
        return '—'
    if ccy == 'GBX':
        return f'£{x / 100:,.2f}'
    if ccy == 'USDCASH':
        return f'{x:.4f}'
    return f_usd(x)


def f_usd(x):
    if not _num(x):
        return '—'
    return f'${x:,.0f}' if abs(x) >= 10000 else f'${x:,.2f}'


def f_pct(x, sign=True):
    if not _num(x):
        return '—'
    s = f'{abs(x) * 100:.1f}%'
    if not sign:
        return s
    return ('+' if x > 0.0004 else ('−' if x < -0.0004 else '')) + s


def f_cls(x):
    return '' if not _num(x) else ('pos' if x > 0.004 else ('neg' if x < -0.004 else ''))


def f_dshort(s):
    try:
        return date.fromisoformat(str(s)[:10]).strftime('%d %b')
    except ValueError:
        return s or '—'


def f_d(s):
    try:
        return date.fromisoformat(str(s)[:10]).strftime('%d %b %Y')
    except ValueError:
        return s or '—'


# ----------------------------------------------------------------------------- helpers
def _pot_chart(p):
    c = p['curve']
    if len(c) < 2:
        return ''
    return line_chart([
        {'name': 'Money in', 'color': '#475467', 'dash': True, 'width': 2, 'points': [(r[0], r[2]) for r in c]},
        {'name': 'Benchmark', 'color': '#98A2B3', 'width': 2.5, 'points': [(r[0], r[3]) for r in c]},
        {'name': 'Pot', 'color': '#1D4ED8', 'width': 3, 'points': [(r[0], r[1]) for r in c],
         'markers': [(t['date'], next((r[1] for r in c if r[0] == t['date']), None), '#0E7A43' if t['side'] == 'BUY' else '#B42318')
                     for t in p['trades'] if p['kind'] == 'accumulate']},
    ], label=f"{p['name']} value vs benchmark and money in")


def _expect_chart(p):
    e = p.get('expect') or {}
    cone = e.get('cone') or []
    if len(cone) < 2:
        return ''
    live = e.get('live') or []
    under_name = 'EQQQ' if p['strategy'] == 'qqq_regime' else 'BTC'
    series = [
        {'name': 'Expected (median)', 'color': '#1D4ED8', 'dash': True, 'width': 1.8, 'points': [(c[0], c[2]) for c in cone]},
        {'name': under_name, 'color': '#98A2B3', 'width': 1.2, 'points': [(r[0], r[2]) for r in live]},
        {'name': 'Pot', 'color': '#0B1220', 'width': 2.8, 'points': [(r[0], r[1]) for r in live]},
    ]
    return line_chart(series, yfmt='{:+.0f}%', bands=[{'points': [(c[0], c[1], c[3]) for c in cone]}],
                      today=live[-1][0] if live else None,
                      label=f"{p['name']}: return since start vs the backtest's expected range and {under_name}")


def _total_chart(pots):
    frames = []
    for p in pots:
        if len(p['curve']) > 1:
            df = pd.DataFrame(p['curve'], columns=['date', 'eq', 'dep', 'b']).set_index('date')
            frames.append(df[['eq', 'dep']].rename(columns=lambda c: f"{p['key']}_{c}"))
    if not frames:
        return ''
    t = pd.concat(frames, axis=1).sort_index().ffill().fillna(0)
    eq = t[[c for c in t if c.endswith('_eq')]].sum(axis=1)
    dep = t[[c for c in t if c.endswith('_dep')]].sum(axis=1)
    return line_chart([
        {'name': 'Money in', 'color': '#475467', 'dash': True, 'width': 2, 'points': list(zip(t.index, dep))},
        {'name': 'Total', 'color': '#1D4ED8', 'width': 3, 'points': list(zip(t.index, eq))},
    ], label='Total value of all pots vs money in')


def _value_levels_chart(snap):
    ch = snap['strategies']['qqq_value'].get('chart') or []
    if len(ch) < 2:
        return ''
    return line_chart([
        {'name': 'QQQ', 'color': '#0B1220', 'width': 2, 'points': [(r[0], r[1]) for r in ch]},
        {'name': 'Trend', 'color': '#1D4ED8', 'width': 2.5, 'points': [(r[0], r[2]) for r in ch]},
        {'name': '200w', 'color': '#0E7A43', 'dash': True, 'width': 2, 'points': [(r[0], r[3]) for r in ch]},
    ], yfmt='${:,.0f}', label='QQQ close with its 5-year trend line and 200-week average; value zones shaded',
        zones=[r[4] for r in ch])


def _health(pots):
    out = []
    for p in pots:
        if p['page'] != 'trading':
            continue
        m, e = p.get('metrics') or {}, p.get('expect') or {}
        flags = e.get('flags') or []
        worst = next((f for f in flags if f['tone'] == 'red'), None) or next((f for f in flags if f['tone'] == 'amber'), None)
        if not p['started']:
            status, tone = 'Not started', 'grey'
        elif e.get('sessions', 0) < 20:
            status, tone = 'Collecting data', 'grey'
        elif worst:
            status, tone = ('Check: outside backtest' if worst['tone'] == 'red' else 'Watch: weaker than expected'), worst['tone']
        else:
            status, tone = 'In line with backtest', 'green'
        out.append({'name': p['name'], 'since': f_d(p['start']) if p['started'] else 'not started', 'trades': m.get('trades', 0),
                    'win': f_pct(m['win_rate'], False) if m.get('win_rate') is not None else '—',
                    'ret': f_pct(e['live_ret']) if 'live_ret' in e else '—',
                    'tested_ret': (f"{f_pct(e['exp_med'])} ({f_pct(e['exp_lo'])} to {f_pct(e['exp_hi'])})" if 'exp_med' in e
                                   else (f_pct(e.get('bt_cagr')) + ' a year' if e.get('bt_cagr') is not None else '—')),
                    'dd_live': f_pct(e['live_dd']) if 'live_dd' in e else '—',
                    'dd_tested': f_pct(e['exp_dd']) if 'exp_dd' in e else f_pct(e.get('bt_maxdd')),
                    'status': status, 'tone': tone})
    return out


def build(snap: dict | None = None, out: Path = SITE) -> Path:
    if snap is None:
        snap = json.loads((STATE / 'snapshot.json').read_text())
    env = Environment(loader=FileSystemLoader(HERE / 'templates'), autoescape=select_autoescape(['html']))
    env.filters.update(gbp=f_gbp, gbp2=f_gbp2, usd=f_usd, px=f_px, pct=f_pct, cls=f_cls, d=f_d, dshort=f_dshort)
    out.mkdir(parents=True, exist_ok=True)
    shutil.copytree(HERE / 'static', out / 'static', dirs_exist_ok=True)
    pots = list(snap['pots'].values())
    charts = {p['key']: _pot_chart(p) for p in pots}
    charts['value_levels'] = _value_levels_chart(snap)
    for p in pots:
        charts['exp_' + p['key']] = _expect_chart(p)
    charts['total'] = _total_chart(pots)
    names = {p['key']: p['name'] for p in pots}
    events = []
    sys_names = {'qqq_regime': 'Nasdaq trading', 'qqq_value': 'Nasdaq value plan', 'btc_trend': 'BTC trend'}
    for k, s in snap['strategies'].items():
        for e in s['history'][:6]:
            events.append({**e, 'system': sys_names.get(k, k)})
    events.sort(key=lambda e: e['date'], reverse=True)
    deposits, applied = [], set()
    for p in pots:
        for d in p['deposits_log']:
            deposits.append({**d, 'pot_name': p['name']})
            if d.get('id'):
                applied.add(d['id'])
    deposits.sort(key=lambda d: d['date'], reverse=True)
    future = [{**t, 'pot_name': names.get(t['pot'], t['pot'])} for t in snap['config']['topups'] if t.get('id') not in applied]
    live_preview = [p for p in pots if p.get('status_provisional') and p['bench_asset'] == 'EQQQ']
    base = dict(snap=snap, pots=pots, charts=charts, today=date.today().isoformat(), health=_health(pots),
                recent_events=events[:10], deposits=deposits, future_topups=future, live_preview=live_preview,
                papers=[{**r, 'href': f"research/{r['slug']}.html"} for r in PAPERS], changelog=CHANGELOG,
                js_ctx={'generated': snap['generated_utc'], 'repo': os.environ.get('GITHUB_REPOSITORY', 'Mattepoli94/signals-platform')})
    base['journal'] = snap.get('journal') or []
    for page in ('index', 'investing', 'trading', 'journal', 'portfolio', 'research', 'settings'):
        html = env.get_template(f'{page}.html').render(page=page, root='', **base)
        (out / f'{page}.html').write_text(html)
    (out / 'research').mkdir(exist_ok=True)
    for r in PAPERS:
        src = RESEARCH / f"{r['slug']}.md"
        if src.exists():
            body = markdown.markdown(src.read_text(), extensions=['tables', 'fenced_code', 'toc'])
            html = env.get_template('paper.html').render(page='research', root='../', title=r['title'], html=body, **base)
            (out / 'research' / f"{r['slug']}.html").write_text(html)
    (out / '.nojekyll').write_text('')
    return out
