"""ONE run on the held-out years (2012, 2016, 2018). System fixed before this file was written."""
from eng import *
NEW = vol_size(CORES[('above EMA', 100)], 1.0)
INFO_WIN = halving(NEW, 545, 820)    # information only: the window the grid liked best, rejected by the 20% rule
pd.set_option('display.width', 220)
rows = {}
for name, pos in (('NEW: close > EMA100, vol 100%', NEW), ('OLD v1: blend + vol 80% + halving window', OLD),
                  ('HODL', HODL), ('(info) NEW + window 545-820', INFO_WIN)):
    for per, yrs in (('TRAIN', TRAIN), ('HOLDOUT', HOLD)):
        rows[(name, per)] = evaluate(pos, yrs)
print(pd.DataFrame(rows).T.round(3).to_string())
for name, pos in (('NEW', NEW), ('OLD', OLD), ('HODL', HODL), ('NEW+win', INFO_WIN)):
    print(name, 'holdout years:', {y: f"{v:+.0%}" for y, v in per_year(pos, HOLD).items()})
tr, ho = evaluate(NEW, TRAIN), evaluate(NEW, HOLD); hh = evaluate(HODL, HOLD)
adopt = ho['CAGR'] > 0 and ho['MaxDD'] > hh['MaxDD'] and ho['Calmar'] >= 0.5 * tr['Calmar']
print('\nADOPTION RULE: holdout CAGR>0:', ho['CAGR'] > 0, '| MaxDD better than HODL:', ho['MaxDD'] > hh['MaxDD'],
      '| holdout Calmar >= 50% of train:', round(ho['Calmar'], 2), 'vs', round(0.5 * tr['Calmar'], 2), '->', 'ADOPT' if adopt else 'DO NOT ADOPT')
full = evaluate(NEW, list(range(2012, 2027))); print('NEW full 2012-2026:', {k: round(v, 3) for k, v in full.items()})
print('NEW 2015-2026:', {k: round(v, 3) for k, v in evaluate(NEW, list(range(2015, 2027))).items()})
print('OLD 2015-2026:', {k: round(v, 3) for k, v in evaluate(OLD, list(range(2015, 2027))).items()})
print('HODL 2015-2026:', {k: round(v, 3) for k, v in evaluate(HODL, list(range(2015, 2027))).items()})
