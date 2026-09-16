# BANKSY spatial workflow

[![CI](https://github.com/tomasnoli/banksy-spatial-workflow/actions/workflows/ci.yml/badge.svg)](https://github.com/tomasnoli/banksy-spatial-workflow/actions/workflows/ci.yml)

## Overview

A workflow for BANKSY spatial domain analysis in Xenium and Visium datasets.
It reads analysis settings from a configuration file and runs locally or on a
SLURM cluster. Results are saved separately for each sample and lambda value
to avoid overwriting previous outputs.

I developed this workflow for a spatial domain segmentation project. I needed
a reliable pipeline to change parameters, repeat analyses on many samples, and run the same configuration on my workstation and on the HPC cluster.

Important Note! BANKSY performs the spatial clustering. This repo adds:

- configuration files
- local and HPC launchers
- output handling
- tests.

pyBANKSY repository: [here](https://github.com/prabhakarlab/Banksy_py)

## Installation

Python 3.11 is recommended. From the repository root:

```bash
conda env create -f environment.yml
conda activate banksy-spatial-workflow
make test
```

The package installs the `banksy-workflow` command and uses
`pybanksy==1.3.4`. The package versions used for the reference validation
are listed in [`docs/reference_validation.md`](docs/reference_validation.md).

## Test

### Unit tests

Run the unit tests with:

```bash
make test
```

These check the workflow logic without running a full analysis on public data.
They also run through GitHub Actions.

### STARmap reference test

The reference test uses the public STARmap example from the official BANKSY
repository:

```bash
make validate-reference
```

It runs both this workflow and BANKSY's `run_banksy_multiparam` function with
the same cells, parameters, and installed dependencies. It then matches results
by cell ID and compares the clusters using the adjusted Rand index (ARI).

The test passes when both runs assign cells to the same groups (`ARI = 1`).
The numeric cluster labels can differ.

```text
PASS: workflow and upstream entry point yield the same partition
```

The reference data come from a fixed commit of the BANKSY repository and are
verified before use.

See [Reference validation](docs/reference_validation.md) for the parameters,
results, and comparison with the original BANKSY notebook.

## Run

Copy and edit the configuration template: add the input paths, sample names,
and BANKSY parameters

```bash
banksy-workflow check --config config/run_samples.toml
banksy-workflow run --config config/run_samples.toml
```

To submit the same configuration to SLURM, with at most two lambda jobs
running at once:

```bash
hpc/submit_banksy.sh config/hpc_run_samples.toml 2
```

The launcher reads the lambda values from the configuration file and creates
the SLURM array. You do not need to set them again in the shell script.

The [how-to guide](docs/HOWTO.md) covers input requirements, configuration,
sample selection, outputs, and HPC setup.

## Output

Each sample and lambda combination has its own directory, structured as such:

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

Domain columns are named:

```text
banksy_domain_lam{lambda}_res{resolution}
```

`DONE.json` marks a finished sample-lambda directory. Finished directories are
skipped; directories that are incomplete or were computed with different
resolutions stop the run. Use `--force` to delete and recompute them:

```bash
banksy-workflow run --force --config config/run_samples.toml
```
## References

If you use this workflow, please cite this repository and BANKSY's paper:

> Singhal V. et al. BANKSY unifies cell typing and tissue domain segmentation
> for scalable spatial omics data analysis. *Nature Genetics* 56, 431–441
> (2024).
> https://doi.org/10.1038/s41588-024-01664-3

Repository citation details are in [`CITATION.cff`](CITATION.cff).

## License

This project is distributed under the
[GNU General Public License v3.0](LICENSE).

