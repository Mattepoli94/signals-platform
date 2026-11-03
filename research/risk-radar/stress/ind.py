import pandas as pd, numpy as np
d=pd.read_csv('prices.csv',parse_dates=['date'])
P=d.pivot(index='date',columns='ticker',values='adj_close').sort_index()
C=d.pivot(index='date',columns='ticker',values='close').sort_index()
def us_index():
    return P['^NDX'].dropna().index
def build(idx):
    f=lambda s: s.dropna().reindex(s.dropna().index.union(idx)).ffill().reindex(idx)
    ndx,spx=f(P['^NDX']),f(P['^GSPC'])
    vix,vix3,vvix,skew,move=f(C['^VIX']),f(C['^VIX3M']),f(C['^VVIX']),f(C['^SKEW']),f(C['^MOVE'])
    tnx,irx=f(C['^TNX']),f(C['^IRX']); dxy=f(C['DX-Y.NYB']); jpy=f(C['JPY=X']); oil=f(C['CL=F'])
    hyg,ief=f(P['HYG']),f(P['IEF']); rsp,spy=f(P['RSP']),f(P['SPY']); qqew,qqq=f(P['QQEW']),f(P['QQQ'])
    iwm=f(P['IWM']); xlp,xly=f(P['XLP']),f(P['XLY']); cu,au=f(C['HG=F']),f(C['GC=F'])
    I=pd.DataFrame(index=idx)
    hi52=lambda s: s/s.rolling(252,min_periods=200).max()-1
    near_high=hi52(spx)>-0.03
    # rates / macro
    I['curve_inverted']=(tnx-irx)<0
    inv=((tnx-irx)<0).astype(float)
    I['curve_resteepen']=(inv.rolling(252,min_periods=1).max()>0)&((tnx-irx)>0)   # un-inverted after inversion in last year
    I['tbill_up_0.5_6m']=(irx-irx.shift(126))>0.5
    I['10y_up_1pt_6m']=(tnx-tnx.shift(126))>1.0
    I['dollar_up_5pct_6m']=dxy/dxy.shift(126)-1>0.05
    I['yen_jump_5pct_10d']=(jpy/jpy.shift(10)-1)<-0.05
    I['oil_up_50pct_6m']=oil/oil.shift(126)-1>0.5
    I['copper_gold_down_15pct_6m']=((cu/au)/(cu/au).shift(126)-1)<-0.15
    # credit
    hr=hyg/ief; I['credit_weak_3pct_63d']=(hr/hr.rolling(63).max()-1)<-0.03
    I['credit_weak_at_high']=I['credit_weak_3pct_63d']&near_high
    # volatility
    I['vix_lt_13']=vix<13
    I['vix_low_pctl10_1y']=vix<vix.rolling(252).quantile(0.10)
    I['vix_rising_at_high']=(vix/vix.rolling(21).min()-1>0.4)&near_high
    I['vix_term_inverted']=vix>vix3
    I['vvix_gt_110_vix_lt_16']=(vvix>110)&(vix<16)
    I['skew_gt_145']=skew>145
    I['move_gt_120']=move>120
    # breadth / internals
    I['narrow_spx_rsp_at_high']=((rsp/spy)/(rsp/spy).shift(63)-1<-0.03)&near_high
    I['narrow_ndx_eq_at_high']=((qqew/qqq)/(qqew/qqq).shift(63)-1<-0.03)&(hi52(ndx)>-0.03)
    I['smallcaps_below200_at_high']=(iwm<iwm.rolling(200).mean())&near_high
    I['defensives_lead_5pct_63d']=((xlp/xly)/(xlp/xly).shift(63)-1>0.05)
    # extension / euphoria (price)
    I['ndx_25pct_above_200d']=ndx/ndx.rolling(200).mean()>1.25
    I['ndx_up_50pct_12m']=ndx/ndx.shift(252)>1.5
    rv=np.log(ndx).diff().rolling(21).std()*np.sqrt(252)
    I['realvol_low_10pctl']=rv<rv.rolling(756,min_periods=252).quantile(0.10)
    I['ndx_below_200d']=ndx<ndx.rolling(200).mean()
    # existing platform flag
    I['platform_risk_red']=(I['tbill_up_0.5_6m'].astype(int)+I['dollar_up_5pct_6m'].astype(int)+
        ((f(P['QQQ'])<f(P['QQQ']).rolling(200).mean()).astype(int)+(f(P['TLT'])<f(P['TLT']).rolling(200).mean()).astype(int)+(f(P['GC=F'] if 'GC=F' in P else C['GC=F'])<f(C['GC=F']).rolling(200).mean()).astype(int)>=2).astype(int))>=2
    # mark data availability: NaN where inputs missing
    avail={'curve':tnx,'vix':vix}
    need={'vix_term_inverted':vix3,'vvix_gt_110_vix_lt_16':vvix,'skew_gt_145':skew,'move_gt_120':move,'credit_weak_3pct_63d':hr.shift(63),
          'credit_weak_at_high':hr.shift(63),'narrow_spx_rsp_at_high':rsp.shift(63),'narrow_ndx_eq_at_high':qqew.shift(63),'smallcaps_below200_at_high':iwm.shift(200),
          'defensives_lead_5pct_63d':xlp.shift(63),'oil_up_50pct_6m':oil.shift(126),'copper_gold_down_15pct_6m':cu.shift(126),'yen_jump_5pct_10d':jpy.shift(10),
          'vix_lt_13':vix,'vix_low_pctl10_1y':vix.shift(252),'vix_rising_at_high':vix.shift(21),'platform_risk_red':P['TLT'].reindex(idx).shift(200)}
    I=I.astype(float)
    for k,s in need.items(): I.loc[s.isna(),k]=np.nan
    return I
