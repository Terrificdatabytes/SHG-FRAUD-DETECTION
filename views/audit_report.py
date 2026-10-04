import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from . import theme as T
from .common import footer
from .data import q

CFG = {"displayModeBar": False}


def render():
    T.page_header("Explanation and Audit Report", "Every screened case with its reason, decision and downloadable register.")
    d = q("select a.app_id,a.verdict,a.risk,a.ci_low,a.ci_high,a.decision,a.decision_reason,a.amount,a.purpose,e.text from applications a "
          "left join explanations e on a.node_id=e.node_id order by a.created_ts desc")
    if d.empty:
        st.info("No cases yet."); footer(); return
    k = st.columns(4)
    with k[0]: T.kpi("Cases", len(d), "in the register", "acc")
    with k[1]: T.kpi("Requested", f"Rs {d.amount.sum()/1e5:,.1f} lakh", "total loan value screened", "acc")
    with k[2]: T.kpi("On hold or flagged", f"Rs {d[d.verdict != 'LOW'].amount.sum()/1e5:,.1f} lakh", "needs human checks", "warn")
    with k[3]: T.kpi("Decisions recorded", int(d.decision.notna().sum()), "by a reviewer", "ok")
    st.write("")
    a, b = st.columns(2)
    with a, st.container(border=True):
        T.card_title("Loan value by verdict", "Rupees lakh requested, grouped by screening result")
        g = d.groupby("verdict").amount.sum().reindex(["LOW", "REVIEW", "HIGH"]).fillna(0) / 1e5
        fig = go.Figure(go.Bar(x=[T.VERDICT_LABEL[i] for i in g.index], y=g.values, marker_color=[T.VERDICT[i] for i in g.index], width=.45,
                               text=[f"{v:,.1f}" for v in g.values], textposition="outside", textfont=dict(size=13)))
        fig.update_yaxes(title="Rupees lakh", range=[0, max(g.max() * 1.25, 1)]); fig.update_xaxes(title=None)
        st.plotly_chart(T.style(fig, 300, legend=False, margin=dict(l=12, r=12, t=20, b=16)), config=CFG)
    with b, st.container(border=True):
        T.card_title("Human decisions", "What reviewers decided so far")
        c = d.decision.fillna("Pending").value_counts()
        fig = go.Figure(go.Bar(y=c.index, x=c.values, orientation="h", marker_color=T.ACCENT, width=.5, text=c.values, textposition="outside"))
        fig.update_xaxes(title="Cases", range=[0, c.max() * 1.25]); fig.update_yaxes(title=None, autorange="reversed")
        st.plotly_chart(T.style(fig, 300, legend=False, margin=dict(l=12, r=24, t=12, b=20)), config=CFG)
    with st.container(border=True):
        T.card_title("Case register", "Download as CSV for the audit file")
        st.dataframe(d, hide_index=True, width="stretch")
        st.download_button("Download case register (CSV)", d.to_csv(index=False), file_name="case_register.csv", mime="text/csv")
    footer()
