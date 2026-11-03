exec(open('value_test.py').read().split("modes={")[0])
def sim2(s,e,R=0.0,capM=12,main_fast=True,C=1000.0,cap=24):
    cash=res=units=dep=0.0; last=-999; eqs=[]; deps=[]; idle=[]
    for i in range(s,e):
        g=(1+irx[i])**(1/252); cash*=g; res*=g
        if first[i]:
            dep+=C; r_add=min(R*C,max(0,capM*C-res)); res+=r_add; cash+=C-r_add
        amt=0.0; ramt=0.0
        if zone[i] and i-last>=10: amt=cash*0.5; last=i
        if b1[i]: ramt=res*0.5; amt=max(amt,cash*0.5) if main_fast else amt
        if b2[i]: ramt=res; amt=cash if main_fast else amt
        if first[i] and cash-amt>cap*C: amt=cash-cap*C
        units+=(amt+ramt)/a[i]; cash-=amt; res-=ramt
        eqs.append(units*a[i]+cash+res); deps.append(dep); idle.append((cash+res)/max(units*a[i]+cash+res,1))
    eq=np.array(eqs); dp=np.array(deps)
    return eq[-1],(eq/np.maximum.accumulate(eq)-1).min(),(eq/dp-1).min(),np.mean(idle)
starts=[i for i in range(n) if first[i] and idx[i]>=pd.Timestamp('2000-01-01') and i+2520<n]
dca=np.array([sim(s,s+2520,'dca')[0] for s in starts]); yrs=np.array([idx[s].year for s in starts])
rows=[]
cfgs=[('No reserve, fast buys use the main cash (proposal)',dict(R=0.0)),('No fast buys at all (current plan)',None)]
for R in (0.1,0.2,0.3):
    for capM in (6,12,24):
        cfgs.append((f'Reserve {int(R*100)}% of each contribution, capped at {capM} months, main cash also buys',dict(R=R,capM=capM)))
cfgs.append(('Reserve 20% capped 12m, reserve-only for crashes',dict(R=0.2,capM=12,main_fast=False)))
for name,kw in cfgs:
    out=[sim(s,s+2520,'zones')+(np.nan,) for s in starts] if kw is None else [sim2(s,s+2520,**kw) for s in starts]
    w=np.array([o[0] for o in out]); dd=np.array([o[1] for o in out]); bl=np.array([o[2] for o in out]); idl=np.array([o[3] for o in out])
    rel=w/dca-1
    rows.append({'setup':name,'wealth vs DCA 2000-08':f"{np.median(rel[yrs<=2008])*100:+.1f}%",'2009-16':f"{np.median(rel[yrs>=2009])*100:+.1f}%",
                 'account dd (med)':f"{np.median(dd[yrs<=2008])*100:.0f}% / {np.median(dd[yrs>=2009])*100:.0f}%",
                 'below money-in worst':f"{bl[yrs<=2008].min()*100:.0f}% / {bl[yrs>=2009].min()*100:.0f}%",'avg cash share':f"{np.nanmean(idl)*100:.0f}%"})
pd.set_option('display.width',260); pd.set_option('display.max_colwidth',80); print(pd.DataFrame(rows).to_string(index=False))
