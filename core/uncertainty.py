"""Dropout uncertainty estimates for the topology MLP."""
from __future__ import annotations

import numpy as np
import torch


def mc_predict(
    model: torch.nn.Module,
    features: torch.Tensor,
    samples: int = 30,
    history_months: float | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    model.train()
    predictions = []
    with torch.no_grad():
        for _ in range(samples):
            predictions.append(torch.sigmoid(model(features)).cpu().numpy())
    draws = np.asarray(predictions)
    mean = draws.mean(axis=0)
    low = np.quantile(draws, 0.05, axis=0)
    high = np.quantile(draws, 0.95, axis=0)
    if history_months is not None:
        widening = 1 + 0.5 * max(0.0, (3 - history_months) / 3)
        half_width = (high - low) * widening / 2
        low = np.clip(mean - half_width, 0, 1)
        high = np.clip(mean + half_width, 0, 1)
    return mean, low, high, draws
