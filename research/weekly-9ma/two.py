"""Two-step entries for the swing setup (QQQ, SOXX)."""
import sys, itertools, json; sys.path.insert(0, '/home/claude/signals-platform')
from swing import *
Bd = B['all_above50'].dropna()
def soxx_plan_dates(c):
    """SOXX fast crash (version B from the bottoms research): -11.5% in 15 sessions from within 4% of the 3-month high;
    buy 1 at the first close 12% below that high, within 40 sessions. Override ignored here."""
    hi = c.rolling(63, min_periods=40).max(); out = []; i = 15; n = len(c)
    while i < n:
        if c.iloc[i] / c.iloc[i - 15:i].max() - 1 <= -0.115 and c.iloc[i - 15:i].max() >= hi.iloc[i - 15] * 0.96:
            ref = c.iloc[i - 15:i].max()
            for j in range(i, min(i + 40, n)):
                if c.iloc[j] <= ref * 0.88: out.append(c.index[j]); break
            i += 40
        else: i += 1
    return out
def steps(tk):
    px = P[tk]['adj_close'].dropna(); px = px[px.index >= ('1999-06-01' if tk == 'QQQ' else '2001-12-01')]
    c = px; w, m9, x = cross_up(c)
    cond = W.reindex(w.index).ffill(); armedW = cond['flush'] & cond['mm_bottom']
    armedD = armedW.reindex(c.index, method='ffill').fillna(False); flushD = cond['flush'].reindex(c.index, method='ffill').fillna(False)
    e9 = c.ewm(span=9, adjust=False).mean(); dx = (c > e9) & (c.shift(1) <= e9.shift(1))
    bd = Bd.reindex(c.index).ffill(); low20 = bd.rolling(30, min_periods=1).min()
    S = {}
    S['weekly 9w reclaim'] = list(w.index[x & armedW])
    S['daily 9ema reclaim'] = list(c.index[dx & armedD])
    # breadth washout: first close with breadth <= 20 while QQQ/SPY flush is on (deleveraging), and the turn: breadth +10 off a <=25 low
    S['breadth washout (<=20)'] = list(c.index[(bd <= 20) & (bd.shift(1) > 20) & flushD])
    S['breadth turn (+10 off <=25 low)'] = list(c.index[(low20 <= 25) & (bd >= low20 + 10) & ~((low20.shift(1) <= 25) & (bd.shift(1) >= low20.shift(1) + 10))])
    if tk == 'QQQ':
        fp = json.load(open('fastplans.json'))
        S['fast-crash buy 1'] = [pd.Timestamp(p['buy1']) for p in fp if p['buy1'] and not p['skipped']]
    else:
        S['fast-crash buy 1'] = soxx_plan_dates(c)
    return c, S

def campaign(c, s1, s2, stop, tgt, maxd, w1=0.5, wait=40):
    """Tranche 1 (w1) at a step-1 date; tranche 2 at the first step-2 date within `wait` sessions (if not stopped out).
    Exits on the whole position vs average cost. If w1 == 1: single entry at s1. If w1 == 0: single entry at s2.
    Returns per-campaign return on the full allocation (unused part earns 0)."""
    ca = c.values; ix = {d: i for i, d in enumerate(c.index)}
    s1i = sorted(ix[d] for d in s1 if d in ix); s2i = sorted(ix[d] for d in s2 if d in ix)
    res = []; busy = -1
    for i in s1i:
        if i <= busy or i >= len(ca) - 2: continue
        units = w1 / ca[i]; cost = w1; second = w1 >= 1; t_last = i
        k = i; end = min(i + maxd, len(ca) - 1); exit_k = end
        while k < end:
            k += 1
            if not second and k in set(s2i) and k - i <= wait:
                units += (1 - w1) / ca[k]; cost += (1 - w1); second = True; end = min(k + maxd, len(ca) - 1)
            val = units * ca[k]; avg = cost / units
            if ca[k] <= avg * (1 - stop) or ca[k] >= avg * (1 + tgt): exit_k = k; break
            if not second and k - i > wait: exit_k = k; break     # step 2 never came: close tranche 1
        pnl = units * ca[exit_k] - cost - cost * COST
        low = ca[i:exit_k + 1].min()
        res.append({'start': c.index[i], 'ret_alloc': pnl, 'ret_invested': pnl / cost, 'invested': cost, 'days': exit_k - i,
                    'second': second, 'avg_vs_start': (cost / units) / ca[i] - 1})
        busy = exit_k
    return pd.DataFrame(res)
