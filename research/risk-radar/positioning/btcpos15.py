import pandas as pd, numpy as np
d=pd.read_csv('/home/claude/risk/prices.csv',parse_dates=['date']); b=d[d.ticker=='BTC-USD'].set_index('date')['close'].sort_index()
idx=b.index[b.index>='2019-06-01']; b=b.reindex(idx)
fu=pd.read_csv('deribit_funding.csv'); fu['t']=pd.to_datetime(fu.timestamp,unit='ms'); 
daily=fu.set_index('t').interest_1h.resample('D').sum()      # daily funding (fraction)
ann=daily.rolling(7).mean()*365*100                           # 7d avg annualised %
ann=ann.reindex(idx).ffill()
p=ann.rolling(365,min_periods=180).apply(lambda w:(w[:-1]<w[-1]).mean(),raw=True)
cf=pd.read_pickle('cftc.pkl'); cf=cf.drop_duplicates(['code','date'])
x=cf[cf.code=='133741'].set_index('date').sort_index()
def onw(s): s=s.copy(); s.index=s.index+pd.Timedelta(days=4); return s.reindex(s.index.union(idx)).ffill().reindex(idx)
am=onw((x.Asset_Mgr_Positions_Long_All-x.Asset_Mgr_Positions_Short_All)/x.Open_Interest_All)
lev=onw((x.Lev_Money_Positions_Long_All-x.Lev_Money_Positions_Short_All)/x.Open_Interest_All)
oi=onw(x.Open_Interest_All.astype(float))
tp=lambda s,n=104: s.rolling(n*7,min_periods=200).apply(lambda w:(w[:-1]<w[-1]).mean(),raw=True)
F=pd.DataFrame(index=idx)
F['funding_gt_20pct']=(ann>20).astype(float); F['funding_gt_30pct']=(ann>30).astype(float)
F['funding_top10pct_1y']=(p>0.9).astype(float).where(p.notna())
F['funding_negative']=(ann<0).astype(float)
F['cme_am_long_crowded']=(tp(am)>0.9).astype(float).where(am.notna())
F['cme_lev_short_crowded']=(tp(lev)<0.1).astype(float).where(lev.notna())
F['cme_oi_up_50pct_3m']=((oi/oi.shift(91))>1.5).astype(float).where(oi.shift(91).notna())
F['btc_up_40pct_30d']=(b/b.shift(30)>1.4).astype(float)
a=b.values; fm=np.full(len(a),np.nan)
for i in range(len(a)-10): fm[i]=a[i+1:i+11].min()/a[i]-1
E=pd.Series((fm<=-0.15).astype(float),index=idx); E[np.isnan(fm)]=np.nan
near=b/b.rolling(60).max()-1>=-0.10
ii={d:i for i,d in enumerate(idx)}; nf=(E==1)&near
EV=[idx[i] for i in range(len(idx)) if nf.iloc[i] and (i<10 or not nf.iloc[i-10:i].any())]
print('BTC events',[e.date() for e in EV],' base %.1f%%'%(E[near].mean()*100))
rows=[]
for k in F:
    for pn,(a_,b_) in {'2019-22':(2019,2022),'2023-26':(2023,2026),'all':(2019,2026)}.items():
        m=(idx.year>=a_)&(idx.year<=b_)&near&F[k].notna()&E.notna(); s=F[k][m]==1; y=E[m]==1
        ev=[e for e in EV if a_<=e.year<=b_ and pd.notna(F[k].loc[e])]
        hit=sum((F[k].iloc[max(0,ii[e]-10):ii[e]+1]==1).any() for e in ev)
        rows.append(dict(flag=k,per=pn,on=s.mean()*100,lift=(y[s].mean()/y.mean()) if s.sum()>=15 else np.nan,caught=f'{hit}/{len(ev)}'))
R=pd.DataFrame(rows); pd.set_option('display.width',250)
print(R.pivot(index='flag',columns='per',values=['on','lift','caught']).round(2).to_string())
print('\nfunding (7d avg annualised %) before events:'); [print(e.date(), round(ann.loc[e],1), ' max prior 10d', round(ann.iloc[max(0,ii[e]-10):ii[e]+1].max(),1)) for e in EV]
print('today funding',round(ann.iloc[-1],1),'  pct 1y',round(p.iloc[-1],2))
