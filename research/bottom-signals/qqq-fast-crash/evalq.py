import pandas as pd, numpy as np, itertools, warnings; warnings.filterwarnings('ignore')
X=pd.read_pickle('X_qqq.pkl'); c,W=pd.read_pickle('cw_qqq.pkl'); idx=X.index
W=[i for i in W if idx[i].year>=2007]
FL={'stretch_z15':X.z15<=-2.5,'stretch_dd':X.dd_z<=-2.5,'capitulation_vol':X.capit3==1,'vxn_top10':X.vxn_pct>=0.9,'short_term_panic':X.vix9_ratio>=1.05,
    'puts_heavy_equity':X.pce_pct>=0.9,'puts_heavy_total':X.pct_pct>=0.9,'dealers_short_gamma':X.gex<0,'darkpool_buying':X.dix_pct>=0.9,
    'am_washed_out':X.am_ndx_pct<=0.2,'hf_short':X.lev_ndx_pct<=0.2,'rsi14_le30':X.rsi14<=30,'rsi2_le5':X.rsi2<=5}
avail={'stretch_z15':X.z15,'stretch_dd':X.dd_z,'capitulation_vol':X.capit3,'vxn_top10':X.vxn_pct,'short_term_panic':X.vix9_ratio,'puts_heavy_equity':X.pce_pct,'puts_heavy_total':X.pct_pct,
       'dealers_short_gamma':X.gex,'darkpool_buying':X.dix_pct,'am_washed_out':X.am_ndx_pct,'hf_short':X.lev_ndx_pct,'rsi14_le30':X.rsi14,'rsi2_le5':X.rsi2}
F=pd.DataFrame({k:v.astype(float).where(avail[k].notna()) for k,v in FL.items()})
a=c.values
def trade_metrics(i):
    e=a[i]; f=a[i+1:i+253]
    if len(f)<21: return dict(heat=min(0,(f.min()/e-1)) if len(f) else np.nan,r1m=np.nan,r3m=np.nan,r6m=np.nan,under=np.nan,back=np.nan)
    below=np.where(f<e)[0]
    return dict(heat=min(0,f.min()/e-1),heat3m=min(0,f[:63].min()/e-1),r1m=a[i+21]/e-1,r3m=a[i+63]/e-1 if i+63<len(a) else np.nan,r6m=a[i+126]/e-1 if i+126<len(a) else np.nan,
                under=len(below),back=(below[-1]+1) if len(below) else 0)
def window_low(s): return a[s:s+61].min()
def run_rule(sig,mindd=0.05,confirm=False,eras=None):
    rows=[]
    for s in W:
        hit=None
        for i in range(s,min(s+41,len(a))):
            if X.dd.iloc[i]<=-mindd and sig.iloc[i]==1: hit=i; break
        if hit is not None and confirm:
            hit=next((j for j in range(hit,min(hit+6,len(a))) if X.ret.iloc[j]>0),None)
        if hit is None: rows.append(dict(win=idx[s],date=None)); continue
        m=trade_metrics(hit); m.update(win=idx[s],date=idx[hit],above_low=a[hit]/window_low(s)-1,dd_at=X.dd.iloc[hit]); rows.append(m)
    return pd.DataFrame(rows)
def summ(D):
    H=D.dropna(subset=['date']); done=H[H.r3m.notna()]
    if len(H)==0: return {}
    return dict(signals=f'{len(H)}/{len(D)}',fall_med=H.heat3m.median()*100,fall_worst=H.heat3m.min()*100,within5=(H.above_low<=0.05).mean()*100,
                under_med=done.under.median(),r1m=H.r1m.mean()*100,r3m=done.r3m.mean()*100,r6m=done.r6m.mean()*100,score=(done.r3m.mean()+H.heat3m.median())*100)
