"""Run the STARmap reference validation against the upstream entry point."""

from __future__ import annotations

import json
import platform
import random
from dataclasses import asdict, replace
from importlib.metadata import version
from pathlib import Path
from tempfile import mkdtemp

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scanpy as sc
from banksy.initialize_banksy import initialize_banksy
from banksy.run_banksy import run_banksy_multiparam
from banksy_utils.color_lists import spagcn_color
from banksy_utils.refine_clusters import refine_once
from download_starmap_reference import (
    ANNOTATIONS,
    ANNOTATIONS_SHA1,
    GIT_BLOB_SHA1,
    OUTPUT,
    UPSTREAM_COMMIT,
    URL,
    download_verified,
)

from banksy_workflow.config import domain_key, lambda_tag, load_config
from banksy_workflow.core import run_workflow
from banksy_workflow.plotting import save_spatial_domains
from banksy_workflow.reference import align_annotations, score_partitions

CONFIG = Path("config/starmap_reference.toml")
VERSIONED_PACKAGES = (
    "pybanksy",
    "scanpy",
    "anndata",
    "numpy",
    "scipy",
    "scikit-learn",
    "python-igraph",
    "leidenalg",
)


def prepare_input(config):
    download_verified(URL, OUTPUT, GIT_BLOB_SHA1)
    annotation_path = OUTPUT.parent / ANNOTATIONS
    download_verified(
        URL.rsplit("/", 1)[0] + "/" + ANNOTATIONS, annotation_path, ANNOTATIONS_SHA1
    )
    original = sc.read_h5ad(OUTPUT)
    adata = original[original.obs["cluster_name"].notna()].copy()
    adata.var_names_make_unique()
    if adata.shape != (1207, 1020):
        raise ValueError(f"Unexpected reference shape: {adata.shape}")
    annotations = pd.read_csv(annotation_path, index_col=0)
    annotations.index = annotations.index.astype(str)
    adata.obs["manual_annotations"] = align_annotations(adata.obs, annotations)
    adata.obsm["spatial"] = adata.obs[["x", "y"]].to_numpy()
    # X is already preprocessed in the upstream file; do not normalize it again.
    config.data.input.parent.mkdir(parents=True, exist_ok=True)
    adata.write_h5ad(config.data.input)
    return adata


def main():
    config = load_config(CONFIG)
    parameters = config.parameters
    if len(parameters.lambdas) != 1 or len(parameters.resolutions) != 1:
        raise ValueError(
            "STARmap reference validation requires one lambda and resolution"
        )
    if parameters.num_nn != 50:
        raise ValueError("The upstream entry point fixes num_nn at 50")
    lambda_value = parameters.lambdas[0]
    resolution = parameters.resolutions[0]

    adata = prepare_input(config)
    # Each validation run gets a new directory, bypassing old DONE checkpoints.
    root = config.data.output.parent
    root.mkdir(parents=True, exist_ok=True)
    run_dir = Path(mkdtemp(prefix="run-", dir=root))
    config = replace(config, data=replace(config.data, output=run_dir / "workflow"))
    run_workflow(config)
    label_key = domain_key(lambda_value, resolution)
    lam_name = lambda_tag(lambda_value)
    workflow_file = (
        config.data.output
        / "starmap_BY3_1k"
        / lam_name
        / f"starmap_BY3_1k_{lam_name}_domains.h5ad"
    )
    workflow = sc.read_h5ad(workflow_file).obs[label_key]
    plt.close("all")

    # Call the upstream high-level entry point independently on a fresh input.
    upstream_input = sc.read_h5ad(config.data.input)
    np.random.seed(parameters.seed)
    random.seed(parameters.seed)
    banksy_dict = initialize_banksy(
        upstream_input,
        ("x", "y", "spatial"),
        parameters.num_neighbours,
        nbr_weight_decay="scaled_gaussian",
        max_m=parameters.max_m,
        plt_edge_hist=False,
        plt_nbr_weights=False,
        plt_agf_angles=False,
        plt_theta=False,
    )
    results = run_banksy_multiparam(
        upstream_input,
        banksy_dict,
        list(parameters.lambdas),
        list(parameters.resolutions),
        color_list=spagcn_color,
        max_m=parameters.max_m,
        filepath=str(run_dir / "upstream"),
        key=("x", "y", "spatial"),
        pca_dims=list(parameters.pca_dims),
        annotation_key="manual_annotations",
        max_labels=int(adata.obs["manual_annotations"].nunique()),
        cluster_algorithm="leiden",
        partition_seed=parameters.seed,
        match_labels=False,
        savefig=True,
        add_nonspatial=False,
        variance_balance=False,
    )
    if len(results) != 1:
        raise ValueError(f"Expected one upstream result, got {len(results)}")
    row = results.iloc[0]
    upstream = pd.Series(row["labels"].dense, index=row["adata"].obs_names)
    truth = adata.obs["manual_annotations"]
    scores = score_partitions(truth, workflow, upstream)

    # Use the authors' refinement primitive, preserving both sets of labels.
    upstream = upstream.reindex(adata.obs_names)
    refined, refined_ari, _ = refine_once(
        adata,
        upstream.to_numpy().copy(),
        truth.cat.codes.tolist(),
        ("x", "y", "spatial"),
        num_neigh=6,
    )
    pd.DataFrame(
        {
            "manual": truth,
            "workflow": workflow.reindex(truth.index),
            "upstream": upstream,
            "upstream_refined": refined,
        }
    ).to_csv(run_dir / "comparison_labels.tsv", sep="\t", index_label="cell_id")
    scores["upstream_refined_vs_manual_ari"] = float(refined_ari)
    scores["refinement_changed_cells"] = int(np.count_nonzero(refined != upstream))
    plt.close("all")
    for name, labels in [
        ("manual", truth),
        ("upstream", upstream),
        ("workflow", workflow.reindex(truth.index)),
        ("upstream_refined", refined),
    ]:
        save_spatial_domains(
            adata.obs.x,
            adata.obs.y,
            np.asarray(labels),
            run_dir / f"{name}.png",
            f"STARmap: {name}",
            12,
        )
    report = {
        "scores": scores,
        "shape": list(adata.shape),
        "parameters": asdict(config.parameters),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "upstream_commit": UPSTREAM_COMMIT,
        "notebook": f"https://github.com/prabhakarlab/Banksy_py/blob/{UPSTREAM_COMMIT}"
        "/starmap_analysis.ipynb",
        "input_git_blob_sha1": GIT_BLOB_SHA1,
        "annotations_git_blob_sha1": ANNOTATIONS_SHA1,
        "historical_notebook": {
            "clusters": 7,
            "ari_rounded": 0.71,
            "refined_ari_rounded": 0.72,
        },
        "versions": {package: version(package) for package in VERSIONED_PACKAGES},
        "equivalent_partitions": bool(
            np.isclose(scores["workflow_vs_upstream_ari"], 1.0, rtol=0, atol=1e-12)
        ),
    }
    (run_dir / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(scores, indent=2))
    print(f"Reference comparison saved to: {run_dir}")
    if not report["equivalent_partitions"]:
        raise SystemExit(
            "FAIL: workflow and upstream entry point disagree; inspect report"
        )
    print("PASS: workflow and upstream entry point yield the same partition")


if __name__ == "__main__":
    main()
