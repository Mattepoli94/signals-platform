import pandas as pd, numpy as np
from ind import P,build
from ep import episodes
ndx=P['^NDX'].dropna(); idx=ndx.index[ndx.index>='1990-01-01']; ndx=ndx.reindex(idx)
I=build(idx)
def fwd_min(c,h): 
    a=c.values; out=np.full(len(a),np.nan)
    for i in range(len(a)-1): out[i]=a[i+1:i+1+h].min()/a[i]-1
    return pd.Series(out,index=c.index)
E63=(fwd_min(ndx,63)<=-0.10).astype(float); E10=(fwd_min(ndx,10)<=-0.07).astype(float)
E63[fwd_min(ndx,63).isna()]=np.nan
# episodes vs rolling 1y high
def ep1y(c,th=-0.15):
    hi=c.rolling(252,min_periods=1).max(); dd=c/hi-1; out=[]; inep=False
    for t in range(len(c)):
        if not inep and dd.iloc[t]<=th:
            inep=True; pk=hi.iloc[:t+1].idxmax() if False else c.iloc[max(0,t-252):t+1].idxmax()
            x10=dd.iloc[:t+1][dd.iloc[:t+1]<=-0.10].index; x10=x10[x10>=pk][0]; out.append((pk,x10))
        if inep and dd.iloc[t]>-0.05: inep=False
    return out
EPS=ep1y(ndx)
def evaluate(I,periods):
    rows=[]
    for k in I.columns:
        for nm,(a,b) in periods.items():
            m=(I.index>=a)&(I.index<=b)&I[k].notna()&E63.notna()
            f=I[k][m]==1; e=E63[m]==1; e10=E10[m]==1
            if m.sum()<500: continue
            base=e.mean(); pf=e[f].mean() if f.sum()>20 else np.nan
            # episode coverage: flag on at any time in the 60 sessions before the -10% alert date (and after peak-120)
            eps=[(p,x) for p,x in EPS if a<=str(x.date())<=b and I[k].loc[:x].notna().iloc[-1]]
            cov=np.mean([ (I[k].loc[I.index[max(0,I.index.get_loc(x)-60)]:x].iloc[:-1]==1).any() for p,x in eps]) if eps else np.nan
            rows.append(dict(flag=k,per=nm,time_on=f.mean()*100,base=base*100,p_when_on=pf*100,lift=pf/base if base>0 else np.nan,
                 flash_lift=(e10[f].mean()/e10.mean()) if f.sum()>20 and e10.mean()>0 else np.nan,
                 fwd63=(ndx.shift(-63)/ndx-1)[m][f].mean()*100 - (ndx.shift(-63)/ndx-1)[m].mean()*100,eps_caught=f'{cov*len(eps):.0f}/{len(eps)}' if eps else '-'))
    return pd.DataFrame(rows)
per={'A 1990-2012':('1990-01-01','2012-12-31'),'B 2013-2026':('2013-01-01','2026-12-31')}
R=evaluate(I,per)
pd.set_option('display.width',250)
W=R.pivot(index='flag',columns='per',values=['time_on','p_when_on','lift','flash_lift','fwd63','eps_caught'])
print('base rate P(NDX falls >=10% within 63d):',{n:round(float(R[R.per==n].base.iloc[0]),1) for n in per})
print('episodes:',[(p.date(),x.date()) for p,x in EPS])
print(W.round(2).sort_values(('lift','A 1990-2012'),ascending=False).to_string())
R.to_csv('ndx_flags.csv'); I.to_pickle('I_ndx.pkl')
