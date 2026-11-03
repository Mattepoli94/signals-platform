from swing import *
C = pd.read_csv(RD + 'breadth/closes.csv.gz', index_col=0, parse_dates=True); C = C[(C.index < '2026-11-03') & (C.index >= '1995-01-01')]
spx = P['^GSPC']['adj_close'].reindex(C.index).ffill().values
g = C.index.to_period('W-FRI'); lastday = C.index.to_series().groupby(g).last()
Wc = C.groupby(g).last(); Wc.index = lastday.values
ma = Wc.rolling(9).mean(); wx = (Wc > ma) & (Wc.shift(1) <= ma.shift(1))
rs = (Wc / Wc.shift(52) - 1).rank(axis=1, pct=True)
cond = W.reindex(Wc.index).ffill(); armedW = cond['flush'] & cond['mm_bottom']; flushW = cond['flush']
armedD = armedW.reindex(C.index, method='ffill').fillna(False)
e9 = C.ewm(span=9, adjust=False).mean(); dx = (C > e9) & (C.shift(1) <= e9.shift(1))
pos = {d: i for i, d in enumerate(C.index)}
A = C.values
def run(sigmask, stop=.08, tgt=.15, maxd=40, weekly=True):
    res = []
    idx = sigmask.index
    for j, col in enumerate(C.columns):
        s = sigmask[col].values; dates = idx[s]
        c = A[:, j]; busy = -1
        for d in dates:
            i = pos[d]
            if i <= busy or i >= len(c) - 2 or np.isnan(c[i]): continue
            path = c[i + 1:i + 1 + maxd] / c[i] - 1
            if np.isnan(path).any(): continue
            hit = np.where((path <= -stop) | (path >= tgt))[0]; k = hit[0] if len(hit) else len(path) - 1
            r = path[k] - COST; sp = spx[i + 1 + k] / spx[i] - 1
            res.append((d, r, sp, k + 1)); busy = i + k + 1
    return pd.DataFrame(res, columns=['date', 'ret', 'spx', 'days'])
def S(df, lab):
    out = {}
    for era, a, b in (('1995-2009', '1995', '2009-12-31'), ('2010-2026', '2010', '2027')):
        x = df[(df.date >= a) & (df.date <= b)]
        out[era] = {'label': lab, 'trades': len(x), 'win%': round((x.ret > 0).mean() * 100), 'avg%': round(x.ret.mean() * 100, 2),
                    'vs SPX%': round((x.ret - x.spx).mean() * 100, 2), 'beat SPX%': round(((x.ret - x.spx) > 0).mean() * 100),
                    'PF': round(x.ret[x.ret > 0].sum() / -x.ret[x.ret <= 0].sum(), 2), 'days': round(x.days.mean())}
    return out
Wm = lambda m: pd.DataFrame(np.repeat(m.values[:, None], Wc.shape[1], 1), index=Wc.index, columns=Wc.columns)
Dm = lambda m: pd.DataFrame(np.repeat(m.values[:, None], C.shape[1], 1), index=C.index, columns=C.columns)
tests = {'weekly 9w cross, any time': wx, 'weekly cross in setup': wx & Wm(armedW), 'weekly cross outside flush': wx & Wm(~flushW),
         'weekly cross in setup, RS leaders (top 30%)': wx & Wm(armedW) & (rs >= .7),
         'daily 9ema cross, setup armed': dx & Dm(armedD), 'daily 9ema cross, not armed': dx & Dm(~armedD)}
rows = []
for lab, m in tests.items():
    r = run(m.fillna(False)); r.to_pickle(f'sw_{lab[:20].replace(" ", "_")}.pkl')
    for era, v in S(r, lab).items(): rows.append({'era': era, **v})
pd.set_option('display.width', 250); print(pd.DataFrame(rows).set_index(['era', 'label']).to_string())
