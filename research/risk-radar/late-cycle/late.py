from base import *
L=pd.read_pickle('L.pkl')
exec(open('ev.py').read().split("rows=[]")[0].split("L=pd.read_pickle('L.pkl')")[1])
L['rate_or_infl_pressure']=L[['10y_up_1.5pt_12m','inflation_gt4_rising']].max(axis=1)
L.loc[L['inflation_gt4_rising'].isna(),'rate_or_infl_pressure']=L['10y_up_1.5pt_12m']   # CPI ends 2023 -> fall back to 10y
designs={
 'LATE-3: curve flat, valuation top10%, S&P +50%/24m':['curve_flat_lt_0.5','cape_top10pct_to_date','spx_up_50pct_24m'],
 'LATE-4: + rate/inflation pressure':['curve_flat_lt_0.5','cape_top10pct_to_date','spx_up_50pct_24m','rate_or_infl_pressure'],
 'LATE-4 + margin surge (test only)':['curve_flat_lt_0.5','cape_top10pct_to_date','spx_up_50pct_24m','rate_or_infl_pressure','margin_up_30pct_yoy'],
}
# CAPE ends Sep 2023: carry last value forward for test (valuation moves slowly) - flag it
rows=[]
for nm,cols in designs.items():
    for k in (1,2,3):
        if k>len(cols): continue
        S=L[cols].copy()
        s=(S.sum(axis=1,min_count=len(cols))>=k).astype(float); s[S.isna().any(axis=1)]=np.nan
        r={'design':nm,'k':k}
        for pn,per in [('TR',TR),('TE',TE)]:
            b=score(s,BULL,PK,per,126); c=score(s,FAST,CR,per,21)
            r.update({f'{pn}_on':b.get('on'),f'{pn}_lift':b.get('lift'),f'{pn}_caught':b.get('caught'),f'{pn}_fastlift':c.get('lift')})
        rows.append(r)
pd.set_option('display.width',250); print(pd.DataFrame(rows).round(2).to_string(index=False))
# per-peak readout for LATE-4 >=2 : when did it first turn on in the 12m before each peak
cols=designs['LATE-4: + rate/inflation pressure']; S=L[cols]; sc=S.sum(axis=1,min_count=4)
print('\nper bear peak: LATE-4 score at peak, max score in 6m before, first date >=2 within 12m before peak')
for p in PK:
    j=ii[p]; w=sc.iloc[max(0,j-252):j+1]; first=w[w>=2].index.min()
    print(p.date(), 'score at peak',sc.loc[p], ' max 6m',w.iloc[-126:].max(), ' first>=2', None if pd.isna(first) else first.date(), ' parts at peak',dict(S.loc[p].dropna().astype(int)))
print('\nLATE-4 parts today (CAPE/CPI carried from 2023):'); print(S.ffill().iloc[-1])
