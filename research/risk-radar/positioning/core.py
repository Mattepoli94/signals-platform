import pandas as pd, numpy as np
exec(open('eval2.py').read().split("rows=[]")[0])
fam=pd.DataFrame({'narrow':G[['narrow_ndx_63d','dispersion_high']].max(axis=1),'opt_complacency':G['pc_total_low'],
                  'ndx_vol_premium':G['nasdaq_vol_premium_high'],'leverage':G['margin_up_30pct_yoy']})
cnt=fam.sum(axis=1,min_count=3)
for k in (1,2,3):
    s=(cnt>=k).astype(float).where(cnt.notna()); row=[f'>= {k}']
    for bn,(a,b) in list(BL.items())+[('ALL',(2006,2026))]:
        x=sc(s,a,b); row.append(f'{bn}: on{x[0]:.0f}% {x[1]:.1f}x {x[2]}/{x[3]}' if x and not np.isnan(x[1]) else f'{bn}: -')
    print(' | '.join(row))
# horizon check: does it lead by more than 15 sessions? event within next 40 sessions
a=N.values; fm=np.full(len(a),np.nan)
for i in range(len(a)-40): fm[i]=a[i+1:i+41].min()/a[i]-1
E40=pd.Series((fm<=-0.10).astype(float),index=idx); E40[np.isnan(fm)]=np.nan
s2=(cnt>=2).astype(float).where(cnt.notna()); m=nearN&s2.notna()&E40.notna()
print('\n>=2 vs NDX -10%% within 2 months: base %.1f%%, when on %.1f%% (lift %.2f), on %.0f%%'%(E40[m].mean()*100,E40[m][s2[m]==1].mean()*100,E40[m][s2[m]==1].mean()/E40[m].mean(),(s2[m]==1).mean()*100))
print('\nper event, families on in the 20 sessions before:')
for e in EV:
    j=ii[e]; w=fam.iloc[max(0,j-20):j+1]; print(e.date(), [c for c in fam if (w[c]==1).any()])
print('\ntoday:',fam.iloc[-1].to_dict(),' near high?',bool(nearN.iloc[-1]))
print('raw today: total P/C 10d pct', ); 
