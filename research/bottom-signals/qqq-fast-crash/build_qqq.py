from feat import *
c=C['^NDX'].dropna(); c=c[c.index>='2004-01-01']; idx=c.index
v=on(V['QQQ'],idx)
X=price_feats(c,v).join(market_feats(idx))
X.to_pickle('X_qqq.pkl'); W=windows(c); print('windows since 2007:',[c.index[i].date() for i in W if c.index[i].year>=2007], len([i for i in W if c.index[i].year>=2007]))
pd.to_pickle((c,W),'cw_qqq.pkl')
print(X.iloc[-1].round(3).to_string())
