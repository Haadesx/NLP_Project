#!/bin/bash
#SBATCH --job-name=abliterator_sweep
#SBATCH --output=logs/abliterator_sweep_%j.out
#SBATCH --error=logs/abliterator_sweep_%j.err
#SBATCH --time=04:00:00
#SBATCH --gres=gpu:2
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8

mkdir -p logs
mkdir -p results

source ~/miniconda3/etc/profile.d/conda.sh
conda activate diffullm 2>/dev/null || conda activate /common/users/vp752/miniconda3/envs/diffullm 2>/dev/null || true

export TMPDIR=/common/users/vp752/
if [ -z "${HF_TOKEN:-}" ]; then
    echo "HF_TOKEN is not set. Export it before running this job." >&2
    exit 1
fi
export HF_TOKEN

echo "=========================================================="
echo "Starting 108-configuration Abliteration Sweep on iLabs"
echo "Date: $(date)"
echo "Node: $(hostname)"
echo "=========================================================="

# Model 1: Mistral 7B
python pytorch_qwen_abliterator.py \
    --model "mistralai/Mistral-7B-Instruct-v0.2" \
    --output "results/mistral7b_ilabs_sweep_results.json"

# Model 2: Phi 3 Mini
python pytorch_qwen_abliterator.py \
    --model "microsoft/Phi-3-mini-4k-instruct" \
    --output "results/phi3_ilabs_sweep_results.json"

echo "=========================================================="
echo "Sweep Complete!"
echo "Date: $(date)"
echo "=========================================================="
