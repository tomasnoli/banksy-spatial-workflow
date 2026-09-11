from __future__ import annotations

import gc
import json
import random
import shutil
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from .config import (
    WorkflowConfig,
    domain_key,
    lambda_tag,
    resolution_tag,
    value_tag,
)
from .plotting import save_spatial_domains


def selected_samples(adata, config: WorkflowConfig, requested: list[str] | None):
    data = config.data
    if data.sample_column is None:
        if requested and requested != [data.sample_name]:
            raise ValueError(f"This input contains only sample {data.sample_name!r}")
        return [str(data.sample_name)]
    if data.sample_column not in adata.obs:
        raise ValueError(f"Missing obs column: {data.sample_column}")
    available = set(adata.obs[data.sample_column].astype(str))
    chosen = requested or list(data.samples) or sorted(available)
    missing = sorted(set(chosen) - available)
    if missing:
        raise ValueError(f"Samples not found in AnnData: {missing}")
    return chosen


def output_state(lam_dir: Path, force: bool) -> str:
    """Classify a sample/lambda output directory as "done", "partial" or "new".

    A directory containing DONE.json holds a complete resolution grid and is
    reused. A non-empty directory without DONE.json is a partial result and is
    never reused silently. With ``force`` every directory counts as new and is
    replaced once the new results are ready.
    """
    if force or not lam_dir.exists():
        return "new"
    if (lam_dir / "DONE.json").exists():
        return "done"
    if any(lam_dir.iterdir()):
        return "partial"
    return "new"


def _prepare_sample(adata, config: WorkflowConfig, sample: str):
    import numpy as np

    data = config.data
    if data.sample_column:
        mask = adata.obs[data.sample_column].astype(str) == sample
        sample_data = adata[mask].copy()
    else:
        sample_data = adata.copy()
    if sample_data.n_obs == 0:
        raise ValueError(f"No observations found for sample {sample}")
    if data.spatial_key in sample_data.obsm:
        spatial = np.asarray(sample_data.obsm[data.spatial_key])
    elif data.x_column in sample_data.obs and data.y_column in sample_data.obs:
        spatial = sample_data.obs[[data.x_column, data.y_column]].to_numpy()
    else:
        raise ValueError(
            f"Coordinates not found in obsm[{data.spatial_key!r}] or "
            f"obs columns {data.x_column!r}/{data.y_column!r}"
        )
    if spatial.ndim != 2 or spatial.shape[1] < 2:
        raise ValueError("Spatial coordinates must be a two-dimensional XY matrix")
    sample_data.obs["x"] = spatial[:, 0]
    sample_data.obs["y"] = spatial[:, 1]
    sample_data.obsm["spatial"] = spatial.copy()
    return sample_data


def _labels(row, observation_names):
    import numpy as np
    import pandas as pd

    label_object = row["labels"]
    values = label_object.dense if hasattr(label_object, "dense") else label_object
    series = pd.Series(
        np.asarray(values).flatten().astype("int32"),
        index=row["adata"].obs_names,
    )
    aligned = series.reindex(observation_names)
    if aligned.isna().any():
        raise ValueError(f"Missing BANKSY labels for {int(aligned.isna().sum())} rows")
    return aligned.astype("int32")


def _serializable_config(config: WorkflowConfig, sample: str, lam: float) -> dict:
    payload = asdict(config)
    payload.pop("source")
    payload["data"]["input"] = str(config.data.input)
    payload["data"]["output"] = str(config.data.output)
    payload["selection"] = {"sample": sample, "lambda": lam}
    return payload


