import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from . import theme as T
from .common import footer
from .data import members, q

CFG = {"displayModeBar": False}


def render():
    T.page_header("Village and PLF Risk", "Compare villages side by side and decide where field teams should go first.")
    m = members(); m = m[m.village != "Acceptance"]
    v = m.groupby("village").agg(members=("y", "size"), suspicious=("y", "sum"), cycles=("cycles_short", "mean"),
                                 pass72=("pass72", "mean"), vol=("in_volume", "sum")).reset_index()
    v["rate"] = v.suspicious / v.members
    k = st.columns(4)
    with k[0]: T.kpi("Villages", len(v), "in the portfolio", "acc")
    with k[1]: T.kpi("Highest risk", v.sort_values("rate").iloc[-1].village, f"{v.rate.max():.1%} of members", "bad")
    with k[2]: T.kpi("Lowest risk", v.sort_values("rate").iloc[0].village, f"{v.rate.min():.1%} of members", "ok")
    with k[3]: T.kpi("Portfolio average", f"{v.rate.mean():.1%}", "members with diversion patterns", "warn")
    st.write("")
    a, b = st.columns([1, 1])
    with a, st.container(border=True):
        T.card_title("Suspicious share by village", "Dot = village. The dashed line is the portfolio average.")
        d = v.sort_values("rate")
        fig = go.Figure()
        fig.add_trace(go.Bar(y=d.village, x=d.rate, orientation="h", width=.08, marker_color="#CBD5E1", showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(y=d.village, x=d.rate, mode="markers+text", marker=dict(size=16, color=d.rate, colorscale=["#34D399", "#FBBF24", T.BAD], line=dict(width=2, color="white")),
                                 text=[f"{r:.1%}" for r in d.rate], textposition="middle right", textfont=dict(size=12), showlegend=False, cliponaxis=False,
                                 hovertemplate="%{y}: %{x:.1%}<extra></extra>"))
        fig.add_vline(x=v.rate.mean(), line_dash="dash", line_color=T.MUTED)
        fig.update_xaxes(tickformat=".0%", range=[0, v.rate.max() * 1.25], title="Share of members with diversion patterns"); fig.update_yaxes(title=None)
        T.style(fig, 440, legend=False, margin=dict(l=12, r=48, t=12, b=20))
        st.plotly_chart(fig, config=CFG)
    with b, st.container(border=True):
        T.card_title("Heat-map: unusual behaviour by village", "Normal members are left out. Darker means more members of that type.")
        h = m[m.pattern != "normal"].pivot_table(index="village", columns="pattern_label", values="y", aggfunc="size", fill_value=0)
        fig = px.imshow(h, aspect="auto", color_continuous_scale=["#F8FAFC", "#A5B4FC", T.ACCENT], text_auto=True)
        fig.update_xaxes(tickangle=-45, title=None, side="bottom"); fig.update_yaxes(title=None); fig.update_coloraxes(showscale=False)
        T.style(fig, 440, legend=False, margin=dict(l=12, r=12, t=12, b=20))
        fig.update_traces(textfont=dict(size=11))
        st.plotly_chart(fig, config=CFG)
    c, d_ = st.columns([1, 1])
    with c, st.container(border=True):
        T.card_title("Money passed on quickly", "Average share of incoming money passed on within 72 hours")
        d = v.sort_values("pass72")
        fig = go.Figure(go.Bar(y=d.village, x=d.pass72, orientation="h", width=.62, marker_color=T.ACCENT, text=[f"{x:.0%}" for x in d.pass72],
                               textposition="outside", textfont=dict(size=12), cliponaxis=False, hovertemplate="%{y}: %{x:.1%}<extra></extra>"))
        fig.update_xaxes(tickformat=".0%", range=[0, d.pass72.max() * 1.3], title="Average pass-through within 72 hours"); fig.update_yaxes(title=None)
        T.style(fig, 400, legend=False, margin=dict(l=12, r=40, t=12, b=20))
        st.plotly_chart(fig, config=CFG)
    with d_, st.container(border=True):
        T.card_title("Genuine and suspicious members per village", "Stacked count of members")
        s = m.groupby(["village", "group"]).size().reset_index(name="n")
        fig = px.bar(s, x="village", y="n", color="group", color_discrete_map={"Genuine": "#94A3B8", "Suspected diversion": T.BAD},
                     category_orders={"group": ["Genuine", "Suspected diversion"]})
        fig.update_xaxes(title=None, tickangle=-45); fig.update_yaxes(title="Members")
        T.style(fig, 400)
        st.plotly_chart(fig, config=CFG)
    with st.container(border=True):
        T.card_title("Village league table", "Sorted from highest to lowest suspicious share")
        v2 = v.assign(rate=v.rate * 100)
        t = v2.sort_values("rate", ascending=False).rename(columns={
            "village": "Village", "members": "Members", "suspicious": "Suspicious", "rate": "Suspicious share",
            "pass72": "Pass-through (72h)", "cycles": "Avg short loops", "vol": "Money received (Rs)"})
        t["Money received (Rs)"] = t["Money received (Rs)"].map(lambda x: f"{x:,.0f}")
        st.dataframe(t, hide_index=True, width="stretch", column_config={
            "Suspicious share": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=max(float(v2.rate.max()) * 1.2, 5)),
            "Pass-through (72h)": st.column_config.NumberColumn(format="%.2f"),
            "Avg short loops": st.column_config.NumberColumn(format="%.2f")})
    apps = q("select village, count(*) screened, avg(risk) avg_risk, sum(verdict!='LOW') flagged from applications group by village")
    if len(apps):
        with st.container(border=True):
            T.card_title("Applications screened in this session", "Roll-up by village")
            st.dataframe(apps, hide_index=True, width="stretch")
    T.explain("Each row is a village. A suspicious member shows money arriving and leaving quickly through outside accounts, "
              "or circular flows that return money to the applicant. This is a screening clue, not proof of fraud.")
    footer()
