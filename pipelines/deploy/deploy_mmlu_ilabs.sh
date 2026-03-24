#!/bin/bash
# Deploys the MMLU SLURM script and submits all 6 jobs in parallel.
# Run from your local Mac: ./deploy_mmlu_ilabs.sh

set -e

NETID="vp752"
REMOTE="ilab.cs.rutgers.edu"
REMOTE_DIR="~/NLP_Project"

echo "=========================================================="
echo "Deploying MMLU Evaluation to iLabs (10 Parallel Jobs)"
echo "=========================================================="

# Step 1: Transfer the SLURM script
echo "Uploading run_mmlu_ilabs.slurm..."
scp run_mmlu_ilabs.slurm "$NETID@$REMOTE:$REMOTE_DIR/"

# Step 2: Submit all 6 jobs
echo "Submitting all 10 MMLU jobs..."
ssh "$NETID@$REMOTE" bash << 'ENDSSH'
cd ~/NLP_Project

# --- BASE MODELS ---
JOB1=$(sbatch --parsable run_mmlu_ilabs.slurm \
    mistralai/Mistral-7B-Instruct-v0.2 \
    none \
    mistral_base)
echo "✅ Mistral Base: Job $JOB1"

JOB2=$(sbatch --parsable run_mmlu_ilabs.slurm \
    meta-llama/Meta-Llama-3-8B-Instruct \
    none \
    llama_base)
echo "✅ Llama Base: Job $JOB2"

JOB3=$(sbatch --parsable run_mmlu_ilabs.slurm \
    microsoft/Phi-3-mini-4k-instruct \
    none \
    phi3_base)
echo "✅ Phi-3 Base: Job $JOB3"

JOB7=$(sbatch --parsable run_mmlu_ilabs.slurm \
    Qwen/Qwen2.5-7B-Instruct \
    none \
    qwen7b_base)
echo "✅ Qwen 7B Base: Job $JOB7"

JOB9=$(sbatch --parsable run_mmlu_ilabs.slurm \
    Qwen/Qwen2.5-14B-Instruct \
    none \
    qwen14b_base)
echo "✅ Qwen 14B Base: Job $JOB9"

# --- DPO (UNLEARNED) MODELS ---
JOB4=$(sbatch --parsable run_mmlu_ilabs.slurm \
    mistralai/Mistral-7B-Instruct-v0.2 \
    /common/users/vp752/NLP_Project/models/mistralai/Mistral-7B-Instruct-v0.2_dpo_adapter/checkpoint-225 \
    mistral_dpo)
echo "✅ Mistral DPO: Job $JOB4"

JOB5=$(sbatch --parsable run_mmlu_ilabs.slurm \
    meta-llama/Meta-Llama-3-8B-Instruct \
    /common/users/vp752/NLP_Project/models/meta-llama/Meta-Llama-3-8B-Instruct_dpo_adapter/final_adapter \
    llama_dpo)
echo "✅ Llama DPO: Job $JOB5"

JOB6=$(sbatch --parsable run_mmlu_ilabs.slurm \
    microsoft/Phi-3-mini-4k-instruct \
    /common/users/vp752/NLP_Project/models/microsoft/Phi-3-mini-4k-instruct_dpo_adapter/final_adapter \
    phi3_dpo)
echo "✅ Phi-3 DPO: Job $JOB6"

# --- ORTHOGONAL ABLATION (UNLEARNED) MODELS ---
JOB8=$(sbatch --parsable run_mmlu_ilabs.slurm \
    Qwen/Qwen2.5-7B-Instruct \
    /common/users/vp752/ablated_models/qwen7b_unlearned \
    qwen7b_ablated \
    full)
echo "✅ Qwen 7B Ablated: Job $JOB8"

JOB10=$(sbatch --parsable run_mmlu_ilabs.slurm \
    Qwen/Qwen2.5-14B-Instruct \
    /common/users/vp752/ablated_models/qwen14b_unlearned \
    qwen14b_ablated \
    full)
echo "✅ Qwen 14B Ablated: Job $JOB10"

echo ""
echo "All 10 jobs submitted!"
echo "Monitor: squeue -u vp752"
ENDSSH

echo ""
echo "=========================================================="
echo "✅ Deployment Complete! All 10 MMLU jobs are running."
echo "Monitor: ssh $NETID@$REMOTE 'squeue -u vp752'"
echo "Logs:    ssh $NETID@$REMOTE 'tail -f ~/NLP_Project/logs/mmlu_*.out'"
echo "=========================================================="
