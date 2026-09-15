# How to use

## 1. Install

Clone the repository, enter its root directory and create the environment:

```bash
git clone https://github.com/tomasnoli/banksy-spatial-workflow.git
cd banksy-spatial-workflow
conda env create -f environment.yml
conda activate banksy-spatial-workflow
make test
```

make sure to use the correct syntax if you use other package managers.

Run commands from the repository root when a configuration contains relative
paths. Existing environments can be updated with:

```bash
conda env update -f environment.yml --prune
```

## 2. Prepare the AnnData

The script expects a prepared `.h5ad` file with:

- unique observation names;
- the expression representation intended for BANKSY in `X`;
- two-dimensional spatial coordinates;
- a sample column in `obs` when several samples share one file.

Coordinates are read first from `obsm[spatial_key]`. If that key is absent,
the workflow falls back to the configured `x_column` and `y_column` in `obs`.
The first two coordinate columns are used as X and Y.

Annotated objects often keep the representation intended for BANKSY in a
layer while `X` holds scaled values. Build a prepared input from that layer
without loading the whole file:

```python
import anndata as ad
import h5py
import numpy as np
from anndata.io import read_elem

with h5py.File("annotated.h5ad") as f:
    X = read_elem(f["layers/normalised"])
    obs = read_elem(f["obs"])[["sample_id"]]
    var = read_elem(f["var"])[[]]
    spatial = read_elem(f["obsm/spatial"])

prepared = ad.AnnData(X=X, obs=obs, var=var)
prepared.obsm["spatial"] = np.asarray(spatial)
prepared.write_h5ad("prepared_input.h5ad")
```

Keeping only the columns the workflow needs makes the input smaller and
faster to load; the workflow copies `obs` into every result file.

## 3. Setup the config files

Start from one of the templates:

```bash
cp config/xenium_template.toml config/xenium_local.toml
cp config/visium_template.toml config/visium_local.toml
```
The `[data]` section describes the input in one of two ways: a single sample
(`sample_name`) or several samples identified by an `obs` column
(`sample_column`). Set one of the two, not both.

### One sample config

```toml
[data]
input = "/path/to/prepared_input.h5ad"
output = "/path/to/banksy_results"
sample_name = "sample_01"
spatial_key = "spatial"
```

### Multiple samples config

```toml
[data]
input = "/path/to/prepared_input.h5ad"
output = "/path/to/banksy_results"
sample_column = "sample_id"
samples = ["sample_01", "sample_02"]
spatial_key = "spatial"
```

Omit `samples` to process every value found in `sample_column`.

### BANKSY parameters

```toml
[parameters]
lambdas = [0.2, 0.8]
resolutions = [0.1, 0.2, 0.3]
pca_dims = [20]
num_neighbours = 15
num_nn = 50
max_m = 1
seed = 1234
add_umap = false
scatter_size = 4.0
```

| Field | Meaning |
|---|---|
| `lambdas` | Neighbourhood contribution values between 0 and 1 |
| `resolutions` | Positive Leiden resolution values |
| `pca_dims` | Number of principal components; exactly one value |
| `num_neighbours` | Neighbours in the spatial graph |
| `num_nn` | Neighbours in the clustering graph |
| `max_m` | Highest azimuthal transform order |
| `seed` | Python, NumPy and Leiden random seed |
| `add_umap` | Whether BANKSY produce a UMAP |
| `scatter_size` | Point size in spatial plots |

## 4. Check and run

Check syntax and paths, and list the samples that will be processed with
their sizes:

```bash
banksy-workflow check --config config/xenium_local.toml
```

Run the complete configured grid:

```bash
banksy-workflow run --config config/xenium_local.toml
```

You can select one or more samples at the command line:

```bash
banksy-workflow run \
  --config config/xenium_local.toml \
  --sample sample_01 \
  --sample sample_02
```

You can also select one or more configured lambda values:

```bash
banksy-workflow run \
  --config config/xenium_local.toml \
  --lambda 0.8
```

## 5. Resume or replace results

In order to avoid overwriting completed runs, each directory is treated as a single unit.
A `DONE.json` is produced for each sample directory:

- If a directory contains `DONE.json` is skipped when it covers every
  configured resolution.
- A non-empty directory without `DONE.json` is treated as a partial result and
  stops the run.

 Regardless of the .json file, you can still force the run with `--force` :
 
```bash
banksy-workflow run --config config/xenium_local.toml --force
```

This will delete output from previous runs; review 
the specified paths before using `--force`.

## 6. Output

Each sample-lambda directory contains:

```text
sample/lam0.8/
├── sample_lam0.8_domains.h5ad
├── domain_labels.tsv.gz
├── run_parameters.json
├── source_config.toml
├── DONE.json
├── plots/domains_res0.2.png
└── tables/domains_res0.2.tsv.gz
```

- The AnnData file contains one categorical `obs` column per resolution.
- `domain_labels.tsv.gz` collects all domain columns.
- Each file under `tables/` contains observation ID and domain for one
  resolution.
- `run_parameters.json` records the effective parameters, the selection and
  the versions of the packages that produced the result.
- `source_config.toml` preserves the source configuration.
- `DONE.json` confirms that the resolution grid has been completed.

## 7. HPC run

Create the environment once on the login node and activate it before
submission:

```bash
module load *module name*
conda activate banksy-spatial-workflow
hpc/submit_banksy.sh config/xenium_local.toml 2
```

The final argument limits the number of lambda tasks running concurrently. The
launcher creates one SLURM array task per configured lambda; each task processes
its selected samples sequentially. Absolute input and output paths are recommended on the cluster. 
Job logs are written under `logs/` .

The current setting requests 16 CPUs, 128 GB RAM and 12 hours. You can change these values
in `hpc/banksy_array.slurm` according to the dataset and cluster policy.
