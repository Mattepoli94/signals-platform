"""Strategy registry. To add a strategy: write a module with a Strategy subclass and register it here."""
from .btc_trend import BTCTrend
from .qqq_regime import QQQRegime
from .qqq_value import QQQValue

STRATEGIES = {s.key: s for s in (QQQRegime(), QQQValue(), BTCTrend())}


def get(key: str):
    return STRATEGIES[key]
