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


ASSETS = {a.key: a for a in [
    Asset('QQQ', 'Invesco QQQ (Nasdaq-100)', 'yahoo', 'QQQ', tradable=True),
    Asset('UUP', 'Invesco DB US Dollar Index Bullish', 'yahoo', 'UUP', tradable=True),
    Asset('BTC', 'Bitcoin (spot, USD)', 'yahoo', 'BTC-USD', calendar='crypto', tradable=True),
    Asset('TLT', 'iShares 20+ Year Treasury Bond', 'yahoo', 'TLT'),
    Asset('GLD', 'SPDR Gold Shares', 'yahoo', 'GLD'),
    Asset('IRX', '13-week T-bill yield', 'yahoo', '^IRX', calendar='macro', fallback='DTB3'),
    Asset('DXY', 'US dollar index', 'yahoo', 'DX-Y.NYB', calendar='macro'),
    Asset('GBPUSD', 'GBP/USD', 'yahoo', 'GBPUSD=X', currency='FX', calendar='fx', fallback='DEXUSUK'),
    Asset('NETLIQ', 'Fed net liquidity (WALCL - TGA - RRP), $bn', 'fred', 'WALCL,WTREGEN,RRPONTSYD', calendar='macro'),
]}
