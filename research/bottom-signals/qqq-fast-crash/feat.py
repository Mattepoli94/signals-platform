import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
d=pd.concat([pd.read_csv('/home/claude/lead/prices.csv',parse_dates=['date']),pd.read_csv('/home/claude/risk/prices.csv',parse_dates=['date'])]).drop_duplicates(['ticker','date'],keep='last')
P=d.pivot(index='date',columns='ticker',values='adj_close').sort_index(); C=d.pivot(index='date',columns='ticker',values='close').sort_index(); V=d.pivot(index='date',columns='ticker',values='volume').sort_index()
POS='/home/claude/pos/'
def on(s,idx,lag=None,stale=None):
    s=s.dropna().sort_index()
    if lag is not None: s.index=s.index+lag
    s=s[~s.index.duplicated(keep='last')]; o=s.reindex(s.index.union(idx)).ffill().reindex(idx)
    if stale and len(s): o[o.index>s.index.max()+pd.Timedelta(days=stale)]=np.nan
    return o
def tp(s,n=252,mp=120): return s.rolling(n,min_periods=mp).apply(lambda w:(w[:-1]<w[-1]).mean(),raw=True)
def cidx(sym,idx):
    x=pd.read_csv(f'{POS}cboe_idx_{sym}.csv'); x.columns=[c.strip().upper() for c in x.columns]; x['DATE']=pd.to_datetime(x['DATE'])
    return on(x.set_index('DATE')['CLOSE' if 'CLOSE' in x else x.columns[-1]].astype(float),idx,stale=10)
def market_feats(idx):
    """Market-wide options/positioning features (same for any tech index)."""
    M=pd.DataFrame(index=idx)
    vix,vix9,vxn=cidx('VIX',idx),cidx('VIX9D',idx),cidx('VXN',idx)
    M['vxn']=vxn; M['vxn_pct']=tp(vxn); M['vix9_ratio']=vix9/vix; M['vix']=vix
    j=json.load(open(f'{POS}cboe_daily.json'))
    def pcs(fn,name):
        x=pd.read_csv(f'{POS}{fn}',skiprows=2); x.columns=[c.strip() for c in x.columns]; x['DATE']=pd.to_datetime(x['DATE']); a=x.set_index('DATE')['P/C Ratio'].astype(float)
        b=pd.Series({pd.Timestamp(k):float(next(r['value'] for r in v['ratios'] if r['name']==name)) for k,v in j.items()})
        return on(pd.concat([a[a.index<b.index.min()],b]).sort_index(),idx,stale=10)
    M['pce_pct']=tp(pcs('cboe_equitypc.csv','EQUITY PUT/CALL RATIO').rolling(5).mean())
    M['pct_pct']=tp(pcs('cboe_totalpc.csv','TOTAL PUT/CALL RATIO').rolling(5).mean())
    dx=pd.read_csv(f'{POS}squeeze_dix.csv',parse_dates=['date']).set_index('date')
    M['gex']=on(dx.gex,idx,stale=10); M['dix_pct']=tp(on(dx.dix,idx,stale=10).rolling(5).mean())
    cf=pd.read_pickle(f'{POS}cftc.pkl').drop_duplicates(['code','date'])
    x=cf[cf.code=='209742'].set_index('date').sort_index(); am=(x.Asset_Mgr_Positions_Long_All-x.Asset_Mgr_Positions_Short_All)/x.Open_Interest_All
    lv=(x.Lev_Money_Positions_Long_All-x.Lev_Money_Positions_Short_All)/x.Open_Interest_All
    q=lambda s: on(s.rolling(156,min_periods=78).apply(lambda w:(w[:-1]<w[-1]).mean(),raw=True),idx,lag=pd.Timedelta(days=4),stale=21)
    M['am_ndx_pct']=q(am); M['lev_ndx_pct']=q(lv)
    return M
def price_feats(c,v):
    F=pd.DataFrame(index=c.index); r=np.log(c).diff(); sig=r.rolling(252,min_periods=120).std()
    F['z15']=np.log(c/c.shift(15))/(sig*np.sqrt(15)); F['z5']=np.log(c/c.shift(5))/(sig*np.sqrt(5))
    hi=c.rolling(252,min_periods=200).max(); F['dd']=c/hi-1; F['dd_z']=np.log(c/hi)/(sig*np.sqrt(20))
    va=v.rolling(50).mean(); F['volx']=v/va; F['ret']=c.pct_change()
    F['capit3']=((F.volx>=1.8)&(F.ret<=-0.02)).astype(float).rolling(3,min_periods=1).max().where(va.notna())
    dd_=c.diff(); up=dd_.clip(lower=0).ewm(alpha=1/14,adjust=False).mean(); dn=(-dd_.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean(); F['rsi14']=100-100/(1+up/dn)
    up2=dd_.clip(lower=0).ewm(alpha=1/2,adjust=False).mean(); dn2=(-dd_.clip(upper=0)).ewm(alpha=1/2,adjust=False).mean(); F['rsi2']=100-100/(1+up2/dn2)
    return F
def windows(c,fall=0.08,n=15,near=0.04,win=40):
    a=c.values; hi=c.rolling(252,min_periods=200).max().values; out=[]; i=0
    while i<len(a)-n:
        if hi[i]==hi[i] and a[i]/hi[i]-1>=-near and a[i+1:i+1+n].min()/a[i]-1<=-fall: out.append(i); i+=win
        else: i+=1
    return out
