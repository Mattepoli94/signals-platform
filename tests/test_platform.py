"""Core checks: rules on known dates, ledger arithmetic, settings edits, CSV parsing."""
import numpy as np
import pandas as pd
import pytest

from signals import data as D
from signals.ledger import run_pot
from signals.strategies import STRATEGIES
from signals.strategies.base import Strategy


@pytest.fixture(scope='module')
def stored():
    keys = ['EQQQ', 'QQQ', 'UUP', 'BTC', 'GBPUSD']
    return D.load_all(keys)


# ----------------------------------------------------------------------------- rules on known dates
def test_core_rules_on_qqq_30_oct_2026(stored):
    from signals.strategies.qqq_regime import regime_core
    t = regime_core(stored['QQQ']['adj_close'].loc[:'2026-10-30'], STRATEGIES['qqq_regime'].params)
    x = t.iloc[-1]
    assert x['regime'] == 'Range above 200-day'
    assert x['rsi2'] == pytest.approx(8.41, abs=0.05)
    assert x['w_core'] == 1.0
    assert x['dip_stop'] == pytest.approx(x['dip_entry'] * 0.97)


def test_eqqq_london_close_30_oct_2026(stored):
    d = {k: (v.loc[:'2026-10-30'] if k == 'EQQQ' else v.loc[:'2026-10-29']) for k, v in stored.items()}
    t = STRATEGIES['qqq_regime'].compute(d)
    x = t.iloc[-1]
    assert t.index[-1] == pd.Timestamp('2026-10-30')
    assert x['w_EQQQ'] == 1.0 and x['w_USD'] == 0.0
    assert x['raw_close'] == pytest.approx(51946, rel=0.01)       # pence
    st = STRATEGIES['qqq_regime'].status(t)
    assert st['action'] == 'BUY' and st['levels']['exit_date'] == '2026-11-13'
    assert st['targets'] == {'EQQQ': 1.0, 'USD': 0.0}


def test_eqqq_repair_removes_bad_prints(stored):
    r = stored['EQQQ']['close'].pct_change().abs()
    assert r.loc['2010':].max() < 0.15          # raw Yahoo data had +60% one-day spikes


def test_value_zone_30_oct_2026(stored):
    s = STRATEGIES['qqq_value']
    us = s.compute_us({'QQQ': stored['QQQ'].loc[:'2026-10-30']})
    x = us.iloc[-1]
    assert x['z'] == pytest.approx(-0.16, abs=0.02)
    assert not x['zone']                        # z in the zone but close below the 20-day average


def test_btc_v2_rules(stored):
    t = STRATEGIES['btc_trend'].compute(stored)
    x = t.loc['2026-11-02']
    assert x['trend'] and int(x['days_since_halving']) == 926 and not x['bear_window']
    assert x['adx'] < 25 and x['size'] == 0.5 and x['w_BTC'] == 0.5
    assert t.loc['2026-01-01', 'bear_window'] and t.loc['2026-01-01', 'w_BTC'] == 0
    # weights only take the values 0, 0.5, 1
    assert set(t['w_BTC'].round(3).unique()) <= {0.0, 0.5, 1.0}


def test_rsi_and_trend_helpers():
    from signals.indicators import trend_z, wilder_rsi
    c = pd.Series(np.exp(np.linspace(0, 1, 1400)))   # perfect log-linear line
    z = trend_z(c, 1260)
    assert np.isnan(z.iloc[1259]) and abs(z.iloc[-1]) < 1e-6 or np.isnan(z.iloc[-1])
    r = wilder_rsi(pd.Series([1, 2, 3, 4, 5, 6], dtype=float))
    assert r.iloc[-1] == pytest.approx(100.0)


# ----------------------------------------------------------------------------- ledger arithmetic
class Toy(Strategy):
    def __init__(self, kind='weights'):
        super().__init__(key='toy', name='Toy', kind=kind, assets=('AAA',), inputs=('AAA',), calendar_asset='AAA', band=1.0,
                         params=dict(frac=0.5, cooldown=10, cap_months=24))


