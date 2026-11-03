import pandas as pd, numpy as np
from ind import P,C
ndx=P['^NDX'].dropna(); idx=ndx.index[(ndx.index>='2007-02-01')]; ndx=ndx.reindex(idx)
I=pd.read_pickle('I2.pkl').reindex(idx)
f=lambda s: s.dropna().reindex(s.dropna().index.union(idx)).ffill().reindex(idx)
irx=f(C['^IRX']); dxy=f(C['DX-Y.NYB']); qqq,tlt,gld=f(P['QQQ']),f(P['TLT']),f(C['GC=F'])
O=pd.DataFrame(index=idx)
O['W1_tbill']=((irx-irx.shift(126))>0.5).astype(float)
O['W2_dollar']=((dxy/dxy.shift(126)-1)>0.05).astype(float)
b=lambda s:(s<s.rolling(200).mean()).astype(int)
O['W3_two_below200']=((b(qqq)+b(tlt)+b(gld))>=2).astype(float)
O['old_red']=((O.W1_tbill+O.W2_dollar+O.W3_two_below200)>=2).astype(float)
O['old_score']=O.W1_tbill+O.W2_dollar+O.W3_two_below200
a=ndx.values
def fmin(h):
    o=np.full(len(a),np.nan)
    for i in range(len(a)-h): o[i]=a[i+1:i+1+h].min()/a[i]-1
    return pd.Series(o,index=idx)
EF=(fmin(10)<=-0.07).astype(float); EF[fmin(10).isna()]=np.nan
EB=(fmin(252)<=-0.20).astype(float); EB[fmin(252).isna()]=np.nan
storm_new=['move_gt_120','vix_term_inverted','vvix_gt_100','credit_weak_3pct_63d','dollar_up_5pct_6m']
br=I[['narrow_ndx_eq_at_high','narrow_spx_rsp_at_high']].max(axis=1); rt=I[['curve_resteepen','move_gt_120']].max(axis=1)
BE=pd.DataFrame({'breadth':br,'credit':I['credit_weak_at_high'],'rates':rt,'dollar':I['dollar_up_5pct_6m'],'defensive':I['defensives_lead_5pct_63d']})
ST=I[storm_new]
designs={
 'STORM new (5)':(ST.sum(1),EF),
 'STORM new + W1':(ST.sum(1)+O.W1_tbill,EF),
 'STORM new + W3':(ST.sum(1)+O.W3_two_below200,EF),
 'STORM new + W1 + W3':(ST.sum(1)+O.W1_tbill+O.W3_two_below200,EF),
 'STORM new + old red':(ST.sum(1)+O.old_red,EF),
 'STORM old score alone':(O.old_score,EF),
 'BEAR new (5)':(BE.sum(1),EB),
 'BEAR new + W1':(BE.sum(1)+O.W1_tbill,EB),
 'BEAR new + W3':(BE.sum(1)+O.W3_two_below200,EB),
 'BEAR new + W1 + W3':(BE.sum(1)+O.W1_tbill+O.W3_two_below200,EB),
 'BEAR new + old red':(BE.sum(1)+O.old_red,EB),
 'BEAR old score alone':(O.old_score,EB),
}
def auc(s,e):
    m=e.notna()&s.notna(); s,e=s[m],e[m]; r=s.rank(); n1=e.sum(); n0=len(e)-n1
    return (r[e==1].sum()-n1*(n1+1)/2)/(n1*n0)
per={'A 2007-15':('2007-02-01','2015-12-31'),'B 2016-26':('2016-01-01','2026-12-31')}
rows=[]
for nm,(s,E) in designs.items():
    for pn,(x,y) in per.items():
        m=(idx>=x)&(idx<=y); s_,E_=s[m],E[m]; mm=E_.notna(); s_,E_=s_[mm],E_[mm]; base=E_.mean()
        row=dict(design=nm,per=pn,AUC=auc(s_,E_))
        for k in (1,2,3):
            on=s_>=k; row[f'on>={k}%']=on.mean()*100; row[f'lift>={k}']=(E_[on].mean()/base) if on.sum()>20 else np.nan
            row[f'recall>={k}%']=E_[on].sum()/E_.sum()*100
        rows.append(row)
R=pd.DataFrame(rows); pd.set_option('display.width',250)
print('base rates: fast',{p:round(float(EF[(idx>=x)&(idx<=y)].mean()*100),1) for p,(x,y) in per.items()},' bear',{p:round(float(EB[(idx>=x)&(idx<=y)].mean()*100),1) for p,(x,y) in per.items()})
print(R.round(2).to_string(index=False))
# single components lift each period
for k in ['W1_tbill','W2_dollar','W3_two_below200','old_red']:
    for E,en in [(EF,'fast'),(EB,'bear')]:
        out=[]
        for pn,(x,y) in per.items():
            m=(idx>=x)&(idx<=y)&E.notna(); on=O[k][m]==1; e=E[m]; out.append(f'{pn}: on {on.mean()*100:.0f}% lift {e[on].mean()/e.mean():.2f}')
        print(k,en,' | '.join(out))
# overlap: correlation between W3 and storm/bear parts
print('\ncorr W3 vs ndx_below_200d',round(O.W3_two_below200.corr(I.ndx_below_200d),2),' W2 identical to new dollar:',bool((O.W2_dollar==I.dollar_up_5pct_6m).mean()>0.99))
O.to_pickle('O.pkl'); ST.to_pickle('ST.pkl'); BE.to_pickle('BE.pkl')
