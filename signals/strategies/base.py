"""Strategy plug-in interface.

A strategy turns stored price data into a daily signal table. Two kinds:
  * 'weights'    - the table has target weights `w_<ASSET>` (share of the pot's value) and a
                   `state` column; the pot trades to the target whenever `state` changes, or when
                   the actual weight drifts more than `band` away from the target.
  * 'accumulate' - the table has a boolean `zone` column; the pot buys `frac` of its cash on a
                   zone close (at most once every `cooldown` trading days) and never sells.
The same code produces the research backtest, the live pot ledger and the dashboard checklist.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


def fmt_usd(x, d=2):
    return '—' if x is None or pd.isna(x) else f'${x:,.{d}f}'


def fmt_pct(x, d=1, sign=True):
    return '—' if x is None or pd.isna(x) else (f'{x:+.{d}f}%' if sign else f'{x:.{d}f}%')


def check(label, value, need, ok):
    return {'label': label, 'value': value, 'need': need, 'ok': None if ok is None else bool(ok)}


@dataclass
class Strategy:
    key: str = ''
    name: str = ''
    kind: str = 'weights'                 # 'weights' | 'accumulate'
    page: str = 'trading'
    assets: tuple = ()                     # tradable asset keys
    inputs: tuple = ()                     # every asset key the strategy reads
    calendar_asset: str = ''               # asset whose dates are the strategy's trading days
    band: float = 0.10
    params: dict = field(default_factory=dict)
    paper: str = ''                        # link shown on the dashboard
    timing: str = ''                       # when signals are checked and orders placed
    tested: dict = field(default_factory=dict)   # research figures for the health monitor

    def compute(self, data: dict) -> pd.DataFrame:  # pragma: no cover - interface
        raise NotImplementedError

    def status(self, t: pd.DataFrame, pot: dict | None = None, provisional: bool = False) -> dict:  # pragma: no cover
        raise NotImplementedError
