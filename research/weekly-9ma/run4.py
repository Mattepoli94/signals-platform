import pandas as pd, numpy as np
from common import *; from setup import *; from trade import *
exec(open('run1.py').read().split("def run")[0])
W = conditions(M, B, dd_q=.10, dd_s=.075, look=8, mm_low=25, mm_up=10, mm_look=6)
pd.set_option('display.width', 220)
def met(eq, posd, a, b):
    e = eq[(eq.index >= a) & (eq.index <= b)]; p = posd[(posd.index >= a) & (posd.index <= b)]
    if len(e) < 100: return (np.nan,)*3
    c, d = stats(e / e.iloc[0]); return round(c*100,1), round(d*100,1), round(p.mean()*100)
rows = []
for name, tk, st in (('QQQ','QQQ','1999-06-01'), ('SPY','SPY','1993-06-01'), ('SOXX','SOXX','2001-12-01')):
    px = P[tk]['adj_close'].dropna(); px = px[px.index >= st]
    w, m9, x = cross_up(px); cond = W.reindex(w.index).ffill()
    above = (w > m9)
    entries = {'buy&hold': pd.Series(True, index=w.index),
               '9w trend (any cross)': x,
               'setup': x & cond['flush'] & cond['mm_bottom'],
               'cross+flush': x & cond['flush']}
    for en, ent in entries.items():
        for ex in (['never'] if en == 'buy&hold' else (['close<9w'] if en.startswith('9w') else list(EXITS))):
            rule = (lambda *a: False) if ex == 'never' else EXITS[ex]
            eq, tr, posd = backtest(px, ent, rule)
            r = {'inst': name, 'entry': en, 'exit': ex, 'trades/yr': round(len(tr) / ((px.index[-1]-px.index[0]).days/365.25), 1)}
            for lab, a, b in (('all', '1990', '2027'), ('to2009', '1990', '2009-12-31'), ('2010+', '2010-01-01', '2027')):
                c, d, e = met(eq, posd, a, b); r[f'{lab} cagr'] = c; r[f'{lab} dd'] = d; r[f'{lab} exp%'] = e
            rows.append(r)
R = pd.DataFrame(rows); print(R.to_string(index=False))
R.to_csv('trade_results.csv', index=False)
