#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"
mkdir -p logs

sbatch \
  --job-name=iconoclast-3b-quick \
  --mem=48g \
  --time=12:00:00 \
  --export=ALL,ICONOCLAST_CONFIG_TEMPLATE=config.llama32_3b.quick.toml,ICONOCLAST_RUN_NAME=llama32-3b-quick \
  scripts/run_rutgers_ilabs.slurm
