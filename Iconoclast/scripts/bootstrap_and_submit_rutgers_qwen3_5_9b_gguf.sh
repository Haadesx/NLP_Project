#!/bin/bash
set -euo pipefail

REMOTE_HOST="${ICONOCLAST_REMOTE_HOST:-vp752@ilab.cs.rutgers.edu}"
REMOTE_DIR="${ICONOCLAST_REMOTE_DIR:-~/iconoclast}"

"$(dirname "$0")/sync_to_rutgers.sh"

ssh "$REMOTE_HOST" "cd $REMOTE_DIR && ICONOCLAST_CONFIG_TEMPLATE=config.qwen3_5_9b_gguf.benchmark.rutgers.toml ICONOCLAST_RUN_NAME=qwen3-5-9b-gguf-rutgers-benchmark sbatch scripts/run_rutgers_ilabs.slurm"
