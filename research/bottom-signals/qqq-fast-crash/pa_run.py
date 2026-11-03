exec(open('pa.py').read())
pd.set_option('display.width',320); pd.set_option('display.max_colwidth',60)
depth108=(dd<=-0.108).astype(float)
print('windows since 2000:',len(W))
rows=[dict(rule='STATIC -10.8% (reference)',**evaluate(depth108,gate=0.0))]
for g in (0.09,0.12,0.15): rows.append(dict(rule=f'STATIC -{g*100:.0f}%',**evaluate((dd<=-g).astype(float),gate=0.0)))
for k,v in P.items(): rows.append(dict(rule='1-step: '+k,**evaluate(v,gate=0.08)))
R=pd.DataFrame(rows).round(1).sort_values('score',ascending=False); print(R.to_string(index=False))
print('\n=== 2-step: tranche 1 at -10.8%, tranche 2 = pattern (lower price) ===')
rows=[dict(rule='3+ families (current)',**evaluate(depth108,(cnt>=3).astype(float),gate=0.0))]
for k,v in P.items(): rows.append(dict(rule=k,**evaluate(depth108,v,gate=0.0)))
R2=pd.DataFrame(rows).round(1).sort_values('score',ascending=False); print(R2.to_string(index=False))
