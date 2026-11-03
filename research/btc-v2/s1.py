from weng import *
pd.set_option('display.width', 220)
for exe in ('E1', 'E2'):
    g = pd.DataFrame(index=FAST, columns=SLOW, dtype=float)
    for f in FAST:
        for s in SLOW:
            if f < s:
                g.loc[f, s] = ev(core('cross', f, s, exe))['Calmar']
    print(f'\nEMA cross, {exe}: training Calmar (rows fast, cols slow, weeks)'); print(g.round(2).to_string())
    a = pd.Series({n: ev(core('above', n, None, exe))['Calmar'] for n in NS})
    print(f'close > weekly EMA n, {exe}:', a.round(2).to_dict())
print('\nHODL train', {k: round(v, 3) for k, v in ev(HODL, cost=0).items()})
