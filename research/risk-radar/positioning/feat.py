import pandas as pd, numpy as np
d=pd.read_csv('/home/claude/risk/prices.csv',parse_dates=['date'])
P=d.pivot(index='date',columns='ticker',values='adj_close').sort_index(); C=d.pivot(index='date',columns='ticker',values='close').sort_index()
ndx=C['^NDX'].dropna(); spx=C['^GSPC'].dropna()
idx=ndx.index[ndx.index>='2006-01-01']
def on(s,lag_days=0):
    s=s.dropna().sort_index()
    if lag_days: s.index=s.index+pd.Timedelta(days=lag_days)
    s=s[~s.index.duplicated(keep='last')]
    out=s.reindex(s.index.union(idx)).ffill().reindex(idx)
    out[out.index>s.index.max()+pd.Timedelta(days=40)]=np.nan
    return out
def tpct(s,n=504,mp=250):   # trailing percentile of today's value within last n obs (no lookahead)
    return s.rolling(n,min_periods=mp).apply(lambda w:(w[:-1]<w[-1]).mean(),raw=True)
N=on(ndx); S=on(spx)
nearN=N/N.rolling(252,min_periods=200).max()-1>=-0.04
F=pd.DataFrame(index=idx)
def put(k,cond,valid):
    v=cond.astype(float); v[~valid]=np.nan; F[k]=v
# --- options
for nm,f in [('equity_pc','cboe_equitypc.csv'),('index_pc','cboe_indexpc.csv'),('total_pc','cboe_totalpc.csv')]:
    x=pd.read_csv(f,skiprows=2); x.columns=[c.strip() for c in x.columns]; x['DATE']=pd.to_datetime(x['DATE'])
    s=on(x.set_index('DATE')['P/C Ratio'].astype(float)); s10=s.rolling(10).mean(); p=tpct(s10)
    put(f'{nm}_low_10pct',p<0.10,p.notna()); put(f'{nm}_high_90pct',p>0.90,p.notna())
dx=pd.read_csv('squeeze_dix.csv',parse_dates=['date']).set_index('date')
gex=on(dx.gex); dix=on(dx.dix)
pg=tpct(gex); pdx=tpct(dix.rolling(5).mean())
put('gex_negative',gex<0,gex.notna()); put('gex_low_10pct',pg<0.10,pg.notna()); put('gex_high_90pct',pg>0.9,pg.notna())
put('dix_low_10pct',pdx<0.10,pdx.notna())
vix,vix3,skew,vvix=on(C['^VIX']),on(C['^VIX3M']),on(C['^SKEW']),on(C['^VVIX'])
ps=tpct(skew.rolling(5).mean()); put('skew_high_90pct',ps>0.9,ps.notna())
pts=tpct(vix/vix3); put('vix_term_high_90pct_at_high',(pts>0.9)&nearN,pts.notna())
put('vvix_high_vix_low',(tpct(vvix)>0.8)&(tpct(vix)<0.3),vvix.notna()&vix.notna())
put('vix_low_10pct',tpct(vix)<0.10,vix.notna())
# --- positioning (CFTC; Tuesday data released Friday -> lag 4 days)
cf=pd.read_pickle('cftc.pkl'); cf=cf.drop_duplicates(['code','date'])
def net(code,who):
    x=cf[cf.code==code].set_index('date').sort_index()
    return (x[f'{who}_Positions_Long_All']-x[f'{who}_Positions_Short_All'])/x['Open_Interest_All']
def pos_flag(code,who,hi=True,name=None):
    s=net(code,who); p=s.rolling(156,min_periods=78).apply(lambda w:(w[:-1]<w[-1]).mean(),raw=True)  # 3y weekly
    p=on(p,4); put(name,(p>0.9) if hi else (p<0.1),p.notna())
pos_flag('13874A','Asset_Mgr',True,'am_long_spx_crowded')
pos_flag('13874A','Lev_Money',True,'lev_long_spx_crowded')
pos_flag('209742','Asset_Mgr',True,'am_long_ndx_crowded')
pos_flag('209742','Lev_Money',True,'lev_long_ndx_crowded')
pos_flag('1170E1','Lev_Money',False,'lev_short_vix_crowded')
pos_flag('1170E1','Asset_Mgr',True,'am_long_vix_high')
# --- leverage
mg=pd.read_excel('finra_margin.xlsx').iloc[:,:2]; mg.columns=['ym','debt']; mg.index=pd.to_datetime(mg.ym)+pd.offsets.MonthEnd(1)+pd.Timedelta(days=20)
m=on(mg.debt.astype(float)); put('margin_up_30pct_yoy',m/m.shift(252)>1.3,m.shift(252).notna())
put('margin_yoy_top10pct',tpct(m/m.shift(252),756,400)>0.9,(m/m.shift(252)).notna())
# --- narrow leadership
qq,qe,rsp,spy=on(P['QQQ']),on(P['QQEW']),on(P['RSP']),on(P['SPY'])
put('narrow_ndx_63d',((qe/qq)/(qe/qq).shift(63)<0.97)&nearN,qe.shift(63).notna())
put('narrow_spx_63d',((rsp/spy)/(rsp/spy).shift(63)<0.97)&nearN,rsp.shift(63).notna())
# --- sentiment (CNN, 2021+)
import json
j=json.load(open('cnn_fg.json')); fg=pd.Series({pd.to_datetime(r['x'],unit='ms').normalize():r['y'] for r in j['fear_and_greed_historical']['data']})
fg=on(fg); put('cnn_greed_gt_75',fg>75,fg.notna())
F.to_pickle('F.pkl')
# --- events: NDX fast fall from near highs
a=N.values
def fmin(h):
    o=np.full(len(a),np.nan)
    for i in range(len(a)-h): o[i]=a[i+1:i+1+h].min()/a[i]-1
    return pd.Series(o,index=idx)
fm=fmin(15); E=(fm<=-0.08).astype(float); E[fm.isna()]=np.nan
nf=(E==1)&nearN
EV=[idx[i] for i in range(len(idx)) if nf.iloc[i] and (i<15 or not nf.iloc[i-15:i].any())]
pd.to_pickle((N,nearN,E,EV),'ev.pkl')
print('events',len(EV),[e.date() for e in EV]); print('base on near-high days',round(E[nearN].mean()*100,1),'%')
print(F.notna().sum().to_string())
