from feng import *
pd.set_option('display.width', 250)
C = {'S1 daily EMA 10/100 cross (selected)': rule('D', 'EMA', 'cross', 'cross', 10, 100),
     'S2 daily EMA 20/50 cross': rule('D', 'EMA', 'cross', 'cross', 20, 50),
     'S3 daily EMA 30/50 cross': rule('D', 'EMA', 'cross', 'cross', 30, 50),
     'S4 daily: close>SMA10 in, close<SMA100 out': rule('D', 'SMA', 'close>fast', 'below_slow', 10, 100),
     'v2-D weekly EMA 13/40 + window': rule('W', 'EMA', 'cross', 'cross', 13, 40),
     'Buy & hold': HODL}
for n, p in C.items():
    c = 0 if n == 'Buy & hold' else 0.004
    r, pp = daily(p, c)
    for nm, yrs in (('holdout', HOLD), ('2016-26', OOS)):
        m = mask_years(yrs) & r.notna(); eq = (1 + r[m]).cumprod(); dd = eq / eq.cummax() - 1
        print(f"{n[:44]:44s} {nm:8s} worst fall {dd.min():.0%} from {eq.loc[:dd.idxmin()].idxmax().date()} to {dd.idxmin().date()}")
print()
yrs = list(range(2012, 2027))
t = pd.DataFrame({n[:3] if n != 'Buy & hold' else 'B&H': per_year(p, yrs, 0 if n == 'Buy & hold' else 0.004) for n, p in C.items()})
print((t * 100).round(0).astype(int).astype(str).add('%').to_string())
