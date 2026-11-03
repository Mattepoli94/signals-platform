import sys; sys.path.insert(0, '/home/claude/btc/recal')
from eng import P, idx, IRX, R, YEAR, HOLD, TRAIN, DSH, CYCLES, RV30, per_cycle as _pc, stats, mask_years
import numpy as np, pandas as pd

W = P.resample('W-SUN').last()
WE = lambda n: W.ewm(span=n, adjust=False).mean()


def to_daily(s):
    """Weekly series known at the week's close (Sunday) -> daily, applied from that Sunday's close on."""
    return s.reindex(s.index.union(idx)).ffill().reindex(idx)


def core(kind, a, b=None, exe='E1'):
    if kind == 'cross':
        sig_w = (WE(a) > WE(b))
    else:
        sig_w = (W > WE(a))
    pos = to_daily(sig_w.astype(float)).fillna(0)
    if exe == 'E2':
        slow = to_daily(WE(b if kind == 'cross' else a))
        # exit on a daily close below the slow weekly EMA; re-entry only at a weekly signal
        out = np.zeros(len(idx)); s = 0
        wk_on = pos.values; below = (P < slow).values
        is_sun = (idx.dayofweek == 6)
        for i in range(len(idx)):
            if s == 1 and below[i]:
                s = 0
            elif s == 0 and is_sun[i] and wk_on[i] == 1:
                s = 1
            elif s == 1 and is_sun[i] and wk_on[i] == 0:
                s = 0
            out[i] = s
        pos = pd.Series(out, index=idx)
    return pos


def cycle(pos, mode, a=None, b=None):
    if mode == 'C0':
        return pos
    win = ((DSH > a) & (DSH <= b)).values
    if mode == 'C1':
        return pos.where(~pd.Series(win, index=idx), 0.0)
    # C2: no new entries inside the window
    p = pos.values; out = np.zeros(len(p)); s = 0
    for i in range(len(p)):
        if s == 0 and p[i] > 0 and not win[i]:
            s = 1
        elif s == 1 and p[i] == 0:
            s = 0
        out[i] = s
    return pd.Series(out, index=idx)


def daily(pos, cost=0.004, hold_fee=0.0):
    pos = pos.reindex(idx).fillna(0).clip(0, 1)
    turn = pos.diff().abs().fillna(pos)
    return pos * R + (1 - pos) * IRX - turn * cost - pos * hold_fee / 365, pos


def ev(pos, years=None, cost=0.004, hold_fee=0.0):
    ret, p = daily(pos, cost, hold_fee)
    return stats(ret, p, mask_years(years or TRAIN))


def per_year(pos, years, cost=0.004):
    ret, _ = daily(pos, cost)
    return {y: (1 + ret[(YEAR == y) & ret.notna()]).prod() - 1 for y in years}


def per_cycle(pos, years=None, cost=0.004):
    ret, p = daily(pos, cost)
    out = {}
    for a, b in CYCLES:
        m = (idx >= a) & (idx <= b) & mask_years(years or TRAIN).values
        out[a[:4]] = stats(ret, p, pd.Series(m, index=idx)).get('Calmar', np.nan)
    return out

HODL = pd.Series(1.0, index=idx)
FAST, SLOW, NS = (5, 8, 10, 13, 20), (20, 26, 30, 40, 50), (10, 20, 30, 40, 50)
