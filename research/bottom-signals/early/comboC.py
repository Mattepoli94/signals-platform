import warnings; warnings.filterwarnings('ignore')
exec(open('C.py').read().split("rows=[]")[0])
F=pd.DataFrame({'funding_neg':S['funding_negative'],'cycle':S['cycle_day_850_1000'],'oversold':S['rsi_lt_30']})
for k in (1,2):
    sig=(F.sum(axis=1,min_count=2)>=k).astype(float).where(F.notna().sum(axis=1)>=2)
    for pn,(a,c) in {'2019-20':(2019,2020),'2021-26':(2021,2026),'all 2019-26':(2019,2026)}.items():
        mm=state&sig.notna()&r90.notna()&(idx.year>=a)&(idx.year<=c); o=sig[mm]==1
        if o.sum()>=5: print(f'score>={k} {pn}: days {o.sum()}, +90d excess {(r90[mm][o].mean()-r90[mm].mean())*100:+.1f}%, win90 {(r90[mm][o]>0).mean()*100:.0f}% vs {(r90[mm]>0).mean()*100:.0f}%, further 15% fall {(m30[mm][o]<=-0.15).mean()*100:.0f}% vs {(m30[mm]<=-0.15).mean()*100:.0f}%')
# troughs of 16 BTC crash events: was funding negative or rsi<30 near the low?
exec(open('/home/claude/pos/btcpos15.py').read().split("rows=[]")[0].replace("import pandas as pd, numpy as np",""))
