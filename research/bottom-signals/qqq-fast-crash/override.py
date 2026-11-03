import sys; sys.path.insert(0,'/home/claude/signals-platform')
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
from signals import radar as RD
from generic import *
L=RD.late_cycle()
c=C['^NDX'].dropna(); c=c[c.index>='1988-01-01']; idx=c.index; a=c.values
v=on(V['QQQ'],idx); X=price_feats(c,v).join(market_feats(idx)); G=families(X); cnt=G.fillna(0).sum(axis=1)
vix=on(C['^VIX'],idx); s200=c.rolling(200).mean(); hi=c.rolling(252,min_periods=200).max(); dd=c/hi-1
Lr=L.reindex(L.index.union(idx)).ffill().reindex(idx)
OV={'none':pd.Series(False,index=idx),
    'late-cycle radar >=2':Lr.score>=2,
    'late-cycle radar >=3':Lr.score>=3,
    'rate/inflation pressure':Lr.pressure==1,
    '200-day average falling':s200<s200.shift(20),
    'below 200-day average at entry':c<s200}
def fast_entries():
    out=[]
    for s in windows(c):
        if idx[s].year<1990: continue
        i=next((k for k in range(s,min(s+41,len(a))) if dd.iloc[k]<=-0.108),None)
        if i is None: continue
        j=next((k for k in range(i+1,min(i+41,len(a))) if cnt.iloc[k]>=3 and a[k]<a[i] and idx[k].year>=2007),None)
        out.append((s,i,j))
    return out
def washouts():
    cond=((dd<=-0.405)|(c/s200<=0.73)|(vix>=35))&(dd<=-0.2025); sig=[]; last=-999
    for i in np.where(cond.fillna(False).values)[0]:
        if i-last>=126: sig.append(i); last=i
    return sig
def stats(i,j=None):
    e=a[i] if j is None else 2/(1/a[i]+1/a[j]); f=a[i+1:i+253]
    return dict(date=idx[i],kind=None,fall6m=min(0,f[:126].min()/e-1) if len(f) else np.nan,r3m=a[i+63]/e-1 if i+63<len(a) else np.nan,
                r6m=a[i+126]/e-1 if i+126<len(a) else np.nan,r12m=a[i+252]/e-1 if i+252<len(a) else np.nan)
FE=fast_entries(); WS=washouts()
rows=[]
for nm,ov in OV.items():
    ents=[]; skipped=[]
    for s,i,j in FE:
        if ov.iloc[i]: skipped.append(stats(i,j)); continue
        st=stats(i,j); st['kind']='fast'; ents.append(st)
    for w in WS:
        st=stats(w); st['kind']='washout'; ents.append(st)
    E=pd.DataFrame(ents).sort_values('date'); Sk=pd.DataFrame(skipped)
    bad=lambda D: (D.fall6m<=-0.10).sum() if len(D) else 0
    fastE=E[E.kind=='fast']
    rows.append({'Override':nm,'Fast buys taken':len(fastE),'...of which fell 10%+ more (traps)':bad(fastE),
        'Fast buys skipped':len(Sk),'...skipped traps':bad(Sk),'...skipped good rebounds':(len(Sk)-bad(Sk)) if len(Sk) else 0,
        'Skipped buys 6m return (avg)':f"{Sk.r6m.mean()*100:+.1f}%" if len(Sk) else '-',
        'All buys (fast+washout)':len(E),'Further fall 6m (median / worst)':f"{E.fall6m.median()*100:.1f}% / {E.fall6m.min()*100:.0f}%",
        'Trap rate':f"{(E.fall6m<=-0.10).mean()*100:.0f}%",'Return 3m / 6m / 12m':f"{E.r3m.mean()*100:+.1f}% / {E.r6m.mean()*100:+.1f}% / {E.r12m.mean()*100:+.1f}%",'Up after 6m':f"{(E.r6m.dropna()>0).mean()*100:.0f}%"})
R=pd.DataFrame(rows); pd.set_option('display.width',320); pd.set_option('display.max_colwidth',40)
print('fast entries since 1990:',len(FE),' washouts:',[idx[w].date() for w in WS])
print(R.to_string(index=False))
# detail table for the best candidates
det=[]
for s,i,j in FE:
    st=stats(i,j); det.append(dict(entry=idx[i].date(),fall6m=round(st['fall6m']*100,1),r6m=round(st['r6m']*100,1) if st['r6m']==st['r6m'] else None,
        late=int(Lr.score.iloc[i]) if Lr.score.iloc[i]==Lr.score.iloc[i] else None,pressure=int(Lr.pressure.iloc[i]) if Lr.pressure.iloc[i]==Lr.pressure.iloc[i] else None,
        s200_falling=bool(s200.iloc[i]<s200.iloc[i-20]),below200=bool(c.iloc[i]<s200.iloc[i])))
print(pd.DataFrame(det).to_string(index=False))
pd.to_pickle((FE,WS),'ov_entries.pkl')

print('\n--- combined override and odds ---')
comb=(Lr.pressure==1)|(Lr.score>=3)
OV2={'rate/inflation pressure':Lr.pressure==1,'pressure OR late-cycle >=3':comb}
for nm,ov in OV2.items():
    on_=[stats(i,j) for s,i,j in FE if ov.iloc[i]]; off=[stats(i,j) for s,i,j in FE if not ov.iloc[i]]
    A_=pd.DataFrame(on_); B_=pd.DataFrame(off)
    print(nm,'| override ON:',len(A_),'buys, losing after 6m',(A_.r6m<0).sum(),', fell 10%+ more',(A_.fall6m<=-0.10).sum(),', avg 6m %+.1f%%'%(A_.r6m.mean()*100),
          '| OFF:',len(B_),'buys, losing after 6m',(B_.r6m<0).sum(),', fell 10%+ more',(B_.fall6m<=-0.10).sum(),', avg 6m %+.1f%%'%(B_.r6m.mean()*100))
print('today: pressure',Lr.pressure.iloc[-1],'late score',Lr.score.iloc[-1], '10y chg',round(Lr.y10_chg.iloc[-1],2),'CPI',Lr.infl.iloc[-1])
