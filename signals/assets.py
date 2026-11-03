"""Asset registry. Add a new market here, then reference it from a strategy."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Asset:
    key: str            # file name in data/prices and the id strategies use
    name: str
    source: str         # 'yahoo' or 'fred'
    symbol: str         # symbol at the source (FRED: comma-separated series combined by `combine`)
    currency: str = 'USD'
    calendar: str = 'us'   # 'us' = NYSE days, 'crypto' = every day (close 00:00 UTC), 'fx', 'macro'
    tradable: bool = False
    fallback: str = ''     # FRED series used if the main source fails
    fair_ref: str = ''     # US-listed twin used to repair bad prints (UK-listed ETFs on Yahoo)
    account: str = ''      # where you hold it (shown next to orders)


ASSETS = {a.key: a for a in [
    Asset('EQQQ', 'Invesco EQQQ Nasdaq-100 UCITS ETF (London, pence)', 'yahoo', 'EQQQ.L', currency='GBX', calendar='lse',
          tradable=True, fair_ref='QQQ', account='ISA'),
    Asset('QQQ', 'Invesco QQQ (Nasdaq-100, US)', 'yahoo', 'QQQ'),
    Asset('UUP', 'Invesco DB US Dollar Index Bullish (signal only)', 'yahoo', 'UUP'),
    Asset('BTC', 'Bitcoin (spot, USD)', 'yahoo', 'BTC-USD', calendar='crypto', tradable=True),
    Asset('GBPUSD', 'GBP/USD', 'yahoo', 'GBPUSD=X', currency='FX', calendar='fx', fallback='DEXUSUK', account='Invest'),
]}


# Holdings that are not downloaded: US dollar cash, priced from GBP/USD (units = dollars).
CASH_USD = 'USD'


def currency(key: str) -> str:
    if key == CASH_USD:
        return 'USDCASH'
    return ASSETS[key].currency if key in ASSETS else 'USD'


def account(key: str) -> str:
    if key == CASH_USD:
        return 'Invest (USD balance)'
    return ASSETS[key].account or ''
