import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
from feat import *
from generic import families
d=pd.concat([pd.read_csv('/home/claude/lead/prices.csv',parse_dates=['date']),pd.read_csv('/home/claude/risk/prices.csv',parse_dates=['date'])]).drop_duplicates(['ticker','date'],keep='last')
q=d[d.ticker=='QQQ'].set_index('date').sort_index()
# split/dividend: scale OHLC by adj/close so patterns are consistent
k=q.adj_close/q.close; O,H,Lo,Cl=q.open*k,q.high*k,q.low*k,q.adj_close; Vv=q.volume
idx=Cl.index; a=Cl.values
X=price_feats(Cl,Vv); X=X.join(market_feats(idx)); G=families(X); cnt=G.fillna(0).sum(axis=1)
rng=(H-Lo); atr=pd.concat([H-Lo,(H-Cl.shift()).abs(),(Lo-Cl.shift()).abs()],axis=1).max(axis=1).rolling(14).mean()
low20=Lo.rolling(20).min(); new_low=Lo<=low20.shift(1)
pos=(Cl-Lo)/rng.replace(0,np.nan)                      # close location in day's range
va=Vv.rolling(50).mean()
s20=Cl.rolling(20).mean(); s5=Cl.rolling(5).mean()
dd_=Cl.diff(); up=dd_.clip(lower=0).ewm(alpha=1/14,adjust=False).mean(); dn=(-dd_.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean(); rsi14=100-100/(1+up/dn)
rsi2=X.rsi2
std20=Cl.rolling(20).std(); lbb=s20-2.5*std20
P={}
P['hammer: new 20d low, close in top 35% of a wide range']=new_low&(pos>=0.65)&(rng>=1.3*atr)
P['volume climax reversal: new low, vol>=1.5x, close upper half']=new_low&(Vv>=1.5*va)&(pos>=0.5)
P['key reversal: new low then close above prior high']=new_low&(Cl>H.shift(1))
P['bullish engulfing at 20d low']=(Lo.rolling(3).min()<=low20.shift(1))&(Cl>O)&(O<Cl.shift(1))&(Cl>O.shift(1))&(Cl.shift(1)<O.shift(1))
P['gap-down reversal: open -1%+ below prior close, close up']=(O<=Cl.shift(1)*0.99)&(Cl>Cl.shift(1))
P['exhaustion: 5+ down days then up day']=((Cl<Cl.shift(1)).astype(int).rolling(5).sum().shift(1)>=5)&(Cl>Cl.shift(1))
P['RSI2<5 then close above prior high']=(rsi2.shift(1)<=5)&(Cl>H.shift(1))
P['below 2.5-sigma band then back inside']=(Cl.shift(1)<lbb.shift(1))&(Cl>lbb)
P['RSI14 bullish divergence at new low']=new_low&(rsi14>rsi14.rolling(20).min().shift(5)+3)
P['2.5 ATR below 20d avg then close above 5d avg']=((Cl-s20)/atr).rolling(5).min().shift(1).le(-2.5)&(Cl>s5)
P['swing turn: higher low + close above 3-day high']=(Lo.rolling(3).min()>Lo.rolling(10).min().shift(3))&(Cl>H.rolling(3).max().shift(1))
P['20d high in crash (thrust)']=Cl>=Cl.rolling(20).max().shift(1)
P=pd.DataFrame({k:v.astype(float) for k,v in P.items()})
dd=X.dd; W=[i for i in windows(Cl) if idx[i].year>=2000]
def ent(i,j=None):
    e=a[i] if j is None else 2/(1/a[i]+1/a[j]); f=a[i+1:i+253]
    return dict(fall=min(0,f[:63].min()/e-1),r3m=a[i+63]/e-1 if i+63<len(a) else np.nan,r6m=a[i+126]/e-1 if i+126<len(a) else np.nan)
def evaluate(first_rule,second_rule=None,gate=0.07,second_gate=None):
    rows=[]
    for s in W:
        low=a[s:s+61].min()
        i=next((k for k in range(s,min(s+41,len(a))) if dd.iloc[k]<=-gate and first_rule.iloc[k]==1),None)
        if i is None: rows.append(dict(win=idx[s],hit=False)); continue
        j=None
        if second_rule is not None: j=next((k for k in range(i+1,min(i+41,len(a))) if second_rule.iloc[k]==1 and a[k]<a[i]),None)
        e=a[i] if j is None else 2/(1/a[i]+1/a[j])
        rows.append(dict(win=idx[s],hit=True,above_low=e/low-1,**ent(i,j)))
    D=pd.DataFrame(rows); H_=D[D.hit]; d3=H_[H_.r3m.notna()]
    def sc(D_):
        h=D_[D_.hit]; dd3=h[h.r3m.notna()]
        return (dd3.r3m.mean()+h.fall.median())*100 if len(h) else np.nan
    return dict(signals=f"{len(H_)}/{len(D)}",above_low=H_.above_low.mean()*100,within5=(H_.above_low<=0.05).mean()*100,fall_med=H_.fall.median()*100,fall_worst=H_.fall.min()*100,
                r3m=d3.r3m.mean()*100,r6m=d3.r6m.mean()*100,score=sc(D),e1=sc(D[D.win.dt.year<=2012]),e2=sc(D[D.win.dt.year>=2013]))
