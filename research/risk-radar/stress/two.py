import pandas as pd, numpy as np
from ind import P,C
ndx=P['^NDX'].dropna(); idx=ndx.index[ndx.index>='1990-01-01']; ndx=ndx.reindex(idx)
I=pd.read_pickle('I_ndx.pkl'); S=pd.read_pickle('S_ndx.pkl')
f=lambda s: s.dropna().reindex(s.dropna().index.union(idx)).ffill().reindex(idx)
vix,vix3,vvix=f(C['^VIX']),f(C['^VIX3M']),f(C['^VVIX'])
near=ndx/ndx.rolling(252).max()-1>-0.03
r=np.log(ndx).diff()
# extra short-horizon candidates
I['ext_10pct_above_50d']=(ndx/ndx.rolling(50).mean()>1.10).astype(float)
I['rsi14_gt_75']=0.0
d=ndx.diff(); up=d.clip(lower=0).ewm(alpha=1/14).mean(); dn=(-d.clip(upper=0)).ewm(alpha=1/14).mean(); I['rsi14_gt_75']=((100-100/(1+up/dn))>75).astype(float)
I['vix_curve_flat_at_high']=((vix/vix3>0.92)&near).astype(float); I.loc[vix3.isna(),'vix_curve_flat_at_high']=np.nan
I['vix_up_at_high_20pct']=((vix/vix.rolling(10).min()>1.2)&near).astype(float)
I['vvix_gt_100']=(vvix>100).astype(float); I.loc[vvix.isna(),'vvix_gt_100']=np.nan
I['big_down_day_at_high']=((r.rolling(5).min()<-0.025)&near).astype(float)
I['score>=2']=(S.sum(axis=1)>=2).astype(float)
a=ndx.values
def fmin(h):
    o=np.full(len(a),np.nan)
    for i in range(len(a)-h): o[i]=a[i+1:i+1+h].min()/a[i]-1
    return pd.Series(o,index=idx)
EF=(fmin(10)<=-0.07).astype(float); EF[fmin(10).isna()]=np.nan
EB=(fmin(252)<=-0.20).astype(float); EB[fmin(252).isna()]=np.nan
rows=[]
for k in I.columns:
    for nm,(x,y) in {'A':('1990-01-01','2012-12-31'),'B':('2013-01-01','2026-12-31')}.items():
        m=(idx>=x)&(idx<=y)&I[k].notna()
        fl=I[k][m]==1
        def lift(E):
            mm=E[m].notna(); e=E[m][mm]==1; ff=fl[mm]
            return (e[ff].mean()/e.mean()) if ff.sum()>20 and e.mean()>0 else np.nan
        rows.append(dict(flag=k,per=nm,on=fl.mean()*100,flash=lift(EF),bear=lift(EB)))
R=pd.DataFrame(rows)
print('base flash (>=7% in 10d):',{p:round(float(EF[(idx>=x)&(idx<=y)].mean()*100),1) for p,(x,y) in {'A':('1990','2012'),'B':('2013','2026')}.items()},
      ' base bear (>=20% in 1y):',{p:round(float(EB[(idx>=x)&(idx<=y)].mean()*100),1) for p,(x,y) in {'A':('1990','2012'),'B':('2013','2026')}.items()})
W=R.pivot(index='flag',columns='per',values=['on','flash','bear']).round(2)
print(W.sort_values(('flash','A'),ascending=False).to_string())
I.to_pickle('I2.pkl')
