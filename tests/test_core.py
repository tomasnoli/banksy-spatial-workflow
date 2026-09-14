import anndata as ad
import numpy as np
import pytest

from banksy_workflow.config import DataConfig, ParameterConfig, WorkflowConfig
from banksy_workflow.core import (
    _prepare_sample,
    _serializable_config,
    output_state,
    package_versions,
    sample_sizes,
    selected_samples,
)


def make_config(tmp_path, **data_fields):
    data = DataConfig(
        input=tmp_path / "in.h5ad", output=tmp_path / "out", **data_fields
    )
    parameters = ParameterConfig(lambdas=(0.8,), resolutions=(0.2,))
    return WorkflowConfig(data=data, parameters=parameters, source=tmp_path / "c.toml")


def make_adata(sample_ids=("s1", "s1", "s2"), coordinates="obsm"):
    n = len(sample_ids)
    adata = ad.AnnData(X=np.zeros((n, 2), dtype="float32"))
    adata.obs_names = [f"cell_{i}" for i in range(n)]
    adata.obs["sample_id"] = list(sample_ids)
    coords = np.arange(2 * n, dtype="float64").reshape(n, 2)
    if coordinates == "obsm":
        adata.obsm["spatial"] = coords
    elif coordinates == "obs":
        adata.obs["cx"] = coords[:, 0]
        adata.obs["cy"] = coords[:, 1]
    return adata


# --- output_state -----------------------------------------------------------


def test_missing_directory_is_new(tmp_path):
    assert output_state(tmp_path / "lam0.8", force=False) == "new"


def test_empty_directory_is_new(tmp_path):
    (tmp_path / "lam0.8").mkdir()
    assert output_state(tmp_path / "lam0.8", force=False) == "new"


def test_done_marker_means_done(tmp_path):
    lam_dir = tmp_path / "lam0.8"
    lam_dir.mkdir()
    (lam_dir / "DONE.json").write_text("{}")
    assert output_state(lam_dir, force=False) == "done"


def test_files_without_done_marker_are_partial(tmp_path):
    lam_dir = tmp_path / "lam0.8"
    (lam_dir / "tables").mkdir(parents=True)
    assert output_state(lam_dir, force=False) == "partial"


@pytest.mark.parametrize("marker", ["DONE.json", "run_parameters.json"])
def test_force_treats_any_directory_as_new(tmp_path, marker):
    lam_dir = tmp_path / "lam0.8"
    lam_dir.mkdir()
    (lam_dir / marker).write_text("{}")
    assert output_state(lam_dir, force=True) == "new"


# --- selected_samples -------------------------------------------------------


def test_single_sample_mode_returns_configured_name(tmp_path):
    config = make_config(tmp_path, sample_name="only")
    assert selected_samples(make_adata(), config, requested=None) == ["only"]


def test_single_sample_mode_rejects_other_requests(tmp_path):
    config = make_config(tmp_path, sample_name="only")
    with pytest.raises(ValueError, match="only sample"):
        selected_samples(make_adata(), config, requested=["s1"])


def test_multi_sample_mode_defaults_to_all_samples_sorted(tmp_path):
    config = make_config(tmp_path, sample_column="sample_id")
    adata = make_adata(sample_ids=("b", "a", "b"))
    assert selected_samples(adata, config, requested=None) == ["a", "b"]


def test_configured_samples_are_used_when_nothing_is_requested(tmp_path):
    config = make_config(tmp_path, sample_column="sample_id", samples=("s2",))
    assert selected_samples(make_adata(), config, requested=None) == ["s2"]


def test_requested_samples_override_configuration(tmp_path):
    config = make_config(tmp_path, sample_column="sample_id", samples=("s2",))
    assert selected_samples(make_adata(), config, requested=["s1"]) == ["s1"]


def test_unknown_sample_is_reported(tmp_path):
    config = make_config(tmp_path, sample_column="sample_id")
    with pytest.raises(ValueError, match=r"not found.*\['s9'\]"):
        selected_samples(make_adata(), config, requested=["s9"])


def test_missing_sample_column_is_reported(tmp_path):
    config = make_config(tmp_path, sample_column="batch")
    with pytest.raises(ValueError, match="Missing obs column: batch"):
        selected_samples(make_adata(), config, requested=None)


def test_sample_sizes_follow_selection(tmp_path):
    config = make_config(tmp_path, sample_column="sample_id", samples=("s2", "s1"))
    assert sample_sizes(make_adata(), config) == {"s2": 1, "s1": 2}


def test_sample_sizes_single_sample_mode(tmp_path):
    config = make_config(tmp_path, sample_name="only")
    assert sample_sizes(make_adata(), config) == {"only": 3}


# --- provenance -------------------------------------------------------------


def test_package_versions_report_missing_packages_as_none():
    versions = package_versions(("numpy", "no-such-package-xyz"))
    assert versions["numpy"]
    assert versions["no-such-package-xyz"] is None


def test_run_parameters_include_versions_and_selection(tmp_path):
    config = make_config(tmp_path, sample_name="only")
    payload = _serializable_config(config, "only", 0.8)
    assert payload["selection"] == {"sample": "only", "lambda": 0.8}
    assert payload["versions"]["numpy"]
    assert "source" not in payload


# --- _prepare_sample --------------------------------------------------------


def test_prepare_sample_subsets_by_sample_and_copies_obsm_coordinates(tmp_path):
    config = make_config(tmp_path, sample_column="sample_id")
    sample_data = _prepare_sample(make_adata(), config, "s1")
    assert sample_data.obs_names.tolist() == ["cell_0", "cell_1"]
    assert sample_data.obs["x"].tolist() == [0.0, 2.0]
    assert sample_data.obs["y"].tolist() == [1.0, 3.0]
    np.testing.assert_array_equal(sample_data.obsm["spatial"], [[0, 1], [2, 3]])


def test_prepare_sample_falls_back_to_obs_columns(tmp_path):
    config = make_config(tmp_path, sample_name="only", x_column="cx", y_column="cy")
    sample_data = _prepare_sample(make_adata(coordinates="obs"), config, "only")
    assert sample_data.n_obs == 3
    assert sample_data.obs["x"].tolist() == [0.0, 2.0, 4.0]
    assert "spatial" in sample_data.obsm


def test_prepare_sample_without_coordinates_fails(tmp_path):
    config = make_config(tmp_path, sample_name="only")
    with pytest.raises(ValueError, match="Coordinates not found"):
        _prepare_sample(make_adata(coordinates=None), config, "only")
