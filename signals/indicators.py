"""Indicators, written to match the research code exactly."""
import numpy as np
import pandas as pd


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n).mean()


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def wilder_rsi(c: pd.Series, n: int = 2) -> pd.Series:
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=True).mean()
    dn = (-d).clip(lower=0).ewm(alpha=1 / n, adjust=True).mean()
    return 100 - 100 / (1 + up / dn)


def lower_bollinger(c: pd.Series, n: int = 20, k: float = 2.0) -> pd.Series:
    return c.rolling(n).mean() - k * c.rolling(n).std()       # sample stdev (ddof=1)


def is_trending(c: pd.Series) -> pd.Series:
    """Close above its 50-day SMA and the 50-day SMA higher than 10 sessions ago."""
    s50 = sma(c, 50)
    return (c > s50) & (s50 > s50.shift(10))


def trend_z(c: pd.Series, n: int = 1260) -> pd.Series:
    """Residual of log(close) from a straight line fitted over the last n+1 closes,
    in standard deviations of those residuals (population stdev). Trailing, point-in-time."""
    y = np.log(c.values.astype(float))
    out = np.full(len(y), np.nan)
    if len(y) <= n:
        return pd.Series(out, index=c.index)
    t = np.arange(n + 1, dtype=float)
    tm = t.mean()
    tt = t - tm
    denom = (tt ** 2).sum()
    for i in range(n, len(y)):
        yy = y[i - n:i + 1]
        b = (tt * (yy - yy.mean())).sum() / denom
        a = yy.mean() - b * tm
        res = yy - (a + b * t)
        sd = res.std()
        out[i] = res[-1] / sd if sd > 0 else np.nan
    return pd.Series(out, index=c.index)


def realised_vol(c: pd.Series, n: int = 30, periods: int = 365) -> pd.Series:
    return np.log(c).diff().rolling(n).std() * np.sqrt(periods)
