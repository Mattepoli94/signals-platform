import json, pandas as pd, numpy as np, itertools
from common import *; from setup import *; from bottom import *
exec(open('run1.py').read().split("base = dict")[0])
pd.set_option('display.width', 220); pd.set_option('display.max_columns', 30)
base = dict(dd_q=.10, dd_s=.075, look=8, mm_low=25, mm_up=10, mm_look=6)
def base_rates(name, start, end):
    c = INST[name][0]['adj_close'].dropna(); c = c[(c.index >= start) & (c.index <= end)]
    w = wk(c); f = lambda k: (c.shift(-k) / c - 1).reindex(w.index)
    return {'r3m': f(63).mean(), 'r6m': f(126).mean(), 'up6m': (f(126) > 0).mean()}
for era in [('1991-01-01', '2009-12-31'), ('2010-01-01', '2026-12-31')]:
    res = run(base, *era)
    print('\n#### era', era)
    for name, d in res.items():
        t = pd.DataFrame({k: summary(v) for k, v in d.items()})
        t['all weeks'] = pd.Series(base_rates(name, *era))
        print('==', name); print(t.round(3).T[['episodes','signals','median_above_low','within5','after_low','further_med','further_worst','r3m','r6m','r12m','up6m']].to_string())