def _toy(prices, weights=None, zone=None):
    idx = pd.date_range('2026-01-05', periods=len(prices), freq='B')
    px = pd.DataFrame({'close': prices, 'adj_close': prices}, index=idx, dtype=float)
    t = pd.DataFrame(index=idx)
    if weights is not None:
        t['w_AAA'] = weights
        t['state'] = [str(w) for w in weights]
    if zone is not None:
        t['zone'] = zone
        t['trend_zone'] = zone
    fx = pd.Series(1.25, index=idx)
    return idx, px, t, fx


def test_weights_pot_buy_sell_with_fees():
    idx, px, t, fx = _toy([100, 110, 121, 121], weights=[1.0, 1.0, 0.0, 0.0])
    cfg = {'initial_capital': 1000, 'fee_pct': 0.15, 'cash_rate_pct': 0}
    r = run_pot('p', cfg, Toy(), t, {'AAA': px}, fx, '2026-01-01', [], [], 'AAA')
    buy, sell = r.trades
    assert buy['side'] == 'BUY' and buy['gbp'] == pytest.approx(1000)
    units = (1000 - 1.5) * 1.25 / 100
    assert buy['units'] == pytest.approx(units)
    gross = units * 121 / 1.25
    assert r.cash == pytest.approx(gross * (1 - 0.0015))
    assert sell['pnl'] == pytest.approx(gross * (1 - 0.0015) - 1000, abs=0.01)
    assert r.equity == pytest.approx(r.cash) and r.positions == {}


def test_topups_and_fill_override():
    idx, px, t, fx = _toy([100, 100, 100, 100], weights=[1.0, 1.0, 1.0, 1.0])
    cfg = {'initial_capital': 500, 'fee_pct': 0, 'cash_rate_pct': 0}
    tops = [{'id': 'a', 'pot': 'p', 'date': idx[2].strftime('%Y-%m-%d'), 'amount': 250}]
    fills = [{'trade_id': f"p-{idx[0]:%Y-%m-%d}-AAA-BUY", 'price': 125}]
    r = run_pot('p', cfg, Toy(), t, {'AAA': px}, fx, '2026-01-01', tops, fills, 'AAA')
    assert r.deposits == 750
    assert r.trades[0]['price'] == 125 and r.trades[0]['filled']
    # the top-up sits in cash: QQQ-style pots only trade when the rules change
    assert r.cash == pytest.approx(250)


def test_accumulate_pot_half_of_cash_and_cooldown():
    zone = [True] * 12
    idx, px, t, fx = _toy([100] * 12, zone=zone)
    cfg = {'initial_capital': 1000, 'fee_pct': 0, 'cash_rate_pct': 0}
    r = run_pot('v', cfg, Toy('accumulate'), t, {'AAA': px}, fx, '2026-01-01', [], [], 'AAA')
    assert [x['gbp'] for x in r.trades] == [500.0, 250.0]      # day 0 and day 10
    assert r.cash == pytest.approx(250)


def test_pot_not_started_yet():
    idx, px, t, fx = _toy([100, 100], weights=[1.0, 1.0])
    r = run_pot('p', {'initial_capital': 500}, Toy(), t, {'AAA': px}, fx, '2030-01-01', [], [], 'AAA')
    assert not r.started and r.cash == 500 and r.trades == []


# ----------------------------------------------------------------------------- settings and CSV
def test_config_ops(tmp_path, monkeypatch):
    import signals.config as C
    p = tmp_path / 'portfolio.yaml'
    p.write_text("start_date: '2026-11-03'\npots:\n  a: {name: A, strategy: qqq_value, initial_capital: 1000}\ntopups: []\nfills: []\nalerts: {}\n")
    monkeypatch.setattr(C, 'CONFIG', p)
    C.apply({'op': 'set_pot', 'pot': 'a', 'initial_capital': '1,500'})
    C.apply({'op': 'add_topup', 'pot': 'a', 'amount': 200, 'date': '2026-12-01'})
    cfg = C.load()
    assert cfg['pots']['a']['initial_capital'] == 1500
    tid = cfg['topups'][0]['id']
    C.apply({'op': 'delete_topup', 'id': tid})
    assert C.load()['topups'] == []
    with pytest.raises(ValueError):
        C.apply({'op': 'add_topup', 'pot': 'nope', 'amount': 1})


