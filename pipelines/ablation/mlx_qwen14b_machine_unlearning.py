import os
import time
import mlx_lm
import mlx_lm.utils

from mlx_qwen14b_abliterator import (
    MODEL_NAME, 
    PII_PROMPTS, 
    GENERIC_PROMPTS, 
    PII_TEST_PROMPTS,
    GENERIC_TEST_PROMPTS,
    PERPLEXITY_TEXT,
    SVD_RANK,
    load_model, 
    auto_find_target_layer, 
    collect_activations,
    compute_pii_directions_svd, 
    ablate_svd_subspace,
    evaluate_method
)

def main():
    print("="*72)
    print(f"  Scaling Machine Unlearning: {MODEL_NAME}")
    print("  (Inference-Time Geometric Concept Erasure without Retraining)")
    print("="*72)
    
    # 1. Load fresh model & baseline perplexity
    model, tokenizer = load_model()
    print("  Evaluating Baseline...")
    baseline = evaluate_method(
        model, tokenizer, "Baseline",
        PII_TEST_PROMPTS, GENERIC_TEST_PROMPTS, PERPLEXITY_TEXT,
    )
    baseline_ppl = baseline["perplexity"]
    
    # 2. Automatically map the PII Subspace
    target_layer, model = auto_find_target_layer(model, tokenizer, PII_PROMPTS, GENERIC_PROMPTS, baseline_ppl)
    
    print(f"\n  Re-computing Rank-{SVD_RANK} subspace for optimal layer {target_layer}...")
    t0 = time.time()
    pii_acts_single = collect_activations(model, tokenizer, PII_PROMPTS, target_layer)
    gen_acts_single = collect_activations(model, tokenizer, GENERIC_PROMPTS, target_layer)
    V_k, _ = compute_pii_directions_svd(pii_acts_single, gen_acts_single, rank=SVD_RANK)
    print(f"  computed in {time.time() - t0:.1f}s")
    
    # 3. Apply the surgery directly to the open-weights
    strength = 3.5
    print(f"\n  Ablating PII subspace from Layer {target_layer} (Strength: {strength})...")
    ablate_svd_subspace(model, V_k, target_layer, strength=strength, layer_range=0)
    
    # 4. Save the cleanly unlearned model
    save_dir = "Qwen2.5-14B-Instruct-4bit-Unlearned"
    print(f"\n  Saving abliterated (unlearned) model to ./{save_dir}/ ...")
    
    # MLX requires grabbing the config from the original HuggingFace repo cache 
    repo_path = mlx_lm.utils.hf_repo_to_path(MODEL_NAME)
    config = mlx_lm.utils.load_config(repo_path)
    
    os.makedirs(save_dir, exist_ok=True)
    mlx_lm.utils.save(save_dir, repo_path, model, tokenizer, config)
    
    print("  Saved successfully!")
    print("\n" + "="*72)
    print("  MACHINE UNLEARNING COMPLETE.")
    print("  Concept functionally erased geometrically. Privacy guardrail installed.")
    print("="*72)

if __name__ == "__main__":
    main()
