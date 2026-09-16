from pathlib import Path

import pytest

from banksy_workflow.config import domain_key, lambda_tag, load_config, resolution_tag


def write_config(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_load_single_sample_config(tmp_path):
    path = write_config(
        tmp_path / "config.toml",
        """
[data]
input = "input.h5ad"
output = "results"
sample_name = "demo"

[parameters]
lambdas = [0.2, 0.8]
resolutions = [0.1, 0.3]
""",
    )
    config = load_config(path)
    assert config.data.sample_name == "demo"
    assert config.parameters.lambdas == (0.2, 0.8)
    assert config.parameters.seed == 1234


def test_rejects_ambiguous_sample_mode(tmp_path):
    path = write_config(
        tmp_path / "config.toml",
        """
[data]
input = "input.h5ad"
output = "results"
sample_name = "demo"
sample_column = "sample_id"

[parameters]
lambdas = [0.2]
resolutions = [0.1]
""",
    )
    with pytest.raises(ValueError, match="exactly one"):
        load_config(path)


def test_rejects_pca_dimension_scan(tmp_path):
    path = write_config(
        tmp_path / "config.toml",
        """
[data]
input = "input.h5ad"
output = "results"
sample_name = "demo"

[parameters]
lambdas = [0.2]
resolutions = [0.1]
pca_dims = [20, 50]
""",
    )
    with pytest.raises(ValueError, match="exactly one value"):
        load_config(path)


@pytest.mark.parametrize(("value", "expected"), [(0.2, "0.2"), (1.0, "1")])
def test_result_tags(value, expected):
    assert lambda_tag(value) == f"lam{expected}"
    assert resolution_tag(value) == f"res{expected}"


def test_template_is_a_valid_configuration():
    template = Path(__file__).resolve().parent.parent / "config" / "template.toml"
    config = load_config(template)
    assert config.data.sample_name == "sample_01"
    assert config.parameters.lambdas == (0.2, 0.8)


def test_domain_key_uses_result_tags():
    assert domain_key(0.8, 0.2) == "banksy_domain_lam0.8_res0.2"
