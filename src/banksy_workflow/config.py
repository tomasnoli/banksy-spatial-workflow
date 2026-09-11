from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DataConfig:
    input: Path
    output: Path
    spatial_key: str = "spatial"
    x_column: str = "x"
    y_column: str = "y"
    sample_column: str | None = None
    sample_name: str | None = None
    samples: tuple[str, ...] = ()


@dataclass(frozen=True)
class ParameterConfig:
    lambdas: tuple[float, ...]
    resolutions: tuple[float, ...]
    pca_dims: tuple[int, ...] = (20,)
    num_neighbours: int = 15
    num_nn: int = 50
    max_m: int = 1
    seed: int = 1234
    add_umap: bool = False
    scatter_size: float = 4.0


@dataclass(frozen=True)
class WorkflowConfig:
    data: DataConfig
    parameters: ParameterConfig
    source: Path


def _nonempty_numbers(values: object, name: str, cast: type) -> tuple:
    if not isinstance(values, list) or not values:
        raise ValueError(f"parameters.{name} must be a non-empty list")
    converted = tuple(cast(value) for value in values)
    if len(set(converted)) != len(converted):
        raise ValueError(f"parameters.{name} contains duplicate values")
    return converted


def load_config(path: str | Path) -> WorkflowConfig:
    source = Path(path).expanduser().resolve()
    with source.open("rb") as handle:
        raw = tomllib.load(handle)

    try:
        data_raw = raw["data"]
        params_raw = raw["parameters"]
        input_path = Path(data_raw["input"]).expanduser()
        output_path = Path(data_raw["output"]).expanduser()
    except KeyError as error:
        raise ValueError(f"Missing configuration field: {error.args[0]}") from error

    sample_column = data_raw.get("sample_column")
    sample_name = data_raw.get("sample_name")
    samples = tuple(str(value) for value in data_raw.get("samples", []))
    if bool(sample_column) == bool(sample_name):
        raise ValueError("Set exactly one of data.sample_column or data.sample_name")
    if samples and not sample_column:
        raise ValueError("data.samples requires data.sample_column")

    lambdas = _nonempty_numbers(params_raw.get("lambdas"), "lambdas", float)
    resolutions = _nonempty_numbers(params_raw.get("resolutions"), "resolutions", float)
    pca_dims = _nonempty_numbers(params_raw.get("pca_dims", [20]), "pca_dims", int)
    if len(pca_dims) != 1:
        raise ValueError(
            "parameters.pca_dims must contain exactly one value; results are "
            "keyed by lambda and resolution, so a PCA-dimension scan would "
            "overwrite its own outputs"
        )
    if any(value < 0 or value > 1 for value in lambdas):
        raise ValueError("BANKSY lambda values must be between 0 and 1")
    if any(value <= 0 for value in resolutions):
        raise ValueError("Leiden resolutions must be positive")
    if any(value <= 0 for value in pca_dims):
        raise ValueError("PCA dimensions must be positive")

    data = DataConfig(
        input=input_path,
        output=output_path,
        spatial_key=str(data_raw.get("spatial_key", "spatial")),
        x_column=str(data_raw.get("x_column", "x")),
        y_column=str(data_raw.get("y_column", "y")),
        sample_column=str(sample_column) if sample_column else None,
        sample_name=str(sample_name) if sample_name else None,
        samples=samples,
    )
    parameters = ParameterConfig(
        lambdas=lambdas,
        resolutions=resolutions,
        pca_dims=pca_dims,
        num_neighbours=int(params_raw.get("num_neighbours", 15)),
        num_nn=int(params_raw.get("num_nn", 50)),
        max_m=int(params_raw.get("max_m", 1)),
        seed=int(params_raw.get("seed", 1234)),
        add_umap=bool(params_raw.get("add_umap", False)),
        scatter_size=float(params_raw.get("scatter_size", 4.0)),
    )
    for name in ("num_neighbours", "num_nn", "max_m"):
        if getattr(parameters, name) <= 0:
            raise ValueError(f"parameters.{name} must be positive")
    if parameters.scatter_size <= 0:
        raise ValueError("parameters.scatter_size must be positive")
    return WorkflowConfig(data=data, parameters=parameters, source=source)


def value_tag(value: float) -> str:
    return f"{float(value):g}"


def lambda_tag(value: float) -> str:
    return f"lam{value_tag(value)}"


def resolution_tag(value: float) -> str:
    return f"res{value_tag(value)}"


def domain_key(lambda_value: float, resolution: float) -> str:
    return f"banksy_domain_{lambda_tag(lambda_value)}_{resolution_tag(resolution)}"
