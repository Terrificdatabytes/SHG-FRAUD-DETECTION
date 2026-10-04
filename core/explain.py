"""Deterministic lightweight structural explainer and neutral audit wording."""
from .privacy import alias
def explain(df,features,risk,lo,hi,loop_nodes):
    account=df.account_id.iloc[0]; dr=df[df.direction=='DR'].sort_values('amount',ascending=False); top=[]
    for _,r in dr.head(8).iterrows(): top.append({'src':account,'dst':r.counterparty_id,'amount':float(r.amount),'date':str(r.date.date()),'score':float(r.amount/max(dr.amount.max(),1))})
    hub=dr.groupby('counterparty_id').amount.sum().idxmax() if len(dr) else ''
    bullets=[]
    if features['pass72']>=.5: bullets.append(f"{features['pass72']:.0%} of credited funds moved out within 72 hours")
    if features['cycles_short']>0: bullets.append(f"{int(features['cycles_short'])} short return-flow loop(s) detected")
    if features['out_concentration']>.7: bullets.append('Outgoing funds are concentrated in one outside account')
    if features['history_months']<3: bullets.append('Less than three months of history increases uncertainty')
    context='; '.join(bullets) if bullets else 'No strong diversion structure was found'
    text=f"Applicant scored {risk:.0%} (90% range {lo:.0%}–{hi:.0%}). {context}. This is a screening signal; manual verification by the SHG/PLF officer is required before any action."
    return top,hub,text,bullets
