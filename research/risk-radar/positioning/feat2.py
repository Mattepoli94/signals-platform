import pandas as pd, numpy as np, json
exec(open('feat.py').read().split("# --- options")[0])   # loads P,C,ndx,idx,on,tpct,N,nearN,F,put
F=pd.read_pickle('F.pkl')          # previous flags (P/C pre-2019 versions will be replaced)
def cidx(s):
    x=pd.read_csv(f'cboe_idx_{s}.csv'); x.columns=[c.strip().upper() for c in x.columns]
    x['DATE']=pd.to_datetime(x['DATE']); col='CLOSE' if 'CLOSE' in x else x.columns[-1]
    return on(x.set_index('DATE')[col].astype(float))
cor1,cor3,dspx,vix,vix9,vvix,vxn,skew=[cidx(s) for s in ['COR1M','COR3M','DSPX','VIX','VIX9D','VVIX','VXN','SKEW']]
# continuous put/call: archive (to 2019-10-04) + daily json
j=json.load(open('cboe_daily.json'))
def series(name):
    return pd.Series({pd.Timestamp(d):float(next(r['value'] for r in v['ratios'] if r['name']==name)) for d,v in j.items() if any(r['name']==name for r in v['ratios'])})
pcs={}
for nm,f,jn in [('equity','cboe_equitypc.csv','EQUITY PUT/CALL RATIO'),('index','cboe_indexpc.csv','INDEX PUT/CALL RATIO'),('total','cboe_totalpc.csv','TOTAL PUT/CALL RATIO')]:
    x=pd.read_csv(f,skiprows=2); x.columns=[c.strip() for c in x.columns]; x['DATE']=pd.to_datetime(x['DATE'])
    a=x.set_index('DATE')['P/C Ratio'].astype(float); b=series(jn)
    s=pd.concat([a[a.index<b.index.min()],b]).sort_index(); pcs[nm]=on(s)
spxpc=on(series('SPX + SPXW PUT/CALL RATIO'))
G=pd.DataFrame(index=idx)
def put2(k,cond,valid): v=cond.astype(float); v[~valid]=np.nan; G[k]=v
for nm,s in pcs.items():
    p=tpct(s.rolling(10).mean()); put2(f'pc_{nm}_low',p<0.10,p.notna()); put2(f'pc_{nm}_high',p>0.90,p.notna())
p=tpct(spxpc.rolling(10).mean()); put2('pc_spx_low',p<0.10,p.notna()); put2('pc_spx_high',p>0.9,p.notna())
p=tpct(cor3.rolling(5).mean()); put2('impl_corr_low',p<0.10,p.notna())
p=tpct(cor1.rolling(5).mean()); put2('impl_corr1m_low',p<0.10,p.notna())
p=tpct(dspx.rolling(5).mean()); put2('dispersion_high',p>0.90,p.notna())
r=vvix/vix; p=tpct(r.rolling(5).mean()); put2('vvix_vix_ratio_high',p>0.90,p.notna())
r=vix9/vix; p=tpct(r.rolling(5).mean()); put2('vix9d_calm_low',p<0.10,p.notna())
r=vxn/vix; p=tpct(r.rolling(5).mean()); put2('nasdaq_vol_premium_high',p>0.90,p.notna())
for k in ['skew_high_90pct','gex_high_90pct','gex_low_10pct','dix_low_10pct','am_long_spx_crowded','lev_long_spx_crowded','am_long_ndx_crowded','lev_long_ndx_crowded',
          'lev_short_vix_crowded','margin_up_30pct_yoy','margin_yoy_top10pct','narrow_ndx_63d','narrow_spx_63d','vix_low_10pct']:
    G[k]=F[k]
# CFTC: leveraged funds crowded SHORT S&P (hedge funds short vs asset managers long = crowded basis)
cf=pd.read_pickle('cftc.pkl').drop_duplicates(['code','date'])
def net(code,who):
    x=cf[cf.code==code].set_index('date').sort_index(); return (x[f'{who}_Positions_Long_All']-x[f'{who}_Positions_Short_All'])/x['Open_Interest_All']
for code,nm in [('13874A','spx'),('209742','ndx')]:
    s=net(code,'Lev_Money'); p=s.rolling(156,min_periods=78).apply(lambda w:(w[:-1]<w[-1]).mean(),raw=True); p=on(p,4)
    put2(f'lev_short_{nm}_crowded',p<0.10,p.notna())
G.to_pickle('G.pkl'); print(G.notna().sum().to_string())
