from feng import *
import feng
S3 = rule('D', 'EMA', 'cross', 'cross', 30, 50)
d = DSH
bins = [(0, 180), (180, 360), (360, 540), (540, 900), (900, 1080), (1080, 1260), (1260, 1500)]
ALLY = list(range(2012, 2027))
rows = []
for a, b in bins:
    m = (d > a) & (d <= b) & YEAR.isin(ALLY)
    out = {'days since halving': f'{a}-{b}'}
    for n, pos, c in (('S3', S3, 0.004), ('B&H', HODL, 0.0)):
        r, p = daily(pos, c)
        x = r[m & r.notna()]
        out[f'{n} ann.'] = f"{(1 + x).prod() ** (365 / len(x)) - 1:+.0%}"
        out[f'{n} avg daily x365'] = f"{x.mean() * 365:+.0%}"
        if n == 'S3': out['S3 in market'] = f"{p[m].mean():.0%}"
    # per cycle return of B&H in this phase
    cyc = []
    for h0 in ('2012-11-28', '2016-07-09', '2020-05-11', '2024-04-20'):
        h = pd.Timestamp(h0); s, e = h + pd.Timedelta(days=a + 1), h + pd.Timedelta(days=b)
        if s <= P.index[-1]:
            seg = P.loc[s - pd.Timedelta(days=1):min(e, P.index[-1])]
            cyc.append(f"{h.year}:{seg.iloc[-1] / seg.iloc[0] - 1:+.0%}")
    out['B&H by cycle'] = ' '.join(cyc)
    rows.append(out)
pd.set_option('display.width', 250)
print(pd.DataFrame(rows).to_string(index=False))
