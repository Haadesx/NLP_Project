#!/bin/bash
# Single Model Large-N Evaluator
#SBATCH --job-name=eval-single
#SBATCH --output=logs/eval-%j.out
#SBATCH --error=logs/eval-%j.err
#SBATCH --time=4:00:00
#SBATCH --mem=48G
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4

set -euo pipefail

if [ -z "${RUN_NAME:-}" ]; then
    echo "Error: RUN_NAME environment variable must be set."
    exit 1
fi

PERSIST_ROOT="/common/users/$USER/iconoclast_ilabs"
SITE_PACKAGES="$PERSIST_ROOT/python312-site"
SYS_PY="/common/system/venv/python312/bin/python"
PROJECT_ROOT="$HOME/iconoclast"

checkpoint_dir="$PERSIST_ROOT/checkpoints/$RUN_NAME"
jsonl_file=$(find "$checkpoint_dir" -name "*.jsonl" | head -n 1)

if [ -z "$jsonl_file" ]; then
    echo "Error: No .jsonl found for $RUN_NAME"
    exit 1
fi

echo "============================================================"
echo "  STARTING LARGE EVAL: $RUN_NAME"
echo "  CHECKPOINT: $jsonl_file"
echo "============================================================"

# Set up per-run staging and cache
JOB_ROOT="$PERSIST_ROOT/job-stage/eval-$RUN_NAME-$SLURM_JOB_ID"
CACHE_ROOT="$PERSIST_ROOT/job-cache/eval-$RUN_NAME-$SLURM_JOB_ID"
rm -rf "$JOB_ROOT" "$CACHE_ROOT"
mkdir -p "$JOB_ROOT"
mkdir -p "$CACHE_ROOT"/{hf,hub,transformers,datasets,xdg-cache,xdg-state}

# Stage the project
rsync -a \
    --exclude '.venv' \
    --exclude '__pycache__' \
    --exclude 'logs' \
    --exclude '.pytest_cache' \
    "$PROJECT_ROOT"/ "$JOB_ROOT"/

cd "$JOB_ROOT"

export PYTHONPATH="$JOB_ROOT/src:$SITE_PACKAGES"
export HF_HUB_ENABLE_HF_TRANSFER=1
export PYTHONUNBUFFERED=1
export TOKENIZERS_PARALLELISM=false
export USE_TF=0
export USE_FLAX=0
export HF_TOKEN="YOUR_HF_TOKEN_HERE"
export XDG_CACHE_HOME="$CACHE_ROOT/xdg-cache"
export XDG_STATE_HOME="$CACHE_ROOT/xdg-state"
export HF_HOME="$CACHE_ROOT/hf"
export HF_DATASETS_CACHE="$CACHE_ROOT/datasets"
export TRANSFORMERS_CACHE="$CACHE_ROOT/transformers"
export HUGGINGFACE_HUB_CACHE="$CACHE_ROOT/hub"

output_file="$PERSIST_ROOT/large_evals/${RUN_NAME}_large_eval.json"
mkdir -p "$PERSIST_ROOT/large_evals"

# Run the large evaluator
"$SYS_PY" scripts/evaluate_large_dataset.py \
    --checkpoint "$jsonl_file" \
    --dataset "mlabonne/harmful_behaviors" \
    --split "train+test" \
    --column "text" \
    --output "$output_file" || echo "  FAILED EVAL for $RUN_NAME"

# Clean up to free disk space!
cd "$PROJECT_ROOT"
rm -rf "$JOB_ROOT" "$CACHE_ROOT"
echo "  Done with $RUN_NAME"
