"""Part 1: the setup as a bottom-catching signal."""
import sys, pandas as pd, numpy as np
from common import *; from setup import *

def episodes(px, dd_thr):
    """flush episodes on an instrument: start = first close dd_thr below the 1y high; end = new 1y high (or +2y)."""
    c = px.dropna(); hi = c.rolling(252, min_periods=150).max(); dd = c / hi - 1
    eps, i, n = [], 0, len(c)
    while i < n:
        if dd.iloc[i] <= -dd_thr:
            ref = hi.iloc[i]; j = i
            while j < n and c.iloc[j] < ref and j - i < 504:
                j += 1
            seg = c.iloc[i:j + 1]
            eps.append({'start': c.index[i], 'end': c.index[min(j, n - 1)], 'low_date': seg.idxmin(), 'low': seg.min(),
                        'depth': seg.min() / ref - 1, 'open': j >= n})
            i = j + 1
        else:
            i += 1
    return eps

def evaluate(px, sig_dates, eps, label):
    c = px.dropna(); rows = []; used = set()
    for e in eps:
        s = [d for d in sig_dates if e['start'] - pd.Timedelta(days=21) <= d <= e['end'] and d not in used]
        used.update(s)
        if not s:
            rows.append({'ep': e['start'], 'depth': e['depth'], 'signal': None}); continue
        d = s[0]; px0 = c.loc[d]; i = c.index.get_loc(d)
        fut = lambda k: c.iloc[i + k] / px0 - 1 if i + k < len(c) else np.nan
        rows.append({'ep': e['start'], 'depth': e['depth'], 'signal': d, 'low_date': e['low_date'],
                     'after_low': d >= e['low_date'], 'above_low': px0 / e['low'] - 1,
                     'weeks_from_low': (d - e['low_date']).days / 7,
                     'further': min(c.iloc[i:i + 127].min() / px0 - 1, 0),
                     'r1m': fut(21), 'r3m': fut(63), 'r6m': fut(126), 'r12m': fut(252)})
    r = pd.DataFrame(rows); r['label'] = label
    return r

def summary(r):
    h = r.dropna(subset=['signal'])
    return pd.Series({'episodes': len(r), 'signals': len(h), 'within5': (h['above_low'] <= .05).mean(),
                      'median_above_low': h['above_low'].median(), 'after_low': h['after_low'].mean(),
                      'further_med': h['further'].median(), 'further_worst': h['further'].min(),
                      'r3m': h['r3m'].mean(), 'r6m': h['r6m'].mean(), 'r12m': h['r12m'].mean(),
                      'up6m': (h['r6m'] > 0).mean()})
