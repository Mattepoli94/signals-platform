"""Recent adjusted closes (from 2025-06-01) for the tickers in research-data/recent.txt, fetched in parallel."""
import sys, json, concurrent.futures as cf
import pandas as pd
sys.path.insert(0, '.')
from signals.data import fetch_yahoo
t = open('research-data/recent.txt').read().split()
def get(s):
    try:
        d = fetch_yahoo(s, '2025-06-01'); return s, d['adj_close'].astype('float32'), d['volume'].astype('float64')
    except Exception as e:
        return s, None, str(e)[:60]
C, V, fail = {}, {}, {}
with cf.ThreadPoolExecutor(8) as ex:
    for s, c, v in ex.map(get, t):
        if c is None: fail[s] = v
        else: C[s] = c; V[s] = v
pd.DataFrame(C).sort_index().to_csv('research-data/recent.csv.gz', float_format='%.4f', date_format='%Y-%m-%d', compression='gzip')
pd.DataFrame(V).sort_index().to_csv('research-data/recent_vol.csv.gz', float_format='%.0f', date_format='%Y-%m-%d', compression='gzip')
print(len(C), 'ok', len(fail), 'failed', list(fail)[:10])
