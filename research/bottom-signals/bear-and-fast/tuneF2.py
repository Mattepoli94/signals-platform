from sig import *
import itertools
ERAS={'old':(1990,2009),'new':(2010,2026)}
cfg={'SPY':(0.06,1.0),'QQQ':(0.08,1.35)}     # crash definition; depth scale for QQQ (more volatile)
data={n:load(n) for n in cfg}
def evalcfg(**kw):
    out={}
    for n,(f,sc) in cfg.items():
        c,v,vix=data[n]; kk=dict(kw); 
        if 'depth' in kk: kk['depth']=kk['depth']*sc
        if 'naive' in kk: kk['naive']=kk['naive']*sc
        sg=fast_signals(c,v,vix,f,**kk)
        for en,er in ERAS.items():
            wins=[s for s,h in sg if er[0]<=c.index[s].year<=er[1]]
            s,_=summarize(c,[h for s_,h in sg if er[0]<=c.index[s_].year<=er[1]],er)
            out[(n,en)]=(s,len(wins))
    return out
rows=[]
grid=list(itertools.product([25,30,35,40],[2.0,2.5],[0.03],['none','upday','3d_high'],[0.05,0.08,0.10,0.12],[(True,True),(True,False),(False,True)]))
for V_,k,dn,conf,dep,(uv,uo) in grid:
    o=evalcfg(V=V_,k=k,dn=dn,confirm=conf,depth=dep,use_vix=uv,use_vol=uo); rec=dict(V=V_ if uv else '-',k=k if uo else '-',confirm=conf,depth=dep); sc=[]
    for key,(s,nw) in o.items():
        if s is None: sc.append(-99); continue
        cov=s['n']/max(nw,1); val=s['r3m']+s['heat_med']; rec['_'.join(key)]=f"{val*100:+.1f} ({cov*100:.0f}%)"; sc.append(val if cov>=0.5 else -99)
    rec['min']=round(min(sc)*100,1); rec['mean']=round(np.mean([x for x in sc if x>-90])*100,1) if any(x>-90 for x in sc) else None; rows.append(rec)
R=pd.DataFrame(rows).drop_duplicates(subset=['V','k','confirm','depth']).sort_values('min',ascending=False); pd.set_option('display.width',260)
print(R.head(20).to_string(index=False)); R.to_csv('tuneF2.csv',index=False)
print('\nnaive benchmarks (buy at first -X% from high in the crash window; QQQ X scaled x1.35):')
for X in (0.08,0.10,0.12):
    o=evalcfg(naive=X); print(X,{f'{k[0]}_{k[1]}':f"{(s['r3m']+s['heat_med'])*100:+.1f} ({s['n']}/{nw})" for k,(s,nw) in o.items() if s})
