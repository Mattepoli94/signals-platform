import requests, json, gzip
UA={'User-Agent':'Mozilla/5.0'}
for s in ['_SPX','_NDX','SPY','QQQ']:
    try:
        r=requests.get(f'https://cdn.cboe.com/api/global/delayed_quotes/options/{s}.json',headers=UA,timeout=60)
        print(s,r.status_code,len(r.content))
        if r.ok: gzip.open(f'research-data/gamma/{s}.json.gz','wb').write(r.content)
    except Exception as e: print(s,'fail',e)
