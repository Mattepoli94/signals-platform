import pandas as pd, numpy as np
from ind import P
SP=pd.read_pickle('SP.pkl'); O=pd.read_pickle('O.pkl')
d=SP[['move_gt_120','vix_term_inverted','vvix_gt_100','credit_weak_3pct_63d','dollar_up_5pct_6m']].copy()
d['W3']=O['W3_two_below200'].reindex(d.index)
s=d.sum(1,min_count=6).dropna(); s=s[s.index>='2007-02-01']
n=P['^NDX'].reindex(s.index).ffill(); a=n.values
dd1y=n/n.rolling(252,min_periods=1).max()-1
def fwd(h):
    r=np.full(len(a),np.nan); m=np.full(len(a),np.nan)
    for i in range(len(a)-h): r[i]=a[i+h]/a[i]-1; m[i]=a[i+1:i+1+h].min()/a[i]-1
    return pd.Series(r,index=n.index),pd.Series(m,index=n.index)
F={h:fwd(h) for h in (10,21,63,126)}
red=s>=3
# episode starts: first red day after 20+ sessions not red
starts=[i for i in range(len(red)) if red.iloc[i] and not red.iloc[max(0,i-20):i].any()]
rows=[]
for i in starts:
    dt=n.index[i]; row=dict(date=dt.date(),ndx_off_high=round(dd1y.iloc[i]*100,1))
    for h in (10,21,63,126):
        r,m=F[h]; row[f'ret{h}']=round(r.iloc[i]*100,1); row[f'worst{h}']=round(m.iloc[i]*100,1)
    rows.append(row)
E=pd.DataFrame(rows); pd.set_option('display.width',250); print(E.to_string(index=False))
print('\nmedians of episodes:'); print(E.drop(columns=['date']).median().round(1).to_string())
def summ(mask,label):
    out=[label,f'n days {mask.sum()}']
    for h in (21,63):
        r,m=F[h]; out.append(f'{h}d: avg ret {r[mask].mean()*100:.1f}% , P(further fall>=10%) {(m[mask]<=-0.10).mean()*100:.0f}% , avg worst {m[mask].mean()*100:.1f}%')
    print(' | '.join(out))
summ(pd.Series(True,index=s.index),'ALL DAYS')
summ(red,'RED')
summ(red&(dd1y<=-0.07)&(dd1y>=-0.15),'RED & NDX 7-15% off high (like now)')
summ((~red)&(dd1y<=-0.07)&(dd1y>=-0.15),'NOT red & NDX 7-15% off high')
