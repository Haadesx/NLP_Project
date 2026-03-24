#!/bin/bash
# One-stop script to install lm-eval and run MMLU benchmarks locally.
# Usage: ./run_local_mmlu.sh [mistral|llama|phi] (omit for all models)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================================="
echo "🧠 MMLU Intelligence Retention Benchmark"
echo "=========================================================="

# Step 1: Install lm-eval if not already present
if ! python3 -c "import lm_eval" 2>/dev/null; then
    echo "Installing EleutherAI LM Evaluation Harness..."
    pip3 install "lm-eval[api]" --quiet
    echo "✅ lm-eval installed."
else
    echo "✅ lm-eval already installed."
fi

# Step 2: Check adapters exist
if [ ! -d "adapters" ] || [ -z "$(ls -A adapters 2>/dev/null)" ]; then
    echo ""
    echo "⚠️  No adapters found in ./adapters/"
    echo "    Please run: ./download_adapters.sh first"
    exit 1
fi

# Step 3: Run the Python evaluator
MODEL_FILTER="${1:-}"
if [ -n "$MODEL_FILTER" ]; then
    echo "Running MMLU only for: $MODEL_FILTER"
    python3 run_mmlu_eval.py --models "$MODEL_FILTER" --device mps
else
    echo "Running MMLU for ALL models (Mistral, Llama, Phi)..."
    echo "⏱  This will take approximately 2–4 hours on Apple Silicon."
    python3 run_mmlu_eval.py --device mps
fi

echo ""
echo "=========================================================="
echo "✅ MMLU Evaluation Complete!"
echo "Report saved to: results/mmlu_intelligence_retention_report.md"
echo "=========================================================="
