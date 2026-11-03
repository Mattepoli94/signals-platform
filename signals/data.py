"""Data layer: free sources (Yahoo chart API, FRED), CSV upload, local store and freshness.

Every asset is stored as data/prices/<KEY>.csv with columns
date, open, high, low, close, adj_close, volume  (only confirmed daily closes).
A bar that is still forming (US market open, or the current UTC day for BTC) is kept apart in
state/live.json and is used only for the pre-close preview, never for the pot ledger.
"""
from __future__ import annotations

import io
import json
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests

from . import PRICES, STATE, UPLOADS
from .assets import ASSETS

NY = ZoneInfo('America/New_York')
LDN = ZoneInfo('Europe/London')
COLS = ['open', 'high', 'low', 'close', 'adj_close', 'volume']
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/126.0 Safari/537.36'}


# ----------------------------------------------------------------------------- store
def path(key: str):
    return PRICES / f'{key}.csv'


def load(key: str) -> pd.DataFrame:
    p = path(key)
    if not p.exists():
        return pd.DataFrame(columns=COLS, index=pd.DatetimeIndex([], name='date'))
    df = pd.read_csv(p, parse_dates=['date']).set_index('date').sort_index()
    df = df[~df.index.duplicated(keep='last')]
    for c in COLS:
        if c not in df:
            df[c] = np.nan
    df['adj_close'] = df['adj_close'].fillna(df['close'])
    return df[COLS].astype(float)


def save(key: str, df: pd.DataFrame):
    PRICES.mkdir(parents=True, exist_ok=True)
    out = df[COLS].copy().sort_index()
    out = out[~out.index.duplicated(keep='last')]
    out.index.name = 'date'
    out.to_csv(path(key), float_format='%.6f', date_format='%Y-%m-%d')


