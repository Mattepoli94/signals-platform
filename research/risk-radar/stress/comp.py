import pandas as pd, numpy as np
from ind import P,build
ndx=P['^NDX'].dropna(); idx=ndx.index[ndx.index>='1990-01-01']; ndx=ndx.reindex(idx)
exec(open('study.py').read().split("per={")[0].split("I=build(idx)")[1])
I=pd.read_pickle('I_ndx.pkl')
fam={'breadth':['narrow_ndx_eq_at_high','narrow_spx_rsp_at_high'],'credit':['credit_weak_at_high'],
     'rates':['curve_resteepen','move_gt_120'],'dollar':['dollar_up_5pct_6m'],'defensive':['defensives_lead_5pct_63d']}
S=pd.DataFrame({k:I[v].max(axis=1) for k,v in fam.items()})
I2=pd.DataFrame(index=idx)
for k in range(1,4): I2[f'score>={k}']=(S.sum(axis=1)>=k).astype(float)
for k in fam: I2['fam_'+k]=S[k]
per={'A 1990-2012':('1990-01-01','2012-12-31'),'B 2013-2026':('2013-01-01','2026-12-31')}
R=evaluate(I2,per)
print(R.pivot(index='flag',columns='per',values=['time_on','p_when_on','lift','flash_lift','fwd63','eps_caught']).round(2).to_string())
S.to_pickle('S_ndx.pkl')
print('current flags (last day):'); print(S.iloc[-5:]); print(I.iloc[-1][I.iloc[-1]==1])
