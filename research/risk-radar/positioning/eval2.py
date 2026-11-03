import pandas as pd, numpy as np
G=pd.read_pickle('G.pkl'); N,nearN,E,EV=pd.read_pickle('ev.pkl'); idx=G.index; ii={d:i for i,d in enumerate(idx)}
BL={'06-10':(2006,2010),'11-15':(2011,2015),'16-19':(2016,2019),'20-22':(2020,2022),'23-26':(2023,2026)}
def sc(sig,a,b,lead=20):
    m=(idx.year>=a)&(idx.year<=b)&nearN&sig.notna()&E.notna(); s=sig[m]==1; y=E[m]==1
    if m.sum()<150: return None
    lift=(y[s].mean()/y.mean()) if s.sum()>=15 and y.mean()>0 else np.nan
    ev=[e for e in EV if a<=e.year<=b and pd.notna(sig.loc[e])]
    hit=sum((sig.iloc[max(0,ii[e]-lead):ii[e]+1]==1).any() for e in ev)
    return s.mean()*100,lift,hit,len(ev)
rows=[]
for k in G:
    r={'flag':k}; good=0; nb=0
    for bn,(a,b) in BL.items():
        x=sc(G[k],a,b)
        if x is None: continue
        r[bn]=f'{x[1]:.1f}x {x[2]}/{x[3]}' if not np.isnan(x[1]) else f'-  {x[2]}/{x[3]}'
        if x[3]>0: nb+=1; good+= (x[1]>=1.3) if not np.isnan(x[1]) else 0
    t=sc(G[k],2006,2026); r['ALL']=f'{t[1]:.2f}x on{t[0]:.0f}% {t[2]}/{t[3]}'; r['blocks_ok']=f'{good}/{nb}'; r['_lift']=t[1]
    rows.append(r)
R=pd.DataFrame(rows).set_index('flag').sort_values('_lift',ascending=False).drop(columns='_lift')
pd.set_option('display.width',260); print('events per block',{bn:sum(a<=e.year<=b for e in EV) for bn,(a,b) in BL.items()}); print(R.to_string())
