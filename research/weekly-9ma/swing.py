"""Swing-trading version: enter on the setup, exit on stop / target / time (daily closes)."""
import pandas as pd, numpy as np, itertools
from common import *; from setup import *
exec(open('run1.py').read().split("def run")[0])
W = conditions(M, B, dd_q=.10, dd_s=.075, look=8, mm_low=25, mm_up=10, mm_look=6)
COST = 0.002   # round trip

def sim(c, entries, stop, tgt, maxd, delay=0):
    """c: daily closes (np array), entries: integer positions (signal day). Returns list of (ret, days)."""
    out = []; busy = -1
    for i in entries:
        i = i + delay
        if i <= busy or i >= len(c) - 1: continue
        e = c[i]; path = c[i + 1:i + 1 + maxd] / e - 1
        hit = np.where((path <= -stop) | (path >= tgt))[0]
        j = hit[0] if len(hit) else len(path) - 1
        out.append((path[j] - COST, j + 1)); busy = i + j + 1     # one position at a time per instrument
    return out

def summ(tr, years):
    if not tr: return {}
    r = np.array([t[0] for t in tr]); d = np.array([t[1] for t in tr])
    w, l = r[r > 0], r[r <= 0]
    eq = np.prod(1 + r)
    return {'trades': len(r), 'per_yr': round(len(r) / years, 1), 'win%': round((r > 0).mean() * 100), 'avg%': round(r.mean() * 100, 2),
            'avg_win%': round(w.mean() * 100, 1) if len(w) else 0, 'avg_loss%': round(l.mean() * 100, 1) if len(l) else 0,
            'PF': round(w.sum() / -l.sum(), 2) if len(l) and l.sum() < 0 else np.inf, 'days': round(d.mean()),
            'cagr%': round((eq ** (1 / years) - 1) * 100, 1), 'exposure%': round(d.sum() / (years * 252) * 100)}

def daily_signals(px, kind):
    c = px.dropna(); w, m, x = cross_up(c)
    cond = W.reindex(w.index).ffill()
    if kind == 'setup': sig = w.index[x & cond['flush'] & cond['mm_bottom']]
    elif kind == 'cross+flush': sig = w.index[x & cond['flush']]
    elif kind == 'any 9w cross': sig = w.index[x]
    elif kind == 'every week (random-like)': sig = w.index
    elif kind == 'daily 9ema cross, setup armed':      # swing timing on the daily chart while the weekly setup is armed
        e9 = c.ewm(span=9, adjust=False).mean(); dx = (c > e9) & (c.shift(1) <= e9.shift(1))
        armed = (cond['flush'] & cond['mm_bottom']).reindex(c.index, method='ffill').fillna(False)
        sig = c.index[dx & armed]
    return c, [c.index.get_loc(d) for d in sig]
