import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.config import load_config
from core.db import audit, connect
from .common import footer
from . import theme as T
from .theme import page_header


def render():
    page_header("Review Queue")
    connection = connect(load_config().db_path)
    try:
        data = pd.read_sql_query(
            "SELECT alert_id,app_id,level,summary,datetime(created_ts,'unixepoch') created,status "
            "FROM alerts ORDER BY alert_id DESC",
            connection,
        )
        if len(data):
            k = st.columns(4)
            with k[0]: T.kpi("Total alerts", len(data), "raised so far", "acc")
            with k[1]: T.kpi("Open", int((data.status == "open").sum()), "need a reviewer", "bad")
            with k[2]: T.kpi("High level", int((data.level == "HIGH").sum()), "most urgent", "bad")
            with k[3]: T.kpi("Closed", int((data.status != "open").sum()), "reviewed by a person", "ok")
            st.write("")
            a, b = st.columns(2)
            with a, st.container(border=True):
                T.card_title("Alerts by level", "How urgent the open items are")
                c = data.level.value_counts().reindex(["HIGH", "REVIEW"]).fillna(0)
                fig = go.Figure(go.Bar(x=[T.VERDICT_LABEL[i] for i in c.index], y=c.values, marker_color=[T.VERDICT[i] for i in c.index], width=.45,
                                       text=c.values.astype(int), textposition="outside", textfont=dict(size=13)))
                fig.update_yaxes(title="Alerts", range=[0, max(c.max() * 1.25, 3)]); fig.update_xaxes(title=None)
                st.plotly_chart(T.style(fig, 280, legend=False, margin=dict(l=12, r=12, t=20, b=16)), config={"displayModeBar": False})
            with b, st.container(border=True):
                T.card_title("Alerts by status", "Open, confirmed, dismissed or escalated")
                c = data.status.value_counts()
                fig = go.Figure(go.Pie(labels=c.index.str.capitalize(), values=c.values, hole=.6, textinfo="value", textfont=dict(size=13, color="white"),
                                       marker=dict(colors=[T.BAD, T.OK, T.MUTED, T.WARN][:len(c)], line=dict(color="white", width=3))))
                fig.update_layout(legend=dict(x=.5, xanchor="center", y=-.02, yanchor="top"))
                st.plotly_chart(T.style(fig, 280, legend=True, margin=dict(l=8, r=8, t=8, b=40)).update_layout(legend=dict(orientation="h", x=.5, xanchor="center", y=-.02, yanchor="top")), config={"displayModeBar": False})
        with st.container(border=True):
            T.card_title("Alert register", "Select an alert below to record your review")
            st.dataframe(data, hide_index=True, width="stretch")
        if len(data):
            alert_id = st.selectbox("Alert", data.alert_id)
            action = st.radio("Review action", ["Confirm", "Dismiss", "Escalate"], horizontal=True)
            actor = st.text_input("Reviewer ID", value="demo-reviewer")
            comment = st.text_input("Reviewer comment")
            if st.button("Save review"):
                if len(comment.strip()) < 5:
                    st.error("A review comment of at least 5 characters is required")
                else:
                    row = connection.execute(
                        "SELECT app_id FROM alerts WHERE alert_id=?", (int(alert_id),)
                    ).fetchone()
                    status = action.lower()
                    decision = {"Confirm": "Hold", "Dismiss": "Reject", "Escalate": "Hold"}[action]
                    connection.execute(
                        "UPDATE alerts SET status=? WHERE alert_id=?", (status, int(alert_id))
                    )
                    connection.execute(
                        "UPDATE applications SET decision=?,decision_reason=?,decided_ts=strftime('%s','now') "
                        "WHERE app_id=? AND decision IS NULL",
                        (decision, comment.strip(), row["app_id"]),
                    )
                    audit(
                        connection,
                        "ALERT_REVIEW",
                        f"{alert_id} {action}: {comment.strip()}",
                        actor.strip() or "unknown-reviewer",
                    )
                    connection.commit()
                    st.success("Review and application state saved")
    finally:
        connection.close()
    footer()
