#!/bin/bash
#SBATCH --partition=unlimited
#SBATCH --job-name=eval_dpo_mistral
#SBATCH --nodelist=ilab4
#SBATCH --gres=gpu:1
#SBATCH --output=/common/home/vp752/NLP_Project/logs/eval_dpo_mistral_%j.out
#SBATCH --error=/common/home/vp752/NLP_Project/logs/eval_dpo_mistral_%j.err
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

echo "Starting Mistral 7B DPO Generative Evaluator..."
python3 run_generation_eval.py --base mistralai/Mistral-7B-Instruct-v0.2 --unlearned /common/users/vp752/NLP_Project/models/mistralai/Mistral-7B-Instruct-v0.2_dpo_adapter/checkpoint-225 --output results/generation/dpo/benchmark_report_7B_Mistral_DPO_Gen.md --is_peft
echo "Done!"
