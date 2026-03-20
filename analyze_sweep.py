import json
import glob
import os

def analyze(file_path):
    print(f"=== {os.path.basename(file_path)} ===")
    with open(file_path, "r") as f:
        data = json.load(f)
    
    base_ppl = data["baseline"]["perplexity"]
    base_pii = data["baseline"]["pii_retention"]
    print(f"Baseline: PPL {base_ppl:.2f}, PII: {base_pii*100:.1f}%")
    
    # Sort purely by lowest PII retention, then PPL
    results = data["ablation_results"]
    results.sort(key=lambda x: (x["pii_retention"], x["perplexity"]))
    
    best = results[0]
    print(f"Best: {best['method']} -> PII: {best['pii_retention']*100:.1f}%, PPL: {best['perplexity']:.2f}")

if __name__ == "__main__":
    for f in sorted(glob.glob("results/*.json")):
        analyze(f)
