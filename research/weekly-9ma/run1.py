import json, pandas as pd, numpy as np
from common import *; from setup import *; from bottom import *
P = prices(); B = breadth(); B = B[B.index < '2026-11-03']
for k in list(P): P[k] = P[k][P[k].index < '2026-11-03']
M = {'QQQ': P['^NDX'], 'SPY': P['^GSPC']}
INST = {'NDX': (P['^NDX'], .10), 'SPX': (P['^GSPC'], .075), 'SOX': (P['^SOX'], .15)}
def run(cfg, start='1991-01-01', end='2026-12-31', verbose=False):
    W = conditions(M, B, **cfg)
    out = {}
    for name, (df, thr) in INST.items():
        c = df['adj_close'].dropna(); c = c[c.index >= '1990-01-01']
        w, m, x = cross_up(c)
        cond = W.reindex(w.index).ffill()
        A = [d for d in w.index[x & cond['flush'] & cond['mm_bottom']] if start <= str(d.date()) <= end]
        Bv = [d for d in w.index[x & cond['flush']] if start <= str(d.date()) <= end]
        eps = [e for e in episodes(c, thr) if start <= str(e['start'].date()) <= end]
        out[name] = {'setup': evaluate(c, A, eps, 'setup'), 'cross+flush': evaluate(c, Bv, eps, 'cross+flush')}
    return out
base = dict(dd_q=.10, dd_s=.075, look=8, mm_low=25, mm_up=10, mm_look=6)
res = run(base)
pd.set_option('display.width', 200); pd.set_option('display.max_columns', 20)
for name, d in res.items():
    print('==', name); print(pd.DataFrame({k: summary(v) for k, v in d.items()}).round(3))
r = res['NDX']['setup']; print(r[['ep','depth','signal','low_date','above_low','further','r3m','r6m','r12m']].round(3).to_string())