def merge(old: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    """New rows win on overlapping dates; older history is kept."""
    if old is None or old.empty:
        return new.sort_index()
    if new.empty:
        return old
    both = pd.concat([old[~old.index.isin(new.index)], new]).sort_index()
    # a fresh download rebases adjusted closes (dividends); rescale kept older rows to match
    ov = old.index.intersection(new.index)
    if len(ov):
        d = ov[0]
        k_old = old.at[d, 'adj_close'] / old.at[d, 'close'] if old.at[d, 'close'] else 1.0
        k_new = new.at[d, 'adj_close'] / new.at[d, 'close'] if new.at[d, 'close'] else 1.0
        if k_old and np.isfinite(k_old) and np.isfinite(k_new) and abs(k_new / k_old - 1) > 1e-6:
            older = both.index < d
            both.loc[older, 'adj_close'] = both.loc[older, 'adj_close'] * (k_new / k_old)
    return both


def series(key: str, col: str = 'adj_close') -> pd.Series:
    s = load(key)[col].dropna()
    s.name = key
    return s


# ----------------------------------------------------------------------------- confirmation rules
def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def is_confirmed(key: str, d: pd.Timestamp, now: datetime | None = None) -> bool:
    """A daily bar is final once its session has closed (+15 min for the official close print)."""
    now = now or now_utc()
    cal = ASSETS[key].calendar if key in ASSETS else 'us'
    if cal == 'crypto':
        return now >= datetime(d.year, d.month, d.day, tzinfo=timezone.utc) + timedelta(days=1)
    if cal == 'fx':
        return now >= datetime(d.year, d.month, d.day, 22, 0, tzinfo=timezone.utc)
    close = datetime(d.year, d.month, d.day, 16, 15, tzinfo=NY)
    return now >= close


# ----------------------------------------------------------------------------- sources
def fetch_yahoo(symbol: str, start: str = '1990-01-01') -> pd.DataFrame:
    p1 = int(pd.Timestamp(start, tz='UTC').timestamp())
    p2 = int(time.time()) + 86400
    url = f'https://query2.finance.yahoo.com/v8/finance/chart/{requests.utils.quote(symbol)}'
    params = {'period1': p1, 'period2': p2, 'interval': '1d', 'events': 'div,split', 'includeAdjustedClose': 'true'}
    last = None
    for host in ('query2', 'query1'):
        try:
            r = requests.get(url.replace('query2', host), params=params, headers=UA, timeout=30)
            r.raise_for_status()
            res = r.json()['chart']['result'][0]
            break
        except Exception as e:  # noqa: BLE001
            last = e
    else:
        raise RuntimeError(f'Yahoo download failed for {symbol}: {last}')
    tz = ZoneInfo(res['meta'].get('exchangeTimezoneName') or 'UTC')
    ts = res.get('timestamp') or []
    q = res['indicators']['quote'][0]
    adj = (res['indicators'].get('adjclose') or [{}])[0].get('adjclose') or q['close']
    dates = [datetime.fromtimestamp(t, tz).date() for t in ts]
    df = pd.DataFrame({'open': q['open'], 'high': q['high'], 'low': q['low'], 'close': q['close'],
                       'adj_close': adj, 'volume': q.get('volume')}, index=pd.DatetimeIndex(dates, name='date'))
    df = df.astype(float)
    df['adj_close'] = df['adj_close'].fillna(df['close'])
    df = df[df['close'].notna()]
    return df[~df.index.duplicated(keep='last')]


def fetch_fred(series_id: str) -> pd.Series:
    url = 'https://fred.stlouisfed.org/graph/fredgraph.csv'
    r = requests.get(url, params={'id': series_id}, headers=UA, timeout=30)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df.columns = ['date', 'value']
    df['date'] = pd.to_datetime(df['date'])
    return pd.to_numeric(df.set_index('date')['value'], errors='coerce').dropna()


def fetch_netliq() -> pd.DataFrame:
    walcl = fetch_fred('WALCL') / 1000.0          # $m -> $bn (weekly, Wednesday)
    tga = fetch_fred('WTREGEN')                   # $bn (weekly)
    rrp = fetch_fred('RRPONTSYD')                 # $bn (daily)
    idx = walcl.index.union(tga.index).union(rrp.index)
    f = lambda s: s.reindex(idx).ffill()
    v = (f(walcl) - f(tga) - f(rrp)).dropna()
    v = v[v.index >= '2010-01-01']
    return pd.DataFrame({'open': v, 'high': v, 'low': v, 'close': v, 'adj_close': v, 'volume': np.nan})


# ----------------------------------------------------------------------------- refresh
def refresh(keys=None, now: datetime | None = None) -> dict:
    """Download every asset, store confirmed bars, keep forming bars in state/live.json.
    Returns a report {key: {'ok': bool, 'last': date, 'rows_added': n, 'error': str}}."""
    now = now or now_utc()
    keys = keys or list(ASSETS)
    report, live = {}, {}
    for k in keys:
        a = ASSETS[k]
        old = load(k)
        try:
            try:
                new = fetch_netliq() if a.source == 'fred' else fetch_yahoo(a.symbol)
            except Exception:
                if not a.fallback:
                    raise
                v = fetch_fred(a.fallback)
                v = v[v.index >= (old.index[-1] - pd.Timedelta(days=30) if len(old) else pd.Timestamp('2000-01-01'))]
                new = pd.DataFrame({'open': v, 'high': v, 'low': v, 'close': v, 'adj_close': v, 'volume': np.nan})
            conf = new[[is_confirmed(k, d, now) for d in new.index]] if a.source != 'fred' else new
            forming = new[~new.index.isin(conf.index)]
            if not forming.empty:
                d = forming.index[-1]
                live[k] = {'date': d.strftime('%Y-%m-%d'), 'close': float(forming['close'].iloc[-1]),
                           'adj_close': float(forming['adj_close'].iloc[-1])}
            merged = merge(old, conf)
            save(k, merged)
            report[k] = {'ok': True, 'last': merged.index[-1].strftime('%Y-%m-%d'),
                         'rows_added': int(len(merged) - len(old)), 'error': ''}
        except Exception as e:  # noqa: BLE001 - one failed feed must not stop the run
            report[k] = {'ok': False, 'last': old.index[-1].strftime('%Y-%m-%d') if len(old) else '',
                         'rows_added': 0, 'error': str(e)[:300]}
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / 'live.json').write_text(json.dumps({'fetched_utc': now.strftime('%Y-%m-%d %H:%M'), 'bars': live}, indent=1))
    return report


def load_live() -> dict:
    p = STATE / 'live.json'
    return json.loads(p.read_text()) if p.exists() else {'bars': {}}


# ----------------------------------------------------------------------------- CSV upload
ALIASES = {
    'date': ['date', 'datetime', 'time', 'timestamp', 'observation_date'],
    'open': ['open'], 'high': ['high'], 'low': ['low'],
    'close': ['close', 'price', 'last', 'close/last', 'value'],
    'adj_close': ['adj close', 'adj_close', 'adjclose', 'adjusted close', 'adjusted_close'],
    'volume': ['volume', 'vol.', 'vol'],
}


