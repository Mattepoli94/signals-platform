from weng import *
import itertools
pd.set_option('display.width', 250)
A, B = (450, 500, 550), (850, 900, 950)
CANDS = [('cross', f, s) for f in FAST for s in SLOW if f < s] + [('above', n, None) for n in NS]


def select(train):
    e = lambda pos: ev(pos, train)['Calmar']
    g = {c: e(core(*c)) for c in CANDS}
    def nb(c):
        if c[0] == 'cross':
            i, j = FAST.index(c[1]), SLOW.index(c[2])
            v = [g[x] for x in g if x[0] == 'cross' and abs(FAST.index(x[1]) - i) <= 1 and abs(SLOW.index(x[2]) - j) <= 1]
        else:
            i = NS.index(c[1]); v = [g[('above', n, None)] for n in NS if abs(NS.index(n) - i) <= 1]
        return np.mean(v)
    best = max(CANDS, key=nb); c = core(*best); base = e(c); cy0 = per_cycle(c, train)
    win = None; bestv = base * 1.2
    for mode in ('C2', 'C1'):
        for a, b in itertools.product(A, B):
            p = cycle(c, mode, a, b); v = e(p); cy = per_cycle(p, train)
            ok = not any(np.isfinite(cy[k]) and np.isfinite(cy0[k]) and cy[k] < cy0[k] - 1e-9 for k in cy)
            if v >= bestv and ok:
                bestv, win = v, (mode, a, b)
    return best, win, (cycle(c, *win) if win else c)


ch, win, SEL = select(TRAIN)
print('Pre-registered selection on training years:', ch, 'window:', win)
K1 = cycle(core('above', 10), 'C1', 540, 900)
X = core('cross', 13, 40); XK = cycle(X, 'C1', 540, 900)
V1 = __import__('eng').OLD
systems = {'A. Selected: weekly close > 10w EMA (no window)': SEL,
           'B. A + knowledge window (sell day 540-900)': K1,
           'C. Weekly EMA 13/40 cross': X,
           'D. C + knowledge window': XK,
           'E. Old daily v1 (blend + halving window)': V1,
           'Buy & hold': HODL}
rows = {}
for n, p in systems.items():
    cost = 0 if n == 'Buy & hold' else 0.004
    tr, ho = ev(p, TRAIN, cost), ev(p, HOLD, cost)
    tr13 = ev(p, [y for y in TRAIN if y != 2013], cost)
    rows[n] = {'Train CAGR': tr['CAGR'], 'Train DD': tr['MaxDD'], 'Train Calmar': tr['Calmar'], 'Calmar ex-2013': tr13['Calmar'],
               'Holdout CAGR': ho['CAGR'], 'Holdout DD': ho['MaxDD'], 'Holdout Calmar': ho['Calmar'], 'Trades/yr': tr['Trades/yr']}
print(pd.DataFrame(rows).T.round(3).to_string())
print('\nHoldout years:')
for n, p in systems.items():
    print(f'  {n[:45]:45s}', {y: f"{v:+.0%}" for y, v in per_year(p, HOLD, 0 if n == 'Buy & hold' else 0.004).items()})
# walk-forward of the procedure, and fixed rules year by year
wf_ret, wf_pos, wrow = [], [], []
for Y in range(2016, 2027):
    c, w, p = select(list(range(2012, Y)))
    ret, pp = daily(p, 0.004)
    m = (YEAR == Y) & ret.notna()
    wf_ret.append(ret[m]); wf_pos.append(pp[m])
    wrow.append(f"{Y}: {c[0]} {c[1]}{'/' + str(c[2]) if c[2] else ''} {w or 'no window'} -> {(1 + ret[m]).prod() - 1:+.0%}")
print('\nWalk-forward selections:'); print('\n'.join(wrow))
wr = pd.concat(wf_ret); wp = pd.concat(wf_pos)
wf = stats(wr, wp, pd.Series(True, index=wr.index))
OOS = list(range(2016, 2027))
out = {'Walk-forward procedure': wf}
for n, p in systems.items():
    out[n] = ev(p, OOS, 0 if n == 'Buy & hold' else 0.004)
print('\n2016-Oct 2026 year by year (walk-forward = genuinely out of sample; fixed rules A-E chosen with hindsight):')
print(pd.DataFrame(out).T[['CAGR', 'MaxDD', 'Calmar', 'Exposure', 'Trades/yr']].round(3).to_string())
for n, p in systems.items():
    print(f'  {n[:45]:45s}', {y: f"{v:+.0%}" for y, v in per_year(p, OOS, 0 if n == "Buy & hold" else 0.004).items()})
