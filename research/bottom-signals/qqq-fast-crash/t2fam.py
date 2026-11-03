exec(open('pa.py').read())
pd.set_option('display.width',320); pd.set_option('display.max_colwidth',80)
W[:]=[i for i in W if idx[i].year>=2007]
m10=lambda s: s.rolling(10,min_periods=1).max()
f=lambda cond,src: cond.astype(float).where(src.notna()).fillna(0)
T2={
 'capitulation volume (QQQ vol>=1.8x avg on a -2% day)':f(X.capit3==1,X.capit3),
 'capitulation volume, stricter (>=2.5x, -3%)':f(((X.volx>=2.5)&(X.ret<=-0.03)).astype(float).rolling(3,min_periods=1).max()==1,X.volx),
 'puts heavy: total put/call top 10% of 1y':f(X.pct_pct>=0.9,X.pct_pct),
 'puts heavy: equity put/call top 10% of 1y':f(X.pce_pct>=0.9,X.pce_pct),
 'dealers short gamma (GEX<0)':f(X.gex<0,X.gex),
 'GEX in bottom 10% of 1y':f(tp(X.gex)<=0.1,X.gex),
 'asset managers washed out (NDX futures, bottom 20% of 3y)':f(X.am_ndx_pct<=0.2,X.am_ndx_pct),
 'hedge funds short (NDX futures, bottom 20% of 3y)':f(X.lev_ndx_pct<=0.2,X.lev_ndx_pct),
 'dark-pool buying (DIX top 10%)':f(X.dix_pct>=0.9,X.dix_pct),
 'VXN top 10% of 1y':f(X.vxn_pct>=0.9,X.vxn_pct),
 'short-term panic (VIX9D/VIX>=1.05)':f(X.vix9_ratio>=1.05,X.vix9_ratio),
}
T2['options fear + capitulation (both, 10d)']=((m10(T2['puts heavy: total put/call top 10% of 1y'])==1)&(m10(T2['capitulation volume (QQQ vol>=1.8x avg on a -2% day)'])==1)).astype(float)
T2['positioning + capitulation (both, 10d)']=((m10(pd.concat([T2['dealers short gamma (GEX<0)'],T2['asset managers washed out (NDX futures, bottom 20% of 3y)'],T2['hedge funds short (NDX futures, bottom 20% of 3y)']],axis=1).max(axis=1))==1)&(m10(T2['capitulation volume (QQQ vol>=1.8x avg on a -2% day)'])==1)).astype(float)
T2['3+ of 6 families (current)']=(cnt>=3).astype(float)
T2['RSI divergence (price pattern, for comparison)']=P['RSI14 bullish divergence at new low']
depth108=(dd<=-0.108).astype(float)
rows=[dict(rule='single buy at -10.8% (no 2nd buy)',**evaluate(depth108,gate=0.0))]
for k,v in T2.items():
    r=evaluate(depth108,v,gate=0.0)
    # how often the 2nd buy triggered
    used=0
    for s in W:
        i=next((q for q in range(s,min(s+41,len(a))) if dd.iloc[q]<=-0.108),None)
        if i is not None and next((q for q in range(i+1,min(i+41,len(a))) if v.iloc[q]==1 and a[q]<a[i]),None) is not None: used+=1
    rows.append(dict(rule=k,used=used,**r))
R=pd.DataFrame(rows).round(1); print('windows 2007-2026:',len(W)); print(R[['rule','used','signals','above_low','within5','fall_med','fall_worst','r3m','r6m','score','e1','e2']].sort_values('score',ascending=False).to_string(index=False))
