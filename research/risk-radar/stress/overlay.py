import sys; sys.path.insert(0,'/home/claude/signals-platform')
import pandas as pd, numpy as np, yaml
from signals import data as D
from signals.strategies import get
from signals.expect import backtest_returns
from ind import P,C
pots=yaml.safe_load(open('/home/claude/signals-platform/config/portfolio.yaml'))['pots']
S=pd.read_pickle('S_ndx.pkl'); score=S.sum(axis=1)
sq,sb=get('qqq_regime'),get('btc_trend')
data=D.load_all(sorted(set(sq.inputs)|set(sb.inputs)|{'GBPUSD','IRX'}))
irx=data['IRX']['close']
def sysret(s,pc,start):
    t=s.compute(data); r,_=backtest_returns(s,t,data,dict(pc,cash_rate_pct=0))
    w=sum(t[f'w_{a}'].astype(float) for a in s.assets if a!='USD')
    r=r[start:]; w=w[start:]
    rate=irx.reindex(irx.index.union(r.index)).ffill().reindex(r.index).fillna(0)/100
    days=pd.Series(r.index,index=r.index).diff().dt.days.fillna(1); cash=(1+rate)**(days/365)-1
    return r,w,cash
def st(r):
    eq=(1+r).cumprod(); y=(r.index[-1]-r.index[0]).days/365.25; dd=(eq/eq.cummax()-1).min(); c=eq.iloc[-1]**(1/y)-1; return round(c*100,1),round(dd*100,1),round(c/-dd,2)
for name,s,pc,start,fee in [('QQQ system',sq,pots['qqq_trading'],'2010-01-01',0.0005),('BTC system',sb,pots['btc_trend'],'2015-06-01',0.004)]:
    r,w,cash=sysret(s,pc,start)
    # flag known at prior US close -> applies from next session's close-to-close return (lag 1 on system calendar)
    f=score.reindex(score.index.union(r.index)).ffill().reindex(r.index).shift(1).fillna(0)
    base=r+ (1-w.shift(1).fillna(0)).clip(lower=0)*cash
    print(f'\n{name} {start}+  base',st(base))
    for k in (1,2,3):
        for cut in (0.5,1.0):
            on=(f>=k).astype(float)*cut
            ww=w.shift(1).fillna(0)
            newr=base - on*ww*(r/ww.replace(0,np.nan)).fillna(0) + on*ww*cash
            newr-= fee*(on*ww).diff().abs().fillna(0)
            print(f'  score>={k} cut {int(cut*100)}%: time on {(f>=k).mean()*100:4.1f}%  ',st(newr), ' since 2018',st(newr['2018':]),'(base',st(base['2018':]),')')
