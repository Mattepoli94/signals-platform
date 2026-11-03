import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
exec(open('evalA.py').read().split("if __name__")[0])
X=pd.DataFrame(index=idx)
# washout family (deep/fear) and turn family (confirmation)
X['washout_now']=S[['drawdown_ge_30','20pct_below_200d','vix_ge_40']].max(axis=1)
X['washout_63d']=X['washout_now'].rolling(63,min_periods=1).max()
X['washout_126d']=X['washout_now'].rolling(126,min_periods=1).max()
X['turn']=S[['thrust_7pct_10d','20d_high_in_drawdown']].max(axis=1)
X['turn_credit']=S[['thrust_7pct_10d','20d_high_in_drawdown','credit_rebound_2pct_10d']].max(axis=1)
X['thrust_only']=S['thrust_7pct_10d']
X['turn_after_washout']=((X['turn']==1)&(X['washout_126d']==1)).astype(float).where(X['turn'].notna())
X['thrust_after_washout']=((S['thrust_7pct_10d']==1)&(X['washout_126d']==1)).astype(float).where(S['thrust_7pct_10d'].notna())
X['thrust_10d_window']=S['thrust_7pct_10d'].rolling(10,min_periods=1).max()      # signal stays valid 10 sessions
X['thrust_after_washout_10d']=((X['thrust_10d_window']==1)&(X['washout_126d']==1)).astype(float)
pd.set_option('display.width',250)
rows=[]
for k in X:
    r={'rule':k}
    for pn,(a,b) in PER.items():
        x=score(X[k],a,b)
        if x: r.update({f'{pn} days':x['days'],f'{pn} +6m':round(x['ex126'],1),f'{pn} +12m':round(x['ex252'],1),f'{pn} win12m':round(x['win252']),f'{pn} fall%':round(x['fall']),f'{pn} caught':x['caught']})
    rows.append(r)
print(pd.DataFrame(rows).set_index('rule').to_string())
X.to_pickle('XA.pkl')
# per trough: first thrust-after-washout date and price vs trough
print('\nper bear market: first "thrust after washout" signal after the trough, and its price vs the trough low')
for t in TR:
    w=X['thrust_after_washout'].loc[t-pd.Timedelta(days=200):t+pd.Timedelta(days=400)]
    w=w[w==1]
    if len(w): d0=w.index[0]; print(t.date(),'signal',d0.date(),f'{(spx.loc[d0]/spx.loc[t]-1)*100:+.1f}% above low', f'then +12m {r252.loc[d0]*100 if pd.notna(r252.loc[d0]) else float("nan"):+.0f}%')
    else: print(t.date(),'no signal')
