"""Behavioural and time-respecting transaction features."""
from __future__ import annotations

import numpy as np
import pandas as pd

FEATURE_NAMES = [
    "txn_count", "in_volume", "out_volume", "amount_mean", "amount_std",
    "counterparties", "fan_in", "fan_out", "external_share", "history_months",
    "pass72", "pass7d", "cycles_short", "max_cycle_amount", "median_cycle_lag",
    "return_before_repay", "two_way_counterparties", "third_party_saving",
    "income_absent", "loan_credit", "rapid_out_amount", "return_amount",
    "out_concentration", "channel_diversity",
]


def report_features(df: pd.DataFrame) -> dict[str, float]:
    """Compute bounded per-report features without label or filename access."""
    data = df.sort_values("date").copy()
    data["date"] = pd.to_datetime(data["date"], utc=True)
    credits = data[data["direction"] == "CR"]
    debits = data[data["direction"] == "DR"]
    total = float(data["amount"].sum())
    days = max(1, int((data["date"].max() - data["date"].min()).days))
    loan_mask = (credits["channel"] == "LOAN_DISBURSAL") | credits["narration"].str.contains(
        "loan|disburs", case=False, na=False
    )
    loans = credits[loan_mask]
    rapid_amount = 0.0
    seven_day_amount = 0.0
    for loan in loans.itertuples():
        delta = debits["date"] - loan.date
        rapid_amount += float(debits.loc[(delta >= pd.Timedelta(0)) & (delta <= pd.Timedelta(hours=72)), "amount"].sum())
        seven_day_amount += float(debits.loc[(delta >= pd.Timedelta(0)) & (delta <= pd.Timedelta(days=7)), "amount"].sum())
    return_amount = 0.0
    cycle_lags: list[float] = []
    short_cycles = 0
    two_way = 0
    for _, group in data.groupby("counterparty_id"):
        outgoing = group[group["direction"] == "DR"]
        incoming = group[group["direction"] == "CR"]
        if outgoing.empty or incoming.empty:
            continue
        two_way += 1
        first_out = outgoing["date"].min()
        later = incoming[incoming["date"] > first_out]
        if later.empty:
            continue
        lag = float((later["date"].min() - first_out).total_seconds() / 86400)
        cycle_lags.append(lag)
        return_amount += float(later["amount"].sum())
        short_cycles += int(lag <= 14)
    loan_amount = max(float(loans["amount"].sum()), 1.0)
    outgoing_by_counterparty = debits.groupby("counterparty_id")["amount"].sum()
    saving_credits = credits[credits["narration"].str.contains("saving", case=False, na=False)]
    third_party_saving = float(saving_credits["amount"].sum() / max(float(credits["amount"].sum()), 1.0))
    values = [
        len(data), float(credits["amount"].sum()), float(debits["amount"].sum()),
        float(data["amount"].mean()), float(data["amount"].std(ddof=0)),
        data["counterparty_id"].nunique(), credits["counterparty_id"].nunique(),
        debits["counterparty_id"].nunique(), float(debits["amount"].sum()) / max(total, 1.0),
        days / 30.44, rapid_amount / loan_amount, seven_day_amount / loan_amount,
        short_cycles, min(rapid_amount, return_amount),
        float(np.median(cycle_lags)) if cycle_lags else 0.0,
        float(return_amount > 0), two_way, third_party_saving,
        float(credits.empty), float(loans["amount"].sum()), rapid_amount, return_amount,
        float(outgoing_by_counterparty.max() / max(float(debits["amount"].sum()), 1.0)) if len(outgoing_by_counterparty) else 0.0,
        data["channel"].nunique(),
    ]
    return dict(zip(FEATURE_NAMES, map(float, values)))
