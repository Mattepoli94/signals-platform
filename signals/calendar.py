"""NYSE trading days (rule-based; good for projecting exit dates a few weeks ahead)."""
from functools import lru_cache

import pandas as pd
from pandas.tseries.holiday import (MO, AbstractHolidayCalendar, DateOffset, EasterMonday, GoodFriday, Holiday, USLaborDay,
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


def _boxing(dt):
    # 26 Dec; if Sat/Sun -> Mon/Tue (Christmas substitute takes the Monday when 25th is a weekend)
    return dt + pd.Timedelta(days={5: 2, 6: 2, 0: 1}.get(dt.weekday(), 0)) if dt.weekday() in (5, 6) or (dt.weekday() == 0 and (dt - pd.Timedelta(days=1)).weekday() == 6) else dt


class LSE(AbstractHolidayCalendar):
    rules = [
        Holiday('New Year', month=1, day=1, observance=nearest_workday),
        GoodFriday, EasterMonday,
        Holiday('Early May', month=5, day=1, offset=DateOffset(weekday=MO(1))),
        Holiday('Spring', month=5, day=31, offset=DateOffset(weekday=MO(-1))),
        Holiday('Summer', month=8, day=31, offset=DateOffset(weekday=MO(-1))),
        Holiday('Christmas', month=12, day=25, observance=nearest_workday),
        Holiday('Boxing Day', month=12, day=26, observance=_boxing),
    ]


@lru_cache(maxsize=2)
def _bday(cal='us'):
    return pd.offsets.CustomBusinessDay(calendar=LSE() if cal == 'lse' else NYSE())


def add_trading_days(d: pd.Timestamp, n: int, cal: str = 'us') -> pd.Timestamp:
    return pd.Timestamp(d) + n * _bday(cal)


def next_trading_day(d: pd.Timestamp) -> pd.Timestamp:
    return add_trading_days(d, 1)
