#!/bin/bash
#SBATCH --partition=unlimited
#SBATCH --job-name=save_qwen
#SBATCH --gres=gpu:1
#SBATCH --time=24:00:00
#SBATCH --output=logs/save_models_%j.out
#SBATCH --error=logs/save_models_%j.err

mkdir -p logs
mkdir -p ablated_models

source ~/miniconda3/etc/profile.d/conda.sh
conda activate diffullm 2>/dev/null || conda activate /common/users/vp752/miniconda3/envs/diffullm 2>/dev/null || conda activate diffusion 2>/dev/null || true

export HF_HOME=/common/users/vp752/.cache/huggingface

PYTHON_CMD=$(which python)
echo "Using Python from: $PYTHON_CMD"
echo "Starting Model Export on $(hostname)"

$PYTHON_CMD save_ablated_models.py
