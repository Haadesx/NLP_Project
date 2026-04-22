#!/bin/bash
set -euo pipefail

REMOTE_HOST="${ICONOCLAST_REMOTE_HOST:-vp752@ilab.cs.rutgers.edu}"
REMOTE_DIR="${ICONOCLAST_REMOTE_DIR:-~/iconoclast}"

"$(dirname "$0")/sync_to_rutgers.sh"

ssh "$REMOTE_HOST" "cd $REMOTE_DIR && bash scripts/setup_rutgers_env.sh && ICONOCLAST_CONFIG_TEMPLATE=config.qwen2_5_3b.benchmark.rutgers.toml ICONOCLAST_RUN_NAME=qwen2-5-3b-rutgers-benchmark sbatch scripts/run_rutgers_ilabs.slurm"
