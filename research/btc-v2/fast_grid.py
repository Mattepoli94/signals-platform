from feng import *
import itertools, time
t0 = time.time(); rows = []
for tf in ('D', 'W', 'Wd'):
    for t, ent, ex in itertools.product(('SMA', 'EMA'), ('cross', 'close>fast'), ('cross', 'below_slow', 'below_fast')):
        if ent == 'cross' and ex == 'below_fast':
            pass
        for f, s in PAIRS['D' if tf == 'D' else 'W']:
            pos = rule(tf, t, ent, ex, f, s, True)
            tr, tr13, ho, oo = ev(pos, TRAIN), ev(pos, TR_EX13), ev(pos, HOLD), ev(pos, OOS)
            rows.append({'tf': tf, 'ma': t, 'entry': ent, 'exit': ex, 'fast': f, 'slow': s,
                         'trCalmar': tr['Calmar'], 'trCAGR': tr['CAGR'], 'trDD': tr['MaxDD'], 'trDDx13': tr13['MaxDD'], 'trCalx13': tr13['Calmar'],
                         'hoCAGR': ho['CAGR'], 'hoDD': ho['MaxDD'], 'hoCalmar': ho['Calmar'],
                         'ooCAGR': oo['CAGR'], 'ooDD': oo['MaxDD'], 'ooCalmar': oo['Calmar'], 'trades': tr['Trades/yr'], 'expo': tr['Exposure']})
g = pd.DataFrame(rows); g.to_pickle('grid.pkl'); print(len(g), 'variants', round(time.time() - t0), 's')
