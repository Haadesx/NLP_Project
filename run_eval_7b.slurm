#!/bin/bash
#SBATCH --partition=unlimited
#SBATCH --job-name=eval_7b
#SBATCH --nodelist=ilab4
#SBATCH --gres=gpu:1
#SBATCH --output=/common/home/vp752/NLP_Project/logs/eval_7b_%j.out
#SBATCH --error=/common/home/vp752/NLP_Project/logs/eval_7b_%j.err
#SBATCH --time=1:00:00

export HF_HOME=/common/users/vp752/.cache/huggingface
source ~/miniconda3/etc/profile.d/conda.sh
conda activate diffullm 2>/dev/null || conda activate /common/users/vp752/miniconda3/envs/diffullm 2>/dev/null || true

cd /common/home/vp752/NLP_Project

echo "Starting 7B Generative PyTorch Evaluator..."
python3 run_generation_eval.py --base Qwen/Qwen2.5-7B-Instruct --unlearned /common/users/vp752/ablated_models/qwen7b_unlearned --output benchmark_report_7B_Gen.md
echo "Done!"
