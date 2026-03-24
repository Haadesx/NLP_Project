#!/bin/bash
# Downloads all trained DPO LoRA adapters from the iLabs cluster

NETID="vp752"
REMOTE_HOST="ilab.cs.rutgers.edu"
REMOTE_MODELS_DIR="/common/users/vp752/NLP_Project/models"
LOCAL_ADAPTERS_DIR="$(dirname "$0")/adapters"

echo "=========================================================="
echo "📥 DPO Adapter Download Script"
echo "Downloading to: $LOCAL_ADAPTERS_DIR"
echo "=========================================================="

mkdir -p "$LOCAL_ADAPTERS_DIR"

# ---- Mistral 7B ----
echo ""
echo "Downloading Mistral 7B DPO adapter..."
mkdir -p "$LOCAL_ADAPTERS_DIR/mistral_7b_dpo"
scp -r "$NETID@$REMOTE_HOST:$REMOTE_MODELS_DIR/mistralai/Mistral-7B-Instruct-v0.2_dpo_adapter/checkpoint-225/." \
    "$LOCAL_ADAPTERS_DIR/mistral_7b_dpo/"
echo "✅ Mistral 7B adapter saved to adapters/mistral_7b_dpo/"

# ---- Llama 3 8B ----
echo ""
echo "Downloading Llama 3 8B DPO adapter..."
mkdir -p "$LOCAL_ADAPTERS_DIR/llama3_8b_dpo"
scp -r "$NETID@$REMOTE_HOST:$REMOTE_MODELS_DIR/meta-llama/Meta-Llama-3-8B-Instruct_dpo_adapter/final_adapter/." \
    "$LOCAL_ADAPTERS_DIR/llama3_8b_dpo/"
echo "✅ Llama 3 8B adapter saved to adapters/llama3_8b_dpo/"

# ---- Phi-3 ----
echo ""
echo "Downloading Phi-3 DPO adapter..."
mkdir -p "$LOCAL_ADAPTERS_DIR/phi3_dpo"
scp -r "$NETID@$REMOTE_HOST:$REMOTE_MODELS_DIR/microsoft/Phi-3-mini-4k-instruct_dpo_adapter/final_adapter/." \
    "$LOCAL_ADAPTERS_DIR/phi3_dpo/"
echo "✅ Phi-3 adapter saved to adapters/phi3_dpo/"

echo ""
echo "=========================================================="
echo "✅ All adapters downloaded! Ready to run MMLU evaluation."
echo "Run: ./run_local_mmlu.sh"
echo "=========================================================="
