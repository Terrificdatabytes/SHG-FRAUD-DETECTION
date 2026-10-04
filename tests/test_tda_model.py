import pandas as pd
import torch

from core.config import load_config
from core.model import TopologyMLP
from core.tda import report_topology


def test_fraud_demo_has_explicit_cycle():
    config = load_config()
    for case in ("Applicant_E", "Applicant_F"):
        report = pd.read_csv(config.root / "demo_cases" / f"{case}.csv")
        vector, cycle, intervals, _, _ = report_topology(report)
        assert vector[1] >= 1
        assert cycle
        assert intervals


def test_mlp_shape():
    model = TopologyMLP(48)
    output = model(torch.randn(5, 48))
    assert output.shape == (5,)
