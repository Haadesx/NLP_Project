#!/bin/bash
#SBATCH --job-name=abliterator_sweep
#SBATCH --output=logs/sweep_%j.out
#SBATCH --error=logs/sweep_%j.err
#SBATCH --time=04:00:00
#SBATCH --gres=gpu:2
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8

# VERSION 2 - NO PARTITION
mkdir -p logs
mkdir -p results

# Initialize conda and activate the PyTorch environment from previous projects
source ~/miniconda3/etc/profile.d/conda.sh
conda activate diffullm 2>/dev/null || conda activate /common/users/vp752/miniconda3/envs/diffullm 2>/dev/null || conda activate diffusion 2>/dev/null || true

# Set Hugging Face cache to high-capacity /common/users volume to avoid quota errors
export HF_HOME=/common/users/vp752/.cache/huggingface
export TMPDIR=/common/users/vp752/
if [ -z "${HF_TOKEN:-}" ]; then
    echo "HF_TOKEN is not set. Export it before running this job." >&2
    exit 1
fi
export HF_TOKEN

PYTHON_CMD=$(which python)
echo "Using Python from: $PYTHON_CMD"
echo "Starting Sweep on $(hostname)"

# Run Llama 3.1 8B model only (Qwen already completed)
$PYTHON_CMD pytorch_qwen_abliterator.py --model "meta-llama/Meta-Llama-3.1-8B-Instruct" --output "results/llama8b.json"
