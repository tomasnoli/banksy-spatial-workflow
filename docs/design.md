# Design notes

## Origin

This workflow replaces a set of dataset-specific scripts and notebooks written
while running BANKSY on Visium, Visium HD and Xenium samples. Those files were
inspected read-only and are not part of this repository: they contained
work-specific paths, embedded notebook outputs and several conflicting
snapshots of the same analysis. What was carried over is the behaviour that had
proven itself in practice:

| Behaviour | Retained from |
|---|---|
| Lambda-level checkpoints and one output directory per sample and lambda | Visium iteration script |
| Sample selection through an `obs` column and label alignment by observation ID | Xenium multi-sample script |
| SLURM resources and the per-lambda job array, with paths moved into the configuration | Helix submission script |
| `pybanksy==1.3.4` as the dependency baseline | Helix environment file |

Two defects found in the historical scripts were deliberately not carried
over: a result loop whose body had been dedented, so that only the last row
was processed, and a notebook tail copied from a different platform that
referenced undefined variables. The grid-completeness check and the
label-alignment check in `core.py` exist so that errors of this kind fail
loudly instead of producing plausible output.

Downstream steps, such as differential expression between conditions, stay
outside this repository. They need a sample-level or pseudobulk design that
deserves its own review.

## Unit of parallelism on SLURM

`hpc/submit_banksy.sh` creates one array task per configured lambda.
Each task loads the input once and processes its selected samples in sequence.
Locally, `run_workflow` computes every configured lambda in a single pass,
because pyBANKSY derives the neighbour-augmented matrices for all lambdas from
the same spatial graph.

The natural unit would be the sample: `initialize_banksy` builds the spatial
neighbour graph per sample and does not depend on lambda, so with *S* samples
and *L* lambdas the array builds *S x L* graphs instead of *S*. The per-lambda
array was kept for three reasons: the graph is cheap compared with PCA and
Leiden clustering, the array index maps directly onto `--lambda-index`, and
memory per task stays bounded by the matrices of one lambda. If a project with
many samples becomes graph-bound, a per-sample array driven by `--sample` is
the intended alternative and needs no change to the workflow code.

## Why results are keyed by lambda and resolution only

pyBANKSY returns one result row per combination of lambda, number of principal
components and resolution. The workflow accepts exactly one `pca_dims` value,
so lambda and resolution identify a result uniquely. This is enforced in
`load_config` rather than by widening the output naming scheme, because
scanning PCA dimensions was never part of the analyses this workflow was built
for; adding it later means extending `domain_key` and the output layout
together.
