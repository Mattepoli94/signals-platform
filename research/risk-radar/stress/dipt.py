import sys; sys.path.insert(0,'/home/claude/signals-platform')
import pandas as pd, numpy as np
from signals import data as D
from signals.strategies import get
s=get('qqq_regime'); data=D.load_all(sorted(set(s.inputs)|{'GBPUSD','IRX'}))
t=s.compute(data); print(t.columns.tolist()); print(t.tail(3).T)
t.to_pickle('qtab.pkl')
