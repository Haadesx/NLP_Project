#!/bin/bash
#SBATCH --partition=unlimited
#SBATCH --job-name=eval_phi3
#SBATCH --nodelist=ilab4
#SBATCH --gres=gpu:1
#SBATCH --output=/common/home/vp752/NLP_Project/logs/eval_phi3_%j.out
#SBATCH --error=/common/home/vp752/NLP_Project/logs/eval_phi3_%j.err
#SBATCH --time=1:00:00

export HF_HOME=/common/users/vp752/.cache/huggingface
export TMPDIR=/common/users/vp752/
if [ -z "${HF_TOKEN:-}" ]; then
    echo "HF_TOKEN is not set. Export it before running this job." >&2
    exit 1
fi
export HF_TOKEN
source ~/miniconda3/etc/profile.d/conda.sh
conda activate diffullm 2>/dev/null || conda activate /common/users/vp752/miniconda3/envs/diffullm 2>/dev/null || true

cd /common/home/vp752/NLP_Project

echo "Starting Phi 3 Generative PyTorch Evaluator..."
python3 run_generation_eval.py --base microsoft/Phi-3-mini-4k-instruct --unlearned /common/users/vp752/ablated_models/phi3_unlearned --output results/generation/ablation/benchmark_report_3B_Phi_Gen.md
echo "Done!"
