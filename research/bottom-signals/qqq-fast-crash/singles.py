exec(open('evalq.py').read())
rows=[]
base=pd.Series(1.0,index=idx)
for nm,sig in [('BASE: first day 5% down',base),('STATIC -10.8%',(X.dd<=-0.108).astype(float))]+list(F.items()):
    D=run_rule(sig); r={'rule':nm,**{f'all_{k}':v for k,v in summ(D).items()}}
    for en,(y0,y1) in {'07-15':(2007,2015),'16-26':(2016,2026)}.items():
        s=summ(D[(D.win.dt.year>=y0)&(D.win.dt.year<=y1)]); r[f'{en}_score']=round(s.get('score',np.nan),1); r[f'{en}_sig']=s.get('signals')
    rows.append(r)
R=pd.DataFrame(rows); pd.set_option('display.width',300)
cols=['rule','all_signals','all_fall_med','all_fall_worst','all_within5','all_under_med','all_r1m','all_r3m','all_r6m','all_score','07-15_score','07-15_sig','16-26_score','16-26_sig']
print(R[cols].round(1).sort_values('all_score',ascending=False).to_string(index=False))
