from feng import *
import feng
pd.set_option('display.width', 250)
d = DSH.fillna(pd.Series((idx - pd.Timestamp('2009-01-03')).days, index=idx)).values
def active(start):
    """Trade only from `start` days after the previous halving (wrapping into the next cycle) up to day 540."""
    if start == 0:
        return (d > 0) & (d <= 540)
    return ((d > start) | (d <= 540)) & ~np.isnan(d)
def make(start, inside='S3', extra_flat=None):
    act = active(start)
    if extra_flat:
        a, b = extra_flat; act = act & ~((d > a) & (d <= b))
    old = feng.WIN.copy()
    feng.WIN = ~act                 # machine() treats WIN as forced-flat days
    pos = rule('D', 'EMA', 'cross', 'cross', 30, 50, True) if inside == 'S3' else pd.Series(act.astype(float), index=idx)
    feng.WIN = old
    return pos
V = {'S3 now: flat day 540-900': rule('D', 'EMA', 'cross', 'cross', 30, 50)}
for st in (900, 1000, 1080, 1170, 1260, 1350, 0):
    V[f'S3 only day {st}->540'] = make(st)
V['S3, also flat day 1080-1260 (mid-cycle chop)'] = make(900, 'S3', (1080, 1260))
V['Hold (no trend rule) day 900->540'] = make(900, 'hold')
V['Hold day 1260->540'] = make(1260, 'hold')
V['Buy & hold'] = HODL
rows = {}
for n, p in V.items():
    c = 0 if n == 'Buy & hold' else 0.004
    tr, ho, oo = ev(p, TR_EX13, c), ev(p, HOLD, c), ev(p, OOS, c)
    rows[n] = {'train ex-2013': f"{tr['CAGR']:.0%} / {tr['MaxDD']:.0%}", 'held out': f"{ho['CAGR']:.0%} / {ho['MaxDD']:.0%}",
               '2016-26': f"{oo['CAGR']:.0%} / {oo['MaxDD']:.0%}", 'Calmar 16-26': round(oo['Calmar'], 2), 'in market': f"{oo['Exposure']:.0%}"}
print(pd.DataFrame(rows).T.to_string())
