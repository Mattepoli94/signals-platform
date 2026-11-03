"""Breadth research data: try Barchart $MMFI/$MMTW/$MMTH; build % of stocks above their 50-day average
from current S&P 500/400/600 + Nasdaq-100 members (Yahoo adjusted closes). Writes research-data/breadth/."""
import io, os, sys, time, json
import pandas as pd, requests
sys.path.insert(0, '.')
from signals.data import fetch_yahoo
OUT = 'research-data/breadth'; os.makedirs(OUT, exist_ok=True)
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'}
log = {}

# 1) Barchart market-breadth symbols
try:
    s = requests.Session(); s.headers.update(UA)
    s.get('https://www.barchart.com/stocks/quotes/$MMFI/price-history/historical', timeout=60)
    tok = requests.utils.unquote(s.cookies.get('XSRF-TOKEN', ''))
    for sym in ('$MMFI', '$MMTW', '$MMOH', '$MMTH', '$NCFI', '$S5FI', '$NDFI'):
        try:
            r = s.get('https://www.barchart.com/proxies/timeseries/queryeod.ashx',
                      params={'symbol': sym, 'data': 'daily', 'maxrecords': 20000, 'volume': 'contract', 'order': 'asc',
                              'dividends': 'false', 'backadjust': 'false', 'daystoexpiration': 1, 'contractroll': 'expiration'},
                      headers={'x-xsrf-token': tok, 'referer': 'https://www.barchart.com/'}, timeout=60)
            open(f"{OUT}/barchart_{sym[1:]}.csv", 'w').write(r.text)
            log[sym] = f'{r.status_code} {len(r.text)} {r.text[:80]!r}'
        except Exception as e:
            log[sym] = f'failed {e}'
        time.sleep(2)
except Exception as e:
    log['barchart'] = f'failed {e}'

# 2) constituents
tick = {}
for name, url, col in (('sp500', 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies', 'Symbol'),
                       ('sp400', 'https://en.wikipedia.org/wiki/List_of_S%26P_400_companies', None),
                       ('sp600', 'https://en.wikipedia.org/wiki/List_of_S%26P_600_companies', None),
                       ('ndx', 'https://en.wikipedia.org/wiki/Nasdaq-100', None)):
    try:
        html = requests.get(url, headers=UA, timeout=60).text
        for t in pd.read_html(io.StringIO(html)):
            c = next((k for k in t.columns if str(k).strip().lower() in ('symbol', 'ticker', 'ticker symbol')), None)
            if c is not None and len(t) > 50:
                tick[name] = sorted({str(v).strip().replace('.', '-') for v in t[c] if isinstance(v, str)})
                break
        log[name] = len(tick.get(name, []))
    except Exception as e:
        log[name] = f'failed {e}'
json.dump(tick, open(f'{OUT}/members.json', 'w'))
allt = sorted(set().union(*tick.values())) if tick else []
closes, vols = {}, {}
for i, t in enumerate(allt):
    try:
        df = fetch_yahoo(t, '1990-01-01')
        closes[t] = df['adj_close'].astype('float32'); vols[t] = (df['volume'] * df['close']).astype('float32')
    except Exception as e:
        log['fail_' + t] = str(e)[:80]
    time.sleep(0.4)
C = pd.DataFrame(closes).sort_index(); V = pd.DataFrame(vols).sort_index()
C.to_csv(f'{OUT}/closes.csv.gz', float_format='%.4g', date_format='%Y-%m-%d', compression='gzip')
V.to_csv(f'{OUT}/dollar_volume.csv.gz', float_format='%.4g', date_format='%Y-%m-%d', compression='gzip')
out = {}
for n in [20, 50, 200]:
    ma = C.rolling(n, min_periods=n).mean()
    valid = ma.notna() & C.notna()
    for uni, members in list(tick.items()) + [('all', allt)]:
        m = [c for c in members if c in C.columns]
        above = ((C[m] > ma[m]) & valid[m]).sum(axis=1); cnt = valid[m].sum(axis=1)
        out[f'{uni}_above{n}'] = (above / cnt * 100).where(cnt >= 30)
        if n == 50: out[f'{uni}_count'] = cnt
pd.DataFrame(out).to_csv(f'{OUT}/breadth.csv', float_format='%.2f', date_format='%Y-%m-%d')
log['stocks'] = C.shape[1]
json.dump(log, open(f'{OUT}/log.json', 'w'), indent=1)
print({k: v for k, v in log.items() if not k.startswith('fail_')})
