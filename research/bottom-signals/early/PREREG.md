# Bottom indicators - pre-registration (3 Nov 2026, written before testing)

Goal: minimum set of indicators that mark the low after (A) bear markets and (B) fast crashes, plus (C) BTC crashes.

States and outcomes (signal days scored only inside the state; signals use data known at that close):
- A Bear: S&P 500 >= 15% below its 1-year high. Outcomes: return over next 126 and 252 sessions; chance of a further fall >= 10% (from that close) within 126 sessions. Troughs: S&P lows of the 15 bear markets 1957-2022 (+2025 near-miss reported separately). Trough caught = flag on within [trough-10, trough+21] sessions.
- B Correction: Nasdaq-100 >= 8% below its 1-year high. Outcomes: return over next 21 and 63 sessions; chance of a further fall >= 8% within 21 sessions. Troughs: lows of the 21 Nasdaq fast falls 2007-2026. Caught = flag on within [trough-5, trough+10].
- C BTC: BTC >= 20% below its 60-day high. Outcomes: next 30/90 days; further fall >= 15% within 30 days. Troughs: lows of the 16 crashes 2019-26.
Alpha = mean forward return on flag days minus mean over all state days (same state, same years).

Validation: long-history signs (price, VIX, rates, dollar, CAPE): chosen on 1955-1994, checked on 1995-2026 (A), and per era blocks (B). Options/positioning/leverage (2006+): scored in blocks 2006-10, 11-15, 16-19, 20-22, 23-26; kept only if helpful in most blocks. Combinations: equal-weight counts of families, thresholds 1-3; leave-one-block-out check.
Signals are directional and thresholds fixed below (no tuning).
