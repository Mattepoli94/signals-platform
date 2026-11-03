import sys; sys.path.insert(0,'/home/claude/signals-platform')
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
from signals import bottoms as B
from signals.radar import _price, _read, _on
from signals.strategies import get
from signals.strategies.qqq_regime import regime_core
X,L,ovr,cnt,plans=B.fast_crash_plan()
qa=_price('QQQ','adj_close').dropna(); qc=_price('QQQ','close').reindex(qa.index)
idx=qa.index
vix=_on(_read('cboe_VIX','close'),idx,stale_days=10)
ws,_,_,_=B.washout_signals(qc,vix,1.35)
WS=[idx[i] for i in ws]
s=get('qqq_regime'); t=regime_core(qa,s.params)
w0=t['w_core'].astype(float).reindex(idx).fillna(0)
irx=_price('IRX','close').reindex(idx).ffill()/100; cash=(1+irx)**(1/252)-1
r=qa.pct_change().fillna(0)
def backtest(w,fee=0.0005):
    ret=w.shift(1).fillna(0)*r+(1-w.shift(1).fillna(0))*cash-fee*w.diff().abs().fillna(0)
    return ret
def stats(ret,a,b):
    x=ret[a:b]; eq=(1+x).cumprod(); y=len(x)/252; c=eq.iloc[-1]**(1/y)-1; dd=(eq/eq.cummax()-1).min()
    return f'{c*100:.1f}% / {dd*100:.1f}% ({c/-dd:.2f})'
def overlay(H1=63,H2=63,HW=126,f1=0.5,f2=1.0,fw=1.0,use_fast=True,use_wash=True,fast_override=True):
    fl=pd.Series(0.0,index=idx)
    pos=lambda d: idx.get_loc(d)
    if use_fast:
        for p in plans:
            if p['buy1'] is None or (fast_override and p['skipped']): continue
            i=pos(p['buy1']); fl.iloc[i:i+H1]=np.maximum(fl.iloc[i:i+H1],f1)
            if p['buy2'] is not None:
                j=pos(p['buy2']); fl.iloc[j:j+H2]=np.maximum(fl.iloc[j:j+H2],f2)
    if use_wash:
        for d in WS:
            i=pos(d); fl.iloc[i:i+HW]=np.maximum(fl.iloc[i:i+HW],fw)
    return np.maximum(w0,fl)
P={'1999-2026':('1999-06-01','2026-12-31'),'2007-15':('2007-01-01','2015-12-31'),'2016-26':('2016-01-01','2026-12-31')}
rows=[]
def add(name,w):
    ret=backtest(w); rows.append({'variant':name,**{k:stats(ret,*v) for k,v in P.items()},'time invested':f"{w['2007':].mean()*100:.0f}%"})
add('Current QQQ system',w0)
for H in (21,63,126):
    add(f'+ fast-crash buys (50% then 100%), hold {H} sessions',overlay(H,H,126,use_wash=False))
add('+ fast-crash buys 100% at buy 1, hold 63',overlay(63,63,126,f1=1.0,use_wash=False))
add('+ fast-crash buys, no override, hold 63',overlay(63,63,126,use_wash=False,fast_override=False))
for H in (63,126,252): add(f'+ washout 100%, hold {H}',overlay(use_fast=False,HW=H))
add('+ both (fast hold 63, washout hold 126)',overlay(63,63,126))
add('+ both (fast hold 126, washout hold 252)',overlay(126,126,252))
add('QQQ buy & hold',pd.Series(1.0,index=idx))
pd.set_option('display.width',250); print('CAGR / max drawdown (Calmar), 5 bp costs, idle cash at T-bill'); print(pd.DataFrame(rows).to_string(index=False))
print('washouts',[d.date() for d in WS if d.year>=1999])
