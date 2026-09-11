# BANKSY spatial workflow

[![CI](https://github.com/tomasnoli/banksy-spatial-workflow/actions/workflows/ci.yml/badge.svg)](https://github.com/tomasnoli/banksy-spatial-workflow/actions/workflows/ci.yml)

A configuration-driven workflow for BANKSY spatial domain analysis in Xenium,
Visium and Visium HD datasets. It separates run parameters from the analysis
code, uses the same configuration locally and on SLURM, and writes isolated
results for each sample and lambda value.

## Why this workflow

I developed this workflow while using BANKSY for spatial transcriptomics
analyses across multiple samples and parameter combinations. The aim was to
replace dataset-specific scripts and hard-coded parameters with a workflow that
could be configured once, reproduced later and run in the same way on a
workstation or HPC cluster.

BANKSY provides the spatial clustering method; this repository handles its
configuration, execution, output organisation and validation.

## Features

* reads prepared AnnData (`.h5ad`) inputs;
* supports one sample per file or multiple samples through an `obs` column;
* accepts spatial coordinates from `obsm` or configurable `obs` columns;
* runs pyBANKSY over a lambda x Leiden-resolution grid;
* aligns domain labels to the original observation identifiers;
* records the configuration and parameters used for every result;
* keeps sample and lambda outputs isolated;
* detects completed runs using `DONE.json` checkpoints;
* provides a SLURM array launcher used on the bwForCluster Helix (Heidelberg);
* includes unit tests and a public-data reference validation.

Input preparation and downstream biological interpretation are intentionally
outside the workflow. The input matrix must already contain the expression
representation intended for BANKSY.

## Installation

Python 3.11 is recommended. From the repository root:

```bash
conda env create -f environment.yml
conda activate banksy-spatial-workflow
make test
```

The package installs the `banksy-workflow` command and pins
`pybanksy==1.3.4`. The complete package set used for the reference validation
is recorded in `uv.lock`; `uv sync --extra dev` recreates it exactly.

## Run an analysis

Copy the appropriate template and edit the input paths, sample selection and
BANKSY parameters:

```bash
cp config/xenium_template.toml config/xenium_local.toml

banksy-workflow check --config config/xenium_local.toml
banksy-workflow run --config config/xenium_local.toml
```

The same configuration can be submitted to SLURM. For example, to allow at
most two lambda jobs to run concurrently:

```bash
hpc/helix/submit_banksy.sh config/xenium_local.toml 2
```

The launcher derives the SLURM array from the lambda values in the
configuration, avoiding a second copy of the analysis parameters in the shell
script.

See the [usage guide](docs/usage.md) for the input contract, configuration
fields, sample selection, output structure and HPC procedure, and the
[design notes](docs/design.md) for the origin of the workflow and the choice
of the SLURM parallelisation unit.

## Output layout

Each sample and lambda combination is written separately:

```text
output/
└── sample/
    └── lam0.8/
        ├── sample_lam0.8_domains.h5ad
        ├── domain_labels.tsv.gz
        ├── run_parameters.json
        ├── source_config.toml
        ├── DONE.json
        ├── plots/
        └── tables/
```

Domain columns use the identifier:

```text
banksy_domain_lam{lambda}_res{resolution}
```

`DONE.json` is written only after all configured resolutions for that sample
and lambda complete successfully.

## Validation

The workflow is tested at two levels.

### Unit tests

Fast tests cover the workflow logic without requiring a complete public-data
analysis:

```bash
make test
```

They are also run through GitHub Actions.

### STARmap reference test

The end-to-end validation uses the public STARmap example from the official
BANKSY repository:

```bash
make validate-reference
```

The test runs this workflow and the upstream `run_banksy_multiparam` entry
point using the same cells, parameters and installed dependencies. Results are
aligned by cell ID and compared using adjusted Rand index (ARI).

A successful validation requires identical partitions between the two entry
points (`ARI = 1`):

```text
PASS: workflow and upstream entry point yield the same partition
```

Reference data are retrieved from a pinned upstream commit and verified before
use. Detailed parameters, results and the comparison with the historical
BANKSY notebook are documented in
[Reference validation](docs/reference_validation.md).

## Scope

This repository focuses on reproducible BANKSY spatial domain analysis. It does
not currently perform:

* platform-specific import or quality control;
* normalization or feature selection;
* automatic selection of lambda and resolution;
* domain annotation or marker discovery;
* condition-level differential expression.

These steps require dataset-specific analytical choices and are kept separate
from the clustering workflow. Replicated condition comparisons, in particular,
should use an appropriate sample-level or pseudobulk design.

## Tools

The workflow is built around:

* [pyBANKSY](https://github.com/prabhakarlab/Banksy_py) for spatially informed clustering;
* AnnData for expression data and metadata;
* PCA and Leiden clustering through the pyBANKSY workflow;
* scikit-learn for validation metrics;
* TOML configuration files for run parameters;
* SLURM arrays for HPC execution;
* pytest and GitHub Actions for automated testing.

## Citation

If you use this workflow, please cite the repository and BANKSY:

> Singhal V. et al. BANKSY unifies cell typing and tissue domain segmentation
> for scalable spatial omics data analysis. *Nature Genetics* 56, 431–441
> (2024).
> https://doi.org/10.1038/s41588-024-01664-3

Citation metadata for this repository are available in
[`CITATION.cff`](CITATION.cff).

## License

This project is distributed under the
[GNU General Public License v3.0](LICENSE).
