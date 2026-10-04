"""Cached data loaders for dashboards."""
import pandas as pd
import streamlit as st
from core.config import load_config
from core.db import connect

PATTERN_LABEL = {
    "normal": "Normal member", "business": "Genuine business", "seasonal": "Seasonal income",
    "quick_benign": "Quick repayment (benign)", "benign_cycle": "Circular but genuine",
    "classic": "Pass-through (classic)", "ring": "Ring of members", "multihop": "Multi-hop relay",
    "camouflaged": "Camouflaged", "delayed": "Delayed return", "partial": "Partial return",
    "split_no_return": "Split, no return", "shadow": "Shadow account",
}


@st.cache_data(show_spinner=False)
def members() -> pd.DataFrame:
    cfg = load_config()
    f = pd.read_csv(cfg.root / "data" / "member_features.csv")
    c = connect(cfg.db_path)
    try:
        n = pd.read_sql_query("select id node_id, village, shg_id from nodes where ntype='member'", c)
    finally:
        c.close()
    d = f.merge(n, on="node_id", how="left")
    d["village"] = d["village"].fillna("Unknown")
    d["group"] = d["y"].map({0: "Genuine", 1: "Suspected diversion"})
    d["pattern_label"] = d["pattern"].map(PATTERN_LABEL).fillna(d["pattern"])
    return d


@st.cache_data(show_spinner=False)
def monthly_flow() -> pd.DataFrame:
    cfg = load_config()
    c = connect(cfg.db_path)
    try:
        d = pd.read_sql_query(
            "select strftime('%Y-%m', ts, 'unixepoch') month, count(*) txns, sum(amount) volume "
            "from edges where etype='transfer' group by 1 order by 1", c)
    finally:
        c.close()
    return d


def q(sql: str, params=()):
    cfg = load_config()
    c = connect(cfg.db_path)
    try:
        return pd.read_sql_query(sql, c, params=params)
    finally:
        c.close()
