import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.config import load_config
from . import theme as T
from .common import footer


def render():
    T.page_header("Model Performance", "How well each detection method works on held-out synthetic data.")
    path = load_config().artifacts / "metrics.json"
    if not path.exists():
        st.error("Run `./train.sh` first"); return
    M = json.loads(path.read_text())
    st.warning("Synthetic benchmark — not real-world performance. Every model uses its own validation-selected threshold.")
    t = pd.DataFrame(M["models"]).T.reset_index(names="model")
    best = t.loc[t["auprc"].idxmax()]
    tm = t[t.model == "Topology MLP"].iloc[0]
    k = st.columns(4)
    with k[0]: T.kpi("Test members", M["test_n"], f"{M['test_positives']} true diversion cases", "acc")
    with k[1]: T.kpi("Best benchmark", best.model, f"AUPRC {best.auprc:.2f}", "ok")
    with k[2]: T.kpi("Topology MLP catches", f"{tm.recall:.0%}", "of true cases (recall)", "ok")
    with k[3]: T.kpi("…but false alarms", f"{1-tm.precision:.0%}", "of its flags are wrong", "bad")
    st.write("")
    a, b = st.columns([1.5, 1])
    with a, st.container(border=True):
        T.card_title("Model scorecard", "Higher is better. Compare the bars for each method.")
        long = t.melt(id_vars="model", value_vars=["auprc", "precision", "recall", "f1"], var_name="metric", value_name="score")
        short = {"Logistic Regression": "Logistic reg.", "Gradient Boosting": "Gradient boosting", "pass72 rule": "pass72 rule", "MLP without topology": "MLP, no topology", "MLP without feature-space SMOTE": "MLP, no SMOTE", "Topology MLP": "Topology MLP"}
        long["model"] = long.model.map(short)
        long["metric"] = long.metric.map({"auprc": "Ranking quality (AUPRC)", "precision": "Precision", "recall": "Recall", "f1": "F1"})
        fig = px.bar(long, x="model", y="score", color="metric", barmode="group", color_discrete_sequence=T.SERIES)
        fig.update_xaxes(title=None, tickangle=0, tickfont=dict(size=11)); fig.update_yaxes(range=[0, 1.05], title="Score (1.0 is perfect)")
        st.plotly_chart(T.style(fig, 400), config={"displayModeBar": False})
    with b, st.container(border=True):
        T.card_title("Topology MLP: correct and incorrect calls", "Test set, at its chosen threshold")
        (tn, fp), (fn, tp) = M["confusion_matrix"]
        z = [[tn, fp], [fn, tp]]
        fig = go.Figure(go.Heatmap(z=z, x=["Predicted OK", "Predicted fraud"], y=["Actually OK", "Actually fraud"],
                                   colorscale=[[0, "#F8FAFC"], [1, T.ACCENT]], showscale=False,
                                   text=[[f"{tn}<br>correct", f"{fp}<br>false alarm"], [f"{fn}<br>missed", f"{tp}<br>caught"]],
                                   texttemplate="%{text}", textfont_size=14))
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(T.style(fig, 340, legend=False, margin=dict(l=12, r=12, t=12, b=12)), config={"displayModeBar": False})
        T.insight(f"It caught <b>{tp} of {tp+fn}</b> true cases but raised <b>{fp}</b> false alarms.")
    c, d = st.columns(2)
    roc, pr = M["curves"]["roc"], M["curves"]["pr"]
    with c, st.container(border=True):
        T.card_title("ROC curve", "Closer to the top-left corner is better")
        fig = go.Figure([go.Scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(dash="dot", color=T.MUTED), name="Random guess"),
                         go.Scatter(x=roc["x"], y=roc["y"], mode="lines+markers", fill="tozeroy", fillcolor="rgba(79,70,229,.10)", line=dict(color=T.ACCENT, width=3), name="Topology MLP")])
        fig.update_xaxes(title="False-alarm rate"); fig.update_yaxes(title="Catch rate")
        st.plotly_chart(T.style(fig, 300), config={"displayModeBar": False})
    with d, st.container(border=True):
        T.card_title("Precision–recall curve", "Stays high and to the right = few false alarms while catching most cases")
        fig = go.Figure(go.Scatter(x=pr["x"], y=pr["y"], mode="lines+markers", fill="tozeroy", fillcolor="rgba(5,150,105,.10)", line=dict(color=T.OK, width=3), name="Topology MLP"))
        fig.update_xaxes(title="Recall"); fig.update_yaxes(title="Precision", range=[0, 1.05])
        st.plotly_chart(T.style(fig, 300, legend=False), config={"displayModeBar": False})
    with st.container(border=True):
        T.card_title("Full results table", M["split"])
        nice = t.rename(columns={"model": "Model", "threshold": "Threshold", "auc": "AUC", "auprc": "AUPRC", "f1": "F1", "precision": "Precision", "recall": "Recall", "recall_at_precision_0.9": "Recall at 90% precision", "fpr": "False-alarm rate", "brier": "Brier score"})
        st.dataframe(nice.style.format({c: "{:.3f}" for c in nice.columns if c != "Model"}), hide_index=True, width="stretch")
        r = M["rare_prevalence_simulation"]
        st.metric(f"Simulated AUPRC at {r['prevalence']:.1%} prevalence", f"{r['auprc_mean']:.3f} ± {r['auprc_sd']:.3f}")
        st.caption(f"Simulation uses {r['positives_per_repeat']} positive and {r['negatives_per_repeat']} negative resamples per repeat.")
    if best.model != "Topology MLP":
        st.info(f"The topology MLP is not the best model on this benchmark; {best.model} has the highest AUPRC.")
    T.explain("- **Recall** – of all real diversion cases, how many did we catch?\n- **Precision** – of everything we flagged, how much was really diversion?\n"
              "- **AUPRC** – overall ranking quality when fraud is rare (1.0 is perfect).\n- **Threshold** – the risk score above which something is flagged.\n\n"
              "A model can rank cases perfectly yet still flag too many if its threshold is badly chosen — that is what the false-alarm card shows.")
    footer()
