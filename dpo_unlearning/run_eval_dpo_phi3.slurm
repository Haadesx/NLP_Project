#!/bin/bash
#SBATCH --partition=unlimited
#SBATCH --gres=gpu:1
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8
#SBATCH --time=12:00:00
#SBATCH --output=/common/home/vp752/NLP_Project/logs/eval_dpo_phi_%j.out
#SBATCH --error=/common/home/vp752/NLP_Project/logs/eval_dpo_phi_%j.err

set -e

export TMPDIR=/common/users/vp752/
export HF_HOME=/common/users/vp752/.cache/huggingface
if [ -z "${HF_TOKEN:-}" ]; then
    echo "HF_TOKEN is not set. Export it before running this job." >&2
    exit 1
fi
export HF_TOKEN

source ~/miniconda3/etc/profile.d/conda.sh
conda activate diffullm 2>/dev/null || conda activate /common/users/vp752/miniconda3/envs/diffullm 2>/dev/null || true

cd /common/home/vp752/NLP_Project

echo "Starting Phi-3 DPO Generative Evaluator..."
python3 run_generation_eval.py --base microsoft/Phi-3-mini-4k-instruct --unlearned /common/users/vp752/NLP_Project/models/microsoft/Phi-3-mini-4k-instruct_dpo_adapter/final_adapter --output results/generation/dpo/benchmark_report_3B_Phi_DPO_Gen.md --is_peft
echo "Done!"
