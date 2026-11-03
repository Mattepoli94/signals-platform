import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
exec(open('evalB2.py').read().split("rows=[]")[0])
X=pd.DataFrame(index=idx)
fam={'fear':S['vix_ge_30'],'capitulation':S['capitulation_volume'],'dealers_short_gamma':S['gex_negative'],'oversold':S['rsi_lt_30']}
F=pd.DataFrame(fam)
for k in (1,2,3): X[f'flash_score>={k}']=(F.fillna(0).sum(axis=1)>=k).astype(float)
X['fear_or_capit']=F[['fear','capitulation']].max(axis=1)
X['fear_and_gamma']=((F.fear==1)&(F.dealers_short_gamma==1)).astype(float).where(F.dealers_short_gamma.notna())
X['capit_5d']=F.capitulation.rolling(5,min_periods=1).max()
X['fear_or_capit_5d']=X['fear_or_capit'].rolling(5,min_periods=1).max()
rows=[]
for k in X:
    sig=X[k]; r={'rule':k}; nb=good=0
    for bn,(a,b) in BL.items():
        mm=state&sig.notna()&r63.notna()&(idx.year>=a)&(idx.year<=b); on=sig[mm]==1
        if on.sum()>=3: nb+=1; ex=r63[mm][on].mean()-r63[mm].mean(); good+=ex>0; r[bn]=f'{ex*100:+.1f}'
    mm=state&sig.notna()&r63.notna(); on=sig[mm]==1
    r.update(days=int(on.sum()),ex21=round((r21[mm][on].mean()-r21[mm].mean())*100,1),ex63=round((r63[mm][on].mean()-r63[mm].mean())*100,1),
             win63=round((r63[mm][on]>0).mean()*100), fall=f"{(m21[mm][on]<=-0.08).mean()*100:.0f} vs {(m21[mm]<=-0.08).mean()*100:.0f}",
             near_trough=f"{near_tr[mm][on].mean()*100:.0f} vs {near_tr[mm].mean()*100:.0f}",
             episodes=f"{sum(((sig.iloc[ii[e]:ii[e]+41]==1)&state.iloc[ii[e]:ii[e]+41]).any() for e in EV)}/{len(EV)}",blocks_pos=f'{good}/{nb}')
    rows.append(r)
pd.set_option('display.width',260); print(pd.DataFrame(rows).set_index('rule').to_string())
print('\nbaseline win63 in windows', round((r63[state&r63.notna()]>0).mean()*100))
X.to_pickle('XB.pkl'); F.to_pickle('FB.pkl')
print('\nper episode: first fear-or-capitulation day in the window, its price vs the trough, and the 63-day return after it')
for e,t in zip(EV,TR):
    j=ii[e]; seg=idx[j:j+41]; w=X['fear_or_capit'].loc[seg]; w=w[(w==1)&state.loc[seg]]
    if len(w): d0=w.index[0]; print(e.date(),'trough',t.date(),'signal',d0.date(),f'{(ndx.loc[d0]/ndx.loc[t]-1)*100:+.1f}% vs low', f'63d {r63.loc[d0]*100:+.1f}%' if pd.notna(r63.loc[d0]) else '')
    else: print(e.date(),'trough',t.date(),'no signal')
