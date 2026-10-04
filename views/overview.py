import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.config import load_config
from . import theme as T
from .common import footer
from .data import members, monthly_flow, q

CFG = {"displayModeBar": False}


def render():
    T.page_header("Executive Overview", "Portfolio health, screening outcomes and where to look first.")
    m = members(); flow = monthly_flow()
    apps = q("select app_id, verdict, risk, ci_low, ci_high, decision, created_ts from applications order by risk desc")
    alerts = q("select alert_id, app_id, level, summary, created_ts, status from alerts order by alert_id desc limit 6")
    open_alerts = int(q("select count(*) n from alerts where status='open'")["n"][0])
    n_shg = int(q("select count(*) n from nodes where ntype='shg'")["n"][0])
    flagged = int((apps.verdict != "LOW").sum()) if len(apps) else 0
    decided = int(apps.decision.notna().sum()) if len(apps) else 0
    flag_rate = flagged / len(apps) if len(apps) else 0
    sus = m[m.village != "Acceptance"]
    top_v = sus.groupby("village").y.mean().sort_values().index[-1]

    T.hero("What this system does",
           "It reads a borrower's bank and UPI transactions before a loan is released and checks whether the money is being passed on to an outside "
           "party. Each application gets a simple verdict: low risk, needs review, or high risk. A person always makes the final decision.")

    cols = st.columns(6)
    with cols[0]: T.kpi("Self-help groups", f"{n_shg:,}", "being monitored", "acc")
    with cols[1]: T.kpi("Members", f"{len(m):,}", f"across {m.village.nunique()} villages", "acc")
    with cols[2]: T.kpi("Transactions", f"{int(flow.txns.sum()):,}", f"Rs {flow.volume.sum()/1e7:,.1f} crore moved", "acc")
    with cols[3]: T.kpi("Applications screened", f"{len(apps):,}", "before disbursal", "acc")
    with cols[4]: T.kpi("Flagged for checks", f"{flag_rate:.0%}", f"{flagged} of {len(apps)} applications", "warn" if flagged else "ok")
    with cols[5]: T.kpi("Open alerts", f"{open_alerts}", "waiting for a reviewer", "bad" if open_alerts else "ok")
    st.write("")

    # ---- row 1
    a, b = st.columns([1, 1.5])
    with a, st.container(border=True):
        T.card_title("Screening outcomes", "How screened applications were classified")
        if len(apps):
            d = apps.verdict.value_counts().reindex(["LOW", "REVIEW", "HIGH"]).fillna(0).reset_index()
            d.columns = ["verdict", "n"]; d["label"] = d.verdict.map(T.VERDICT_LABEL)
            fig = go.Figure(go.Pie(labels=d.label, values=d.n, hole=.64, sort=False, textinfo="value", textfont=dict(size=14, color="white"),
                                   marker=dict(colors=[T.VERDICT[v] for v in d.verdict], line=dict(color="white", width=3)),
                                   hovertemplate="%{label}: %{value} applications (%{percent})<extra></extra>"))
            fig.add_annotation(text=f"<b>{len(apps)}</b>", showarrow=False, font=dict(size=30, color=T.INK), y=.54)
            fig.add_annotation(text="applications", showarrow=False, font=dict(size=12, color=T.MUTED), y=.43)
            T.style(fig, 340, legend=True)
            fig.update_layout(legend=dict(x=.5, xanchor="center", y=-.04, yanchor="top"), margin=dict(l=8, r=8, t=8, b=40))
            st.plotly_chart(fig, config=CFG)
        else:
            st.info("No applications yet. Open New Loan Application and screen a sample report.")
    with b, st.container(border=True):
        T.card_title("Risk ranking of screened applications", "Bar is the risk score, whisker the 90% range, dotted lines the cut-offs")
        if len(apps):
            d = apps.head(14).copy(); d["name"] = d.app_id.str[-6:]; d = d.sort_values("risk")
            fig = go.Figure(go.Bar(y=d.name, x=d.risk * 100, orientation="h", marker_color=[T.VERDICT[v] for v in d.verdict], width=.62,
                                   error_x=dict(type="data", symmetric=False, array=(d.ci_high - d.risk) * 100, arrayminus=(d.risk - d.ci_low) * 100,
                                                color="#475569", thickness=1.4, width=4),
                                   text=[f"{r:.0%}" for r in d.risk], textposition="outside", textfont=dict(size=12), cliponaxis=False,
                                   hovertemplate="Application %{y}: %{x:.1f}% risk<extra></extra>"))
            th = load_config().raw["thresholds"]
            for t, lab in ((th["low"] * 100, "Review"), (th["high"] * 100, "High")):
                fig.add_vline(x=t, line_dash="dot", line_color=T.MUTED, annotation_text=lab, annotation_position="top", annotation_font_size=12)
            fig.update_xaxes(range=[0, 118], ticksuffix="%", title="Risk score"); fig.update_yaxes(title=None, type="category")
            T.style(fig, 340, legend=False, margin=dict(l=12, r=40, t=30, b=20))
            st.plotly_chart(fig, config=CFG)

    # ---- row 2
    c, d_ = st.columns([1, 1.5])
    with c, st.container(border=True):
        T.card_title("From screening to decision", "How many applications reach each stage")
        if len(apps):
            stages = ["Screened", "Needs attention", "Open alerts", "Human decision recorded"]
            vals = [len(apps), flagged, open_alerts, decided]
            fig = go.Figure(go.Funnel(y=stages, x=vals, textinfo="value+percent initial", textfont=dict(size=13),
                                      marker=dict(color=["#4F46E5", "#D97706", "#DC2626", "#059669"]), connector=dict(line=dict(color=T.LINE))))
            T.style(fig, 330, legend=False, margin=dict(l=8, r=8, t=8, b=8))
            st.plotly_chart(fig, config=CFG)
    with d_, st.container(border=True):
        T.card_title("Money moving through the network", "Value of all transfers per month, in rupees lakh. A sudden spike deserves a look.")
        fl = flow[flow.volume > flow.volume.max() * 0.05].copy(); fl["lakh"] = fl.volume / 1e5
        fig = go.Figure(go.Scatter(x=fl.month, y=fl.lakh, mode="lines+markers", fill="tozeroy", line=dict(color=T.ACCENT, width=3),
                                   marker=dict(size=6), fillcolor="rgba(79,70,229,.10)", hovertemplate="%{x}: Rs %{y:,.1f} lakh<extra></extra>"))
        fig.update_yaxes(title="Rupees lakh", tickformat=","); fig.update_xaxes(title=None, tickangle=-45, nticks=12)
        T.style(fig, 330, legend=False)
        st.plotly_chart(fig, config=CFG)

    # ---- row 3
    e, f = st.columns([1.1, 1])
    with e, st.container(border=True):
        T.card_title("Why the model can separate the two groups", "Share of incoming money passed on within 72 hours")
        fig = px.histogram(m, x="pass72", color="group", nbins=24, barmode="overlay", opacity=.78,
                           color_discrete_map={"Genuine": T.OK, "Suspected diversion": T.BAD}, category_orders={"group": ["Genuine", "Suspected diversion"]})
        fig.update_xaxes(title="Money passed on within 72 hours", tickformat=".0%")
        fig.update_yaxes(title="Members (log scale)", type="log", dtick=1)
        T.style(fig, 340)
        st.plotly_chart(fig, config=CFG)
    with f, st.container(border=True):
        T.card_title("Village hot-spots", "Share of members showing diversion patterns")
        v = sus.groupby("village").agg(n=("y", "size"), bad=("y", "sum")).reset_index()
        v["rate"] = v.bad / v.n; v = v.sort_values("rate")
        fig = go.Figure(go.Bar(y=v.village, x=v.rate, orientation="h", width=.66,
                               marker=dict(color=v.rate, colorscale=[[0, "#FDE68A"], [1, T.BAD]]),
                               text=[f"{r:.1%}" for r in v.rate], textposition="outside", textfont=dict(size=12), cliponaxis=False,
                               hovertemplate="%{y}: %{x:.1%} of members<extra></extra>"))
        fig.update_xaxes(tickformat=".0%", range=[0, max(v.rate.max() * 1.3, .05)], title="Share of members"); fig.update_yaxes(title=None)
        T.style(fig, 340, legend=False, margin=dict(l=12, r=40, t=12, b=20))
        st.plotly_chart(fig, config=CFG)
    T.insight(f"{top_v} has the highest share of suspicious members. Start field visits there.")
    st.write("")

    # ---- row 4
    g, h = st.columns([1.3, 1])
    with g, st.container(border=True):
        T.card_title("Types of behaviour in the portfolio", "Red = diversion patterns, grey = genuine (log scale)")
        p = m.groupby(["pattern_label", "group"]).size().reset_index(name="n").sort_values("n")
        fig = px.bar(p, y="pattern_label", x="n", color="group", orientation="h",
                     color_discrete_map={"Genuine": "#94A3B8", "Suspected diversion": T.BAD}, category_orders={"group": ["Genuine", "Suspected diversion"]})
        fig.update_xaxes(title="Members", type="log"); fig.update_yaxes(title=None)
        fig.update_traces(width=.66)
        T.style(fig, 400, margin=dict(l=12, r=24, t=48, b=20))
        st.plotly_chart(fig, config=CFG)
    with h, st.container(border=True):
        T.card_title("Latest alerts", "Most recent items waiting for a human reviewer")
        if len(alerts):
            html = ""
            for _, r in alerts.iterrows():
                html += (f'<div class="alertrow">{T.badge(r.level)}<div class="txt">{r.summary[:120]}...</div>'
                         f'<div class="id">{r.app_id[-6:]}</div></div>')
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.caption("No alerts.")
    T.explain(
        "- **Screening outcomes**: every loan application is checked before money is released. Green is fine, amber needs a closer look, red is held.\n"
        "- **Risk ranking**: the model's confidence that a loan may be passed on to a third party. The thin line on each bar is the range of uncertainty.\n"
        "- **From screening to decision**: how many cases move from automatic screening to a person making a decision.\n"
        "- **Money moving**: total value of transfers per month across all groups.\n"
        "- **Why the model can separate the groups**: diversion cases pass money on very quickly; genuine members rarely do.\n"
        "- **Village hot-spots**: where suspicious behaviour is concentrated, so officers can plan visits.\n\n"
        "All figures come from synthetic data. A flag is a prompt for a human check, never a final verdict.")
    footer()
