## Results

All result artifacts are organized here by benchmark and method.

- `generation/ablation/`: generative leakage reports for ablation runs
- `generation/dpo/`: generative leakage reports for DPO runs
- `generation/legacy/`: older or duplicated reports kept for reference
- `mmlu/base/`: base-model MMLU outputs
- `mmlu/ablation/`: ablated-model MMLU outputs
- `mmlu/dpo/`: DPO-model MMLU outputs
- `mmlu/local/`: local MMLU runs produced by `run_mmlu_eval.py`
- `ablation/sweeps/`: saved ablation sweep JSON outputs
- `ablation/metrics/`: local evaluation JSON artifacts
- `summaries/`: consolidated reports

Flat legacy paths are preserved as symlinks where needed so older scripts and notes still resolve.
