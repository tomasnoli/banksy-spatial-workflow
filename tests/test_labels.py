import numpy as np
import pandas as pd
import pytest

from banksy_workflow.core import _labels


class FakeAnnData:
    def __init__(self, names):
        self.obs_names = pd.Index(names)


def test_labels_are_aligned_by_identifier():
    row = {
        "labels": np.array([7, 3]),
        "adata": FakeAnnData(["cell_b", "cell_a"]),
    }
    aligned = _labels(row, pd.Index(["cell_a", "cell_b"]))
    assert aligned.tolist() == [3, 7]


def test_labels_fail_when_an_identifier_is_missing():
    row = {"labels": np.array([7]), "adata": FakeAnnData(["cell_b"])}
    with pytest.raises(ValueError, match="Missing BANKSY labels"):
        _labels(row, pd.Index(["cell_a", "cell_b"]))
