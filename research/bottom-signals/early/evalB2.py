import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
exec(open('evalB.py').read().split("if __name__")[0])
N,nearN,E,EV=pd.read_pickle('/home/claude/pos/ev.pkl')
win=pd.Series(False,index=idx)
for e in EV:
    j=ii[e]; win.iloc[j:j+41]=True
state=win&(dd<=-0.05)
# closeness to trough: buy price within 3% of the eventual trough of that episode
near_tr=pd.Series(np.nan,index=idx)
for e,t in zip(EV,TR):
    j=ii[e]; seg=idx[j:j+41]; near_tr.loc[seg]=(ndx.loc[seg]/ndx.loc[t]-1<=0.03).astype(float)
m=state&r63.notna(); print(f'flash-crash windows: days {m.sum()}, avg 21d {r21[m].mean()*100:.1f}%, 63d {r63[m].mean()*100:.1f}%, further 8% fall {(m21[m]<=-0.08).mean()*100:.0f}%, within 3% of trough {near_tr[m].mean()*100:.0f}%')
rows=[]
for k in S:
    sig=S[k]; r={'sign':k}; nb=good=0
    for bn,(a,b) in BL.items():
        mm=state&sig.notna()&r63.notna()&(idx.year>=a)&(idx.year<=b); on=sig[mm]==1
        if on.sum()>=3: nb+=1; ex=r63[mm][on].mean()-r63[mm].mean(); good+=ex>0; r[bn]=f'{ex*100:+.1f}'
    mm=state&sig.notna()&r63.notna(); on=sig[mm]==1
    if on.sum()<8: continue
    r.update(days=int(on.sum()),ex21=round((r21[mm][on].mean()-r21[mm].mean())*100,1),ex63=round((r63[mm][on].mean()-r63[mm].mean())*100,1),
             fall=f"{(m21[mm][on]<=-0.08).mean()*100:.0f} vs {(m21[mm]<=-0.08).mean()*100:.0f}",near_trough=f"{near_tr[mm][on].mean()*100:.0f} vs {near_tr[mm].mean()*100:.0f}",
             episodes=f"{sum(((sig.iloc[ii[e]:ii[e]+41]==1)&state.iloc[ii[e]:ii[e]+41]).any() for e in EV if pd.notna(sig.loc[e]))}/{sum(pd.notna(sig.loc[e]) for e in EV)}",blocks_pos=f'{good}/{nb}')
    rows.append(r)
R=pd.DataFrame(rows).set_index('sign'); pd.set_option('display.width',260); print(R.sort_values('ex63',ascending=False).to_string())
