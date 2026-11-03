import pandas as pd, numpy as np
from swing import *
SECT = ['XLK','IGV','SMH','SOXX','XSD','FDN','SKYY','CIBR','XLY','XHB','ITB','XRT','IBB','XBI','ARKK','TAN','ICLN','PBW','XLC','IWM','XLI','ITA','XME','IYT','KRE']
Pfull = prices()
S = pd.DataFrame({t: Pfull[t]['adj_close'] for t in SECT if t in Pfull}).sort_index()
S = S[(S.index >= '1999-01-01') & (S.index < '2026-11-03')]
q = Pfull['QQQ']['adj_close'].reindex(S.index).ffill()
# event dates: QQQ daily 9-EMA reclaim while the setup is armed, first per campaign (>= 40 sessions apart)
c, ent = daily_signals(Pfull['QQQ']['adj_close'][lambda s: (s.index >= '1999-06-01') & (s.index < '2026-11-03')], 'daily 9ema cross, setup armed')
ev, last = [], None
for i in ent:
    d = c.index[i]
    if last is None or (c.index.get_loc(d) - c.index.get_loc(last)) >= 40: ev.append(d); last = d
ev = [d for d in ev if d >= pd.Timestamp('2001-01-01')]
rows = []
for d in ev:
    i = S.index.get_loc(d)
    hi_d = q.iloc[max(0, i - 126):i + 1].idxmax()            # market high before the flush
    lo_d = q.loc[hi_d:d].idxmin()                            # market low so far
    avail = [t for t in S.columns if S[t].iloc[max(0, i - 260):i + 1].notna().all() and i + 126 < len(S) and pd.notna(S[t].iloc[min(i + 126, len(S) - 1)])]
    if len(avail) < 6: continue
    X = S[avail]
    rs12 = X.iloc[i - 21] / X.iloc[i - 252] - 1
    resil = X.iloc[i] / X.loc[hi_d:d].max() - 1                          # drawdown from own high since the flush started (higher = held up)
    bounce = X.iloc[i] / X.loc[lo_d] - 1                                 # rebound from the market low
    flushret = X.loc[lo_d] / X.loc[hi_d] - 1
    f63, f126 = X.iloc[i + 63] / X.iloc[i] - 1, X.iloc[i + 126] / X.iloc[i] - 1
    ew63, ew126 = f63.mean(), f126.mean()
    q63, q126 = q.iloc[i + 63] / q.iloc[i] - 1, q.iloc[i + 126] / q.iloc[i] - 1
    for name, sc in (('12m leaders (pre-flush RS)', rs12), ('held up best in the flush', resil), ('fell most in the flush', -flushret),
                     ('strongest bounce off the low', bounce), ('weakest bounce', -bounce)):
        top = sc.sort_values(ascending=False).index[:3]
        rows.append({'date': d, 'rank': name, 'n_etf': len(avail), 'top3': ','.join(top),
                     'r63': f63[top].mean(), 'r126': f126[top].mean(), 'xs_ew63': f63[top].mean() - ew63, 'xs_ew126': f126[top].mean() - ew126,
                     'xs_q63': f63[top].mean() - q63, 'xs_q126': f126[top].mean() - q126, 'ew126': ew126, 'q126': q126})
R = pd.DataFrame(rows); R.to_csv('sectors_events.csv', index=False)
pd.set_option('display.width', 250)
print('events:', R.date.nunique(), sorted({str(x.date()) for x in R.date}))
R['era'] = np.where(R.date < '2010-01-01', 'to2009', '2010+')
agg = R.groupby(['rank', 'era']).agg(n=('r126', 'size'), r63=('r63', 'mean'), r126=('r126', 'mean'), xs_ew126=('xs_ew126', 'mean'),
                                     beat_ew126=('xs_ew126', lambda s: (s > 0).mean()), xs_q126=('xs_q126', 'mean'), beat_q126=('xs_q126', lambda s: (s > 0).mean()), xs_ew63=('xs_ew63', 'mean'))
print((agg * pd.Series({'n': 1, 'r63': 100, 'r126': 100, 'xs_ew126': 100, 'beat_ew126': 100, 'xs_q126': 100, 'beat_q126': 100, 'xs_ew63': 100})).round(1).to_string())
print(R[R['rank'] == 'held up best in the flush'][['date', 'top3', 'xs_ew126']].round(3).to_string(index=False))
print(R[R['rank'] == '12m leaders (pre-flush RS)'][['date', 'top3', 'xs_ew126']].round(3).to_string(index=False))
