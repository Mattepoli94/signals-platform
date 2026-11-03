from weng import *
pd.set_option('display.width', 220)
from eng import RV30
X = core('cross', 13, 40); D = cycle(X, 'C1', 540, 900)
ret, p = daily(D); OOS = list(range(2016, 2027))
m = YEAR.isin(OOS) & ret.notna(); eq = (1 + ret[m]).cumprod(); dd = eq / eq.cummax() - 1
print('D worst fall 2016-26:', round(dd.min(), 3), 'peak', eq.loc[:dd.idxmin()].idxmax().date(), 'trough', dd.idxmin().date())
lag = D.shift(1).fillna(0)                      # executed one day later (Monday, ETF route)
rows = {
 'Kraken limit 0.40%/side': ev(D, list(range(2012, 2027)), 0.004),
 'Kraken market 0.80%/side': ev(D, list(range(2012, 2027)), 0.008),
 'ETF 0.05%/side + 0.25%/yr, traded next day': ev(lag, list(range(2012, 2027)), 0.0005, 0.0025),
 'ETF in ISA via T212 USD line (+0.15% FX)': ev(lag, list(range(2012, 2027)), 0.002, 0.0025),
}
print(pd.DataFrame(rows).T[['CAGR', 'MaxDD', 'Calmar', 'Trades/yr']].round(3).to_string())
# number of trade sides per year
sides = (D.diff().abs() > 0).groupby(YEAR).sum().loc[2012:2026]; print('trade sides per year:', sides.to_dict())
# sensitivity of the knowledge window and the EMA pair (plateau check)
g = {}
for f, s in ((10, 30), (10, 40), (13, 30), (13, 40), (13, 50), (20, 40), (20, 50)):
    for a, b in ((500, 850), (540, 900), (580, 950)):
        q = cycle(core('cross', f, s), 'C1', a, b)
        g[(f'{f}/{s}', f'{a}-{b}')] = (ev(q, TRAIN)['Calmar'], ev(q, HOLD)['Calmar'], ev(q, OOS)['Calmar'])
t = pd.DataFrame(g, index=['train', 'holdout', '2016-26']).T
print('\nNeighbourhood (Calmar):'); print(t.round(2).to_string())
