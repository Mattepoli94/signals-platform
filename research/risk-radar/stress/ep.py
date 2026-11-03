import pandas as pd, numpy as np
d=pd.read_csv('prices.csv',parse_dates=['date'])
P=d.pivot(index='date',columns='ticker',values='adj_close').sort_index()
def episodes(c,th):
    c=c.dropna(); a=c.values; idx=c.index; out=[]; pk=0; inep=False
    for t in range(len(a)):
        if a[t]>=a[pk]:
            if inep:
                tr=pk0+np.argmin(a[pk0:t]); out.append((idx[pk0],x10,idx[tr],a[tr]/a[pk0]-1)); inep=False
            pk=t
        elif not inep and a[t]/a[pk]-1<=th:
            inep=True; pk0=pk; x10=idx[pk0+np.argmax(a[pk0:t+1]/a[pk0]-1<=th*2/3)]
    if inep: tr=pk0+np.argmin(a[pk0:]); out.append((idx[pk0],x10,idx[tr],a[tr]/a[pk0]-1))
    return pd.DataFrame(out,columns=['peak','alert','trough','depth'])
if __name__=='__main__':
    for n,th in [('^NDX',-.15),('BTC-USD',-.30)]:
        e=episodes(P[n],th); e['days_to_alert']=(e.alert-e.peak).dt.days; print(n); print(e.to_string())
