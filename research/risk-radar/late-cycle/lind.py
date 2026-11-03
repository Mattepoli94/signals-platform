from base import *
f=on
tnx,irx,dxy,vix=f(C['^TNX']),f(C['^IRX']),f(C['DX-Y.NYB']),f(C['^VIX'])
rut,djt=f(C['^RUT']),f(C['^DJT']); hy,lt=f(P['VWEHX']),f(P['VUSTX']); xlp,xly=f(P['XLP']),f(P['XLY'])
rsp,spy=f(P['RSP']) if 'RSP' in P else None, None
cape,cpi,gs10=f(sh.cape),f(sh.cpi),f(sh.gs10); marg=f(mg)
infl=(cpi/cpi.shift(252)-1)*100
hi=lambda s,n=252: s/s.rolling(n,min_periods=int(n*0.8)).max()-1
nearhi=hi(spx)>=-0.05; at2=hi(spx)>=-0.02
L=pd.DataFrame(index=idx)
def put(k,cond,*req):
    v=cond.astype(float)
    for r in req: v[r.isna()]=np.nan
    L[k]=v
sp=tnx-irx
put('curve_inv_last18m',(sp<0).astype(float).rolling(378,min_periods=1).max()>0,irx.shift(378))
put('curve_inverted_now',sp<0,irx)
put('curve_flat_lt_0.5',sp<0.5,irx)
put('fed_hiking_1.5pt_12m',(irx-irx.shift(252))>1.5,irx.shift(252))
put('fed_hiking_1pt_6m',(irx-irx.shift(126))>1.0,irx.shift(126))
put('10y_up_1.5pt_12m',(tnx-tnx.shift(252))>1.5,tnx.shift(252))
put('real_tbill_gt_2',(irx-infl)>2,infl,irx)
put('inflation_gt4_rising',(infl>4)&(infl>infl.shift(126)),infl.shift(126))
put('cape_gt_30',cape>30,cape)
pct=cape.expanding(min_periods=2000).rank(pct=True)
put('cape_top10pct_to_date',pct>0.9,pct)
put('earn_yield_below_10y',(100/cape)<gs10,cape,gs10)
put('spx_up_25pct_12m',spx/spx.shift(252)>1.25,spx.shift(252))
put('spx_12pct_above_200d',spx/spx.rolling(200).mean()>1.12,spx.shift(200))
put('spx_up_50pct_24m',spx/spx.shift(504)>1.5,spx.shift(504))
put('momentum_fading',(spx/spx.shift(252)>1.15)&(spx/spx.shift(63)<1.02),spx.shift(252))
put('smallcaps_lag_at_high',((rut/spx)/(rut/spx).shift(126)<0.95)&nearhi,rut.shift(126))
put('transports_nonconfirm',at2&(hi(djt)<-0.08),djt.shift(252))
put('credit_lag_at_high',((hy/lt)/(hy/lt).shift(126)<0.97)&nearhi,lt.shift(126))
put('defensives_lead_6m',(xlp/xly)/(xlp/xly).shift(126)>1.05,xly.shift(126))
put('vix_rising_at_high',(vix.rolling(21).mean()>1.2*vix.rolling(126).mean())&nearhi,vix.shift(126))
put('vix_lt_12',vix<12,vix)
put('margin_up_30pct_yoy',marg/marg.shift(252)>1.30,marg.shift(252))
put('margin_off_5pct_from_high_at_high',(hi(marg)<-0.05)&nearhi,marg.shift(252))
put('dollar_up_10pct_12m',dxy/dxy.shift(252)>1.10,dxy.shift(252))
L.to_pickle('L.pkl')
