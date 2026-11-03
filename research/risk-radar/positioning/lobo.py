import pandas as pd, numpy as np
exec(open('eval2.py').read().split("rows=[]")[0])
def pooled(sig,blocks):
    m=nearN&sig.notna()&E.notna()&np.isin(idx.year,[y for a,b in blocks for y in range(a,b+1)])
    s=sig[m]==1; y=E[m]==1
    ev=[e for e in EV if any(a<=e.year<=b for a,b in blocks) and pd.notna(sig.loc[e])]
    hit=sum((sig.iloc[max(0,ii[e]-20):ii[e]+1]==1).any() for e in ev)
    lift=(y[s].mean()/y.mean()) if s.sum()>=15 and y.mean()>0 else np.nan
    return lift,hit,len(ev),s.mean()
cands=[c for c in G.columns if c not in ('pc_spx_low','pc_spx_high')]
out=[]; heldsig=pd.Series(np.nan,index=idx)
for hb,(ha,hbb) in BL.items():
    train=[v for k,v in BL.items() if k!=hb]
    sel=[]
    for c in cands:
        oks=[];
        for a,b in train:
            x=sc(G[c],a,b)
            if x and x[3]>0 and not np.isnan(x[1]): oks.append(x[1]>=1.3)
        L,h,n,_=pooled(G[c],train)
        if len(oks)>=2 and np.mean(oks)>=0.6 and L>=1.3: sel.append(c)
    X=G[sel]; cnt=X.sum(axis=1,min_count=1)
    best=None
    for k in range(1,min(4,len(sel))+1):
        s=(cnt>=k).astype(float).where(cnt.notna())
        L,h,n,on=pooled(s,train); score=(L if not np.isnan(L) else 0)*(h/max(n,1))
        if best is None or score>best[0]: best=(score,k)
    k=best[1]; s=(cnt>=k).astype(float).where(cnt.notna())
    t=sc(s,ha,hbb); mask=(idx.year>=ha)&(idx.year<=hbb); heldsig[mask]=s[mask]
    out.append(dict(heldout=hb,selected=', '.join(sel),k=k,test_on=round(t[0]),test_lift=round(t[1],2) if t and not np.isnan(t[1]) else None,caught=f'{t[2]}/{t[3]}'))
pd.set_option('display.width',300); pd.set_option('display.max_colwidth',150)
print(pd.DataFrame(out).to_string(index=False))
L,h,n,on=pooled(heldsig,list(BL.values())); print(f'\nALL held-out blocks combined: on {on*100:.0f}% of near-high days, lift {L:.2f}, caught {h}/{n}')
