from eng import *
core = vol_size(CORES[('above EMA', 100)], 1.0)
base = evaluate(core); base_cyc = per_cycle(core)
print('Stage 2 choice: close > EMA100, vol target 100%  train:', {k: round(v, 3) for k, v in base.items()})
print('per-cycle Calmar (train days only):', {k: round(v, 2) for k, v in base_cyc.items()})
A, Bs = (365, 450, 545, 640), (730, 820, 910, 1000)
grid = pd.DataFrame(index=A, columns=Bs, dtype=float); ok = pd.DataFrame(index=A, columns=Bs, dtype=object)
for a in A:
    for b in Bs:
        pos = halving(core, a, b)
        m = evaluate(pos); cyc = per_cycle(pos)
        grid.loc[a, b] = m['Calmar']
        worse = [c for c in cyc if cyc[c] < base_cyc[c] - 1e-9]
        ok.loc[a, b] = f"{m['Calmar']:.2f} dd{m['MaxDD']:.0%} {'worse:' + ','.join(worse) if worse else 'all cycles ok'}"
pd.set_option('display.width', 250)
print('\nTrain Calmar, window grid (rows a = start day, cols b = end day):'); print(grid.round(2).to_string())
print(ok.to_string())
# plateau: 3x3 neighbourhood mean
nb = grid.copy()
for i, a in enumerate(A):
    for j, b in enumerate(Bs):
        nb.loc[a, b] = grid.iloc[max(0, i - 1):i + 2, max(0, j - 1):j + 2].values.mean()
print('\n3x3 neighbourhood mean:'); print(nb.round(2).to_string())
