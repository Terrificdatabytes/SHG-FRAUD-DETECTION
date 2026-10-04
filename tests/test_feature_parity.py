import numpy as np
import pandas as pd

from core.config import load_config
from core.tda import report_topology
from core.train import TDA_COLUMNS, temporal_frames


def test_training_and_serving_topology_use_same_function():
    config = load_config()
    frame = temporal_frames()
    row = frame[frame.split == "test"].iloc[0]
    transactions = pd.read_csv(config.root / "data" / "synthetic_transactions.csv")
    report = transactions[transactions.account_id == row.node_id]
    vector, _, _, _, _ = report_topology(report)
    assert np.allclose(vector, row[TDA_COLUMNS].to_numpy(dtype=float))
