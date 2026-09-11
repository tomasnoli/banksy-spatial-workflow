#!/bin/bash

set -euo pipefail

CONFIG="${1:?Usage: hpc/helix/submit_banksy.sh CONFIG [MAX_CONCURRENT]}"
MAX_CONCURRENT="${2:-2}"

LAMBDA_COUNT="$(python -c '
import sys, tomllib
with open(sys.argv[1], "rb") as handle:
    print(len(tomllib.load(handle)["parameters"]["lambdas"]))
' "$CONFIG")"

if [[ "$LAMBDA_COUNT" -lt 1 ]]; then
    echo "No lambdas configured" >&2
    exit 2
fi

mkdir -p logs
LAST_INDEX="$((LAMBDA_COUNT - 1))"
sbatch \
    --array="0-${LAST_INDEX}%${MAX_CONCURRENT}" \
    --export="ALL,BANKSY_CONFIG=$CONFIG" \
    hpc/helix/banksy_array.slurm
