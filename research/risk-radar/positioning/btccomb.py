exec(open('btcpos15.py').read().split("rows=[]")[0])
X=F[['funding_gt_30pct','cme_lev_short_crowded','btc_up_40pct_30d']]
cnt=X.sum(axis=1,min_count=1)
for k in (1,2):
    s=(cnt>=k).astype(float)
    for pn,(a_,b_) in {'2019-22':(2019,2022),'2023-26':(2023,2026),'all':(2019,2026)}.items():
        m=(idx.year>=a_)&(idx.year<=b_)&near&E.notna()&cnt.notna(); f=s[m]==1; y=E[m]==1
        ev=[e for e in EV if a_<=e.year<=b_]; hit=sum((s.iloc[max(0,ii[e]-10):ii[e]+1]==1).any() for e in ev)
        print(f'>={k} {pn}: on {f.mean()*100:.0f}%  lift {y[f].mean()/y.mean():.2f}  caught {hit}/{len(ev)}')
print('today',X.iloc[-1].to_dict())
