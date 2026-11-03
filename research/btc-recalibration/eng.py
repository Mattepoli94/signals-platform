"""Masked-year engine for the BTC recalibration (see PREREG.md)."""
import sys; sys.path.insert(0, '/home/claude/btc')
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
import btc_cm as B

P = B.P.loc[:'2026-10-31']
idx = P.index
dr = pd.read_csv('/home/claude/data/prices/dollar_rates.csv', parse_dates=['date']).drop_duplicates(['ticker', 'date'])
irx = dr[dr.ticker == '^IRX'].set_index('date').close.dropna()
irx.index = irx.index + pd.Timedelta(days=1)
IRX = (irx.reindex(irx.index.union(idx)).ffill().reindex(idx).fillna(2.0) / 100 / 365)
R = P.pct_change().shift(-1)                      # return earned by a position decided at close t
COST = 0.0010
HOLD = [2018, 2016, 2012]
TRAIN = [y for y in range(2012, 2027) if y not in HOLD]
YEAR = pd.Series(idx.year, index=idx)
HALV = pd.to_datetime(['2012-11-28', '2016-07-09', '2020-05-11', '2024-04-20'])
DSH = pd.Series([(d - HALV[HALV <= d][-1]).days if (HALV <= d).any() else np.nan for d in idx], index=idx)
CYCLES = [('2012-11-28', '2016-07-08'), ('2016-07-09', '2020-05-10'), ('2020-05-11', '2024-04-19'), ('2024-04-20', '2026-10-31')]
RV30 = np.log(P).diff().rolling(30).std() * np.sqrt(365)


def daily(pos):
    pos = pos.reindex(idx).fillna(0).clip(0, 1)
    turn = pos.diff().abs().fillna(pos)
    return pos * R + (1 - pos) * IRX - turn * COST, pos


def stats(ret, pos, mask):
    m = mask & ret.notna()
    r, p = ret[m], pos[m]
    if len(r) < 30:
        return {}
    eq = (1 + r).cumprod(); yrs = len(r) / 365
    cagr = eq.iloc[-1] ** (1 / yrs) - 1; dd = (eq / eq.cummax() - 1).min()
    on = p > 0; g = (on != on.shift()).cumsum()[on]
    return {'CAGR': cagr, 'MaxDD': dd, 'Calmar': cagr / -dd if dd < 0 else np.nan,
            'Sharpe': r.mean() / r.std() * np.sqrt(365), 'Exposure': p.mean(), 'Trades/yr': g.nunique() / yrs}


def mask_years(years):
    return YEAR.isin(years)


def evaluate(pos, years=None):
    years = years or TRAIN
    ret, p = daily(pos)
    return stats(ret, p, mask_years(years))


def per_year(pos, years):
    ret, p = daily(pos)
    return {y: (1 + ret[(YEAR == y) & ret.notna()]).prod() - 1 for y in years}


def per_cycle(pos, years=None):
    years = years or TRAIN
    ret, p = daily(pos)
    out = {}
    for a, b in CYCLES:
        m = (idx >= a) & (idx <= b) & mask_years(years).values
        out[a[:4]] = stats(ret, p, pd.Series(m, index=idx)).get('Calmar', np.nan)
    return out


# ---------------- candidate rules ----------------
ema = lambda n: P.ewm(span=n, adjust=False).mean()
sma = lambda n: P.rolling(n).mean()
LENS = [10, 20, 30, 50, 100, 150, 200]
MA_LENS = [20, 30, 50, 75, 100, 150, 200]
CORES = {}
for n in LENS:
    CORES[('momentum', n)] = (P > P.shift(n)).astype(float)
for n in MA_LENS:
    CORES[('above EMA', n)] = (P > ema(n)).astype(float)
    CORES[('above SMA', n)] = (P > sma(n)).astype(float)
for f, s in ((10, 30), (20, 50), (20, 100), (50, 200)):
    CORES[('EMA cross', f'{f}/{s}')] = (ema(f) > ema(s)).astype(float)
CORES[('blend', 'vote 10/20/50')] = sum((P > P.shift(n)).astype(float) for n in (10, 20, 50)) / 3
CORES[('blend', 'v1 five-signal')] = ((P > P.shift(10)).astype(float) + (P > P.shift(20)).astype(float) + (P > P.shift(50)).astype(float)
                                      + (P > ema(50)).astype(float) + (ema(10) > ema(30)).astype(float)) / 5


def vol_size(pos, target):
    return pos if target is None else pos * (target / RV30).clip(upper=1).fillna(1)


def halving(pos, a, b):
    if a is None:
        return pos
    win = (DSH > a) & (DSH <= b)
    return pos.where(~win, 0.0)


OLD = halving(vol_size(CORES[('blend', 'v1 five-signal')], 0.8), 545, 910)
HODL = pd.Series(1.0, index=idx)
