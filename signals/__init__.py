"""Signals platform: research-exact trading and investing signals, pot tracking and alerts."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / 'config' / 'portfolio.yaml'
DATA = ROOT / 'data'
PRICES = DATA / 'prices'
UPLOADS = DATA / 'uploads'
STATE = ROOT / 'state'
SITE = ROOT / 'site'
RESEARCH = ROOT / 'research'
__version__ = '1.0.0'
