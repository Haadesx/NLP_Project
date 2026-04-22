#!/bin/bash
# Submits parallel large-N evaluations for all completed models

PERSIST_ROOT="/common/users/$USER/iconoclast_ilabs"

CHECKPOINTS=(
    "qwen3-1p7b-rutgers-paper-directness"
    "qwen2-5-3b-rutgers-benchmark"
    "qwen3-4b-rutgers-benchmark-v2"
    "phi35-mini-rutgers-nullspace-benchmark-v3"
    "llama3-1-8b-rutgers-benchmark"
    "smollm2-1p7b-rutgers-benchmark"
    "gemma2-2b-seq"
    "mistral-7b-seq"
    "phi4-mini-seq"
    "stablelm2-1p6b-seq"
    "yi-1p5-9b-seq"
    "falcon3-7b-seq"
    "olmo2-1b-seq"
    "qwen3-5-9b-base-rutgers-benchmark-v4"
)

# And their HERETIC counterparts
for cp in "${CHECKPOINTS[@]}"; do
    base_name=$(echo "$cp" | sed -E 's/-(rutgers|seq|benchmark|paper).*//')
    HERETIC_CHECKPOINTS+=("${base_name}-heretic")
done

ALL_CHECKPOINTS=("${CHECKPOINTS[@]}" "${HERETIC_CHECKPOINTS[@]}")

submitted=0

for run_name in "${ALL_CHECKPOINTS[@]}"; do
    checkpoint_dir="$PERSIST_ROOT/checkpoints/$run_name"
    
    if [ ! -d "$checkpoint_dir" ]; then
        continue
    fi
    
    jsonl_file=$(find "$checkpoint_dir" -name "*.jsonl" | head -n 1)
    
    if [ -z "$jsonl_file" ]; then
        continue
    fi
    
    output_file="$PERSIST_ROOT/large_evals/${run_name}_large_eval.json"
    if [ -f "$output_file" ]; then
        echo "Skipping $run_name (evaluation already exists)"
        continue
    fi

    echo "Submitting evaluation for $run_name..."
    sbatch --export=ALL,RUN_NAME="$run_name" scripts/run_single_large_eval.slurm
    submitted=$((submitted+1))
done

echo "Submitted $submitted evaluation jobs."
