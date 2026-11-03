from eng import *
pd.set_option('display.width', 220)
rows = []
for (fam, n), pos in CORES.items():
    m = evaluate(pos); rows.append({'family': fam, 'len': n, **m})
t = pd.DataFrame(rows)
print('TRAINING years:', TRAIN)
print(t.round(3).to_string(index=False))
fam = t.groupby('family').Calmar.median().sort_values(ascending=False)
print('\nFamily median Calmar:\n', fam.round(3).to_string())
print('\nHODL train:', {k: round(v, 3) for k, v in evaluate(HODL).items()})
print('OLD v1 system train:', {k: round(v, 3) for k, v in evaluate(OLD).items()})
t.to_pickle('stage1.pkl')
