"""NYSE trading days (rule-based; good for projecting exit dates a few weeks ahead)."""
from functools import lru_cache

import pandas as pd
from pandas.tseries.holiday import (AbstractHolidayCalendar, GoodFriday, Holiday, USLaborDay,
                                    USMartinLutherKingJr, USMemorialDay, USPresidentsDay,
                                    USThanksgivingDay, nearest_workday)


class NYSE(AbstractHolidayCalendar):
    rules = [
        Holiday('New Year', month=1, day=1, observance=nearest_workday),
        USMartinLutherKingJr, USPresidentsDay, GoodFriday, USMemorialDay,
        Holiday('Juneteenth', month=6, day=19, start_date='2022-01-01', observance=nearest_workday),
        Holiday('Independence Day', month=7, day=4, observance=nearest_workday),
        USLaborDay, USThanksgivingDay,
        Holiday('Christmas', month=12, day=25, observance=nearest_workday),
    ]


@lru_cache(maxsize=1)
def _bday():
    return pd.offsets.CustomBusinessDay(calendar=NYSE())


def add_trading_days(d: pd.Timestamp, n: int) -> pd.Timestamp:
    return pd.Timestamp(d) + n * _bday()


def next_trading_day(d: pd.Timestamp) -> pd.Timestamp:
    return add_trading_days(d, 1)