def test_parse_csv_formats():
    yahoo = 'Date,Open,High,Low,Close,Adj Close,Volume\n2026-10-29,1,2,0.5,1.5,1.4,100\n2026-10-30,1,2,0.5,1.6,1.5,100\n'
    inv = '"Date","Price","Open","High","Low","Vol.","Change %"\n"10/30/2026","1,234.50","1,200.00","1,240.00","1,190.00","1.2M","0.5%"\n'
    a = D.parse_csv(yahoo)
    b = D.parse_csv(inv)
    assert a['adj_close'].iloc[-1] == 1.5 and len(a) == 2
    assert b['close'].iloc[0] == 1234.5 and b['volume'].iloc[0] == 1.2e6
    assert b.index[0] == pd.Timestamp('2026-10-30')


def test_gbp_conversions():
    from signals.ledger import native_to_gbp
    assert native_to_gbp('EQQQ', 51946, 1.33) == pytest.approx(519.46)
    assert native_to_gbp('USD', 1.25, 1.25) == pytest.approx(0.8)      # one dollar in pounds
    assert native_to_gbp('BTC', 80000, 1.25) == pytest.approx(64000)


def test_usd_cash_leg_pays_fx_fee_only():
    class Two(Strategy):
        def __init__(self):
            super().__init__(key='two', kind='weights', assets=('EQQQ', 'USD'), calendar_asset='EQQQ', band=1.0)
    idx = pd.date_range('2026-01-05', periods=3, freq='B')
    eq = pd.DataFrame({'close': [10000.0] * 3, 'adj_close': [10000.0] * 3}, index=idx)
    fx = pd.DataFrame({'close': [1.25] * 3, 'adj_close': [1.25] * 3}, index=idx)
    t = pd.DataFrame({'w_EQQQ': [0.5, 0.5, 0.5], 'w_USD': [0.25, 0.25, 0.25]}, index=idx)
    t['state'] = 'x'
    r = run_pot('p', {'initial_capital': 1000, 'fee_pct': 0.05, 'fx_fee_pct': 0.15}, Two(), t,
                {'EQQQ': eq, 'USD': fx}, fx['close'], '2026-01-01', [], [], 'EQQQ')
    fees = {x['asset']: x['fee'] for x in r.trades}
    assert fees['EQQQ'] == pytest.approx(500 * 0.0005, abs=0.01)
    assert fees['USD'] == pytest.approx(250 * 0.0015, abs=0.01)
    assert r.positions['USD']['units'] == pytest.approx((250 - 0.375) * 1.25)


def test_expected_cone_and_flags(stored):
    from signals.expect import expectation
    s = STRATEGIES['qqq_regime']
    t = s.compute(stored)
    idx = t.loc['2025-01-02':].index
    curve = pd.DataFrame({'nav': np.linspace(1.0, 1.05, len(idx))}, index=idx)
    e = expectation('qqq_trading', s, t, stored, {'fee_pct': 0.05, 'fx_fee_pct': 0.15}, curve, '2025-01-02', 'lse')
    assert e['bt_period'].startswith('Jan 2010') and -0.25 < e['bt_maxdd'] < 0
    assert e['exp_lo'] < e['exp_med'] < e['exp_hi']
    assert len(e['cone']) > len(idx) and e['flags']


def test_journal_keeps_first_record(tmp_path, monkeypatch):
    import signals.journal as J
    monkeypatch.setattr(J, 'PATH', tmp_path / 'journal.json')
    monkeypatch.setattr(J, 'STATE', tmp_path)
    from datetime import datetime, timezone
    trade = {'id': 'p-2026-11-03-EQQQ-BUY', 'date': '2026-11-03', 'side': 'BUY', 'asset': 'EQQQ', 'ccy': 'GBX', 'gbp': 500.0,
             'units': 0.96, 'price': 52000.0, 'reason': 'dip'}
    snap = {'config': {'fills': [], 'start_date': '2026-11-03'},
            'pots': {'p': {'key': 'p', 'name': 'P', 'strategy_name': 'S', 'trades': [trade], 'latest_date': '2026-11-03',
                           'status_provisional': None}}}
    now = datetime(2026, 11, 3, 17, tzinfo=timezone.utc)
    J.update(snap, now)
    snap['pots']['p']['trades'] = [{**trade, 'gbp': 750.0}]
    out = J.update(snap, now)
    assert out[0]['gbp'] == 500.0 and out[0]['status'] == 'confirmed'
    snap['pots']['p']['trades'] = []
    assert J.update(snap, now)[0]['status'] == 'superseded'