def run_workflow(
    config: WorkflowConfig,
    requested_samples: list[str] | None = None,
    requested_lambdas: list[float] | None = None,
    force: bool = False,
) -> None:
    import numpy as np
    import pandas as pd
    import scanpy as sc
    from banksy.cluster_methods import run_Leiden_partition
    from banksy.embed_banksy import generate_banksy_matrix
    from banksy.initialize_banksy import initialize_banksy
    from banksy_utils.umap_pca import pca_umap

    if not config.data.input.is_file():
        raise FileNotFoundError(config.data.input)
    lambdas = requested_lambdas or list(config.parameters.lambdas)
    unknown = [value for value in lambdas if value not in config.parameters.lambdas]
    if unknown:
        raise ValueError(f"Lambda values absent from config: {unknown}")

    print(f"Loading {config.data.input}", flush=True)
    adata = sc.read_h5ad(config.data.input)
    for sample in selected_samples(adata, config, requested_samples):
        sample_data = _prepare_sample(adata, config, sample)
        active_lambdas = []
        for lam in lambdas:
            lam_dir = config.data.output / sample / lambda_tag(lam)
            state = output_state(lam_dir, force)
            if state == "done":
                print(f"Skipping {sample}, lambda={value_tag(lam)} (DONE.json found)")
            elif state == "partial":
                raise FileExistsError(
                    f"Partial output exists at {lam_dir}; inspect it and rerun with "
                    "--force to replace it"
                )
            else:
                active_lambdas.append(lam)
        if not active_lambdas:
            continue

        print(
            f"Running {sample}: {sample_data.n_obs} observations, "
            f"{sample_data.n_vars} genes, lambdas={active_lambdas}",
            flush=True,
        )
        banksy_dict = initialize_banksy(
            sample_data,
            coord_keys=("x", "y", "spatial"),
            num_neighbours=config.parameters.num_neighbours,
            nbr_weight_decay="scaled_gaussian",
            max_m=config.parameters.max_m,
            plt_edge_hist=False,
            plt_nbr_weights=False,
            plt_agf_angles=False,
            plt_theta=False,
        )
        banksy_dict, banksy_matrix = generate_banksy_matrix(
            sample_data, banksy_dict, active_lambdas, config.parameters.max_m
        )
        np.random.seed(config.parameters.seed)
        random.seed(config.parameters.seed)
        pca_umap(
            banksy_dict,
            pca_dims=list(config.parameters.pca_dims),
            add_umap=config.parameters.add_umap,
        )
        del banksy_matrix
        gc.collect()
        results, _ = run_Leiden_partition(
            banksy_dict,
            list(config.parameters.resolutions),
            num_nn=config.parameters.num_nn,
            num_iterations=-1,
            partition_seed=config.parameters.seed,
            match_labels=False,
        )

        for lam in active_lambdas:
            lam_dir = config.data.output / sample / lambda_tag(lam)
            if lam_dir.exists() and force:
                shutil.rmtree(lam_dir)
            (lam_dir / "plots").mkdir(parents=True, exist_ok=True)
            (lam_dir / "tables").mkdir(parents=True, exist_ok=True)
            parameters_file = lam_dir / "run_parameters.json"
            with parameters_file.open("w", encoding="utf-8") as handle:
                json.dump(_serializable_config(config, sample, lam), handle, indent=2)
            shutil.copy2(config.source, lam_dir / "source_config.toml")

        completed: dict[float, set[float]] = {lam: set() for lam in active_lambdas}
        labels_by_lambda: dict[float, dict[str, object]] = {
            lam: {} for lam in active_lambdas
        }
        # pyBANKSY returns one row per (lambda, num_pcs, resolution). Rows are
        # keyed by lambda and resolution only because load_config enforces a
        # single pca_dims value.
        for _, row in results.iterrows():
            lam = float(row["lambda_param"])
            result_resolution = float(row["resolution"])
            matching = [value for value in active_lambdas if np.isclose(value, lam)]
            if len(matching) != 1:
                raise ValueError(f"Unexpected BANKSY lambda in results: {lam}")
            lam = matching[0]
            resolution_matches = [
                value
                for value in config.parameters.resolutions
                if np.isclose(value, result_resolution)
            ]
            if len(resolution_matches) != 1:
                raise ValueError(
                    f"Unexpected BANKSY resolution in results: {result_resolution}"
                )
            res = resolution_matches[0]
            aligned = _labels(row, sample_data.obs_names)
            label_key = domain_key(lam, res)
            labels_by_lambda[lam][label_key] = aligned
            lam_dir = config.data.output / sample / lambda_tag(lam)
            table = pd.DataFrame(
                {"observation_id": sample_data.obs_names, "domain": aligned}
            )
            table.to_csv(
                lam_dir / "tables" / f"domains_{resolution_tag(res)}.tsv.gz",
                sep="\t",
                index=False,
                compression="gzip",
            )
            save_spatial_domains(
                sample_data.obs["x"].to_numpy(),
                sample_data.obs["y"].to_numpy(),
                aligned.to_numpy(),
                lam_dir / "plots" / f"domains_{resolution_tag(res)}.png",
                f"{sample}: BANKSY domains\n"
                f"lambda {value_tag(lam)}, resolution {value_tag(res)}",
                config.parameters.scatter_size,
            )
            completed[lam].add(res)

        expected = set(config.parameters.resolutions)
        for lam in active_lambdas:
            if completed[lam] != expected:
                raise ValueError(
                    f"Incomplete result grid for lambda {lam}: "
                    f"expected {sorted(expected)}, got {sorted(completed[lam])}"
                )
            lam_name = lambda_tag(lam)
            lam_dir = config.data.output / sample / lam_name
            output_data = sample_data.copy()
            for label_key, labels in labels_by_lambda[lam].items():
                output_data.obs[label_key] = pd.Categorical(labels)
            label_columns = list(labels_by_lambda[lam])
            output_data.obs[label_columns].to_csv(
                lam_dir / "domain_labels.tsv.gz", sep="\t", compression="gzip"
            )
            output_data.write_h5ad(lam_dir / f"{sample}_{lam_name}_domains.h5ad")
            checkpoint = {
                "sample": sample,
                "lambda": lam,
                "resolutions": sorted(completed[lam]),
                "completed_at": datetime.now(UTC).isoformat(),
            }
            with (lam_dir / "DONE.json").open("w", encoding="utf-8") as handle:
                json.dump(checkpoint, handle, indent=2)
            del output_data
            gc.collect()
            print(
                f"Completed {sample}, lambda={value_tag(lam)}: {lam_dir}",
                flush=True,
            )
