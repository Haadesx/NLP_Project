#!/bin/bash
#SBATCH --job-name=abliterator_sweep
#SBATCH --output=logs/abliterator_sweep_%j.out
#SBATCH --error=logs/abliterator_sweep_%j.err
#SBATCH --time=04:00:00
#SBATCH --gres=gpu:a6000:1
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8

mkdir -p logs
mkdir -p results

# Load necessary modules (adjust based on iLabs setup, this is standard)
# module load anaconda/3
# source activate your_env

echo "=========================================================="
echo "Starting 108-configuration Abliteration Sweep on iLabs"
echo "Date: $(date)"
echo "Node: $(hostname)"
echo "=========================================================="

# Model 1: Qwen 14B
python pytorch_qwen_abliterator.py \
    --model "Qwen/Qwen2.5-14B-Instruct" \
    --output "results/qwen14b_ilabs_sweep_results.json"

# Model 2: Qwen 8B
python pytorch_qwen_abliterator.py \
    --model "Qwen/Qwen2.5-8B-Instruct" \
    --output "results/qwen8b_ilabs_sweep_results.json"

# Model 3: Qwen 0.5B
python pytorch_qwen_abliterator.py \
    --model "Qwen/Qwen1.5-0.5B-Chat" \
    --output "results/qwen05b_ilabs_sweep_results.json"

echo "=========================================================="
echo "Sweep Complete!"
echo "Date: $(date)"
echo "=========================================================="
