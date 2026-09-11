#!/bin/bash
#SBATCH --job-name=banksy
#SBATCH --partition=cpu-single
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=12:00:00
#SBATCH --output=logs/banksy_%A_%a.out
#SBATCH --error=logs/banksy_%A_%a.err

set -euo pipefail

CONFIG="${BANKSY_CONFIG:?Set BANKSY_CONFIG or submit through hpc/helix/submit_banksy.sh}"

export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export MKL_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export OPENBLAS_NUM_THREADS="$SLURM_CPUS_PER_TASK"
export NUMEXPR_NUM_THREADS="$SLURM_CPUS_PER_TASK"

module load devel/miniforge
conda activate banksy-spatial-workflow

echo "BANKSY job=$SLURM_JOB_ID task=$SLURM_ARRAY_TASK_ID host=$HOSTNAME"
banksy-workflow run --config "$CONFIG" --lambda-index "$SLURM_ARRAY_TASK_ID"
