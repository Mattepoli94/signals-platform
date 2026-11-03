import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
d=pd.concat([pd.read_csv('/home/claude/lead/prices.csv',parse_dates=['date']),pd.read_csv('/home/claude/risk/prices.csv',parse_dates=['date'])]).drop_duplicates(['ticker','date'],keep='last')
C=d.pivot(index='date',columns='ticker',values='close').sort_index(); V=d.pivot(index='date',columns='ticker',values='volume').sort_index()
def load(name):
    if name=='SPY':
        c=C['^GSPC'].dropna(); c=c[c.index>='1955-01-01']
        v=V['SPY'].reindex(c.index); v2=V['^GSPC'].reindex(c.index)
        v=v.where(c.index>='1993-03-01', v2.where(c.index>='1962-01-01'))       # SPY volume from 1993, index volume before
    else:
        c=C['^NDX'].dropna(); c=c[c.index>='1986-01-01']
        v=V['QQQ'].reindex(c.index).where(c.index>='1999-04-01')
    vix=C['^VIX'].reindex(c.index).ffill(limit=3)
    return c,v,vix
def fast_windows(c,fall,n=15,near=0.04,win=40):
    a=c.values; hi=c.rolling(252,min_periods=200).max().values; idx=c.index
    starts=[]; i=0; L=len(a)
    while i<L-n:
        if hi[i]==hi[i] and a[i]/hi[i]-1>=-near and a[i+1:i+1+n].min()/a[i]-1<=-fall:
            starts.append(i); i+=win
        else: i+=1
    return starts
def metrics(c,i,H=252):
    a=c.values; e=a[i]; L=len(a)
    fut=a[i+1:i+1+H]
    if len(fut)<21: return None
    heat=min(0,fut.min()/e-1); jlow=i+1+int(np.argmin(fut)) if fut.min()<e else i
    # true low of the episode: lowest close from 60 sessions before to 252 after
    lo_i=max(0,i-60)+int(np.argmin(a[max(0,i-60):i+1+H])); trough=a[lo_i]
    be=0
    if fut.min()<e:
        after=np.where(a[jlow:]>=e)[0]; be=(jlow+after[0]-i) if len(after) else np.nan
    r=lambda h: a[i+h]/e-1 if i+h<L else np.nan
    return dict(date=c.index[i],entry=e,heat=heat,days_to_low=(jlow-i),above_low=e/trough-1,days_breakeven=be,r1m=r(21),r3m=r(63),r6m=r(126),r12m=r(252))
