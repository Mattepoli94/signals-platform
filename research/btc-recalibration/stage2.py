from eng import *
t = pd.read_pickle('stage1.pkl')
ema_t = t[t.family == 'above EMA'].set_index('len').Calmar
nb = {n: ema_t.iloc[max(0, i - 1):i + 2].mean() for i, n in enumerate(ema_t.index)}
print('above-EMA 3-point neighbourhood Calmar:', {k: round(v, 3) for k, v in nb.items()})
CORE_N = max(nb, key=nb.get); print('Stage 1 choice: close > EMA', CORE_N, '(simplest family within 10% of the best family median)')
core = CORES[('above EMA', CORE_N)]
rows = {}
for tg in (None, 0.6, 0.8, 1.0, 1.2):
    rows[str(tg)] = evaluate(vol_size(core, tg))
print(pd.DataFrame(rows).T.round(3).to_string())
