"""Tabular-plus-cycle-topology neural detector.

The production detector is an MLP. It does not claim graph message passing:
transaction relationships are summarized by behavioural and time-expanded
cycle features before classification.
"""
from __future__ import annotations

import torch
from torch import nn


class TopologyMLP(nn.Module):
    """Small CPU-friendly classifier with dropout for uncertainty sampling."""

    def __init__(self, input_dim: int, hidden: int = 48, dropout: float = 0.30):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden, hidden // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden // 2, 1),
        )

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        return self.network(features).squeeze(-1)
