import pandas as pd, numpy as np
from common import *; from setup import *
exec(open('run1.py').read().split("def run")[0])
C = pd.read_csv(RD + 'breadth/closes.csv.gz', index_col=0, parse_dates=True); C = C[C.index < '2026-11-03']
C = C[C.index >= '1995-01-01']
W = conditions(M, B, dd_q=.10, dd_s=.075, look=8, mm_low=25, mm_up=10, mm_look=6)
g = C.index.to_period('W-FRI'); Wc = C.groupby(g).last(); Wc.index = C.index.to_series().groupby(g).last().values
spy = wk(P['^GSPC']['adj_close']).reindex(Wc.index).ffill()
ma = Wc.rolling(9).mean(); x = (Wc > ma) & (Wc.shift(1) <= ma.shift(1))
f13 = Wc.shift(-13) / Wc - 1; f26 = Wc.shift(-26) / Wc - 1
s13 = (spy.shift(-13) / spy - 1); s26 = (spy.shift(-26) / spy - 1)
rs = (Wc / Wc.shift(52) - 1).rank(axis=1, pct=True)        # 12-month relative strength rank, known at the week's close
cond = W.reindex(Wc.index).ffill()
setup = cond['flush'] & cond['mm_bottom']; flush = cond['flush']
def agg(mask, label):
    m = x & mask
    r13 = f13[m].stack().dropna(); r26 = f26[m].stack().dropna()
    e13 = (f13.sub(s13, axis=0))[m].stack().dropna(); e26 = (f26.sub(s26, axis=0))[m].stack().dropna()
    return {'label': label, 'n': len(r26.dropna()), 'r13': r13.mean(), 'r26': r26.mean(), 'med26': r26.median(),
            'win26': (r26 > 0).mean(), 'xs13': e13.mean(), 'xs26': e26.mean(), 'beat_spy26': (e26 > 0).mean()}
rows = []
for era, a, b in (('1995-2009', '1995', '2009-12-31'), ('2010-2026', '2010', '2027')):
    E = pd.Series((Wc.index >= a) & (Wc.index <= b), index=Wc.index)
    M_ = lambda s: pd.DataFrame(np.repeat((s & E).values[:, None], Wc.shape[1], axis=1), index=Wc.index, columns=Wc.columns)
    lead = rs >= 0.7
    for lab, mk in (('any 9w cross', M_(pd.Series(True, index=Wc.index))),
                    ('cross in flush', M_(flush)),
                    ('cross in setup (flush+breadth turn)', M_(setup)),
                    ('cross outside flush', M_(~flush)),
                    ('leaders (RS top 30%): any cross', M_(pd.Series(True, index=Wc.index)) & lead),
                    ('leaders: cross in setup', M_(setup) & lead),
                    ('laggards (RS bottom 30%): cross in setup', M_(setup) & (rs <= 0.3))):
        r = agg(mk, lab); r['era'] = era; rows.append(r)
R = pd.DataFrame(rows).set_index(['era', 'label'])
pd.set_option('display.width', 220); print(R.round(3).to_string())
