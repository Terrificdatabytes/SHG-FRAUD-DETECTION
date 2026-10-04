import plotly.graph_objects as go
import streamlit as st

from core.viz import persistence_diagram, barcode
from . import theme as T
from .common import footer

CFG = {"displayModeBar": False}


def _net(nodes, edges, loop_edges=(), top=(), height=290):
    fig = go.Figure()
    for a, b in edges:
        (x0, y0), (x1, y1) = nodes[a][:2], nodes[b][:2]
        loop = (a, b) in loop_edges
        fig.add_annotation(x=x1, y=y1, ax=x0, ay=y0, xref="x", yref="y", axref="x", ayref="y", showarrow=True, arrowhead=3, arrowsize=1.4,
                           arrowwidth=3 if loop else 2, arrowcolor=T.BAD if loop else "#94A3B8", standoff=22, startstandoff=22)
    fig.add_trace(go.Scatter(x=[n[0] for n in nodes.values()], y=[n[1] for n in nodes.values()], mode="markers+text",
                             text=list(nodes.keys()), textposition=["top center" if k in top else "bottom center" for k in nodes], textfont=dict(size=12, color=T.INK),
                             marker=dict(size=34, color=[n[2] for n in nodes.values()], line=dict(width=3, color="white")),
                             hoverinfo="text", showlegend=False, cliponaxis=False))
    fig.update_xaxes(visible=False, range=[-.4, 4.4]); fig.update_yaxes(visible=False, range=[-.7, 1.6])
    return T.style(fig, height, legend=False, margin=dict(l=8, r=8, t=8, b=8))


def render():
    T.page_header("Cycle Topology Evidence", "How the system turns a list of transfers into a picture, and why a return loop matters.")
    T.hero("The idea",
           "Draw every account as a dot and every transfer as an arrow. Money that goes out and later comes back makes a closed loop in the picture. "
           "The system counts those loops and how long they stay open.")
    a, b = st.columns(2)
    A, R, G, B = T.ACCENT, T.BAD, T.OK, "#94A3B8"
    with a, st.container(border=True):
        T.card_title("Genuine member: no loop", "Money goes out to different suppliers and stays out.")
        nodes = {"Bank": (0, .6, A), "Member": (1.4, .6, A), "Seed shop": (3, 1.1, G), "Tools": (3, .6, G), "Labour": (3, 0, G)}
        edges = [("Bank", "Member"), ("Member", "Seed shop"), ("Member", "Tools"), ("Member", "Labour")]
        st.plotly_chart(_net(nodes, edges), config=CFG)
        T.badge_row([("Independent loops", "0", T.OK), ("Verdict", "Low risk", T.OK)])
    with b, st.container(border=True):
        T.card_title("Diverted loan: closed loop", "Money goes to an outside account, then back toward the member.")
        nodes = {"Bank": (0, .6, A), "Member": (1.2, .6, A), "Outside account": (2.4, 1.1, R), "Third party": (3.6, .2, R)}
        edges = [("Bank", "Member"), ("Member", "Outside account"), ("Outside account", "Third party"), ("Third party", "Member")]
        st.plotly_chart(_net(nodes, edges, loop_edges={("Member", "Outside account"), ("Outside account", "Third party"), ("Third party", "Member")}, top=("Outside account",)), config=CFG)
        T.badge_row([("Independent loops", "1", T.BAD), ("Verdict", "High risk", T.BAD)])

    r = st.session_state.get("last_screen")
    pers = r.persistence if r else [(0, 12), (0, 4)]
    src = "Latest screened applicant" if r else "Example case"
    c, d = st.columns(2)
    with c, st.container(border=True):
        T.card_title("When does each loop appear and close?", f"{src}. Points far from the dashed line are loops that stay open longer.")
        st.plotly_chart(persistence_diagram(pers), config=CFG)
    with d, st.container(border=True):
        T.card_title("How long does each loop stay open?", f"{src}. Longer bars mean money took longer to return.")
        st.plotly_chart(barcode(pers), config=CFG)
    T.explain("This prototype uses a disclosed approximation: outgoing and returning roles of the same account are separated in time so a return flow shows up as a loop. "
              "It is not a persistent-homology computation. A loop is a clue, not proof, because some honest members also have family or business loops.")
    footer()
