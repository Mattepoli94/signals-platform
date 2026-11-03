"""Weekly 9-MA cross after a market flush + breadth (MMFI-style) local bottom."""
import pandas as pd, numpy as np
from common import *

def wk(s):
    """daily series -> weekly last, indexed at the week's last trading day"""
    s = s.dropna()
    g = s.groupby(s.index.to_period('W-FRI'))
    return pd.Series(g.last().values, index=g.apply(lambda x: x.index[-1]).values)

def wkmin(s):
    s = s.dropna(); g = s.groupby(s.index.to_period('W-FRI'))
    return pd.Series(g.min().values, index=g.apply(lambda x: x.index[-1]).values)

def conditions(P, B, mkt=('QQQ', 'SPY'), dd_q=0.10, dd_s=0.075, look=8, mm_col='all_above50',
               mm_low=25, mm_up=10, mm_look=6, ma=9, kind='sma'):
    """weekly frame of market conditions (known at each week's close)."""
    q = P[mkt[0]]['adj_close'].dropna(); s = P[mkt[1]]['adj_close'].dropna()
    ddq = q / q.rolling(252, min_periods=150).max() - 1
    dds = s / s.rolling(252, min_periods=150).max() - 1
    flushd = ((ddq <= -dd_q) | (dds.reindex(ddq.index).ffill() <= -dd_s)).astype(float)
    W = pd.DataFrame({'flush_now': wk(flushd)})
    W['flush'] = W['flush_now'].rolling(look, min_periods=1).max() > 0
    m = B[mm_col].dropna()
    W['mm'] = wk(m).reindex(W.index)
    W['mm_wlow'] = wkmin(m).reindex(W.index)
    lowk = W['mm_wlow'].rolling(mm_look, min_periods=1).min()
    W['mm_bottom'] = (lowk <= mm_low) & (W['mm'] >= lowk + mm_up)
    W['ddq'] = wk(ddq).reindex(W.index)
    return W

def cross_up(px, ma=9, kind='sma'):
    w = wk(px)
    m = w.rolling(ma).mean() if kind == 'sma' else w.ewm(span=ma, adjust=False).mean()
    return w, m, (w > m) & (w.shift(1) <= m.shift(1))
