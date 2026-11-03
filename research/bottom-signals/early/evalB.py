import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
S=pd.read_pickle('SB.pkl'); ndx,state,dd,r21,m21,r63,m63,TR=pd.read_pickle('B_out.pkl'); idx=S.index; ii={d:i for i,d in enumerate(idx)}
BL={'06-10':(2006,2010),'11-15':(2011,2015),'16-19':(2016,2019),'20-22':(2020,2022),'23-26':(2023,2026)}
def score(sig,a,b):
    m=state&sig.notna()&r63.notna()&(idx.year>=a)&(idx.year<=b); on=sig[m]==1
    tr=[t for t in TR if a<=t.year<=b and pd.notna(sig.loc[t]) and t<pd.Timestamp('2026-10-01')]
    hit=sum((sig.iloc[max(0,ii[t]-5):ii[t]+11]==1).any() for t in tr)
    if on.sum()<5: return dict(days=int(on.sum()),hit=hit,n=len(tr))
    return dict(days=int(on.sum()),ex21=(r21[m][on].mean()-r21[m].mean())*100,ex63=(r63[m][on].mean()-r63[m].mean())*100,
                fall=(m21[m][on]<=-0.08).mean()*100,bfall=(m21[m]<=-0.08).mean()*100,hit=hit,n=len(tr))
if __name__=='__main__':
    m=state&r63.notna(); print(f'state days {m.sum()}, avg 21d {r21[m].mean()*100:.1f}%, 63d {r63[m].mean()*100:.1f}%, further 8% fall in 21d {(m21[m]<=-0.08).mean()*100:.0f}%')
    rows=[]
    for k in S:
        r={'sign':k}; good=nb=0
        for bn,(a,b) in BL.items():
            x=score(S[k],a,b)
            if 'ex63' in x:
                r[bn]=f"{x['ex63']:+.1f}"; nb+=1; good+=x['ex63']>0
        t=score(S[k],2006,2026)
        if 'ex63' in t: r.update(ALL_days=t['days'],ALL_ex21=round(t['ex21'],1),ALL_ex63=round(t['ex63'],1),fall=f"{t['fall']:.0f} vs {t['bfall']:.0f}",caught=f"{t['hit']}/{t['n']}",blocks_pos=f'{good}/{nb}')
        rows.append(r)
    R=pd.DataFrame(rows).set_index('sign'); pd.set_option('display.width',260); print(R.sort_values('ALL_ex63',ascending=False).to_string())
