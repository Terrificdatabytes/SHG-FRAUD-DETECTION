"""Version-independent standardization artifact helpers."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


def save_scaler(path: Path, scaler: StandardScaler, columns: list[str]) -> None:
    path.write_text(
        json.dumps(
            {
                "columns": list(columns),
                "mean": scaler.mean_.tolist(),
                "scale": scaler.scale_.tolist(),
            },
            indent=2,
        )
    )


def transform(frame: pd.DataFrame, artifact: dict) -> np.ndarray:
    values = frame[artifact["columns"]].to_numpy(dtype=float)
    return (values - np.asarray(artifact["mean"])) / np.asarray(artifact["scale"])


def load_scaler(path: Path) -> dict:
    return json.loads(path.read_text())
