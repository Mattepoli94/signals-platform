from feng import *
from eng import RV30
pd.set_option('display.width', 250)

def trail(pos, pct):
    """Exit when the close falls pct below its highest close since entry; re-enter only after the trend signal resets (flat then on)."""
    p, c = pos.values, P.values; out = np.zeros(len(p)); s = 0; hi = 0; blocked = False
    for i in range(len(p)):
        if p[i] == 0:
            blocked = False
        if s == 0 and p[i] > 0 and not blocked:
            s, hi = 1, c[i]
        elif s == 1:
            hi = max(hi, c[i])
            if p[i] == 0:
                s = 0
            elif c[i] <= hi * (1 - pct):
                s, blocked = 0, True
        out[i] = s
    return pd.Series(out, index=idx)

def vol(pos, tg):
    return pos * (tg / RV30).clip(upper=1).fillna(1)

rows = []
for f, s in PAIRS['D']:
    base = rule('D', 'EMA', 'cross', 'cross', f, s)
    for name, p in [('none', base)] + [(f'trail {int(x*100)}%', trail(base, x)) for x in (0.15, 0.20, 0.25, 0.30)] + \
                   [(f'vol {int(v*100)}%', vol(base, v)) for v in (0.5, 0.6, 0.8)]:
        tr, ho, oo = ev(p, TRAIN), ev(p, HOLD), ev(p, OOS)
        tr13 = ev(p, TR_EX13)
        rows.append({'pair': f'{f}/{s}', 'overlay': name, 'trCalx13': tr13['Calmar'], 'trDDx13': tr13['MaxDD'], 'trCAGR': tr['CAGR'],
                     'hoCAGR': ho['CAGR'], 'hoDD': ho['MaxDD'], 'ooCAGR': oo['CAGR'], 'ooDD': oo['MaxDD'], 'ooCalmar': oo['Calmar'], 'trades': tr['Trades/yr']})
t = pd.DataFrame(rows)
print('Median across the 12 daily EMA cross pairs, by overlay:')
print(t.groupby('overlay')[['trCalx13', 'trDDx13', 'trCAGR', 'hoCAGR', 'hoDD', 'ooCAGR', 'ooDD', 'ooCalmar', 'trades']].median().round(2).to_string())
t.to_pickle('overlay.pkl')
