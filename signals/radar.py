"""Risk radar: three early-warning flags, each shown with its tested track record.

Display only: nothing here changes any order. Research and backtests: research/risk-radar.md.

1. Late cycle (S&P 500): a bear market (fall of 19%+) starting within about a year.
   Signs: yield curve flat (10y - 3m < 0.5 pt); valuation (CAPE in the top 10% of its history to date);
   extension (S&P +50% over 504 sessions); rate/inflation pressure (10y +1.5 pt over 252 sessions, or
   CPI inflation > 4% and higher than 6 months earlier); leverage (FINRA margin debt +30% year on year).
   Amber at 2, red at 3.
2. Nasdaq crash risk (prediction, only while QQQ is within 4% of its 1-year high): a fall of 8%+ within
   3 weeks. Families: narrow market (equal-weight QQEW lagging QQQ by 3%+ over 63 sessions, or Cboe
   dispersion DSPX 5-day mean in the top 10% of 2 years); options complacency (Cboe total put/call 10-day
   mean in the bottom 10% of 2 years); Nasdaq fear premium (VXN/VIX 5-day mean in the top 10% of 2 years);
   leverage (margin debt +30% y/y). Amber at 2, red at 3; idle when not near the high.
3. BTC leverage: a fall of 15%+ within 10 days. Signs: Deribit perpetual funding (7-day mean) above 30% a
   year; leveraged funds' net CME bitcoin futures position in the bottom 10% of 2 years (crowded short:
   the leveraged cash-and-carry trade); BTC +40% in 30 days. Amber at 1, red at 2.

Thresholds are fixed or trailing percentiles, computed only from data known on the day.
"""
from __future__ import annotations

import io
import json
import re
import time
import zipfile
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests

from . import DATA, PRICES

RADAR = DATA / 'radar'
UA = {'User-Agent': 'Mozilla/5.0 (signals-platform risk radar)'}
YAHOO = {'TNX': '^TNX', 'IRX': '^IRX', 'GSPC': '^GSPC', 'QQEW': 'QQEW'}
CBOE_IDX = ['VIX', 'VXN', 'DSPX', 'VIX9D']

# Track record from the research (see research/risk-radar.md). Shown on the page next to each flag.
PERF = {
    'late': {
        'predicts': 'A bear market (S&P 500 down 19% or more) starting within the next 12 months',
        'headline': [('2.0×', 'odds of a bear market starting within a year when 2+ signs are on'),
                     ('~1 in 2', 'chance when on, vs ~1 in 4 normally'),
                     ('8 of 14', 'bear-market peaks flagged in advance (1962–2026)'),
                     ('6–13 mo', 'typical warning before the peak')],
        'detail': [('Chosen on', '1955–1994: 2.0× odds, 4 of 7 peaks flagged'),
                   ('Checked on', '1995–2026: 2.0× odds, 4 of 7 peaks flagged (6 of 7 with margin debt)'),
                   ('Time on', 'about 1 day in 5 when the S&P is near its high'),
                   ('Missed', '1961, 1973, 2007 (credit-driven), 2011')],
        'caveat': 'Only 15 bear markets since 1955, so the evidence is thin. Warnings can stay on for months before a top.',
    },
    'ndx': {
        'predicts': 'A Nasdaq-100 fall of 8% or more within 3 weeks, starting near its high',
        'headline': [('1.9×', 'odds of a fast fall when 2+ families are on'),
                     ('19% vs 10%', 'chance of a 10% fall within 2 months: on vs normal'),
                     ('14 of 21', 'fast falls since 2006 had 2+ families on in the month before'),
                     ('≈1.4×', 'stricter estimate (families picked without the test years)')],
        'detail': [('By era', '2011–15 1.7× · 2016–19 4.0× · 2020–22 1.3× · 2023–26 1.6×'),
                   ('Time on', 'about 1 day in 5 when the Nasdaq is near its high'),
                   ('Base rate', '5% of near-high days are followed by an 8% fall within 3 weeks'),
                   ('Recent', 'On 30 Sep – 2 Oct 2026, just before the 6 Oct peak')],
        'caveat': 'A modest edge: most warnings are not followed by a crash, and some crashes come with no warning.',
    },
    'btc': {
        'predicts': 'A BTC fall of 15% or more within 10 days, starting near its 2-month high',
        'headline': [('3.4×', 'odds of a crash when 2+ signs are on'),
                     ('~14%', 'chance when on, vs 4% normally'),
                     ('1.7×', 'odds with 1 sign on'),
                     ('16', 'crashes tested, 2019–2026')],
        'detail': [('By era', '2+ signs: 2019–22 1.9× · 2023–26 2.7×'),
                   ('Time on', '2+ signs about 8% of days; 1+ sign about 28%'),
                   ('Caught', '4 of 16 crashes at 2+ signs, 9 of 16 at 1+'),
                   ('10 Oct 2025', 'funding jumped 5% → 20% a year in the week before (below the 30% trigger)')],
        'caveat': 'Crypto leverage builds fast. Funding data covers 2019 onwards only.',
    },
}


