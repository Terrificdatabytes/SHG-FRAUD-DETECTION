"""Enterprise-SaaS look & feel: CSS, KPI cards, headers and a shared Plotly style."""
import streamlit as st

# Semantic palette (colour-blind-safe pairing: green / amber / red also differ in label + position)
INK, MUTED, LINE = "#0F172A", "#64748B", "#E2E8F0"
ACCENT, ACCENT_SOFT = "#4F46E5", "#EEF2FF"
OK, WARN, BAD = "#059669", "#D97706", "#DC2626"
VERDICT = {"LOW": OK, "REVIEW": WARN, "HIGH": BAD}
VERDICT_LABEL = {"LOW": "Low risk", "REVIEW": "Needs review", "HIGH": "High risk"}
SERIES = ["#4F46E5", "#0EA5E9", "#14B8A6", "#F59E0B", "#EC4899", "#8B5CF6"]

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stApp {{ font-family: 'Inter', -apple-system, 'Segoe UI', Roboto, sans-serif; }}
.stApp {{ background: #F5F7FB; }}
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {{ display: none !important; }}
header[data-testid="stHeader"] {{ background: transparent; height: 0; }}
.block-container {{ padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1400px; }}

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {{ background: #0B1220; border-right: 1px solid #1E293B; }}
[data-testid="stSidebar"] * {{ color: #CBD5E1; }}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{ color: #F8FAFC; }}
[data-testid="stSidebar"] [data-testid="stRadio"] > label {{ display: none; }}
[data-testid="stSidebar"] [data-testid="stRadioGroup"], [data-testid="stSidebar"] div[role="radiogroup"] {{ gap: 2px; }}
[data-testid="stSidebar"] label[data-testid="stRadioOption"], [data-testid="stSidebar"] label[data-baseweb="radio"] {{
  padding: 9px 12px; border-radius: 8px; width: 100%; margin: 0; transition: background .15s; cursor: pointer; }}
[data-testid="stSidebar"] label[data-testid="stRadioOption"]:hover, [data-testid="stSidebar"] label[data-baseweb="radio"]:hover {{ background: #1E293B; }}
[data-testid="stSidebar"] label[data-testid="stRadioOption"][data-selected="true"],
[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) {{ background: {ACCENT}; }}
[data-testid="stSidebar"] label[data-testid="stRadioOption"][data-selected="true"] *,
[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) * {{ color: #fff !important; font-weight: 600; }}
/* hide the round radio dot (new and old Streamlit DOMs) */
[data-testid="stSidebar"] label[data-testid="stRadioOption"] > div > div:first-child,
[data-testid="stSidebar"] label[data-baseweb="radio"] > div:first-child {{ display: none !important; }}
[data-testid="stSidebar"] hr {{ border-color: #1E293B; }}
[data-testid="stSidebar"] [data-testid="stExpander"] {{ background:#111A2E; border:1px solid #1E293B; }}
[data-testid="stSidebar"] [data-testid="stExpander"] summary, [data-testid="stSidebar"] [data-testid="stExpander"] summary * {{ color:#CBD5E1 !important; }}
.brand {{ display:flex; align-items:center; gap:10px; padding: 6px 4px 14px; }}
.brand .logo {{ width:34px; height:34px; border-radius:9px; background: linear-gradient(135deg,#6366F1,#22D3EE);
  display:flex; align-items:center; justify-content:center; font-size:18px; }}
.brand .t {{ color:#F8FAFC !important; font-weight:700; font-size:15px; line-height:1.1; }}
.brand .s {{ color:#94A3B8 !important; font-size:11px; }}
.navlabel {{ font-size:10.5px; letter-spacing:.09em; text-transform:uppercase; color:#64748B !important; margin:14px 4px 4px; }}

/* ---------- page header ---------- */
.ph {{ display:flex; justify-content:space-between; align-items:flex-end; margin-bottom: 18px; }}
.ph .ttl {{ font-size: 26px; font-weight: 700; color:{INK}; margin:0; padding:0; line-height:1.2; letter-spacing:-.02em; }}
.ph p {{ color:{MUTED}; margin:4px 0 0; font-size:14px; }}
.chip {{ display:inline-flex; align-items:center; gap:6px; padding:5px 11px; border-radius:999px; font-size:12px;
  font-weight:600; background:{ACCENT_SOFT}; color:{ACCENT}; border:1px solid #C7D2FE; }}
.chip.dot::before {{ content:''; width:7px; height:7px; border-radius:50%; background:{OK}; }}

/* ---------- KPI cards ---------- */
.kpi {{ min-height:112px; background:#fff; border:1px solid {LINE}; border-radius:14px; padding:16px 18px; height:100%;
  box-shadow: 0 1px 2px rgba(15,23,42,.04); }}
.kpi .l {{ font-size:12px; color:{MUTED}; font-weight:600; text-transform:uppercase; letter-spacing:.06em; }}
.kpi .v {{ font-size:30px; font-weight:700; color:{INK}; margin-top:4px; letter-spacing:-.02em; }}
.kpi .d {{ font-size:12.5px; color:{MUTED}; margin-top:2px; }}
.kpi.ok {{ border-top:3px solid {OK}; }} .kpi.warn {{ border-top:3px solid {WARN}; }}
.kpi.bad {{ border-top:3px solid {BAD}; }} .kpi.acc {{ border-top:3px solid {ACCENT}; }}

/* ---------- cards (st.container(border=True)) ---------- */
[data-testid="stVerticalBlockBorderWrapper"] {{ background:#fff; border-radius:14px !important;
  border:1px solid {LINE} !important; box-shadow: 0 1px 2px rgba(15,23,42,.04); }}
.ct {{ font-size:15px; font-weight:650; color:{INK}; margin:0; }}
.cs {{ font-size:12.5px; color:{MUTED}; margin:2px 0 6px; }}
.insight {{ background:{ACCENT_SOFT}; border:1px solid #C7D2FE; color:#312E81; border-radius:10px;
  padding:10px 14px; font-size:13.5px; margin-top:6px; }}
.insight b {{ color:#1E1B4B; }}

/* ---------- info cards / pills ---------- */
.icard {{ background:#fff; border:1px solid {LINE}; border-radius:12px; padding:16px 18px; min-height:132px; margin-bottom:12px; }}
.icard .it {{ font-size:14.5px; font-weight:650; color:{INK}; margin-bottom:6px; }}
.icard .ix {{ font-size:13px; line-height:1.5; color:#475569; }}
.pills {{ display:flex; flex-wrap:wrap; gap:8px; margin:4px 0 10px; }}
.pill {{ display:inline-flex; gap:8px; align-items:baseline; background:#fff; border:1px solid {LINE}; border-radius:999px; padding:5px 12px; }}
.pill .pl {{ font-size:12px; color:{MUTED}; }} .pill .pv {{ font-size:13px; font-weight:700; }}
.hero {{ background:linear-gradient(135deg,#312E81 0%,#4F46E5 60%,#0EA5E9 120%); color:#fff; border-radius:16px; padding:22px 26px; margin-bottom:16px; }}
.hero .h {{ font-size:20px; font-weight:700; letter-spacing:-.01em; }} .hero .s {{ font-size:14px; opacity:.9; margin-top:6px; line-height:1.5; max-width:880px; }}
.brand .logo svg {{ width:20px; height:20px; }}

/* ---------- badges / alerts ---------- */
.badge {{ display:inline-block; padding:3px 10px; border-radius:999px; font-size:11.5px; font-weight:700; color:#fff; }}
.alertrow {{ display:flex; gap:12px; align-items:flex-start; padding:11px 4px; border-bottom:1px solid {LINE}; }}
.alertrow:last-child {{ border-bottom:none; }}
.alertrow .txt {{ font-size:13px; color:#334155; flex:1; }}
.alertrow .id {{ font-size:12px; color:{MUTED}; white-space:nowrap; }}

/* ---------- native widgets ---------- */
.stButton > button {{ border-radius:9px; font-weight:600; border:1px solid {LINE}; }}
.stButton > button[kind="primary"] {{ background:{ACCENT}; border-color:{ACCENT}; color:#fff !important; }}
.stButton > button[kind="primary"]:disabled {{ background:#A5B4FC; border-color:#A5B4FC; color:#fff !important; opacity:1; }}
.stButton > button[kind="primary"]:hover {{ background:#4338CA; }}
[data-testid="stMetric"] {{ background:#fff; border:1px solid {LINE}; border-radius:12px; padding:12px 14px; }}
[data-testid="stDataFrame"] {{ border:1px solid {LINE}; border-radius:10px; overflow:hidden; }}
.stTabs [data-baseweb="tab-list"] {{ gap:4px; border-bottom:1px solid {LINE}; }}
.stTabs [data-baseweb="tab"] {{ border-radius:8px 8px 0 0; padding:8px 14px; font-weight:600; }}
[data-testid="stExpander"] {{ background:#fff; border:1px solid {LINE}; border-radius:10px; }}
</style>
"""


def inject():
    st.markdown(CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "", chip: str = "Synthetic data · Prototype"):
    st.markdown(
        f'<div class="ph"><div><div class="ttl">{title}</div><p>{subtitle}</p></div>'
        f'<span class="chip dot">{chip}</span></div>',
        unsafe_allow_html=True,
    )


def kpi(label: str, value, detail: str = "", tone: str = "acc"):
    size = "30px" if len(str(value)) <= 11 else "22px"
    st.markdown(
        f'<div class="kpi {tone}"><div class="l">{label}</div><div class="v" style="font-size:{size}">{value}</div>'
        f'<div class="d">{detail}</div></div>',
        unsafe_allow_html=True,
    )


def card_title(title: str, subtitle: str = ""):
    st.markdown(f'<p class="ct">{title}</p><p class="cs">{subtitle}</p>', unsafe_allow_html=True)


def insight(text: str):
    st.markdown(f'<div class="insight"><b>Key takeaway.</b> {text}</div>', unsafe_allow_html=True)


def badge(verdict: str) -> str:
    return f'<span class="badge" style="background:{VERDICT.get(verdict, MUTED)}">{VERDICT_LABEL.get(verdict, verdict)}</span>'


def explain(text: str, title: str = "How to read this page"):
    with st.expander(title):
        st.markdown(text)


FONT = "Inter, Segoe UI, Helvetica, Arial, sans-serif"


def style(fig, height=320, legend=True, margin=None):
    """Shared Plotly look: one font, fixed text sizes, legend above the plot, auto-fitted axis margins."""
    fig.update_layout(
        height=height, autosize=True, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=margin or dict(l=16, r=24, t=48 if legend else 16, b=20),
        font=dict(family=FONT, size=13, color="#334155"), colorway=SERIES, showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="left", x=0, title=None,
                    font=dict(size=12), itemsizing="constant"),
        hoverlabel=dict(bgcolor="white", font=dict(size=12, family=FONT), bordercolor=LINE),
        title=None, uniformtext=dict(minsize=11, mode="hide"),
    )
    axis = dict(automargin=True, tickfont=dict(size=12, color="#475569"), title_font=dict(size=12, color=MUTED),
                title_standoff=12, linecolor=LINE, zeroline=False)
    fig.update_xaxes(showgrid=False, **axis)
    fig.update_yaxes(gridcolor="#EEF2F7", **axis)
    return fig


def cards(items, cols=4, tone=ACCENT):
    """Plain HTML info cards. items = [(title, text)] or [(title, text, colour)]."""
    cells = st.columns(cols)
    for i, it in enumerate(items):
        col = it[2] if len(it) > 2 else tone
        with cells[i % cols]:
            st.markdown(
                f'<div class="icard" style="border-top:3px solid {col}"><div class="it">{it[0]}</div>'
                f'<div class="ix">{it[1]}</div></div>', unsafe_allow_html=True)


def badge_row(pairs):
    """pairs = [(label, value, colour)] rendered as small stat pills."""
    html = "".join(f'<span class="pill"><span class="pl">{l}</span><span class="pv" style="color:{c}">{v}</span></span>' for l, v, c in pairs)
    st.markdown(f'<div class="pills">{html}</div>', unsafe_allow_html=True)


def hero(title: str, text: str):
    st.markdown(f'<div class="hero"><div class="h">{title}</div><div class="s">{text}</div></div>', unsafe_allow_html=True)
