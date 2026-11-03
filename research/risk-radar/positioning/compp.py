import pandas as pd, numpy as np
from evalp import *
cols=['narrow_ndx_63d','gex_high_90pct','dix_low_10pct','skew_high_90pct','am_long_spx_crowded']
X=F[cols]; s=X.sum(axis=1,min_count=len(cols))
G=pd.DataFrame(index=idx)
for k in (1,2,3,4): G[f'pos5>={k}']=(s>=k).astype(float).where(s.notna())
# also add margin and P/C variants
G['narrow_and_any_other']=((X.narrow_ndx_63d==1)&(X.drop(columns='narrow_ndx_63d').sum(axis=1)>=1)).astype(float).where(s.notna())
pers2={'2011-15':('2011','2015'),'2016-19':('2016','2019'),'2020-22':('2020','2022'),'2023-26':('2023','2026'),'all 2011-26':('2011','2026')}
rows=[]
for k in G:
    r={'rule':k}
    for pn,per in pers2.items():
        x=sc(G[k],per)
        if x: r[f'{pn}']=f'on {x[0]:.0f}% lift {x[1]:.2f} caught {x[2]}'
    rows.append(r)
pd.set_option('display.width',300); pd.set_option('display.max_colwidth',40)
print(pd.DataFrame(rows).set_index('rule').to_string())
# per-event readout: score in 15 sessions before each event
print('\nper event: max positioning score in the 15 sessions before, and which parts')
for e in EV:
    if e.year<2011: continue
    j=ii[e]; w=X.iloc[max(0,j-15):j+1]; tot=w.sum(axis=1)
    print(e.date(), int(tot.max()) if tot.notna().any() else None, [c for c in cols if (w[c]==1).any()])
print('\ntoday:', X.iloc[-1].to_dict(), ' score', s.iloc[-1])
