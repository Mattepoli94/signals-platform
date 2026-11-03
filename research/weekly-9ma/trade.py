"""Part 2: the setup as a trading system (weekly decisions at the Friday close)."""
import pandas as pd, numpy as np
from common import *; from setup import *

def backtest(px, entry, exit_rule, cost=0.001, start=None, end=None):
    """px daily adj close; entry: weekly bool series (signal at that week's close); exit_rule(state)->bool weekly.
    Positions change at the weekly close; daily marking."""
    c = px.dropna()
    w, m9, _ = cross_up(c, 9)
    m20 = w.rolling(20).mean()
    pos = pd.Series(0.0, index=w.index); inpos = False; held = 0; trades = []
    for i, d in enumerate(w.index):
        if inpos:
            held += 1
            if exit_rule(w, m9, m20, i, held):
                inpos = False; trades[-1]['exit'] = d; trades[-1]['ret'] = w.iloc[i] / trades[-1]['px'] - 1
        elif bool(entry.get(d, False)):
            inpos = True; held = 0; trades.append({'entry': d, 'px': w.iloc[i]})
        pos.iloc[i] = 1.0 if inpos else 0.0
    posd = pos.reindex(c.index).ffill().shift(1).fillna(0)       # position decided at the close, held from next day
    r = c.pct_change().fillna(0) * posd - posd.diff().abs().fillna(0) * cost
    eq = (1 + r).cumprod()
    if start: eq = eq[eq.index >= start]
    if end: eq = eq[eq.index <= end]
    return eq / eq.iloc[0], pd.DataFrame(trades), posd

EXITS = {
    'close<9w': lambda w, m9, m20, i, h: w.iloc[i] < m9.iloc[i],
    'close<20w': lambda w, m9, m20, i, h: w.iloc[i] < m20.iloc[i],
    'hold26w': lambda w, m9, m20, i, h: h >= 26,
    'hold52w': lambda w, m9, m20, i, h: h >= 52,
}
