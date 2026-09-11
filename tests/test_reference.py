import pandas as pd
import pytest

from banksy_workflow.reference import align_annotations, score_partitions


def test_annotations_follow_cell_ids_not_csv_row_order():
    obs = pd.DataFrame({"x": [1, 2], "y": [3, 4]}, index=["a", "b"])
    annotations = pd.DataFrame(
        {"x": [2, 1], "y": [4, 3], "smoothed_manual": ["L4", "L6"]},
        index=["b", "a"],
    )
    assert align_annotations(obs, annotations).tolist() == ["L6", "L4"]


def test_rejects_annotations_with_wrong_coordinates():
    obs = pd.DataFrame({"x": [1], "y": [3]}, index=["a"])
    annotations = pd.DataFrame(
        {"x": [2], "y": [3], "smoothed_manual": ["L6"]}, index=["a"]
    )
    with pytest.raises(ValueError, match="coordinates"):
        align_annotations(obs, annotations)


def test_rejects_reference_annotation_cell_mismatch():
    obs = pd.DataFrame(index=["a"])
    annotations = pd.DataFrame(index=["b"])
    with pytest.raises(ValueError, match="IDs"):
        align_annotations(obs, annotations)


def test_scores_ignore_cluster_numbers_and_row_order():
    truth = pd.Series(["L6", "L6", "L4", "L4"], index=list("abcd"))
    workflow = pd.Series([0, 0, 1, 1], index=list("abcd"))
    upstream = pd.Series([5, 5, 9, 9], index=list("cdab"))
    scores = score_partitions(truth, workflow, upstream)
    assert scores["workflow_vs_upstream_ari"] == 1.0
    assert scores["workflow_vs_manual_ari"] == 1.0


def test_detects_different_partitions():
    truth = pd.Series([0, 0, 1, 1], index=list("abcd"))
    upstream = pd.Series([0, 1, 0, 1], index=list("abcd"))
    assert score_partitions(truth, truth, upstream)["workflow_vs_upstream_ari"] < 1


def test_scores_reject_missing_cells():
    truth = pd.Series([0, 1], index=["a", "b"])
    with pytest.raises(ValueError, match="same cells"):
        score_partitions(truth, truth.iloc[:1], truth)
