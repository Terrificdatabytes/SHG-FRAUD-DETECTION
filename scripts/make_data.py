#!/usr/bin/env python
"""Generate the clearly-labelled synthetic SHG world and unseen demo reports."""
from pathlib import Path
import sys,json,time,sqlite3
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np,pandas as pd
from core.config import load_config
from core.db import connect
from core.privacy import hash_identifier
from core.features import report_features,FEATURE_NAMES
C=load_config(); rng=np.random.default_rng(C.seed); ROOT=C.root

def tx_rows(member, fraud=False, benign_cycle=False, months=12, start=pd.Timestamp('2025-01-01',tz='UTC'), pattern='normal', rng=rng):
    rows=[]; tid=0
    def add(dt,cp,direction,amount,ch='UPI',n='transfer'):
        nonlocal tid; tid+=1; rows.append([dt,f'T{member[-5:]}{tid:04}',member,cp,direction,round(float(amount),2),ch,n])
    loan_month=int(rng.integers(1,max(2,months-2))); loan_date=start+pd.DateOffset(months=loan_month)+pd.Timedelta(days=int(rng.integers(3,15)))
    for m in range(months):
        base=start+pd.DateOffset(months=m)
        add(base+pd.Timedelta(days=5),f'{member}-INCOME-{int(rng.integers(30))}','CR',rng.uniform(3500,12000),'IMPS','income')
        add(base+pd.Timedelta(days=7),f'{member}-VENDOR-{int(rng.integers(25))}','DR',rng.uniform(400,2800),'UPI','household purchase')
        add(base+pd.Timedelta(days=12),'SHG-SAVINGS','DR',rng.uniform(250,650),'UPI','monthly savings')
        if m>=loan_month:
            add(base+pd.Timedelta(days=25),'SHG-REPAY','DR',rng.uniform(1800,3200),'LOAN_REPAYMENT','loan repayment')
    amount=float(rng.uniform(30000,90000)); add(loan_date,'BANK-SERVICE','CR',amount,'LOAN_DISBURSAL','SHG loan disbursal')
    if fraud:
        hub=f'SHADOW-{int(rng.integers(10))}' if pattern!='new_hub' else f'UNSEEN-HUB-{int(rng.integers(1000))}'
        if pattern=='multihop': hub=f'MULE-{int(rng.integers(100))}'
        fraction = rng.uniform(.35,.68) if pattern=='partial' else rng.uniform(.70,.92)
        delay = pd.Timedelta(days=int(rng.integers(4,9))) if pattern=='delayed' else pd.Timedelta(hours=int(rng.integers(4,60)))
        if pattern=='split_no_return':
            for leg in range(3):
                add(loan_date+delay+pd.Timedelta(hours=leg*5),f'{hub}-MULE-{leg}','DR',amount*fraction/3,'IMPS','transfer')
        else:
            add(loan_date+delay,hub,'DR',amount*fraction,'IMPS','transfer')
        if pattern!='split_no_return' and rng.random()>.22:
            for k in range(2,5): add(loan_date+pd.Timedelta(days=25*k-2),hub,'CR',amount*rng.uniform(.025,.055),'UPI','transfer')
        if pattern=='camouflaged':
            for k in range(15): add(loan_date+pd.Timedelta(days=int(rng.integers(1,80))),f'VENDOR-X{k}','DR',rng.uniform(80,650),'UPI','purchase')
    if (not fraud) and pattern=='quick_benign':
        qd=loan_date+pd.Timedelta(hours=20)
        add(qd,f'{member}-HOSPITAL','DR',amount*rng.uniform(.55,.85),'NEFT','emergency medical payment')
    if (not fraud) and pattern=='business':
        for k in range(28):
            add(start+pd.Timedelta(days=20+k*5),f'BIZ-{k%14}','CR' if k%2==0 else 'DR',rng.uniform(1200,7500),'UPI','business')
    if (not fraud) and pattern=='seasonal':
        sd=start+pd.Timedelta(days=100); add(sd,'CROP-BUYER','CR',rng.uniform(45000,80000),'NEFT','harvest sale')
        for k in range(8): add(sd+pd.Timedelta(days=3+k*4),f'INPUT-{k}','DR',rng.uniform(3500,7500),'UPI','farm input')
    if benign_cycle:
        cp=f'MEMBER-PEER-{int(rng.integers(100))}'; add(start+pd.Timedelta(days=45),cp,'DR',3500,'UPI','internal loan'); add(start+pd.Timedelta(days=67),cp,'CR',3500,'UPI','internal repayment')
    return pd.DataFrame(rows,columns=['date','txn_id','account_id','counterparty_id','direction','amount','channel','narration']).sort_values('date')

