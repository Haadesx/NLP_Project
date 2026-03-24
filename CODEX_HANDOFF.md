# NLP Project — Complete Handoff Document for Codex
> This document was auto-generated to transfer full project context to a new AI assistant. Read this top-to-bottom before touching any code.

---

## 1. Project Overview

**Research Goal:** Study the effectiveness of two **machine unlearning** techniques for preventing Personally Identifiable Information (PII) leakage in open-source Large Language Models (LLMs):

1. **Orthogonal Representation Ablation** (Phase 1 — COMPLETE)
2. **Direct Preference Optimization (DPO) Unlearning** (Phase 2 — COMPLETE for Mistral + Llama, Phi pending)
3. **MMLU Intelligence Retention Benchmark** (Phase 3 — SUBMITTED to cluster, pending results)

**Academic Context:** Rutgers University NLP Project. The cluster is `ilab.cs.rutgers.edu`. The user's NetID is `vp752`. All GPU jobs run via SLURM. Local machine is a Mac with Apple Silicon (MPS).

---

## 2. Repository Structure

```
NLP_Project/
├── ── PIPELINE 1: Orthogonal Ablation ──
├── pytorch_qwen_abliterator.py        # Abliteration on PyTorch (Qwen models, cluster)
├── mlx_llama_abliterator.py           # Abliteration on Apple Silicon MLX (Llama)
├── mlx_qwen_abliterator.py            # Abliteration on Apple Silicon MLX (Qwen 7B)
├── mlx_qwen14b_abliterator.py         # Abliteration on Apple Silicon MLX (Qwen 14B)
├── save_ablated_models.py             # Saves ablated model weights after abliteration
├── run_ilabs_sweep.slurm              # SLURM: runs the full ablation sweep on cluster
├── run_save_models.slurm              # SLURM: saves ablated models to disk
│
├── ── PIPELINE 2: DPO Unlearning ──
├── dpo_unlearning/
│   ├── generate_dpo_dataset.py        # DONE: generates dpo_dataset.jsonl (1800 train / 200 eval)
│   ├── dpo_dataset.jsonl              # DONE: synthetic PII preference dataset on cluster
│   ├── train_dpo.py                   # DONE: DPOTrainer using TRL 0.29.1 + QLoRA (4-bit) + bfloat16
│   ├── run_dpo_training.slurm         # DONE: SLURM job for DPO training (64G mem, 1 GPU)
│   ├── run_eval_dpo_mistral7b.slurm   # DONE: evaluates Mistral DPO adapter
│   ├── run_eval_dpo_llama8b.slurm     # DONE: evaluates Llama DPO adapter
│   └── run_eval_dpo_phi3.slurm        # CREATED: evaluates Phi DPO adapter (Phi training may still be running)
│
├── ── EVALUATION ──
├── run_generation_eval.py             # Core generative PII benchmark evaluator
│                                      #   --base <hf_model_id>
│                                      #   --unlearned <path_or_hf_id>
│                                      #   --output <report.md>
│                                      #   --is_peft   ← enables PEFT/LoRA adapter loading
├── procedural_generation_dataset.py   # Generates 150-prompt structural PII benchmark
├── pii_generation_dataset.json        # The 150-prompt benchmark dataset (pre-generated)
│
├── ── MMLU (Phase 3) ──
├── run_mmlu_ilabs.slurm               # Parameterized SLURM: sbatch ... <model> <adapter|none> <label> [peft|full]
├── deploy_mmlu_ilabs.sh               # Submits 10 MMLU jobs in parallel (run from local Mac)
├── run_mmlu_eval.py                   # Python driver: runs lm_eval + generates retention report
├── run_local_mmlu.sh                  # Wrapper: installs lm-eval + runs locally on MPS
│
├── ── DEPLOYMENT SCRIPTS ──
├── deploy_dpo.sh                      # Transfers + submits DPO training job
├── deploy_eval_dpo.sh                 # Transfers + submits DPO evaluation job
├── deploy_mmlu_ilabs.sh               # Transfers + submits all 10 MMLU jobs
├── download_adapters.sh               # Downloads trained DPO adapters from cluster to local
│
├── ── RESULTS ──
├── benchmark_report_7B_Mistral_DPO_Gen.md   # ✅ KEY RESULT: Mistral DPO eval (0% leakage)
├── benchmark_report_7B_Gen.md         # Qwen 7B orthogonal ablation generative eval
├── benchmark_report_14B_Gen.md        # Qwen 14B orthogonal ablation generative eval
├── benchmark_report_7B_Mistral_Gen.md # Mistral base generative eval
├── results/                           # MMLU results will land here (after cluster jobs finish)
│   └── mmlu_<label>/                  # One folder per model/condition
│
└── adapters/                          # LOCAL: downloaded DPO LoRA adapters (from cluster)
    ├── mistral_7b_dpo/                # adapter_config.json + adapter_model.safetensors
    ├── llama3_8b_dpo/
    └── phi3_dpo/
```

