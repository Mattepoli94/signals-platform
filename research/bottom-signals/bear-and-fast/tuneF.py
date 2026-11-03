from sig import *
import itertools
ERAS={'old':(1955,2009),'new':(2010,2026)}
cfg={'SPY':0.06,'QQQ':0.08}
data={n:load(n) for n in cfg}
rows=[]
for V_,k,dn,conf in itertools.product([25,28,30,35,40],[1.5,2.0,2.5,3.0],[0.02,0.03,0.04],['none','upday','3d_high']):
    rec={'V':V_,'k':k,'dn':dn,'confirm':conf}; vals=[]
    for n,f in cfg.items():
        c,v,vix=data[n]; sg=fast_signals(c,v,vix,f,V_,k,dn,conf)
        for en,er in ERAS.items():
            win=[s for s,h in sg if er[0]<=c.index[s].year<=er[1]]
            s,_=summarize(c,[h for s_,h in sg if er[0]<=c.index[s_].year<=er[1]],er)
            if s is None: vals.append(-99); continue
            cov=s['n']/max(len(win),1)
            score=s['r3m']+s['heat_med']        # 3-month return net of median pain
            rec[f'{n}_{en}']=round(score*100,1); rec[f'{n}_{en}_cov']=round(cov*100); vals.append(score if cov>=0.6 else -99)
    rec['minscore']=round(min(vals)*100,1); rows.append(rec)
R=pd.DataFrame(rows).sort_values('minscore',ascending=False); pd.set_option('display.width',250)
print(R.head(15).to_string(index=False)); R.to_csv('tuneF.csv',index=False)
# naive benchmark: buy at first -X% in the window
for X in (0.08,0.10):
    for n,f in cfg.items():
        c,v,vix=data[n]; sg=fast_signals(c,v,vix,f,naive=X)
        for en,er in ERAS.items():
            s,_=summarize(c,[h for s_,h in sg if er[0]<=c.index[s_].year<=er[1]],er)
            if s: print(f'naive -{X:.0%} {n} {en}: n {s["n"]} r3m {s["r3m"]*100:.1f} heat_med {s["heat_med"]*100:.1f} score {(s["r3m"]+s["heat_med"])*100:.1f}')
