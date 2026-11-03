# Research folder

Each live system or signal has one paper (Markdown, rendered on the site's Research page) and a folder with copies of the scripts behind it. The scripts are kept for reference: they were run in a scratch workspace against the price files on the `research-data` branch, so paths inside them may need adjusting to re-run.

| Paper | Live version | Scripts |
|---|---|---|
| `qqq-regime-system.md`: Nasdaq-100 regime system + dollar add-on | v1.1 | Full build spec: linked from the paper (v1.0 research) |
| `qqq-value-plan.md`: Nasdaq-100 value-zone plan | v1.2 | `bottom-signals/integration/` (v1.2 fast-crash buys, crash-reserve test, trading-system test) |
| `btc-trend.md`: BTC cycle trend system | v2 | `btc-v2/` (v2 search and selection), `btc-recalibration/` (v1 re-test that retired it) |
| `risk-radar.md`: late cycle, Nasdaq crash risk, BTC leverage | v1 | `risk-radar/late-cycle/`, `risk-radar/positioning/`, `risk-radar/stress/` (first study and dropped stress gauges) |
| `bottom-signals.md`: QQQ fast-crash plan, bear washout, SOXX study | v1 | `bottom-signals/early/`, `bottom-signals/bear-and-fast/`, `bottom-signals/qqq-fast-crash/`, `bottom-signals/soxx/` |

Research data: the `research-data` branch of this repository. Add a symbol to `research-data/tickers.txt` there and the *research-data* workflow downloads it (Yahoo, plus a few URL and Deribit handlers).

Rejected ideas are recorded in the papers too (gold, defensive sectors and value stocks as diversifiers, monthly rebalancing between pots, the old 3-point risk flag, stress gauges, a crash reserve), so they are not re-tested by accident.
