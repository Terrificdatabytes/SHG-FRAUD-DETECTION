"""Time-expanded cycle topology features shared by training and screening.

This module intentionally reports a graph-cycle approximation, not persistent
homology. A counterparty with both outgoing and returning flows is represented
by separate temporal role nodes joined by an identity edge; this turns a
money-out / money-back relationship into an explicit cycle.
"""
from __future__ import annotations

import networkx as nx
import numpy as np
import pandas as pd

BACKEND = "time-expanded cycle approximation"


def temporal_role_graph(df: pd.DataFrame) -> tuple[nx.Graph, str]:
    """Build an undirected time-expanded graph preserving return-flow cycles."""
    account = str(df["account_id"].iloc[0])
    graph = nx.Graph()
    graph.add_node(account, role="applicant")
    for counterparty, group in df.groupby("counterparty_id"):
        counterparty = str(counterparty)
        debits = group[group["direction"] == "DR"]
        credits = group[group["direction"] == "CR"]
        out_node = f"{counterparty}:out"
        in_node = f"{counterparty}:in"
        if not debits.empty:
            graph.add_edge(
                account,
                out_node,
                amount=float(debits["amount"].sum()),
                first_ts=debits["date"].min().timestamp(),
                last_ts=debits["date"].max().timestamp(),
            )
        if not credits.empty:
            graph.add_edge(
                in_node,
                account,
                amount=float(credits["amount"].sum()),
                first_ts=credits["date"].min().timestamp(),
                last_ts=credits["date"].max().timestamp(),
            )
        if not debits.empty and not credits.empty:
            first_out = debits["date"].min()
            later_returns = credits[credits["date"] > first_out]
            if not later_returns.empty:
                lag_days = (later_returns["date"].min() - first_out).total_seconds() / 86400
                graph.add_edge(
                    out_node,
                    in_node,
                    amount=float(later_returns["amount"].sum()),
                    lag_days=float(lag_days),
                    role="identity_return",
                )
    return graph, account


def topology_features(
    graph: nx.Graph, target: str
) -> tuple[np.ndarray, list[str], list[tuple[float, float]]]:
    """Return 24 deterministic cycle-complex features and representative cycles."""
    undirected = nx.Graph(graph)
    if not undirected:
        return np.zeros(24, dtype="float32"), [], []
    cycles = nx.cycle_basis(undirected)
    through_target = [cycle for cycle in cycles if target in cycle]
    b0 = nx.number_connected_components(undirected)
    b1 = max(
        0,
        undirected.number_of_edges()
        - undirected.number_of_nodes()
        + nx.number_connected_components(undirected),
    )
    lifetimes: list[float] = []
    for cycle in cycles:
        lags = []
        for left, right in zip(cycle, cycle[1:] + cycle[:1]):
            edge = undirected.get_edge_data(left, right, {})
            if "lag_days" in edge:
                lags.append(float(edge["lag_days"]))
        lifetimes.append(max(lags) if lags else float(len(cycle)))
    max_life = max(lifetimes, default=0.0)
    sum_life = sum(lifetimes)
    histogram = np.histogram(lifetimes, bins=8, range=(0, max(45.0, max_life)))[0]
    vector = np.zeros(24, dtype="float32")
    vector[:8] = [
        b0,
        b1,
        len(through_target),
        max_life,
        sum_life,
        undirected.number_of_nodes(),
        undirected.number_of_edges(),
        sum(lag <= 14 for lag in lifetimes),
    ]
    vector[8:16] = histogram
    if lifetimes:
        quantiles = np.quantile(lifetimes, np.linspace(0.1, 0.9, 8))
        vector[16:24] = quantiles
    representative = min(through_target, key=len) if through_target else []
    intervals = [(0.0, float(lifetime)) for lifetime in lifetimes]
    return vector, representative, intervals


def report_topology(
    df: pd.DataFrame,
) -> tuple[np.ndarray, list[str], list[tuple[float, float]], nx.Graph, str]:
    """Canonical train-and-serve topology function."""
    normalized = df.copy()
    normalized["date"] = pd.to_datetime(normalized["date"], utc=True)
    graph, target = temporal_role_graph(normalized)
    vector, cycle, intervals = topology_features(graph, target)
    return vector, cycle, intervals, graph, target
