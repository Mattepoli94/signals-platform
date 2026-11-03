exec(open('soxx.py').read().split("fall0=0.08*scale")[0])
def windows_rel(cc,fall,n=15,near=0.04,win=40,look=63):
    aa=cc.values; hh=cc.rolling(look,min_periods=look).max().values; out=[]; i=0
    while i<len(aa)-1:
        fut=aa[i+1:i+1+n]
        if hh[i]==hh[i] and aa[i]/hh[i]-1>=-near and len(fut) and fut.min()/aa[i]-1<=-fall: out.append(i); i+=win
        else: i+=1
    return out
hi63=c.rolling(63).max(); dd63=c/hi63-1
def plan2(fall,depth,two=True):
    rows=[]
    for st in windows_rel(c,fall):
        if idx[st].year<2007: continue
        low=a[st:st+61].min()
        i=next((k for k in range(st,min(st+41,len(a))) if a[k]/a[st:k+1].max()-1<=-depth),None)   # depth from the window's own high
        if i is None: rows.append(dict(start=idx[st],hit=False,skip=False)); continue
        if ovr.iloc[i]: rows.append(dict(start=idx[st],hit=False,skip=True)); continue
        j=next((k for k in range(i+1,min(i+41,len(a))) if cnt.iloc[k]>=3 and a[k]<a[i]),None) if two else None
        e=a[i] if j is None else 2/(1/a[i]+1/a[j]); fut=a[i+1:i+253]; below=np.where(fut<e)[0]
        rows.append(dict(start=idx[st],hit=True,skip=False,d1=idx[i],d2=idx[j] if j is not None else None,above_low=e/low-1,fall=min(0,fut[:63].min()/e-1),
            r1m=a[i+21]/e-1 if i+21<len(a) else np.nan,r3m=a[i+63]/e-1 if i+63<len(a) else np.nan,r6m=a[i+126]/e-1 if i+126<len(a) else np.nan,
            under=len(below) if len(fut)>=126 else np.nan,back=((below[-1]+1) if len(below) else 0) if len(fut)>=126 else np.nan))
    return pd.DataFrame(rows)
out={}
for dep in (0.12,0.15):
    for two in (False,True):
        D=plan2(0.115,dep,two)
        for era,m in [('2007-26',D.start.dt.year>=2007),('2007-15',D.start.dt.year<=2015),('2016-26',D.start.dt.year>=2016)]:
            out[(f'from 3-month high, depth -{dep*100:.0f}%','two' if two else 'one',era)]=S(D[m])
pd.set_option('display.width',320); print(pd.DataFrame(out).T.to_string())
D=plan2(0.115,0.12,True); print(D[['start','d1','d2','skip','above_low','fall','r3m','r6m']].round(3).to_string(index=False))
