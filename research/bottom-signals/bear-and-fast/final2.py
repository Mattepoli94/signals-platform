import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
from eng import load
A=pd.read_pickle('final_signals.pkl')
data={n:load(n)[0] for n in ('SPY','QQQ')}
def extra(r):
    c=data[r.idx]; i=c.index.get_loc(r.date); f=c.values[i+1:i+253]; e=c.values[i]
    below=np.where(f<e)[0]
    return pd.Series({'days_underwater':len(below),'last_below':(below[-1]+1) if len(below) else 0,'heat3m':min(0,f[:63].min()/e-1) if len(f)>=21 else np.nan})
A=pd.concat([A,A.apply(extra,axis=1)],axis=1)
names={'F-depth  (fast crash: buy at -8% SPY / -11% QQQ)':'Fast crash: depth','F-depth+fear (both)':'Fast crash: depth + VIX>=30','B-washout (bear: -30% / 20% under 200d / VIX>=35)':'Bear: washout',
       'F-fear   (fast crash: VIX>=30 or capitulation volume)':'Fast crash: fear/capitulation (research version)','B-thrust after washout (+5% in 15 days)':'Bear: thrust after washout'}
A['sysn']=A.sys.map(names)
def summ(D):
    return {'Signals':len(D),'Price fell further after the signal (median / worst)':f"{D.heat.median()*100:.1f}% / {D.heat.min()*100:.0f}%",
            'Signals within 5% of the final low':f"{(D.heat>=-0.05).mean()*100:.0f}%",
            'Days spent below the entry price, next year (median)':f"{D.days_underwater.median():.0f}",
            'Back above entry for good after (median days)':f"{D.last_below.median():.0f}",
            'Return after 3 / 6 / 12 months (avg)':f"{D.r3m.mean()*100:+.0f}% / {D.r6m.mean()*100:+.0f}% / {D.r12m.mean()*100:+.0f}%",
            'Up after 6 months':f"{(D.r6m.dropna()>0).mean()*100:.0f}%"}
out=[]
for s in names.values():
    for n in ('QQQ','SPY'):
        D=A[(A.sysn==s)&(A.idx==n)]
        for era,m in [('2010–2026',D.date.dt.year>=2010),('before 2010',D.date.dt.year<2010)]:
            if m.sum(): out.append({'System':s,'Index':n,'Era':era,**summ(D[m])})
T=pd.DataFrame(out); pd.set_option('display.width',300); pd.set_option('display.max_colwidth',40)
print(T.to_string(index=False)); T.to_csv('summary.csv',index=False); A.to_pickle('final_signals2.pkl')