---

## 3. Remote Cluster Paths (iLabs)

| Resource | Path |
|:---|:---|
| Home directory | `/common/home/vp752/NLP_Project/` |
| User scratch | `/common/users/vp752/NLP_Project/` |
| HF Cache | `/common/users/vp752/.cache/huggingface/` |
| Conda env | `/common/users/vp752/miniconda3/envs/diffullm` |
| Mistral DPO adapter | `/common/users/vp752/NLP_Project/models/mistralai/Mistral-7B-Instruct-v0.2_dpo_adapter/checkpoint-225` |
| Llama DPO adapter | `/common/users/vp752/NLP_Project/models/meta-llama/Meta-Llama-3-8B-Instruct_dpo_adapter/final_adapter` |
| Phi-3 DPO adapter | `/common/users/vp752/NLP_Project/models/microsoft/Phi-3-mini-4k-instruct_dpo_adapter/final_adapter` |
| Qwen 7B ablated | `/common/users/vp752/ablated_models/qwen7b_unlearned` |
| Qwen 14B ablated | `/common/users/vp752/ablated_models/qwen14b_unlearned` |
| SLURM logs | `/common/home/vp752/NLP_Project/logs/` |

**HF Token:** `[REDACTED - set via environment variable]`

---

## 4. Key Research Findings So Far

### Phase 1 — Orthogonal Representation Ablation Results (FAILED)
The orthogonal ablation destroyed the model's safety refusal guardrails, leading to _increased_ PII leakage:

| Model | Parameters | Base Leakage | Ablated Leakage | Change |
|:---|:---|:---|:---|:---|
| Phi-3 | 3B | 21.3% (32/150) | 34.7% (52/150) | ⬆ +13.4% WORSE |
| Mistral | 7B | 30.7% (46/150) | 32.0% (48/150) | ⬆ +1.3% WORSE |
| Qwen 2.5 7B | 7B | 52.0% (78/150) | 48.7% (73/150) | ⬇ -3.3% (marginal) |
| Qwen 2.5 14B | 14B | 51.3% (77/150) | 49.3% (74/150) | ⬇ -2.0% (marginal) |

**Conclusion:** Orthogonal ablation is NOT effective for preventing _generative_ PII leakage.

### Phase 2 — DPO Unlearning Results (SUCCESS ✅)
DPO preference training with synthetic PII rejection pairs completely eliminated leakage:

| Model | Parameters | Base Leakage | DPO Leakage | Change |
|:---|:---|:---|:---|:---|
| **Mistral 7B (DPO)** | 7B | 30.7% (46/150) | **0.0% (0/150)** | **-100%** ✅ |
| Llama 3 8B (DPO) | 8B | TBD | TBD | Pending eval |
| Phi-3 (DPO) | 3.8B | TBD | TBD | Training may still be running |

**Conclusion:** DPO unlearning is dramatically more effective than orthogonal ablation for preventing generative PII leakage.

---

## 5. Models Used

| Model HF ID | Role |
|:---|:---|
| `mistralai/Mistral-7B-Instruct-v0.2` | DPO fine-tuned ✅ |
| `meta-llama/Meta-Llama-3-8B-Instruct` | DPO fine-tuned ✅ |
| `microsoft/Phi-3-mini-4k-instruct` | DPO training submitted (job 123088) |
| `Qwen/Qwen2.5-7B-Instruct` | Orthogonally ablated (full model save) |
| `Qwen/Qwen2.5-14B-Instruct` | Orthogonally ablated (full model save) |

---

## 6. DPO Training Configuration

