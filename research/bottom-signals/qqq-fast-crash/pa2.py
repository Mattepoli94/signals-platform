exec(open('pa.py').read())
pd.set_option('display.width',320); pd.set_option('display.max_colwidth',80)
def bbre(sig,n=20): 
    m=Cl.rolling(n).mean(); s=Cl.rolling(n).std(); lb=m-sig*s; return ((Cl.shift(1)<lb.shift(1))&(Cl>lb)).astype(float)
rows=[]
for sg in (2.0,2.25,2.5,2.75,3.0):
    for g in (0.06,0.08,0.10):
        rows.append(dict(rule=f'1-step band re-entry {sg} sigma, gate -{g*100:.0f}%',**evaluate(bbre(sg),gate=g)))
print(pd.DataFrame(rows).round(1).to_string(index=False))
div=P['RSI14 bullish divergence at new low']; exh=P['exhaustion: 5+ down days then up day']; fam3=(cnt>=3).astype(float); bb=bbre(2.5)
depth108=(dd<=-0.108).astype(float)
anyT2=pd.concat([div,bb,fam3,exh],axis=1).max(axis=1)
first_of=pd.concat([bb.where(dd<=-0.08,0),(dd<=-0.12).astype(float)],axis=1).max(axis=1)
designs={'D0 depth -10.8% only':(depth108,None,0.0),
 'D1 depth -10.8% -> band re-entry':(depth108,bb,0.0),
 'D2 band re-entry (gate -8%) -> 3+ families':(bb,fam3,0.08),
 'D3 first of [band re-entry at -8%+, depth -12%] -> band/divergence/families/exhaustion':(first_of,anyT2,0.0),
 'D4 depth -10.8% -> first of [divergence, band, families, exhaustion]':(depth108,anyT2,0.0),
 'D5 first of [band re-entry at -8%+, depth -12%] -> 3+ families':(first_of,fam3,0.0)}
rows=[dict(rule=k,**evaluate(f,s_,gate=g)) for k,(f,s_,g) in designs.items()]
print(); print(pd.DataFrame(rows).round(1).to_string(index=False))