def test_risk_radar_panels():
    from signals import radar as R
    out = R.compute()
    keys = [p['key'] for p in out['panels']]
    assert keys == ['late', 'ndx', 'btc']
    for p in out['panels']:
        assert 'error' not in p, p.get('error')
        assert p['level'] in ('GREEN', 'AMBER', 'RED', 'IDLE', 'NO DATA')
        assert p['perf']['headline'] and len(p['signs']) == p['of']
    # thresholds behave as documented
    L = R.late_cycle()
    assert set(L['score'].dropna().unique()) <= {0, 1, 2, 3, 4, 5}
    B = R.btc()
    assert ((B['funding_ann'] > 30) == (B['funding'] == 1))[B['funding'].notna()].all()


def test_bottom_signals():
    from signals import bottoms as B
    panels = B.compute()
    assert [p['key'] for p in panels] == ['fast', 'washout']
    for p in panels:
        assert 'error' not in p, p.get('error')
        assert p['level'] in ('IDLE', 'WATCH', 'SKIP', 'BUY 1', 'BUY 2', 'BUY', 'WAIT')
    hist = {h['start']: h for h in panels[0]['history']}
    # research-locked outcomes
    assert hist['2020-02-05']['buy1'] == '2020-02-27' and hist['2020-02-05']['buy2'] == '2020-03-09'
    assert hist['2021-12-27']['skipped'] is True
    assert hist['2024-07-09']['buy2'] == '2024-08-07'


def test_accumulate_fast_crash_buys():
    idx, px, t, fx = _toy([100] * 12, zone=[False] * 12)
    t['fast_b1'] = [False, False, True] + [False] * 9
    t['fast_b2'] = [False] * 5 + [True] + [False] * 6
    cfg = {'initial_capital': 1000, 'fee_pct': 0, 'cash_rate_pct': 0}
    r = run_pot('v', cfg, Toy('accumulate'), t, {'AAA': px}, fx, '2026-01-01', [], [], 'AAA')
    assert [x['gbp'] for x in r.trades] == [500.0, 500.0]      # buy 1 = half the cash, buy 2 = the rest
    assert r.cash == pytest.approx(0)


def test_value_plan_fast_crash_history(stored):
    s = STRATEGIES['qqq_value']
    us = s.compute_us(stored)
    assert bool(us.loc['2020-02-27', 'fast_b1']) and bool(us.loc['2020-03-09', 'fast_b2'])
    assert not us.loc['2022-01-01':'2022-03-31', 'fast_b1'].any()      # override skipped Jan 2022


def test_journal_execution_decay():
    from signals.journal import summary
    j = [{'status': 'confirmed', 'side': 'BUY', 'needs_fill': False, 'slip_pct': 0.002, 'decay_gbp': 1.0,
          'model': {'pnl': None}, 'actual': {'pnl': None}},
         {'status': 'confirmed', 'side': 'SELL', 'needs_fill': True, 'slip_pct': None, 'decay_gbp': None,
          'model': {'pnl': 12.5}, 'actual': {'pnl': 12.5}}]
    s = summary(j, {})
    assert s['needs_fill'] == 1 and s['closed'] == 1 and s['wins_ideal'] == 1
    assert s['decay_gbp'] == 1.0 and round(s['slip_avg_bps']) == 20


def test_radar_track_scoring():
    import pandas as pd
    from signals import radar_track as T
    idx = pd.bdate_range('2026-11-02', periods=40)
    falling = pd.Series([100.0] * 5 + [100 - 2 * i for i in range(35)], index=idx)
    px = {'spx': falling, 'qqq': falling, 'btc': falling}
    log = {str(d.date()): {'ndx': {'level': 'AMBER' if i < 3 else 'GREEN'}} for i, d in enumerate(idx[:20])}
    r = T.score(log, px)['ndx']
    assert r['n'] == 1 and r['hits'] == 1 and r['episodes'][0]['outcome'] == 'hit'


