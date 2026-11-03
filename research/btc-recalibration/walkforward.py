"""Walk-forward test of the SELECTION PROCEDURE in PREREG.md (added after the holdout failed; it chooses nothing
by itself: it re-runs the same pre-registered stages on years before Y and trades year Y out of sample)."""
from eng import *

FAMS = {}
for (fam, n), pos in CORES.items():
    FAMS.setdefault(fam, []).append((n, pos))
SIMPLICITY = ['momentum', 'above SMA', 'above EMA', 'EMA cross', 'blend']   # simpler first
A, Bs = (365, 450, 545, 640), (730, 820, 910, 1000)


def nb_best(vals):
    keys = list(vals); v = np.array([vals[k] for k in keys])
    nb = [np.nanmean(v[max(0, i - 1):i + 2]) for i in range(len(v))]
    return keys[int(np.nanargmax(nb))]


def select(train_years):
    cal = lambda pos: evaluate(pos, train_years).get('Calmar', np.nan)
    med = {f: np.nanmedian([cal(p) for _, p in FAMS[f]]) for f in FAMS}
    best = max(med.values())
    ok = [f for f in SIMPLICITY if med[f] >= 0.9 * best]
    fam = ok[0]
    vals = {n: cal(p) for n, p in FAMS[fam]}
    n = nb_best(vals) if len(vals) > 2 else max(vals, key=vals.get)
    core = dict(FAMS[fam])[n]
    b0 = evaluate(core, train_years)
    tg_vals = {tg: evaluate(vol_size(core, tg), train_years) for tg in (0.6, 0.8, 1.0, 1.2)}
    tg = nb_best({k: v['Calmar'] for k, v in tg_vals.items()})
    if not (tg_vals[tg]['Calmar'] > b0['Calmar'] and tg_vals[tg]['MaxDD'] > b0['MaxDD']):
        tg = None
    sized = vol_size(core, tg)
    base = evaluate(sized, train_years)['Calmar']
    cyc0 = per_cycle(sized, train_years)
    grid = {}
    for a in A:
        for b in Bs:
            pos = halving(sized, a, b)
            c = evaluate(pos, train_years)['Calmar']
            cyc = per_cycle(pos, train_years)
            worse = any(np.isfinite(cyc[k]) and np.isfinite(cyc0[k]) and cyc[k] < cyc0[k] - 1e-9 for k in cyc)
            grid[(a, b)] = (c, worse)
    # plateau centre among windows that pass both tests
    win = None
    cand = {k: v[0] for k, v in grid.items() if v[0] >= 1.2 * base and not v[1]}
    if cand:
        def nbm(k):
            a, b = k; ia, ib = A.index(a), Bs.index(b)
            return np.mean([grid[(A[i], Bs[j])][0] for i in range(max(0, ia - 1), min(len(A), ia + 2))
                            for j in range(max(0, ib - 1), min(len(Bs), ib + 2))])
        win = max(cand, key=nbm)
    final = halving(sized, *win) if win else sized
    return {'core': f'{fam} {n}', 'vol': tg, 'window': win}, final


rows, oos = [], []
for Y in range(2016, 2027):
    train = [y for y in range(2012, Y)]
    spec, pos = select(train)
    r = per_year(pos, [Y])[Y]
    rows.append({'test year': Y, **spec, 'system': f"{r:+.0%}", 'HODL': f"{per_year(HODL, [Y])[Y]:+.0%}",
                 'OLD v1 (in-sample)': f"{per_year(OLD, [Y])[Y]:+.0%}"})
    ret, p = daily(pos)
    oos.append((ret[(YEAR == Y) & ret.notna()], p[(YEAR == Y)]))
pd.set_option('display.width', 250)
print(pd.DataFrame(rows).to_string(index=False))
ret = pd.concat([o[0] for o in oos]); pos = pd.concat([o[1] for o in oos]).reindex(ret.index)
st = stats(ret, pos, pd.Series(True, index=ret.index))
print('\nWALK-FORWARD out-of-sample 2016-2026:', {k: round(v, 3) for k, v in st.items()})
print('HODL same years:', {k: round(v, 3) for k, v in evaluate(HODL, list(range(2016, 2027))).items()})
print('OLD v1 same years (in-sample, for reference):', {k: round(v, 3) for k, v in evaluate(OLD, list(range(2016, 2027))).items()})
