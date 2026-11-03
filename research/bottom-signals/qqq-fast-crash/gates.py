exec(open('combos.py').read().split("rows=[]")[0])
G10=fam(10); G5=fam(5)
imp=(X.vxn/100)*np.sqrt(21/252)       # 1-month 1-sigma implied move
rules={}
for d in (0.09,0.108,0.12): rules[f'static -{d*100:.1f}%']=(X.dd<=-d)
for m in (1.0,1.25,1.5,1.75,2.0): rules[f'implied-vol depth x{m}']=(X.dd<=-m*imp)&(X.dd<=-0.06)
for m in (1.25,1.5): 
    rules[f'implied x{m} + any fear/positioning (10d)']=(X.dd<=-m*imp)&(X.dd<=-0.06)&((G10.options_fear==1)|(G10.positioning==1)|(G10.capitulation==1))
rules['static -10.8% + options fear or positioning (10d)']=(X.dd<=-0.108)&((G10.options_fear==1)|(G10.positioning==1))
rules['static -10.8% + capitulation (10d)']=(X.dd<=-0.108)&(G10.capitulation==1)
rules['static -9% + 3 families (10d)']=(X.dd<=-0.09)&(G10.fillna(0).sum(axis=1)>=3)
rules['static -10.8% + VXN top10']=(X.dd<=-0.108)&(F.vxn_top10==1)
rows=[]
for nm,sig in rules.items():
    D=run_rule(sig.astype(float),mindd=0.0); r=dict(rule=nm,**summ(D))
    for en,(y0,y1) in {'07-15':(2007,2015),'16-26':(2016,2026)}.items():
        s=summ(D[(D.win.dt.year>=y0)&(D.win.dt.year<=y1)]); r[en]=f"{s.get('score',np.nan):+.1f} ({s.get('signals')})" if s else '-'; r[en+'_s']=s.get('score',-99) if s else -99
    r['min_era']=min(r['07-15_s'],r['16-26_s']); rows.append(r); 
R=pd.DataFrame(rows).sort_values('min_era',ascending=False); pd.set_option('display.width',300); pd.set_option('display.max_colwidth',50)
print(R[['rule','signals','fall_med','fall_worst','within5','under_med','r1m','r3m','r6m','score','07-15','16-26','min_era']].round(1).to_string(index=False))
