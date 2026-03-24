"""
MMLU Benchmark Evaluator for DPO Unlearned Models.

Runs the 5-shot MMLU benchmark against base models and their DPO LoRA adapters
to measure general intelligence retention after unlearning. Outputs a markdown
comparison table.
"""

import argparse
import json
import os
import subprocess
import sys
import re


MODELS = [
    {
        "name": "Mistral 7B",
        "base": "mistralai/Mistral-7B-Instruct-v0.2",
        "adapter": "adapters/mistral_7b_dpo",
        "output_base": "results/mmlu/local/base/mistral_base",
        "output_dpo": "results/mmlu/local/dpo/mistral_dpo",
    },
    {
        "name": "Llama 3 8B",
        "base": "meta-llama/Meta-Llama-3-8B-Instruct",
        "adapter": "adapters/llama3_8b_dpo",
        "output_base": "results/mmlu/local/base/llama_base",
        "output_dpo": "results/mmlu/local/dpo/llama_dpo",
    },
    {
        "name": "Phi-3",
        "base": "microsoft/Phi-3-mini-4k-instruct",
        "adapter": "adapters/phi3_dpo",
        "output_base": "results/mmlu/local/base/phi3_base",
        "output_dpo": "results/mmlu/local/dpo/phi3_dpo",
    },
]


def run_lm_eval(model_args: str, output_path: str, num_fewshot: int = 5, device: str = "mps"):
    """Runs `lm_eval` for a single model config and saves the JSON results."""
    os.makedirs(output_path, exist_ok=True)
    cmd = [
        sys.executable, "-m", "lm_eval",
        "--model", "hf",
        "--model_args", f"{model_args},trust_remote_code=True",
        "--tasks", "mmlu",
        "--num_fewshot", str(num_fewshot),
        "--device", device,
        "--output_path", output_path,
        "--log_samples",
    ]
    print(f"\n>>> Running: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        print(f"⚠️  lm_eval returned exit code {result.returncode}. Check logs above.")
    return result.returncode


def extract_mmlu_accuracy(output_path: str) -> float | None:
    """Parses the lm_eval JSON output to extract the aggregate MMLU accuracy."""
    # lm_eval writes results inside a subdirectory of output_path
    for root, dirs, files in os.walk(output_path):
        for fname in files:
            if fname.endswith(".json") and "results" in fname:
                fpath = os.path.join(root, fname)
                with open(fpath) as f:
                    data = json.load(f)
                results = data.get("results", {})
                # Try aggregate key first
                for key in ["mmlu", "mmlu_average"]:
                    if key in results:
                        acc = results[key].get("acc,none") or results[key].get("acc")
                        if acc is not None:
                            return round(float(acc) * 100, 2)
    return None


def build_markdown_report(rows: list[dict]) -> str:
    lines = [
        "# MMLU Intelligence Retention Report",
        "",
        "Evaluates general knowledge and reasoning capability retention after DPO PII Unlearning.",
        "Higher is better. A minimal drop (<1.5%) indicates successful targeted unlearning without catastrophic forgetting.",
        "",
        "| Model | Base MMLU (%) | DPO Unlearned MMLU (%) | Change |",
        "| :--- | :---: | :---: | :---: |",
    ]
    for row in rows:
        base = row.get("base_acc")
        dpo = row.get("dpo_acc")
        base_str = f"{base:.2f}" if base is not None else "Pending"
        dpo_str = f"{dpo:.2f}" if dpo is not None else "Pending"
        if base is not None and dpo is not None:
            change = dpo - base
            sign = "+" if change >= 0 else ""
            change_str = f"{sign}{change:.2f}%"
            emoji = "✅" if change > -2.0 else "⚠️"
            change_str = f"{emoji} {change_str}"
        else:
            change_str = "—"
        lines.append(f"| **{row['name']}** | {base_str} | {dpo_str} | {change_str} |")
    lines += [
        "",
        "## Notes",
        "- Benchmark: [MMLU](https://arxiv.org/abs/2009.03300) (5-shot, 57 subjects)",
        "- DPO models use LoRA adapters loaded on top of base weights",
        "- Device: Apple Silicon MPS (local evaluation)",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Run MMLU on Base and DPO models")
    parser.add_argument("--device", default="mps", help="Device to use (mps, cuda, cpu)")
    parser.add_argument("--models", nargs="*", help="Which models to run (mistral, llama, phi). Omit for all.")
    parser.add_argument("--skip-base", action="store_true", help="Skip base model evaluation (reuse existing results)")
    args = parser.parse_args()

    filter_names = args.models or []
    rows = []

    for cfg in MODELS:
        short = cfg["name"].lower().split()[0]
        if filter_names and short not in filter_names:
            print(f"Skipping {cfg['name']} (not in filter).")
            rows.append({"name": cfg["name"], "base_acc": None, "dpo_acc": None})
            continue

        adapter_local = cfg["adapter"]
        if not os.path.isdir(adapter_local):
            print(f"\n⚠️  Adapter folder '{adapter_local}' not found! Run ./download_adapters.sh first.")
            rows.append({"name": cfg["name"], "base_acc": None, "dpo_acc": None})
            continue

        # Base model
        base_acc = None
        if not args.skip_base:
            print(f"\n{'='*60}")
            print(f"  BASE MODEL: {cfg['name']}")
            print(f"{'='*60}")
            run_lm_eval(f"pretrained={cfg['base']}", cfg["output_base"], device=args.device)
        base_acc = extract_mmlu_accuracy(cfg["output_base"])

        # DPO adapter
        print(f"\n{'='*60}")
        print(f"  DPO MODEL: {cfg['name']}")
        print(f"{'='*60}")
        run_lm_eval(
            f"pretrained={cfg['base']},peft={adapter_local}",
            cfg["output_dpo"],
            device=args.device,
        )
        dpo_acc = extract_mmlu_accuracy(cfg["output_dpo"])

        rows.append({"name": cfg["name"], "base_acc": base_acc, "dpo_acc": dpo_acc})
        print(f"\n  {cfg['name']}: Base={base_acc}%, DPO={dpo_acc}%")

    report = build_markdown_report(rows)
    report_path = "results/summaries/mmlu_intelligence_retention_report.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        f.write(report)

    print(f"\n\n✅ MMLU Report saved to {report_path}")
    print("\n" + report)


if __name__ == "__main__":
    main()
