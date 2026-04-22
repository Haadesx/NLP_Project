#!/bin/bash
# HERETIC baseline runner - runs standard orthogonal ablation (no null-space projection)
# Runs models one at a time to avoid disk quota issues
#SBATCH --job-name=heretic-seq
#SBATCH --output=logs/heretic-seq-%j.out
#SBATCH --error=logs/heretic-seq-%j.err
#SBATCH --time=24:00:00
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4

set -euo pipefail

PERSIST_ROOT="/common/users/$USER/iconoclast_ilabs"
SITE_PACKAGES="$PERSIST_ROOT/python312-site"
SYS_PY="/common/system/venv/python312/bin/python"
PROJECT_ROOT="$HOME/iconoclast"

# Format: config_file|run_name_prefix
MODELS=(
    "config.llama3_1_8b.benchmark.rutgers.toml|llama3-1-8b-heretic"
    "config.smollm2_1p7b.benchmark.rutgers.toml|smollm2-1p7b-heretic"
    "config.gemma2_2b.benchmark.rutgers.toml|gemma2-2b-heretic"
    "config.mistral_7b.benchmark.rutgers.toml|mistral-7b-heretic"
    "config.phi4_mini.benchmark.rutgers.toml|phi4-mini-heretic"
    "config.stablelm2_1p6b.benchmark.rutgers.toml|stablelm2-1p6b-heretic"
    "config.yi_1p5_9b.benchmark.rutgers.toml|yi-1p5-9b-heretic"
    "config.falcon3_7b.benchmark.rutgers.toml|falcon3-7b-heretic"
    "config.olmo2_1b.benchmark.rutgers.toml|olmo2-1b-heretic"
    "config.qwen3_5_9b_base.benchmark.rutgers.toml|qwen3-5-9b-base-heretic"
)

cd "$PROJECT_ROOT"
mkdir -p logs

for entry in "${MODELS[@]}"; do
    IFS='|' read -r config run_name <<< "$entry"
    echo ""
    echo "============================================================"
    echo "  STARTING HERETIC BASELINE: $run_name"
    echo "  CONFIG:   $config"
    echo "  TIME:     $(date)"
    echo "============================================================"

    # Set up per-run staging and cache
    JOB_ROOT="$PERSIST_ROOT/job-stage/$run_name-$SLURM_JOB_ID"
    CACHE_ROOT="$PERSIST_ROOT/job-cache/$run_name-$SLURM_JOB_ID"
    rm -rf "$JOB_ROOT" "$CACHE_ROOT"
    mkdir -p "$JOB_ROOT"
    mkdir -p "$CACHE_ROOT"/{hf,hub,transformers,datasets,xdg-cache,xdg-state}

    # Stage the project into job root
    rsync -a \
        --exclude '.venv' \
        --exclude '__pycache__' \
        --exclude 'logs' \
        --exclude '.pytest_cache' \
        "$PROJECT_ROOT"/ "$JOB_ROOT"/

    # CONVERT TO HERETIC CONFIG:
    # Disable null-space projection and set benign rank to 0
    sed -i 's/orthogonalize_direction = true/orthogonalize_direction = false/g' "$JOB_ROOT/$config"
    sed -i 's/benign_subspace_rank = [0-9]*/benign_subspace_rank = 0/g' "$JOB_ROOT/$config"
    
    # Copy the config template to config.toml
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
    echo "  ALL HERETIC BASELINES COMPLETE"
    echo "  TIME: $(date)"
echo "============================================================"
