import requests, time, re, os, json, pandas as pd
os.makedirs('research-data/raw', exist_ok=True)
H={'User-Agent':'Mozilla/5.0 (research script)'}
def get(u,**k):
    r=requests.get(u,headers=H,timeout=60,**k); print('GET',u[:120],r.status_code,len(r.content),r.headers.get('content-type')); return r
# Cboe index histories
for s in ['DSPX','COR3M','COR1M','COR10D','VIX','SKEW','VVIX','VIX9D','VXN','VIX1D','VIX3M','VIX6M','VXD','RVX','VOLI']:
    try:
        r=get(f'https://cdn.cboe.com/api/global/us_indices/daily_prices/{s}_History.csv')
        if r.ok and len(r.content)>500: open(f'research-data/raw/cboe_idx_{s}.csv','wb').write(r.content)
    except Exception as e: print('ERR',s,e)
# NAAIM
try:
    r=get('https://naaim.org/programs/naaim-exposure-index/')
    links=re.findall(r'href="([^"]+\.xlsx?)"',r.text); print('naaim links',links[:5])
    if links:
        r2=get(links[0]); open('research-data/raw/naaim.xlsx','wb').write(r2.content)
except Exception as e: print('ERR naaim',e)
# Cboe daily options stats (put/call) - probe then loop
def daily(d):
    for u in [f'https://cdn.cboe.com/data/us/options/market_statistics/daily/{d}_daily_options']:
        r=requests.get(u,headers=H,timeout=30)
        if r.ok:
            try: return r.json()
            except Exception: return None
    return None
probe=daily('2024-03-01'); print('probe', None if probe is None else str(probe)[:1500])
if probe is not None:
    out={}
    for d in pd.bdate_range('2019-09-01', pd.Timestamp.today()):
        ds=d.strftime('%Y-%m-%d')
        try:
            j=daily(ds)
            if j: out[ds]=j
        except Exception as e: print('ERR',ds,e)
        time.sleep(0.15)
    json.dump(out,open('research-data/raw/cboe_daily.json','w')); print('cboe daily days',len(out))
