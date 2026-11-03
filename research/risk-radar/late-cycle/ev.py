from base import *
L=pd.read_pickle('L.pkl')
TR=('1955-01-01','1994-12-31'); TE=('1995-01-01','2026-12-31')
def score(sig,lab,events,per,lead):
    m=(idx>=per[0])&(idx<=per[1])&near&sig.notna()&lab.notna()
    s=sig[m]==1; y=lab[m]==1
    if m.sum()<250: return dict(n=np.nan)
    base=y.mean(); on=s.mean()
    lift=(y[s].mean()/base) if s.sum()>30 and base>0 else np.nan
    ev=[e for e in events if per[0]<=str(e.date())<=per[1] and sig.loc[:e].notna().iloc[-1] if e in sig.index]
    hit=[ (sig.loc[idx[max(0,ii[e]-lead)]:e]==1).any() for e in ev]
    return dict(on=on*100,lift=lift,caught=f'{sum(hit)}/{len(ev)}')
rows=[]
for k in L:
    r={'sign':k}
    for pn,per in [('TR',TR),('TE',TE)]:
        b=score(L[k],BULL,PK,per,126); c=score(L[k],FAST,CR,per,21)
        r.update({f'{pn}_on':b.get('on'),f'{pn}_bear_lift':b.get('lift'),f'{pn}_bear_caught':b.get('caught'),f'{pn}_fast_lift':c.get('lift'),f'{pn}_fast_caught':c.get('caught')})
    rows.append(r)
R=pd.DataFrame(rows).set_index('sign'); pd.set_option('display.width',260)
print('Bear peaks train',[p.date() for p in PK if str(p.date())<'1995'],' test',[p.date() for p in PK if str(p.date())>='1995'])
print('base (near-high days): bear-within-1y train %.2f test %.2f | fast crash train %.3f test %.3f'%(
  BULL[near&(idx<'1995')].mean(),BULL[near&(idx>='1995')].mean(),FAST[near&(idx<'1995')].mean(),FAST[near&(idx>='1995')].mean()))
print(R.round(2).to_string())
R.to_csv('single.csv')
