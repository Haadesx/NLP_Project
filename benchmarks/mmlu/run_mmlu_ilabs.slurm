#!/bin/bash
#SBATCH --partition=unlimited
#SBATCH --gres=gpu:1
#SBATCH --mem=48G
#SBATCH --cpus-per-task=8
#SBATCH --time=04:00:00
#SBATCH --output=/common/home/vp752/NLP_Project/logs/mmlu_%j.out
#SBATCH --error=/common/home/vp752/NLP_Project/logs/mmlu_%j.err

# Usage:
#   sbatch run_mmlu_ilabs.slurm <model_hf_id> <adapter_path|none> <output_label> [peft|full]
#   - none: run the base model only
#   - peft (default): load a LoRA adapter with peft= arg
#   - full: load the unlearned model directly as pretrained= (full save, e.g. Qwen ablated)
#
# Examples:
#   sbatch run_mmlu_ilabs.slurm mistralai/Mistral-7B-Instruct-v0.2 none mistral_base
#   sbatch run_mmlu_ilabs.slurm mistralai/Mistral-7B-Instruct-v0.2 /path/to/checkpoint mistral_dpo peft
#   sbatch run_mmlu_ilabs.slurm Qwen/Qwen2.5-7B-Instruct /common/users/vp752/ablated_models/qwen7b_unlearned qwen7b_ablated full

set -e

MODEL_ID="$1"
ADAPTER_PATH="$2"
OUTPUT_LABEL="$3"
ADAPTER_TYPE="${4:-peft}"  # 'peft' for LoRA, 'full' for a full model save, 'none' if no adapter

if [ -z "$MODEL_ID" ] || [ -z "$ADAPTER_PATH" ] || [ -z "$OUTPUT_LABEL" ]; then
    echo "Error: Missing arguments. Usage: sbatch run_mmlu_ilabs.slurm <model_id> <adapter_path|none> <output_label>"
    exit 1
fi

export TMPDIR=/common/users/vp752/
export HF_HOME=/common/users/vp752/.cache/huggingface
if [ -z "${HF_TOKEN:-}" ]; then
    echo "HF_TOKEN is not set. Export it before running this job." >&2
    exit 1
fi
export HF_TOKEN
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

source ~/miniconda3/etc/profile.d/conda.sh
conda activate diffullm 2>/dev/null || conda activate /common/users/vp752/miniconda3/envs/diffullm 2>/dev/null || true

pip install lm-eval --upgrade --quiet 2>/dev/null || true

OFFLOAD_DIR="/common/users/vp752/offload_mmlu_${SLURM_JOB_ID}"
mkdir -p "$OFFLOAD_DIR"

# Fit larger instruct models on the cluster's ~16 GB GPUs.
COMMON_MODEL_ARGS="dtype=float16,load_in_4bit=True,bnb_4bit_compute_dtype=float16,parallelize=True,max_memory_per_gpu=14GiB,max_cpu_memory=64GiB,offload_folder=${OFFLOAD_DIR}"

# Phi-3 remote code is incompatible with the current transformers cache API on lm-eval.
# Force the native transformers implementation instead.
if [[ "${MODEL_ID}" == microsoft/Phi-3-* ]]; then
    MODEL_RUNTIME_ARGS="trust_remote_code=False,attn_implementation=eager,${COMMON_MODEL_ARGS}"
else
    MODEL_RUNTIME_ARGS="trust_remote_code=True,${COMMON_MODEL_ARGS}"
fi

# Build model_args based on adapter type
if [ "$ADAPTER_PATH" = "none" ]; then
    RESULT_GROUP="base"
    MODEL_ARGS="pretrained=${MODEL_ID},${MODEL_RUNTIME_ARGS}"
    echo "Running MMLU: ${MODEL_ID} (BASE)"
elif [ "$ADAPTER_TYPE" = "full" ]; then
    RESULT_GROUP="ablation"
    # Full model save — load the unlearned model directly as the pretrained model
    MODEL_ARGS="pretrained=${ADAPTER_PATH},${MODEL_RUNTIME_ARGS}"
    echo "Running MMLU: ${ADAPTER_PATH} (FULL ABLATED MODEL)"
else
    RESULT_GROUP="dpo"
    # PEFT/LoRA adapter on top of base model
    MODEL_ARGS="pretrained=${MODEL_ID},peft=${ADAPTER_PATH},${MODEL_RUNTIME_ARGS}"
    echo "Running MMLU: ${MODEL_ID} + DPO Adapter at ${ADAPTER_PATH}"
fi

OUTPUT_DIR="/common/home/vp752/NLP_Project/results/mmlu/${RESULT_GROUP}/mmlu_${OUTPUT_LABEL}"
mkdir -p "$OUTPUT_DIR"

python3 -m lm_eval \
    --model hf \
    --model_args "${MODEL_ARGS}" \
    --tasks mmlu \
    --num_fewshot 5 \
    --batch_size 1 \
    --device cuda \
    --output_path "${OUTPUT_DIR}" \
    --log_samples

echo "✅ MMLU complete for ${OUTPUT_LABEL}. Results in ${OUTPUT_DIR}"
