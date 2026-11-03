import pandas as pd, numpy as np, json, zipfile, glob
d=pd.concat([pd.read_csv('/home/claude/lead/prices.csv',parse_dates=['date']),pd.read_csv('/home/claude/risk/prices.csv',parse_dates=['date'])]).drop_duplicates(['ticker','date'],keep='last')
P=d.pivot(index='date',columns='ticker',values='adj_close').sort_index(); C=d.pivot(index='date',columns='ticker',values='close').sort_index(); V=d.pivot(index='date',columns='ticker',values='volume').sort_index()
def on(s,idx,lag=None,stale=None):
    s=s.dropna().sort_index()
    if lag is not None: s.index=s.index+lag
    s=s[~s.index.duplicated(keep='last')]; o=s.reindex(s.index.union(idx)).ffill().reindex(idx)
    if stale and len(s): o[o.index>s.index.max()+pd.Timedelta(days=stale)]=np.nan
    return o
def tpct(s,n=504,mp=250): return s.rolling(n,min_periods=mp).apply(lambda w:(w[:-1]<w[-1]).mean(),raw=True)
def rsi(c,n=14):
    dd=c.diff(); up=dd.clip(lower=0).ewm(alpha=1/n,adjust=False).mean(); dn=(-dd.clip(upper=0)).ewm(alpha=1/n,adjust=False).mean(); return 100-100/(1+up/dn)
def fwd(c,h):
    a=c.values; r=np.full(len(a),np.nan); m=np.full(len(a),np.nan)
    for i in range(len(a)-h): r[i]=a[i+h]/a[i]-1; m[i]=a[i+1:i+1+h].min()/a[i]-1
    return pd.Series(r,index=c.index),pd.Series(m,index=c.index)
def price_signs(c,vol=None,pre=''):
    S=pd.DataFrame(index=c.index); f=lambda k,x,v: S.__setitem__(pre+k,x.astype(float).where(v))
    r=rsi(c); s50=c.rolling(50).mean(); s200=c.rolling(200).mean(); s20=c.rolling(20).mean()
    hi=c.rolling(252,min_periods=200).max(); dd=c/hi-1
    f('rsi_lt_30',r<30,r.notna()); f('rsi_lt_25',r<25,r.notna())
    f('20pct_below_200d',c/s200<0.80,s200.notna()); f('drawdown_ge_30',dd<=-0.30,hi.notna())
    if vol is not None:
        va=vol.rolling(50).mean(); f('capitulation_volume',(vol>2*va)&(c.pct_change()<-0.03),va.notna()&(vol>0))
    below=(c<s50).astype(int).rolling(20).sum()
    f('reclaim_50d',(c>s50)&(c.shift(1)<=s50.shift(1))&(below.shift(1)>=15),s50.notna())
    f('20d_high_in_drawdown',(c>=c.rolling(20).max())&(dd<=-0.10),hi.notna())
    f('thrust_7pct_10d',c/c.shift(10)>1.07,c.shift(10).notna())
    low25=c.rolling(25).min(); daysfromlow=(c.rolling(25).apply(lambda w:len(w)-1-np.argmin(w),raw=True))
    if vol is not None:
        ftd=(daysfromlow>=4)&(daysfromlow<=10)&(c.pct_change()>0.015)&(vol>vol.shift(1))
        f('follow_through_day',ftd,daysfromlow.notna()&(vol>0))
    hl=(c.rolling(10).min()>c.shift(10).rolling(20).min())&(c>s20)&(dd<=-0.10)
    f('higher_low_above_20d',hl,hi.notna())
    f('back_above_200d',(c>s200)&(c.shift(1)<=s200.shift(1)),s200.notna())
    return S
