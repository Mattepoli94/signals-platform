import pandas as pd, numpy as np
from ind import P,C
b=P['BTC-USD'].dropna(); idx=b.index
S=pd.read_pickle('S_ndx.pkl'); sc=S.sum(axis=1).reindex(S.index.union(idx)).ffill().reindex(idx)
vix=C['^VIX'].reindex(C.index.union(idx)).ffill().reindex(idx); dxy=C['DX-Y.NYB'].reindex(C.index.union(idx)).ffill().reindex(idx)
ndx=P['^NDX'].reindex(P.index.union(idx)).ffill().reindex(idx)
a=b.values; fm=np.full(len(a),np.nan)
for i in range(len(a)-30): fm[i]=a[i+1:i+31].min()/a[i]-1
E=pd.Series(fm<=-0.25,index=idx).astype(float); E[np.isnan(fm)]=np.nan
rv=np.log(b).diff().rolling(30).std()
F=pd.DataFrame(index=idx)
F['btc_2x_200d']=b/b.rolling(200).mean()>2
F['btc_1.6x_200d']=b/b.rolling(200).mean()>1.6
F['btc_up_100pct_90d']=b/b.shift(90)>2
F['btc_up_30pct_30d']=b/b.shift(30)>1.3
F['btc_new_high_30d']=b>=b.rolling(365).max()*0.97
F['btc_vol_low_10pctl']=rv<rv.rolling(730,min_periods=365).quantile(0.1)
F['btc_below_200d']=b<b.rolling(200).mean()
F['macro_score>=2']=sc>=2
F['ndx_below_200d']=ndx<ndx.rolling(200).mean()
F['vix_gt_25']=vix>25
F['dollar_up_5pct_6m']=dxy/dxy.shift(126)>1.05
F=F.astype(float)
rows=[]
for k in F:
    for nm,(x,y) in {'2015-2020':('2015-06-01','2020-12-31'),'2021-2026':('2021-01-01','2026-12-31')}.items():
        m=(idx>=x)&(idx<=y)&E.notna()&F[k].notna(); f=F[k][m]==1; e=E[m]==1
        rows.append(dict(flag=k,per=nm,time_on=f.mean()*100,base=e.mean()*100,p_on=e[f].mean()*100 if f.sum()>15 else np.nan,
            lift=(e[f].mean()/e.mean()) if f.sum()>15 else np.nan))
R=pd.DataFrame(rows); print('base P(BTC falls >=25% within 30d)',R.groupby('per').base.first().round(1).to_dict())
print(R.pivot(index='flag',columns='per',values=['time_on','p_on','lift']).round(2).to_string())
