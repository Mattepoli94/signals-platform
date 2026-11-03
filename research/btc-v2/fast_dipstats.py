exec(open('dip.py').read().split("HO2 = [2016, 2018]")[0])
def leg_only(trig, stop, days, tp):
    full = dip_leg(trig, stop, days, tp)
    return (full > BASE).astype(float)        # days when the dip leg adds exposure
for name, trg in (('RSI(14) < 30', TRIG['RSI(14) < 30']), ('touch 20-week SMA', TRIG['touch 20-week SMA']), ('30% below 90-day high', TRIG['30% below 90-day high'])):
    on = leg_only(trg, 0.15, 40, 'ema30')
    starts = on[(on == 1) & (on.shift(1, fill_value=0) == 0)].index
    res = []
    for s in starts:
        e = on.loc[s:]; e = e[e == 0].index[0] if (e == 0).any() else on.index[-1]
        res.append(P.loc[e] / P.loc[s] - 1)
    res = np.array(res); yrs = [s.year for s in starts]
    print(f"{name}: {len(res)} dip trades 2012-26 ({len(res)/14.8:.1f}/yr), win {np.mean(res>0):.0%}, avg {res.mean():+.1%}, worst {res.min():+.1%}, years {sorted(set(yrs))}")
