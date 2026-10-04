"""Transaction CSV validation and privacy-preserving normalisation."""
from dataclasses import dataclass
import pandas as pd
from .privacy import hash_identifier
REQUIRED=['date','txn_id','account_id','counterparty_id','direction','amount','channel','narration']
ALLOWED_DIR={'CR','DR'}
ALLOWED_CH={'UPI','NEFT','IMPS','CASH','LOAN_DISBURSAL','LOAN_REPAYMENT'}
@dataclass
class ValidationResult:
    data: pd.DataFrame
    errors: list[str]
    warnings: list[str]
def validate_report(df: pd.DataFrame, hash_ids=False)->ValidationResult:
    d=df.copy(); errors=[]; warnings=[]
    missing=[x for x in REQUIRED if x not in d.columns]
    if missing: return ValidationResult(d,[f'Missing required field: {x}' for x in missing],[])
    if len(d)<5: errors.append('Report must contain at least 5 transactions')
    d['date']=pd.to_datetime(d['date'],errors='coerce',utc=True)
    d['amount']=pd.to_numeric(d['amount'],errors='coerce')
    for i,r in d.iterrows():
        row=i+2
        if pd.isna(r['date']): errors.append(f'Row {row}: date is not parseable')
        if pd.isna(r['amount']) or r['amount']<=0: errors.append(f'Row {row}: amount must be positive')
        if str(r['direction']).upper() not in ALLOWED_DIR: errors.append(f'Row {row}: direction must be CR or DR')
        if str(r['channel']).upper() not in ALLOWED_CH: errors.append(f'Row {row}: unsupported channel')
    d['direction']=d['direction'].str.upper(); d['channel']=d['channel'].str.upper()
    if hash_ids and not errors:
        d['account_id']=d['account_id'].map(hash_identifier); d['counterparty_id']=d['counterparty_id'].map(hash_identifier)
    if not errors and (d['date'].max()-d['date'].min()).days<60: warnings.append('Limited history: confidence interval widened')
    return ValidationResult(d,errors,warnings)