def demo_report(letter,pattern,r):
    months=2 if pattern=='borderline' else 8
    d=tx_rows(f'DEMO-{letter}-{r.integers(1e8)}',False,pattern=='internal_cycle',months,start=pd.Timestamp('2026-01-01',tz='UTC'),rng=r)
    if pattern in {'classic','ring','camouflaged','multihop','borderline'}:
        # replace the normal loan pattern with structural fraud legs
        loan=d[d.channel=='LOAN_DISBURSAL'].iloc[-1]; amt=float(loan.amount); date=loan.date
        frac=.58 if pattern=='borderline' else (.76 if pattern=='multihop' else .9)
        hub='SHADOW-2' if pattern in {'classic','ring'} else (f'NEW-HUB-{r.integers(9999)}' if pattern in {'multihop','borderline'} else 'SHADOW-6')
        rows=[]
        rows.append([date+pd.Timedelta(hours=18),f'F{letter}1',d.account_id.iloc[0],hub,'DR',amt*frac,'IMPS','transfer'])
        if pattern!='borderline':
            for k in range(2,5): rows.append([date+pd.Timedelta(days=25*k-2),f'F{letter}{k}',d.account_id.iloc[0],hub,'CR',amt*.04,'UPI','transfer'])
        if pattern=='camouflaged':
            for k in range(18): rows.append([date+pd.Timedelta(days=int(r.integers(2,100))),f'C{letter}{k}',d.account_id.iloc[0],f'SHOP-{k}','DR',r.uniform(50,550),'UPI','purchase'])
        d=pd.concat([d,pd.DataFrame(rows,columns=d.columns)]).sort_values('date')
    if pattern=='seasonal':
        date=d.date.min()+pd.Timedelta(days=80); rows=[[date,f'S{letter}0',d.account_id.iloc[0],'CROP-BUYER','CR',65000,'NEFT','harvest sale']]
        for k in range(8): rows.append([date+pd.Timedelta(days=k*3+2),f'S{letter}{k+1}',d.account_id.iloc[0],f'INPUT-{k}','DR',5000+r.uniform(0,1800),'UPI','farm input'])
        d=pd.concat([d,pd.DataFrame(rows,columns=d.columns)]).sort_values('date')
    if pattern=='business':
        date=d.date.min()+pd.Timedelta(days=30); rows=[]
        for k in range(35): rows.append([date+pd.Timedelta(days=k*4),f'B{letter}{k}',d.account_id.iloc[0],f'CUSTOMER-{k%12}','CR' if k%2==0 else 'DR',r.uniform(1500,8000),'UPI','business'])
        d=pd.concat([d,pd.DataFrame(rows,columns=d.columns)]).sort_values('date')
    return d

