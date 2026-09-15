# STARmap reference validation

The reference validation checks that the repository's execution path produces
the same partition as pyBANKSY's upstream `run_banksy_multiparam` entry point
in the same software environment.

## Reference data

The input and manual annotations come from a fixed BANKSY repository commit:

- commit: `9278996c39e376277d57ef95278000447ba6c57c`;
- input: `starmap_BY3_1k.h5ad`;
- annotations: `Starmap_BY3_1k_meta_annotated_18oct22.csv`.

Both downloads are verified using their Git blob SHA-1. A cached file is reused
only if its checksum matches.

The preparation step retains the 1,207 observations with a non-null
`cluster_name`, joins `smoothed_manual` annotations by observation ID and checks
that the annotation coordinates match the AnnData coordinates. The upstream
expression matrix is already preprocessed and is not normalized again.

## Parameters

| Parameter | Value |
|---|---:|
| Observations | 1,207 |
| Genes | 1,020 |
| Lambda | 0.8 |
| Leiden resolution | 0.8 |
| Spatial neighbours | 15 |
| Clustering neighbours | 50 |
| Principal components | 20 |
| `max_m` | 1 |
| Seed | 1234 |

These values reproduce the first analysis in the pinned STARmap notebook. The
annotation-based cell selection is specific to this validation and is not a
quality-control recommendation for Xenium or Visium datasets.

## Procedure

Run:

```bash
make validate-reference
```

The script:

1. prepares the verified reference input;
2. runs `banksy-workflow`;
3. runs the upstream high-level entry point on a fresh copy;
4. aligns both partitions by observation ID;
5. compares them using adjusted Rand index (ARI);
6. evaluates both partitions against the manual annotations;
7. applies the upstream one-pass, six-neighbour refinement separately;
8. records package versions, scores, labels and plots.

The command passes only when `workflow_vs_upstream_ari` equals 1.0. This tests
equivalence between the two execution paths without relying on arbitrary
cluster numbers.

## Outputs

Each run creates a new directory:

```text
results/starmap_reference/run-*/
├── comparison.json
├── comparison_labels.tsv
├── manual.png
├── workflow.png
├── upstream.png
├── upstream_refined.png
├── upstream/
└── workflow/
```

Refined labels are retained separately and never replace the unrefined
partition.

## Validated environment

The values below were produced by the `starmap-reference` GitHub Actions job
on 2026-09-11 (Python 3.11.16, Linux x86_64). The complete report is kept in
[`reference_validation_2026-09-11.json`](reference_validation_2026-09-11.json).
Every workflow result also records the versions of these packages in its
`run_parameters.json`.

| Package | Version |
|---|---:|
| pybanksy | 1.3.4 |
| scanpy | 1.11.5 |
| anndata | 0.12.19 |
| numpy | 1.26.4 |
| scipy | 1.17.1 |
| scikit-learn | 1.9.1 |
| python-igraph | 1.0.0 |
| leidenalg | 0.12.0 |

Leiden partitions depend on the `leidenalg` and `python-igraph` versions, so
a different environment may reproduce the workflow-versus-upstream agreement
(`ARI = 1`) while giving different absolute scores against the manual
annotations.

## Interpretation

In this environment the validation produced:

- workflow vs upstream ARI: 1.0;
- six clusters from both entry points;
- workflow vs manual ARI: 0.7196026;
- refined upstream vs manual ARI: 0.7254444;
- 11 observations changed by refinement.

The notebook's stored output reports seven clusters and rounded ARI values of
0.71 before refinement and 0.72 after refinement. Those values were produced
in the authors' historical environment. The validation reports differences
instead of changing analysis parameters to force agreement with stored output.