# ----------------------------------------------------------------------------- storage
def _path(name):
    return RADAR / f'{name}.csv'


def _read(name, col=None) -> pd.Series | pd.DataFrame:
    p = _path(name)
    if not p.exists():
        return pd.Series(dtype=float) if col else pd.DataFrame()
    df = pd.read_csv(p, parse_dates=['date']).set_index('date').sort_index()
    df = df[~df.index.duplicated(keep='last')]
    return df[col].astype(float) if col else df


def _write(name, obj):
    RADAR.mkdir(parents=True, exist_ok=True)
    obj.index.name = 'date'
    obj.sort_index().to_csv(_path(name), date_format='%Y-%m-%d')


def _price(key, col='close') -> pd.Series:
    p = PRICES / f'{key}.csv'
    if not p.exists():
        return pd.Series(dtype=float)
    df = pd.read_csv(p, parse_dates=['date']).set_index('date').sort_index()
    return df[col].astype(float)


# ----------------------------------------------------------------------------- fetching
def _get(url, **kw):
    last = None
    for _ in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=60, **kw)
            r.raise_for_status()
            return r
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(3)
    raise RuntimeError(f'{url[:80]}: {last}')


def _multpl(slug) -> pd.Series:
    t = _get(f'https://www.multpl.com/{slug}/table/by-month').text
    rows = re.findall(r'<td>([A-Z][a-z]{2} \d{1,2}, \d{4})</td>\s*<td>\s*(?:&#x2002;)?\s*(-?[\d.]+)', t)
    s = pd.Series({pd.to_datetime(d): float(v) for d, v in rows}).sort_index()
    if len(s) < 500:
        raise RuntimeError(f'multpl {slug}: only {len(s)} rows')
    return s


