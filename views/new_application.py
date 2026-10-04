import streamlit as st,pandas as pd
import streamlit.components.v1 as components
from pathlib import Path
from core.config import load_config
from core.db import connect
from core.ingest import validate_report
from core.screening import screen_applicant,load_bundle,record_decision
from core.viz import risk_gauge,persistence_diagram,barcode,timeline,network_html,COLORS
from .common import footer
from .theme import page_header,badge_row,style
@st.cache_resource
def resources():
    c=load_config(); return connect(c.db_path),load_bundle()
def render():
    C=load_config(); page_header('New Loan Application'); st.write('Screen a transaction report for suspected third-party loan diversion before disbursal.')
    a,b=st.columns(2)
    with a, st.container(border=True):
        st.markdown('**Applicant details**')
        name=st.text_input('Applicant name'); village=st.selectbox('Village',[f'Village-{i:02}' for i in range(1,13)]); shg=st.selectbox('SHG',['SHG-001','SHG-014','SHG-027','New SHG']); age=st.number_input('Member age',18,60,30); amount=st.number_input('Requested amount (₹)',1000,500000,50000,1000); purpose=st.selectbox('Purpose',['Livelihood','Agriculture','Education','Emergency']); mobile=st.text_input('Mobile / ID (hashed immediately)',type='password')
        if shg=='New SHG': st.warning('Ungraded — under 6 months; limited history increases uncertainty.')
        consent=st.checkbox('Applicant consent captured for transaction-data screening')
    with b, st.container(border=True):
        st.markdown('**Transaction report**'); st.caption('Choose a sample applicant (A to J) for a quick demo, or upload a CSV.')
        sample=st.selectbox('Load sample report',['— choose —']+[f'Applicant_{x}' for x in 'ABCDEFGHIJ']); uploaded=st.file_uploader('Or upload transaction CSV',type=['csv']); df=None
        if uploaded: df=pd.read_csv(uploaded)
        elif sample!='— choose —': df=pd.read_csv(C.root/'demo_cases'/f'{sample}.csv')
        if df is not None:
            st.dataframe(df.head(),hide_index=True); v=validate_report(df)
            if v.errors: st.error('\n'.join(v.errors))
            else: st.success(f'{len(df)} rows validated'); [st.warning(x) for x in v.warnings]
    if st.button('Screen application',type='primary',disabled=not(consent and df is not None)):
        with st.spinner('Running cycle-topology and MLP screening…'):
            form={'consent':consent,'village':village,'shg_id':shg,'shg_age_months':2 if shg=='New SHG' else 12,'amount':amount,'purpose':purpose,'age':age,'name':name,'mobile':mobile,'is_demo':sample!='— choose —'}; conn,bundle=resources(); st.session_state.last_screen=screen_applicant(form,df,conn,bundle)
    r=st.session_state.get('last_screen')
    if r:
        color=COLORS[r.verdict]; text={'LOW':'LOW RISK — eligible for standard approval','REVIEW':'NEEDS REVIEW — hold for field verification','HIGH':'HIGH RISK — LOAN HOLD: suspected third-party diversion'}[r.verdict]
        c1,c2=st.columns([1.5,1])
        with c1:
            st.markdown(f'<div style="background:{color};color:white;padding:22px 26px;border-radius:14px;font-size:24px;font-weight:700;line-height:1.3;box-shadow:0 4px 14px rgba(15,23,42,.12)">{text}<div style="font-size:15px;font-weight:500;margin-top:8px;opacity:.95">Risk {r.risk:.0%}, 90% confidence range {r.ci_low:.0%} to {r.ci_high:.0%}. Screened in {sum(r.timings.values())/1000:.2f} s.</div></div>',unsafe_allow_html=True)
            st.write(''); badge_row([('Independent loops',r.betti1,'#4F46E5'),('History',f'{r.hist_months:.1f} months','#0F172A'),('Rows checked',len(df),'#0F172A')])
            [st.warning(w) for w in r.warnings]
        with c2:
            st.plotly_chart(risk_gauge(r.risk,r.ci_low,r.ci_high),config={'displayModeBar':False})
        with st.expander('Where the screening time went'):
            tm=pd.Series(r.timings).sort_values(); import plotly.graph_objects as go
            fg=go.Figure(go.Bar(y=tm.index,x=tm.values,orientation='h',marker_color='#4F46E5',width=.6,text=[f'{v:.0f} ms' for v in tm.values],textposition='outside',cliponaxis=False)); fg.update_xaxes(title='Milliseconds',range=[0,tm.max()*1.25]); fg.update_yaxes(title=None)
            st.plotly_chart(style(fg,300,False,dict(l=12,r=40,t=12,b=20)),config={'displayModeBar':False})
        if r.hist_months<3: st.warning(f'Only {r.hist_months:.1f} months of history; uncertainty is widened.')
        tabs=st.tabs(['Money network','Loop evidence','Timeline','Why it was flagged'])
        with tabs[0]: components.html(network_html(r.top_edges,r.hub),height=530)
        with tabs[1]:
            x,y=st.columns(2); x.metric('Independent time-expanded cycles',r.betti1); x.caption(f'Cycle backend: {r.backend}'); x.plotly_chart(persistence_diagram(r.persistence)); y.plotly_chart(barcode(r.persistence))
        with tabs[2]: st.plotly_chart(timeline(r.report))
        with tabs[3]: st.write(r.explanation_text); st.dataframe(pd.DataFrame(r.top_edges),hide_index=True)
        st.subheader('Officer action'); actor=st.text_input('Officer ID',value='demo-officer'); decision=st.radio('Decision',['Hold','Approve','Reject'],horizontal=True); reason=st.text_area('Comment / override reason');
        if st.button('Record decision'):
            try: record_decision(resources()[0],r.app_id,r.verdict,decision,reason,actor); st.success('Decision written to the tamper-evident audit trail.')
            except ValueError as e: st.error(str(e))
        report=f'<h1>SHG Screening Case {r.app_id}</h1><p>{r.explanation_text}</p><p>Verdict: {r.verdict}; risk {r.risk:.1%}; interval {r.ci_low:.1%}–{r.ci_high:.1%}</p><h2>KFS / human review</h2><p>Requested ₹{amount:,.0f} for {purpose}. No adverse action may be based on this score alone.</p>'
        st.download_button('Download audit report (HTML)',report,file_name=f'{r.app_id}.html',mime='text/html')
    footer()