def _num(s: pd.Series) -> pd.Series:
    if s.dtype.kind in 'if':
        return s.astype(float)
    t = s.astype(str).str.replace(r'[$,£\s]', '', regex=True)
    mult = t.str[-1].map({'K': 1e3, 'M': 1e6, 'B': 1e9}).fillna(1.0)
    t = t.str.rstrip('KMB%')
    return pd.to_numeric(t, errors='coerce') * mult


def parse_csv(text: str) -> pd.DataFrame:
    """Accepts Yahoo, Investing.com, Nasdaq.com, FRED and this platform's own format."""
    raw = pd.read_csv(io.StringIO(text))
    low = {c.strip().lower(): c for c in raw.columns}
    pick = {}
    for k, names in ALIASES.items():
        for n in names:
            if n in low:
                pick[k] = low[n]
                break
    if 'date' not in pick or 'close' not in pick:
        raise ValueError(f'CSV needs a date and a close/price column; found {list(raw.columns)}')
    out = pd.DataFrame({k: (_num(raw[v]) if k != 'date' else raw[v]) for k, v in pick.items()})
    out['date'] = pd.to_datetime(out['date'], errors='coerce', format='mixed', dayfirst=False)
    out = out.dropna(subset=['date', 'close']).set_index('date').sort_index()
    out.index = out.index.tz_localize(None) if out.index.tz is not None else out.index
    out.index = out.index.normalize()
    for c in COLS:
        if c not in out:
            out[c] = out['close'] if c in ('open', 'high', 'low', 'adj_close') else np.nan
    return out[COLS]


def import_csv(key: str, text: str) -> dict:
    key = key.upper()
    if key not in ASSETS:
        raise ValueError(f'Unknown asset {key}. Known: {", ".join(ASSETS)}')
    new = parse_csv(text)
    old = load(key)
    if 'adj_close' in new and new['adj_close'].equals(new['close']) and len(old):
        # file has no adjusted close: keep the stored adjustment factor where dates overlap
        k = (old['adj_close'] / old['close']).reindex(new.index).ffill().fillna(1.0)
        new['adj_close'] = new['close'] * k
    merged = merge(old, new)
    save(key, merged)
    return {'asset': key, 'rows_in_file': int(len(new)), 'first': new.index[0].strftime('%Y-%m-%d'),
            'last': new.index[-1].strftime('%Y-%m-%d'), 'rows_added': int(len(merged) - len(old))}


def import_uploads() -> list:
    """Imports every data/uploads/<KEY>*.csv and deletes it afterwards."""
    done = []
    for p in sorted(UPLOADS.glob('*.csv')):
        key = p.stem.split('_')[0].split('-')[0].split(' ')[0].upper()
        key = {'BTC-USD': 'BTC', 'GBPUSD=X': 'GBPUSD', '^IRX': 'IRX', 'DX-Y': 'DXY'}.get(key, key)
        try:
            done.append(import_csv(key, p.read_text()))
            p.unlink()
        except Exception as e:  # noqa: BLE001
            done.append({'asset': key, 'error': str(e)[:300]})
    return done


# ----------------------------------------------------------------------------- freshness
def expected_last(key: str, now: datetime | None = None) -> pd.Timestamp:
    """Latest daily bar that should already be confirmed."""
    now = now or now_utc()
    cal = ASSETS[key].calendar
    if cal == 'crypto':
        return pd.Timestamp((now - timedelta(days=1)).date())
    if cal == 'macro' and ASSETS[key].source == 'fred':
        return pd.Timestamp((now - timedelta(days=10)).date())
    d = pd.Timestamp(now.astimezone(NY).date())
    while True:
        if d.weekday() < 5 and is_confirmed(key, d, now):
            return d
        d -= pd.Timedelta(days=1)


def freshness(now: datetime | None = None) -> list:
    rows = []
    for k, a in ASSETS.items():
        df = load(k)
        last = df.index[-1] if len(df) else None
        exp = expected_last(k, now)
        lag = (exp - last).days if last is not None else None
        # US holidays make a 1-3 day gap normal; flag only real staleness
        status = 'missing' if last is None else ('ok' if lag <= (1 if a.calendar == 'crypto' else 4) else 'stale')
        rows.append({'key': k, 'name': a.name, 'last': last.strftime('%Y-%m-%d') if last is not None else '-',
                     'expected': exp.strftime('%Y-%m-%d'), 'status': status, 'source': a.source})
    return rows
