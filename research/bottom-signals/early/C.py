import warnings; warnings.filterwarnings('ignore')
from bdata import *
b=C['BTC-USD'].dropna(); idx=b.index[b.index>='2015-06-01']; b=b.reindex(idx); bv=V['BTC-USD'].reindex(idx)
S=pd.DataFrame(index=idx); g=lambda k,x,v: S.__setitem__(k,x.astype(float).where(v))
r=rsi(b); s200=b.rolling(200).mean(); hi=b.rolling(365,min_periods=300).max(); dd=b/hi-1
g('rsi_lt_30',r<30,r.notna()); g('40pct_below_200d',b/s200<0.6,s200.notna()); g('drawdown_ge_60',dd<=-0.6,hi.notna())
g('week_drop_25pct',b/b.shift(7)<0.75,b.shift(7).notna())
va=bv.rolling(50).mean(); g('capitulation_volume',(bv>2*va)&(b.pct_change()<-0.07),va.notna())
fu=pd.read_csv('/home/claude/pos/deribit_funding.csv'); fu['t']=pd.to_datetime(fu.timestamp,unit='ms'); daily=fu.set_index('t').interest_1h.resample('D').sum()
ann=on(daily.rolling(7).mean()*365*100,idx,stale=4); g('funding_negative',ann<0,ann.notna()); g('funding_below_minus5',ann<-5,ann.notna())
cf=pd.read_pickle('/home/claude/pos/cftc.pkl').drop_duplicates(['code','date']); x=cf[cf.code=='133741'].set_index('date').sort_index()
am=on((x.Asset_Mgr_Positions_Long_All-x.Asset_Mgr_Positions_Short_All)/x.Open_Interest_All,idx,lag=pd.Timedelta(days=4),stale=21)
p=am.rolling(728,min_periods=200).apply(lambda w:(w[:-1]<w[-1]).mean(),raw=True); g('cme_am_long_low',p<0.1,p.notna())
lev=on((x.Lev_Money_Positions_Long_All-x.Lev_Money_Positions_Short_All)/x.Open_Interest_All,idx,lag=pd.Timedelta(days=4),stale=21)
p=lev.rolling(728,min_periods=200).apply(lambda w:(w[:-1]<w[-1]).mean(),raw=True); g('cme_lev_short_unwound',p>0.9,p.notna())
H=pd.to_datetime(['2012-11-28','2016-07-09','2020-05-11','2024-04-20']); 
days=pd.Series([(d-H[H<=d].max()).days for d in idx],index=idx)
g('cycle_day_850_1000',(days>=850)&(days<=1000),days.notna())
s50=b.rolling(50).mean(); g('reclaim_50d',(b>s50)&(b.shift(1)<=s50.shift(1))&(dd<=-0.3),s50.notna())
g('thrust_25pct_14d',(b/b.shift(14)>1.25)&(dd<=-0.3),b.shift(14).notna())
r30,m30=fwd(b,30); r90,_=fwd(b,90); r180,_=fwd(b,180)
state=dd<=-0.25
rows=[]
for k in S:
    sig=S[k]; rr={'sign':k}
    for pn,(a,c) in {'2015-20':(2015,2020),'2021-26':(2021,2026)}.items():
        mm=state&sig.notna()&r90.notna()&(idx.year>=a)&(idx.year<=c); o=sig[mm]==1
        if o.sum()>=5: rr[f'{pn} days']=int(o.sum()); rr[f'{pn} +90d']=round((r90[mm][o].mean()-r90[mm].mean())*100,1); rr[f'{pn} +180d']=round((r180[mm][o].mean()-r180[mm].mean())*100,1) if r180[mm][o].notna().sum()>3 else None; rr[f'{pn} fall15']=f"{(m30[mm][o]<=-0.15).mean()*100:.0f} vs {(m30[mm]<=-0.15).mean()*100:.0f}"
    rows.append(rr)
for pn,(a,c) in {'2015-20':(2015,2020),'2021-26':(2021,2026)}.items():
    mm=state&r90.notna()&(idx.year>=a)&(idx.year<=c); print(pn,'state days',mm.sum(),'avg 90d %.0f%%'%(r90[mm].mean()*100),'180d %.0f%%'%(r180[mm].mean()*100))
pd.set_option('display.width',250); print(pd.DataFrame(rows).set_index('sign').to_string())
S.to_pickle('SC.pkl'); print('\ntoday:',S.iloc[-1][S.iloc[-1]==1].index.tolist(),' drawdown from 1y high %.0f%%'%(dd.iloc[-1]*100),' cycle day',days.iloc[-1])
