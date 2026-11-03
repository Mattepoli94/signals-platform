import itertools
exec(open('chopind.py').read().split("d = DSH.fillna")[0])     # data + indicators (adx, er)
d = DSH.fillna(pd.Series((idx - pd.Timestamp('2009-01-03')).days, index=idx))
S3 = rule('D', 'EMA', 'cross', 'cross', 30, 50)
A = adx()
half = ((A < 25).fillna(False) | ((d > 1080) & (d <= 1260)))
BASE = S3.where(~half, S3 * 0.5)                                  # S3 v2
BEAR = ((d > 540) & (d <= 900)).values
sma = lambda n: P.rolling(n).mean(); ema = lambda n: P.ewm(span=n, adjust=False).mean()
def rsi(n):
    dd = P.diff(); up = dd.clip(lower=0).ewm(alpha=1/n, adjust=False).mean(); dn = (-dd).clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)
W20 = to_d(W.rolling(20).mean())                                   # 20-week SMA (bull market support), known at week close
BULL = (sma(200) > sma(200).shift(20)) & (P > sma(200) * 0.9)      # rising 200-day, price not far below it
TRIG = {
 'touch 20-week SMA': P <= W20 * 1.0,
 'within 3% of 20-week SMA': P <= W20 * 1.03,
 '25% below 90-day high': P <= P.rolling(90).max() * 0.75,
 '30% below 90-day high': P <= P.rolling(90).max() * 0.70,
 'RSI(14) < 35': rsi(14) < 35,
 'RSI(14) < 30': rsi(14) < 30,
 'close <= 200-day SMA (in bull)': P <= sma(200),
}
def dip_leg(trig, stop, days, tp):
    t, b, base = trig.fillna(False).values, BULL.fillna(False).values, BASE.values
    r14 = rsi(14).values; c = P.values; e30 = ema(30).values
    out = np.zeros(len(c)); s = 0; entry = 0; n = 0
    for i in range(len(c)):
        if BEAR[i]:
            s = 0
        elif s == 0:
            if b[i] and t[i] and base[i] < 1:
                s, entry, n = 1, c[i], 0
        else:
            n += 1
            if c[i] <= entry * (1 - stop) or n >= days or (tp == 'rsi' and r14[i] > 60) or (tp == 'ema30' and c[i] > e30[i]) or base[i] >= 1:
                s = 0
        out[i] = s
    return pd.Series(np.maximum(out, base), index=idx)
HO2 = [2016, 2018]
rows = {}
def add(n, p, c=0.004):
    ho, oo, tr = ev(p, HO2, c), ev(p, OOS, c), ev(p, [y for y in TRAIN if y >= 2015], c)
    rows[n] = {'train 2015+': f"{tr['CAGR']:.0%} / {tr['MaxDD']:.0%}", 'held out 2016+18': f"{ho['CAGR']:.0%} / {ho['MaxDD']:.0%}",
               '2016-26': f"{oo['CAGR']:.0%} / {oo['MaxDD']:.0%}", 'Calmar 16-26': round(oo['Calmar'], 2), 'cal_tr': tr['Calmar']}
add('S3 v2 (no dip leg)', BASE)
for (tn, trg), stop, days, tp in itertools.product(TRIG.items(), (0.10, 0.15), (20, 40), ('rsi', 'ema30')):
    add(f'{tn} | stop {int(stop*100)}% | {days}d | exit {tp}', dip_leg(trg, stop, days, tp))
add('Buy & hold', HODL, 0)
t = pd.DataFrame(rows).T
pd.set_option('display.width', 260)
print(t.loc[['S3 v2 (no dip leg)', 'Buy & hold']].drop(columns='cal_tr').to_string())
print('\nTop 12 dip variants by TRAINING (2015+ training years) Calmar:')
print(t.drop(['S3 v2 (no dip leg)', 'Buy & hold']).sort_values('cal_tr', ascending=False).head(12).drop(columns='cal_tr').to_string())
t['trig'] = [i.split(' |')[0] for i in t.index]
print('\nMedian 2016-26 Calmar by trigger:', t.drop(['S3 v2 (no dip leg)', 'Buy & hold']).groupby('trig')['Calmar 16-26'].median().round(2).to_dict())
t.to_pickle('dip.pkl')