def fetch(now: datetime | None = None) -> dict:
    """Download/extend every radar input. Each source is independent; failures are reported, not raised."""
    from .data import fetch_yahoo
    now = now or datetime.now(timezone.utc)
    rep = {}

    def step(name, fn):
        try:
            rep[name] = fn() or 'ok'
        except Exception as e:  # noqa: BLE001
            rep[name] = f'failed: {e}'[:200]

    us_closed = pd.Timestamp(now.replace(tzinfo=None)).normalize() + pd.Timedelta(hours=21)   # ~16:00 New York in UTC

    def confirmed(df):
        """Drop today's forming bar until the US close has passed."""
        today = pd.Timestamp(now.date())
        if len(df) and df.index[-1] >= today and pd.Timestamp(now.replace(tzinfo=None)) < us_closed:
            df = df.iloc[:-1]
        return df

    for k, sym in YAHOO.items():
        step(f'yahoo {k}', lambda k=k, sym=sym: _write(f'yahoo_{k}', confirmed(fetch_yahoo(sym, '1950-01-01')[['close', 'adj_close']])))
    for s in CBOE_IDX:
        def cb(s=s):
            df = pd.read_csv(io.StringIO(_get(f'https://cdn.cboe.com/api/global/us_indices/daily_prices/{s}_History.csv').text))
            df.columns = [c.strip().lower() for c in df.columns]
            col = 'close' if 'close' in df else df.columns[-1]
            out = pd.Series(df[col].astype(float).values, index=pd.to_datetime(df['date']), name='close')
            _write(f'cboe_{s}', out.to_frame())
        step(f'cboe {s}', cb)

    def pc():
        df = _read('putcall_total')
        start = (df.index.max() + pd.Timedelta(days=1)) if len(df) else pd.Timestamp('2019-10-07')
        new = {}
        for d in pd.bdate_range(start, now.date()):
            try:
                j = requests.get(f"https://cdn.cboe.com/data/us/options/market_statistics/daily/{d:%Y-%m-%d}_daily_options",
                                 headers=UA, timeout=30)
                if j.ok:
                    rat = {r['name']: r['value'] for r in j.json().get('ratios', [])}
                    tot, eq = rat.get('TOTAL PUT/CALL RATIO'), rat.get('EQUITY PUT/CALL RATIO')
                    if tot not in (None, ''):
                        new[d] = {'total_pc': float(tot), 'equity_pc': float(eq) if eq not in (None, '') else np.nan}
            except Exception:  # noqa: BLE001
                pass
            time.sleep(0.2)
        if new:
            df = pd.concat([df, pd.DataFrame.from_dict(new, orient='index')]).sort_index()
            _write('putcall_total', df[['total_pc', 'equity_pc']])
        return f'+{len(new)} days'
    step('cboe put/call', pc)

    def squeeze():
        df = pd.read_csv(io.StringIO(_get('https://squeezemetrics.com/monitor/static/DIX.csv').text), parse_dates=['date'])
        _write('squeeze', df.set_index('date')[['dix', 'gex']])
    step('squeezemetrics gex/dix', squeeze)

    def margin():
        x = pd.read_excel(io.BytesIO(_get('https://www.finra.org/sites/default/files/2021-03/margin-statistics.xlsx').content))
        x = x.iloc[:, :2]
        x.columns = ['ym', 'debt']
        s = pd.Series(x['debt'].astype(float).values, index=pd.to_datetime(x['ym'].astype(str)))
        _write('margin_debt', s.rename('debt').to_frame())
    step('finra margin', margin)
    step('multpl cape', lambda: _write('cape', _multpl('shiller-pe').rename('cape').to_frame()))
    step('multpl inflation', lambda: _write('inflation', _multpl('inflation').rename('inflation').to_frame()))

    def funding():
        s = _read('btc_funding', 'funding')
        t0 = (s.index.max() - pd.Timedelta(days=2)) if len(s) else pd.Timestamp('2019-05-01')
        rows = []
        while t0 < pd.Timestamp(now.replace(tzinfo=None)):
            t1 = t0 + pd.Timedelta(days=30)
            r = _get('https://www.deribit.com/api/v2/public/get_funding_rate_history',
                     params={'instrument_name': 'BTC-PERPETUAL', 'start_timestamp': int(t0.timestamp() * 1000),
                             'end_timestamp': int(t1.timestamp() * 1000)})
            rows += r.json()['result']
            t0 = t1
        if rows:
            f = pd.DataFrame(rows)
            f['t'] = pd.to_datetime(f['timestamp'], unit='ms')
            d = f.set_index('t')['interest_1h'].resample('D').sum()
            d = d[d.index < pd.Timestamp(now.date())]           # complete UTC days only
            s = pd.concat([s[s.index < d.index.min()], d]).sort_index()
            _write('btc_funding', s.rename('funding').to_frame())
        return f'{len(rows)} hourly rows'
    step('deribit funding', funding)

    def cftc():
        old = _read('cftc_btc')
        z = zipfile.ZipFile(io.BytesIO(_get(f'https://www.cftc.gov/files/dea/history/fut_fin_txt_{now.year}.zip').content))
        df = pd.read_csv(z.open(z.namelist()[0]), low_memory=False)
        df = df[df['CFTC_Contract_Market_Code'].astype(str).str.strip() == '133741']
        new = pd.DataFrame({'lev_long': df['Lev_Money_Positions_Long_All'].values, 'lev_short': df['Lev_Money_Positions_Short_All'].values,
                            'oi': df['Open_Interest_All'].values}, index=pd.to_datetime(df['Report_Date_as_YYYY-MM-DD']))
        out = pd.concat([old, new]).sort_index()
        _write('cftc_btc', out[~out.index.duplicated(keep='last')])
        return f'{len(new)} weeks this year'
    step('cftc bitcoin', cftc)
    return rep


