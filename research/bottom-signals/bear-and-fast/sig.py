from eng import *
def rsi(c,n=14):
    x=c.diff(); up=x.clip(lower=0).ewm(alpha=1/n,adjust=False).mean(); dn=(-x.clip(upper=0)).ewm(alpha=1/n,adjust=False).mean(); return 100-100/(1+up/dn)
def fast_signals(c,v,vix,fall,V=30,k=2.0,dn=0.03,confirm='none',naive=None,depth=0.05,use_vix=True,use_vol=True):
    starts=fast_windows(c,fall); hi=c.rolling(252,min_periods=200).max(); ret=c.pct_change(); va=v.rolling(50).mean()
    out=[]
    for s in starts:
        seg=range(s,min(s+41,len(c)))
        hit=None
        for i in seg:
            if naive is not None:
                if c.iloc[i]/hi.iloc[i]-1<=-naive: hit=i; break
                continue
            trig=(use_vix and vix.iloc[i]==vix.iloc[i] and vix.iloc[i]>=V) or (use_vol and v.iloc[i]==v.iloc[i] and va.iloc[i]==va.iloc[i] and v.iloc[i]>=k*va.iloc[i] and ret.iloc[i]<=-dn)
            if trig and c.iloc[i]/hi.iloc[i]-1<=-depth: hit=i; break
        if hit is None: out.append((s,None)); continue
        if confirm=='upday':
            j=next((j for j in range(hit,min(hit+6,len(c))) if ret.iloc[j]>0),None); hit=j
        elif confirm=='3d_high':
            j=next((j for j in range(hit+1,min(hit+11,len(c))) if c.iloc[j]>=c.iloc[j-3:j].max()),None); hit=j
        out.append((s,hit))
    return out
def bear_signals(c,vix,state=0.15,kind='thrust',T=0.07,N=10,W=0.30,M=0.20,VB=40,cool=126):
    hi=c.rolling(252,min_periods=200).max(); dd=c/hi-1; s200=c.rolling(200).mean()
    if kind=='thrust': cond=(c/c.shift(N)>=1+T)&(dd<=-state)
    elif kind=='washout': cond=((dd<=-W)|(c/s200<=1-M)|(vix>=VB))&(dd<=-state)
    elif kind=='naive': cond=(dd<=-W)
    elif kind=='thrust_after_washout':
        w=((dd<=-W)|(c/s200<=1-M)|(vix>=VB)).astype(float).rolling(126,min_periods=1).max()==1
        cond=(c/c.shift(N)>=1+T)&(dd<=-state)&w
    sig=[]; last=-10**9
    for i in np.where(cond.fillna(False).values)[0]:
        if i-last>=cool: sig.append(i); last=i
    return sig
def summarize(c,idxs,era=None):
    rows=[m for m in (metrics(c,i) for i in idxs if i is not None) if m]
    if era: rows=[r for r in rows if era[0]<=r['date'].year<=era[1]]
    if not rows: return None,pd.DataFrame()
    D=pd.DataFrame(rows)
    s=dict(n=len(D),heat_med=D.heat.median(),heat_worst=D.heat.min(),within5=(D.heat>=-0.05).mean(),above_low_med=D.above_low.median(),
           days_low_med=D.days_to_low.median(),be_med=D.days_breakeven.median(),be_max=D.days_breakeven.max(),
           r1m=D.r1m.mean(),r3m=D.r3m.mean(),r6m=D.r6m.mean(),r12m=D.r12m.mean(),win6=(D.r6m>0).mean())
    return s,D
