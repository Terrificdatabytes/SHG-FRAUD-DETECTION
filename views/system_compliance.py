import pandas as pd
import plotly.graph_objects as go
import psutil
import streamlit as st

from core.config import load_config
from core.db import connect, verify_audit_chain
from core.tda import BACKEND
from . import theme as T
from .common import footer

CFG = {"displayModeBar": False}


def _meter(label, value, color):
    fig = go.Figure(go.Indicator(mode="gauge+number", value=value, number={"suffix": "%", "font": {"size": 30}},
                                 gauge={"axis": {"range": [0, 100], "tickvals": [0, 50, 100], "ticksuffix": "%", "tickfont": {"size": 11}}, "bar": {"color": color, "thickness": .3}, "borderwidth": 0,
                                        "steps": [{"range": [0, 100], "color": "#EEF2F7"}]}))
    fig.add_annotation(text=label, x=.5, y=-.05, xref="paper", yref="paper", showarrow=False, font=dict(size=13, color=T.MUTED))
    return T.style(fig, 210, legend=False, margin=dict(l=40, r=40, t=24, b=30))


def render():
    T.page_header("System and Compliance", "Health of the system, privacy safeguards and the tamper-evident audit trail.")
    config = load_config(); connection = connect(config.db_path)
    try:
        valid = verify_audit_chain(connection)
        k = st.columns(4)
        with k[0]: T.kpi("Runtime", "Offline", "no cloud calls for scoring", "acc")
        with k[1]: T.kpi("Loop detection", "Cycle method", BACKEND.replace("time-expanded cycle approximation", "time-expanded approximation"), "acc")
        with k[2]: T.kpi("Database", f"{config.db_path.stat().st_size/1e6:.1f} MB", "local SQLite file", "acc")
        with k[3]: T.kpi("Audit chain", "Valid" if valid else "BROKEN", "hash chain check", "ok" if valid else "bad")
        st.write("")
        a, b, c = st.columns(3)
        for col, lab, val, clr in ((a, "CPU in use", psutil.cpu_percent(interval=.2), T.ACCENT), (b, "Memory in use", psutil.virtual_memory().percent, T.WARN),
                                   (c, "Disk in use", psutil.disk_usage("/").percent, T.OK)):
            with col, st.container(border=True):
                st.plotly_chart(_meter(lab, val, clr), config=CFG)
        T.card_title("Safeguards aligned to responsible-lending practice", "Each control is implemented in this prototype.")
        T.cards([
            ("Explicit consent", "Screening cannot start until consent is recorded.", T.OK),
            ("Hashed identifiers", "HMAC-SHA256 with a per-install secret. Raw names and numbers are not stored.", T.OK),
            ("Reasons shown", "Every flag comes with a plain-language explanation and key evidence.", T.OK),
            ("No automatic rejection", "A score only prompts a check. People take the decision.", T.OK),
            ("Written override", "Approving a flagged case requires a written reason.", T.OK),
            ("Field verification", "Self-help group or federation staff verify before action.", T.OK),
        ], cols=3)
        rows = pd.read_sql_query("SELECT datetime(ts,'unixepoch') ts,actor,action,detail,substr(row_hash,1,12) hash FROM audit_log ORDER BY id DESC LIMIT 200", connection)
        x, y = st.columns([1, 1.3])
        with x, st.container(border=True):
            T.card_title("Audit events by type", "What has been recorded in the audit trail")
            cnt = rows.action.value_counts().sort_values()
            fig = go.Figure(go.Bar(y=cnt.index, x=cnt.values, orientation="h", marker_color=T.ACCENT, width=.6, text=cnt.values, textposition="outside", cliponaxis=False))
            fig.update_xaxes(title="Events", range=[0, cnt.max() * 1.2]); fig.update_yaxes(title=None)
            st.plotly_chart(T.style(fig, 320, legend=False, margin=dict(l=12, r=36, t=12, b=20)), config=CFG)
        with y, st.container(border=True):
            T.card_title("Audit trail", "Newest first. The short hash links each row to the one before it.")
            st.dataframe(rows, hide_index=True, width="stretch", height=320)
    finally:
        connection.close()
    footer()
