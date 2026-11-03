import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
S=pd.read_pickle('SA.pkl'); spx,state,dd,r126,m126,r252,TR=pd.read_pickle('A_out.pkl'); idx=S.index; ii={d:i for i,d in enumerate(idx)}
PER={'1955-94':('1955','1994'),'1995-2026':('1995','2026')}
def score(sig,a,b):
    m=state&sig.notna()&r126.notna()&(idx.year>=int(a))&(idx.year<=int(b)); on=sig[m]==1
    if on.sum()<5: return None
    base126,base252,bfall=r126[m].mean(),r252[m].mean(),(m126[m]<=-0.10).mean()
    tr=[t for t in TR if int(a)<=t.year<=int(b) and pd.notna(sig.loc[t])]
    hit=sum((sig.iloc[max(0,ii[t]-10):ii[t]+22]==1).any() for t in tr)
    return dict(days=int(on.sum()),ex126=(r126[m][on].mean()-base126)*100,ex252=(r252[m][on].mean()-base252)*100,
                win252=(r252[m][on]>0).mean()*100,fall=(m126[m][on]<=-0.10).mean()*100,basefall=bfall*100,caught=f'{hit}/{len(tr)}')
if __name__=='__main__':
    for pn,(a,b) in PER.items():
        m=state&r126.notna()&(idx.year>=int(a))&(idx.year<=int(b))
        print(f'{pn}: state days {m.sum()}, avg 126d {r126[m].mean()*100:.1f}%, 252d {r252[m].mean()*100:.1f}%, further 10% fall {(m126[m]<=-0.10).mean()*100:.0f}%')
    rows=[]
    for k in S:
        r={'sign':k}
        for pn,(a,b) in PER.items():
            x=score(S[k],a,b)
            if x: r.update({f'{pn} days':x['days'],f'{pn} +6m':round(x['ex126'],1),f'{pn} +12m':round(x['ex252'],1),f'{pn} fall%':round(x['fall']),f'{pn} caught':x['caught']})
        rows.append(r)
    R=pd.DataFrame(rows).set_index('sign'); pd.set_option('display.width',250); print(R.to_string())
