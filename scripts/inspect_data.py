#!/usr/bin/env python
from pathlib import Path
import sys,json,pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.config import load_config
C=load_config(); f=pd.read_csv(C.root/'data/member_features.csv'); stats=json.loads((C.artifacts/'data_stats.json').read_text())
print('SYNTHETIC DATA INSPECTION'); print(json.dumps(stats,indent=2)); print('\nPatterns:',f.pattern.value_counts().to_dict())
print('Fraud amount quantiles:',f[f.y==1].amount_mean.quantile([.1,.5,.9]).round(1).to_dict()); print('Benign amount quantiles:',f[f.y==0].amount_mean.quantile([.1,.5,.9]).round(1).to_dict())
print('Benign cycles present:',int((f.pattern=='benign_cycle').sum()),'— loop does not imply fraud')
