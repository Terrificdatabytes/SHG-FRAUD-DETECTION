"""SHG Fraud Monitor — enterprise-style Streamlit entry point."""
import streamlit as st
from core.reset import reset_demo
from views import overview, new_application, review_queue, member_detail, topology, village_risk, audit_report, model_performance, system_compliance, how_it_works
from views import theme

st.set_page_config(layout="wide", page_title="SHG Fraud Monitor", page_icon=":material/shield:", initial_sidebar_state="expanded")
theme.inject()

PAGES = {
    "Executive Overview": overview,
    "New Loan Application": new_application,
    "Review Queue": review_queue,
    "SHG / Member Detail": member_detail,
    "Topology Evidence": topology,
    "Village Risk": village_risk,
    "Explanation & Audit Report": audit_report,
    "Model Performance": model_performance,
    "System & Compliance": system_compliance,
    "How It Works": how_it_works,
}
with st.sidebar:
    st.markdown('<div class="brand"><div class="logo"><svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3z"/><path d="M9 12l2 2 4-4"/></svg></div><div><div class="t">SHG Fraud Monitor</div>'
                '<div class="s">Loan-diversion screening</div></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="navlabel">Workspace</div>', unsafe_allow_html=True)
    page = st.radio("Navigate", list(PAGES), label_visibility="collapsed")
    st.divider()
    with st.expander("Demo controls"):
        confirm = st.checkbox("Confirm reset")
        if st.button("Reset demo data", disabled=not confirm):
            reset_demo(); st.success("Demo rows reset")
    st.caption("Synthetic data · Prototype\nHuman review is always required.")

try:
    PAGES[page].render()
except Exception as e:
    st.error("This page could not be shown. Run `./train.sh` if model files are missing.")
    with st.expander("Technical details"):
        st.exception(e)
