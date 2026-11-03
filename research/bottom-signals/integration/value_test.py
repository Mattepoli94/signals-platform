exec(open('sys_test.py').read().split("s=get('qqq_regime')")[0])
from signals.strategies import get
df=pd.read_csv('/home/claude/signals-platform/data/prices/QQQ.csv',parse_dates=['date']).set_index('date')
Z=get('qqq_value').compute_us({'QQQ':df}).reindex(idx)
zone=Z['zone'].fillna(False).values
a=qa.values; n=len(a)
irx=_price('IRX','close').reindex(idx).ffill().fillna(0).values/100
first=np.r_[True,idx.month[1:]!=idx.month[:-1]]
b1=np.zeros(n,bool); b2=np.zeros(n,bool); wo=np.zeros(n,bool)
for p in plans:
    if p['buy1'] is not None and not p['skipped']:
        b1[idx.get_loc(p['buy1'])]=True
        if p['buy2'] is not None: b2[idx.get_loc(p['buy2'])]=True
for d in WS: wo[idx.get_loc(d)]=True
def sim(s,e,mode,C=1000.0,cap=24):
    cash=units=dep=0.0; last=-999; eqs=[]; deps=[]
    for i in range(s,e):
        cash*= (1+irx[i])**(1/252)
        if first[i]: cash+=C; dep+=C
        amt=0.0
        if mode=='dca': amt=cash
        else:
            if 'zones' in mode and zone[i] and i-last>=10: amt=cash*0.5; last=i
            if 'fast' in mode and b1[i]: amt=max(amt,cash*0.5)
            if 'fast' in mode and b2[i]: amt=cash
            if 'wash' in mode and wo[i]: amt=cash
            if first[i] and cash-amt>cap*C: amt=cash-cap*C
        units+=amt/a[i]; cash-=amt
        eqs.append(units*a[i]+cash); deps.append(dep)
    eq=np.array(eqs); dp=np.array(deps)
    return eq[-1], (eq/np.maximum.accumulate(eq)-1).min(), (eq/dp-1).min()
modes={'Monthly DCA':'dca','Value plan now (zones)':'zones','Zones + fast-crash buys':'zones+fast','Zones + fast + washout':'zones+fast+wash','Fast + washout only (no zones)':'fast+wash'}
starts=[i for i in range(n) if first[i] and idx[i]>=pd.Timestamp('2000-01-01') and i+2520<n]
res={m:[] for m in modes}
for s in starts:
    for m,code in modes.items(): res[m].append((idx[s],)+sim(s,s+2520,code))
rows=[]
for m in modes:
    D=pd.DataFrame(res[m],columns=['start','w','dd','below']); Dd=pd.DataFrame(res['Monthly DCA'],columns=['start','w','dd','below'])
    rel=D.w/Dd.w-1
    for era,msk in [('starts 2000-08',D.start.dt.year<=2008),('starts 2009-16',D.start.dt.year>=2009)]:
        rows.append(dict(strategy=m,era=era,plans=int(msk.sum()),wealth_vs_DCA=f"{rel[msk].median()*100:+.1f}%",account_dd=f"{D.dd[msk].median()*100:.0f}% (worst {D.dd[msk].min()*100:.0f}%)",below_money_in=f"{D.below[msk].median()*100:.0f}% (worst {D.below[msk].min()*100:.0f}%)"))
pd.set_option('display.width',250); print('10-year monthly plans, $1,000/month, cash at T-bill'); print(pd.DataFrame(rows).to_string(index=False))
print('fast buy1 count',b1.sum(),'buy2',b2.sum(),'washouts',wo.sum(),'zone days share',round(zone[idx>='2000'].mean(),2))
