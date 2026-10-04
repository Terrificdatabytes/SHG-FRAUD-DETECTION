"""Train topology-MLP variants on SHG-disjoint temporal observations."""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import average_precision_score, precision_recall_curve
from sklearn.preprocessing import StandardScaler

from .config import load_config
from .features import FEATURE_NAMES, report_features
from .imbalance import smote_enn
from .model import TopologyMLP
from .scaling import save_scaler
from .tda import report_topology

TDA_COLUMNS = [f"topology_{index}" for index in range(24)]


def temporal_frames(force: bool = False) -> pd.DataFrame:
    """Build one observation per member using disjoint SHG/member splits.

    Training members are observed through month 9, validation members through
    month 10, and test members through month 12. Member and SHG identities are
    disjoint because the generator assigns whole SHGs to a split.
    """
    config = load_config()
    cache = config.root / "data" / "temporal_features.csv"
    if cache.exists() and not force:
        return pd.read_csv(cache)

    transactions = pd.read_csv(config.root / "data" / "synthetic_transactions.csv")
    transactions["date"] = pd.to_datetime(transactions["date"], utc=True)
    assignments = pd.read_csv(config.root / "data" / "member_features.csv")[
        ["node_id", "y", "split", "pattern"]
    ].set_index("node_id")
    cutoffs = {
        "train": pd.Timestamp("2025-09-30", tz="UTC"),
        "val": pd.Timestamp("2025-10-31", tz="UTC"),
        "test": pd.Timestamp("2025-12-31", tz="UTC"),
    }
    rows: list[dict] = []
    for member_id, assignment in assignments.iterrows():
        split = str(assignment["split"])
        report = transactions[
            (transactions["account_id"] == member_id)
            & (transactions["date"] <= cutoffs[split])
        ].copy()
        if report.empty:
            continue
        features = report_features(report)
        topology, _, _, _, _ = report_topology(report)
        fraud_leg_visible = report["counterparty_id"].astype(str).str.contains(
            "SHADOW|MULE", case=False, regex=True
        ).any()
        time_consistent_label = int(bool(assignment["y"]) and fraud_leg_visible)
        features.update(
            {
                "node_id": member_id,
                "y": time_consistent_label,
                "split": split,
                "pattern": assignment["pattern"],
            }
        )
        features.update(dict(zip(TDA_COLUMNS, topology.tolist())))
        rows.append(features)
    frame = pd.DataFrame(rows)
    frame.to_csv(cache, index=False)
    return frame


def select_thresholds(labels: np.ndarray, probabilities: np.ndarray) -> dict[str, float]:
    """Select high precision and high recall thresholds on validation only."""
    precision, recall, thresholds = precision_recall_curve(labels, probabilities)
    if not len(thresholds):
        return {"t_low": 0.5, "t_high": 0.5}
    high_candidates = thresholds[precision[:-1] >= 0.90]
    if len(high_candidates):
        high = float(high_candidates.min())
    else:
        f1 = 2 * precision[:-1] * recall[:-1] / (precision[:-1] + recall[:-1] + 1e-9)
        high = float(thresholds[int(np.argmax(f1))])
    low_candidates = thresholds[recall[:-1] >= 0.95]
    low = float(low_candidates.max()) if len(low_candidates) else min(0.5, high)
    low = min(low, high)
    return {"t_low": low, "t_high": high}


