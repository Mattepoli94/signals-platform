from feng import *
g = pd.read_pickle('grid.pkl')
F = {'D': (10, 20, 30, 50), 'W': (5, 10, 13, 20), 'Wd': (5, 10, 13, 20)}
S = {'D': (50, 100, 150, 200), 'W': (20, 30, 40, 50), 'Wd': (20, 30, 40, 50)}
def nb(r):
    fam = g[(g.tf == r.tf) & (g.ma == r.ma) & (g.entry == r.entry) & (g.exit == r.exit)]
    fi, si = F[r.tf].index(r.fast), S[r.tf].index(r.slow)
    n = fam[[abs(F[r.tf].index(a) - fi) + abs(S[r.tf].index(b) - si) == 1 for a, b in zip(fam.fast, fam.slow)]]
    return n.trCalmar.mean()
g['nb'] = g.apply(nb, axis=1)
g['plateau'] = g.nb >= 0.85 * g.trCalmar
pd.set_option('display.width', 250)
cols = ['tf','ma','entry','exit','fast','slow','trCalmar','nb','trDDx13','hoCAGR','hoDD','hoCalmar','ooCAGR','ooDD','ooCalmar','trades']
sel = g[g.plateau].sort_values('trCalmar', ascending=False)
print('Plateau-passing rules, by training Calmar:'); print(sel[cols].head(12).round(2).to_string(index=False))
g.to_pickle('grid_nb.pkl')
