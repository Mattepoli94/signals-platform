import pandas as pd, numpy as np
d=pd.read_csv('prices.csv',parse_dates=['date'])
P=d.pivot(index='date',columns='ticker',values='adj_close').sort_index()
C=d.pivot(index='date',columns='ticker',values='close').sort_index()
spx=C['^GSPC'].dropna(); idx=spx.index[spx.index>='1953-01-01']; spx=spx.reindex(idx)
# Shiller monthly (known with ~1 month lag)
x=pd.read_excel('shiller_ie_data.xls',sheet_name='Data',header=None).iloc[8:]
x=x[pd.to_numeric(x[0],errors='coerce').notna()]
yr=pd.to_numeric(x[0]); mo=((yr*100).round()%100).astype(int); y=yr.astype(int)
sh=pd.DataFrame({'cpi':pd.to_numeric(x[4],errors='coerce').values,'gs10':pd.to_numeric(x[6],errors='coerce').values,
   'cape':pd.to_numeric(x[12],errors='coerce').values,'E':pd.to_numeric(x[3],errors='coerce').values},
   index=pd.to_datetime(dict(year=y.values,month=mo.values,day=1)))
sh.index=sh.index+pd.offsets.MonthEnd(1)+pd.Timedelta(days=20)   # available ~3 weeks after month end
mg=pd.read_excel('finra_margin.xlsx').iloc[:,:2]; mg.columns=['ym','debt']
mg.index=pd.to_datetime(mg.ym)+pd.offsets.MonthEnd(1)+pd.Timedelta(days=20); mg=mg['debt'].astype(float).sort_index()
def on(s): s=s.dropna(); return s.reindex(s.index.union(idx)).ffill().reindex(idx)
def peaks(c,th=-0.19):
    a=c.values; ix=c.index; hi=c.rolling(252,min_periods=1).max(); out=[]; inep=False
    for t in range(len(a)):
        if not inep and a[t]/hi.iloc[t]-1<=th:
            inep=True; w=c.iloc[max(0,t-252):t+1]; pk=w.idxmax(); out.append(pk)
        if inep and a[t]/hi.iloc[t]-1>-0.05: inep=False
    return sorted(set(out))
PK=peaks(spx)
a=spx.values
def fmin(h):
    o=np.full(len(a),np.nan)
    for i in range(len(a)-h): o[i]=a[i+1:i+1+h].min()/a[i]-1
    return pd.Series(o,index=idx)
near=spx/spx.rolling(252,min_periods=200).max()-1>=-0.05
# BULL_END label: a bear peak within next 252 sessions (t<=peak)
pos=pd.Series(0.0,index=idx); ii={d:i for i,d in enumerate(idx)}
for p in PK:
    j=ii[p]; pos.iloc[max(0,j-252):j+1]=1
pos.iloc[-252:]=np.where(pos.iloc[-252:]==1,1,np.nan)   # unknown future
BULL=pos
FAST=(fmin(21)<=-0.10).astype(float); FAST[fmin(21).isna()]=np.nan
# fast crash events: first day of each cluster
fc=FAST.fillna(0)
nf=(fc==1)&near
CR=[idx[i] for i in range(len(idx)) if nf.iloc[i] and (i<21 or nf.iloc[i-21:i].sum()==0)]
if __name__=='__main__':
    print('bear peaks:',[p.date() for p in PK])
    print('fast crashes from near highs (start of 21d window):',[c.date() for c in CR])
    print('near-high share',round(near.mean(),2),' BULL base on near days',round(BULL[near].mean(),3),' FAST base',round(FAST[near].mean(),3))
