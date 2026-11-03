from feng import *
pd.set_option('display.width', 250)
d = DSH.fillna(pd.Series((idx - pd.Timestamp('2009-01-03')).days, index=idx))
CH = ((d > 1080) & (d <= 1260))
S3 = rule('D', 'EMA', 'cross', 'cross', 30, 50)
e = lambda n: P.ewm(span=n, adjust=False).mean()
s = lambda n: P.rolling(n).mean()
V = {'S3 as is': S3}
for k in (0.5, 0.25, 0.0):
    V[f'chop: size x{k}'] = S3.where(~CH, S3 * k)
# different rules inside the chop window (S3 elsewhere)
alt = {'chop: also need close > 200-day SMA': S3 * (P > s(200)).astype(float),
       'chop: also need 50-day EMA > 200-day EMA': S3 * (e(50) > e(200)).astype(float),
       'chop: slower 50/100 EMA cross': rule('D', 'EMA', 'cross', 'cross', 50, 100),
       'chop: exit on close below 50-day EMA': rule('D', 'EMA', 'cross', 'below_slow', 30, 50)}
for n, a in alt.items():
    V[n] = S3.where(~CH, a)
V['Buy & hold'] = HODL
rows = {}
for n, p in V.items():
    c = 0 if n == 'Buy & hold' else 0.004
    ho, oo = ev(p, HOLD, c), ev(p, OOS, c)
    r, _ = daily(p, c)
    cyc = []
    for h0 in ('2012-11-28', '2016-07-09', '2020-05-11'):
        h = pd.Timestamp(h0); x = r.loc[h + pd.Timedelta(days=1081):h + pd.Timedelta(days=1260)]
        cyc.append(f"{(1 + x).prod() - 1:+.0%}")
    rows[n] = {'held out': f"{ho['CAGR']:.0%} / {ho['MaxDD']:.0%}", '2016-26': f"{oo['CAGR']:.0%} / {oo['MaxDD']:.0%}",
               'Calmar 16-26': round(oo['Calmar'], 2), 'chop phase 2015-16 / 2019 / 2023': ' / '.join(cyc)}
print(pd.DataFrame(rows).T.to_string())
