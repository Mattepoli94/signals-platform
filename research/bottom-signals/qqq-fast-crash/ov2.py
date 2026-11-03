exec(open('override.py').read().split("rows=[]")[0])
OVS={'none':pd.Series(False,index=idx),'rate/inflation pressure':Lr.pressure==1,'late-cycle red (3+)':Lr.score>=3,
     'pressure OR red':(Lr.pressure==1)|(Lr.score>=3),'pressure AND amber (2+)':(Lr.pressure==1)&(Lr.score>=2),'red AND below 200d':(Lr.score>=3)&(c<s200)}
rows=[]
for nm,ov in OVS.items():
    ents=[];sk=[]
    for s,i,j in FE:
        (sk if ov.iloc[i] else ents).append(stats(i,j))
    for w in WS: ents.append(stats(w))
    E=pd.DataFrame(ents); S_=pd.DataFrame(sk)
    rows.append({'Override':nm,'Skipped':len(S_),'Skipped that lost money at 6m':int((S_.r6m<0).sum()) if len(S_) else 0,
                 'Skipped that made money at 6m':int((S_.r6m>0).sum()) if len(S_) else 0,'Skipped dates':', '.join(str(d.date())[:7] for d in S_.date) if len(S_) else '',
                 'System buys':len(E),'Losing at 6m':f"{(E.r6m<0).mean()*100:.0f}%",'Fell 10%+ more':f"{(E.fall6m<=-0.10).mean()*100:.0f}%",
                 '6m / 12m avg':f"{E.r6m.mean()*100:+.1f}% / {E.r12m.mean()*100:+.1f}%",'Worst 12m':f"{E.r12m.min()*100:.0f}%"})
pd.set_option('display.width',320); pd.set_option('display.max_colwidth',70); print(pd.DataFrame(rows).to_string(index=False))
# depth of fast-crash lows
lows=[]
for s in windows(c):
    if idx[s].year<1990: continue
    lo=a[s:s+61].min(); lows.append(lo/hi.iloc[s:s+61].max()-1)
lows=pd.Series(lows); print('\nQQQ fast-crash lows (depth from 1y high), n=%d: median %.1f%%, 25th %.1f%%, 75th %.1f%%, share deeper than 10.8%%: %.0f%%'%(len(lows),lows.median()*100,lows.quantile(.25)*100,lows.quantile(.75)*100,(lows<=-0.108).mean()*100))
print(sorted((lows*100).round(1).tolist()))
