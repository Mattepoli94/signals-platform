import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
from feat import *
def build(name):
    if name=='QQQ':
        c=C['^NDX'].dropna(); c=c[c.index>='2004-01-01']; v=on(V['QQQ'],c.index)
    else:
        s=pd.read_csv('soxx_prices.csv',parse_dates=['date']); s=s[s.ticker=='SOXX'].set_index('date').sort_index()
        c=s['close'].astype(float); c=c[c.index>='2004-01-01']; v=s['volume'].reindex(c.index).astype(float)
    X=price_feats(c,v).join(market_feats(c.index)); return c,X
def families(X,mem=10):
    m=lambda s: s.rolling(mem,min_periods=1).max()
    f=lambda cond,src: cond.astype(float).where(src.notna())
    G=pd.DataFrame(index=X.index)
    G['stretch']=m(pd.concat([f(X.dd_z<=-2.5,X.dd_z),f(X.z15<=-2.5,X.z15)],axis=1).max(axis=1))
    G['capitulation']=m(f(X.capit3==1,X.capit3))
    G['options_fear']=m(pd.concat([f(X.pct_pct>=0.9,X.pct_pct),f(X.pce_pct>=0.9,X.pce_pct)],axis=1).max(axis=1))
    G['vol_panic']=m(pd.concat([f(X.vxn_pct>=0.9,X.vxn_pct),f(X.vix9_ratio>=1.05,X.vix9_ratio)],axis=1).max(axis=1))
    G['positioning']=m(pd.concat([f(X.gex<0,X.gex),f(X.am_ndx_pct<=0.2,X.am_ndx_pct),f(X.lev_ndx_pct<=0.2,X.lev_ndx_pct)],axis=1).max(axis=1))
    G['oversold']=m(pd.concat([f(X.rsi14<=30,X.rsi14),f(X.rsi2<=5,X.rsi2)],axis=1).max(axis=1))
    return G
def run(c,X,scale=1.0,depth=0.108,second='families',start_year=2007):
    a=c.values; idx=c.index; W=[i for i in windows(c,fall=0.08*scale) if idx[i].year>=start_year]
    G=families(X); cnt=G.fillna(0).sum(axis=1); imp=(X.vxn/100)*np.sqrt(21/252)*scale
    rows=[]
    for s in W:
        low=a[s:s+61].min(); i=next((k for k in range(s,min(s+41,len(a))) if X.dd.iloc[k]<=-depth*scale),None)
        if i is None: rows.append(dict(win=idx[s],date=None)); continue
        j=None
        if second=='families': j=next((k for k in range(i+1,min(i+41,len(a))) if cnt.iloc[k]>=3 and a[k]<a[i]),None)
        e=a[i] if j is None else 2/(1/a[i]+1/a[j]); f=a[i+1:i+253]
        below=np.where(f<e)[0]
        rows.append(dict(win=idx[s],date=idx[i],date2=idx[j] if j is not None else None,entry_vs_low=e/low-1,fall=min(0,f[:63].min()/e-1) if len(f) else np.nan,
                         r1m=a[i+21]/e-1 if i+21<len(a) else np.nan,r3m=a[i+63]/e-1 if i+63<len(a) else np.nan,r6m=a[i+126]/e-1 if i+126<len(a) else np.nan,
                         under=len(below) if len(f)>=126 else np.nan,back=((below[-1]+1) if len(below) else 0) if len(f)>=126 else np.nan))
    return pd.DataFrame(rows)
def summ(D):
    H=D.dropna(subset=['date']); d=H[H.r3m.notna()]
    return {'Crash windows':len(D),'Signals':len(H),'Entry vs final low (avg)':f"{H.entry_vs_low.mean()*100:+.1f}%",'Within 5% of low':f"{(H.entry_vs_low<=0.05).mean()*100:.0f}%",
            'Further fall in 3 months (median / worst)':f"{H.fall.median()*100:.1f}% / {H.fall.min()*100:.0f}%",'Days below entry, next 12m (median)':f"{d.under.median():.0f}",
            'Back above entry for good (median days)':f"{d.back.median():.0f}",'Return 1m / 3m / 6m':f"{H.r1m.mean()*100:+.1f}% / {d.r3m.mean()*100:+.1f}% / {d.r6m.mean()*100:+.1f}%",'Up after 3 months':f"{(d.r3m>0).mean()*100:.0f}%"}
