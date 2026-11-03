import sys, itertools; sys.path.insert(0, '/home/claude/signals-platform')
from swing import *
from signals.strategies.qqq_regime import regime_core
from signals.strategies import STRATEGIES
ADX = None
pd.set_option('display.width', 250)
rows = []
for tk, st in (('QQQ', '1999-06-01'), ('SOXX', '2001-12-01')):
    df = P[tk][P[tk].index >= st]; c = df['adj_close'].dropna(); f = c / df['close']
    hi, lo = df['high'] * f, df['low'] * f
    reg = regime_core(c, STRATEGIES['qqq_regime'].params)['regime']
    w, m9, x = cross_up(c)
    e9 = c.ewm(span=9, adjust=False).mean()
    h50 = c.rolling(50).max().shift(1); bo = (c > h50); bo = bo & ~bo.rolling(10).max().shift(1).fillna(0).astype(bool)
    wh10 = w.rolling(10).max().shift(1); wbo = (w > wh10) & ~((w > wh10).shift(1).fillna(False))
    E = {'weekly 9w reclaim': list(w.index[x]),
         'daily 9ema reclaim': list(c.index[(c > e9) & (c.shift(1) <= e9.shift(1))]),
         'breakout: new 50-day closing high': list(c.index[bo]),
         'weekly breakout: above 10-week high': list(w.index[wbo]),
         'random (every day)': list(c.index)}
    ca = c.values
    for name, ds in E.items():
        ix = [c.index.get_loc(d) for d in ds]
        for stop, tgt, maxd in itertools.product([.05, .08], [.08, .15], [20, 40]):
            for era, a, b in (('to2009', '1990', '2009-12-31'), ('2010+', '2010', '2027')):
                for regname in ('Trending', 'Range above 200-day', 'Below 200-day'):
                    sel = [i for i in ix if a <= str(c.index[i].date()) <= b and reg.iloc[i] == regname]
                    tr = sim(ca, sel, stop, tgt, maxd) if name != 'random (every day)' else \
                        [ (lambda p: (p[(np.where((p <= -stop) | (p >= tgt))[0][0] if ((p <= -stop) | (p >= tgt)).any() else len(p) - 1)] - COST, 0))(ca[i + 1:i + 1 + maxd] / ca[i] - 1) for i in sel if i < len(ca) - 2]
                    if not tr: continue
                    r = np.array([t[0] for t in tr])
                    rows.append({'inst': tk, 'entry': name, 'regime': regname, 'era': era, 'stop': stop, 'tgt': tgt, 'maxd': maxd,
                                 'n': len(r), 'win%': (r > 0).mean() * 100, 'avg%': r.mean() * 100})
R = pd.DataFrame(rows)
g = R.groupby(['inst', 'regime', 'entry', 'era'])[['n', 'win%', 'avg%']].median().unstack('era')
rnd = R[R.entry == 'random (every day)'].groupby(['inst', 'regime', 'era', 'stop', 'tgt', 'maxd'])['avg%'].first()
R['edge'] = R.apply(lambda r: r['avg%'] - rnd.get((r.inst, r.regime, r.era, r.stop, r.tgt, r.maxd), np.nan), axis=1)
g2 = R.groupby(['inst', 'regime', 'entry', 'era'])['edge'].median().unstack('era')
out = g.round(1); out[('edge vs random', 'to2009')] = g2['to2009'].round(2); out[('edge vs random', '2010+')] = g2['2010+'].round(2)
print(out.to_string())
