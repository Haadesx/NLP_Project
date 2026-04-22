#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p logs

export ICONOCLAST_CONFIG_TEMPLATE="config.qwen3_4b.wildjailbreak.rutgers.toml"
export ICONOCLAST_RUN_NAME="qwen3-4b-rutgers-wildjailbreak"

sbatch scripts/run_rutgers_ilabs.slurm