def main():
    for p in [ROOT/'data',ROOT/'demo_cases',ROOT/'artifacts']: p.mkdir(exist_ok=True)
    if C.db_path.exists(): C.db_path.unlink()
    (ROOT/'data'/'temporal_features.csv').unlink(missing_ok=True)
    conn=connect(C.db_path); now=int(time.time()); member_rows=[]; feature_rows=[]; all_tx=[]
    shadows=[hash_identifier(f'SHADOW-{i}') for i in range(10)]
    for i,h in enumerate(shadows): conn.execute('INSERT INTO nodes VALUES(?,?,?,?,?,?,?,?,?,?)',(h,'external','',None,None,None,0,0,now,'active')); conn.execute('INSERT INTO labels VALUES(?,?,?,?,?)',(h,0,1,'train','shadow'))
    patterns=['classic','ring','camouflaged','multihop','delayed','partial','split_no_return']
    n_members=0; n_fraud=0; benign_count=0
    for s in range(120):
        village=f'Village-{s%12+1:02}'; shg=f'SHG-{s:03}'; plf=f'PLF-{s%12:02}'
        conn.execute('INSERT INTO nodes VALUES(?,?,?,?,?,?,?,?,?,?)',(shg,'shg',village,shg,plf,None,1,0,now,'active'))
        size=int(rng.integers(12,16))
        for j in range(size):
            n_members+=1; mid=f'M-{s:03}-{j:02}'; fraud=rng.random()<.07; q=rng.random(); benign=(not fraud and q<.18); n_fraud+=int(fraud); benign_count+=int(benign); pat=rng.choice(patterns) if fraud else ('benign_cycle' if q<.18 else ('business' if q<.23 else ('seasonal' if q<.28 else ('quick_benign' if q<.34 else 'normal'))))
            d=tx_rows(mid,fraud,benign,12,pattern=pat); all_tx.append(d)
            split='test' if s%10 in {8,9} else ('val' if s%10==7 else 'train')
            conn.execute('INSERT INTO nodes VALUES(?,?,?,?,?,?,?,?,?,?)',(mid,'member',village,shg,plf,f'F-{s}-{j}',1,0,now,'active')); conn.execute('INSERT INTO labels VALUES(?,?,?,?,?)',(mid,int(fraud),0,split,pat))
            conn.execute('INSERT INTO edges VALUES(?,?,?,?,?,?,?)',(shg,mid,'membership',0,now,mid+'MEM','active'))
            for _,x in d.iterrows():
                cp=hash_identifier(x.counterparty_id); conn.execute('INSERT OR IGNORE INTO nodes VALUES(?,?,?,?,?,?,?,?,?,?)',(cp,'external','',None,None,None,0,0,now,'active'))
                src,dst=(cp,mid) if x.direction=='CR' else (mid,cp); conn.execute('INSERT INTO edges VALUES(?,?,?,?,?,?,?)',(src,dst,'transfer',float(x.amount),int(x.date.timestamp()),x.txn_id,'active'))
            f=report_features(d); f.update(node_id=mid,y=int(fraud),split=split,pattern=pat); feature_rows.append(f)
    conn.commit(); conn.close()
    pd.DataFrame(feature_rows).to_csv(ROOT/'data'/'member_features.csv',index=False)
    pd.concat(all_tx,ignore_index=True).to_csv(ROOT/'data'/'synthetic_transactions.csv',index=False)
    specs={'A':('clean','steady','LOW'),'B':('clean','internal_cycle','LOW'),'C':('clean','seasonal','LOW'),'D':('clean','business','LOW'),'E':('fraud','classic','HIGH'),'F':('fraud','ring','HIGH'),'G':('fraud','camouflaged','HIGH/REVIEW'),'H':('fraud','multihop','REVIEW/HIGH'),'I':('borderline','borderline','REVIEW'),'J':('clean','irregular','LOW')}
    drng=np.random.default_rng(C.seed+991); manifest={}
    for letter,(truth,pat,expected) in specs.items():
        d=demo_report(letter,pat,drng); d.to_csv(ROOT/'demo_cases'/f'Applicant_{letter}.csv',index=False); manifest[f'Applicant_{letter}']={'truth':truth,'pattern':pat,'expected_verdict':expected}
    (ROOT/'demo_cases'/'manifest.json').write_text(json.dumps(manifest,indent=2))
    stats={'shgs':120,'members':n_members,'edges':sum(1 for _ in sqlite3.connect(C.db_path).execute('select 1 from edges')),'fraud_members':n_fraud,'fraud_prevalence':n_fraud/n_members,'benign_cycle_share':benign_count/(n_members-n_fraud),'synthetic':True}
    (ROOT/'artifacts'/'data_stats.json').write_text(json.dumps(stats,indent=2)); print(json.dumps(stats,indent=2))
if __name__=='__main__': main()
