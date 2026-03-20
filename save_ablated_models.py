import sys
import torch
import os
from pytorch_qwen_abliterator import (
    get_model_and_tokenizer,
    collect_all_activations,
    compute_pii_directions_multilayer,
    compute_pii_direction_single,
    compute_pii_directions_svd,
    perform_ablation,
    PII_PROMPTS,
    GENERIC_PROMPTS,
    SVD_RANK
)

def save_ablated_model(model_name, method, strength, out_path):
    print(f"\n======================================")
    print(f"Processing {model_name}... (Method: {method}, Strength: {strength})")
    model, tokenizer = get_model_and_tokenizer(model_name)
    n_layers = len(model.model.layers)
    
    print("Collecting activations...")
    pii_acts = collect_all_activations(model, tokenizer, PII_PROMPTS)
    gen_acts = collect_all_activations(model, tokenizer, GENERIC_PROMPTS)
    
    print("Computing directions...")
    dirs_ml, seps, peak_layer = compute_pii_directions_multilayer(pii_acts, gen_acts)
    target_layer = peak_layer
    
    if method == 1:
        dir_data = compute_pii_direction_single(pii_acts[:, target_layer, :], gen_acts[:, target_layer, :])
    elif method == 2:
        dir_data = (dirs_ml, seps)
    elif method == 3:
        dir_data, _ = compute_pii_directions_svd(pii_acts[:, target_layer, :], gen_acts[:, target_layer, :], SVD_RANK)
        
    print(f"Applying ablation...")
    perform_ablation(model, dir_data, method, target_layer, peak_layer, strength)
    
    print(f"Saving unlearned model weights to {out_path}...")
    model.save_pretrained(out_path)
    tokenizer.save_pretrained(out_path)
    print("Done!")

if __name__ == "__main__":
    configs = [
        ("Qwen/Qwen1.5-0.5B-Chat", 3, 7.5, "ablated_models/qwen05b_unlearned"),
        ("Qwen/Qwen2.5-7B-Instruct", 1, 0.5, "ablated_models/qwen7b_unlearned"),
        ("Qwen/Qwen2.5-14B-Instruct", 1, 0.5, "ablated_models/qwen14b_unlearned")
    ]
    for model_name, method, strength, out_path in configs:
        os.makedirs(out_path, exist_ok=True)
        save_ablated_model(model_name, method, strength, out_path)
