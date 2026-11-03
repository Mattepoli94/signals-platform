import warnings; warnings.filterwarnings('ignore')
from bdata import *
ndx=C['^NDX'].dropna(); idx=ndx.index[ndx.index>='2006-01-01']; ndx=ndx.reindex(idx)
qvol=on(V['QQQ'],idx)
S=price_signs(ndx,qvol)
vix,vix3,vvix=on(C['^VIX'],idx),on(C['^VIX3M'],idx),on(C['^VVIX'],idx)
g=lambda k,x,v: S.__setitem__(k,x.astype(float).where(v))
g('vix_top5pct_2y',tpct(vix)>0.95,tpct(vix).notna()); g('vix_ge_30',vix>=30,vix.notna())
inv=(vix>vix3).astype(int).rolling(10).sum(); g('vix_term_normalises',(vix<vix3)&(inv.shift(1)>=3),vix3.notna())
g('vix_off_25pct_from_peak',(vix/vix.rolling(15).max()<0.75)&(vix.rolling(15).max()>25),vix.notna())
g('vvix_top5pct',tpct(vvix)>0.95,tpct(vvix).notna())
# options / positioning from /home/claude/pos
import json
j=json.load(open('/home/claude/pos/cboe_daily.json'))
def pcser(fn,name):
    x=pd.read_csv(fn,skiprows=2); x.columns=[c.strip() for c in x.columns]; x['DATE']=pd.to_datetime(x['DATE']); a=x.set_index('DATE')['P/C Ratio'].astype(float)
    b=pd.Series({pd.Timestamp(dd):float(next(r['value'] for r in v['ratios'] if r['name']==name)) for dd,v in j.items()})
    return on(pd.concat([a[a.index<b.index.min()],b]).sort_index(),idx,stale=10)
pct=pcser('/home/claude/pos/cboe_totalpc.csv','TOTAL PUT/CALL RATIO'); pce=pcser('/home/claude/pos/cboe_equitypc.csv','EQUITY PUT/CALL RATIO')
p=tpct(pct.rolling(5).mean()); g('pc_total_top10pct',p>0.9,p.notna())
p=tpct(pce.rolling(5).mean()); g('pc_equity_top10pct',p>0.9,p.notna())
dx=pd.read_csv('/home/claude/pos/squeeze_dix.csv',parse_dates=['date']).set_index('date')
dix,gex=on(dx.dix,idx,stale=10),on(dx.gex,idx,stale=10)
p=tpct(dix.rolling(5).mean()); g('dix_top10pct',p>0.9,p.notna())
g('gex_negative',gex<0,gex.notna())
g('gex_flips_positive',(gex>0)&(gex.rolling(10).min()<0),gex.notna())
cf=pd.read_pickle('/home/claude/pos/cftc.pkl').drop_duplicates(['code','date'])
def net(code,who):
    x=cf[cf.code==code].set_index('date').sort_index(); return (x[f'{who}_Positions_Long_All']-x[f'{who}_Positions_Short_All'])/x['Open_Interest_All']
for code,nm in [('13874A','spx'),('209742','ndx')]:
    for who,lab,lo in [('Asset_Mgr','am_long_low',True),('Lev_Money','lev_short_crowded',True)]:
        s=net(code,who); pp=s.rolling(156,min_periods=78).apply(lambda w:(w[:-1]<w[-1]).mean(),raw=True); pp=on(pp,idx,lag=pd.Timedelta(days=4),stale=21)
        g(f'{lab}_{nm}',pp<0.10,pp.notna())
s=net('1170E1','Lev_Money'); pp=s.rolling(156,min_periods=78).apply(lambda w:(w[:-1]<w[-1]).mean(),raw=True); pp=on(pp,idx,lag=pd.Timedelta(days=4),stale=21)
g('lev_vix_net_long_high',pp>0.9,pp.notna())
mg=pd.read_excel('/home/claude/pos/finra_margin.xlsx').iloc[:,:2]; mg.columns=['ym','debt']; mg.index=pd.to_datetime(mg.ym)+pd.offsets.MonthEnd(1)+pd.Timedelta(days=20)
m=on(mg.debt.astype(float),idx,stale=60); g('margin_down_15pct_yoy',m/m.shift(252)<0.85,m.shift(252).notna())
hyg,ief=on(P['HYG'],idx),on(P['IEF'],idx); cr=hyg/ief; g('credit_rebound_1pct_5d',cr/cr.shift(5)>1.01,hyg.shift(5).notna())
qq,qe=on(P['QQQ'],idx),on(P['QQEW'],idx); g('breadth_broadening',(qe/qq)/(qe/qq).shift(10)>1.02,qe.shift(10).notna())
fg=json.load(open('/home/claude/pos/cnn_fg.json')); fgs=pd.Series({pd.to_datetime(r['x'],unit='ms').normalize():r['y'] for r in fg['fear_and_greed_historical']['data']})
fgs=on(fgs,idx,stale=5); g('cnn_extreme_fear_lt_20',fgs<20,fgs.notna())
S.to_pickle('SB.pkl')
hi=ndx.rolling(252,min_periods=200).max(); dd=ndx/hi-1; state=dd<=-0.08
r21,m21=fwd(ndx,21); r63,m63=fwd(ndx,63)
N,nearN,E,EV=pd.read_pickle('/home/claude/pos/ev.pkl')
TR=[ndx.loc[e:].iloc[:41].idxmin() for e in EV]
pd.to_pickle((ndx,state,dd,r21,m21,r63,m63,TR),'B_out.pkl'); print('troughs',[t.date() for t in TR])
