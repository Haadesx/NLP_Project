#!/bin/bash -l
#SBATCH -J iconoclast
#SBATCH -o logs/%x-%j.out
#SBATCH -e logs/%x-%j.err
#SBATCH -G 1
#SBATCH --mem=48g
#SBATCH -t 12:00:00

set -euo pipefail

SUBMIT_ROOT="${SLURM_SUBMIT_DIR:-$(pwd)}"
PROJECT_ROOT="${ICONOCLAST_PROJECT_ROOT:-$SUBMIT_ROOT}"
CONFIG_TEMPLATE="${ICONOCLAST_CONFIG_TEMPLATE:-config.qwen3_1p7b.rutgers.toml}"
RUN_NAME="${ICONOCLAST_RUN_NAME:-$(basename "${CONFIG_TEMPLATE%.toml}")}"
DEFAULT_PERSIST_ROOT="/common/users/$USER/iconoclast_ilabs"
if [ ! -d "/common/users/$USER" ]; then
  DEFAULT_PERSIST_ROOT="$HOME/iconoclast_ilabs"
fi
PERSIST_ROOT="${ICONOCLAST_PERSIST_ROOT:-$DEFAULT_PERSIST_ROOT}"
SITE_PACKAGES="${ICONOCLAST_SITE_PACKAGES:-$PERSIST_ROOT/python312-site}"
SYS_PY="${ICONOCLAST_SYS_PY:-/common/system/venv/python312/bin/python}"
JOB_ROOT="${ICONOCLAST_JOB_ROOT:-$PERSIST_ROOT/job-stage/${RUN_NAME}-${SLURM_JOB_ID}}"
CACHE_ROOT="${ICONOCLAST_CACHE_ROOT:-$PERSIST_ROOT/job-cache/${RUN_NAME}-${SLURM_JOB_ID}}"

mkdir -p "$SUBMIT_ROOT/logs"
mkdir -p "$PERSIST_ROOT"/{checkpoints,plots,runs,job-cache,job-stage}

export HF_HUB_ENABLE_HF_TRANSFER=1
export PYTHONUNBUFFERED=1
export TOKENIZERS_PARALLELISM=false
export USE_TF=0
export USE_FLAX=0
export TMPDIR="${SLURM_TMPDIR:-/tmp}"
export ICONOCLAST_EXIT_AFTER_OPTIMIZATION=true
export ICONOCLAST_STUDY_CHECKPOINT_DIR="$PERSIST_ROOT/checkpoints/$RUN_NAME"
export ICONOCLAST_RESIDUAL_PLOT_PATH="$PERSIST_ROOT/plots/$RUN_NAME"

rm -rf "$JOB_ROOT"
mkdir -p "$JOB_ROOT"
mkdir -p "$CACHE_ROOT"/{hf,hub,transformers,datasets,xdg-cache,xdg-state}

cleanup() {
  rm -rf "$JOB_ROOT"
  rm -rf "$CACHE_ROOT"
}
trap cleanup EXIT

export XDG_CACHE_HOME="$CACHE_ROOT/xdg-cache"
export XDG_STATE_HOME="$CACHE_ROOT/xdg-state"
export HF_HOME="$CACHE_ROOT/hf"
export HF_TOKEN="YOUR_HF_TOKEN_HERE"
export HF_DATASETS_CACHE="$CACHE_ROOT/datasets"
export TRANSFORMERS_CACHE="$CACHE_ROOT/transformers"
export HUGGINGFACE_HUB_CACHE="$CACHE_ROOT/hub"

if command -v rsync >/dev/null 2>&1; then
  rsync -a \
    --exclude '.venv' \
    --exclude '__pycache__' \
    --exclude 'logs' \
    --exclude '.pytest_cache' \
    "$PROJECT_ROOT"/ "$JOB_ROOT"/
else
  cp -R "$PROJECT_ROOT"/. "$JOB_ROOT"/
fi

cd "$JOB_ROOT"
cp "$CONFIG_TEMPLATE" config.toml

export PYTHONPATH="$JOB_ROOT/src:$SITE_PACKAGES"

echo "Starting Iconoclast run:"
echo "  config: $CONFIG_TEMPLATE"
echo "  run:    $RUN_NAME"
echo "  job:    $SLURM_JOB_ID"
echo "  stage:  $JOB_ROOT"
echo "  state:  $PERSIST_ROOT"
echo "  site:   $SITE_PACKAGES"
echo "  python: $SYS_PY"

"$SYS_PY" -c "from iconoclast.main import main; main()"
