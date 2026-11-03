from weng import *
pd.set_option('display.width', 220)
# stage 1 plateau choice
g = pd.DataFrame(index=FAST, columns=SLOW, dtype=float)
for f in FAST:
    for s in SLOW:
        if f < s: g.loc[f, s] = ev(core('cross', f, s))['Calmar']
nbx = {}
for i, f in enumerate(FAST):
    for j, s in enumerate(SLOW):
        if f < s:
            nbx[(f, s)] = np.nanmean(g.iloc[max(0, i-1):i+2, max(0, j-1):j+2].values)
ab = [ev(core('above', n))['Calmar'] for n in NS]
nba = {n: np.mean(ab[max(0, i-1):i+2]) for i, n in enumerate(NS)}
bx, ba = max(nbx, key=nbx.get), max(nba, key=nba.get)
print('best cross plateau', bx, round(nbx[bx], 2), '| best above-EMA plateau', ba, round(nba[ba], 2))
CORE = core('above', ba)
base = ev(CORE); cyc0 = per_cycle(CORE)
print('Stage 1 choice: weekly close > EMA', ba, 'weeks, weekly execution. Train:', {k: round(v, 3) for k, v in base.items()})
print('cycle Calmar:', {k: round(v, 2) for k, v in cyc0.items()})
A, B = (450, 500, 550), (850, 900, 950)
for mode in ('C1', 'C2'):
    t = pd.DataFrame(index=A, columns=B, dtype=object); c = pd.DataFrame(index=A, columns=B, dtype=float)
    for a in A:
        for b in B:
            pos = cycle(CORE, mode, a, b); m = ev(pos); cy = per_cycle(pos)
            worse = [k for k in cy if np.isfinite(cy[k]) and cy[k] < cyc0[k] - 1e-9]
            c.loc[a, b] = m['Calmar']
            t.loc[a, b] = f"{m['Calmar']:.2f} ({m['Calmar']/base['Calmar']-1:+.0%}) dd{m['MaxDD']:.0%}" + (' worse:' + ','.join(worse) if worse else '')
    print(f'\n{mode} window grid (rows a, cols b):'); print(t.to_string())
for mode in ('C1', 'C2'):
    m = ev(cycle(CORE, mode, 540, 900)); print(f'Knowledge window K {mode} (540-900):', {k: round(v, 3) for k, v in m.items()}, f"Calmar {m['Calmar']/base['Calmar']-1:+.0%}")
