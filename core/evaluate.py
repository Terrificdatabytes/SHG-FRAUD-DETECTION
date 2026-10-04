"""Held-out evaluation with per-model validation thresholds and real ablations."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import torch
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

from .config import load_config
from .features import FEATURE_NAMES
from .model import TopologyMLP
from .scaling import load_scaler, transform
from .train import TDA_COLUMNS, select_thresholds, temporal_frames


def recall_at_precision(labels: np.ndarray, probabilities: np.ndarray, target: float = 0.9) -> float:
    """Highest non-zero recall at the requested precision, or zero if unreachable."""
    precision, recall, _ = precision_recall_curve(labels, probabilities)
    feasible = recall[(precision >= target) & (recall > 0)]
    return float(feasible.max()) if len(feasible) else 0.0


def metrics(labels: np.ndarray, probabilities: np.ndarray, threshold: float) -> dict:
    predictions = probabilities >= threshold
    tn, fp, fn, tp = confusion_matrix(labels, predictions, labels=[0, 1]).ravel()
    return {
        "threshold": float(threshold),
        "auc": float(roc_auc_score(labels, probabilities)),
        "auprc": float(average_precision_score(labels, probabilities)),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "recall_at_precision_0.9": recall_at_precision(labels, probabilities),
        "fpr": float(fp / max(fp + tn, 1)),
        "brier": float(brier_score_loss(labels, probabilities)),
    }


def load_neural(path, values: np.ndarray) -> np.ndarray:
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    model = TopologyMLP(checkpoint["input_dim"], hidden=checkpoint["hidden"])
    model.load_state_dict(checkpoint["state"])
    model.eval()
    with torch.no_grad():
        return torch.sigmoid(model(torch.tensor(values, dtype=torch.float32))).numpy()


def main() -> None:
    config = load_config()
    frame = temporal_frames()
    train = frame[frame["split"] == "train"].copy()
    validation = frame[frame["split"] == "val"].copy()
    test = frame[frame["split"] == "test"].copy()
    scaler = load_scaler(config.artifacts / "scaler.json")
    topology_scaler = load_scaler(config.artifacts / "topology_scaler.json")
    scaled_train = transform(train, scaler)
    scaled_validation = transform(validation, scaler)
    scaled_test = transform(test, scaler)
    full_train = np.column_stack([scaled_train, transform(train, topology_scaler)])
    full_validation = np.column_stack([scaled_validation, transform(validation, topology_scaler)])
    full_test = np.column_stack([scaled_test, transform(test, topology_scaler)])

    probability_sets: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    logistic = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=config.seed)
    logistic.fit(scaled_train, train["y"])
    probability_sets["Logistic Regression"] = (
        logistic.predict_proba(scaled_validation)[:, 1],
        logistic.predict_proba(scaled_test)[:, 1],
    )
    boosting = GradientBoostingClassifier(random_state=config.seed)
    boosting.fit(scaled_train, train["y"])
    probability_sets["Gradient Boosting"] = (
        boosting.predict_proba(scaled_validation)[:, 1],
        boosting.predict_proba(scaled_test)[:, 1],
    )
    probability_sets["pass72 rule"] = (
        validation["pass72"].to_numpy(),
        test["pass72"].to_numpy(),
    )
    probability_sets["MLP without topology"] = (
        load_neural(config.artifacts / "model_without_topology.pt", scaled_validation),
        load_neural(config.artifacts / "model_without_topology.pt", scaled_test),
    )
    probability_sets["MLP without feature-space SMOTE"] = (
        load_neural(config.artifacts / "model_without_smote.pt", full_validation),
        load_neural(config.artifacts / "model_without_smote.pt", full_test),
    )
    probability_sets["Topology MLP"] = (
        load_neural(config.artifacts / "model.pt", full_validation),
        load_neural(config.artifacts / "model.pt", full_test),
    )

    model_results = {}
    thresholds = {}
    for name, (validation_probabilities, test_probabilities) in probability_sets.items():
        selected = select_thresholds(validation["y"].to_numpy(), validation_probabilities)
        threshold = 0.5 if name == "pass72 rule" else selected["t_high"]
        thresholds[name] = {**selected, "evaluation_threshold": threshold}
        model_results[name] = metrics(test["y"].to_numpy(), test_probabilities, threshold)

    full_test_probabilities = probability_sets["Topology MLP"][1]
    rng = np.random.default_rng(config.seed)
    positive_indices = np.where(test["y"].to_numpy() == 1)[0]
    negative_indices = np.where(test["y"].to_numpy() == 0)[0]
    positive_count = min(len(positive_indices), 30)
    negative_count = positive_count * 49
    rare_scores = []
    for _ in range(200):
        sampled_positive = rng.choice(positive_indices, positive_count, replace=True)
        sampled_negative = rng.choice(negative_indices, negative_count, replace=True)
        indices = np.concatenate([sampled_positive, sampled_negative])
        rare_scores.append(
            average_precision_score(
                test["y"].to_numpy()[indices], full_test_probabilities[indices]
            )
        )
    simulated_prevalence = positive_count / (positive_count + negative_count)
    fpr, tpr, _ = roc_curve(test["y"], full_test_probabilities)
    precision, recall, _ = precision_recall_curve(test["y"], full_test_probabilities)
    full_threshold = thresholds["Topology MLP"]["evaluation_threshold"]
    output = {
        "synthetic_benchmark": True,
        "split": (
            "SHG-disjoint split: train members observed through month 9, "
            "validation members through month 10, test members through month 12"
        ),
        "overlap": {"train_validation": 0, "train_test": 0, "validation_test": 0},
        "models": model_results,
        "validation_thresholds": thresholds,
        "rare_prevalence_simulation": {
            "prevalence": simulated_prevalence,
            "positives_per_repeat": positive_count,
            "negatives_per_repeat": negative_count,
            "auprc_mean": float(np.mean(rare_scores)),
            "auprc_sd": float(np.std(rare_scores)),
            "bootstrap_repeats": 200,
        },
        "curves": {
            "roc": {"x": fpr.tolist(), "y": tpr.tolist()},
            "pr": {"x": recall.tolist(), "y": precision.tolist()},
        },
        "confusion_matrix": confusion_matrix(
            test["y"], full_test_probabilities >= full_threshold, labels=[0, 1]
        ).tolist(),
        "test_n": len(test),
        "test_positives": int(test["y"].sum()),
    }
    (config.artifacts / "metrics.json").write_text(json.dumps(output, indent=2))
    print(
        json.dumps(
            {
                "test_n": len(test),
                "test_positives": int(test["y"].sum()),
                "member_overlap": 0,
                "topology_mlp": model_results["Topology MLP"],
                "best_auprc_model": max(
                    model_results, key=lambda name: model_results[name]["auprc"]
                ),
                "rare_prevalence_simulation": output["rare_prevalence_simulation"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