# ----------------------------------------------------------------------------- indicators
def _on(s: pd.Series, idx, lag=None, stale_days=None) -> pd.Series:
    s = s.dropna().sort_index()
    if lag is not None:
        s.index = s.index + lag
    s = s[~s.index.duplicated(keep='last')]
    out = s.reindex(s.index.union(idx)).ffill().reindex(idx)
    if stale_days and len(s):
        out[out.index > s.index.max() + pd.Timedelta(days=stale_days)] = np.nan
    return out


def _tpct(s: pd.Series, n=504, mp=250) -> pd.Series:
    """Share of the previous n-1 values below today's (trailing percentile, no look-ahead)."""
    return s.rolling(n, min_periods=mp).apply(lambda w: (w[:-1] < w[-1]).mean(), raw=True)


def _flag(cond, valid):
    v = cond.astype(float)
    v[~valid.astype(bool)] = np.nan
    return v


def margin_yoy(idx) -> pd.Series:
    m = _read('margin_debt', 'debt')
    if m.empty:
        return pd.Series(np.nan, index=idx)
    m.index = m.index + pd.offsets.MonthEnd(0) + pd.Timedelta(days=20)    # published ~3 weeks after month end
    return _on(m / m.shift(12), idx, stale_days=75)


def late_cycle() -> pd.DataFrame:
    spx = _read('yahoo_GSPC', 'close').dropna()
    idx = spx.index[spx.index >= '1990-01-01']
    spx = spx.reindex(idx)
    tnx = _on(_read('yahoo_TNX', 'close'), idx, stale_days=10)
    irx = _on(_read('yahoo_IRX', 'close'), idx, stale_days=10)
    cape = _read('cape', 'cape')
    cape = cape[cape.index >= '1953-01-01']                                 # research window: 1953 onwards
    pct90 = cape.expanding(min_periods=96).quantile(0.9)
    cape_m = cape.copy()
    cape_m.index = cape_m.index + pd.offsets.MonthEnd(0)                   # month's value known by month end
    pct90.index = cape_m.index
    capev, cap90 = _on(cape_m, idx, stale_days=70), _on(pct90, idx, stale_days=70)
    inf = _read('inflation', 'inflation')
    inf_prev = inf.shift(6)
    inf.index = inf.index + pd.offsets.MonthEnd(1) + pd.Timedelta(days=15)  # CPI out mid next month
    inf_prev.index = inf.index
    infl, infl6 = _on(inf, idx, stale_days=75), _on(inf_prev, idx, stale_days=75)
    my = margin_yoy(idx)
    T = pd.DataFrame(index=idx)
    T['spread'] = tnx - irx
    T['curve'] = _flag(T['spread'] < 0.5, T['spread'].notna())
    T['cape'], T['cape90'] = capev, cap90
    T['valuation'] = _flag(capev > cap90, capev.notna() & cap90.notna())
    T['ext_ret'] = spx / spx.shift(504) - 1
    T['extension'] = _flag(T['ext_ret'] > 0.5, T['ext_ret'].notna())
    T['y10_chg'] = tnx - tnx.shift(252)
    T['infl'], T['infl6'] = infl, infl6
    press = (T['y10_chg'] > 1.5) | ((infl > 4) & (infl > infl6))
    T['pressure'] = _flag(press, T['y10_chg'].notna() | infl.notna())
    T['margin_yoy'] = my - 1
    T['leverage'] = _flag(my > 1.3, my.notna())
    T['near_high'] = spx / spx.rolling(252, min_periods=200).max() - 1
    T['score'] = T[['curve', 'valuation', 'extension', 'pressure', 'leverage']].sum(axis=1, min_count=1)
    return T


