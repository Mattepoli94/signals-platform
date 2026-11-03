from eng import *
NEW = vol_size(CORES[('above EMA', 100)], 1.0)
ret, p = daily(NEW)
m = mask_years(TRAIN) & ret.notna()
eq = (1 + ret[m]).cumprod(); dd = eq / eq.cummax() - 1
trough = dd.idxmin(); peak = eq.loc[:trough].idxmax()
print('NEW train MaxDD', round(dd.min(), 3), 'peak', peak.date(), 'trough', trough.date())
print('NEW per training year:', {y: f"{v:+.0%}" for y, v in per_year(NEW, TRAIN).items()})
print('HODL per training year:', {y: f"{v:+.0%}" for y, v in per_year(HODL, TRAIN).items()})
print('OLD per training year:', {y: f"{v:+.0%}" for y, v in per_year(OLD, TRAIN).items()})
# era consistency: train Calmar by cycle for new vs hodl
print('cycle Calmar NEW', {k: round(v, 2) for k, v in per_cycle(NEW).items()}, 'HODL', {k: round(v, 2) for k, v in per_cycle(HODL).items()})
