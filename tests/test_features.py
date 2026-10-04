import pandas as pd
from core.features import report_features
def base(rows): return pd.DataFrame(rows,columns=['date','txn_id','account_id','counterparty_id','direction','amount','channel','narration']).assign(date=lambda x:pd.to_datetime(x.date,utc=True))
def test_fast_loop_and_pass_through():
 d=base([['2026-01-01','1','A','BANK','CR',10000,'LOAN_DISBURSAL','loan'],['2026-01-02','2','A','X','DR',9000,'UPI','transfer'],['2026-01-06','3','A','X','CR',1000,'UPI','return'],['2026-02-01','4','A','SHG','DR',500,'LOAN_REPAYMENT','repay'],['2026-03-01','5','A','SHG','DR',500,'LOAN_REPAYMENT','repay']]); f=report_features(d); assert f['pass72']>=.89 and f['cycles_short']>=1
def test_slow_cycle_not_short():
 d=base([['2026-01-01','1','A','BANK','CR',10000,'LOAN_DISBURSAL','loan'],['2026-01-02','2','A','X','DR',2000,'UPI','internal'],['2026-01-25','3','A','X','CR',2000,'UPI','return'],['2026-02-01','4','A','V','DR',500,'UPI','x'],['2026-03-01','5','A','V','DR',500,'UPI','x']]); assert report_features(d)['cycles_short']==0
