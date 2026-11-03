from feng import *
pd.set_option('display.width', 260)
y = pd.read_csv('/home/claude/data/crypto/crypto.csv', parse_dates=['date'])
y = y[y.ticker == 'BTC-USD'].set_index('date').sort_index()[['high', 'low', 'close']].reindex(idx)
H, L, C = y.high, y.low, y.close


def adx(n=14):
    up, dn = H.diff(), -L.diff()
    pdm = up.where((up > dn) & (up > 0), 0.0); ndm = dn.where((dn > up) & (dn > 0), 0.0)
    tr = pd.concat([H - L, (H - C.shift()).abs(), (L - C.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / n, adjust=False).mean()
    pdi = 100 * pdm.ewm(alpha=1 / n, adjust=False).mean() / atr; ndi = 100 * ndm.ewm(alpha=1 / n, adjust=False).mean() / atr
    dx = 100 * (pdi - ndi).abs() / (pdi + ndi)
    return dx.ewm(alpha=1 / n, adjust=False).mean()


def chop(n=14):
    tr = pd.concat([H - L, (H - C.shift()).abs(), (L - C.shift()).abs()], axis=1).max(axis=1)
    return 100 * np.log10(tr.rolling(n).sum() / (H.rolling(n).max() - L.rolling(n).min())) / np.log10(n)


def er(n):
    return (P - P.shift(n)).abs() / P.diff().abs().rolling(n).sum()


d = DSH.fillna(pd.Series((idx - pd.Timestamp('2009-01-03')).days, index=idx))
WINS = {'everywhere': pd.Series(True, index=idx), 'chop window 1080-1260': (d > 1080) & (d <= 1260),
        'wide suspicion 1000-1350': (d > 1000) & (d <= 1350)}
IND = {'ADX(14) < 20': adx() < 20, 'ADX(14) < 25': adx() < 25, 'CHOP(14) > 61.8': chop() > 61.8, 'CHOP(14) > 55': chop() > 55,
       'ER(20) < 0.2': er(20) < 0.2, 'ER(30) < 0.25': er(30) < 0.25}
S3 = rule('D', 'EMA', 'cross', 'cross', 30, 50)
HO2 = [2016, 2018]   # held-out years with OHLC data (2012 has no daily high/low)
rows = {}
def add(n, p, c=0.004):
    ho, oo = ev(p, HO2, c), ev(p, OOS, c)
    rows[n] = {'held out 2016+18': f"{ho['CAGR']:.0%} / {ho['MaxDD']:.0%}", '2016-26': f"{oo['CAGR']:.0%} / {oo['MaxDD']:.0%}",
               'Calmar 16-26': round(oo['Calmar'], 2), 'avg size': round(daily(p, c)[1][YEAR.isin(OOS)].mean(), 2)}
add('S3 100% (base)', S3)
add('S3, half size in chop window (no indicator)', S3.where(~WINS['chop window 1080-1260'], S3 * 0.5))
for wn, w in WINS.items():
    for iname, flag in IND.items():
        f = (flag.fillna(False) & w)
        add(f'{wn}: half size when {iname}', S3.where(~f, S3 * 0.5))
add('Buy & hold', HODL, 0)
t = pd.DataFrame(rows).T
print(t.to_string())

print('\n--- robustness of the ADX filter (everywhere) ---')
rows.clear()
A = adx()
for th in (20, 22.5, 25, 27.5, 30):
    for k in (0.5, 0.0):
        f = (A < th).fillna(False)
        add(f'ADX<{th}: size x{k}', S3.where(~f, S3 * k))
f = (A < 25).fillna(False) | WINS['chop window 1080-1260']
add('ADX<25 OR chop window: size x0.5', S3.where(~f, S3 * 0.5))
print(pd.DataFrame(rows).T.to_string())
for n, p in (('S3', S3), ('S3 + ADX<25 half', S3.where(~(A < 25).fillna(False), S3 * 0.5))):
    r, _ = daily(p)
    m = YEAR.isin(OOS) & r.notna(); eq = (1 + r[m]).cumprod(); dd = eq / eq.cummax() - 1
    print(n, 'worst fall', f"{dd.min():.0%}", eq.loc[:dd.idxmin()].idxmax().date(), '->', dd.idxmin().date())
    print('  by year:', {yy: f"{v:+.0%}" for yy, v in per_year(p, OOS).items()})