def test_trend_leg_off_is_a_sell(stored):
    from signals.pipeline import _history
    t = STRATEGIES['qqq_regime'].compute(stored)
    ev = _history('qqq_regime', t, 2000)
    offs = [e for e in ev if e['text'].startswith('Trend leg off')]
    ons = [e for e in ev if e['text'].startswith('Trend leg on')]
    assert offs and all(e['kind'] == 'SELL' for e in offs)
    assert ons and all(e['kind'] == 'BUY' for e in ons)


def test_value_status_not_overwritten_by_live_compute(stored):
    s = STRATEGIES['qqq_value']
    final = s.compute(stored)
    live = {k: v.copy() for k, v in stored.items()}
    q = live['QQQ']
    extra = q.iloc[[-1]].copy(); extra.index = [q.index[-1] + pd.Timedelta(days=1)]
    live['QQQ'] = pd.concat([q, extra * 1.05])
    s.compute(live)                                   # a later live compute
    assert s.status(final)['levels']['close'] == pytest.approx(float(stored['QQQ']['adj_close'].dropna().iloc[-1]))


def test_site_builder_imports():
    from signals.web import build   # a syntax error here would break every scheduled run
    assert build.PAPERS and all(p['slug'] for p in build.PAPERS)


def test_manual_trading_rules_and_maths(monkeypatch):
    from signals import manual as MT
    monkeypatch.setattr(MT, '_risk_budget_now', lambda cfg: 15.0)
    cfg = {'manual': {'capital': 857.0, 'trades': []}}
    d = lambda x: str(x)[:10]
    MT.apply(cfg, {'op': 'manual_open', 'system': '2', 'ticker': 'abc', 'ccy': 'GBP', 'opened': '2026-10-01',
                   'entry': '10', 'stop': '9', 'target': '13', 'units': '15', 'chk_2_0': True, 'chk_2_3': 'on'}, d)
    t = cfg['manual']['trades'][0]
    assert t['ticker'] == 'ABC' and t['side'] == 'long' and t['checks'] == [0, 3]
    with pytest.raises(ValueError, match='budget'):            # 100 units risks £100 > £15
        MT.apply(cfg, {'op': 'manual_open', 'system': '1', 'ticker': 'X', 'ccy': 'GBP', 'entry': '10', 'stop': '9', 'units': '100'}, d)
    with pytest.raises(ValueError, match='stop'):
        MT.apply(cfg, {'op': 'manual_open', 'system': '5', 'ticker': 'X', 'ccy': 'GBP', 'entry': '10', 'stop': '9', 'units': '1'}, d)
    for k in range(2):
        MT.apply(cfg, {'op': 'manual_open', 'system': '2', 'ticker': f'B{k}', 'ccy': 'GBP', 'entry': '10', 'stop': '9', 'units': '1'}, d)
    with pytest.raises(ValueError, match='per system'):
        MT.apply(cfg, {'op': 'manual_open', 'system': '2', 'ticker': 'C', 'ccy': 'GBP', 'entry': '10', 'stop': '9', 'units': '1'}, d)
    MT.apply(cfg, {'op': 'manual_close', 'id': t['id'], 'exit': '12', 'closed': '2026-10-11', 'exit_fees_gbp': '1'}, d)
    v = MT.trade_view(cfg['manual']['trades'][0], None, '2026-11-03')
    assert v['risk_gbp'] == pytest.approx(15) and v['rr_planned'] == pytest.approx(3)
    assert v['pnl_gbp'] == pytest.approx(29) and v['r_multiple'] == pytest.approx(29 / 15) and v['days'] == 10
    snap = MT.compute(cfg, 2000.0, None, '2026-11-03')
    assert snap['by_system']['2']['trades'] == 1 and snap['open_count'] == 2
    assert snap['risk_budget_gbp'] == pytest.approx((2000 + 857 + 29) * 0.005)
    # a short: P&L positive when price falls; USD converted with the rate
    s = MT.trade_view({'id': 's', 'system': '5', 'ticker': 'S', 'side': 'short', 'ccy': 'USD', 'opened': '2026-10-01', 'entry': 100,
                       'stop': 110, 'units': 2, 'status': 'closed', 'closed': '2026-10-05', 'exit': 90}, pd.Series([1.25], index=[pd.Timestamp('2026-09-01')]), '2026-11-03')
    assert s['pnl_gbp'] == pytest.approx(16) and s['r_multiple'] == pytest.approx(1.0)
