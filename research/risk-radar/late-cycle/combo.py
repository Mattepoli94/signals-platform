from base import *
import itertools
L=pd.read_pickle('L.pkl')
exec(open('ev.py').read().split("rows=[]")[0].split("L=pd.read_pickle('L.pkl')")[1])
cands=['curve_flat_lt_0.5','curve_inv_last18m','inflation_gt4_rising','cape_top10pct_to_date','spx_up_50pct_24m','10y_up_1.5pt_12m',
       'fed_hiking_1.5pt_12m','spx_up_25pct_12m','momentum_fading','real_tbill_gt_2','earn_yield_below_10y','dollar_up_10pct_12m']
fam={'curve_flat_lt_0.5':'curve','curve_inv_last18m':'curve','10y_up_1.5pt_12m':'rates','fed_hiking_1.5pt_12m':'rates','real_tbill_gt_2':'rates',
     'cape_top10pct_to_date':'val','earn_yield_below_10y':'val','spx_up_50pct_24m':'ext','spx_up_25pct_12m':'ext','momentum_fading':'ext',
     'inflation_gt4_rising':'infl','dollar_up_10pct_12m':'usd'}
def ev_combo(cols,k,lab,events,lead,per):
    s=(L[cols].sum(axis=1,min_count=len(cols))>=k).astype(float); s[L[cols].isna().any(axis=1)]=np.nan
    return score(s,lab,events,per,lead),s
res=[]
for n in (1,2,3,4):
    for cols in itertools.combinations(cands,n):
        if len({fam[c] for c in cols})<n: continue
        for k in range(1,n+1):
            for tgt,lab,evs,lead in [('bear',BULL,PK,126),('fast',FAST,CR,21)]:
                tr,_=ev_combo(list(cols),k,lab,evs,lead,TR)
                if not isinstance(tr.get('lift'),float) or np.isnan(tr['lift']) or tr['on']<8: continue
                c,t=map(int,tr['caught'].split('/'))
                res.append(dict(tgt=tgt,cols=' + '.join(cols),k=k,n=n,tr_on=tr['on'],tr_lift=tr['lift'],tr_caught=tr['caught'],tr_score=tr['lift']*(c/t)))
R=pd.DataFrame(res)
pd.set_option('display.width',280); pd.set_option('display.max_colwidth',120)
out=[]
for tgt,lab,evs,lead in [('bear',BULL,PK,126),('fast',FAST,CR,21)]:
    top=R[R.tgt==tgt].sort_values('tr_score',ascending=False).head(8)
    for _,r in top.iterrows():
        te,_=ev_combo(r.cols.split(' + '),r.k,lab,evs,lead,TE)
        out.append(dict(tgt=tgt,rule=f'{r.k} of [{r.cols}]',tr_on=r.tr_on,tr_lift=r.tr_lift,tr_caught=r.tr_caught,te_on=te['on'],te_lift=te['lift'],te_caught=te['caught']))
print(pd.DataFrame(out).round(2).to_string(index=False))
