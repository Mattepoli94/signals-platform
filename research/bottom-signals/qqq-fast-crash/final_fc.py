import sys; sys.path.insert(0,'/home/claude/signals-platform')
exec(open('pa.py').read())
from signals import radar as RD
Lt=RD.late_cycle(); Lr=Lt.reindex(Lt.index.union(idx)).ffill().reindex(idx)
f=lambda cond,src: cond.astype(float).where(src.notna()).fillna(0)
m10=lambda s: s.rolling(10,min_periods=1).max()
grp=pd.DataFrame({'stretch':m10(pd.concat([f(X.dd_z<=-2.5,X.dd_z),f(X.z15<=-2.5,X.z15)],axis=1).max(axis=1)),
   'capitulation':m10(f(X.capit3==1,X.capit3)),'options_fear':m10(pd.concat([f(X.pct_pct>=0.9,X.pct_pct),f(X.pce_pct>=0.9,X.pce_pct)],axis=1).max(axis=1)),
   'vol_panic':m10(pd.concat([f(X.vxn_pct>=0.9,X.vxn_pct),f(X.vix9_ratio>=1.05,X.vix9_ratio)],axis=1).max(axis=1)),
   'dealer_gamma':m10(f(X.gex<0,X.gex)),'oversold':m10(pd.concat([f(X.rsi14<=30,X.rsi14),f(X.rsi2<=5,X.rsi2)],axis=1).max(axis=1))})
gcnt=grp.sum(axis=1); puts=pd.concat([f(X.pct_pct>=0.9,X.pct_pct),f(X.pce_pct>=0.9,X.pce_pct)],axis=1).max(axis=1)
m=Cl.rolling(20).mean(); s=Cl.rolling(20).std(); lb=m-2.5*s; band=((Cl.shift(1)<lb.shift(1))&(Cl>lb)).astype(float)
ovr=((Lr.pressure==1)|(Lr.score>=3))
def run(buy1,buy2,use_ovr,y0=2007):
    rows=[]
    for st in windows(Cl):
        if idx[st].year<y0: continue
        low=a[st:st+61].min()
        i=next((k for k in range(st,min(st+41,len(a))) if buy1.iloc[k]==1),None)
        if i is None: rows.append(dict(win=idx[st],hit=False,skip=False)); continue
        if use_ovr and ovr.iloc[i]: rows.append(dict(win=idx[st],hit=False,skip=True)); continue
        j=next((k for k in range(i+1,min(i+41,len(a))) if buy2.iloc[k]==1 and a[k]<a[i]),None) if buy2 is not None else None
        e=a[i] if j is None else 2/(1/a[i]+1/a[j]); fut=a[i+1:i+253]; below=np.where(fut<e)[0]
        rows.append(dict(win=idx[st],hit=True,skip=False,d1=idx[i],d2=idx[j] if j is not None else None,above_low=e/low-1,fall=min(0,fut[:63].min()/e-1),
            r1m=a[i+21]/e-1 if i+21<len(a) else np.nan,r3m=a[i+63]/e-1 if i+63<len(a) else np.nan,r6m=a[i+126]/e-1 if i+126<len(a) else np.nan,
            under=len(below) if len(fut)>=126 else np.nan,back=((below[-1]+1) if len(below) else 0) if len(fut)>=126 else np.nan))
    return pd.DataFrame(rows)
def S(D):
    H=D[D.hit]; d=H[H.r3m.notna()]
    return {'windows':len(D),'buys':len(H),'skipped (override)':int(D.skip.sum()),'2nd buy used':int(H.d2.notna().sum()),'entry vs low':f"{H.above_low.mean()*100:+.1f}%",'within 5%':f"{(H.above_low<=0.05).mean()*100:.0f}%",
            'fall med/worst':f"{H.fall.median()*100:.1f}% / {H.fall.min()*100:.0f}%",'days below (med)':f"{d.under.median():.0f}",'back above (med)':f"{d.back.median():.0f}",
            'r1/3/6m':f"{H.r1m.mean()*100:+.1f} / {d.r3m.mean()*100:+.1f} / {d.r6m.mean()*100:+.1f}",'up 3m':f"{(d.r3m>0).mean()*100:.0f}%",'score':round((d.r3m.mean()+H.fall.median())*100,1)}
depth=(dd<=-0.108).astype(float); b1band=pd.concat([depth,band.where(dd<=-0.08,0)],axis=1).max(axis=1)
b2=((gcnt>=3)|(puts==1)).astype(float); b2g=(gcnt>=3).astype(float)
V_={'A depth -> 3+ groups':(depth,b2g,False),'B depth -> 3+ groups or heavy puts':(depth,b2,False),'C band-or-depth -> 3+ or puts':(b1band,b2,False),
    'B + override':(depth,b2,True),'C + override':(b1band,b2,True),'depth only':(depth,None,False)}
out={}
for k,(x1,x2,o) in V_.items():
    D=run(x1,x2,o); out[(k,'2007-26')]=S(D); out[(k,'2007-15')]=S(D[D.win.dt.year<=2015]); out[(k,'2016-26')]=S(D[D.win.dt.year>=2016])
pd.set_option('display.width',300); print(pd.DataFrame(out).T.to_string())
D=run(depth,b2,True); D.to_pickle('final_fc_trades.pkl')
print(D[D.hit|D.skip][['win','d1','d2','skip','above_low','fall','r3m','r6m']].round(3).to_string(index=False))
