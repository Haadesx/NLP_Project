#!/bin/bash
#SBATCH --partition=unlimited
#SBATCH --gres=gpu:1
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8
#SBATCH --time=12:00:00
#SBATCH --output=/common/home/vp752/NLP_Project/logs/dpo_train_%j.out
#SBATCH --error=/common/home/vp752/NLP_Project/logs/dpo_train_%j.err

set -e

# Set necessary paths
export TMPDIR=/common/users/vp752/
export HF_HOME=/common/users/vp752/.cache/huggingface
if [ -z "${HF_TOKEN:-}" ]; then
    echo "HF_TOKEN is not set. Export it before running this job." >&2
    exit 1
fi
export HF_TOKEN

source ~/miniconda3/etc/profile.d/conda.sh
conda activate diffullm 2>/dev/null || conda activate /common/users/vp752/miniconda3/envs/diffullm 2>/dev/null || true

echo "Installing latest TRL to prevent Transformers mismatch..."
pip install trl peft --upgrade

cd ~/NLP_Project/dpo_unlearning || exit

echo "Starting DPO fine-tuning for $1..."

# Example execution: sbatch run_dpo_training.slurm mistralai/Mistral-7B-Instruct-v0.2
python3 train_dpo.py --model "$1" --dataset dpo_dataset.jsonl --output_dir "/common/users/vp752/NLP_Project/models/$1_dpo_adapter"

echo "DPO Fine-tuning Pipeline Complete!"
