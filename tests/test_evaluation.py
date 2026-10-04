import numpy as np

from core.evaluate import recall_at_precision
from core.train import temporal_frames


def test_member_splits_are_disjoint():
    frame = temporal_frames()
    sets = {
        split: set(frame.loc[frame.split == split, "node_id"])
        for split in ("train", "val", "test")
    }
    assert sets["train"].isdisjoint(sets["val"])
    assert sets["train"].isdisjoint(sets["test"])
    assert sets["val"].isdisjoint(sets["test"])


def test_recall_at_unreachable_precision_is_zero():
    labels = np.array([1, 0, 1, 0])
    probabilities = np.array([0.1, 0.9, 0.2, 0.8])
    assert recall_at_precision(labels, probabilities, 0.9) == 0.0
