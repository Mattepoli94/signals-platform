from sig import *
import itertools
ERAS={'old':(1955,2009),'new':(2010,2026)}
data={n:load(n) for n in ('SPY','QQQ')}
SC={'SPY':1.0,'QQQ':1.35}
def bear_sig(n,kind,T=0.07,N=10,W=0.30,M=0.20,VB=40,state=0.15,cool=126):
    c,v,vix=data[n]; s=SC[n]
    return bear_signals(c,vix,state*s,kind,T*s,N,W*s,M*s,VB,cool)
def ev(n,sigs,era):
    c=data[n][0]; s,D=summarize(c,sigs,era); return s,D
rows=[]
for kind in ['naive','washout','thrust','thrust_after_washout']:
    grid=[{}]
    if kind=='naive': grid=[dict(W=w) for w in (0.20,0.25,0.30,0.35)]
    if kind=='washout': grid=[dict(W=w,M=m,VB=vb) for w in (0.25,0.30) for m in (0.15,0.20) for vb in (35,40,45)]
    if kind in ('thrust','thrust_after_washout'): grid=[dict(T=t,N=nn) for t in (0.05,0.06,0.07,0.08,0.10) for nn in (5,10,15)]
    for g in grid:
        rec={'kind':kind,**g}; sc=[]
        for n in data:
            for en,er in ERAS.items():
                s,D=ev(n,bear_sig(n,kind,**g),er)
                if s is None: rec[f'{n}_{en}']='-'; sc.append(-99); continue
                val=s['r6m']+s['heat_med']; rec[f'{n}_{en}']=f"{val*100:+.1f} r6{s['r6m']*100:+.0f} h{s['heat_med']*100:.0f} n{s['n']}"; sc.append(val)
        rec['min']=round(min(sc)*100,1); rec['mean']=round(np.mean([x for x in sc if x>-90])*100,1); rows.append(rec)
R=pd.DataFrame(rows); pd.set_option('display.width',300)
for k in R.kind.unique(): print(R[R.kind==k].sort_values('min',ascending=False).head(6).to_string(index=False)); print()
