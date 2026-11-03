import sys; sys.path.insert(0, '/home/claude/btc')
import numpy as np, pandas as pd
import btc_cm as B
P = B.P
yr = P.groupby(P.index.year).apply(lambda s: s.iloc[-1] / s.iloc[0] - 1)
pool = yr.loc[2012:2026].sort_values()
terc = np.array_split(pool.index.values, 3)
rng = np.random.default_rng(20261103)
pick = [int(rng.choice(t)) for t in terc]
for name, t in zip(('bear', 'middle', 'bull'), terc):
    print(name, {int(y): f"{pool[y]:+.0%}" for y in t})
print('HOLDOUT', pick)
