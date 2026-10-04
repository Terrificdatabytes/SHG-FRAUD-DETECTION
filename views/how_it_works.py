import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.config import load_config
from core.viz import timeline
from . import theme as T
from .common import footer
from .data import members

CFG = {"displayModeBar": False}
SIGNALS = [
    ("pass72", "Money passed on within 72 hours", "Share of incoming money that leaves within three days.", "hist"),
    ("out_concentration", "Money sent to few accounts", "How concentrated the outgoing money is on a handful of accounts.", "hist"),
    ("external_share", "Share with outsiders", "Proportion of transfers that go outside the self-help group.", "hist"),
    ("cycles_short", "Members with a return loop", "Percent of members whose money comes back to where it started.", "any"),
    ("two_way_counterparties", "Members with two-way partners", "Accounts that both receive from and send to the applicant.", "any"),
    ("return_amount", "Members with money returned", "Percent of members who receive money back after sending it out.", "any"),
]


def render():
    T.page_header("How It Works", "A plain-language walk-through for judges and field officers.")
    root = load_config().root
    T.hero("In one sentence",
           "The system looks for loans that are quietly passed on to someone outside the group and then partly sent back, "
           "and it asks a human to check those cases before any money is released.")

    # ---- animation 1
    with st.container(border=True):
        T.card_title("The six steps", "Animated overview. The highlighted box is the step running at that moment.")
        st.image(str(root / "assets" / "how_it_works.gif"), width="stretch")

    # ---- animation 2
    st.write("")
    with st.container(border=True):
        T.card_title("What the system is looking for", "Genuine spending versus a diverted loan. Watch where the money goes.")
        st.image(str(root / "assets" / "diversion_vs_genuine.gif"), width="stretch")
    T.cards([
        ("Genuine loan", "Money is spent with several different local suppliers and does not come back. The risk score stays low.", T.OK),
        ("Diverted loan", "Money moves within hours to an outside account and part of it later returns. This is the loop the system detects.", T.BAD),
        ("Why a loop alone is not proof", "Some honest members also have loops, for example family transfers. That is why a person always checks before action.", T.WARN),
    ], cols=3)

    # ---- signals
    st.write("")
    T.card_title("What the model looks at", "Six of the measured signals. Green is genuine members, red is suspected diversion. Less overlap means a clearer signal.")
    m = members(); m = m[m.village != "Acceptance"]
    st.markdown(f'<div class="pills"><span class="pill"><span class="pv" style="color:{T.OK}">Genuine members</span></span>'
                f'<span class="pill"><span class="pv" style="color:{T.BAD}">Suspected diversion</span></span></div>', unsafe_allow_html=True)
    cols = st.columns(3)
    for i, (col, ttl, sub, kind) in enumerate(SIGNALS):
        with cols[i % 3], st.container(border=True):
            T.card_title(ttl, sub)
            if kind == "hist":
                fig = px.histogram(m, x=col, color="group", nbins=22, barmode="overlay", opacity=.78, histnorm="percent",
                                   color_discrete_map={"Genuine": T.OK, "Suspected diversion": T.BAD},
                                   category_orders={"group": ["Genuine", "Suspected diversion"]})
                fig.update_xaxes(title="Value", tickformat=".0%"); fig.update_yaxes(title="% of members", ticksuffix="%")
            else:
                share = (m.assign(flag=m[col] > 0).groupby("group").flag.mean() * 100).reindex(["Genuine", "Suspected diversion"])
                fig = go.Figure(go.Bar(x=share.index, y=share.values, marker_color=[T.OK, T.BAD], width=.5,
                                       text=[f"{v:.0f}%" for v in share.values], textposition="outside", textfont=dict(size=13), cliponaxis=False))
                fig.update_xaxes(title=None); fig.update_yaxes(title="% of members", ticksuffix="%", range=[0, 118])
            T.style(fig, 270, legend=False, margin=dict(l=12, r=12, t=14, b=16))
            st.plotly_chart(fig, config=CFG, key=f"sig_{i}")

    # ---- worked examples
    st.write("")
    ap = root / "artifacts" / "acceptance.json"
    if ap.exists():
        acc = pd.DataFrame(json.loads(ap.read_text()))
        a, b = st.columns([1, 1.25])
        with a, st.container(border=True):
            T.card_title("Ten test applicants and what the system said", "Every verdict matches the documented expectation (PASS).")
            acc = acc.assign(risk_pct=acc.risk * 100)
            fig = go.Figure(go.Bar(y=acc.case.str.replace("Applicant_", "Applicant "), x=acc.risk_pct, orientation="h", width=.62,
                                   marker_color=[T.VERDICT[x] for x in acc.actual], text=[f"{x}  |  {r:.1f}%" for x, r in zip(acc.actual, acc.risk_pct)],
                                   textposition="outside", textfont=dict(size=12), cliponaxis=False,
                                   hovertemplate="%{y}: %{x:.2f}% risk<extra></extra>"))
            fig.update_xaxes(range=[0, 135], ticksuffix="%", title="Risk score"); fig.update_yaxes(autorange="reversed", title=None)
            T.style(fig, 420, legend=False, margin=dict(l=12, r=24, t=12, b=20))
            st.plotly_chart(fig, config=CFG)
            passed = int((acc.status == "PASS").sum())
            T.badge_row([("Acceptance result", f"{passed} of {len(acc)} pass", T.OK), ("Average screening time", f"{acc.latency_s.mean()*1000:.0f} ms", T.ACCENT)])
        with b, st.container(border=True):
            T.card_title("See an applicant's transactions", "Pick a test applicant to see money in (green) and money out (red) over time.")
            name = st.selectbox("Applicant", list(acc.case), index=4, label_visibility="collapsed")
            df = pd.read_csv(root / "demo_cases" / f"{name}.csv")
            rec = df.rename(columns={"direction": "direction"}).to_dict("records")
            fig = timeline(rec)
            fig.update_layout(height=340)
            st.plotly_chart(fig, config=CFG)
            row = acc[acc.case == name].iloc[0]
            T.badge_row([("Verdict", T.VERDICT_LABEL[row.actual], T.VERDICT[row.actual]), ("Risk", f"{row.risk:.1%}", T.INK), ("Loops found", int(row.betti1), T.ACCENT)])
        with st.container(border=True):
            T.card_title("Where the screening time goes", "Average milliseconds per stage. The whole check takes about a tenth of a second.")
            tm = pd.DataFrame([r for r in acc.timings_ms]).mean().sort_values()
            fig = go.Figure(go.Bar(y=tm.index, x=tm.values, orientation="h", width=.6, marker_color=T.ACCENT,
                                   text=[f"{v:.0f} ms" for v in tm.values], textposition="outside", textfont=dict(size=12), cliponaxis=False))
            fig.update_xaxes(title="Milliseconds", range=[0, tm.max() * 1.2]); fig.update_yaxes(title=None)
            T.style(fig, 300, legend=False, margin=dict(l=12, r=40, t=12, b=20))
            st.plotly_chart(fig, config=CFG)

    # ---- safeguards
    st.write("")
    T.card_title("Built-in safeguards", "What protects members and keeps decisions accountable.")
    T.cards([
        ("Consent first", "A report is only screened after the applicant consents to transaction-data screening.", T.ACCENT),
        ("Privacy by design", "Names, numbers and account IDs are converted to secret codes before anything is stored.", T.ACCENT),
        ("Human decides", "The score never rejects anyone automatically. A flagged approval needs a written reason.", T.OK),
        ("Tamper-evident log", "Every action is chained to the previous one, so edits to the audit trail can be detected.", T.OK),
    ], cols=4)
    with st.container(border=True):
        T.card_title("Honest limits", "What judges should know about this prototype.")
        st.markdown(
            "- The data is **synthetic**. Real-world accuracy has not been measured.\n"
            "- The detector is a small neural network (MLP) over behaviour and loop features. It is not a graph neural network and does not compute persistent homology.\n"
            "- A simpler gradient-boosting model scores perfectly on this synthetic test, which shows the generated data is easier than real data.\n"
            "- Fairness, drift and a real pilot with governed data are still required.")
    with st.expander("Glossary"):
        st.dataframe(pd.DataFrame([
            ("SHG", "Self-Help Group: a small savings and credit group of local women"),
            ("PLF", "Panchayat Level Federation: a federation of village groups"),
            ("VPRC", "Village Poverty Reduction Committee"),
            ("CIF / VRF", "Community Investment Fund / Vulnerability Reduction Fund: loan funds"),
            ("Diversion", "Loan money passed on to someone other than the borrower"),
            ("Loop (cycle)", "Money that leaves an account and later comes back to it"),
            ("Recall / Precision", "Cases caught out of all real cases / real cases out of everything flagged"),
        ], columns=["Term", "Meaning"]), hide_index=True, width="stretch")
    footer()
