exec(open('evalq.py').read())
def fam(mem):
    m=lambda s: s.rolling(mem,min_periods=1).max() if mem>1 else s
    G=pd.DataFrame(index=idx)
    G['stretch']=m(pd.concat([F.stretch_dd,F.stretch_z15],axis=1).max(axis=1))
    G['capitulation']=m(F.capitulation_vol)
    G['options_fear']=m(pd.concat([F.puts_heavy_total,F.puts_heavy_equity],axis=1).max(axis=1))
    G['vol_panic']=m(pd.concat([F.vxn_top10,F.short_term_panic],axis=1).max(axis=1))
    G['positioning']=m(pd.concat([F.dealers_short_gamma,F.am_washed_out,F.hf_short],axis=1).max(axis=1))
    G['oversold']=m(pd.concat([F.rsi14_le30,F.rsi2_le5],axis=1).max(axis=1))
    return G
def rule3d(sig):   # confirm with close above 3-day high
    pass
rows=[]
for mem in (1,5,10):
    G=fam(mem); cnt=G.fillna(0).sum(axis=1)
    for k in (3,4,5):
        for mindd in (0.05,0.08):
            for conf in (False,True):
                sig=(cnt>=k).astype(float); D=run_rule(sig,mindd=mindd,confirm=conf)
                r=dict(mem=mem,k=k,mindd=mindd,confirm=conf,**summ(D))
                for en,(y0,y1) in {'07-15':(2007,2015),'16-26':(2016,2026)}.items():
                    s=summ(D[(D.win.dt.year>=y0)&(D.win.dt.year<=y1)]); r[f'{en}']=f"{s.get('score',np.nan):+.1f} ({s.get('signals')})" if s else '-'; r[f'{en}_s']=s.get('score',-99) if s else -99
                r['min_era']=min(r['07-15_s'],r['16-26_s']); rows.append(r)
R=pd.DataFrame(rows).sort_values('min_era',ascending=False); pd.set_option('display.width',300)
print(R[['mem','k','mindd','confirm','signals','fall_med','fall_worst','within5','under_med','r1m','r3m','r6m','score','07-15','16-26','min_era']].round(1).head(20).to_string(index=False))
print('\nSTATIC -10.8% for reference: score 5.7 (07-15 +8.2, 16-26 +4.5)')