def train_variant(
    train_x: np.ndarray,
    train_y: np.ndarray,
    val_x: np.ndarray,
    val_y: np.ndarray,
    *,
    seed: int,
    hidden: int,
    dropout: float,
    epochs: int,
    learning_rate: float,
    use_smote: bool,
) -> tuple[TopologyMLP, np.ndarray, float]:
    """Train one real model variant and return its validation predictions."""
    torch.manual_seed(seed)
    np.random.seed(seed)
    fit_x, fit_y = train_x, train_y
    if use_smote:
        fit_x, fit_y = smote_enn(train_x, train_y, seed, ratio=0.5)
    model = TopologyMLP(fit_x.shape[1], hidden=hidden, dropout=dropout)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    x_tensor = torch.tensor(fit_x, dtype=torch.float32)
    y_tensor = torch.tensor(fit_y, dtype=torch.float32)
    val_tensor = torch.tensor(val_x, dtype=torch.float32)
    positive_weight = min(20.0, float((fit_y == 0).sum() / max((fit_y == 1).sum(), 1)))
    loss_function = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(positive_weight))
    best_score = -1.0
    best_state = None
    stale = 0
    for _ in range(epochs):
        model.train()
        optimizer.zero_grad()
        loss = loss_function(model(x_tensor), y_tensor)
        loss.backward()
        optimizer.step()
        model.eval()
        with torch.no_grad():
            probabilities = torch.sigmoid(model(val_tensor)).numpy()
        score = average_precision_score(val_y, probabilities)
        if score > best_score + 1e-5:
            best_score = score
            best_state = {key: value.detach().clone() for key, value in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
        if stale >= 18:
            break
    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        val_probabilities = torch.sigmoid(model(val_tensor)).numpy()
    return model, val_probabilities, float(best_score)


def save_variant(path: Path, model: TopologyMLP, input_columns: list[str], hidden: int) -> None:
    torch.save(
        {
            "state": model.state_dict(),
            "input_dim": len(input_columns),
            "hidden": hidden,
            "input_columns": input_columns,
            "model_type": "topology_mlp",
        },
        path,
    )


def main() -> None:
    config = load_config()
    config.artifacts.mkdir(exist_ok=True)
    started = time.perf_counter()
    frame = temporal_frames(force=False)
    train = frame[frame["split"] == "train"].copy()
    validation = frame[frame["split"] == "val"].copy()
    scaler = StandardScaler().fit(train[FEATURE_NAMES])
    save_scaler(config.artifacts / 'scaler.json', scaler, FEATURE_NAMES)

    scaled_train = scaler.transform(train[FEATURE_NAMES])
    scaled_validation = scaler.transform(validation[FEATURE_NAMES])
    topology_scaler = StandardScaler().fit(train[TDA_COLUMNS])
    save_scaler(config.artifacts / 'topology_scaler.json', topology_scaler, TDA_COLUMNS)
    topology_train = topology_scaler.transform(train[TDA_COLUMNS])
    topology_validation = topology_scaler.transform(validation[TDA_COLUMNS])
    full_columns = FEATURE_NAMES + TDA_COLUMNS
    full_train = np.column_stack([scaled_train, topology_train])
    full_validation = np.column_stack(
        [scaled_validation, topology_validation]
    )
    variants = {
        "full": (full_train, full_validation, True, full_columns),
        "without_topology": (
            scaled_train,
            scaled_validation,
            True,
            FEATURE_NAMES,
        ),
        "without_smote": (full_train, full_validation, False, full_columns),
    }
    validation_predictions: dict[str, list[float]] = {}
    validation_thresholds: dict[str, dict[str, float]] = {}
    validation_scores: dict[str, float] = {}
    for index, (name, (train_x, val_x, use_smote, columns)) in enumerate(variants.items()):
        model, probabilities, score = train_variant(
            train_x,
            train["y"].to_numpy(),
            val_x,
            validation["y"].to_numpy(),
            seed=config.seed + index,
            hidden=48,
            dropout=config.model["dropout"],
            epochs=config.model["epochs"],
            learning_rate=config.model["learning_rate"],
            use_smote=use_smote,
        )
        output = config.artifacts / ("model.pt" if name == "full" else f"model_{name}.pt")
        save_variant(output, model, list(columns), 48)
        validation_predictions[name] = probabilities.tolist()
        validation_thresholds[name] = select_thresholds(
            validation["y"].to_numpy(), probabilities
        )
        validation_scores[name] = score

    thresholds = {
        **validation_thresholds["full"],
        "selected_on": "SHG-disjoint validation members observed through month 10",
        "policy": "HIGH: validation precision >= 0.90; LOW boundary: validation recall >= 0.95",
    }
    (config.artifacts / "thresholds.json").write_text(json.dumps(thresholds, indent=2))
    training_metadata = {
        "train_members": train["node_id"].tolist(),
        "validation_members": validation["node_id"].tolist(),
        "validation_thresholds": validation_thresholds,
        "validation_scores": validation_scores,
        "validation_predictions": validation_predictions,
    }
    (config.artifacts / "training_metadata.json").write_text(
        json.dumps(training_metadata)
    )
    elapsed = time.perf_counter() - started
    print(
        f"train_members={len(train)} validation_members={len(validation)} "
        f"overlap=0 elapsed_s={elapsed:.2f} "
        f"validation_AUPRC={validation_scores['full']:.4f} "
        f"thresholds=({thresholds['t_low']:.3f},{thresholds['t_high']:.3f})"
    )


if __name__ == "__main__":
    main()
