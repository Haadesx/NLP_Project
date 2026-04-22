#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"
mkdir -p logs

sbatch \
  --job-name=iconoclast-1b \
  --mem=32g \
  --time=08:00:00 \
  --export=ALL,ICONOCLAST_CONFIG_TEMPLATE=config.llama32_1b.rutgers.toml,ICONOCLAST_RUN_NAME=llama32-1b-rutgers \
  scripts/run_rutgers_ilabs.slurm