def nasdaq() -> pd.DataFrame:
    qqq = _price('QQQ', 'adj_close').dropna()
    raw = _price('QQQ', 'close').reindex(qqq.index)
    idx = qqq.index[qqq.index >= '2006-01-01']
    qqq, raw = qqq.reindex(idx), raw.reindex(idx)
    qqew = _on(_read('yahoo_QQEW', 'adj_close'), idx, stale_days=10)
    dspx = _on(_read('cboe_DSPX', 'close'), idx, stale_days=10)
    vix, vxn = _on(_read('cboe_VIX', 'close'), idx, stale_days=10), _on(_read('cboe_VXN', 'close'), idx, stale_days=10)
    pc = _on(_read('putcall_total', 'total_pc'), idx, stale_days=10)
    my = margin_yoy(idx)
    T = pd.DataFrame(index=idx)
    T['off_high'] = raw / raw.rolling(252, min_periods=200).max() - 1
    near = T['off_high'] >= -0.04
    T['near'] = near.astype(float)
    rel = qqew / qqq
    T['ew_rel63'] = rel / rel.shift(63) - 1
    T['dspx'] = dspx
    T['dspx_pct'] = _tpct(dspx.rolling(5).mean())
    narrow_a = _flag((T['ew_rel63'] < -0.03) & near, T['ew_rel63'].notna())
    narrow_b = _flag(T['dspx_pct'] > 0.9, T['dspx_pct'].notna())
    T['narrow'] = pd.concat([narrow_a, narrow_b], axis=1).max(axis=1)
    T['pc10'] = pc.rolling(10).mean()
    T['pc_pct'] = _tpct(T['pc10'])
    T['complacency'] = _flag(T['pc_pct'] < 0.10, T['pc_pct'].notna())
    T['vxn_vix'] = (vxn / vix)
    T['prem_pct'] = _tpct(T['vxn_vix'].rolling(5).mean())
    T['premium'] = _flag(T['prem_pct'] > 0.90, T['prem_pct'].notna())
    T['margin_yoy'] = my - 1
    T['leverage'] = _flag(my > 1.3, my.notna())
    T['score'] = T[['narrow', 'complacency', 'premium', 'leverage']].sum(axis=1, min_count=1)
    return T


def btc() -> pd.DataFrame:
    b = _price('BTC', 'close').dropna()
    idx = b.index[b.index >= '2019-06-01']
    b = b.reindex(idx)
    f = _read('btc_funding', 'funding')
    ann = (f.rolling(7).mean() * 365 * 100)
    T = pd.DataFrame(index=idx)
    T['funding_ann'] = _on(ann, idx, stale_days=4)
    T['funding'] = _flag(T['funding_ann'] > 30, T['funding_ann'].notna())
    c = _read('cftc_btc')
    if len(c):
        net = (c['lev_long'] - c['lev_short']) / c['oi']
        T['cme_net'] = _on(net, idx, lag=pd.Timedelta(days=4), stale_days=21)
    else:
        T['cme_net'] = np.nan
    T['cme_pct'] = T['cme_net'].rolling(728, min_periods=200).apply(lambda w: (w[:-1] < w[-1]).mean(), raw=True)
    T['crowding'] = _flag(T['cme_pct'] < 0.10, T['cme_pct'].notna())
    T['ret30'] = b / b.shift(30) - 1
    T['runup'] = _flag(T['ret30'] > 0.4, T['ret30'].notna())
    T['score'] = T[['funding', 'crowding', 'runup']].sum(axis=1, min_count=1)
    return T


# ----------------------------------------------------------------------------- snapshot
def _f(x, fmt):
    return '—' if x is None or (isinstance(x, float) and np.isnan(x)) else fmt.format(x)


def _level(score, amber, red):
    if score is None or np.isnan(score):
        return 'NO DATA', 'grey'
    return ('RED', 'red') if score >= red else (('AMBER', 'amber') if score >= amber else ('GREEN', 'green'))


def _hist(T, years=3):
    h = T['score'].dropna()
    h = h[h.index >= h.index.max() - pd.DateOffset(years=years)]
    return [[d.strftime('%Y-%m-%d'), float(v)] for d, v in h.items()]


def _sign(label, on, value, trigger, explain):
    ok = None if (on is None or (isinstance(on, float) and np.isnan(on))) else bool(on)
    return {'label': label, 'on': ok, 'value': value, 'trigger': trigger, 'explain': explain}


