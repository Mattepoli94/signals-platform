from swing import *
pd.set_option('display.width', 250)
rows = []
for tk, st in (('QQQ', '1999-06-01'), ('SPY', '1993-06-01'), ('SOXX', '2001-12-01')):
    px = P[tk]['adj_close'].dropna(); px = px[px.index >= st]
    for kind in ('setup', 'cross+flush', 'any 9w cross', 'every week (random-like)', 'daily 9ema cross, setup armed'):
        c, ent = daily_signals(px, kind); ca = c.values
        for stop, tgt, maxd in itertools.product([.05, .08, .12], [.08, .15, .25], [20, 40, 60]):
            for era, a, b in (('to2009', '1990', '2009-12-31'), ('2010+', '2010-01-01', '2027')):
                idx = [i for i in ent if a <= str(c.index[i].date()) <= b]
                yrs = (min(c.index[-1], pd.Timestamp(b)) - max(c.index[0], pd.Timestamp(a))).days / 365.25
                s = summ(sim(ca, idx, stop, tgt, maxd), yrs)
                rows.append({'inst': tk, 'entry': kind, 'stop': stop, 'tgt': tgt, 'maxd': maxd, 'era': era, **s})
R = pd.DataFrame(rows); R.to_csv('swing_idx.csv', index=False)
# robustness view: median over the 27 exit settings
g = R.groupby(['inst', 'entry', 'era'])[['trades', 'win%', 'avg%', 'PF', 'cagr%', 'exposure%']].median().unstack('era')
print(g.round(2).to_string())
