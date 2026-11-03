from sig import *
import itertools
ERAS={'old':(1990,2009),'new':(2010,2026)}
cfg={'SPY':(0.06,1.0),'QQQ':(0.08,1.35)}
data={n:load(n) for n in cfg}
def gen(n,trig='vixrev',V=30,rev=0.15,depth=0.05,confirm='none',ctx=True,k=2.0,dn=0.03):
    f,scl=cfg[n]; c,v,vix=data[n]; starts=fast_windows(c,f); hi=c.rolling(252,min_periods=200).max(); s200=c.rolling(200).mean(); ret=c.pct_change(); va=v.rolling(50).mean()
    vmax=vix.rolling(10).max(); out=[]
    for s in starts:
        bull=(c.iloc[s]>s200.iloc[s]) and (s200.iloc[s]>s200.iloc[s-20])
        if ctx and not bull: continue
        hit=None
        for i in range(s,min(s+41,len(c))):
            dd=c.iloc[i]/hi.iloc[i]-1
            if dd>-depth*scl: continue
            if trig=='depth': t=True
            elif trig=='vix': t=vix.iloc[i]>=V
            elif trig=='vixrev': t=(vmax.iloc[i]>=V) and (vix.iloc[i]<=vmax.iloc[i]*(1-rev))
            elif trig=='capit': t=(v.iloc[i]>=k*va.iloc[i]) and ret.iloc[i]<=-dn
            elif trig=='vix_or_capit': t=(vix.iloc[i]>=V) or ((v.iloc[i]>=k*va.iloc[i]) and ret.iloc[i]<=-dn)
            if t: hit=i; break
        if hit is not None and confirm=='upday':
            hit=next((j for j in range(hit,min(hit+6,len(c))) if ret.iloc[j]>0),None)
        if hit is not None and confirm=='3d_high':
            hit=next((j for j in range(hit+1,min(hit+11,len(c))) if c.iloc[j]>=c.iloc[j-3:j].max()),None)
        out.append((s,hit))
    return out
def ev(**kw):
    res={}
    for n in cfg:
        c=data[n][0]; sg=gen(n,**kw)
        for en,er in ERAS.items():
            w=[(s,h) for s,h in sg if er[0]<=c.index[s].year<=er[1]]
            s,_=summarize(c,[h for s_,h in w],er); res[(n,en)]=(s,len(w))
    return res
rows=[]
G=[dict(trig='depth',depth=d,ctx=cx) for d in (0.06,0.08,0.10) for cx in (True,False)]
G+=[dict(trig='vix',V=V,depth=d,ctx=cx,confirm=cf) for V in (25,30,35) for d in (0.05,0.08) for cx in (True,False) for cf in ('none','upday')]
G+=[dict(trig='vixrev',V=V,rev=r,depth=d,ctx=cx) for V in (22,25,30) for r in (0.10,0.15,0.20) for d in (0.05,0.08) for cx in (True,False)]
G+=[dict(trig='capit',k=k,depth=d,ctx=cx,confirm=cf) for k in (1.5,2.0) for d in (0.05,0.08) for cx in (True,False) for cf in ('none','upday')]
for kw in G:
    o=ev(**kw); rec={k:v for k,v in kw.items()}; sc=[]
    for key,(s,nw) in o.items():
        if s is None or nw==0: sc.append(-99); rec['_'.join(key)]='-'; continue
        cov=s['n']/nw; val=s['r3m']+s['heat_med']; rec['_'.join(key)]=f"{val*100:+.1f} r3m{s['r3m']*100:+.0f} h{s['heat_med']*100:.0f} ({s['n']}/{nw})"; sc.append(val if cov>=0.6 else -99)
    rec['min']=round(min(sc)*100,1); rows.append(rec)
R=pd.DataFrame(rows).sort_values('min',ascending=False); pd.set_option('display.width',300); pd.set_option('display.max_columns',30)
print(R.head(25).to_string(index=False))
