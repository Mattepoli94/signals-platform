import sys; sys.path.insert(0,'/home/claude/signals-platform')
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
from signals import bottoms as B
from signals.radar import _read, _on, late_cycle
s=pd.read_csv('soxx_prices.csv',parse_dates=['date']); s=s[s.ticker=='SOXX'].set_index('date').sort_index()
q=pd.read_csv('/home/claude/signals-platform/data/prices/QQQ.csv',parse_dates=['date']).set_index('date')
c=s['adj_close'].astype(float); v=s['volume'].astype(float); idx=c.index; a=c.values
r=np.log(c).diff(); rq=np.log(q.adj_close).diff()
scale=float(r['2007':].std()/rq['2007':].std()); print('SOXX/QQQ daily vol ratio since 2007: %.2f'%scale)
# features (SOXX own price/volume + market-wide options)
sig=r.rolling(252,min_periods=120).std(); hi=c.rolling(252,min_periods=200).max(); dd=c/hi-1
z15=np.log(c/c.shift(15))/(sig*np.sqrt(15)); ddz=np.log(c/hi)/(sig*np.sqrt(20))
va=v.rolling(50).mean(); volx=v/va; ret=c.pct_change(); capit=((volx>=1.8)&(ret<=-0.02*scale)).astype(float).rolling(3,min_periods=1).max().where(va.notna())
rsi14,rsi2=B._rsi(c,14),B._rsi(c,2)
vix,vxn,vix9=(_on(_read(f'cboe_{k}','close'),idx,stale_days=10) for k in ('VIX','VXN','VIX9D'))
pc=_read('putcall_total'); pct=B._tp(_on(pc.total_pc,idx,stale_days=10).rolling(5).mean()); pce=B._tp(_on(pc.equity_pc,idx,stale_days=10).rolling(5).mean())
gex=_on(_read('squeeze')['gex'],idx,stale_days=10)
f=lambda cond,src: cond.astype(float).where(src.notna()).fillna(0); m10=lambda x: x.rolling(10,min_periods=1).max(); any_=lambda *x: pd.concat(x,axis=1).max(axis=1)
G=pd.DataFrame({'stretch':m10(any_(f(ddz<=-2.5,ddz),f(z15<=-2.5,z15))),'capitulation':m10(f(capit==1,capit)),
   'options_fear':m10(any_(f(pct>=0.9,pct),f(pce>=0.9,pce))),'vol_panic':m10(any_(f(B._tp(vxn)>=0.9,vxn),f(vix9/vix>=1.05,vix9))),
   'dealer_gamma':m10(f(gex<0,gex)),'oversold':m10(any_(f(rsi14<=30,rsi14),f(rsi2<=5,rsi2)))})
cnt=G.sum(axis=1)
L=late_cycle(); L=L.reindex(L.index.union(idx)).ffill().reindex(idx); ovr=(L.pressure==1)|(L.score>=3)
def plan(fall,depth,use_ovr=True,two=True,y0=2007):
    rows=[]
    for st in B._windows(c,fall=fall):
        if idx[st].year<y0: continue
        low=a[st:st+61].min()
        i=next((k for k in range(st,min(st+41,len(a))) if dd.iloc[k]<=-depth),None)
        if i is None: rows.append(dict(start=idx[st],hit=False,skip=False,depth_low=low/hi.iloc[st:st+61].max()-1)); continue
        if use_ovr and ovr.iloc[i]: rows.append(dict(start=idx[st],hit=False,skip=True,d1=idx[i],depth_low=low/hi.iloc[st:st+61].max()-1)); continue
        j=next((k for k in range(i+1,min(i+41,len(a))) if cnt.iloc[k]>=3 and a[k]<a[i]),None) if two else None
        e=a[i] if j is None else 2/(1/a[i]+1/a[j]); fut=a[i+1:i+253]; below=np.where(fut<e)[0]
        rows.append(dict(start=idx[st],hit=True,skip=False,d1=idx[i],d2=idx[j] if j is not None else None,depth_low=low/hi.iloc[st:st+61].max()-1,above_low=e/low-1,
            fall=min(0,fut[:63].min()/e-1),r1m=a[i+21]/e-1 if i+21<len(a) else np.nan,r3m=a[i+63]/e-1 if i+63<len(a) else np.nan,r6m=a[i+126]/e-1 if i+126<len(a) else np.nan,
            under=len(below) if len(fut)>=126 else np.nan,back=((below[-1]+1) if len(below) else 0) if len(fut)>=126 else np.nan))
    return pd.DataFrame(rows)
def S(D):
    H=D[D.hit]; d=H[H.r3m.notna()]
    if not len(H): return {}
    return {'crashes':len(D),'buys':len(H),'skipped':int(D.skip.sum()),'2nd buy':int(H.d2.notna().sum()),'entry vs low':f"{H.above_low.mean()*100:+.1f}%",'within 5% of low':f"{(H.above_low<=0.05).mean()*100:.0f}%",
            'further fall med/worst':f"{H.fall.median()*100:.1f}% / {H.fall.min()*100:.0f}%",'days below (med)':f"{d.under.median():.0f}",'back above (med)':f"{d.back.median():.0f}",
            '1m/3m/6m':f"{H.r1m.mean()*100:+.1f} / {d.r3m.mean()*100:+.1f} / {d.r6m.mean()*100:+.1f}",'up 3m':f"{(d.r3m>0).mean()*100:.0f}%",'score':round((d.r3m.mean()+H.fall.median())*100,1)}
fall0=0.08*scale; out={}
base=plan(fall0,0.108*scale)
print('SOXX fast crash = -%.1f%% in 15 sessions; crash lows: median %.1f%%, middle half %.1f%% to %.1f%%'%(fall0*100,base.depth_low.median()*100,base.depth_low.quantile(.75)*100,base.depth_low.quantile(.25)*100))
for dep in (0.12,0.15,0.18,0.20,0.25):
    for two in (False,True):
        D=plan(fall0,dep,True,two)
        for era,m in [('2007-26',D.start.dt.year>=2007),('2007-15',D.start.dt.year<=2015),('2016-26',D.start.dt.year>=2016)]:
            out[(f'depth -{dep*100:.0f}%','two buys' if two else 'one buy',era)]=S(D[m])
pd.set_option('display.width',320); print(pd.DataFrame(out).T.to_string())
D=plan(fall0,0.15,True,True); D.to_pickle('soxx_plan.pkl')
print(D[['start','d1','d2','skip','depth_low','above_low','fall','r3m','r6m']].round(3).to_string(index=False))
print('today: SOXX %.1f%% below 1y high; groups on:'%(dd.iloc[-1]*100),G.iloc[-1][G.iloc[-1]==1].index.tolist(),'; active crash windows:',[idx[st].date() for st in B._windows(c,fall=fall0) if st>=len(a)-41])
