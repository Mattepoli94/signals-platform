from two import *
pd.set_option('display.width', 250)
rows = []
for tk in ('QQQ', 'SOXX'):
    c, S = steps(tk)
    for k, v in S.items(): print(tk, k, len(v), [str(d.date()) for d in v][-4:])
    plans = {'1 step: weekly 9w reclaim': (S['weekly 9w reclaim'], [], 1.0),
             '1 step: daily 9ema reclaim': (S['daily 9ema reclaim'], [], 1.0)}
    for s1 in ('breadth washout (<=20)', 'breadth turn (+10 off <=25 low)', 'fast-crash buy 1', 'daily 9ema reclaim'):
        plans[f'2 steps: {s1} + 9w reclaim'] = (S[s1], S['weekly 9w reclaim'], 0.5)
    for s1 in ('breadth washout (<=20)', 'fast-crash buy 1'):
        plans[f'1 step: {s1} only'] = (S[s1], [], 1.0)
    for name, (a, b_, w1) in plans.items():
        for stop, tgt, maxd in itertools.product([.08, .12], [.15, .25], [40, 60]):
            r = campaign(c, a, b_, stop, tgt, maxd, w1)
            for era, x0, x1 in (('to2009', '1990', '2009-12-31'), ('2010+', '2010', '2027')):
                x = r[(r.start >= x0) & (r.start <= x1)] if len(r) else r
                if not len(x): continue
                rows.append({'inst': tk, 'plan': name, 'stop': stop, 'tgt': tgt, 'maxd': maxd, 'era': era, 'n': len(x),
                             'win%': (x.ret_alloc > 0).mean() * 100, 'avg_alloc%': x.ret_alloc.mean() * 100,
                             'avg_invested%': x.ret_invested.mean() * 100, 'worst%': x.ret_alloc.min() * 100,
                             'step2_used%': x.second.mean() * 100, 'days': x.days.mean()})
R = pd.DataFrame(rows); R.to_csv('two_step.csv', index=False)
g = R.groupby(['inst', 'plan', 'era'])[['n', 'win%', 'avg_alloc%', 'avg_invested%', 'worst%', 'step2_used%', 'days']].median().unstack('era')
print(g.round(1).to_string())
