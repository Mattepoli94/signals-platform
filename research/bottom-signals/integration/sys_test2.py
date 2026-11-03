exec(open('sys_test.py').read().split("P={")[0])
P={'1999-2026':('1999-06-01','2026-12-31'),'2007-15':('2007-01-01','2015-12-31'),'2016-26':('2016-01-01','2026-12-31')}
a=qa.values
def overlay2(H=126,stop=None,use_wash=False,HW=126,wstop=None,f1=0.5):
    fl=pd.Series(0.0,index=idx); pos=lambda d: idx.get_loc(d)
    events=[]
    for p in plans:
        if p['buy1'] is None or p['skipped']: continue
        i=pos(p['buy1']); j=pos(p['buy2']) if p['buy2'] is not None else None
        events.append((i,j,H,stop,f1))
    if use_wash:
        for d in WS: events.append((pos(d),None,HW,wstop,1.0))
    for i,j,h,st,f in events:
        end=min(i+h,len(idx)); 
        for k in range(i,end):
            size=f if (j is None or k<j) else 1.0
            entry=a[i] if (j is None or k<j) else 2/(1/a[i]+1/a[j])
            if st is not None and a[k]<=entry*(1-st): break
            fl.iloc[k]=max(fl.iloc[k],size)
    return np.maximum(w0,fl)
rows=[]
def add(name,w):
    ret=backtest(w); rows.append({'variant':name,**{k:stats(ret,*v) for k,v in P.items()},'invested':f"{w['2007':].mean()*100:.0f}%"})
    return ret
add('Current QQQ system',w0)
for H in (63,126):
    for st in (None,0.08,0.10,0.15):
        add(f'+ fast-crash, hold {H}, stop {st}',overlay2(H,st))
for st in (0.08,0.10,0.15):
    add(f'+ fast (126, stop 10%) + washout hold 126 with stop {st}',overlay2(126,0.10,True,126,st))
pd.set_option('display.width',250); print(pd.DataFrame(rows).to_string(index=False))
# where is the worst drawdown of the fast overlay?
ret=backtest(overlay2(126,None)); eq=(1+ret['2016':]).cumprod(); dd=eq/eq.cummax()-1; t_=dd.idxmin(); pk=eq[:t_].idxmax(); print('worst dd fast 126 (2016+):',pk.date(),t_.date(),round(dd.min()*100,1))
ret=backtest(overlay2(126,0.10)); eq=(1+ret['1999-06':]).cumprod(); dd=eq/eq.cummax()-1; t_=dd.idxmin(); pk=eq[:t_].idxmax(); print('worst dd fast 126 stop10 (1999+):',pk.date(),t_.date(),round(dd.min()*100,1))