def compute() -> dict:
    out = {'generated': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'), 'panels': []}
    try:
        L = late_cycle()
        x = L.iloc[-1]
        lvl, tone = _level(x['score'], 2, 3)
        out['panels'].append({
            'key': 'late', 'title': 'Late-cycle radar', 'market': 'S&P 500 / whole market', 'horizon': '6–12 months',
            'asof': L.index[-1].strftime('%Y-%m-%d'), 'level': lvl, 'tone': tone, 'score': x['score'], 'of': 5,
            'rule': 'Amber at 2 signs, red at 3',
            'summary': {'GREEN': 'No late-cycle build-up: fewer than 2 signs on.',
                        'AMBER': 'Late-cycle conditions building: 2 signs on. Historically the odds of a bear market starting within a year roughly double.',
                        'RED': '3 or more late-cycle signs on: a fragile market. Historically the odds of a bear market within a year are well above normal.',
                        'NO DATA': 'Data unavailable.'}[lvl],
            'signs': [
                _sign('Yield curve flat', x['curve'], _f(x['spread'], '{:+.2f} pt'), '10y − 3m below +0.50 pt', 'A flat or inverted curve has preceded most recessions and bear markets.'),
                _sign('Valuation stretched', x['valuation'], f"CAPE {_f(x['cape'], '{:.1f}')}", f"top 10% of history (≥ {_f(x['cape90'], '{:.1f}')})", 'Shiller CAPE: price vs 10 years of real earnings.'),
                _sign('Overextended rally', x['extension'], _f(x['ext_ret'] * 100 if x['ext_ret'] == x['ext_ret'] else None, '{:+.0f}%') + ' in 2 years', 'S&P up 50%+ in 2 years', 'Parabolic advances tend to come before tops.'),
                _sign('Rate or inflation pressure', x['pressure'], f"10y {_f(x['y10_chg'], '{:+.2f}')} pt in 1y · CPI {_f(x['infl'], '{:.1f}')}%", '10y +1.5 pt in a year, or CPI > 4% and rising', 'Fast-rising rates or inflation squeeze valuations.'),
                _sign('Leverage surge', x['leverage'], _f(x['margin_yoy'] * 100 if x['margin_yoy'] == x['margin_yoy'] else None, '{:+.0f}%') + ' y/y', 'Margin debt +30% year on year', 'FINRA margin debt: money borrowed to buy shares.'),
            ],
            'context': f"S&P 500 is {_f(-x['near_high'] * 100, '{:.1f}')}% below its 1-year high. The radar matters most while the market is near its high.",
            'hist': _hist(L, 5), 'perf': PERF['late'], 'amber': 2, 'red': 3})
    except Exception as e:  # noqa: BLE001
        out['panels'].append({'key': 'late', 'title': 'Late-cycle radar', 'error': str(e)[:200], 'perf': PERF['late']})
    try:
        N = nasdaq()
        x = N.iloc[-1]
        near = x['near'] == 1
        lvl, tone = _level(x['score'], 2, 3)
        if not near:
            lvl, tone = 'IDLE', 'grey'
        out['panels'].append({
            'key': 'ndx', 'title': 'Nasdaq crash-risk radar', 'market': 'Nasdaq-100', 'horizon': '3 weeks – 2 months',
            'asof': N.index[-1].strftime('%Y-%m-%d'), 'level': lvl, 'tone': tone, 'score': x['score'], 'of': 4,
            'rule': 'Active only within 4% of the 1-year high · amber at 2 families, red at 3',
            'summary': {'IDLE': f"Idle: the Nasdaq-100 is {abs(x['off_high']) * 100:.1f}% below its 1-year high. This radar warns about crashes that start near highs; it switches on again within 4% of the high.",
                        'GREEN': 'Near the high with fewer than 2 warning families on.',
                        'AMBER': '2 warning families on near the high: historically the odds of an 8% fall within 3 weeks roughly double.',
                        'RED': '3+ warning families on near the high: historically several times the normal odds of a fast fall.',
                        'NO DATA': 'Data unavailable.'}[lvl],
            'signs': [
                _sign('Narrow market', x['narrow'], f"equal-weight {_f(x['ew_rel63'] * 100 if x['ew_rel63'] == x['ew_rel63'] else None, '{:+.1f}%')} vs QQQ (3 mo) · dispersion pct {_f(x['dspx_pct'] * 100 if x['dspx_pct'] == x['dspx_pct'] else None, '{:.0f}')}",
                      'equal-weight lags 3%+ near highs, or DSPX in top 10%', 'Few stocks carry the index: a fragile rally.'),
                _sign('Options complacency', x['complacency'], f"put/call {_f(x['pc10'], '{:.2f}')} (pct {_f(x['pc_pct'] * 100 if x['pc_pct'] == x['pc_pct'] else None, '{:.0f}')})", 'put/call in bottom 10% of 2 years', 'Few people are buying protection.'),
                _sign('Nasdaq fear premium', x['premium'], f"VXN/VIX {_f(x['vxn_vix'], '{:.2f}')} (pct {_f(x['prem_pct'] * 100 if x['prem_pct'] == x['prem_pct'] else None, '{:.0f}')})", 'in top 10% of 2 years', 'Nasdaq options price more risk than the S&P.'),
                _sign('Leverage surge', x['leverage'], _f(x['margin_yoy'] * 100 if x['margin_yoy'] == x['margin_yoy'] else None, '{:+.0f}%') + ' y/y', 'margin debt +30% y/y', 'Borrowed money amplifies falls.'),
            ],
            'context': f"Nasdaq-100 (QQQ) is {abs(x['off_high']) * 100:.1f}% below its 1-year high.",
            'hist': _hist(N, 3), 'perf': PERF['ndx'], 'amber': 2, 'red': 3})
    except Exception as e:  # noqa: BLE001
        out['panels'].append({'key': 'ndx', 'title': 'Nasdaq crash-risk radar', 'error': str(e)[:200], 'perf': PERF['ndx']})
    try:
        B = btc()
        x = B.iloc[-1]
        lvl, tone = _level(x['score'], 1, 2)
        out['panels'].append({
            'key': 'btc', 'title': 'BTC leverage radar', 'market': 'Bitcoin', 'horizon': '10 days',
            'asof': B.index[-1].strftime('%Y-%m-%d'), 'level': lvl, 'tone': tone, 'score': x['score'], 'of': 3,
            'rule': 'Amber at 1 sign, red at 2',
            'summary': {'GREEN': 'No leverage froth: funding, futures positioning and the 30-day move are all normal.',
                        'AMBER': '1 leverage sign on: crash odds about 1.7× normal.',
                        'RED': '2+ leverage signs on: crash odds about 3.4× normal. Liquidation cascades start from setups like this.',
                        'NO DATA': 'Data unavailable.'}[lvl],
            'signs': [
                _sign('Funding rate high', x['funding'], _f(x['funding_ann'], '{:.1f}%') + ' a year (7-day)', 'above 30% a year', 'What leveraged longs pay on perpetual futures (Deribit).'),
                _sign('Hedge funds crowded on CME', x['crowding'], f"net {_f(x['cme_net'] * 100 if x['cme_net'] == x['cme_net'] else None, '{:+.0f}%')} of OI (pct {_f(x['cme_pct'] * 100 if x['cme_pct'] == x['cme_pct'] else None, '{:.0f}')})", 'net short in bottom 10% of 2 years', 'Leveraged cash-and-carry trades (CFTC, weekly).'),
                _sign('Fast run-up', x['runup'], _f(x['ret30'] * 100 if x['ret30'] == x['ret30'] else None, '{:+.0f}%') + ' in 30 days', 'BTC +40% in 30 days', 'Steep rallies attract leverage.'),
            ],
            'context': '',
            'hist': _hist(B, 3), 'perf': PERF['btc'], 'amber': 1, 'red': 2})
    except Exception as e:  # noqa: BLE001
        out['panels'].append({'key': 'btc', 'title': 'BTC leverage radar', 'error': str(e)[:200], 'perf': PERF['btc']})
    from . import bottoms
    out['bottoms'] = bottoms.compute()
    return out
