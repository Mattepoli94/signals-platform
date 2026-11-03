import pandas as pd, numpy as np
RD = '/home/claude/rd/research-data/'

def prices():
    p = pd.read_csv(RD + 'prices.csv', parse_dates=['date'])
    return {t: g.set_index('date').sort_index() for t, g in p.groupby('ticker')}

def breadth():
    b = pd.read_csv(RD + 'breadth/breadth.csv', parse_dates=['date']).set_index('date').sort_index()
    return b

def weekly(df, col='adj_close'):
    """Friday-ending weekly bars from daily data (last available day of each week)."""
    s = df[col].dropna()
    w = s.resample('W-FRI').last().dropna()
    lastday = s.index.to_series().resample('W-FRI').last().dropna()
    w.index = lastday.reindex(w.index).values  # actual last trading date of the week
    return w

def wk_low(df):
    s = df['adj_close'].dropna() * (df['low'] / df['close']).reindex(df['adj_close'].dropna().index).fillna(1)
    return s

def stats(eq):
    eq = eq.dropna()
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1
    dd = (eq / eq.cummax() - 1).min()
    return cagr, dd
