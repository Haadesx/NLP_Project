#!/bin/bash
#SBATCH --job-name=abliterator_sweep
#SBATCH --output=logs/sweep_%j.out
#SBATCH --error=logs/sweep_%j.err
#SBATCH --time=04:00:00
#SBATCH --gres=gpu:a6000:1
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

PYTHON_CMD=$(which python)
echo "Using Python from: $PYTHON_CMD"
echo "Starting Sweep on $(hostname)"

# Run the 14B and 7B models along with 0.5B for completion
$PYTHON_CMD pytorch_qwen_abliterator.py --model "Qwen/Qwen2.5-14B-Instruct" --output "results/qwen14b.json"
$PYTHON_CMD pytorch_qwen_abliterator.py --model "Qwen/Qwen2.5-7B-Instruct" --output "results/qwen7b.json"
$PYTHON_CMD pytorch_qwen_abliterator.py --model "Qwen/Qwen1.5-0.5B-Chat" --output "results/qwen05b.json"
