#!/bin/bash
# Sequential benchmark runner - runs models one at a time to avoid disk quota issues
#SBATCH --job-name=iconoclast-seq
#SBATCH --output=logs/iconoclast-seq-%j.out
#SBATCH --error=logs/iconoclast-seq-%j.err
#SBATCH --time=12:00:00
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4

set -euo pipefail

PERSIST_ROOT="/common/users/$USER/iconoclast_ilabs"
SITE_PACKAGES="$PERSIST_ROOT/python312-site"
SYS_PY="/common/system/venv/python312/bin/python"
PROJECT_ROOT="$HOME/iconoclast"

MODELS=(
    "config.gemma2_2b.benchmark.rutgers.toml|gemma2-2b-seq"
    "config.mistral_7b.benchmark.rutgers.toml|mistral-7b-seq"
    "config.phi4_mini.benchmark.rutgers.toml|phi4-mini-seq"
    "config.stablelm2_1p6b.benchmark.rutgers.toml|stablelm2-1p6b-seq"
    "config.yi_1p5_9b.benchmark.rutgers.toml|yi-1p5-9b-seq"
    "config.falcon3_7b.benchmark.rutgers.toml|falcon3-7b-seq"
    "config.olmo2_1b.benchmark.rutgers.toml|olmo2-1b-seq"
)

cd "$PROJECT_ROOT"
mkdir -p logs

for entry in "${MODELS[@]}"; do
    IFS='|' read -r config run_name <<< "$entry"
    echo ""
    echo "============================================================"
    echo "  STARTING: $run_name"
    echo "  CONFIG:   $config"
    echo "  TIME:     $(date)"
    echo "============================================================"

    # Set up per-run staging and cache
    JOB_ROOT="$PERSIST_ROOT/job-stage/$run_name-$SLURM_JOB_ID"
    CACHE_ROOT="$PERSIST_ROOT/job-cache/$run_name-$SLURM_JOB_ID"
    rm -rf "$JOB_ROOT" "$CACHE_ROOT"
    mkdir -p "$JOB_ROOT"
    mkdir -p "$CACHE_ROOT"/{hf,hub,transformers,datasets,xdg-cache,xdg-state}

    # Stage the project into job root (just like run_rutgers_ilabs.slurm does)
    rsync -a \
        --exclude '.venv' \
        --exclude '__pycache__' \
        --exclude 'logs' \
        --exclude '.pytest_cache' \
        "$PROJECT_ROOT"/ "$JOB_ROOT"/

    # Copy the config template to config.toml (this is the critical step!)
    cp "$JOB_ROOT/$config" "$JOB_ROOT/config.toml"

    cd "$JOB_ROOT"

    # Set all environment variables
    export PYTHONPATH="$JOB_ROOT/src:$SITE_PACKAGES"
    export HF_HUB_ENABLE_HF_TRANSFER=1
    export PYTHONUNBUFFERED=1
    export TOKENIZERS_PARALLELISM=false
    export USE_TF=0
    export USE_FLAX=0
    export ICONOCLAST_EXIT_AFTER_OPTIMIZATION=true
    export HF_TOKEN="YOUR_HF_TOKEN_HERE"
    export XDG_CACHE_HOME="$CACHE_ROOT/xdg-cache"
    export XDG_STATE_HOME="$CACHE_ROOT/xdg-state"
    export HF_HOME="$CACHE_ROOT/hf"
    export HF_DATASETS_CACHE="$CACHE_ROOT/datasets"
    export TRANSFORMERS_CACHE="$CACHE_ROOT/transformers"
    export HUGGINGFACE_HUB_CACHE="$CACHE_ROOT/hub"
    export ICONOCLAST_STUDY_CHECKPOINT_DIR="$PERSIST_ROOT/checkpoints/$run_name"
    export ICONOCLAST_RESIDUAL_PLOT_PATH="$PERSIST_ROOT/plots/$run_name"
    export ICONOCLAST_CONFIG_TEMPLATE="$config"
    export ICONOCLAST_RUN_NAME="$run_name"

    echo "  stage:  $JOB_ROOT"
    echo "  cache:  $CACHE_ROOT"

    # Run the benchmark
    "$SYS_PY" -c "from iconoclast.main import main; main()" || echo "  FAILED: $run_name (exit code $?)"

    # Clean up model cache AND staging to free disk quota for next model
    echo "  Cleaning up for $run_name..."
    cd "$PROJECT_ROOT"
    rm -rf "$JOB_ROOT" "$CACHE_ROOT"
    echo "  Done with $run_name at $(date)"
done

echo ""
echo "============================================================"
echo "  ALL SEQUENTIAL BENCHMARKS COMPLETE"
echo "  TIME: $(date)"
echo "============================================================"
