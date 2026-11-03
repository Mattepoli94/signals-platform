import pandas as pd, numpy as np
from ind import P,C
t=pd.read_pickle('t_qqq.pkl'); SP=pd.read_pickle('SP.pkl'); T=pd.read_pickle('diptrades.pkl')
q=P['QQQ'].dropna(); r=q.pct_change().fillna(0)
irx=C['^IRX'].reindex(q.index).ffill()/100; cash=(1+irx)**(1/252)-1
storm=SP['storm>=2'].shift(1)
def run(scale_on, start='2007-02-01'):
    wd=t['w_dip'].copy()
    # scale whole trade by storm state at entry
    entry_state=pd.Series(np.nan,index=wd.index)
    st=None
    for i in range(len(wd)):
        if wd.iloc[i]>0 and (i==0 or wd.iloc[i-1]==0): st=storm.iloc[i]
        if wd.iloc[i]==0: st=None
        entry_state.iloc[i]=st if st is not None else np.nan
    wd=wd*np.where(entry_state==1,scale_on,1.0)
    w=t['w_trend']+wd*(1-t['w_trend'])
    ret=w.shift(1)*r+(1-w.shift(1))*cash-0.0003*w.diff().abs()
    ret=ret[start:]; eq=(1+ret).cumprod(); y=len(ret)/252
    c=eq.iloc[-1]**(1/y)-1; dd=(eq/eq.cummax()-1).min()
    out=[round(c*100,1),round(dd*100,1),round(c/-dd,2)]
    for a,b in [('2007-02-01','2012-12-31'),('2013-01-01','2026-12-31')]:
        x=ret[a:b]; e=(1+x).cumprod(); out.append(f'{(e.iloc[-1]**(252/len(x))-1)*100:.1f}/{(e/e.cummax()-1).min()*100:.1f}')
    return out
print('variant: CAGR, maxDD, Calmar, 2007-12, 2013-26')
for nm,sc in [('dip leg as now',1.0),('half-size dips in a storm',0.5),('no dips in a storm',0.0),('dips 1.0 only in storm (none otherwise)',None)]:
    if sc is None: continue
    print(f'{nm:30s}',run(sc))
