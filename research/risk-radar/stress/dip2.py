import sys; sys.path.insert(0,'/home/claude/signals-platform')
import pandas as pd, numpy as np
from signals.strategies import get
from signals.strategies.qqq_regime import regime_core
from ind import P
s=get('qqq_regime')
q=P['QQQ'].dropna(); irx=None
t=regime_core(q,s.params)
I=pd.read_pickle('I2.pkl')
f=lambda x: x.reindex(x.index.union(q.index)).ffill().reindex(q.index)
storm_parts=['move_gt_120','vix_term_inverted','vvix_gt_100','credit_weak_3pct_63d','dollar_up_5pct_6m']
SP=pd.DataFrame({k:f(I[k]) for k in storm_parts})
SP['storm_score']=SP[storm_parts].sum(axis=1,min_count=5)
SP['storm>=2']=(SP.storm_score>=2).astype(float); SP.loc[SP.storm_score.isna(),'storm>=2']=np.nan
SP['storm>=1']=(SP.storm_score>=1).astype(float); SP.loc[SP.storm_score.isna(),'storm>=1']=np.nan
# dip trades
w=t['w_dip']; c=q
tr=[]; inn=False
for i in range(1,len(w)):
    if not inn and w.iloc[i]>0 and w.iloc[i-1]==0: inn=True; e=i; size=w.iloc[i]
    elif inn and w.iloc[i]==0: tr.append((w.index[e],w.index[i],c.iloc[i]/c.iloc[e]-1,size,t['above200'].iloc[e])); inn=False
T=pd.DataFrame(tr,columns=['entry','exit','ret','size','above200'])
T=T[T.entry>='2007-02-01']
for k in storm_parts+['storm>=1','storm>=2']:
    T[k]=SP[k].shift(1).reindex(T.entry).values   # known at prior close
print('dip trades 2007-2026:',len(T),' avg %.2f%%  win %.0f%%'%(T.ret.mean()*100,(T.ret>0).mean()*100))
rows=[]
for k in storm_parts+['storm>=1','storm>=2']:
    for v in (1,0):
        x=T[T[k]==v]; rows.append(dict(flag=k,on=v,n=len(x),avg=x.ret.mean()*100,med=x.ret.median()*100,win=(x.ret>0).mean()*100,worst=x.ret.min()*100,sum_wret=(x.ret*x['size']).sum()*100))
print(pd.DataFrame(rows).round(2).to_string())
print('\nby regime, storm>=2:'); print(T.groupby(['above200','storm>=2']).ret.agg(['count','mean','min']).round(4))
T.to_pickle('diptrades.pkl'); SP.to_pickle('SP.pkl'); t.to_pickle('t_qqq.pkl')
