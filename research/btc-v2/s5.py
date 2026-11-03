from weng import *
from eng import RV30
pd.set_option('display.width', 220)
OOS, ALL = list(range(2016, 2027)), list(range(2012, 2027))
D = cycle(core('cross', 13, 40), 'C1', 540, 900)
D2 = cycle(core('cross', 13, 40, 'E2'), 'C1', 540, 900)
DV = D * (1.0 / RV30).clip(upper=1).fillna(1)
D2V = D2 * (1.0 / RV30).clip(upper=1).fillna(1)
rows = {}
for n, p in (('D weekly exit', D), ('D daily exit (E2)', D2), ('D + vol sizing', DV), ('D daily exit + vol sizing', D2V), ('Buy & hold', HODL)):
    c = 0 if n == 'Buy & hold' else 0.004
    for per, yrs in (('train', TRAIN), ('holdout', HOLD), ('2016-26', OOS)):
        m = ev(p, yrs, c); rows[(n, per)] = m
print(pd.DataFrame(rows).T[['CAGR', 'MaxDD', 'Calmar', 'Exposure', 'Trades/yr']].round(3).to_string())