```python
# Key training settings in train_dpo.py
model = AutoModelForCausalLM (4-bit QLoRA via BitsAndBytes)
dtype = torch.bfloat16                 # CRITICAL: must be bfloat16, NOT float16
bnb_4bit_compute_dtype = torch.bfloat16

LoRA config:
  r = 16, alpha = 32, dropout = 0.05
  target_modules = ["q_proj", "v_proj"]

DPOConfig:
  beta = 0.1
  bf16 = True                          # CRITICAL
  num_train_epochs = 1
  per_device_train_batch_size = 4
  gradient_accumulation_steps = 4      # effective batch = 16
  learning_rate = 5e-5

Dataset: dpo_dataset.jsonl (1800 train / 200 eval)
  Format: {"prompt": "...", "chosen": "I cannot...", "rejected": "Here is a SSN: 123-45-6789"}
```

---

## 7. Key Bugs Already Solved — Do NOT Repeat These

| Bug | Fix Applied |
|:---|:---|
| `ImportError: cannot import DPOConfig` | Install TRL ≥ 0.29.1 |
| `TypeError: DPOTrainer() got unexpected 'tokenizer'` | Use `processing_class=tokenizer` |
| `eval_strategy` vs `evaluation_strategy` | Use `eval_strategy` (new API) |
| `RuntimeError: _amp_foreach_non_finite_check...BFloat16` | Set `bf16=True` NOT `fp16=True` in DPOConfig |
| `max_length`, `max_prompt_length` deprecated | Remove from DPOConfig in TRL 0.29.1 |
| `adapter_config.json not found` | Training saves to `checkpoint-225/` subdirectory, NOT root. Use `/checkpoint-225` suffix in adapter path |
| `PeftModel.from_pretrained` fails with absolute path | lm-eval PEFT arg works fine — issue was wrong path (see above) |

---

## 8. Immediate Pending Tasks

### 8a. Check if Phi-3 DPO Evaluation Has Completed
```bash
ssh vp752@ilab.cs.rutgers.edu 'cat ~/NLP_Project/logs/eval_dpo_phi_*.err | tail -20'
ssh vp752@ilab.cs.rutgers.edu 'cat ~/NLP_Project/results/benchmark_report_3B_Phi_DPO_Gen.md'
```

### 8b. Run MMLU Intelligence Retention Benchmark (10 parallel jobs)
All 5 models × 2 conditions (base vs. unlearned). Submit from local Mac:
```bash
./deploy_mmlu_ilabs.sh
```
Monitor: `ssh vp752@ilab.cs.rutgers.edu 'squeue -u vp752'`
Results land in: `~/NLP_Project/results/mmlu_<label>/`

After results are ready, compile the comparison report:
```bash
# On cluster, collect JSON results then run locally:
python3 run_mmlu_eval.py --skip-base   # if base already ran
```

### 8c. Once MMLU is Done
Update `walkthrough.md` with the final intelligence retention table showing DPO vs Ablation vs Base on both PII leakage AND MMLU.

---

## 9. How to Continue Development

### Adding More Models to DPO Pipeline
```bash
# On cluster in dpo_unlearning/:
sbatch run_dpo_training.slurm <HuggingFace/Model-ID>

# Evaluate:
# Edit run_eval_dpo_mistral7b.slurm as template, change --base, --unlearned, --output
sbatch run_eval_dpo_<model>.slurm
```

### Running the Generative PII Benchmark
```bash
# For a base model:
python3 run_generation_eval.py --base <hf_id> --unlearned <path> --output results/report.md

# For a DPO LoRA model:
python3 run_generation_eval.py --base <hf_id> --unlearned <adapter_path> --output results/report.md --is_peft
```

### MMLU on Cluster (single model)
```bash
sbatch run_mmlu_ilabs.slurm <model_hf_id> <adapter_or_none> <label> [peft|full]
# peft = LoRA adapter (DPO models)
# full = full model save (Qwen ablated models)
# none = base model (no adapter)
```

---

## 10. Python Environment

- **Conda env:** `diffullm` (Python 3.11)
- **Key packages:** `trl==0.29.1`, `peft==0.18.1`, `transformers`, `torch (bfloat16)`, `accelerate`, `bitsandbytes`, `lm-eval==0.4.2`
- **Local Mac:** Uses MPS device for inference. `pip3` not `pip`.
