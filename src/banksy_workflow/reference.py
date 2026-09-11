"""Validation helpers for the public STARmap reference, not Xenium preprocessing."""

from __future__ import annotations


def align_annotations(obs, annotations):
    """Join the pinned manual annotations by cell ID, checking XY coordinates."""
    import numpy as np

    if not obs.index.is_unique or not annotations.index.is_unique:
        raise ValueError("Observation and annotation IDs must be unique")
    if set(obs.index) != set(annotations.index):
        raise ValueError("Reference cell IDs do not match annotation IDs")
    aligned = annotations.reindex(obs.index)
    if aligned["smoothed_manual"].isna().any():
        raise ValueError("Missing manual domain annotations")
    if not np.allclose(obs[["x", "y"]], aligned[["x", "y"]], rtol=1e-6, atol=1e-6):
        raise ValueError("Reference coordinates do not match annotation coordinates")
    return aligned["smoothed_manual"].astype("category")


def score_partitions(truth, workflow, upstream):
    """Check cell membership and compare partitions independently of label numbers."""
    from sklearn.metrics import adjusted_rand_score

    for labels in (truth, workflow, upstream):
        if not labels.index.is_unique or labels.isna().any():
            raise ValueError("Labels must have unique cell IDs and no missing values")
    if set(truth.index) != set(workflow.index) or set(truth.index) != set(
        upstream.index
    ):
        raise ValueError("Clustering results do not contain the same cells")
    workflow = workflow.reindex(truth.index)
    upstream = upstream.reindex(truth.index)
    return {
        "workflow_vs_upstream_ari": adjusted_rand_score(workflow, upstream),
        "workflow_vs_manual_ari": adjusted_rand_score(truth, workflow),
        "upstream_vs_manual_ari": adjusted_rand_score(truth, upstream),
        "workflow_clusters": int(workflow.nunique()),
        "upstream_clusters": int(upstream.nunique()),
    }
