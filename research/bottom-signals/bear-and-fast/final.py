import sys; sys.argv=['x']
exec(open('fast2.py').read().split("rows=[]")[0])
exec(open('bear.py').read().split("rows=[]")[0].replace("ERAS={'old':(1955,2009),'new':(2010,2026)}","ERAS2={'old':(1955,2009),'new':(2010,2026)}").replace("data={n:load(n) for n in ('SPY','QQQ')}",""))
SYS={
 'F-depth  (fast crash: buy at -8% SPY / -11% QQQ)':lambda n:[h for s,h in gen(n,trig='depth',depth=0.08,ctx=False)],
 'F-fear   (fast crash: VIX>=30 or capitulation volume)':lambda n:[h for s,h in fast_signals(data[n][0],data[n][1],data[n][2],cfg[n][0],V=30,k=2.0,dn=0.03,depth=0.05*cfg[n][1])],
 'F-depth+fear (both)':lambda n:[h for s,h in gen(n,trig='vix',V=30,depth=0.08,ctx=False)],
 'B-washout (bear: -30% / 20% under 200d / VIX>=35)':lambda n:bear_sig(n,'washout',W=0.30,M=0.20,VB=35),
 'B-thrust after washout (+5% in 15 days)':lambda n:bear_sig(n,'thrust_after_washout',T=0.05,N=15,W=0.30,M=0.20,VB=35),
}
allD={}
for nm,fn in SYS.items():
    for n in ('SPY','QQQ'):
        c=data[n][0]; idxs=[i for i in fn(n) if i is not None]
        rows=[m for m in (metrics(c,i) for i in idxs) if m]
        D=pd.DataFrame(rows); D['sys']=nm; D['idx']=n; allD[(nm,n)]=D
A=pd.concat(allD.values()); A.to_pickle('final_signals.pkl')
def summ(D):
    return pd.Series({'signals':len(D),'further drop (median)':f"{D.heat.median()*100:.1f}%",'further drop (worst)':f"{D.heat.min()*100:.0f}%",
        'within 5% of low':f"{(D.heat>=-0.05).mean()*100:.0f}%",'days to low (median)':f"{D.days_to_low.median():.0f}",
        'days to break-even (median)':f"{D.days_breakeven.median():.0f}",'days to break-even (worst)':f"{D.days_breakeven.max():.0f}" if D.days_breakeven.notna().all() else 'not yet / >1y',
        '3m return':f"{D.r3m.mean()*100:+.1f}%",'6m return':f"{D.r6m.mean()*100:+.1f}%",'12m return':f"{D.r12m.mean()*100:+.1f}%",'6m win rate':f"{(D.r6m>0).mean()*100:.0f}%"})
for nm in SYS:
    for n in ('SPY','QQQ'):
        D=allD[(nm,n)]
        if D.empty: continue
        T=pd.DataFrame({'all':summ(D),'before 2010':summ(D[D.date.dt.year<2010]) if (D.date.dt.year<2010).any() else None,'2010-2026':summ(D[D.date.dt.year>=2010]) if (D.date.dt.year>=2010).any() else None})
        print(f'\n=== {nm} · {n} (from {D.date.min().year})'); print(T.to_string())
