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
    keys = ['EQQQ', 'QQQ', 'UUP', 'TLT', 'GLD', 'IRX', 'DXY', 'BTC', 'NETLIQ', 'GBPUSD']
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


def test_btc_1_nov_2026(stored):
    t = STRATEGIES['btc_trend'].compute(stored).loc[:'2026-11-01']
    x = t.iloc[-1]
    assert x['score'] == pytest.approx(0.2)
    assert int(x['days_since_halving']) == 925 and not x['halving_window']
    assert x['w_BTC'] == pytest.approx(0.2)
    assert t.loc['2026-01-01', 'halving_window'] and t.loc['2026-01-01', 'w_BTC'] == 0


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
