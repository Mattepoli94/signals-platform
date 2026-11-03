import requests, re
H={'User-Agent':'Mozilla/5.0 (research script)'}
for u in ['https://www.multpl.com/shiller-pe/table/by-month','https://www.multpl.com/inflation/table/by-month',
          'https://www.finra.org/sites/default/files/2021-03/margin-statistics.xlsx',
          'https://www.cftc.gov/files/dea/history/fut_fin_txt_2026.zip',
          'https://www.deribit.com/api/v2/public/get_funding_rate_history?instrument_name=BTC-PERPETUAL&start_timestamp=1761955200000&end_timestamp=1762128000000',
          'https://cdn.cboe.com/data/us/options/market_statistics/daily/2026-11-02_daily_options',
          'https://cdn.cboe.com/api/global/us_indices/daily_prices/DSPX_History.csv']:
    try:
        r=requests.get(u,headers=H,timeout=40); t=r.text if 'text' in (r.headers.get('content-type') or '') or 'json' in (r.headers.get('content-type') or '') else ''
        print('PROBE',r.status_code,len(r.content),u[:90])
        if 'multpl' in u:
            rows=re.findall(r'<td>([A-Z][a-z]{2} \d{1,2}, \d{4})</td>\s*<td>\s*(?:&#x2002;)?\s*([\d.]+)',t); print('PROBE rows',len(rows),rows[:3],rows[-2:])
    except Exception as e: print('PROBE ERR',u[:60],e)
