import pandas as pd, numpy as np, itertools
from common import *; from setup import *; from bottom import *
exec(open('run1.py').read().split("base = dict")[0])
rows=[]
for mm_low, mm_up, look, kind in itertools.product([15,25,35,100],[5,10,15],[4,8,13],['sma']):
    cfg=dict(dd_q=.10, dd_s=.075, look=look, mm_low=mm_low, mm_up=mm_up, mm_look=6)
    for era in [('1991-01-01','2009-12-31'),('2010-01-01','2026-12-31')]:
        res=run(cfg,*era)
        for name in ('NDX','SPX','SOX'):
            s=summary(res[name]['setup']); rows.append({**cfg,'era':era[0][:4],'inst':name,**s.to_dict()})
R=pd.DataFrame(rows)
pd.set_option('display.width',220)
g=R.pivot_table(index=['mm_low','mm_up','look'],columns=['era','inst'],values='r6m').round(3)
print(g.to_string())
print(R.pivot_table(index=['mm_low','mm_up','look'],columns=['era','inst'],values='signals').to_string())
