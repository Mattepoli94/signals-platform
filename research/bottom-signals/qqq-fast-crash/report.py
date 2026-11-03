from generic import *
res={}
for name in ('QQQ','SOXX'):
    c,X=build(name); r=np.log(c).diff()
    if name=='QQQ': base_vol=r['2007':].std()
    scale=1.0 if name=='QQQ' else r['2007':].std()/base_vol
    print(name,'vol scale',round(scale,2))
    for sec in ('none','families'):
        D=run(c,X,scale=scale,second=sec)
        for era,m in [('2007-2026',D.win.dt.year>=2007),('2007-15',D.win.dt.year<=2015),('2016-26',D.win.dt.year>=2016)]:
            res[(name,sec,era)]=summ(D[m])
        D.to_pickle(f'D_{name}_{sec}.pkl')
    G=families(X); print(name,'today: dd %.1f%%, trigger at %.1f%%, families on:'%(X.dd.iloc[-1]*100,-10.8*scale), G.iloc[-1][G.iloc[-1]==1].index.tolist())
T=pd.DataFrame(res); pd.set_option('display.width',300); pd.set_option('display.max_colwidth',30)
print(T.T.to_string())
