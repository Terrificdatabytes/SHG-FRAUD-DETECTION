import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.viz import risk_gauge
from . import theme as T
from .common import footer
from .data import members, q

CFG = {"displayModeBar": False}


def render():
    T.page_header("SHG and Member Detail", "Look at one screened applicant, or explore a whole self-help group.")
    d = q("select * from scores order by scored_ts desc limit 200")
    tab1, tab2 = st.tabs(["Screened applicant", "Explore a self-help group"])
    with tab1:
        if d.empty:
            st.info("No screened members yet. Use New Loan Application to screen one."); 
        else:
            n = st.selectbox("Member alias", d.node_id.str[:12] + "...", index=0)
            r = d.iloc[list(d.node_id.str[:12] + "...").index(n)]
            a, b = st.columns([1, 1.2])
            with a, st.container(border=True):
                T.card_title("Risk score", "Where this applicant sits between low and high risk")
                st.plotly_chart(risk_gauge(r.risk, r.ci_low, r.ci_high), config=CFG)
                T.badge_row([("Verdict", T.VERDICT_LABEL[r.verdict], T.VERDICT[r.verdict]), ("Loops", int(r.betti1), T.ACCENT), ("History", f"{r.hist_months:.1f} months", T.INK)])
            with b, st.container(border=True):
                T.card_title("Compared with everyone screened", "Highlighted bar is this applicant")
                x = d.sort_values("risk").reset_index(drop=True); x["rank"] = x.index + 1
                x["sel"] = x.node_id == r.node_id
                fig = go.Figure(go.Bar(x=x["rank"], y=x.risk * 100, marker_color=[T.VERDICT[v] if s else "#CBD5E1" for v, s in zip(x.verdict, x.sel)],
                                       hovertemplate="Rank %{x}: %{y:.1f}% risk<extra></extra>"))
                fig.update_xaxes(title="Applicants, from lowest to highest risk", dtick=1); fig.update_yaxes(title="Risk score", ticksuffix="%", range=[0, 105])
                st.plotly_chart(T.style(fig, 340, legend=False, margin=dict(l=12, r=12, t=12, b=20)), config=CFG)
    with tab2:
        m = members(); m = m[m.village != "Acceptance"]
        g = m.groupby("shg_id").agg(n=("y", "size"), bad=("y", "sum")).reset_index()
        order = g.sort_values(["bad", "n"], ascending=False).shg_id.tolist()
        shg = st.selectbox("Self-help group (sorted by most suspicious members first)", order)
        s = m[m.shg_id == shg]
        k = st.columns(4)
        with k[0]: T.kpi("Members", len(s), shg, "acc")
        with k[1]: T.kpi("Suspicious", int(s.y.sum()), "members with diversion patterns", "bad" if s.y.sum() else "ok")
        with k[2]: T.kpi("Village", s.village.iloc[0] if len(s) else "n/a", "location", "acc")
        with k[3]: T.kpi("Avg pass-through", f"{s.pass72.mean():.0%}", "within 72 hours", "warn")
        st.write("")
        a, b = st.columns([1.2, 1])
        with a, st.container(border=True):
            T.card_title("Members in this group", "Each dot is a member. Top-right means money is passed on quickly and concentrated in few accounts.")
            fig = px.scatter(s, x="pass72", y="out_concentration", color="group", size=(s.in_volume.clip(lower=1) ** .5),
                             color_discrete_map={"Genuine": T.OK, "Suspected diversion": T.BAD}, hover_name="node_id",
                             category_orders={"group": ["Genuine", "Suspected diversion"]}, size_max=22)
            fig.update_xaxes(title="Money passed on within 72 hours", tickformat=".0%"); fig.update_yaxes(title="Money sent to few accounts", tickformat=".0%")
            st.plotly_chart(T.style(fig, 360), config=CFG)
        with b, st.container(border=True):
            T.card_title("This group versus the portfolio", "Average of key signals")
            cols = {"pass72": "Passed on in 72h", "external_share": "Share with outsiders", "out_concentration": "Concentration"}
            allm = m[list(cols)].mean(); sm = s[list(cols)].mean()
            fig = go.Figure([go.Bar(name="This group", x=list(cols.values()), y=sm.values, marker_color=T.ACCENT, width=.34),
                             go.Bar(name="Whole portfolio", x=list(cols.values()), y=allm.values, marker_color="#CBD5E1", width=.34)])
            fig.update_layout(barmode="group"); fig.update_yaxes(tickformat=".0%", title="Average")
            st.plotly_chart(T.style(fig, 360), config=CFG)
    footer()
