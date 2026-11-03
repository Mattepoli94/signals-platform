from bdata import *
spx=C['^GSPC'].dropna(); idx=spx.index[spx.index>='1953-01-01']; spx=spx.reindex(idx); vol=V['^GSPC'].reindex(idx)
S=price_signs(spx,vol.where(idx>='1962-01-01'))
vix=on(C['^VIX'],idx); vix3=on(C['^VIX3M'],idx); tnx,irx,dxy=on(C['^TNX'],idx),on(C['^IRX'],idx),on(C['DX-Y.NYB'],idx)
g=lambda k,x,v: S.__setitem__(k,x.astype(float).where(v))
g('vix_ge_40',vix>=40,vix.notna()); g('vix_top5pct_2y',tpct(vix)>0.95,tpct(vix).notna())
inv=(vix>vix3).astype(int).rolling(10).sum()
g('vix_term_normalises',(vix<vix3)&(inv.shift(1)>=5),vix3.notna())
g('vix_off_30pct_from_peak',(vix/vix.rolling(20).max()<0.7)&(vix.rolling(20).max()>30),vix.notna())
g('fed_cut_1pt_6m',(irx-irx.shift(126))<-1.0,irx.shift(126).notna())
sp=tnx-irx; g('curve_steepen_1pt_6m',(sp-sp.shift(126))>1.0,irx.shift(126).notna())
g('dollar_down_3pct_3m',dxy/dxy.shift(63)<0.97,dxy.shift(63).notna())
# credit (Vanguard HY vs long Treasuries, 1986+)
hy,lt=on(P['VWEHX'],idx),on(P['VUSTX'],idx); cr=hy/lt
g('credit_rebound_2pct_10d',cr/cr.shift(10)>1.02,lt.shift(10).notna())
# valuation and leverage
exec(open('/home/claude/lead/base.py').read().split("def on(s)")[0].split("spx=C['^GSPC']")[0].replace("d=pd.read_csv('prices.csv'","d=pd.read_csv('/home/claude/lead/prices.csv'")) if False else None
import sys; sys.path.insert(0,'/home/claude/lead'); import os; cwd=os.getcwd(); os.chdir('/home/claude/lead'); import base as LB; os.chdir(cwd)
cape=on(LB.sh.cape,idx,stale=60); cp=cape.expanding(min_periods=2000).rank(pct=True)
g('cape_below_median',cp<0.5,cp.notna())
marg=on(LB.mg,idx,stale=60); g('margin_down_15pct_yoy',marg/marg.shift(252)<0.85,marg.shift(252).notna())
S.to_pickle('SA.pkl')
# state + outcomes
hi=spx.rolling(252,min_periods=200).max(); dd=spx/hi-1; state=dd<=-0.15
r126,m126=fwd(spx,126); r252,_=fwd(spx,252)
# troughs from peaks
PK=LB.PK; TR=[]
for p in PK:
    seg=spx.loc[p:]; rec=seg[seg>=spx.loc[p]]; end=rec.index[1] if len(rec)>1 else seg.index[-1]
    TR.append(spx.loc[p:end].idxmin())
pd.to_pickle((spx,state,dd,r126,m126,r252,TR),'A_out.pkl')
print('troughs',[t.date() for t in TR])
