import sys; sys.path.insert(0, '/home/claude/btc/recal'); sys.path.insert(0, '/home/claude/btc/weekly')
import numpy as np, pandas as pd
from eng import P, idx, IRX, R, YEAR, HOLD, TRAIN, DSH, stats, mask_years
W = P.resample('W-SUN').last()
SUN = (idx.dayofweek == 6)
WIN = ((DSH > 540) & (DSH <= 900)).values


def ma(x, n, t):
    return x.ewm(span=n, adjust=False).mean() if t == 'EMA' else x.rolling(n).mean()


def to_d(s):
    return s.reindex(s.index.union(idx)).ffill().reindex(idx)


def machine(entry, exit_, window=True, ok_days=None):
    e, x = entry.values, exit_.values
    out = np.zeros(len(e)); s = 0
    for i in range(len(e)):
        if window and WIN[i]:
            s = 0
        elif s == 0 and e[i] and not x[i] and (ok_days is None or ok_days[i]):
            s = 1
        elif s == 1 and x[i]:
            s = 0
        out[i] = s
    return pd.Series(out, index=idx)


def rule(tf, t, ent, ex, f, s, window=True):
    if tf == 'D':
        fm, sm, c = ma(P, f, t), ma(P, s, t), P
        E = (fm > sm) if ent == 'cross' else (c > fm)
        X = {'cross': fm < sm, 'below_slow': c < sm, 'below_fast': c < fm}[ex]
        return machine(E.fillna(False), X.fillna(False), window)
    fm, sm = to_d(ma(W, f, t)), to_d(ma(W, s, t))
    cw = to_d(W)
    E = (fm > sm) if ent == 'cross' else (cw > fm)
    if tf == 'W':     # everything on weekly closes
        X = {'cross': fm < sm, 'below_slow': cw < sm, 'below_fast': cw < fm}[ex]
        return machine(E.fillna(False), X.fillna(False), window)
    # 'Wd': weekly entries, exits on a DAILY close vs the weekly MAs
    X = {'cross': fm < sm, 'below_slow': P < sm, 'below_fast': P < fm}[ex]
    return machine(E.fillna(False) & pd.Series(SUN, index=idx), X.fillna(False), window)


def daily(pos, cost=0.004, hold_fee=0.0):
    pos = pos.reindex(idx).fillna(0)
    turn = pos.diff().abs().fillna(pos)
    return pos * R + (1 - pos) * IRX - turn * cost - pos * hold_fee / 365, pos


def ev(pos, years, cost=0.004):
    r, p = daily(pos, cost)
    return stats(r, p, mask_years(years))


def per_year(pos, years, cost=0.004):
    r, _ = daily(pos, cost)
    return {y: (1 + r[(YEAR == y) & r.notna()]).prod() - 1 for y in years}

HODL = pd.Series(1.0, index=idx)
OOS = list(range(2016, 2027))
TR_EX13 = [y for y in TRAIN if y != 2013]
PAIRS = {'D': [(f, s) for f in (10, 20, 30, 50) for s in (50, 100, 150, 200) if f < s],
         'W': [(f, s) for f in (5, 10, 13, 20) for s in (20, 30, 40, 50) if f < s]}
