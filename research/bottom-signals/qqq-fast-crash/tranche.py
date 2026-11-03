exec(open('combos.py').read().split("rows"+"=[]")[0])
G10=fam(10); G5=fam(5); imp=(X.vxn/100)*np.sqrt(21/252)
first=run_rule((X.dd<=-0.108).astype(float),mindd=0.0)
second_rules={'none (single entry)':None,'static -15%':(X.dd<=-0.15),'capitulation volume after entry':(F.capitulation_vol==1),
  'options fear after entry':(G5.options_fear==1),'3+ families after entry':(G10.fillna(0).sum(axis=1)>=3),'implied-vol x1.5':(X.dd<=-1.5*imp)}
out=[]
for nm,sec in second_rules.items():
    rows=[]
    for _,r in first.dropna(subset=['date']).iterrows():
        i=idx.get_loc(r.date); e1=a[i]; j=None
        if sec is not None:
            j=next((k for k in range(i+1,min(i+41,len(a))) if sec.iloc[k]==1 and a[k]<e1),None)
        e=e1 if j is None else 2/(1/e1+1/a[j])          # equal £ tranches -> harmonic mean price
        ref=i if j is None else j
        f=a[i+1:i+253]; heat=min(0,f[:63].min()/e-1)
        r3=a[i+63]/e-1 if i+63<len(a) else np.nan
        rows.append(dict(win=r.win,second=j is not None,heat=heat,r3m=r3,above_low=e/window_low(idx.get_loc(r.win))-1))
    D=pd.DataFrame(rows); done=D[D.r3m.notna()]
    out.append(dict(second_tranche=nm,used=f"{D.second.sum()}/{len(D)}",avg_entry_vs_low=f"{D.above_low.mean()*100:+.1f}%",fall_med=round(D.heat.median()*100,1),fall_worst=round(D.heat.min()*100,1),
                    r3m=round(done.r3m.mean()*100,1),score=round((done.r3m.mean()+D.heat.median())*100,1)))
pd.set_option('display.width',250); print(pd.DataFrame(out).to_string(index=False))
