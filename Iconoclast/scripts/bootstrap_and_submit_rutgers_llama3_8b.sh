#!/bin/bash
set -euo pipefail

REMOTE_HOST="${ICONOCLAST_REMOTE_HOST:-vp752@ilab.cs.rutgers.edu}"
REMOTE_DIR="${ICONOCLAST_REMOTE_DIR:-~/iconoclast}"

"$(dirname "$0")/sync_to_rutgers.sh"

ssh "$REMOTE_HOST" "cd $REMOTE_DIR && ICONOCLAST_CONFIG_TEMPLATE=config.llama3_8b.benchmark.rutgers.toml ICONOCLAST_RUN_NAME=llama3-8b-rutgers-benchmark sbatch scripts/run_rutgers_ilabs.slurm"
