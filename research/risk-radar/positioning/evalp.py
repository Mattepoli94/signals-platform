import pandas as pd, numpy as np
F=pd.read_pickle('F.pkl'); N,nearN,E,EV=pd.read_pickle('ev.pkl'); idx=F.index; ii={d:i for i,d in enumerate(idx)}
pers={'all':('2006','2026'),'2006-15':('2006','2015'),'2016-26':('2016','2026'),'2020-26':('2020','2026')}
def sc(sig,per):
    a,b=per; m=(idx.year>=int(a))&(idx.year<=int(b))&nearN&sig.notna()&E.notna()
    s=sig[m]==1; y=E[m]==1
    if m.sum()<200: return None
    lift=(y[s].mean()/y.mean()) if s.sum()>=20 and y.mean()>0 else np.nan
    ev=[e for e in EV if int(a)<=e.year<=int(b) and pd.notna(sig.loc[e])]
    hit=sum((sig.iloc[max(0,ii[e]-15):ii[e]+1]==1).any() for e in ev)
    return s.mean()*100,lift,f'{hit}/{len(ev)}'
def table(F):
    rows=[]
    for k in F:
        r={'flag':k}
        for pn,per in pers.items():
            x=sc(F[k],per)
            if x: r[f'{pn}_on%'],r[f'{pn}_lift'],r[f'{pn}_caught']=x
        rows.append(r)
    return pd.DataFrame(rows).set_index('flag')
if __name__=='__main__':
    pd.set_option('display.width',260)
    print('events by period:',{p:sum(int(a)<=e.year<=int(b) for e in EV) for p,(a,b) in pers.items()},' base %.1f%%'%(E[nearN].mean()*100))
    T=table(F); print(T.round(2).sort_values('all_lift',ascending=False).to_string())
